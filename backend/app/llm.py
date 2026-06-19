"""LLM-powered rationale generation for recommendations.

Takes the structured recommendation data and generates a natural-language
explanation that a fantasy manager can act on. Falls back to the engine's
built-in rationale when the LLM is unavailable.

Uses OpenAI's chat completions API (gpt-4o-mini for speed/cost).
"""
from __future__ import annotations

import httpx

from .config import settings

MODEL = "gpt-4o-mini"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = """You are a fantasy sports analyst writing quick, actionable waiver recommendations.

Given structured recommendation data, write a 2-3 sentence rationale that:
1. Explains WHY this player is valuable this week (schedule, matchups, role)
2. Explains WHO to drop and why they're the weakest link
3. Uses a confident, conversational tone — like a fantasy podcast host

Keep it concise. No hedging. Use the player's name naturally.
Do NOT repeat the raw numbers verbatim — interpret them for the manager."""


def generate_rationale(rec: dict, sport: str = "nba") -> str | None:
    """Generate a natural-language rationale for a recommendation.

    Returns None if the LLM is unavailable or fails (caller should
    fall back to the engine's built-in rationale).
    """
    if not settings.openai_api_key:
        return None

    sport_name = "basketball" if sport == "nba" else "baseball"
    user_msg = (
        f"Sport: {sport_name}\n"
        f"Add: {rec.get('add_name', '?')} ({rec.get('add_position', '?')})\n"
        f"Games this week: {rec.get('n_games', 0)}\n"
        f"Soft matchups: {rec.get('soft_matchups', 0)}\n"
        f"Projected value: {rec.get('add_value', 0):.1f}\n"
        f"Drop: {rec.get('drop_name', 'none')}\n"
        f"Drop value: {rec.get('drop_value', 0):.1f}\n"
        f"Marginal gain: {rec.get('marginal', 0):+.1f}\n"
        f"Engine rationale: {rec.get('rationale', '')}"
    )

    try:
        resp = httpx.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 150,
                "temperature": 0.7,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def enrich_recommendations(recs: list[dict], sport: str = "nba", max_enriched: int = 10) -> list[dict]:
    """Add LLM rationales to the top N recommendations.

    Only enriches the top `max_enriched` to control API costs.
    Each rec gets an `llm_rationale` field (None if LLM unavailable).
    """
    if not settings.openai_api_key:
        return recs

    for rec in recs[:max_enriched]:
        llm = generate_rationale(rec, sport)
        rec["llm_rationale"] = llm
    return recs
