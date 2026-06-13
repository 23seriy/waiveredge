"""Validate the scoring engine against REAL NBA data — for free.

Pulls real player game logs straight from stats.nba.com (the NBA's official source
that free APIs like balldontlie wrap) via nba_api. Works from a residential IP;
datacenter IPs are what stats.nba.com blocks, which is exactly why a *deployed*
product pays for a stabilized feed instead.

One LeagueGameLog request returns every player's box score for a date range. We
split it into a projection window and the week after it, then run the real engine:

  1. DATA   — real box scores arrive from stats.nba.com.
  2. FACE   — top players by recency-weighted fppg are actual NBA stars.
  3. ENGINE — projections x team-matchup x schedule-density rerank real players,
              and rank_waiver_adds produces a sensible action list.

Caveats vs the paid balldontlie path: team-level matchups (no positional DvP) and
no injuries — those specifics are what the ALL-STAR tier cleanly provides. The core
fusion (projection x games-this-week x matchup, value-over-replacement) is fully
exercised on real players.

    .venv/bin/python scripts/validate_nba_api.py [season e.g. 2025-26]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.scoring.engine import project_value, rank_waiver_adds  # noqa: E402
from app.scoring.matchups import compute_dvp  # noqa: E402
from app.scoring.projections import project_all  # noqa: E402
from app.scoring.scoring_systems import DEFAULT_POINTS_SCORING  # noqa: E402
from app.scoring.types import GameLog, Player, ScheduledGame  # noqa: E402

from nba_api.stats.endpoints import leaguegamelog  # noqa: E402

SCORING = DEFAULT_POINTS_SCORING
SEASONS_TO_TRY = [sys.argv[1]] if len(sys.argv) > 1 else ["2025-26", "2024-25", "2023-24"]


def parse_min(value: object) -> int:
    if value in (None, ""):
        return 0
    s = str(value).split(":")[0].strip()
    try:
        return int(float(s))
    except ValueError:
        return 0


def fetch_logs(season: str, date_from: str, date_to: str, retries: int = 3):
    """date_from/date_to are MM/DD/YYYY (nba_api format)."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            ep = leaguegamelog.LeagueGameLog(
                season=season,
                season_type_all_star="Regular Season",
                player_or_team_abbreviation="P",
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                timeout=60,
            )
            return ep.get_data_frames()[0]
        except Exception as e:  # noqa: BLE001 — network flakiness; retry
            last = e
            print(f"   (attempt {attempt + 1} failed: {type(e).__name__}; retrying...)")
            time.sleep(3 * (attempt + 1))
    raise last  # type: ignore[misc]


def split_matchup(team: str, matchup: str) -> tuple[str, str, str]:
    """Return (opponent, home_team, visitor_team) from e.g. 'OKC vs. LAL' / 'OKC @ LAL'."""
    sep = " vs. " if " vs. " in matchup else " @ "
    left, right = matchup.split(sep)
    opp = right.strip()
    if sep == " vs. ":
        return opp, team, opp          # team is home
    return opp, opp, team              # team is away


def main() -> int:
    bar = "=" * 72
    print(f"\n{bar}\n REAL-DATA VALIDATION via nba_api (stats.nba.com)\n{bar}")

    season = None
    df = None
    for s in SEASONS_TO_TRY:
        jan = int(s[:4]) + 1
        print(f"\n[DATA] trying season {s} — pulling box scores 01/05/{jan}..01/25/{jan} "
              f"from stats.nba.com...")
        try:
            df = fetch_logs(s, f"01/05/{jan}", f"01/25/{jan}")
        except Exception as e:  # noqa: BLE001
            print(f"[DATA] season {s} fetch failed after retries: {e}")
            continue
        if df is not None and len(df) > 0:
            season = s
            break
        print(f"[DATA] season {s} returned 0 rows; trying older season...")

    if df is None or season is None or len(df) == 0:
        print("\n[DATA] Could not retrieve data from stats.nba.com. It may be rate-limiting; "
              "re-run in a minute, or pass a season: validate_nba_api.py 2024-25")
        return 1

    jan = int(season[:4]) + 1
    stats_end = f"{jan}-01-18"
    week_start, week_end = f"{jan}-01-19", f"{jan}-01-25"
    rows = df.to_dict("records")
    print(f"[DATA] season {season}: {len(rows)} player game-log rows pulled.")

    players: dict[int, Player] = {}
    logs_by_player: dict[int, list[GameLog]] = {}
    all_logs: list[GameLog] = []
    schedule_map: dict[str, ScheduledGame] = {}

    for r in rows:
        date = str(r.get("GAME_DATE", ""))[:10]
        team = str(r.get("TEAM_ABBREVIATION", ""))
        matchup = str(r.get("MATCHUP", ""))
        pid = r.get("PLAYER_ID")
        gid = str(r.get("GAME_ID", ""))
        if not (team and matchup and pid and gid) or ("vs." not in matchup and "@" not in matchup):
            continue
        opp, home, visitor = split_matchup(team, matchup)

        # Schedule comes from the target-week rows.
        if week_start <= date <= week_end and gid not in schedule_map:
            schedule_map[gid] = ScheduledGame(gid, date, home, visitor)

        # Projection logs come from on/before the window end (and the player played).
        if date <= stats_end and parse_min(r.get("MIN")) > 0:
            line = {"pts": r.get("PTS") or 0, "reb": r.get("REB") or 0, "ast": r.get("AST") or 0,
                    "stl": r.get("STL") or 0, "blk": r.get("BLK") or 0, "fg3m": r.get("FG3M") or 0,
                    "turnover": r.get("TOV") or 0}
            log = GameLog(pid, gid, date, team, opp, "ALL", line)
            all_logs.append(log)
            logs_by_player.setdefault(pid, []).append(log)
            players[pid] = Player(pid, str(r.get("PLAYER_NAME", "")), team, ["ALL"])

    schedule = list(schedule_map.values())
    print(f"[DATA] usable logs (<= {stats_end})={len(all_logs)}  unique_players={len(players)}  "
          f"games in target week ({week_start}..{week_end})={len(schedule)}")
    if not all_logs or not schedule:
        print("\nWindow had no usable data; try another season: validate_nba_api.py 2024-25")
        return 2

    projections = project_all(logs_by_player, SCORING)
    dvp = compute_dvp(all_logs, SCORING)            # team-level (position is uniform)
    players_by_team: dict[str, list[Player]] = {}
    for p in players.values():
        players_by_team.setdefault(p.team_id, []).append(p)

    qualified = [pid for pid, pr in projections.items() if pr.games_sampled >= 3]
    by_fppg = sorted(qualified, key=lambda pid: projections[pid].fppg, reverse=True)

    # ---- CHECK 2: face validity --------------------------------------------
    print(f"\n[FACE] Top 15 by recency-weighted fppg ({len(qualified)} players, >=3 games) — "
          f"should be recognizable stars:")
    for pid in by_fppg[:15]:
        p, pr = players[pid], projections[pid]
        print(f"   {pr.fppg:6.1f} fppg  {p.name:<26} {p.team_id:>3}  ({pr.games_sampled} g)")

    # ---- CHECK 3a: schedule-density rerank ---------------------------------
    games_per_team: dict[str, int] = {}
    for g in schedule:
        games_per_team[g.home_team_id] = games_per_team.get(g.home_team_id, 0) + 1
        games_per_team[g.visitor_team_id] = games_per_team.get(g.visitor_team_id, 0) + 1
    dens = sorted(games_per_team.items(), key=lambda kv: -kv[1])
    print(f"\n[ENGINE] Real schedule this week — {len(games_per_team)} teams play; "
          f"{', '.join(f'{t}={n}' for t, n in dens[:8])}")

    pool = by_fppg[:80]
    weekly = {pid: project_value(players[pid], projections[pid], schedule, (week_start, week_end),
                                 dvp, {}, players_by_team) for pid in pool}
    by_weekly = sorted(pool, key=lambda pid: weekly[pid].value, reverse=True)
    fppg_rank = {pid: i for i, pid in enumerate(pool, 1)}
    print("\n[ENGINE] Top 12 by PROJECTED WEEKLY VALUE (fppg x games x matchup):")
    print("         value  games  Δrank  player")
    for wrank, pid in enumerate(by_weekly[:12], 1):
        vr = weekly[pid]
        delta = fppg_rank[pid] - wrank
        arrow = f"+{delta}" if delta > 0 else (str(delta) if delta < 0 else "·")
        print(f"   {vr.value:8.1f} {vr.n_games:5d}  {arrow:>5}  {players[pid].name} ({players[pid].team_id})")
    print("   (Δrank = positions moved vs raw-fppg order — schedule density + matchup at work)")

    # ---- CHECK 3b: rank_waiver_adds on a synthetic league ------------------
    roster_ids = by_fppg[45:55]
    roster = [players[pid] for pid in roster_ids]
    roster_set = set(roster_ids)
    fa_ids = [pid for pid in by_fppg[60:130]
              if pid not in roster_set and games_per_team.get(players[pid].team_id, 0) > 0][:30]
    free_agents = [players[pid] for pid in fa_ids]
    recs = rank_waiver_adds(roster, free_agents, set(), projections, schedule,
                            (week_start, week_end), dvp, {}, players_by_team)
    print(f"\n[ENGINE] rank_waiver_adds — synthetic mid-tier roster ({len(roster)}) vs "
          f"{len(free_agents)} waiver-caliber FAs — top 8 adds:")
    for i, r in enumerate(recs[:8], 1):
        print(f"   {i}. [{r.marginal:+6.1f}]  {r.rationale}")

    print(f"\n[OK] Real NBA box scores from stats.nba.com flowed through projections + team-DvP + "
          f"schedule + value-over-replacement. Engine validated on real data (season {season}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
