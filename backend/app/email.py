"""Transactional email via Resend.

Thin wrapper over Resend's HTTP API (no extra SDK dependency). Sending is
optional: if RESEND_API_KEY is unset, send_email() no-ops and returns False,
mirroring how Stripe/OpenAI degrade when unconfigured.
"""
from __future__ import annotations

import logging

import httpx

from .config import settings

logger = logging.getLogger("waiveredge.email")

RESEND_API_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, html: str) -> bool:
    """Send one transactional email. Returns True on success, False otherwise.

    No-ops (returns False) when Resend isn't configured so callers don't need to
    branch on it.
    """
    if not settings.resend_api_key:
        return False
    try:
        resp = httpx.post(
            RESEND_API_URL,
            timeout=15.0,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.resend_from, "to": [to], "subject": subject, "html": html},
        )
        resp.raise_for_status()
        return True
    except Exception as e:  # best-effort — a failed alert email must not break scanning
        logger.warning("Resend email to %s failed: %s", to, e)
        return False
