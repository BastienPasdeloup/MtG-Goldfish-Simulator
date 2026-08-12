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
from .game_state import GameState, Permanent, make_permanent, new_game_from_deck
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

#: Cap the replay-step detail stored per tree node (keeps a pathological
#: single-action resolution from bloating the serialized tree).
_MAX_NODE_STEPS = 40

#: Cap the number of explored-states-tree NODES recorded per game. The SEARCH is
#: unbounded (this only limits what's kept for the tree viz), but the recorded
#: tree is what dominates the saved session size — an unbounded run that explores
#: millions of states produced ~20 MB+ of gzipped tree PER GAME (600 MB sessions).
#: best-first finds a success early, so the winning line is recorded before the
#: cap; `tree_truncated` tells the viewer the rest was elided. Per-worker in the
#: parallel path, so the merged tree can reach ~cap × workers.
_TREE_NODE_CAP = 30000

#: Sentinel used in a fixed-config `library` list for an UNKNOWN card pinned at
#: that depth (a random card fills it) — see _build_fixed_variant. Mirrored in
#: the web UI as FC_UNKNOWN.
_FC_UNKNOWN = "__unknown__"


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
    #: Record the explored-states TREE (for the tree viz). Off by DEFAULT — don't
    #: build it, which trims memory + the saved session size (the tree dominates
    #: it) and shaves the recording overhead. Replays are unaffected.
    save_tree: bool = False
    #: Fixed-config mode: a fully-specified starting state (a plain dict — the
    #: FixedConfig model dumped) the search begins from instead of an opening
    #: hand. Keys: battlefield [{name, tapped}], hand/graveyard/exile [names],
    #: life, opponent_life, mana_pool {sym: n}, storm_count, turn, phase. The
    #: library is the deck cards not placed elsewhere (shuffled per game seed).
    #: Mutually exclusive with fixed_hand.
    fixed_config: dict | None = None


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
    # Wall-clock seconds this game's search took (per-game "Time" column).
    elapsed_s: float = 0.0


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
        should_skip: Callable[[], bool] | None = None,
        instant_speed: bool = False,
        game_index: int = 0,
        on_progress: Callable[[int, int, int, float], None] | None = None,
    ) -> None:
        self.properties = properties
        self.deadline = deadline
        # Live in-game progress: `on_progress(game_index, explored, considered,
        # elapsed_s)` is called from the search hot path, throttled to ~2s.
        self.game_index = game_index
        self._on_progress = on_progress
        self._last_progress = 0.0
        self.instant_speed = instant_speed  # explore instant-speed windows?
        self.timed_out = False
        # Cooperative cancellation: when this returns True the current game is
        # abandoned ASAP (checked in the search's hot path via budget_exceeded).
        self._should_stop = should_stop
        # Per-game skip: abandon THIS game (counts as a failure), unlike stop
        # which ends the whole run.
        self._should_skip = should_skip
        self.stopped = False
        self.ever_satisfied: set[str] = set()  # any line, this game
        self.success_log: list[str] | None = None
        self.max_rank = max(
            ((p.turn, phase_index(p.phase)) for p in properties), default=(0, 0)
        )
        # Wall-clock start of this game's search (for the per-game "Time" column
        # and the live in-game progress ticker).
        self.start_time = time.monotonic()
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
        satisfied: frozenset[str] = frozenset(), steps: list[str] | None = None,
    ) -> dict | None:
        """Attach a child node to `parent` for a newly created state. Returns
        the new node, or None once the recording cap is hit. Nodes carry a
        transient "_p" parent reference (stripped before the tree is returned)
        so the winning line can be marked bottom-up, and "sat" — the property
        ids verified on this line so far (refreshed at the node's own
        checkpoint) — for the per-property status circles in the tree view.
        `steps` is the ordered list of replay-frame descriptions that occurred
        while reaching this node (abilities resolving, triggers, reveals, ...) —
        the same detail the board replay shows — so the tree view can expose
        everything that happened at the node, not just its one-line label."""
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
        if steps:
            node["steps"] = steps[:_MAX_NODE_STEPS]
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
        if self._should_skip is not None and self._should_skip():
            # Abandon THIS game (it becomes an unsuccessful result); the run
            # continues with the next game. Marked as a timeout for the stats.
            self.timed_out = True
            return True
        now = time.monotonic()
        if self._on_progress is not None and now - self._last_progress >= 1.0:
            self._last_progress = now
            self._on_progress(self.game_index, self.branches_explored,
                              self.branches_considered, now - self.start_time)
        if now > self.deadline:
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
def _resolve_suspend(state: GameState) -> list[GameState] | None:
    """At the beginning of the player's upkeep, remove a time counter from every
    suspended card; a card whose last counter is removed is cast for free (its
    impl's `on_suspend_resolve`, which may BRANCH — e.g. Profane Tutor's tutor).
    Returns the resulting branch states, or None when nothing resolves (search
    continues on the single unchanged state)."""
    if not state.suspended:
        return None
    from ..cards.registry import build_card

    ready, remaining = [], []
    for entry in state.suspended:
        entry["counters"] -= 1
        state.emit(f"{entry['name']}: remove a time counter "
                   f"({entry['counters']} remaining)")
        (ready if entry["counters"] <= 0 else remaining).append(entry)
    state.suspended = remaining
    if not ready:
        return None

    branches = [state]
    for entry in ready:
        card = entry["card"]
        nxt: list[GameState] = []
        for b in branches:
            if card in b.exile:
                b.exile.remove(card)
            b.emit(f"{entry['name']}: last time counter removed — cast it for free")
            res = build_card(card).on_suspend_resolve(b)
            nxt.extend([b] if res is None else res)
        branches = nxt
    return branches


def _apply_step_entry(state: GameState) -> list[GameState] | None:
    suspend_branches: list[GameState] | None = None
    if state.phase == Phase.UNTAP:
        # An extra turn (Time Walk / Time Vault) takes a full untap/draw/main/combat
        # cycle WITHOUT advancing the turn counter — modelling the tempo gain.
        if state.extra_turns > 0:
            state.extra_turns -= 1
            state.extra_turn_index += 1
            state.emit(f"extra turn (Turn {state.turn} +{state.extra_turn_index})")
        else:
            state.turn += 1
            state.extra_turn_index = 0
        state.reset_turn_counters()
        # Untap restrictions (Winter Orb: ≤1 land while untapped; Winter Moon:
        # ≤1 nonbasic land). Limits are the min across all such permanents, read
        # BEFORE anything untaps (so Winter Orb's own tapped state still counts).
        land_limit = nonbasic_limit = creature_limit = None
        for p in state.battlefield:
            ll = p.impl.untap_land_limit(state, p)
            if ll is not None:
                land_limit = ll if land_limit is None else min(land_limit, ll)
            nl = p.impl.untap_nonbasic_limit(state, p)
            if nl is not None:
                nonbasic_limit = nl if nonbasic_limit is None else min(nonbasic_limit, nl)
            cl = p.impl.untap_creature_limit(state, p)
            if cl is not None:
                creature_limit = cl if creature_limit is None else min(creature_limit, cl)
        lands_up = nonbasic_up = creatures_up = 0
        for perm in state.battlefield:
            perm.summoning_sick = False
            # Basalt Monolith & co. don't untap during the untap step.
            if perm.impl.skips_untap(state, perm):
                continue
            # A static effect elsewhere can hold a permanent tapped (Meekstone:
            # creatures with power 3+ don't untap).
            if any(o.impl.prevents_untap(state, o, perm) for o in state.battlefield):
                continue
            # Smoke: untap at most N creatures.
            if perm.is_creature_now and perm.tapped and creature_limit is not None:
                if creatures_up >= creature_limit:
                    continue
                perm.tapped = False
                creatures_up += 1
                continue
            if perm.is_land and perm.tapped and (land_limit is not None or nonbasic_limit is not None):
                is_basic = "basic" in perm.type_line.lower()
                if land_limit is not None and lands_up >= land_limit:
                    continue
                if not is_basic and nonbasic_limit is not None and nonbasic_up >= nonbasic_limit:
                    continue
                perm.tapped = False
                lands_up += 1
                if not is_basic:
                    nonbasic_up += 1
            else:
                perm.tapped = False
        state.mana_pool.clear()
    elif state.phase == Phase.UPKEEP:
        # "Draw a card at the beginning of the next turn's upkeep" (baubles).
        if state.pending_upkeep_draws:
            n = state.pending_upkeep_draws
            state.pending_upkeep_draws = 0
            state.emit(f"delayed upkeep draw: draw {n} card(s)")
            state.draw(n)
        # Graveyard-based upkeep abilities (Nether Shadow returns itself).
        from ..cards import build_card
        for i, card in enumerate(list(state.graveyard)):
            build_card(card).graveyard_upkeep(state, card, i)
        suspend_branches = _resolve_suspend(state)
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
            elif perm.counters.get("end_step_exile"):
                # "Exile it at the beginning of the next end step" (Corpse Dance,
                # Shallow Grave — temporary reanimation).
                state.emit(f"{perm.name}: exile at beginning of end step")
                state.leaves_battlefield(perm, "exile")
            elif perm.counters.get("end_step_destroy") and perm.turn_flags.get("attacked"):
                # "At the beginning of the next end step, destroy it if it
                # attacked this turn" (Berserk).
                state.emit(f"{perm.name}: destroyed at end step (attacked this turn)")
                state.leaves_battlefield(perm, "graveyard", reason="destroy")
        # "At the beginning of the next end step, untap up to N lands" (Teferi,
        # Hero of Dominaria +1). Untap the tapped lands (up to N) so the mana is
        # available for the end-step instant-speed window / next turn.
        if state.untap_lands_end_step:
            n = state.untap_lands_end_step
            state.untap_lands_end_step = 0
            untapped = []
            for perm in state.battlefield:
                if n <= 0:
                    break
                if perm.is_land and perm.tapped:
                    perm.tapped = False
                    untapped.append(perm.name)
                    n -= 1
            if untapped:
                state.emit(f"Teferi, Hero of Dominaria: untap {', '.join(untapped)}")
    elif state.phase == Phase.CLEANUP:
        for perm in state.battlefield:
            perm.temp_power = 0
            perm.temp_toughness = 0
            perm.temp_keywords.clear()
            perm.removed_keywords_eot.clear()  # end-of-turn keyword removals end
            # An until-end-of-turn colour override ends now.
            if perm.color_override_eot:
                perm.color_override = None
                perm.color_override_eot = False
            # Man-land animation ends at cleanup — but a PERMANENT animation
            # (Ba Sing Se's earthbend) stays a creature.
            if perm.becomes is not None and not perm.becomes.get("permanent"):
                # A temporary full copy (Shifting Woodland) restores its
                # original card + impl; a plain man-land just drops `becomes`.
                if "orig_card" in perm.becomes:
                    perm.card = perm.becomes["orig_card"]
                    perm.impl = perm.becomes["orig_impl"]
                perm.becomes = None
            perm.damage = 0
        state.check_deaths()

    # "At the beginning of <phase>" triggers (upkeep, combat, end step...).
    # These may BRANCH (e.g. Emperor of Bones' begin-of-combat "exile up to one
    # target from a graveyard"): settle() then returns several branch states,
    # which _advance hands back to the search frontier. A suspend that resolved
    # this upkeep may already have produced branches — queue the phase triggers on
    # each and settle them together.
    targets = suspend_branches if suspend_branches is not None else [state]
    for b in targets:
        b.queue_phase_triggers(b.phase)
    return state.settle(suspend_branches)


def _goto_next_phase(state: GameState) -> None:
    state.mana_pool.clear()
    # An additional combat phase (Fear of Missing Out): after END_COMBAT, loop
    # back to BEGIN_COMBAT instead of moving on to the postcombat main phase.
    # `attackers` was already cleared by the END_COMBAT step entry, so a fresh
    # combat can be declared (with whatever creatures are untapped — e.g. FOMO's
    # delirium untap target). The rank (turn, phase_index) dips back to combat
    # for this turn; that never trips `max_rank` pruning (a strict > check) and
    # property re-checks are sticky, so time-based timing stays correct.
    if state.phase == Phase.END_COMBAT and state.extra_combats > 0:
        state.extra_combats -= 1
        state.phase = Phase.BEGIN_COMBAT
        return
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


def _is_on_track(state: GameState, ctx: "_SearchContext", satisfied: frozenset[str]) -> bool:
    """Whether EVERY still-pending property already holds in `state` — its board
    condition is met even though a future "at the end of X" deadline hasn't
    formally verified it yet. Evaluated ONCE per decision checkpoint (never per
    frontier push — that was too slow); a property whose code raises simply
    doesn't hold. Used only to ORDER the search, never to mark a property
    satisfied (that stays with `_check_due` at the property's own timing)."""
    pending = [p for p in ctx.properties if p.id not in satisfied]
    if not pending:
        return False
    for p in pending:
        try:
            if not p.evaluate(state):
                return False
        except Exception:
            return False
    return True


def _progress_score(state: GameState, satisfied: frozenset[str]) -> int:
    """Score for best-first search: lower = more promising. Rewards satisfied
    properties first, then board development and cards seen.

    On-track boost: a state flagged `_on_track` (all pending properties already
    hold — see `_is_on_track`) is prioritized, and among on-track states the ones
    further along (nearer the "end of X" deadline) come first, so the search
    commits to driving such a line to its deadline instead of wandering across
    siblings. The boost is smaller than one satisfied property, so it only orders
    among lines with the same satisfied count — it never overrides real
    verification, and it drops as soon as the condition stops holding."""
    base = (
        len(satisfied) * 1_000_000
        + len(state.battlefield) * 1_000
        + state.cards_drawn * 10
        + state.turn
    )
    if getattr(state, "_on_track", False):
        base += 500_000 + state.turn * 100 + phase_index(state.phase)
    return -base


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


def _is_noise_frame(desc: str) -> bool:
    """Bookkeeping frames that shouldn't be chosen as a branch's distinguishing
    detail: mana taps and "(on the stack)" announcements. Two branches that
    differ only in WHICH lands they tapped are not meaningfully different for a
    label — skip past those to the actual effect (the ability, the reveal, ...)."""
    d = desc or ""
    return d.startswith("tap for mana") or d.endswith("(on the stack)")


def _option_details(blist: list[GameState], base_len: int) -> list[str | None]:
    """When one action fans out into several branches, describe what makes each
    branch different: the first MEANINGFUL log message (past the parent's
    `base_len`) at which the branches diverge — e.g. "exchange text boxes with
    X" vs "... Y", two fetch targets, or "Peter Parker's Camera: copy ..." vs
    the plain resolution. Bookkeeping frames (mana taps, "on the stack") are
    skipped so a trivial mana-tap difference doesn't mask the real choice.
    Returns one detail per branch (None when the branches never diverge)."""
    seqs = [[d for fr in b.log[base_len:]
             if not _is_noise_frame(d := fr.get("desc", ""))] for b in blist]
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

    def offer_child(branch, satisfied, parent_node, label, ckind, child_depth,
                    base_len=None):
        """Give a newly created child state its tree node and route it: onto
        the frontier (normal), or into the split collection (during a split
        expansion, children at the collection depth are handed back to the
        caller — for the workers, or for another expansion round — instead of
        being explored here). `base_len` is the parent's log length, so the new
        replay frames (this node's `steps`) can be captured."""
        steps = None
        if base_len is not None:
            steps = [d for fr in branch.log[base_len:] if (d := fr.get("desc"))]
        # Inherit the parent line's on-track flag as a cheap ordering hint (a
        # clone doesn't carry it). It's recomputed accurately when this child is
        # itself reached and checkpointed.
        branch._on_track = getattr(state, "_on_track", False)
        node = ctx.new_tree_node(parent_node, label, branch, satisfied, steps=steps)
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
            adv_base = len(state.log)
            try:
                status, satisfied, branches = _advance(state, ctx, satisfied)
            except Exception as exc:  # a crash while stepping the game forward
                ctx.record_bug(exc, state=state, context=f"advancing @ {state.phase.value}")
                ctx.new_tree_node(node, "⚠ error advancing the game", state, satisfied)
                continue
            # The frames emitted while advancing (phase transitions, upkeep/step
            # triggers resolving) belong to this advance node — record them so the
            # tree exposes them, matching the board replay. Per-branch frames past
            # here are captured on the child nodes (offer_child, below).
            if node is not None and own:
                node.setdefault("steps", []).extend(
                    d for fr in state.log[adv_base:] if (d := fr.get("desc")))
                node["steps"] = node["steps"][:_MAX_NODE_STEPS]
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
                    offer_child(branch, satisfied, node, label, "advance", depth + 1,
                                base_len=len(state.log))
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
        # Evaluate "on track" ONCE here (per decision checkpoint, not per push):
        # if every pending property already holds, this line's continuations are
        # prioritized so the search drives it to its "end of X" deadline.
        state._on_track = _is_on_track(state, ctx, satisfied)
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
                offer_child(branch, satisfied, node, label, ckind, depth + 1,
                            base_len=len(state.log))
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


def _make_face_down(perm, reason: str = "facedown", *, power=None, toughness=None) -> None:
    """Turn a permanent face down: a 2/2 colourless nameless creature. `reason`
    (manifest / morph / megamorph / disguise / cloak / facedown) records HOW it
    was turned down and sets characteristics that differ — disguise and cloak
    make it a 2/2 with ward {2}; the rest are a plain 2/2. An explicit
    power/toughness override (Alter card > Set power/toughness) REPLACES the 2/2
    body, and any +1/+1 counters still stack on top (via effective P/T). Its
    printed characteristics are hidden; `becomes` supplies the body."""
    perm.face_down = True
    perm.becomes = {
        "type_line": "Creature",
        "power": 2 if power is None else int(power),
        "toughness": 2 if toughness is None else int(toughness),
        "permanent": True,
    }
    perm.color_override = []
    if reason in ("disguise", "cloak"):
        perm.extra_keywords.add("ward")


def _build_fixed_variant(base_state: GameState, fixed: dict, seed: int) -> GameState:
    """Build the starting state for a Fixed-config run: place named deck cards
    into the battlefield / hand / graveyard / exile, set life totals, mana pool,
    storm count, turn and phase; the remaining deck cards form the library
    (shuffled by `seed`). Battlefield permanents are not summoning-sick and fire
    NO enter-the-battlefield triggers (they are already in play)."""
    rng = random.Random(seed)
    variant = base_state.clone()
    lib_pool = list(base_state.library)          # deck cards
    cmd_pool = list(base_state.command_zone)     # commander(s)
    sb_pool = list(base_state.sideboard)         # "outside the game" (the companion)

    def take(name: str):
        # The companion is in the sideboard, so the editor can place it into a game
        # area; a taken sideboard card leaves the wish pool (set below).
        for pool in (lib_pool, cmd_pool, sb_pool):
            for i, c in enumerate(pool):
                if c.name == name:
                    return pool.pop(i)
        return None

    variant.hand, variant.battlefield = [], []
    variant.graveyard, variant.exile = [], []
    variant.mana_pool.clear()

    # `placed[i]` is the permanent built for battlefield spec i (or None if the
    # card could not be taken), so attachment indices line up with the spec.
    specs = list(fixed.get("battlefield", []))
    placed: list = []
    for spec in specs:
        name = spec.get("name") if isinstance(spec, dict) else spec
        is_token = isinstance(spec, dict) and spec.get("token")
        copy_of = spec.get("copy_of") if isinstance(spec, dict) else None
        added = spec.get("added") if isinstance(spec, dict) else None
        if is_token and not copy_of:
            # A plain token: created fresh (not a deck card); make_token already
            # puts it on the battlefield.
            perm = variant.make_token(
                name, int(spec.get("power") or 0), int(spec.get("toughness") or 0),
                spec.get("type_line") or "Token", text=spec.get("text") or "",
                colors=spec.get("colors") or [])
        elif copy_of or added:
            # Build the permanent from the card data carried in the spec, so
            # build_card() picks up that card's implementation BY NAME (full copy
            # with abilities for an implemented card; a vanilla body otherwise).
            # A COPY token (is_token) or an ADDED arbitrary card (not a deck card,
            # nontoken — may even be a nonpermanent, placed for sandbox testing).
            from ..deck.models import CardData
            pw, tf = spec.get("power"), spec.get("toughness")
            built = CardData(
                name=copy_of or name,
                type_line=spec.get("type_line") or ("Token" if is_token else ""),
                power=None if pw is None else str(pw),
                toughness=None if tf is None else str(tf),
                colors=list(spec.get("colors") or []),
                oracle_text=spec.get("oracle_text") or spec.get("text") or "",
                mana_cost=spec.get("mana_cost") or "",
                cmc=float(spec.get("cmc") or 0),
                keywords=list(spec.get("keywords") or []),
            )
            perm = variant.put_on_battlefield(built, token=bool(is_token), fire_etb=False)
            if copy_of:
                perm.is_copy = True
        else:
            card = take(name)
            if card is None:
                placed.append(None)
                continue
            perm = make_permanent(variant, card,
                                  is_commander=card.name in base_state.commander_names)
            variant.battlefield.append(perm)
        # Not summoning-sick by default; the editor can mark "arrived this turn".
        perm.summoning_sick = bool(spec.get("sick")) if isinstance(spec, dict) else False
        if isinstance(spec, dict):
            perm.tapped = bool(spec.get("tapped"))
            if not is_token:
                perm.transformed = bool(spec.get("transformed"))  # DFC back face
            # Counters OVERRIDE the natural enters-with counters for the kinds
            # given (a planeswalker keeps its base loyalty unless set here).
            for kind, n in (spec.get("counters") or {}).items():
                if n:
                    perm.counters[kind] = int(n)
                else:
                    perm.counters.pop(kind, None)
            # Granted keywords: permanent (extra_keywords) vs until end of turn
            # (temp_keywords) — separate per-keyword lists.
            for kw in (spec.get("granted") or []):
                perm.extra_keywords.add(str(kw).lower())
            for kw in (spec.get("granted_eot") or []):
                perm.temp_keywords.add(str(kw).lower())
            for kw in (spec.get("removed_keywords") or []):
                perm.removed_keywords.add(str(kw).lower())
            for kw in (spec.get("removed_keywords_eot") or []):
                perm.removed_keywords_eot.add(str(kw).lower())
            # Editor "Alter card": override P/T, creature subtypes ("Set creature
            # types") and/or add the Creature card type ("Make a creature"). These
            # fold into a single `becomes` animation. Each contributing change has
            # its own "until end of turn" flag; the animation is temporary if ANY
            # of them is EOT (they share one `becomes`), permanent otherwise.
            sp, st_ = spec.get("set_power"), spec.get("set_toughness")
            set_ctypes = spec.get("set_creature_types")
            mk = spec.get("make_creature")
            if (mk or sp is not None or st_ is not None or set_ctypes is not None):
                head, _sep, tail = perm.type_line.partition("—")
                left = head.strip()
                if mk and "creature" not in left.lower():
                    left = (left + " Creature").strip()
                right = " ".join(set_ctypes) if set_ctypes is not None else tail.strip()
                tl = left + (f" — {right}" if right else "")
                base_p = perm.base_power() if perm.is_creature_now else 0
                base_t = perm.base_toughness() if perm.is_creature_now else 0
                eot = bool(spec.get("make_creature_eot") or spec.get("set_creature_types_eot")
                           or spec.get("set_power_eot") or spec.get("set_toughness_eot"))
                perm.becomes = {
                    "type_line": tl,
                    "power": int(sp) if sp is not None else base_p,
                    "toughness": int(st_) if st_ is not None else base_t,
                    "permanent": not eot,
                }
            if spec.get("face_down"):
                _make_face_down(perm, spec.get("face_down"),
                                power=spec.get("set_power"), toughness=spec.get("set_toughness"))
            # "Set color" override (deck cards; tokens/added cards carry colour in
            # their built CardData). Recolour for BOTH gameplay and display; an EOT
            # override is cleared at cleanup.
            set_colors = spec.get("set_colors")
            if set_colors is not None and not (spec.get("token") or spec.get("added")):
                perm.color_override = list(set_colors)
                perm.color_override_eot = bool(spec.get("set_colors_eot"))
                perm.card = perm.card.model_copy(update={"colors": list(set_colors)})
        placed.append(perm)
    # Resolve attachments (auras/equipment) now that all permanents exist.
    for i, spec in enumerate(specs):
        perm = placed[i]
        if perm is None or not isinstance(spec, dict):
            continue
        host_idx = spec.get("attached_to")
        if host_idx is not None and 0 <= host_idx < len(placed) and placed[host_idx] is not None:
            perm.attached_to = placed[host_idx].uid
    for name in fixed.get("hand", []):
        card = take(name)
        if card is not None:
            variant.hand.append(card)
    for name in fixed.get("graveyard", []):
        card = take(name)
        if card is not None:
            variant.graveyard.append(card)
    # Map each battlefield permanent by the name shown in the editor, so an exile
    # entry may declare it was "exiled with" that permanent.
    placed_by_name = {}
    for i, spec in enumerate(specs):
        if placed[i] is None:
            continue
        nm = spec.get("name") if isinstance(spec, dict) else spec
        placed_by_name.setdefault(nm, placed[i])
    for entry in fixed.get("exile", []):
        # Entry is either a bare name, or {"name", "exiled_with", ...}. An
        # `added` exile entry carries its own card data (the exiled card is not
        # in the deck — e.g. a creature Superior Spider-Man copied from an
        # opponent's graveyard), so it is built from the spec rather than taken.
        if isinstance(entry, str):
            name, host_name, added = entry, None, False
        else:
            name, host_name, added = entry.get("name"), entry.get("exiled_with"), entry.get("added")
        if added:
            from ..deck.models import CardData
            pw, tf = entry.get("power"), entry.get("toughness")
            card = CardData(
                name=name, type_line=entry.get("type_line") or "",
                power=None if pw is None else str(pw),
                toughness=None if tf is None else str(tf),
                colors=list(entry.get("colors") or []),
                oracle_text=entry.get("oracle_text") or "",
                mana_cost=entry.get("mana_cost") or "",
                cmc=float(entry.get("cmc") or 0),
                keywords=list(entry.get("keywords") or []),
            )
        else:
            card = take(name)
        if card is None:
            continue
        variant.exile.append(card)
        host = placed_by_name.get(host_name) if host_name else None
        if host is None and host_name:
            # The chosen exiler is NOT on the battlefield (e.g. an opponent's Aang
            # picked via "Exiled with > Other card…"). Build a PHANTOM source from
            # its implementation (by name) so its exile mechanism still activates —
            # airbend (Aang), playable-from-exile (Gwen/Hoarding/Inti), etc. The
            # phantom gets a NEGATIVE uid so the "source still in play" check in
            # actions treats it as permanently available (it never leaves).
            from ..cards.registry import get_impl
            from ..deck.models import CardData
            impl_cls = get_impl(host_name)
            if impl_cls is not None:
                phantom = Permanent(card=CardData(name=host_name), impl=impl_cls(CardData(name=host_name)),
                                    uid=-(len(variant.exile)))
                host = phantom
        if host is not None:
            # Route it into THAT permanent's exile mechanism (Gwen/Hoarding/Inti →
            # playable from exile; Aang → recast for {2}; Leyline/Parallax → return
            # when it leaves; Superior Spider-Man → he becomes a copy; default →
            # recorded in its exiled_with).
            host.impl.link_exiled_card(variant, host, card)
            variant.exile_source[id(card)] = host.name  # names the exile-zone badge

    # Commanders "removed from any area" are shuffled into the deck: pull them
    # out of the command-zone pool and into the shuffled library remainder.
    for name in fixed.get("commander_removed", []):
        for i, c in enumerate(cmd_pool):
            if c.name == name:
                lib_pool.append(cmd_pool.pop(i))
                break

    # Explicit ordering of the library top (front = top). Each entry is either a
    # card NAME (a KNOWN card at that depth) or the "__unknown__" sentinel (a
    # RANDOM card pinned at that depth), so the player can say e.g. "I know the
    # top card and the 3rd card, the 2nd is unknown". Known cards are reserved
    # first, then the unknown slots are filled from the shuffled remainder; what
    # is left forms the (shuffled) rest below. Only the KNOWN cards are marked
    # known in the library (fake-shuffle keeps them near the top).
    ordered: list = []
    unknown_slots: list[int] = []
    known: list = []
    for entry in fixed.get("library", []):
        if entry == _FC_UNKNOWN:
            unknown_slots.append(len(ordered))
            ordered.append(None)  # placeholder, filled from the pool below
        else:
            card = take(entry)
            if card is not None:
                ordered.append(card)
                known.append(card)
    rng.shuffle(lib_pool)
    for slot in unknown_slots:
        ordered[slot] = lib_pool.pop() if lib_pool else None
    ordered = [c for c in ordered if c is not None]
    variant.library = ordered + lib_pool  # set top (known + filled unknowns), then rest
    variant.command_zone = cmd_pool       # commanders not placed on the battlefield
    variant.sideboard = sb_pool           # wish pool minus any placed sideboard card (companion)
    if known:
        variant.mark_known_in_library(*known)

    variant.life = int(fixed.get("life", 20))
    variant.opponent_life = int(fixed.get("opponent_life", 20))
    variant.opp_life_turn_start = variant.opponent_life  # nothing lost yet this turn
    variant.storm_count = int(fixed.get("storm_count", 0))
    variant.energy = int(fixed.get("energy", 0))
    for sym, n in (fixed.get("mana_pool") or {}).items():
        if n:
            variant.mana_pool.add(sym, int(n))
    variant.turn = max(1, int(fixed.get("turn", 1)))
    try:
        variant.phase = Phase(fixed.get("phase", "precombat_main"))
    except ValueError:
        variant.phase = Phase.PRECOMBAT_MAIN

    # Declared attackers (only meaningful in a combat phase): mark them as
    # attacking so the search resolves combat from here (combat_actions returns
    # [] once state.attackers is set, so the attack is "already declared").
    combat = variant.phase in (Phase.BEGIN_COMBAT, Phase.DECLARE_ATTACKERS,
                               Phase.DECLARE_BLOCKERS, Phase.COMBAT_DAMAGE, Phase.END_COMBAT)
    if combat:
        for i, spec in enumerate(specs):
            perm = placed[i]
            if perm is not None and isinstance(spec, dict) and spec.get("attacking") \
                    and perm.is_creature_now:
                variant.attackers.append(perm.uid)
                perm.turn_flags["attacked"] = 1
                variant.attacked_this_turn = True

    # Commander tax: the commander has already been cast `count` times this game.
    for name, count in (fixed.get("commander_cast") or {}).items():
        count = int(count)
        if count > 0:
            variant.commander_cast_count[name] = count
            variant.commander_cast_this_game = True

    variant.rng_seed = seed  # drives mid-game shuffles
    return variant


def _apply_start_of_game(state: GameState) -> None:
    """Start-of-game replacement effects that depend on the opening hand.

    Gemstone Caverns: if you're on the DRAW (not the starting player) and it's in
    your opening hand, you begin the game with it on the battlefield with a luck
    counter, exiling a card from your hand. On the play it stays a normal land in
    hand. The exiled card is the highest-mana-value one (least useful early)."""
    if state.on_the_play:
        return
    gem = next((c for c in state.hand if c.name == "Gemstone Caverns"), None)
    if gem is None:
        return
    state.hand.remove(gem)
    perm = state.put_on_battlefield(gem, fire_etb=False)
    perm.counters["luck"] = 1
    if state.hand:  # "If you do, exile a card from your hand."
        victim = max(state.hand, key=lambda c: (c.cmc, c.name))
        state.hand.remove(victim)
        state.exile.append(victim)
        state.emit(
            f"Gemstone Caverns: begin in play with a luck counter (on the draw) — "
            f"exile {victim.name}")
    else:
        state.emit("Gemstone Caverns: begin in play with a luck counter (on the draw)")


def _seed_game(
    base_state: GameState,
    properties: list[CompiledProperty],
    config: SimulationConfig,
    game_index: int,
    should_stop: Callable[[], bool] | None = None,
    should_skip: Callable[[], bool] | None = None,
    deadline: float | None = None,
    on_progress: Callable[[int, int, int, float], None] | None = None,
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
                         should_skip=should_skip, instant_speed=config.instant_speed,
                         game_index=game_index, on_progress=on_progress,
                         tree_cap=(_TREE_NODE_CAP if config.save_tree else 1))
    # Root of the recorded search tree: the game before any hand is kept.
    root = {"id": 0, "label": "game", "turn": 0, "phase": "start", "children": [], "success": False, "sat": []}
    ctx.tree_root = root
    ctx.tree_count = 1

    if config.fixed_config:
        # Fixed-config mode: begin from a single, fully-specified state (no
        # opening hand / mulligan branching) and search forward. Only the
        # library (the deck cards left over) varies per game seed.
        variant = _build_fixed_variant(base_state, config.fixed_config,
                                        config.base_seed + game_index)
        hand_names = [c.name for c in variant.hand]
        variant.emit(
            f"fixed config — turn {variant.turn}, {variant.phase.value} · "
            f"life {variant.life}, {variant.mana_pool.total()} mana · hand {hand_names}")
        node = ctx.new_tree_node(
            root, f"fixed config (turn {variant.turn}, {variant.phase.value})", variant)
        if node is not None:
            node["hand"] = hand_names
        items = [(variant, frozenset(), node, "advance", node is not None, 0)]
        ctx.branches_considered += 1
        return ctx, root, items, [(node, hand_names)], list(variant.library)

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
        # Start-of-game replacements that depend on the opening hand (Gemstone
        # Caverns beginning in play on the draw).
        _apply_start_of_game(variant)
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
    winning_hand = (keep_nodes[0][1] if (config.fixed_hand or config.fixed_config)
                    else [c.name for c in shuffled[:7]])
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
        elapsed_s=time.monotonic() - ctx.start_time,
    )


def simulate_game(
    base_state: GameState,
    properties: list[CompiledProperty],
    config: SimulationConfig,
    game_index: int,
    should_stop: Callable[[], bool] | None = None,
    should_skip: Callable[[], bool] | None = None,
    on_game_start: Callable[[int, list], None] | None = None,
    on_progress: Callable[[int, int, int, float], None] | None = None,
) -> GameOutcome:
    ctx, root, items, keep_nodes, shuffled = _seed_game(
        base_state, properties, config, game_index,
        should_stop=should_stop, should_skip=should_skip, on_progress=on_progress)
    if on_game_start is not None:
        # The opening hand is known once the game is seeded — report it so the
        # results table can show a "running" row (with its hand) live.
        hand = keep_nodes[0][1] if keep_nodes else []
        on_game_start(game_index, list(hand))
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


def _worker_init(deck, specs, config: SimulationConfig, stop_event, found_event, progress) -> None:
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
    _WORKER["progress"] = progress  # shared list: live [explored, considered] per part


def _worker_progress(part: int) -> Callable[[int, int, int, float], None]:
    """A progress callback for a subtree worker: writes its running branch counts
    into the shared list at its part's slots (throttled by the ctx to ~1s), so
    the master can report LIVE parallel progress."""
    arr = _WORKER.get("progress")

    def cb(_gi: int, explored: int, considered: int, _el: float) -> None:
        if arr is not None:
            try:
                arr[2 * part] = explored
                arr[2 * part + 1] = considered
            except Exception:  # noqa: BLE001 - progress is best-effort
                pass
    return cb


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
        deadline=deadline, on_progress=_worker_progress(part),
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
    should_skip: Callable[[], bool] | None = None,
    on_game_start: Callable[[int, list], None] | None = None,
    on_progress: Callable[[int, int, int, float], None] | None = None,
    progress_arr=None,
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
        base_state, properties, config, game_index,
        should_stop=should_stop, should_skip=should_skip)
    if on_game_start is not None:
        on_game_start(game_index, list(keep_nodes[0][1] if keep_nodes else []))

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
    if progress_arr is not None:                # zero the live counters for this game
        for _pi in range(len(progress_arr)):
            progress_arr[_pi] = 0
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
    tainted = False
    last_prog = time.monotonic()
    while pending:
        now = time.monotonic()
        # Live in-game progress while the workers churn (every ~1s): sum the
        # workers' shared branch counters. Each worker's count includes the shared
        # shallow prefix, so mirror the final merge (shallow + Σ(worker−shallow)).
        if on_progress is not None and now - last_prog >= 1.0:
            last_prog = now
            expl, cons = ctx.branches_explored, ctx.branches_considered
            if progress_arr is not None:
                we = [progress_arr[2 * p] for p in range(num_parts)]
                wc = [progress_arr[2 * p + 1] for p in range(num_parts)]
                expl = shallow_explored + sum(max(0, x - shallow_explored) for x in we)
                cons = shallow_considered + sum(max(0, x - shallow_considered) for x in wc)
            on_progress(game_index, expl, cons, now - ctx.start_time)
        if should_stop and should_stop():
            # User abort: abandon the game IMMEDIATELY. Its result is discarded
            # (return None), so there is no reason to wait for workers to hand
            # anything back — the old grace period was the main "Stop is slow"
            # delay. Signal them to wind down; the caller kills the pool next.
            stop_event.set()
            return None
        if should_skip and should_skip():
            # Skip THIS game: abandon it instantly as an unsuccessful (timed-out)
            # result and move to the next. Wind the workers down NOW by setting
            # `found_event` (they treat it as "solved, stop searching") — it is
            # cleared at the start of the next game, so the pool stays usable.
            found_event.set()
            ctx.timed_out = True
            le, lc = _live_parallel_counts(progress_arr, num_parts, shallow_explored, shallow_considered)
            ctx.branches_explored = max(ctx.branches_explored, le)
            ctx.branches_considered = max(ctx.branches_considered, lc)
            return _assemble_outcome(ctx, root, keep_nodes, shuffled, config,
                                     game_index, False)
        if now >= hard_deadline:
            tainted = True
            if on_tainted is not None:
                on_tainted()  # stragglers are wedged — pool must be recycled
            break
        done, pending = futures_wait(pending, timeout=0.1)
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
    # Floor the reported counts at what the workers actually explored (from the
    # shared live counters): a tainted game loses the wedged workers' returned
    # results, so the merge above would otherwise undercount to ~the shallow prefix.
    le, lc = _live_parallel_counts(progress_arr, num_parts, shallow_explored, shallow_considered)
    ctx.branches_explored = max(ctx.branches_explored, le)
    ctx.branches_considered = max(ctx.branches_considered, lc)
    return _assemble_outcome(ctx, root, keep_nodes, shuffled, config, game_index, success)


def _live_parallel_counts(progress_arr, num_parts, shallow_e, shallow_c) -> tuple[int, int]:
    """The workers' running branch counts (from the shared list) merged the same
    way the final tally is (shallow prefix once + each worker's own subtrees).
    Used as a FLOOR on the reported counts so a game whose workers were abandoned
    (wedged/tainted — their futures never returned to be merged) still reports the
    exploration it actually did, instead of collapsing to just the shallow count
    (the "live counter hit millions but the final says 10k" bug)."""
    if progress_arr is None:
        return 0, 0
    we = [progress_arr[2 * p] for p in range(num_parts)]
    wc = [progress_arr[2 * p + 1] for p in range(num_parts)]
    return (shallow_e + sum(max(0, x - shallow_e) for x in we),
            shallow_c + sum(max(0, x - shallow_c) for x in wc))


def _new_pool(mp_ctx, workers, deck, specs, config, stop_event, found_event, progress):
    from concurrent.futures import ProcessPoolExecutor

    return ProcessPoolExecutor(
        max_workers=workers, mp_context=mp_ctx, initializer=_worker_init,
        initargs=(deck, specs, config, stop_event, found_event, progress),
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
    should_skip: Callable[[], bool] | None = None,
    on_game_start: Callable[[int, list], None] | None = None,
    on_progress: Callable[[int, int, int, float], None] | None = None,
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

    pool = manager = stop_event = found_event = mp_ctx = specs = progress_arr = None
    if workers > 1 and indices and can_parallel:
        import multiprocessing as mp

        specs = [p.spec for p in properties]
        mp_ctx = mp.get_context("spawn")  # fork is unsafe under a threaded server
        manager = mp_ctx.Manager()
        stop_event = manager.Event()
        found_event = manager.Event()
        # Shared live branch counts per worker part ([explored, considered] × workers),
        # so the master can report parallel progress every ~1s (see _worker_progress).
        progress_arr = manager.list([0] * (2 * workers))
        pool = _new_pool(mp_ctx, workers, deck, specs, config, stop_event, found_event, progress_arr)

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
                        on_tainted=lambda: tainted.__setitem__(0, True),
                        should_skip=should_skip, on_game_start=on_game_start,
                        on_progress=on_progress, progress_arr=progress_arr)
                else:
                    outcome = simulate_game(base_state, properties, config, i,
                                            should_stop=should_stop,
                                            should_skip=should_skip,
                                            on_game_start=on_game_start,
                                            on_progress=on_progress)
            except Exception as exc:  # keep the run alive; report the game as buggy
                outcome = _buggy_outcome(i, exc)
            # A tainted pool has a wedged worker process holding a core hostage:
            # kill it, and (unless the run is ending) spin up a fresh pool so the
            # remaining games keep full parallelism and stay responsive.
            if tainted[0] and pool is not None:
                _terminate_pool(pool)
                pool = (None if (should_stop and should_stop())
                        else _new_pool(mp_ctx, workers, deck, specs, config,
                                       stop_event, found_event, progress_arr))
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
