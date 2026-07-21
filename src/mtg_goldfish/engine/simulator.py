"""Exhaustive solitaire simulator.

For each game (one random shuffle) we branch over:

  * mulligan keeps — all ways to bottom `Y` of the opening 7 cards, and
  * every line of play — each legal ordering of plays at every priority window
    (sorcery-speed plays in the main phases; instant-speed plays — instants,
    flash, activated abilities — in the other steps' instant-speed windows),

exploring until the latest property trigger moment is reached. A game is a
**success** if some single line satisfies *all* properties at their respective
trigger moments. We also record, per game, which properties were satisfiable
in *any* line (for per-property statistics).

The search order is configurable (`SimulationConfig.search_mode`) — greedy
best-first on a board-progress score, or breadth-first. Every mode visits the
same states; only the visit order differs.

The search is exhaustive and runs until whichever comes first: the per-game
wall-clock timeout expires, every property has been satisfied on some line, or
no live branch can satisfy the remaining properties anymore (the frontier
drains). There is deliberately no node cap.

Mana is solved deterministically (see `actions.plan_payment`) so it is not a
branch point.
"""
from __future__ import annotations

import base64
import gzip
import heapq
import itertools
import json
import os
import random
import time
import traceback
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .actions import (
    PassPhase,
    _has_instant_actions,
    combat_actions,
    deal_combat_damage,
    legal_actions,
)
from .game_state import GameState, new_game_from_deck
from .phases import MAIN_PHASES, TURN_ORDER, Phase, phase_index

#: Non-main steps that grant priority for instant-speed plays. Untap and
#: cleanup grant no priority; the main phases and declare-attackers are handled
#: explicitly (they always stop for sorcery-speed plays / the attack decision).
INSTANT_STEPS: tuple[Phase, ...] = (
    Phase.UPKEEP,
    Phase.DRAW,
    Phase.BEGIN_COMBAT,
    Phase.DECLARE_BLOCKERS,
    Phase.COMBAT_DAMAGE,
    Phase.END_COMBAT,
    Phase.END_STEP,
)


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
    "best_first": "Best-first · greedy on board progress (default)",
    "bfs": "BFS · breadth-first (shallowest lines first)",
}


@dataclass
class SimulationConfig:
    num_games: int = 100
    timeout_per_game_s: float = 5.0
    mulligans: int = 0
    on_the_play: bool = True
    base_seed: int = 12345
    keep_success_logs: int = 25  # how many successful game logs to retain
    search_mode: str = "best_first"  # see SEARCH_MODES
    #: Explore instant-speed plays: open decision windows in non-main steps
    #: (instants/flash/abilities) AND allow countering your own spells. Off by
    #: default — it multiplies the branching factor and is much slower.
    instant_speed: bool = False
    #: Fixed-hand mode: force this exact opening hand (card names) and shuffle
    #: only the rest of the library. None = normal random hands + mulligans.
    fixed_hand: list[str] | None = None
    #: Fixed-hand mode: if set, pad the forced hand with random cards from the
    #: (shuffled) rest of the library up to this total hand size.
    fixed_hand_pad_to: int | None = None
    #: Fake shuffling: mid-game "shuffles" never really reorder the library —
    #: only cards whose position the player knows (Brainstorm put-backs, scry
    #: bottoms...) are reinserted at random spots. Keeps the library
    #: near-constant across all lines of play (see GameState.fake_shuffle).
    fake_shuffle: bool = False
    #: Games run in parallel across CPU cores (one process per worker). None =
    #: automatic (all cores but one, to keep the machine responsive); 1 = fully
    #: sequential in-process.
    parallel_workers: int | None = None


@dataclass
class GameOutcome:
    game_index: int
    success: bool
    satisfied: set[str] = field(default_factory=set)  # props hit in any line
    timed_out: bool = False
    sample_log: list[str] = field(default_factory=list)
    # Per-game search shape (populated for the runs table + tree view).
    opening_hand: list[str] = field(default_factory=list)  # the kept (winning) hand
    branches_explored: int = 0
    branches_considered: int = 0
    tree: dict | None = None
    # gzip+base64 of dumps_tree(tree): parallel workers pre-compress the tree
    # (pickling a raw multi-MB tree dict back to the parent costs far more than
    # gzipping it in the worker) and null out `tree`.
    tree_gz: str | None = None
    tree_truncated: bool = False
    # Exceptions hit during this game's search (see _SearchContext.record_bug).
    bugs: list[dict] = field(default_factory=list)


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
        tree_cap: int | None = None,  # None = record the FULL explored tree
        should_stop: Callable[[], bool] | None = None,
        instant_speed: bool = False,
    ) -> None:
        self.properties = properties
        self.deadline = deadline
        self.instant_speed = instant_speed  # explore instant-speed windows?
        self.timed_out = False
        # Cooperative cancellation: when this returns True the current game is
        # abandoned ASAP (checked in the search's hot path via budget_exceeded).
        self._should_stop = should_stop
        self.stopped = False
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
        # Bugs hit during the search (exceptions raised while applying an action
        # or stepping the game). Recorded rather than silently swallowed so a
        # buggy card can't invisibly hide otherwise-viable lines; surfaced per
        # game in the runs table. De-duplicated by (context, exception) so one
        # recurring fault doesn't flood the list.
        self.bugs: list[dict] = []
        self._bug_keys: set[tuple] = set()
        # ---- within-game parallel split (see _simulate_game_split) ----
        # When set, children created at (or past) this depth are NOT pushed
        # onto the frontier — they are collected in depth_leaves for handing to
        # the workers (or for another expansion round).
        self.stop_depth: int | None = None
        self.depth_leaves: list[tuple] = []

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
        if self.timed_out or self.stopped:
            return True
        if self._should_stop is not None and self._should_stop():
            self.stopped = True  # user cancelled — abandon the current game now
            return True
        if time.monotonic() > self.deadline:
            self.timed_out = True
            return True
        return False

    def record_bug(self, exc: BaseException, *, context: str,
                   state: GameState | None = None) -> None:
        """Record an exception raised during the search. Kept short and
        de-duplicated: the last frame of the traceback usually pins the culprit
        card/engine call, which is what a debugging user needs."""
        tb = traceback.extract_tb(exc.__traceback__)
        last = tb[-1] if tb else None
        where = f"{last.filename.split('/')[-1]}:{last.lineno} in {last.name}" if last else "?"
        key = (context, type(exc).__name__, str(exc), where)
        if key in self._bug_keys:
            return
        self._bug_keys.add(key)
        self.bugs.append({
            "context": context,
            "error": f"{type(exc).__name__}: {exc}",
            "where": where,
            "turn": state.turn if state is not None else None,
            "phase": state.phase.value if state is not None else None,
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-2000:],
        })


# --------------------------------------------------------------------------
# Turn progression
# --------------------------------------------------------------------------
def _apply_step_entry(state: GameState) -> list[GameState] | None:
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
        # Decayed permanents that attacked are sacrificed at end of combat.
        for perm in list(state.battlefield):
            if perm.counters.get("decayed") and perm.uid in state.attackers:
                state.emit(f"{perm.name}: decayed — sacrifice at end of combat")
                state.leaves_battlefield(perm, "graveyard", reason="sacrifice")
        state.attackers.clear()
    elif state.phase == Phase.END_STEP:
        # "Sacrifice it at the beginning of the next end step" (Emperor of Bones'
        # reanimated creatures, Stadium Headliner's mobilized tokens).
        for perm in list(state.battlefield):
            if perm.counters.get("end_step_sac"):
                state.emit(f"{perm.name}: sacrifice at beginning of end step")
                state.leaves_battlefield(perm, "graveyard", reason="sacrifice")
    elif state.phase == Phase.CLEANUP:
        for perm in state.battlefield:
            perm.temp_power = 0
            perm.temp_toughness = 0
            perm.temp_keywords.clear()
            perm.becomes = None  # man-land animation ends
            perm.damage = 0
        state.check_deaths()

    # "At the beginning of <phase>" triggers (upkeep, combat, end step...).
    # These may BRANCH (e.g. Emperor of Bones' begin-of-combat "exile up to one
    # target from a graveyard"): settle() then returns several branch states,
    # which _advance hands back to the search frontier.
    state.queue_phase_triggers(state.phase)
    return state.settle()


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
        except Exception as exc:
            # A property whose code raises can NEVER be satisfied — which would
            # otherwise look exactly like "no line works" and make every game
            # search to timeout with no clue why. Record it (dedup'd, surfaced
            # per game as a 🐛) so the broken property is visible, not silent.
            ctx.record_bug(exc, state=state,
                           context=f"evaluating property {getattr(prop, 'id', '?')}")
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
    (status, satisfied, branches) with status in {"success", "dead",
    "unviable", "decision", "branch"} — "unviable" means a property can no
    longer be verified on this line ("dead" is a budget cut). `branches` is None
    except for "branch", where a phase-entry triggered ability fanned out into
    several states the caller must push back onto the search frontier.

    A "decision" is returned in every main phase (full sorcery-speed plays), at
    declare-attackers (the attack decision, plus any instant-speed plays), and
    in any other step where an instant-speed play is actually available — so all
    lines of play, including instant-speed ones, are explored. Steps with no
    available play are skipped so the search doesn't fan out a bare "pass" at
    every step."""
    while True:
        if ctx.budget_exceeded():
            return "dead", satisfied, None
        if (state.turn, phase_index(state.phase)) > ctx.max_rank:
            return "unviable", satisfied, None  # past every remaining trigger moment

        # Each branch of a fanned-out phase trigger resumes here with its
        # step-entry already applied — skip re-applying it exactly once.
        if state._skip_step_entry == (state.turn, state.phase):
            state._skip_step_entry = None
        else:
            branches = _apply_step_entry(state)
            if branches is not None:
                # A phase-entry trigger branched (e.g. Emperor of Bones' exile).
                # Hand each fully-settled branch back to the search to continue
                # advancing; mark where it must skip the step-entry it just ran.
                for b in branches:
                    b._skip_step_entry = (b.turn, b.phase)
                return "branch", satisfied, branches

        # One checkpoint per phase entry: evaluates "at" properties due right
        # here and "before" properties whose moment has not been reached yet.
        satisfied = _check_due(state, ctx, satisfied)
        if _all_satisfied(ctx, satisfied):
            return "success", satisfied, None
        if not _viable(state, ctx, satisfied):
            return "unviable", satisfied, None  # some property can no longer be verified

        if state.phase in MAIN_PHASES:
            return "decision", satisfied, None
        # The attack decision always matters; instant-speed windows only when the
        # user opted into them (they explode the branching factor).
        if state.phase == Phase.DECLARE_ATTACKERS and (
            combat_actions(state) or (ctx.instant_speed and _has_instant_actions(state))
        ):
            return "decision", satisfied, None
        if ctx.instant_speed and state.phase in INSTANT_STEPS and _has_instant_actions(state):
            return "decision", satisfied, None

        _goto_next_phase(state)


def _option_details(blist: list[GameState], base_len: int) -> list[str | None]:
    """When one action fans out into several branches, describe what makes each
    branch different: the first log message (past the parent's `base_len`) at
    which the branches diverge — e.g. "exchange text boxes with X" vs "... Y",
    or two different fetch targets. Returns one detail per branch (None when
    the branches' logs never diverge)."""
    seqs = [[fr.get("desc", "") for fr in b.log[base_len:]] for b in blist]
    for i in range(max((len(s) for s in seqs), default=0)):
        if len({s[i] if i < len(s) else None for s in seqs}) > 1:
            return [s[i] if i < len(s) else None for s in seqs]
    return [None] * len(blist)


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


def _search(items: list[tuple], ctx: _SearchContext, mode: str) -> bool:
    """Search over game states. `items` are (state, satisfied, node, kind, own,
    depth) seeds, where kind is "advance" (state must first be advanced through
    non-choice steps) or "decision" (the player holds priority — a main phase,
    declare-attackers, or an instant-speed window); `own` says whether `node`
    was created for this very state (vs. a truncation fallback); `depth` counts
    how many child states separate it from the game root (used to split the
    tree across worker processes — see _simulate_game_split).

    Every branch state created by an action gets its own tree node — including
    passing priority — so the recorded tree shows ALL states created during
    the search. Actions that raise mid-apply are recorded as bugs (see
    `ctx.record_bug`) and shown as error leaves, never silently dropped. All
    modes are exhaustive; they differ only in visit order."""
    # Best-first uses move-ordering as a heap tie-break; BFS is pure
    # breadth-first with no reordering.
    heuristic = mode != "bfs"

    if mode == "bfs":
        frontier: deque = deque(items)
        pop = frontier.popleft
        push = frontier.append
    else:  # best_first: a min-heap on the board-progress score
        seq = itertools.count()  # tie-breaker: insertion order
        frontier_h: list[tuple] = []
        for it in items:
            heapq.heappush(frontier_h, (_progress_score(it[0], it[1]), next(seq), it))
        frontier = frontier_h
        pop = lambda: heapq.heappop(frontier)[2]  # noqa: E731
        push = lambda it: heapq.heappush(frontier, (_progress_score(it[0], it[1]), next(seq), it))  # noqa: E731

    def offer_child(branch, satisfied, parent_node, label, ckind, child_depth):
        """Give a newly created child state its tree node and route it: onto
        the frontier (normal), or into the split collection (during a split
        expansion, children at the collection depth are handed back to the
        caller — for the workers, or for another expansion round — instead of
        being explored here)."""
        node = ctx.new_tree_node(parent_node, label, branch, satisfied)
        if ctx.stop_depth is not None and child_depth >= ctx.stop_depth:
            ctx.depth_leaves.append(
                (branch, satisfied, node, ckind, node is not None, child_depth))
            return
        push((branch, satisfied, node or parent_node, ckind, node is not None, child_depth))

    while frontier:
        if ctx.timed_out or ctx.stopped:
            return False
        state, satisfied, node, kind, own, depth = pop()
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
            try:
                status, satisfied, branches = _advance(state, ctx, satisfied)
            except Exception as exc:  # a crash while stepping the game forward
                ctx.record_bug(exc, state=state, context=f"advancing @ {state.phase.value}")
                ctx.new_tree_node(node, "⚠ error advancing the game", state, satisfied)
                continue
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
            if status == "branch":
                # A phase-entry triggered ability fanned out (e.g. Emperor of
                # Bones' begin-of-combat exile). Give each branch its own tree
                # node and push it back to keep advancing from after the trigger.
                ctx.branches_considered += len(branches)
                details = (_option_details(branches, len(state.log))
                           if len(branches) > 1 else [None])
                for k, branch in enumerate(branches):
                    label = f"{state.phase.value} trigger · option {k + 1}/{len(branches)}"
                    if details[k]:
                        label += f" — {details[k]}"
                    offer_child(branch, satisfied, node, label, "advance", depth + 1)
                continue
            kind = status  # "decision"

        # A decision point: the player holds priority. In a main phase full
        # sorcery-speed plays are offered; elsewhere only instant-speed ones.
        # Checkpoint after every action too, so "before <phase>" properties can
        # be satisfied at any moment and stop the search immediately.
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
        if state.phase in MAIN_PHASES:
            actions = list(legal_actions(state, sorcery_speed_ok=True))
        elif ctx.instant_speed:
            actions = list(legal_actions(state, sorcery_speed_ok=False))  # instant window
        else:
            actions = [PassPhase()]  # non-main step, instant plays disabled: just pass
        if state.phase == Phase.DECLARE_ATTACKERS:
            # The attack decision, alongside any instant-speed plays and pass.
            actions = list(combat_actions(state)) + actions

        if heuristic:
            actions.sort(key=_action_priority, reverse=True)
        ctx.branches_considered += len(actions)

        for action in actions:
            child = state.clone()
            try:
                branches = action.apply(child)
            except Exception as exc:
                # Never silently drop a line: record the bug (surfaced per game
                # in the runs table) and leave an error leaf in the tree.
                ctx.record_bug(exc, state=child, context=f"applying '{action.label}'")
                ctx.new_tree_node(node, f"⚠ error — {action.label}", child, satisfied)
                continue
            blist = branches if branches is not None else [child]
            # An action whose resolution fans out (fetch targets, surveil
            # piles...) yields several candidate branches: count the extras as
            # considered so `explored <= considered` always holds.
            ctx.branches_considered += max(0, len(blist) - 1)
            # Branching plays (targets, modes...) get their distinguishing
            # detail in the label so the tree shows WHAT each option does.
            details = _option_details(blist, len(state.log)) if len(blist) > 1 else [None]
            for k, branch in enumerate(blist):
                branch.check_deaths()
                label = action.label
                if len(blist) > 1:
                    label += f" · option {k + 1}/{len(blist)}"
                    if details[k]:
                        label += f" — {details[k]}"
                if isinstance(action, PassPhase):
                    # Passing priority advances to the next step; every other
                    # action (including declaring attackers) keeps priority so
                    # further plays this step are explored.
                    _goto_next_phase(branch)
                    ckind = "advance"
                else:
                    ckind = "decision"
                # Every created state gets a node (inside offer_child); past
                # the recording cap the nearest recorded ancestor is kept for
                # success marking (flagged not-owned so "sat" isn't overwritten).
                offer_child(branch, satisfied, node, label, ckind, depth + 1)
    return False


# --------------------------------------------------------------------------
# Search-tree serialization (used by the web runner and the parallel workers)
# --------------------------------------------------------------------------
def dumps_tree(root: dict) -> str:
    """Compact-JSON-encode a search tree iteratively.

    The tree can be thousands of nodes deep (DFS lines), and `json.dumps`
    recurses one C frame per nesting level — deep trees blow the recursion
    limit. Every node field is shallow except "children" (the only recursive
    link), so we dump each node's shallow fields with `json.dumps` and stitch
    the `children` nesting together with an explicit stack."""
    parts: list[str] = []
    # LIFO of work items: ("open", node) emits a node; ("raw", s) emits text.
    stack: list[tuple] = [("open", root)]
    while stack:
        kind, val = stack.pop()
        if kind == "raw":
            parts.append(val)
            continue
        node = val
        shallow = {k: v for k, v in node.items() if k != "children"}
        head = json.dumps(shallow, separators=(",", ":"))
        children = node.get("children") or []
        # Re-append "children" as the final key of the object.
        open_obj = ('{"children":[' if head == "{}"
                    else head[:-1] + ',"children":[')
        if not children:
            parts.append(open_obj + "]}")
            continue
        parts.append(open_obj)
        stack.append(("raw", "]}"))
        # Push children reversed with commas so they emit as c0,c1,...,cN.
        for i in range(len(children) - 1, -1, -1):
            stack.append(("open", children[i]))
            if i > 0:
                stack.append(("raw", ","))
    return "".join(parts)


def compress_tree(root: dict) -> str:
    """gzip+base64 a search tree (highly repetitive JSON, ~20x smaller)."""
    return base64.b64encode(gzip.compress(dumps_tree(root).encode(), 6)).decode("ascii")


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


def _fixed_opening_hand(
    library: list, names: list[str], pad_to: int | None = None
) -> list[tuple[list, list, list]]:
    """Fixed-hand mode: pull the requested cards (by name, honouring copies)
    out of the shuffled library into the opening hand; the remainder stays in
    shuffled order as the library. With `pad_to`, top up the hand with random
    cards (the top of the already-shuffled remainder) to that total size.
    A single keep, no mulligans."""
    lib = list(library)
    hand: list = []
    for name in names:
        card = next((c for c in lib if c.name == name), None)
        if card is None:
            continue  # not available in this many copies — skip it
        lib.remove(card)
        hand.append(card)
    if pad_to is not None:
        while len(hand) < pad_to and lib:
            hand.append(lib.pop(0))  # lib is shuffled — its top is random
    return [(hand, lib, [])]


def _seed_game(
    base_state: GameState,
    properties: list[CompiledProperty],
    config: SimulationConfig,
    game_index: int,
    should_stop: Callable[[], bool] | None = None,
    deadline: float | None = None,
) -> tuple[_SearchContext, dict, list[tuple], list[tuple], list]:
    """Deterministically set up one game: the shuffled library, the search
    context/tree root, and the opening-keep frontier seeds. Everything derives
    from `config.base_seed + game_index`, so the master process and its
    subtree workers rebuild the exact same game independently — no game state
    ever crosses a process boundary."""
    rng = random.Random(config.base_seed + game_index)
    shuffled = list(base_state.library)
    rng.shuffle(shuffled)

    hand_size = 7
    if deadline is None:
        deadline = time.monotonic() + config.timeout_per_game_s
    ctx = _SearchContext(properties, deadline, should_stop=should_stop,
                         instant_speed=config.instant_speed)
    # Root of the recorded search tree: the game before any hand is kept.
    root = {"id": 0, "label": "game", "turn": 0, "phase": "start", "children": [], "success": False, "sat": []}
    ctx.tree_root = root
    ctx.tree_count = 1

    if config.fixed_hand:
        # Fixed-hand mode: the opening hand is chosen by the user (optionally
        # padded with random cards up to a chosen size); only the rest of the
        # library varies (per game seed). No mulligan branching.
        keeps = _fixed_opening_hand(shuffled, config.fixed_hand, config.fixed_hand_pad_to)
    else:
        keeps = _opening_hands(shuffled, hand_size, config.mulligans)
        if config.search_mode == "best_first":
            # Heuristic keep ordering: try hands whose land count is closest to
            # 3 first (all keeps are still searched — this only changes order).
            def _keep_score(variant: tuple) -> int:
                lands = sum(1 for c in variant[0] if c.is_land)
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
        if bottomed:
            # The player saw the bottomed cards go under: with fake shuffling
            # on, the next "shuffle" reinserts exactly these at random spots.
            variant.mark_known_in_library(*bottomed)
        play_draw = "on the play" if variant.on_the_play else "on the draw"
        if config.fixed_hand:
            variant.emit(f"fixed opening hand ({play_draw}): {[c.name for c in hand]}")
        elif bottomed:
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
        items.append((variant, frozenset(), hand_node, "advance", hand_node is not None, 0))

    ctx.branches_considered += len(items)  # the keeps are candidates too
    return ctx, root, items, keep_nodes, shuffled


def _assemble_outcome(
    ctx: _SearchContext, root: dict, keep_nodes: list[tuple], shuffled: list,
    config: SimulationConfig, game_index: int, success: bool,
) -> GameOutcome:
    root["success"] = success
    _strip_parents(root)

    # For failed games there is no single "kept" hand — report the 7 drawn
    # (or the fixed hand in fixed-hand mode).
    winning_hand = keep_nodes[0][1] if config.fixed_hand else [c.name for c in shuffled[:7]]
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
        sample_log=ctx.success_log or [],
        opening_hand=winning_hand,
        branches_explored=ctx.branches_explored,
        branches_considered=ctx.branches_considered,
        tree=root,
        tree_truncated=ctx.tree_truncated,
        bugs=ctx.bugs,
    )


def simulate_game(
    base_state: GameState,
    properties: list[CompiledProperty],
    config: SimulationConfig,
    game_index: int,
    should_stop: Callable[[], bool] | None = None,
) -> GameOutcome:
    ctx, root, items, keep_nodes, shuffled = _seed_game(
        base_state, properties, config, game_index, should_stop=should_stop)
    try:
        success = _search(items, ctx, config.search_mode)
    except Exception as exc:  # a crash in the search itself, not a single action
        ctx.record_bug(exc, context="search")
        success = False
    return _assemble_outcome(ctx, root, keep_nodes, shuffled, config, game_index, success)


def _buggy_outcome(game_index: int, exc: BaseException) -> GameOutcome:
    """A placeholder outcome for a game whose setup/search crashed outright."""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return GameOutcome(
        game_index=game_index, success=False,
        bugs=[{"context": "game setup/search", "error": f"{type(exc).__name__}: {exc}",
               "where": "?", "turn": None, "phase": None, "traceback": tb[-2000:]}],
    )


def _count_game(stats: SimulationStats, outcome: GameOutcome) -> None:
    stats.games_run += 1
    if outcome.success:
        stats.successes += 1
    if outcome.timed_out:
        stats.timeouts += 1
    for pid in outcome.satisfied:
        stats.per_property[pid] = stats.per_property.get(pid, 0) + 1


# ---- within-game parallel search -------------------------------------------
# Games run SEQUENTIALLY (results stream in game order), but each game's tree
# is explored across CPU cores. Mid-game states can't cross a process boundary
# (card implementations are factory-built classes, unpicklable), so nothing is
# shipped: every worker deterministically REBUILDS the same game from the seed,
# replays the same shallow search the master did, and explores only its
# assigned share of the subtrees hanging at a chosen split depth. Subtree
# numbering is by creation order, which is identical in every process, so the
# master can graft the returned subtrees back into its own tree.
_WORKER: dict = {}

#: Don't split deeper than this many levels looking for enough subtrees.
_SPLIT_MAX_DEPTH = 12

#: How long PAST a game's own deadline to keep waiting for a worker before
#: treating it as wedged. A worker stuck in card code that never returns to its
#: search loop never rechecks its (cooperative) deadline or the stop flag, so
#: its future would never complete and the wait would hang forever; past this
#: grace we kill the process and rebuild the pool so the run keeps moving. The
#: grace also covers a well-behaved worker serialising a large result back.
_WORKER_GRACE_S = 5.0
#: On a user Stop, how long to let workers wind down before abandoning them
#: (their results are discarded anyway, so this only needs to be responsive).
_STOP_GRACE_S = 2.0


def _worker_init(deck, specs, config: SimulationConfig, stop_event, found_event) -> None:
    from ..cards import load_all_cards
    from ..properties.evaluator import compile_all

    load_all_cards()
    base = new_game_from_deck(deck, on_the_play=config.on_the_play)
    base.instant_speed = config.instant_speed
    base.fake_shuffle = config.fake_shuffle
    _WORKER["base"] = base
    _WORKER["props"] = compile_all(specs)  # exec'd check fns can't be pickled
    _WORKER["config"] = config
    _WORKER["stop"] = stop_event    # the user pressed Stop
    _WORKER["found"] = found_event  # another worker found this game's success


def _throttled_stop(*events, interval: float = 0.15) -> Callable[[], bool]:
    """Wrap cross-process Events in a time-throttled checker: `is_set()` on a
    manager proxy is an IPC round-trip, far too slow for the search's hot path."""
    memo = {"t": 0.0, "hit": False}

    def check() -> bool:
        if memo["hit"]:
            return True
        now = time.monotonic()
        if now - memo["t"] >= interval:
            memo["t"] = now
            memo["hit"] = any(e.is_set() for e in events)
        return memo["hit"]

    return check


def _expand_to_split(
    ctx: _SearchContext, items: list[tuple], mode: str, min_leaves: int,
) -> tuple[str, list[tuple], int]:
    """Shallow expansion shared by the master and the workers: process the
    search level by level, collecting the children at the smallest depth that
    offers at least `min_leaves` subtrees. Because the master and every worker
    run this EXACT procedure on the EXACT same (seed-rebuilt) game, they end up
    with the same leaves in the same order — that shared numbering is what lets
    a worker's subtrees be grafted back onto the master's tree without any game
    state ever crossing a process boundary.

    Returns (status, leaves, depth) with status "split" (leaves ready to
    distribute), "success" (all properties satisfied while still shallow) or
    "done" (frontier drained / budget cut — nothing left to split)."""
    depth, current = 1, items
    while True:
        ctx.stop_depth = depth
        ctx.depth_leaves = []
        success = _search(current, ctx, mode)
        leaves = ctx.depth_leaves
        ctx.stop_depth = None
        ctx.depth_leaves = []
        if success:
            return "success", leaves, depth
        if not leaves or ctx.timed_out or ctx.stopped:
            return "done", leaves, depth
        if len(leaves) >= min_leaves or depth >= _SPLIT_MAX_DEPTH:
            return "split", leaves, depth
        current = leaves  # not enough parallelism there — expand one level deeper
        depth += 1


def _tree_worker(game_index: int, min_leaves: int, num_parts: int, part: int,
                 remaining_s: float) -> dict:
    """Explore this worker's share of one game's subtrees and return them
    (plus counters/bugs/success data) for the master to merge. The game and
    its shallow expansion are rebuilt from the seed — deterministically
    identical to the master's."""
    config: SimulationConfig = _WORKER["config"]
    # Test-only wedge injection: simulate a worker stuck in card code (never
    # returns, never rechecks the deadline/stop) so the containment path — kill
    # the process, rebuild the pool, keep the run moving — can be tested.
    _hang = os.environ.get("MTG_TEST_HANG_GAME")
    if _hang is not None and _hang.isdigit() and int(_hang) == game_index:
        time.sleep(3600)
    deadline = time.monotonic() + remaining_s
    ctx, root, items, keep_nodes, shuffled = _seed_game(
        _WORKER["base"], _WORKER["props"], config, game_index,
        should_stop=_throttled_stop(_WORKER["stop"], _WORKER["found"]),
        deadline=deadline,
    )
    success = False
    subtrees: dict[int, dict] = {}
    try:
        status, leaves, depth = _expand_to_split(ctx, items, config.search_mode, min_leaves)
        if status == "split":
            assigned = [(j, leaves[j]) for j in range(len(leaves)) if j % num_parts == part]
            success = _search([it for _, it in assigned], ctx, config.search_mode)
            for j, it in assigned:
                node = it[2]
                if node is not None:
                    _strip_parents(node)  # the "_p" chain would drag the whole tree
                    subtrees[j] = node
        else:
            # Shouldn't happen (the master only launches workers after finding
            # a split), but stay graceful: report what this replay concluded.
            success = status == "success"
    except Exception as exc:
        ctx.record_bug(exc, context="search")
    return {
        "part": part,
        "success": success,
        "success_log": ctx.success_log or [],
        "satisfied": sorted(ctx.ever_satisfied),
        "timed_out": ctx.timed_out,
        "explored": ctx.branches_explored,
        "considered": ctx.branches_considered,
        "bugs": ctx.bugs,
        "subtrees": subtrees,
    }


def _clear_success(node: dict) -> None:
    """Unmark a subtree's success flags (iterative — trees can be deep)."""
    stack = [node]
    while stack:
        n = stack.pop()
        n["success"] = False
        stack.extend(n.get("children") or [])


def _simulate_game_split(
    base_state: GameState,
    properties: list[CompiledProperty],
    config: SimulationConfig,
    game_index: int,
    pool,
    workers: int,
    stop_event,
    found_event,
    should_stop: Callable[[], bool] | None,
    on_tainted: Callable[[], None] | None = None,
) -> GameOutcome | None:
    """One game, its tree explored in parallel. The master expands the search
    level by level until enough subtrees hang at some depth (or the search
    finishes inline for tiny games), then hands each worker its share. Returns
    None when the user stopped mid-game (the game is abandoned, not counted).

    `on_tainted` is called if a worker has to be abandoned past its deadline
    (wedged in card code): its process is still alive and holding a core, so
    the caller must kill and rebuild the pool before the next game."""
    from concurrent.futures import wait as futures_wait

    ctx, root, items, keep_nodes, shuffled = _seed_game(
        base_state, properties, config, game_index, should_stop=should_stop)

    # Phase 1 — shallow expansion in this process: process everything above
    # the split depth, collecting the children AT it instead of exploring them.
    min_leaves = 3 * workers  # enough subtrees for decent load balance
    try:
        status, leaves, depth = _expand_to_split(ctx, items, config.search_mode, min_leaves)
    except Exception as exc:
        ctx.record_bug(exc, context="search")
        return _assemble_outcome(ctx, root, keep_nodes, shuffled, config, game_index, False)
    if status != "split":
        # Solved (or exhausted/cut) within the shallow region — no workers.
        if ctx.stopped and should_stop and should_stop():
            return None  # user abort — don't report a half-searched game
        return _assemble_outcome(ctx, root, keep_nodes, shuffled, config, game_index,
                                 status == "success")

    # Phase 2 — fan the subtrees out to the workers.
    shallow_explored = ctx.branches_explored
    shallow_considered = ctx.branches_considered
    found_event.clear()
    remaining = max(0.05, ctx.deadline - time.monotonic())
    num_parts = min(workers, len(leaves))
    futures = [pool.submit(_tree_worker, game_index, min_leaves, num_parts, part, remaining)
               for part in range(num_parts)]
    results: list[dict] = []
    pending = set(futures)
    # A worker that wedges deep in card code never returns to its search loop,
    # so it never rechecks its (cooperative) deadline or the stop flag and its
    # future would never complete — making an unbounded wait hang the whole run
    # (the bug this guards against). Bound it by a hard wall-clock limit: the
    # game's own remaining time plus a grace for well-behaved workers to notice
    # their soft deadline and hand results back. Past the limit the stragglers
    # are wedged: abandon them and flag the pool for a kill + rebuild.
    hard_deadline = time.monotonic() + remaining + _WORKER_GRACE_S
    stop_deadline = None  # a shorter grace, armed once the user hits Stop
    tainted = False
    while pending:
        now = time.monotonic()
        if should_stop and should_stop():
            stop_event.set()  # well-behaved workers wind down within ~0.15 s
            if stop_deadline is None:
                stop_deadline = now + _STOP_GRACE_S
        limit = stop_deadline if stop_deadline is not None else hard_deadline
        if now >= limit:
            tainted = True
            if on_tainted is not None:
                on_tainted()  # stragglers are wedged — pool must be recycled
            break
        done, pending = futures_wait(pending, timeout=0.2)
        for fut in done:
            try:
                r = fut.result()
            except Exception as exc:  # worker died / unpicklable result
                ctx.record_bug(exc, context="parallel subtree worker")
                continue
            results.append(r)
            if r["success"]:
                found_event.set()  # the others can stop — the game is solved
    if should_stop and should_stop():
        return None  # user abort — don't report a half-searched game

    # Phase 3 — merge. One winner is chosen (lowest part index for
    # determinism); other workers' incidental successes are unmarked so the
    # tree shows a single gold line.
    by_part = {r["part"]: r for r in results}
    success_parts = sorted(p for p, r in by_part.items() if r["success"])
    winner = by_part[success_parts[0]] if success_parts else None
    for r in results:
        if winner is not None and r is not winner:
            for node in r["subtrees"].values():
                _clear_success(node)

    seen_bugs = {(b["context"], b["error"], b["where"]) for b in ctx.bugs}
    for r in results:
        # Workers replay the master's shallow search, so their counters include
        # it — count that shared prefix once, plus each worker's own subtrees.
        ctx.branches_explored += max(0, r["explored"] - shallow_explored)
        ctx.branches_considered += max(0, r["considered"] - shallow_considered)
        ctx.ever_satisfied |= set(r["satisfied"])
        for b in r["bugs"]:  # shallow-region bugs are seen by every worker
            key = (b["context"], b["error"], b["where"])
            if key not in seen_bugs:
                seen_bugs.add(key)
                ctx.bugs.append(b)

    for j, leaf in enumerate(leaves):
        node = leaf[2]
        r = by_part.get(j % num_parts)
        sub = (r or {}).get("subtrees", {}).get(j)
        if node is None or sub is None:
            continue  # worker died or was stopped before reaching this subtree
        node["children"] = sub.get("children", [])
        node["sat"] = sub.get("sat", node["sat"])
        if sub.get("success"):
            node["success"] = True
            _mark_success(node)  # light the winning line up to the root

    success = winner is not None
    if success:
        ctx.success_log = winner["success_log"]
    # A tainted game hit the wall clock (a worker had to be abandoned), so it
    # counts as timed out, like any other deadline cut.
    ctx.timed_out = (not success) and (
        ctx.timed_out or tainted or any(r["timed_out"] for r in results))
    return _assemble_outcome(ctx, root, keep_nodes, shuffled, config, game_index, success)


def _new_pool(mp_ctx, workers, deck, specs, config, stop_event, found_event):
    from concurrent.futures import ProcessPoolExecutor

    return ProcessPoolExecutor(
        max_workers=workers, mp_context=mp_ctx, initializer=_worker_init,
        initargs=(deck, specs, config, stop_event, found_event),
    )


def _terminate_pool(pool) -> None:
    """Force-kill a pool's worker processes and drop the executor. A worker
    wedged in card code that never rechecks its deadline won't exit on a plain
    shutdown() (which would wait for it), so we kill the processes outright —
    the only way to reclaim a wedged core without hanging the whole run."""
    for proc in list(getattr(pool, "_processes", {}).values()):
        try:
            proc.kill()
        except Exception:  # noqa: BLE001 - best-effort teardown
            pass
    try:
        pool.shutdown(wait=False, cancel_futures=True)
    except Exception:  # noqa: BLE001
        pass


def run_simulation(
    deck,
    properties: list[CompiledProperty],
    config: SimulationConfig,
    on_game: Callable[[GameOutcome, SimulationStats], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    *,
    game_indices: list[int] | None = None,
    initial_stats: dict | None = None,
) -> SimulationStats:
    """Run the games of `game_indices` (default: all `config.num_games`),
    invoking `on_game` after each for live reporting. Games run STRICTLY IN
    ORDER, one at a time — but each game's tree search is spread across CPU
    cores when possible (see SimulationConfig.parallel_workers and
    `_simulate_game_split`). `should_stop` allows cooperative cancellation —
    it is checked between games AND inside each game's search (including the
    subtree workers), so Stop abandons the game in progress immediately rather
    than waiting for its timeout.

    `game_indices` + `initial_stats` support RESUMING a partial run: pass the
    not-yet-run indices and the stored stats dict, and the counts continue
    from there (per-game seeds only depend on the index, so a resumed game is
    identical to what it would have been in the original run)."""
    stats = SimulationStats(total_games=config.num_games)
    stats.per_property = {p.id: 0 for p in properties}
    if initial_stats:
        stats.games_run = int(initial_stats.get("games_run") or 0)
        stats.successes = int(initial_stats.get("successes") or 0)
        stats.timeouts = int(initial_stats.get("timeouts") or 0)
        for pid, n in (initial_stats.get("per_property") or {}).items():
            stats.per_property[pid] = int(n)
    indices = (list(game_indices) if game_indices is not None
               else list(range(config.num_games)))

    base_state = new_game_from_deck(deck, on_the_play=config.on_the_play)
    base_state.instant_speed = config.instant_speed  # gates counter-your-own etc.
    base_state.fake_shuffle = config.fake_shuffle

    workers = (config.parallel_workers if config.parallel_workers
               else max(1, (os.cpu_count() or 2) - 1))
    # The workers recompile the properties from their specs; hand-built
    # property objects (tests) don't have one — those run fully sequentially.
    can_parallel = all(getattr(p, "spec", None) is not None for p in properties)

    pool = manager = stop_event = found_event = mp_ctx = specs = None
    if workers > 1 and indices and can_parallel:
        import multiprocessing as mp

        specs = [p.spec for p in properties]
        mp_ctx = mp.get_context("spawn")  # fork is unsafe under a threaded server
        manager = mp_ctx.Manager()
        stop_event = manager.Event()
        found_event = manager.Event()
        pool = _new_pool(mp_ctx, workers, deck, specs, config, stop_event, found_event)

    try:
        for i in indices:
            if should_stop and should_stop():
                break
            tainted = [False]
            try:
                if pool is not None:
                    outcome = _simulate_game_split(
                        base_state, properties, config, i, pool, workers,
                        stop_event, found_event, should_stop,
                        on_tainted=lambda: tainted.__setitem__(0, True))
                else:
                    outcome = simulate_game(base_state, properties, config, i,
                                            should_stop=should_stop)
            except Exception as exc:  # keep the run alive; report the game as buggy
                outcome = _buggy_outcome(i, exc)
            # A tainted pool has a wedged worker process holding a core hostage:
            # kill it, and (unless the run is ending) spin up a fresh pool so the
            # remaining games keep full parallelism and stay responsive.
            if tainted[0] and pool is not None:
                _terminate_pool(pool)
                pool = (None if (should_stop and should_stop())
                        else _new_pool(mp_ctx, workers, deck, specs, config,
                                       stop_event, found_event))
            # If Stop fired during this game, abandon it: don't report a
            # half-searched game as a result or count it.
            if outcome is None or (should_stop and should_stop()):
                break
            _count_game(stats, outcome)
            if on_game:
                on_game(outcome, stats)
    finally:
        if pool is not None:
            _terminate_pool(pool)  # never blocks, even on a wedged worker
        if manager is not None:
            try:
                manager.shutdown()
            except Exception:  # noqa: BLE001
                pass

    return stats
