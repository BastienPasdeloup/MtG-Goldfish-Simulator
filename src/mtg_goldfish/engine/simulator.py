"""Exhaustive solitaire simulator.

For each game (one random shuffle) we branch over:

  * mulligan keeps — all ways to bottom `Y` of the opening 7 cards, and
  * every line of play — each legal ordering of lands/spells each turn,

exploring until the latest property trigger moment is reached. A game is a
**success** if some single line satisfies *all* properties at their respective
trigger moments. We also record, per game, which properties were satisfiable
in *any* line (for per-property statistics).

The search order is configurable (`SimulationConfig.search_mode`) — DFS with
or without heuristic move ordering, BFS, or greedy best-first on a progress
score. Every mode visits the same states (the search stays exhaustive until
success, timeout or the node cap); only the visit order differs.

Mana is solved deterministically (see `actions.plan_payment`) so it is not a
branch point. Search is bounded by a per-game wall-clock timeout and a node cap.
"""
from __future__ import annotations

import heapq
import itertools
import random
import time
from collections import deque
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


#: Available search strategies (value -> user-facing label). All are
#: exhaustive; they differ only in the order states are visited.
SEARCH_MODES: dict[str, str] = {
    "dfs_heuristic": "DFS · heuristic move ordering (default)",
    "dfs": "DFS · natural move order",
    "bfs": "BFS · breadth-first (shallowest lines first)",
    "best_first": "Best-first · greedy on board progress",
}


@dataclass
class SimulationConfig:
    num_games: int = 100
    timeout_per_game_s: float = 5.0
    mulligans: int = 0
    on_the_play: bool = True
    max_nodes_per_game: int = 200_000
    base_seed: int = 12345
    keep_success_logs: int = 25  # how many successful game logs to retain
    search_mode: str = "dfs_heuristic"  # see SEARCH_MODES


@dataclass
class GameOutcome:
    game_index: int
    success: bool
    satisfied: set[str] = field(default_factory=set)  # props hit in any line
    timed_out: bool = False
    node_capped: bool = False
    sample_log: list[str] = field(default_factory=list)
    # Per-game search shape (populated for the runs table + tree view).
    opening_hand: list[str] = field(default_factory=list)  # the kept (winning) hand
    branches_explored: int = 0
    branches_considered: int = 0
    tree: dict | None = None
    tree_truncated: bool = False


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
        tree_cap: int | None = None,  # None = record the FULL explored tree
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
        # Search-shape bookkeeping (for the per-run table + tree view).
        self.branches_explored = 0     # states actually processed by the search
        self.branches_considered = 0   # candidate branches created / enumerated
        self.tree_cap = tree_cap
        self.tree_count = 0            # nodes recorded so far (bounded by tree_cap)
        self.tree_truncated = False
        self.tree_root: dict | None = None

    def new_tree_node(
        self, parent: dict | None, label: str, state: GameState,
        satisfied: frozenset[str] = frozenset(),
    ) -> dict | None:
        """Attach a child node to `parent` for a newly created state. Returns
        the new node, or None once the recording cap is hit. Nodes carry a
        transient "_p" parent reference (stripped before the tree is returned)
        so the winning line can be marked bottom-up, and "sat" — the property
        ids verified on this line so far (refreshed at the node's own
        checkpoint) — for the per-property status circles in the tree view."""
        if self.tree_cap is not None and self.tree_count >= self.tree_cap:
            self.tree_truncated = True
            return None
        node = {
            "id": self.tree_count,
            "label": label,
            "turn": state.turn,
            "phase": state.phase.value,
            "children": [],
            "success": False,
            "sat": sorted(satisfied),
            "_p": parent,
        }
        self.tree_count += 1
        if parent is not None:
            parent["children"].append(node)
        return node

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
    state.queue_phase_triggers(state.phase)
    state.settle_nonbranching(f"{state.phase.value} triggers")


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
    state: GameState, ctx: _SearchContext, satisfied: frozenset[str]
) -> frozenset[str]:
    """Evaluate properties due at this checkpoint; return the (possibly grown)
    satisfied set. Timing semantics:

      * "at <phase> of turn N"     — checked when the game is exactly there;
      * "before <phase> of turn N" — checked at EVERY checkpoint strictly
        before that moment (any earlier phase, any earlier turn).

    Satisfaction is sticky along a line: once a property holds at one of its
    checkpoints it stays satisfied, so the search stops as soon as every
    property has been verified somewhere on the line."""
    rank = (state.turn, phase_index(state.phase))
    for prop in ctx.properties:
        if prop.id in satisfied:
            continue
        target = (prop.turn, phase_index(prop.phase))
        due = rank < target if prop.timing == "before" else rank == target
        if not due:
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


def _viable(state: GameState, ctx: _SearchContext, satisfied: frozenset[str]) -> bool:
    """Pruning: a line is only worth exploring while EVERY unsatisfied property
    can still be verified later on it. Once an "at" moment is past (or a
    "before" deadline reached) with the property unsatisfied, no descendant of
    this state can make the game a success — the branch is dropped."""
    rank = (state.turn, phase_index(state.phase))
    for prop in ctx.properties:
        if prop.id in satisfied:
            continue
        target = (prop.turn, phase_index(prop.phase))
        dead = rank >= target if prop.timing == "before" else rank > target
        if dead:
            return False
    return True


# --------------------------------------------------------------------------
# Strategy-driven search over a single game
# --------------------------------------------------------------------------
def _action_priority(action) -> int:
    """Rough goodness of an action, used to order (NOT prune) the search:
    lands and the commander develop the board fastest, then tutors/fetches,
    then other spells, then activated abilities; passing is always tried last.
    The sort is stable, so equal-priority actions keep their natural order."""
    label = getattr(action, "label", "")
    if isinstance(action, PassPhase):
        return 0
    if label.startswith("play land"):
        return 100
    if label.startswith("cast commander"):
        return 90
    if "fetch" in label or "search" in label or "tutor" in label:
        return 80
    if label.startswith("cast "):
        return 70
    return 60  # activated abilities, attacks, everything else


def _progress_score(state: GameState, satisfied: frozenset[str]) -> int:
    """Score for best-first search: lower = more promising. Rewards satisfied
    properties first, then board development and cards seen."""
    return -(
        len(satisfied) * 1_000_000
        + len(state.battlefield) * 1_000
        + state.cards_drawn * 10
        + state.turn
    )


def _advance(state: GameState, ctx: _SearchContext, satisfied: frozenset[str]):
    """Advance the state deterministically (no choices) until a decision point,
    a success, or the search horizon. Mutates `state`. Returns
    (status, satisfied) with status in {"success", "dead", "unviable",
    "decision", "combat"} — "unviable" means a property can no longer be
    verified on this line ("dead" is a budget cut)."""
    while True:
        if ctx.budget_exceeded():
            return "dead", satisfied
        if (state.turn, phase_index(state.phase)) > ctx.max_rank:
            return "unviable", satisfied  # past every remaining trigger moment

        _apply_step_entry(state)

        # One checkpoint per phase entry: evaluates "at" properties due right
        # here and "before" properties whose moment has not been reached yet.
        satisfied = _check_due(state, ctx, satisfied)
        if _all_satisfied(ctx, satisfied):
            return "success", satisfied
        if not _viable(state, ctx, satisfied):
            return "unviable", satisfied  # some property can no longer be verified

        if state.phase in MAIN_PHASES:
            return "decision", satisfied

        if state.phase == Phase.DECLARE_ATTACKERS and combat_actions(state):
            return "combat", satisfied

        _goto_next_phase(state)


def _mark_success(node: dict | None) -> None:
    """Mark the winning line bottom-up via the transient parent references."""
    while node is not None:
        node["success"] = True
        node = node.get("_p")


def _finish_success(
    state: GameState, ctx: _SearchContext, satisfied: frozenset[str], node: dict | None
) -> None:
    """Wrap up a successful line: emit a final frame showing the state at the
    moment every property is verified (so the replay ends on the final state),
    attach a terminal tree node for it, and mark the winning line."""
    state.emit(f"✓ all properties satisfied — {state.phase.value} of turn {state.turn}")
    final = ctx.new_tree_node(node, "✓ all properties satisfied", state, satisfied)
    _mark_success(final or node)
    ctx.success_log = list(state.log)


def _strip_parents(node: dict) -> None:
    # Iterative: the full (uncapped) tree can be thousands of levels deep.
    stack = [node]
    while stack:
        n = stack.pop()
        n.pop("_p", None)
        stack.extend(n["children"])


#: Frontier safety valve: BFS/best-first keep many live states in memory, so
#: cap the frontier (each entry holds a full GameState clone).
_MAX_FRONTIER = 150_000


def _search(items: list[tuple], ctx: _SearchContext, mode: str) -> bool:
    """Search over game states. `items` are (state, satisfied, node, kind, own)
    seeds, where kind is "advance" (state must first be advanced through
    non-choice phases), "decision" (main phase, player holds priority) or
    "combat" (declare attackers, each option ends the decision); `own` says
    whether `node` was created for this very state (vs. a truncation fallback).

    Every branch state created by an action gets its own tree node — including
    passing priority — so the recorded tree shows ALL states created during
    the search. All modes are exhaustive; they differ only in visit order."""
    heuristic = mode in ("dfs_heuristic", "best_first")

    if mode == "bfs":
        frontier: deque = deque(items)
        pop = frontier.popleft
        push = frontier.append
    elif mode == "best_first":
        seq = itertools.count()  # tie-breaker: insertion order
        frontier_h: list[tuple] = []
        for it in items:
            heapq.heappush(frontier_h, (_progress_score(it[0], it[1]), next(seq), it))
        frontier = frontier_h
        pop = lambda: heapq.heappop(frontier)[2]  # noqa: E731
        push = lambda it: heapq.heappush(frontier, (_progress_score(it[0], it[1]), next(seq), it))  # noqa: E731
    else:  # dfs / dfs_heuristic: children are pushed reversed so the
        frontier = list(reversed(items))  # highest-priority branch pops first
        pop = frontier.pop
        push = frontier.append

    while frontier:
        if ctx.timed_out or ctx.node_capped:
            return False
        if len(frontier) > _MAX_FRONTIER:
            ctx.node_capped = True
            return False
        state, satisfied, node, kind, own = pop()
        if ctx.budget_exceeded():
            return False
        ctx.branches_explored += 1  # a state actually processed
        # A node's "sat" may only be refreshed while the state is still at the
        # node's recorded turn/phase — i.e. for items born at a decision point.
        # Advance items move to later phases first; what gets verified there
        # belongs to the nodes created there.
        refresh_ok = kind == "decision"

        if kind == "advance":
            # NOTE: the node's "sat" deliberately stays as recorded at creation
            # — anything verified during this advance belongs to LATER phases
            # and shows up on the nodes created there (otherwise circles would
            # turn green one phase early in the tree).
            status, satisfied = _advance(state, ctx, satisfied)
            if status == "success":
                _finish_success(state, ctx, satisfied, node)
                return True
            if status == "unviable":
                # A property-violating dead end: record it as an explicit leaf
                # so the tree shows where and why the line was abandoned.
                ctx.new_tree_node(node, "✗ dead end — a property can no longer be verified",
                                  state, satisfied)
                continue
            if status == "dead":
                continue
            kind = status  # "decision" | "combat"

        if kind == "decision":
            # Checkpoint after every action too, so "before <phase>" properties
            # can be satisfied at any moment and stop the search immediately.
            satisfied = _check_due(state, ctx, satisfied)
            if refresh_ok and own and node is not None:
                node["sat"] = sorted(satisfied)
            if _all_satisfied(ctx, satisfied):
                _finish_success(state, ctx, satisfied, node)
                return True
            if not _viable(state, ctx, satisfied):
                ctx.new_tree_node(node, "✗ dead end — a property can no longer be verified",
                                  state, satisfied)
                continue  # some property can no longer be verified from here
            actions = list(legal_actions(state))
            once = False
        else:  # combat: each option immediately advances to the next phase
            actions = list(combat_actions(state))
            once = True

        if heuristic:
            actions.sort(key=_action_priority, reverse=True)
        ctx.branches_considered += len(actions)

        children: list[tuple] = []
        for action in actions:
            child = state.clone()
            try:
                branches = action.apply(child)
            except Exception:
                continue  # a card action that turned out to be illegal mid-apply
            blist = branches if branches is not None else [child]
            # An action whose resolution fans out (fetch targets, surveil
            # piles...) yields several candidate branches: count the extras as
            # considered so `explored <= considered` always holds.
            ctx.branches_considered += max(0, len(blist) - 1)
            for k, branch in enumerate(blist):
                branch.check_deaths()
                label = action.label + (f" · option {k + 1}/{len(blist)}" if len(blist) > 1 else "")
                if isinstance(action, PassPhase) or once:
                    _goto_next_phase(branch)
                    ckind = "advance"
                else:
                    ckind = "decision"
                # Every created state gets a node; past the recording cap we
                # keep the nearest recorded ancestor for success marking (but
                # flag it as not-owned so its "sat" isn't overwritten).
                new_node = ctx.new_tree_node(node, label, branch, satisfied)
                children.append((branch, satisfied, new_node or node, ckind, new_node is not None))

        if mode in ("dfs", "dfs_heuristic"):
            for it in reversed(children):
                push(it)
        else:
            for it in children:
                push(it)
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
    # Root of the recorded search tree: the game before any hand is kept.
    root = {"id": 0, "label": "game", "turn": 0, "phase": "start", "children": [], "success": False, "sat": []}
    ctx.tree_root = root
    ctx.tree_count = 1

    keeps = _opening_hands(shuffled, hand_size, config.mulligans)
    if config.search_mode in ("dfs_heuristic", "best_first"):
        # Heuristic keep ordering: try hands whose land count is closest to 3
        # first (all keeps are still searched — this only changes the order).
        def _keep_score(variant: tuple) -> int:
            lands = sum(1 for c in variant[0] if "land" in (c.type_line or "").lower())
            return abs(lands - 3)

        keeps = sorted(keeps, key=_keep_score)

    items: list[tuple] = []
    keep_nodes: list[tuple[dict | None, list[str]]] = []
    for hand, library, bottomed in keeps:
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
        hand_names = [c.name for c in hand]
        hand_node = ctx.new_tree_node(root, f"keep {hand_names}", variant)
        if hand_node is not None:
            hand_node["hand"] = hand_names  # shown when hovering the initial state
        keep_nodes.append((hand_node, hand_names))
        items.append((variant, frozenset(), hand_node, "advance", hand_node is not None))

    ctx.branches_considered += len(items)  # the keeps are candidates too
    success = _search(items, ctx, config.search_mode)
    root["success"] = success
    _strip_parents(root)

    # For failed games there is no single "kept" hand — report the 7 drawn.
    winning_hand = [c.name for c in shuffled[:hand_size]]
    if success:
        for hand_node, hand_names in keep_nodes:
            if hand_node is not None and hand_node["success"]:
                winning_hand = hand_names
                break

    return GameOutcome(
        game_index=game_index,
        success=success,
        satisfied=set(ctx.ever_satisfied),
        timed_out=ctx.timed_out,
        node_capped=ctx.node_capped,
        sample_log=ctx.success_log or [],
        opening_hand=winning_hand,
        branches_explored=ctx.branches_explored,
        branches_considered=ctx.branches_considered,
        tree=root,
        tree_truncated=ctx.tree_truncated,
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
