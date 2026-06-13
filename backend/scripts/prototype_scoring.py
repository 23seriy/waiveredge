"""WaiverEdge scoring prototype — ranked waiver action list over REAL NBA data.

Loads the real fixtures (materializing them from stats.nba.com on first run) and prints
the engine's ranked "do this now" waiver list for the default roster, with the reasoning.

    .venv/bin/python scripts/prototype_scoring.py

Refresh the underlying data with:  python scripts/dump_real_fixtures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.recommendations import load_fixtures  # noqa: E402
from app.scoring.engine import project_value, rank_waiver_adds  # noqa: E402
from app.scoring.matchups import compute_dvp  # noqa: E402
from app.scoring.projections import project_all  # noqa: E402
from app.scoring.types import GameLog, Injury, Player, ScheduledGame  # noqa: E402


def main() -> None:
    fx = load_fixtures()
    scoring = fx["roster"]["scoring"]
    window = (fx["roster"]["week_start"], fx["roster"]["week_end"])

    team_abbr = {t["id"]: t["abbreviation"] for t in fx["teams"]}
    players = {p["id"]: Player(p["id"], p["name"], p["team_id"], p["positions"])
               for p in fx["players"]}

    all_logs = [GameLog(**lg) for lg in fx["game_logs"]]
    logs_by_player: dict[int, list[GameLog]] = {}
    for lg in all_logs:
        logs_by_player.setdefault(lg.player_id, []).append(lg)

    schedule = [ScheduledGame(**g) for g in fx["schedule"]]
    injuries = {i["player_id"]: Injury(**i) for i in fx["injuries"]}

    players_by_team: dict[int, list[Player]] = {}
    for p in players.values():
        players_by_team.setdefault(p.team_id, []).append(p)

    projections = project_all(logs_by_player, scoring)
    dvp = compute_dvp(all_logs, scoring)

    roster = [players[r["player_id"]] for r in fx["roster"]["roster"]]
    free_agents = [players[pid] for pid in fx["roster"]["free_agents"]]
    droppable = set(fx["roster"]["droppable"])

    bar = "=" * 70
    print(f"\n{bar}\n WAIVEREDGE — weekly waiver action list  ({window[0]} -> {window[1]})\n{bar}")

    games_per_team: dict[int, int] = {}
    for g in schedule:
        games_per_team[g.home_team_id] = games_per_team.get(g.home_team_id, 0) + 1
        games_per_team[g.visitor_team_id] = games_per_team.get(g.visitor_team_id, 0) + 1
    top_dens = sorted(games_per_team.items(), key=lambda kv: -kv[1])[:8]
    print("\nSchedule density (games this week, busiest 8):")
    for tid, n in top_dens:
        print(f"   {team_abbr.get(tid, tid):>4}  {'#' * n} {n}")

    recs = rank_waiver_adds(roster, free_agents, droppable, projections, schedule,
                            window, dvp, injuries, players_by_team)

    print("\nTop 10 free-agent adds (value over replacement for the default roster):\n")
    for i, r in enumerate(recs[:10], 1):
        fppg = projections.get(r.add_player_id)
        base = f"{fppg.fppg:.1f} fppg" if fppg else "n/a"
        print(f" {i:2d}. [{r.marginal:+6.1f}]  {r.rationale}")
        print(f"          ({base} baseline; add {r.add_value:.1f} vs drop "
              f"{r.drop_name or '—'} {r.drop_value:.1f})")

    if recs:
        top = recs[0]
        add = players[top.add_player_id]
        vr = project_value(add, projections[add.id], schedule, window, dvp, injuries,
                           players_by_team)
        print(f"\nWhy #1 ({add.name}) — per-game breakdown:")
        print(f"   baseline {projections[add.id].fppg:.1f} fppg x role {vr.role_mult:.2f} "
              f"x availability {vr.avail_prob:.2f}")
        for c in vr.contributions:
            soft = " (soft)" if dvp.is_soft(c.opponent_id, add.primary) else ""
            print(f"     vs {team_abbr.get(c.opponent_id, c.opponent_id):>4}  "
                  f"matchup x{c.matchup_mult:.2f}{soft}  -> {c.points:.1f} fpts")
        print(f"   weekly total: {vr.value:.1f} fpts\n")


if __name__ == "__main__":
    main()
