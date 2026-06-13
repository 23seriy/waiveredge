"""Validate the scoring engine against REAL balldontlie data.

Pulls a dense mid-season window of real NBA box scores + a real upcoming-week
schedule + current injuries, then runs the actual scoring engine on it. Three checks:

  1. DATA   — every endpoint authenticates and returns rows (teams/games/stats/injuries).
  2. FACE   — top players by recency-weighted fppg are actually NBA stars.
  3. ENGINE — projections x DvP x schedule-density rerank real players, and
              rank_waiver_adds produces a sensible action list over a synthetic league.

Usage:
    .venv/bin/python scripts/validate_real.py [stats_start stats_end week_start week_end]

Defaults validate on Jan 2026 regular-season data (dense, many teams).
The key is read from $BALLDONTLIE_API_KEY, then backend/.env, then repo-root .env.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.data.balldontlie import BalldontlieClient, BalldontlieError  # noqa: E402
from app.scoring.engine import project_value, rank_waiver_adds  # noqa: E402
from app.scoring.matchups import compute_dvp  # noqa: E402
from app.scoring.projections import project_all  # noqa: E402
from app.scoring.scoring_systems import DEFAULT_POINTS_SCORING  # noqa: E402
from app.scoring.types import GameLog, Injury, Player, ScheduledGame  # noqa: E402

# Defaults: a dense regular-season stretch and the week right after it.
STATS_START, STATS_END = "2026-01-05", "2026-01-18"
WEEK_START, WEEK_END = "2026-01-19", "2026-01-25"
if len(sys.argv) == 5:
    STATS_START, STATS_END, WEEK_START, WEEK_END = sys.argv[1:5]

SCORING = DEFAULT_POINTS_SCORING


def resolve_key() -> str:
    import os

    if os.environ.get("BALLDONTLIE_API_KEY"):
        return os.environ["BALLDONTLIE_API_KEY"].strip()
    for rel in ("backend/.env", ".env", "../.env"):
        p = (BACKEND / rel) if not rel.startswith("..") else (BACKEND.parent / rel[3:])
        candidate = Path(rel)
        for path in (p, candidate, BACKEND / ".env", BACKEND.parent / ".env"):
            if path.exists():
                m = re.search(r'^\s*BALLDONTLIE_API_KEY\s*=\s*(.*)$', path.read_text(), re.M)
                if m and m.group(1).strip().strip('"').strip("'"):
                    return m.group(1).strip().strip('"').strip("'")
    return ""


def primary_position(pos: str | None) -> str:
    if not pos:
        return "UTIL"
    token = pos.replace("-", " ").split()[0].upper()
    return {"G": "PG", "F": "SF"}.get(token, token)


def parse_min(value: object) -> int:
    if not value:
        return 0
    s = str(value).split(":")[0]
    return int(s) if s.lstrip("-").isdigit() else 0


def main() -> int:
    key = resolve_key()
    if not key:
        print("ERROR: no BALLDONTLIE_API_KEY found in env, backend/.env, or root .env")
        return 1

    bar = "=" * 72
    print(f"\n{bar}\n REAL-DATA VALIDATION  (stats {STATS_START}..{STATS_END}, "
          f"week {WEEK_START}..{WEEK_END})\n{bar}")

    teams_raw = games_raw = stats_raw = injuries_raw = None
    with BalldontlieClient(api_key=key, min_interval=0.15) as bdl:
        # 1) Free endpoints first — proves auth works at all.
        try:
            teams_raw = bdl.teams()
            games_raw = bdl.games(WEEK_START, WEEK_END)
        except (BalldontlieError, httpx.HTTPStatusError) as e:
            print(f"\n[DATA] FAILED on a free endpoint: {e}")
            return 2
        print(f"\n[DATA] teams={len(teams_raw)}  games_this_week={len(games_raw)}")

        # 2) ALL-STAR endpoints — stats + injuries.
        try:
            print("[DATA] pulling box scores (this can take ~10-30s)...")
            stats_raw = bdl.stats(STATS_START, STATS_END)
        except (BalldontlieError, httpx.HTTPStatusError) as e:
            print(f"\n[DATA] /v1/stats FAILED: {e}")
            print("       This endpoint needs the ALL-STAR tier ($9.99/mo). "
                  "Free endpoints worked, so the key is valid — just upgrade the tier.")
            return 3
        try:
            injuries_raw = bdl.player_injuries()
        except (BalldontlieError, httpx.HTTPStatusError) as e:
            print(f"[DATA] /v1/player_injuries unavailable ({e}); continuing without injuries.")
            injuries_raw = []
    print(f"[DATA] stat_rows={len(stats_raw)}  injuries={len(injuries_raw)}")

    team_abbr = {t["id"]: t["abbreviation"] for t in teams_raw}

    # Build schedule.
    schedule: list[ScheduledGame] = []
    for g in games_raw:
        home = (g.get("home_team") or {}).get("id") or g.get("home_team_id")
        vis = (g.get("visitor_team") or {}).get("id") or g.get("visitor_team_id")
        if home and vis:
            schedule.append(ScheduledGame(g["id"], str(g.get("date", ""))[:10], home, vis))

    # Build game logs + a player index from real box scores (skip DNPs).
    players: dict[int, Player] = {}
    logs_by_player: dict[int, list[GameLog]] = {}
    all_logs: list[GameLog] = []
    skipped = 0
    for s in stats_raw:
        player = s.get("player") or {}
        team = s.get("team") or {}
        game = s.get("game") or {}
        pid, gid, tid = player.get("id"), game.get("id"), team.get("id")
        if not (pid and gid and tid):
            skipped += 1
            continue
        if parse_min(s.get("min")) <= 0:
            continue
        home = game.get("home_team_id") or (game.get("home_team") or {}).get("id")
        vis = game.get("visitor_team_id") or (game.get("visitor_team") or {}).get("id")
        if home is None or vis is None:
            skipped += 1
            continue
        opp = vis if tid == home else home
        pos = primary_position(player.get("position"))
        line = {k: (s.get(k) or 0) for k in ("pts", "reb", "ast", "stl", "blk", "fg3m", "turnover")}
        log = GameLog(pid, gid, str(game.get("date", ""))[:10], tid, opp, pos, line)
        all_logs.append(log)
        logs_by_player.setdefault(pid, []).append(log)
        name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
        players[pid] = Player(pid, name, tid, [pos])  # latest team wins

    print(f"[DATA] usable logs={len(all_logs)}  unique_players={len(players)}  skipped_rows={skipped}")
    if not all_logs or not schedule:
        print("\nNot enough real data in this window (logs or schedule empty). "
              "Try a different window: validate_real.py <stats_start> <stats_end> <week_start> <week_end>")
        return 4

    projections = project_all(logs_by_player, SCORING)
    dvp = compute_dvp(all_logs, SCORING)
    injuries = {
        (i.get("player") or {}).get("id"): Injury(
            (i.get("player") or {}).get("id"), i.get("status", ""), i.get("description", "") or "")
        for i in injuries_raw if (i.get("player") or {}).get("id")
    }
    players_by_team: dict[int, list[Player]] = {}
    for p in players.values():
        players_by_team.setdefault(p.team_id, []).append(p)

    qualified = [pid for pid, pr in projections.items() if pr.games_sampled >= 3]
    by_fppg = sorted(qualified, key=lambda pid: projections[pid].fppg, reverse=True)

    # ---- CHECK 2: face validity --------------------------------------------
    print(f"\n[FACE] Top 15 players by recency-weighted fppg "
          f"({len(qualified)} players with >=3 games) — should be recognizable stars:")
    for pid in by_fppg[:15]:
        p, pr = players[pid], projections[pid]
        print(f"   {pr.fppg:6.1f} fppg  {p.name:<24} {team_abbr.get(p.team_id,'?'):>3} {p.primary} "
              f"({pr.games_sampled} g)")

    # ---- CHECK 3a: schedule-density rerank ---------------------------------
    games_per_team: dict[int, int] = {}
    for g in schedule:
        games_per_team[g.home_team_id] = games_per_team.get(g.home_team_id, 0) + 1
        games_per_team[g.visitor_team_id] = games_per_team.get(g.visitor_team_id, 0) + 1
    dens = sorted(games_per_team.items(), key=lambda kv: -kv[1])
    print(f"\n[ENGINE] Real schedule density this week — "
          f"{len(games_per_team)} teams play; "
          f"{', '.join(f'{team_abbr.get(t,t)}={n}' for t, n in dens[:6])} ...")

    pool = by_fppg[:80]
    weekly = {pid: project_value(players[pid], projections[pid], schedule, (WEEK_START, WEEK_END),
                                 dvp, injuries, players_by_team) for pid in pool}
    by_weekly = sorted(pool, key=lambda pid: weekly[pid].value, reverse=True)
    fppg_rank = {pid: i for i, pid in enumerate(sorted(pool, key=lambda p: projections[p].fppg,
                                                        reverse=True), 1)}
    print("\n[ENGINE] Top 12 by PROJECTED WEEKLY VALUE (fppg x games x matchup x availability):")
    print("         value  games  Δrank  player")
    for wrank, pid in enumerate(by_weekly[:12], 1):
        vr = weekly[pid]
        delta = fppg_rank[pid] - wrank
        arrow = f"+{delta}" if delta > 0 else (str(delta) if delta < 0 else "·")
        print(f"   {vr.value:8.1f} {vr.n_games:5d}  {arrow:>5}  {players[pid].name} "
              f"({team_abbr.get(players[pid].team_id,'?')})")
    print("   (Δrank = positions moved vs raw-fppg order — schedule + matchup at work)")

    # ---- CHECK 3b: rank_waiver_adds on a synthetic league ------------------
    roster_ids = by_fppg[45:55]                       # mid-tier "your team"
    roster = [players[pid] for pid in roster_ids]
    roster_set = set(roster_ids)
    fa_ids = [pid for pid in by_fppg[60:130]
              if pid not in roster_set and games_per_team.get(players[pid].team_id, 0) > 0][:30]
    free_agents = [players[pid] for pid in fa_ids]
    recs = rank_waiver_adds(roster, free_agents, set(), projections, schedule,
                            (WEEK_START, WEEK_END), dvp, injuries, players_by_team)
    print(f"\n[ENGINE] rank_waiver_adds on a synthetic mid-tier roster "
          f"({len(roster)} players) vs {len(free_agents)} waiver-caliber FAs — top 8 adds:")
    for i, r in enumerate(recs[:8], 1):
        print(f"   {i}. [{r.marginal:+6.1f}]  {r.rationale}")

    inj_hits = sum(1 for r in recs if "elevated role" in r.rationale or "availability" in r.rationale)
    print(f"\n[OK] Validation complete. Real data flowed through projections + DvP + schedule + "
          f"value-over-replacement.\n     Injury signals affecting ranked adds: {inj_hits}. "
          f"Active injuries loaded: {len(injuries)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
