"""Exhaustive solitaire simulator.

For each game (one random shuffle) we branch over:

  * mulligan keeps — all ways to bottom `Y` of the opening 7 cards, and
  * every line of play — each legal ordering of lands/spells each turn,

exploring depth-first until the latest property trigger moment is reached. A
game is a **success** if some single line satisfies *all* properties at their
respective trigger moments. We also record, per game, which properties were
satisfiable in *any* line (for per-property statistics).

Mana is solved deterministically (see `actions.plan_payment`) so it is not a
branch point. Search is bounded by a per-game wall-clock timeout and a node cap.
"""
from __future__ import annotations

import itertools
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .actions import PassPhase, combat_actions, deal_combat_damage, legal_actions
from .game_state import GameState, new_game_from_deck
from .phases import MAIN_PHASES, TURN_ORDER, Phase, phase_index


class CompiledProperty(Protocol):
    """What the simulator needs from a property (see `properties` package)."""

    id: str
    description: str
    timing: str  # "before" | "at"
    phase: Phase
    turn: int

    def evaluate(self, state: GameState) -> bool: ...


@dataclass
class SimulationConfig:
    num_games: int = 100
    timeout_per_game_s: float = 5.0
    mulligans: int = 0
    on_the_play: bool = True
    max_nodes_per_game: int = 200_000
    base_seed: int = 12345
    keep_success_logs: int = 25  # how many successful game logs to retain


@dataclass
class GameOutcome:
    game_index: int
    success: bool
    satisfied: set[str] = field(default_factory=set)  # props hit in any line
    timed_out: bool = False
    node_capped: bool = False
    sample_log: list[str] = field(default_factory=list)


@dataclass
class SimulationStats:
    total_games: int = 0
    games_run: int = 0
    successes: int = 0
    timeouts: int = 0
    per_property: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "total_games": self.total_games,
            "games_run": self.games_run,
            "successes": self.successes,
            "timeouts": self.timeouts,
            "success_rate": (self.successes / self.games_run) if self.games_run else 0.0,
            "per_property": dict(self.per_property),
        }


class _SearchContext:
    def __init__(
        self,
        properties: list[CompiledProperty],
        deadline: float,
        max_nodes: int,
    ) -> None:
        self.properties = properties
        self.deadline = deadline
        self.max_nodes = max_nodes
        self.nodes = 0
        self.timed_out = False
        self.node_capped = False
        self.ever_satisfied: set[str] = set()  # any line, this game
        self.success_log: list[str] | None = None
        self.max_rank = max(
            ((p.turn, phase_index(p.phase)) for p in properties), default=(0, 0)
        )

    def budget_exceeded(self) -> bool:
        if self.node_capped or self.timed_out:
            return True
        self.nodes += 1
        if self.nodes > self.max_nodes:
            self.node_capped = True
            return True
        if time.monotonic() > self.deadline:
            self.timed_out = True
            return True
        return False


# --------------------------------------------------------------------------
# Turn progression
# --------------------------------------------------------------------------
def _apply_step_entry(state: GameState) -> None:
    if state.phase == Phase.UNTAP:
        state.turn += 1
        state.reset_turn_counters()
        for perm in state.battlefield:
            perm.tapped = False
            perm.summoning_sick = False
        state.mana_pool.clear()
    elif state.phase == Phase.DRAW:
        skip = state.turn == 1 and state.on_the_play
        if not skip and state.library:
            state.draw(1)
            state.emit(f"draw ({len(state.hand)} in hand)")
    elif state.phase == Phase.COMBAT_DAMAGE:
        if state.attackers:
            deal_combat_damage(state)
    elif state.phase == Phase.END_COMBAT:
        state.attackers.clear()
    elif state.phase == Phase.CLEANUP:
        for perm in state.battlefield:
            perm.temp_power = 0
            perm.temp_toughness = 0
            perm.damage = 0
        state.check_deaths()

    # "At the beginning of <phase>" triggers (upkeep, combat, end step...).
    for perm in list(state.battlefield):
        perm.impl.on_phase(state, perm, state.phase)
    state.check_deaths()


def _goto_next_phase(state: GameState) -> None:
    state.mana_pool.clear()
    idx = phase_index(state.phase)
    if idx + 1 < len(TURN_ORDER):
        state.phase = TURN_ORDER[idx + 1]
    else:
        state.phase = Phase.UNTAP  # next turn; turn counter bumps on untap entry


# --------------------------------------------------------------------------
# Property checking
# --------------------------------------------------------------------------
def _check_due(
    state: GameState, ctx: _SearchContext, timing: str, satisfied: frozenset[str]
) -> frozenset[str]:
    """Evaluate properties due now; return the (possibly grown) satisfied set."""
    rank = (state.turn, phase_index(state.phase))
    for prop in ctx.properties:
        if (prop.turn, phase_index(prop.phase)) != rank or prop.timing != timing:
            continue
        if prop.id in satisfied:
            continue
        try:
            ok = bool(prop.evaluate(state))
        except Exception:
            ok = False
        if ok:
            ctx.ever_satisfied.add(prop.id)
            satisfied = satisfied | {prop.id}
    return satisfied


def _all_satisfied(ctx: _SearchContext, satisfied: frozenset[str]) -> bool:
    return len(satisfied) == len(ctx.properties) and len(ctx.properties) > 0


# --------------------------------------------------------------------------
# Depth-first search over a single opening hand
# --------------------------------------------------------------------------
def _run_from_phase(state: GameState, ctx: _SearchContext, satisfied: frozenset[str]) -> bool:
    if ctx.budget_exceeded():
        return False
    if (state.turn, phase_index(state.phase)) > ctx.max_rank:
        return False

    _apply_step_entry(state)

    satisfied = _check_due(state, ctx, "before", satisfied)
    if _all_satisfied(ctx, satisfied):
        ctx.success_log = list(state.log)
        return True

    if state.phase in MAIN_PHASES:
        return _decision_point(state, ctx, satisfied, legal_actions)

    satisfied = _check_due(state, ctx, "at", satisfied)
    if _all_satisfied(ctx, satisfied):
        ctx.success_log = list(state.log)
        return True

    if state.phase == Phase.DECLARE_ATTACKERS:
        options = combat_actions(state)
        if options:
            return _decision_point(state, ctx, satisfied, lambda s: combat_actions(s), once=True)

    _goto_next_phase(state)
    return _run_from_phase(state, ctx, satisfied)


def _decision_point(
    state: GameState, ctx: _SearchContext, satisfied: frozenset[str],
    enumerate_actions, once: bool = False,
) -> bool:
    """Branch over the legal actions at this point. `once=True` means each
    option immediately advances to the next phase (e.g. declare attackers);
    otherwise the player keeps priority in the phase until passing."""
    if ctx.budget_exceeded():
        return False

    satisfied = _check_due(state, ctx, "at", satisfied)
    if _all_satisfied(ctx, satisfied):
        ctx.success_log = list(state.log)
        return True

    for action in enumerate_actions(state):
        child = state.clone()
        try:
            branches = action.apply(child)
        except Exception:
            continue  # a card action that turned out to be illegal mid-apply
        for branch in (branches if branches is not None else [child]):
            branch.check_deaths()
            if isinstance(action, PassPhase) or once:
                _goto_next_phase(branch)
                if _run_from_phase(branch, ctx, satisfied):
                    return True
            else:
                if _decision_point(branch, ctx, satisfied, enumerate_actions):
                    return True
            if ctx.timed_out or ctx.node_capped:
                return False
    return False


# --------------------------------------------------------------------------
# Mulligans + per-game driver
# --------------------------------------------------------------------------
def _opening_hands(
    library: list, hand_size: int, mulligans: int
) -> list[tuple[list, list, list]]:
    """Yield (hand, library, bottomed) variants after drawing `hand_size` and
    bottoming `mulligans` cards. All ways of choosing which cards to bottom are
    returned."""
    drawn = library[:hand_size]
    rest = library[hand_size:]
    y = max(0, min(mulligans, hand_size))
    if y == 0:
        return [(list(drawn), list(rest), [])]
    variants: list[tuple[list, list, list]] = []
    for bottom_idx in itertools.combinations(range(hand_size), y):
        bottom = [drawn[i] for i in bottom_idx]
        keep = [drawn[i] for i in range(hand_size) if i not in bottom_idx]
        variants.append((keep, rest + bottom, bottom))
    return variants


def simulate_game(
    base_state: GameState,
    properties: list[CompiledProperty],
    config: SimulationConfig,
    game_index: int,
) -> GameOutcome:
    rng = random.Random(config.base_seed + game_index)
    shuffled = list(base_state.library)
    rng.shuffle(shuffled)

    hand_size = 7
    deadline = time.monotonic() + config.timeout_per_game_s
    ctx = _SearchContext(properties, deadline, config.max_nodes_per_game)

    success = False
    for hand, library, bottomed in _opening_hands(shuffled, hand_size, config.mulligans):
        variant = base_state.clone()
        variant.library = list(library)
        variant.hand = list(hand)
        variant.turn = 0
        variant.phase = Phase.UNTAP
        variant.rng_seed = config.base_seed + game_index  # mid-game shuffles
        play_draw = "on the play" if variant.on_the_play else "on the draw"
        if bottomed:
            variant.emit(
                f"mulligan {config.mulligans} ({play_draw}) — keep "
                f"{[c.name for c in hand]}, bottom {[c.name for c in bottomed]}"
            )
        else:
            variant.emit(f"opening hand ({play_draw}): {[c.name for c in hand]}")
        if _run_from_phase(variant, ctx, frozenset()):
            success = True
            break
        if ctx.timed_out or ctx.node_capped:
            break

    return GameOutcome(
        game_index=game_index,
        success=success,
        satisfied=set(ctx.ever_satisfied),
        timed_out=ctx.timed_out,
        node_capped=ctx.node_capped,
        sample_log=ctx.success_log or [],
    )


def run_simulation(
    deck,
    properties: list[CompiledProperty],
    config: SimulationConfig,
    on_game: Callable[[GameOutcome, SimulationStats], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> SimulationStats:
    """Run `config.num_games` games, invoking `on_game` after each for live
    reporting. `should_stop` allows cooperative cancellation."""
    base_state = new_game_from_deck(deck, on_the_play=config.on_the_play)
    stats = SimulationStats(total_games=config.num_games)
    stats.per_property = {p.id: 0 for p in properties}

    for i in range(config.num_games):
        if should_stop and should_stop():
            break
        outcome = simulate_game(base_state, properties, config, i)
        stats.games_run += 1
        if outcome.success:
            stats.successes += 1
        if outcome.timed_out:
            stats.timeouts += 1
        for pid in outcome.satisfied:
            stats.per_property[pid] = stats.per_property.get(pid, 0) + 1
        if on_game:
            on_game(outcome, stats)

    return stats
