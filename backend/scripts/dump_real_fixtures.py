"""Refresh the real NBA fixtures the app serves.

Pulls real players/box scores/schedule from stats.nba.com into sample_data/*.json
(the canonical fixtures the API reads). The API also materializes these automatically
on first use; run this to force a refresh or target a specific season.

    .venv/bin/python scripts/dump_real_fixtures.py [season e.g. 2025-26]
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.data.nba_fixtures import build_real_fixtures  # noqa: E402

SAMPLE_DIR = BACKEND / "sample_data"


def main() -> int:
    seasons = [sys.argv[1]] if len(sys.argv) > 1 else None
    summary = build_real_fixtures(SAMPLE_DIR, seasons)
    print(f"\n[OK] Wrote REAL fixtures to {SAMPLE_DIR}")
    print(f"     season={summary['season']}  week={summary['week_start']}..{summary['week_end']}")
    print(f"     teams={summary['teams']} players={summary['players']} "
          f"logs={summary['logs']} schedule_games={summary['schedule_games']}")
    print("     default roster (used by /api/recommendations/sample):")
    for name in summary["sample_roster"]:
        print(f"        {name}")
    print("\nServe it:  uvicorn app.main:app --reload")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
