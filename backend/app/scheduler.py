"""Background scheduler for nightly fixture refresh.

Runs as a daemon thread on app startup. Checks fixture staleness every
hour and rebuilds any sport that's older than CACHE_MAX_AGE_SECONDS.
This ensures users always get fresh data without manual intervention.

In production, this replaces the need for an external cron job.
"""
from __future__ import annotations

import threading
import time
import logging

from .recommendations import (
    CACHE_MAX_AGE_SECONDS,
    SPORT_DIRS,
    _build_fixtures_background,
    _build_status,
    _is_fresh,
)

logger = logging.getLogger("waiveredge.scheduler")

# How often to check for stale fixtures (1 hour).
CHECK_INTERVAL_SECONDS = 60 * 60


def _scheduler_loop() -> None:
    """Main scheduler loop — runs forever in a daemon thread."""
    logger.info("Fixture refresh scheduler started (check interval: %ds)", CHECK_INTERVAL_SECONDS)

    # Wait 30s on startup to let the app initialize.
    time.sleep(30)

    while True:
        for sport in SPORT_DIRS:
            try:
                if not _is_fresh(sport):
                    status = _build_status.get(sport, {})
                    if not status.get("building"):
                        logger.info("Fixtures for %s are stale — starting background rebuild", sport)
                        _build_fixtures_background(sport)
                    else:
                        logger.info("Fixtures for %s are stale but build already in progress", sport)
                else:
                    data_dir = SPORT_DIRS[sport]
                    roster_file = data_dir / "roster.json"
                    if roster_file.exists():
                        age_h = (time.time() - roster_file.stat().st_mtime) / 3600
                        logger.debug("Fixtures for %s are fresh (%.1fh old)", sport, age_h)
            except Exception as e:
                logger.warning("Scheduler error for %s: %s", sport, e)

        # Scan connected leagues for injury-driven pickup opportunities.
        try:
            from .api.alerts import scan_all_connections
            result = scan_all_connections()
            if result["new_alerts"]:
                logger.info("Injury scan: %d new alerts across %d connections",
                            result["new_alerts"], result["connections_scanned"])
        except Exception as e:
            logger.warning("Injury scan failed: %s", e)

        time.sleep(CHECK_INTERVAL_SECONDS)


def start_scheduler() -> None:
    """Start the background fixture refresh scheduler."""
    thread = threading.Thread(target=_scheduler_loop, name="fixture-scheduler", daemon=True)
    thread.start()
