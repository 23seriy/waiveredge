"""9-category (z-score) ranking — the category-mode counterpart to engine.py.

Where points mode reduces a player to one weighted number, category mode keeps a
per-category vector and ranks by the sum of z-scores over the league's active
categories. Schedule density and the existing multipliers carry through exactly as
in points mode: a player's weekly category totals are
``per_game_stat × (Σ matchup_mult over games this week) × role_mult × avail``,
so a 4-game player still out-values an equal 2-game player.

Percentages (FG%/FT%) use volume-weighted impact — you can't average a percentage,
so a category's value is ``weekly_attempts × (player_pct − league_pct)``. Turnovers
are negated (fewer is better). z-scores are taken against a stable reference pool so
the baseline doesn't swing with a small free-agent set.

Pure stdlib.
"""
from __future__ import annotations

from statistics import mean, pstdev

from .engine import availability_prob, games_in_window, role_multiplier
from .matchups import DvPTable
from .scoring_systems import CATEGORY_LABEL, CATEGORY_META
from .types import (
    CategoryValueResult,
    Injury,
    Player,
    Projection,
    Recommendation,
    ScheduledGame,
)

# Players need at least this many sampled games to enter the z-score reference pool.
MIN_REF_GAMES = 3
# A weak-category add must clear this z in a category to be called "helpful" there.
HELP_Z_THRESHOLD = 0.25


def _weekly(
    player: Player,
    projection: Projection,
    schedule: list[ScheduledGame],
    window: tuple[str, str],
    dvp: DvPTable,
    injuries: dict[int, Injury],
    players_by_team: dict[int, list[Player]],
) -> tuple[int, int, float, str, float, dict[str, float]]:
    """Projected weekly per-stat totals + the schedule/role/availability context."""
    games = games_in_window(player.team_id, schedule, window[0], window[1])
    role_mult, role_note = role_multiplier(player, injuries, players_by_team)
    avail = availability_prob(player.id, injuries)
    soft = 0
    mm_sum = 0.0
    for g in games:
        opp = g.opponent_of(player.team_id)
        if dvp.is_soft(opp, player.primary):
            soft += 1
        mm_sum += dvp.multiplier(opp, player.primary)
    eff = role_mult * avail * mm_sum  # effective games = Σ(matchup) × role × avail
    weekly = {s: v * eff for s, v in projection.per_game.items()}
    return len(games), soft, role_mult, role_note, avail, weekly


def _cat_raw(weekly: dict[str, float], cat: str, league_pct: dict[str, float]) -> float:
    """Raw category value: counting total, volume-weighted impact for percentages,
    or computed ratio for rate stats (ERA, WHIP)."""
    meta = CATEGORY_META[cat]
    if meta.get("percentage"):
        att = weekly.get(meta["att"], 0.0)
        made = weekly.get(meta["made"], 0.0)
        if att <= 0:
            return 0.0
        return att * (made / att - league_pct.get(cat, 0.0))
    if meta.get("rate"):
        den = weekly.get(meta["den"], 0.0)
        if den <= 0:
            return 0.0
        num = sum(weekly.get(s, 0.0) for s in meta["num"])
        return (num / den) * meta.get("scale", 1.0)
    return weekly.get(meta["stat"], 0.0)


class Reference:
    """Per-category mean/std and league percentages used to z-score candidates."""

    def __init__(self, weeklies: list[dict[str, float]], active_cats: list[str]):
        self.league_pct: dict[str, float] = {}
        for cat in active_cats:
            meta = CATEGORY_META[cat]
            if meta.get("percentage"):
                tot_att = sum(w.get(meta["att"], 0.0) for w in weeklies)
                tot_made = sum(w.get(meta["made"], 0.0) for w in weeklies)
                self.league_pct[cat] = (tot_made / tot_att) if tot_att > 0 else 0.0

        self.mean: dict[str, float] = {}
        self.std: dict[str, float] = {}
        for cat in active_cats:
            raws = [_cat_raw(w, cat, self.league_pct) for w in weeklies]
            self.mean[cat] = mean(raws) if raws else 0.0
            self.std[cat] = pstdev(raws) if len(raws) > 1 else 0.0

    def z(self, weekly: dict[str, float], cat: str) -> float:
        std = self.std.get(cat, 0.0)
        if std <= 0:
            return 0.0
        z = (_cat_raw(weekly, cat, self.league_pct) - self.mean[cat]) / std
        return -z if CATEGORY_META[cat].get("negative") else z


def category_value(weekly: dict[str, float], active_cats: list[str],
                   ref: Reference) -> tuple[dict[str, float], float]:
    per_cat_z = {cat: round(ref.z(weekly, cat), 3) for cat in active_cats}
    return per_cat_z, round(sum(per_cat_z.values()), 3)


def _cat_rationale(add: Player, fav: CategoryValueResult, drop_name: str | None,
                   marginal: float, helps: list[str]) -> str:
    parts = [f"{fav.n_games} game{'s' if fav.n_games != 1 else ''} this week"]
    if helps:
        parts.append("helps your weak cats: " + ", ".join(CATEGORY_LABEL[c] for c in helps))
    if fav.role_mult > 1.0 and fav.role_note:
        parts.append(fav.role_note)
    if fav.avail_prob < 1.0:
        parts.append(f"availability {int(fav.avail_prob * 100)}%")
    top = [(c, z) for c, z in sorted(fav.per_cat_z.items(), key=lambda kv: kv[1], reverse=True)[:2] if z > 0]
    top_str = ", ".join(f"{CATEGORY_LABEL[c]} +{z:.1f}z" for c, z in top)
    head = f"{add.name} ({'/'.join(add.positions)}) — " + ", ".join(parts) + "."
    tail = f" {fav.total_z:+.1f}z this week"
    if top_str:
        tail += f" ({top_str})"
    if drop_name:
        tail += f"; +{marginal:.1f}z over {drop_name}"
    return head + tail + "."


def rank_category_adds(
    roster: list[Player],
    free_agents: list[Player],
    droppable_ids: set[int],
    projections: dict[int, Projection],
    schedule: list[ScheduledGame],
    window: tuple[str, str],
    dvp: DvPTable,
    injuries: dict[int, Injury],
    players_by_team: dict[int, list[Player]],
    categories: list[str],
    reference_players: list[Player] | None = None,
) -> list[Recommendation]:
    """Rank free agents by 9-cat value-over-replacement for this roster."""
    active = [c for c in categories if c in CATEGORY_META]

    # Build the z-score reference distribution from a stable pool.
    ref_pool = reference_players if reference_players is not None else (roster + free_agents)
    ref_weeklies: list[dict[str, float]] = []
    for p in ref_pool:
        proj = projections.get(p.id)
        if not proj or proj.games_sampled < MIN_REF_GAMES or not proj.per_game:
            continue
        *_, weekly = _weekly(p, proj, schedule, window, dvp, injuries, players_by_team)
        ref_weeklies.append(weekly)
    ref = Reference(ref_weeklies, active)

    def value_of(p: Player) -> CategoryValueResult:
        proj = projections.get(p.id) or Projection(p.id, 0.0, 0, {})
        n, soft, role_mult, role_note, avail, weekly = _weekly(
            p, proj, schedule, window, dvp, injuries, players_by_team)
        per_cat_z, total = category_value(weekly, active, ref)
        return CategoryValueResult(p.id, n, soft, role_mult, role_note, avail,
                                   weekly, per_cat_z, total)

    roster_vals = {p.id: value_of(p) for p in roster}

    # Roster's weakest categories = lowest aggregate z across rostered players.
    agg = {c: 0.0 for c in active}
    for v in roster_vals.values():
        for c in active:
            agg[c] += v.per_cat_z.get(c, 0.0)
    weak = sorted(active, key=lambda c: agg[c])[:3]

    recs: list[Recommendation] = []
    for fa in free_agents:
        fav = value_of(fa)
        candidates = [
            p for p in roster
            if (not droppable_ids or p.id in droppable_ids)
            and any(pos in fa.positions for pos in p.positions)
        ]
        drop = min(candidates, key=lambda p: roster_vals[p.id].total_z, default=None)
        drop_z = roster_vals[drop.id].total_z if drop else 0.0
        marginal = round(fav.total_z - drop_z, 3)
        helps = [c for c in weak if fav.per_cat_z.get(c, 0.0) > HELP_Z_THRESHOLD]
        recs.append(Recommendation(
            add_player_id=fa.id, add_name=fa.name, add_position="/".join(fa.positions),
            add_value=fav.total_z,
            drop_player_id=drop.id if drop else None,
            drop_name=drop.name if drop else None,
            drop_value=round(drop_z, 3),
            slot=next((pos for pos in fa.positions), "UTIL"),
            n_games=fav.n_games, soft_matchups=fav.soft_matchups,
            marginal=marginal,
            rationale=_cat_rationale(fa, fav, drop.name if drop else None, marginal, helps),
            total_z=fav.total_z, per_cat_z=fav.per_cat_z, helps=helps,
        ))
    recs.sort(key=lambda r: r.marginal, reverse=True)
    return recs
