"""Google OAuth 2.0 authentication + HMAC-signed Bearer token.

Flow:
1. Frontend links to GET /api/auth/google → redirect to Google consent screen.
2. Google redirects back to GET /api/auth/google/callback?code=... .
3. We exchange the code for tokens, decode the id_token for profile info,
   upsert a User row, and redirect to the frontend with ?token=... .
4. Frontend stores the token in localStorage and sends it as Authorization: Bearer.
5. GET /api/auth/me returns the current user from the Bearer token.
6. POST /api/auth/logout is a no-op (frontend clears localStorage).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import bcrypt
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import safe_redirect_url, settings
from ..db import get_db
from ..models import User

router = APIRouter(prefix="/api/auth", tags=["auth-google"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

TOKEN_MAX_AGE = 30 * 24 * 3600  # 30 days


# --- HMAC-signed token helpers ---

def _sign(payload: str) -> str:
    sig = hmac.new(settings.app_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify(token: str) -> dict | None:
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return None
    payload, sig = parts
    expected = hmac.new(settings.app_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        return None
    if data.get("exp", 0) < time.time():
        return None
    return data


def _make_token(user: User) -> str:
    payload = json.dumps({
        "uid": user.id,
        "exp": int(time.time()) + TOKEN_MAX_AGE,
    })
    return _sign(payload)


def _get_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """FastAPI dependency: returns the logged-in User or None."""
    token = _get_bearer_token(request)
    if not token:
        return None
    data = _verify(token)
    if not data:
        return None
    return db.query(User).filter(User.id == data["uid"]).first()


def require_user(user: User | None = Depends(get_current_user)) -> User:
    """FastAPI dependency: requires a logged-in user or raises 401."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# --- Password helpers ---

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# --- Email/password models ---

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


# --- Email/password endpoints ---

@router.post("/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    """Create a new account with email and password."""
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email is required.")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    existing = db.query(User).filter(User.email == email).first()
    if existing and existing.password_hash:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    if existing:
        # User exists from OAuth but has no password — allow setting one.
        existing.password_hash = _hash_password(req.password)
        if req.name and not existing.name:
            existing.name = req.name
        db.commit()
        token = _make_token(existing)
        return {"token": token, "user": {"id": existing.id, "email": existing.email, "name": existing.name}}

    user = User(
        email=email,
        password_hash=_hash_password(req.password),
        name=req.name.strip() or email.split("@")[0],
    )
    db.add(user)
    db.commit()
    token = _make_token(user)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Sign in with email and password."""
    email = req.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not _check_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = _make_token(user)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}


# --- Endpoints ---

@router.get("/google")
def google_login():
    """Redirect the user to Google's OAuth consent page."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(code: str = Query(...), db: Session = Depends(get_db)):
    """Handle Google's OAuth callback — exchange code, upsert user, set cookie."""
    # Exchange code for tokens.
    try:
        token_resp = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Google token exchange failed: {exc}") from exc

    # Fetch user profile.
    try:
        profile_resp = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=10,
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch Google profile: {exc}") from exc

    google_id = profile.get("sub", "")
    email = profile.get("email", "")
    name = profile.get("name", "")
    picture = profile.get("picture", "")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Google did not return required profile info.")

    # Upsert user.
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()
    if user:
        user.google_id = google_id
        user.name = name
        user.picture = picture
        if user.email != email:
            user.email = email
    else:
        user = User(email=email, google_id=google_id, name=name, picture=picture)
        db.add(user)
    db.flush()
    db.commit()

    # Generate token and redirect to frontend with it in the URL.
    token = _make_token(user)
    return RedirectResponse(safe_redirect_url(f"{settings.frontend_url}/auth/callback?token={token}"))


@router.get("/me")
def me(user: User | None = Depends(get_current_user)):
    """Return the current logged-in user, or null."""
    if not user:
        return {"user": None}
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "tier": user.tier,
        }
    }


@router.post("/logout")
def logout():
    """No-op — frontend clears localStorage."""
    return {"ok": True}
