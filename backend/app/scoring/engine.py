"""The recommendation engine — the core IP.

Fuses four signals into a single, explainable number per candidate:

    weekly_value = sum over games in the window of:
        fppg  x  role_mult  x  matchup_mult  x  avail_prob

then ranks waiver/free-agent adds by VALUE OVER REPLACEMENT for *this* roster:

    marginal = weekly_value(candidate) - weekly_value(weakest droppable rostered
               player who shares a position with the candidate)

That last step is the whole product: a generic "best available" list ignores your
roster; this answers "what should I do with MY team right now."
"""
from __future__ import annotations

from .matchups import DvPTable
from .types import (
    GameContribution,
    Injury,
    Player,
    Projection,
    Recommendation,
    ScheduledGame,
    ValueResult,
)

# How an injury designation maps to the probability the player suits up for a game.
AVAILABILITY = {
    "out": 0.0,
    "doubtful": 0.25,
    "questionable": 0.5,
    "game-time decision": 0.6,
    "gtd": 0.6,
    "day-to-day": 0.75,
}
# When a same-position teammate is ruled OUT, a backup's minutes/usage rise.
ROLE_BUMP = 1.15


def availability_prob(player_id: int, injuries: dict[int, Injury]) -> float:
    inj = injuries.get(player_id)
    if inj is None:
        return 1.0
    return AVAILABILITY.get(inj.status.strip().lower(), 1.0)


def role_multiplier(
    player: Player,
    injuries: dict[int, Injury],
    players_by_team: dict[int, list[Player]],
) -> tuple[float, str]:
    """Bump a player's value if a same-position teammate is ruled Out.

    Heuristic but transparent — the note is surfaced in the recommendation so the
    user sees exactly why the player's role is elevated.
    """
    teammates = players_by_team.get(player.team_id, [])
    for tm in teammates:
        if tm.id == player.id:
            continue
        inj = injuries.get(tm.id)
        if inj and inj.status.strip().lower() == "out" and tm.primary == player.primary:
            return ROLE_BUMP, f"elevated role — {tm.name} ({tm.primary}) out"
    return 1.0, ""


def games_in_window(
    team_id: int,
    schedule: list[ScheduledGame],
    start_date: str,
    end_date: str,
) -> list[ScheduledGame]:
    return sorted(
        (g for g in schedule if g.involves(team_id) and start_date <= g.date <= end_date),
        key=lambda g: g.date,
    )


def project_value(
    player: Player,
    projection: Projection,
    schedule: list[ScheduledGame],
    window: tuple[str, str],
    dvp: DvPTable,
    injuries: dict[int, Injury],
    players_by_team: dict[int, list[Player]],
) -> ValueResult:
    start, end = window
    games = games_in_window(player.team_id, schedule, start, end)
    role_mult, role_note = role_multiplier(player, injuries, players_by_team)
    avail = availability_prob(player.id, injuries)

    contributions: list[GameContribution] = []
    soft = 0
    total = 0.0
    for g in games:
        opp = g.opponent_of(player.team_id)
        mm = dvp.multiplier(opp, player.primary)
        if dvp.is_soft(opp, player.primary):
            soft += 1
        pts = projection.fppg * role_mult * mm * avail
        total += pts
        contributions.append(
            GameContribution(game_id=g.id, opponent_id=opp, matchup_mult=mm,
                             avail_prob=avail, points=round(pts, 2))
        )

    return ValueResult(
        player_id=player.id,
        value=round(total, 2),
        n_games=len(games),
        soft_matchups=soft,
        role_mult=role_mult,
        role_note=role_note,
        avail_prob=avail,
        contributions=contributions,
    )


def _rationale(add: Player, vr: ValueResult, drop_name: str | None, marginal: float) -> str:
    parts = [f"{vr.n_games} game{'s' if vr.n_games != 1 else ''} this week"]
    if vr.soft_matchups:
        parts.append(f"{vr.soft_matchups} vs soft matchup{'s' if vr.soft_matchups != 1 else ''}")
    if vr.role_mult > 1.0 and vr.role_note:
        parts.append(vr.role_note)
    if vr.avail_prob < 1.0:
        parts.append(f"availability {int(vr.avail_prob * 100)}%")
    head = f"{add.name} ({'/'.join(add.positions)}) — " + ", ".join(parts) + "."
    tail = f" Projected {vr.value:.1f} fpts"
    if drop_name:
        tail += f" (+{marginal:.1f} over {drop_name})"
    return head + tail + "."


def rank_waiver_adds(
    roster: list[Player],
    free_agents: list[Player],
    droppable_ids: set[int],
    projections: dict[int, Projection],
    schedule: list[ScheduledGame],
    window: tuple[str, str],
    dvp: DvPTable,
    injuries: dict[int, Injury],
    players_by_team: dict[int, list[Player]],
) -> list[Recommendation]:
    """Rank free agents by value-over-replacement for this roster."""

    def value_of(p: Player) -> ValueResult:
        proj = projections.get(p.id, Projection(p.id, 0.0, 0))
        return project_value(p, proj, schedule, window, dvp, injuries, players_by_team)

    roster_values = {p.id: value_of(p) for p in roster}

    recs: list[Recommendation] = []
    for fa in free_agents:
        fa_vr = value_of(fa)
        fa_proj = projections.get(fa.id)

        # Weakest droppable rostered player who shares a position with this FA.
        candidates = [
            p for p in roster
            if (not droppable_ids or p.id in droppable_ids)
            and any(pos in fa.positions for pos in p.positions)
        ]
        drop = min(candidates, key=lambda p: roster_values[p.id].value, default=None)
        drop_value = roster_values[drop.id].value if drop else 0.0
        drop_proj = projections.get(drop.id) if drop else None
        marginal = round(fa_vr.value - drop_value, 2)
        slot = next((pos for pos in fa.positions), "UTIL")

        recs.append(
            Recommendation(
                add_player_id=fa.id,
                add_name=fa.name,
                add_position="/".join(fa.positions),
                add_value=fa_vr.value,
                drop_player_id=drop.id if drop else None,
                drop_name=drop.name if drop else None,
                drop_value=round(drop_value, 2),
                slot=slot,
                n_games=fa_vr.n_games,
                soft_matchups=fa_vr.soft_matchups,
                marginal=marginal,
                rationale=_rationale(fa, fa_vr, drop.name if drop else None, marginal),
                add_fppg=round(fa_proj.fppg, 1) if fa_proj else 0.0,
                drop_fppg=round(drop_proj.fppg, 1) if drop_proj else 0.0,
            )
        )

    recs.sort(key=lambda r: r.marginal, reverse=True)
    return recs
