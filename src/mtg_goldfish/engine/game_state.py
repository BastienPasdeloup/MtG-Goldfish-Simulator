"""Runtime game state for a solitaire game.

`GameState` is the single mutable object the simulator branches over. It is
cloned at every decision point, so it deliberately holds plain, cheap-to-copy
data. `CardData` and card behaviour (`Card`) instances are treated as immutable
and shared between clones; only per-game facts (zones, tapped status, counters)
are copied.

The query helpers near the bottom form the **stable API that compiled property
code runs against** — keep them backwards compatible.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from ..deck.models import CardData, Deck
from .mana import ManaPool
from .phases import Phase, phase_index

if TYPE_CHECKING:  # imported lazily in make_permanent to avoid an import cycle
    from ..cards import Card


class CardList(list):
    """A list of cards returned by the property API (e.g. `cards_put_by`) that
    ALSO answers numeric comparisons by its length. So a property can either
    inspect the cards — `any(c.is_double_faced for c in cards_put_by(...))` —
    or treat the result as a count — `cards_put_by(...) >= 1` — and both read
    naturally. Without this, comparing the list to a number (a very common way
    to phrase "put at least one card") raises `TypeError`, which the search
    silently treats as "property not satisfied" and then explores forever."""

    def _n(self, other):
        return len(self) if isinstance(other, (int, float)) and not isinstance(other, bool) else None

    def __ge__(self, other):
        n = self._n(other); return n >= other if n is not None else super().__ge__(other)

    def __gt__(self, other):
        n = self._n(other); return n > other if n is not None else super().__gt__(other)

    def __le__(self, other):
        n = self._n(other); return n <= other if n is not None else super().__le__(other)

    def __lt__(self, other):
        n = self._n(other); return n < other if n is not None else super().__lt__(other)

    def __eq__(self, other):
        n = self._n(other); return n == other if n is not None else super().__eq__(other)

    def __ne__(self, other):
        n = self._n(other); return n != other if n is not None else super().__ne__(other)

    def __contains__(self, item):
        # `"Tropical Island" in cards_put_by(...)` — a STRING tests membership by
        # card NAME (case-insensitive substring, matching the rest of the API's
        # name handling, and any face of a DFC), so a property can ask "was this
        # named card put into play" without pulling `.name` off each object.
        if isinstance(item, str):
            needle = item.lower()
            for c in self:
                names = [getattr(c, "name", "") or ""]
                names += [getattr(f, "name", "") or "" for f in getattr(c, "faces", []) or []]
                if any(needle in nm.lower() for nm in names):
                    return True
            return False
        return super().__contains__(item)

    __hash__ = None  # lists are unhashable; keep it that way


def _pt(value: str | None) -> int:
    """Parse a power/toughness string to an int; non-numeric (e.g. '*') -> 0."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


#: Rules text for the standard predefined tokens, so token tiles can show a
#: textbox without every `make_token` call site having to spell it out.
#: Call sites may still pass an explicit `text=` to override.
_TOKEN_TEXT: dict[str, str] = {
    "Treasure": "{T}, Sacrifice this token: Add one mana of any color.",
    "Food": "{2}, {T}, Sacrifice this token: You gain 3 life.",
    "Clue": "{2}, Sacrifice this token: Draw a card.",
    "Blood": "{1}, {T}, Discard a card, Sacrifice this token: Draw a card.",
    "Map": "{1}, {T}, Sacrifice this token: Target creature you control explores.",
    "Lander": "{2}, {T}, Sacrifice this token: Search your library for a basic "
              "land card, put it onto the battlefield tapped, then shuffle.",
    "Construct": "This token gets +1/+1 for each artifact you control.",
    "Eldrazi Spawn": "Sacrifice this token: Add {C}.",
    "Powerstone": "{T}: Add {C}. This mana can't be spent to cast a nonartifact spell.",
}


@dataclass
class Permanent:
    card: CardData
    impl: "Card"
    tapped: bool = False
    summoning_sick: bool = True
    is_commander: bool = False
    is_token: bool = False
    transformed: bool = False           # DFC on its back face
    counters: dict[str, int] = field(default_factory=dict)  # '+1/+1', 'fade', 'loyalty', flags...
    turn_flags: dict[str, int] = field(default_factory=dict)  # cleared each untap
    temp_power: int = 0                 # until end of turn
    temp_toughness: int = 0
    temp_keywords: set = field(default_factory=set)  # lowercase, until end of turn
    extra_keywords: set = field(default_factory=set)  # lowercase, permanent grants (not cleared at cleanup)
    # P/T-defining behaviour stays anchored to the permanent even when its text
    # box moves (Deadpool's exchange): when set, dynamic P/T is read from this
    # impl instead of `impl`.
    pt_impl: "Card | None" = None
    damage: int = 0                     # marked damage, cleared at cleanup
    attached_to: int | None = None      # equipment: uid of the equipped creature
    exiled_with: list[CardData] = field(default_factory=list)  # e.g. Parallax Wave
    chosen: str | None = None           # "as ~ enters, choose ..." (Multiversal Passage)
    # Until-end-of-turn "becomes a creature" animation (man-lands: Mishra's
    # Factory, Den of the Bugbear, ...). When set, it overrides the type line
    # and base P/T: {"type_line": str, "power": int, "toughness": int}. Cleared
    # at cleanup. Granted keywords ride on `temp_keywords` as usual.
    becomes: dict | None = None
    # An explicit colour override (Fixed-config "Set color", or a colour-changing
    # effect): a list of "W"/"U"/"B"/"R"/"G" (empty = colourless). None = use the
    # card's printed colours. Read via the `colors` property.
    color_override: list | None = None
    # Face-down (manifest / morph): a 2/2 colourless nameless creature. Its
    # printed name/characteristics are hidden in the viewer; the 2/2 body comes
    # from `becomes`. Turning it face up clears this + becomes + color_override.
    face_down: bool = False
    # This permanent is a COPY of another (token copy / Astral Dragon / Saw in
    # Half / a Fixed-config copy token) — shown with a "copy" badge.
    is_copy: bool = False
    uid: int = 0

    @property
    def colors(self) -> list:
        """Current colours (the override if set, else the card's printed colours)."""
        if self.color_override is not None:
            return list(self.color_override)
        return list(self.card.colors or [])

    # ---- face-aware views ---------------------------------------------------
    @property
    def face(self):
        """The active face's data (falls back to the card itself)."""
        if self.transformed and len(self.card.faces) > 1:
            return self.card.faces[1]
        if self.card.faces:
            return self.card.faces[0]
        return self.card

    @property
    def name(self) -> str:
        return self.face.name or self.card.name

    @property
    def type_line(self) -> str:
        if self.becomes is not None:
            return self.becomes["type_line"]
        return self.face.type_line or self.card.type_line

    @property
    def is_creature_now(self) -> bool:
        return "creature" in self.type_line.split("—")[0].lower()

    @property
    def is_land(self) -> bool:
        # Only the card types (left of the "—") count — this must NOT match a
        # subtype like "Lander" (a Lander token is an Artifact, not a Land).
        return "land" in self.type_line.split("—")[0].lower()

    @property
    def is_lander(self) -> bool:
        return "lander" in self.type_line.lower()

    def base_power(self) -> int:
        if self.becomes is not None and self.becomes.get("power") is not None:
            return int(self.becomes["power"])
        return _pt(self.face.power)

    def base_toughness(self) -> int:
        if self.becomes is not None and self.becomes.get("toughness") is not None:
            return int(self.becomes["toughness"])
        return _pt(self.face.toughness)

    def clone(self) -> "Permanent":
        return Permanent(
            card=self.card,
            impl=self.impl,
            tapped=self.tapped,
            summoning_sick=self.summoning_sick,
            is_commander=self.is_commander,
            is_token=self.is_token,
            transformed=self.transformed,
            counters=dict(self.counters),
            turn_flags=dict(self.turn_flags),
            temp_power=self.temp_power,
            temp_toughness=self.temp_toughness,
            temp_keywords=set(self.temp_keywords),
            extra_keywords=set(self.extra_keywords),
            pt_impl=self.pt_impl,
            damage=self.damage,
            attached_to=self.attached_to,
            exiled_with=list(self.exiled_with),
            chosen=self.chosen,
            becomes=dict(self.becomes) if self.becomes is not None else None,
            color_override=list(self.color_override) if self.color_override is not None else None,
            face_down=self.face_down,
            is_copy=self.is_copy,
            uid=self.uid,
        )


@dataclass(frozen=True)
class StackAbility:
    label: str
    resolve: Callable[["GameState"], list["GameState"] | None]
    source_name: str | None = None
    kind: str = "triggered"
    trigger_text: str | None = None
    ability_text: str | None = None

    @property
    def name(self) -> str:
        return self.label

    def public(self) -> dict:
        return {
            "name": self.label,
            "source_name": self.source_name or self.label,
            "kind": self.kind,
            "trigger": self.trigger_text,
            "ability": self.ability_text or self.label,
        }


@dataclass
class StackResponse:
    """A player's instant-speed response to an ability waiting on the stack —
    e.g. Peter Parker's Camera copying a triggered/activated ability before it
    resolves. `apply(state)` mutates the state in place (pays the cost, taps the
    source, pushes whatever the response puts on the stack) and returns True if
    it actually happened. Offered in the priority window that
    `resolve_triggered_abilities` opens before it resolves the top ability
    (see `GameState._stack_response_branches`)."""

    label: str
    apply: Callable[["GameState"], bool]


def _commander_return_trigger(card: CardData, from_zone: str) -> "StackAbility":
    """A commander that left the battlefield may be returned to the command zone
    by its owner (it briefly passed through `from_zone`). Resolves as a BRANCH:
    one line leaves it in `from_zone`, one moves it to the command zone (noting
    an ``enter_command_zone`` event so properties can see the return)."""
    def resolve(st: "GameState"):
        from ..cards._common import branch_over

        def fn(branch: "GameState", choice: str):
            zone = {"graveyard": branch.graveyard, "exile": branch.exile,
                    "hand": branch.hand}.get(from_zone)
            if choice == "command" and zone is not None and card in zone:
                zone.remove(card)
                branch.command_zone.append(card)
                branch.note_event("enter_command_zone", card.name, is_commander=True)
                branch.emit(f"{card.name}: return to the command zone")
            else:
                branch.emit(f"{card.name}: stay in the {from_zone}")
            return None

        return branch_over(st, ["command", "stay"], fn)

    return StackAbility(
        label=f"{card.name}: return to command zone?",
        resolve=resolve,
        source_name=card.name,
        kind="triggered",
        trigger_text="a commander left play",
    )


@dataclass
class GameState:
    format_id: str = "duel_commander"
    commander_color_identity: tuple[str, ...] = ()

    library: list[CardData] = field(default_factory=list)
    hand: list[CardData] = field(default_factory=list)
    battlefield: list[Permanent] = field(default_factory=list)
    graveyard: list[CardData] = field(default_factory=list)
    exile: list[CardData] = field(default_factory=list)
    command_zone: list[CardData] = field(default_factory=list)
    stack: list[CardData | StackAbility] = field(default_factory=list)
    # Cards exiled "you may play it" (source_uid, card); playable while source lives.
    exile_playable: list[tuple[int, CardData]] = field(default_factory=list)
    # Cards airbended into exile (Aang, Swift Savior): their owner may cast them
    # for {2} for as long as they remain exiled (no source-permanent dependency,
    # unlike exile_playable). Any face of a modal card that has a mana cost may
    # be cast this way. The card objects also live in `exile` (zone display).
    airbend_exile: list[CardData] = field(default_factory=list)
    # id(card) -> name of the permanent it was "exiled with" (Fixed-config setup),
    # so the exile-zone badge names the source regardless of which mechanism the
    # card was routed into (playable / airbend / return-on-leave / copy).
    exile_source: dict = field(default_factory=dict)
    # For a spell cast as a non-front face (e.g. an airbended modal card's back
    # side): id(card) -> face index, so the board viewer shows the face actually
    # being cast on the stack (not the default front). Cleared when the card
    # leaves the stack; keyed by id() (card objects live the whole game).
    stack_face: dict[int, int] = field(default_factory=dict)

    mana_pool: ManaPool = field(default_factory=ManaPool)
    life: int = 20
    opponent_life: int = 20   # phantom opponent for combat damage / Bolt etc.
    # The opponent's life at the START of the current turn, so a property can ask
    # "opponent lost >= N life this turn" (opponent_life_lost_this_turn()).
    opp_life_turn_start: int = 20

    turn: int = 0
    phase: Phase = Phase.UNTAP
    on_the_play: bool = True
    rng_seed: int = 0         # drives deterministic mid-game shuffles
    #: Whether the search explores instant-speed plays (set from the config).
    #: Cards can gate instant-speed-only options on it (e.g. countering your own
    #: spell — see cards._common.counterspell).
    instant_speed: bool = False
    #: Fake shuffling (set from the config): when True, "shuffle" never really
    #: reorders the library — only the cards whose position the player KNOWS
    #: (put on top by a Brainstorm, bottomed by a mulligan/scry...) are pulled
    #: out and reinserted at random spots; everything else keeps its order. The
    #: goal is a near-constant library across all lines of play, so lines that
    #: shuffle differently (e.g. via a fetch land) don't each get a fresh top of
    #: library (which over-evaluates "find X" probabilities).
    fake_shuffle: bool = False
    #: id()s of library cards whose position the player currently knows (see
    #: mark_known_in_library). Cleared by every shuffle, real or fake.
    known_library_ids: set = field(default_factory=set)

    # per-turn counters (reset at untap)
    lands_played_this_turn: int = 0
    bonus_land_drops: int = 0  # one-shot extras this turn (Summer Bloom)
    spells_cast_this_turn: int = 0
    creature_spells_cast_this_turn: int = 0
    noncreature_spells_cast_this_turn: int = 0
    cards_drawn_this_turn: int = 0
    permanent_left_battlefield_this_turn: bool = False  # revolt
    gy_this_turn: list[str] = field(default_factory=list)  # names put in GY this turn
    descended_this_turn: bool = False  # a permanent card entered your GY this turn
    crimes_this_turn: int = 0  # times you committed a crime (targeted an opponent)
    attacked_this_turn: bool = False  # you declared one or more attackers this turn
    left_graveyard_this_turn: bool = False  # a card left your graveyard this turn
    # Moonmist: combat damage by creatures other than Werewolves/Wolves is
    # prevented this turn (checked in deal_combat_damage).
    prevent_nonwolf_combat_damage: bool = False
    # One-shot "cast without paying its mana cost this turn" grants (World War
    # Hulk chapter I). Each: {"colors": tuple|None, "creature": bool, "label": str}
    # — a matching hand spell may be cast for free, consuming the grant. Offered
    # by actions.legal_actions and cleared at the start of your next turn.
    free_casts: list = field(default_factory=list)
    # Teferi, Time Raveler +1: until your next turn you may cast sorcery spells
    # as though they had flash (they become instant-speed in the search's
    # instant-speed windows). Cleared at your next untap.
    cast_sorcery_as_flash: bool = False
    # Teferi, Hero of Dominaria +1: untap up to this many lands at the beginning
    # of the next end step (applied in the CLEANUP/END_STEP step entry).
    untap_lands_end_step: int = 0
    # Additional combat phases still owed this turn (Fear of Missing Out). When
    # leaving END_COMBAT with this > 0, the turn loops back to BEGIN_COMBAT
    # (decrementing) instead of advancing to the postcombat main phase.
    extra_combats: int = 0
    # "This turn, you may play lands and cast spells from your graveyard" and
    # "if a card would be put into your graveyard this turn, exile it instead"
    # (Yawgmoth's Will). Statics on permanents (Emet-Selch // Hades) grant the
    # same via `grants_gy_play_all` / `replaces_gy_with_exile`. Reset each turn.
    gy_play_all: bool = False
    gy_exile_replace: bool = False

    # game-long bookkeeping
    cards_drawn: int = 0
    commander_cast_count: dict[str, int] = field(default_factory=dict)
    # A commander has been cast from the command zone this game. With a partner
    # pair only ONE commander may be cast per game — once one is cast the other
    # is no longer castable (the already-cast one may still be re-cast).
    commander_cast_this_game: bool = False
    storm_count: int = 0
    energy: int = 0           # energy counters (a pool — never emptied by phases)
    attackers: list[int] = field(default_factory=list)  # uids attacking this turn
    _next_uid: int = 1
    log: list[dict] = field(default_factory=list)
    # Game-long EVENT history for property queries ("Nick Fury's ability found a
    # target", "its trigger put 2 lands into play"): dicts with at least
    # {"turn", "kind", "name"}, plus "via"/"via_kind" (the resolving spell or
    # ability that caused the effect) and kind-specific flags. See note_event().
    events: list[dict] = field(default_factory=list)
    # What is currently resolving, as (via_kind, source_name) —
    # ("triggered"|"activated"|"spell"|"land_drop", name). Effects recorded
    # while set are attributed to it. Managed by resolve_triggered_abilities /
    # resolve_to_* / PlayLand and cleared when settle() hands back control.
    resolving: tuple | None = None
    # >0 while a stack ability's resolve() runs. Resolutions are ATOMIC:
    # abilities that trigger during one are queued on the stack but only start
    # resolving once the current resolution completes (nested settle calls
    # defer — see resolve_triggered_abilities / settle).
    _resolve_depth: int = 0
    # Transient: set while a resolution is required to be non-branching
    # (settle_nonbranching — cast/combat-damage triggers, direct battlefield
    # entries). It closes the instant-speed response window so those atomic
    # settles can't fan out (see _stack_response_branches). Never cloned.
    _suppress_responses: bool = False
    # Transient: when a phase-entry triggered ability BRANCHES (e.g. Emperor of
    # Bones' begin-of-combat exile with several graveyard choices), the search
    # fans the branches back onto its frontier as "advance" items. Each branch
    # has already had its step-entry (phase logic + triggers) applied, so this
    # marks the (turn, phase) at which _advance must SKIP re-applying step-entry
    # once, resuming just after the trigger. Never carried across clone().
    _skip_step_entry: tuple | None = None
    # Commander name(s) from the deck (stable — usable whether the commander is
    # in the command zone, on the battlefield or anywhere else).
    commander_names: tuple[str, ...] = ()

    # per-turn HISTORY (never reset — lets properties describe past states, e.g.
    # "a card went to the graveyard on every turn"). Keyed by turn number.
    graveyard_by_turn: dict = field(default_factory=dict)  # turn -> [card names]
    entered_by_turn: dict = field(default_factory=dict)     # turn -> [{name,is_creature,is_land,is_token}]

    # ---- cloning -----------------------------------------------------------
    def clone(self) -> "GameState":
        return GameState(
            format_id=self.format_id,
            commander_color_identity=self.commander_color_identity,
            library=list(self.library),
            hand=list(self.hand),
            battlefield=[p.clone() for p in self.battlefield],
            graveyard=list(self.graveyard),
            exile=list(self.exile),
            command_zone=list(self.command_zone),
            stack=list(self.stack),
            exile_playable=list(self.exile_playable),
            airbend_exile=list(self.airbend_exile),
            exile_source=dict(self.exile_source),
            stack_face=dict(self.stack_face),
            mana_pool=self.mana_pool.copy(),
            life=self.life,
            opponent_life=self.opponent_life,
            opp_life_turn_start=self.opp_life_turn_start,
            turn=self.turn,
            phase=self.phase,
            on_the_play=self.on_the_play,
            rng_seed=self.rng_seed,
            instant_speed=self.instant_speed,
            fake_shuffle=self.fake_shuffle,
            known_library_ids=set(self.known_library_ids),
            lands_played_this_turn=self.lands_played_this_turn,
            bonus_land_drops=self.bonus_land_drops,
            spells_cast_this_turn=self.spells_cast_this_turn,
            creature_spells_cast_this_turn=self.creature_spells_cast_this_turn,
            noncreature_spells_cast_this_turn=self.noncreature_spells_cast_this_turn,
            cards_drawn_this_turn=self.cards_drawn_this_turn,
            permanent_left_battlefield_this_turn=self.permanent_left_battlefield_this_turn,
            gy_this_turn=list(self.gy_this_turn),
            descended_this_turn=self.descended_this_turn,
            crimes_this_turn=self.crimes_this_turn,
            attacked_this_turn=self.attacked_this_turn,
            left_graveyard_this_turn=self.left_graveyard_this_turn,
            prevent_nonwolf_combat_damage=self.prevent_nonwolf_combat_damage,
            free_casts=[dict(g) for g in self.free_casts],
            cast_sorcery_as_flash=self.cast_sorcery_as_flash,
            untap_lands_end_step=self.untap_lands_end_step,
            extra_combats=self.extra_combats,
            gy_play_all=self.gy_play_all,
            gy_exile_replace=self.gy_exile_replace,
            cards_drawn=self.cards_drawn,
            commander_cast_count=dict(self.commander_cast_count),
            commander_cast_this_game=self.commander_cast_this_game,
            storm_count=self.storm_count,
            energy=self.energy,
            attackers=list(self.attackers),
            _next_uid=self._next_uid,
            log=list(self.log),
            events=list(self.events),  # entries are append-only, never mutated
            resolving=self.resolving,
            _resolve_depth=self._resolve_depth,
            commander_names=self.commander_names,
            graveyard_by_turn={t: list(v) for t, v in self.graveyard_by_turn.items()},
            entered_by_turn={t: [dict(e) for e in v] for t, v in self.entered_by_turn.items()},
        )

    # ---- helpers -----------------------------------------------------------
    def new_uid(self) -> int:
        uid = self._next_uid
        self._next_uid += 1
        return uid

    def find_permanent(self, uid: int) -> Permanent | None:
        for p in self.battlefield:
            if p.uid == uid:
                return p
        return None

    def emit(self, message: str) -> None:
        """Append a log *frame*: a description plus a compact board snapshot,
        so the winning line can be replayed graphically."""
        frame = {"desc": message}
        frame.update(self.snapshot())
        self.log.append(frame)

    def push_triggered_abilities(self, abilities: list[StackAbility]) -> None:
        """Push abilities in the order they should resolve."""
        for ability in reversed(abilities):
            self.stack.append(ability)
            self.emit(f"{ability.name} (on the stack)")

    def resolve_triggered_abilities(self) -> list["GameState"] | None:
        # Resolutions are ATOMIC: while an ability is resolving, anything that
        # triggers is queued on the stack but does NOT start resolving — it
        # extends the pending work that the OUTER loop picks up once the
        # current resolution has fully completed.
        if self._resolve_depth > 0:
            return None
        branched = False
        states = [self]
        while True:
            progressed = False
            next_states: list[GameState] = []
            for state in states:
                top = state.stack[-1] if state.stack else None
                if not isinstance(top, StackAbility):
                    next_states.append(state)
                    continue
                progressed = True
                # Priority window: before `top` resolves, let the player respond
                # at instant speed (e.g. Peter Parker's Camera copying it). Each
                # response is its own branch that acts and then re-enters the loop
                # with what it put on the stack now on top; THIS state still goes
                # on to resolve `top` (the "decline to respond" line).
                responders = state._stack_response_branches(top)
                if responders:
                    branched = True
                    next_states.extend(responders)
                ability = state.stack.pop()
                if ability.kind == "triggered":
                    state.note_event("trigger_resolved", ability.source_name or ability.label,
                                     detail=ability.label)
                # Attribute every effect of this resolution (permanents put
                # into play, cards drawn...) to the resolving ability, and mark
                # the resolution ATOMIC (nested settle calls defer; queued
                # triggers resolve on a later iteration of THIS loop).
                prev_resolving = state.resolving
                state.resolving = (ability.kind, ability.source_name or ability.label)
                state._resolve_depth += 1
                # The ability's effects apply the moment it resolves: pop it,
                # run the effect, and let the effect's own emit be the single
                # replay frame (stack popped + effects applied together). Only
                # if the effect emitted nothing do we add a fallback frame.
                base_len = len(state.log)
                branches = ability.resolve(state)
                if branches is None:
                    state._resolve_depth = 0
                    state.resolving = prev_resolving
                    if len(state.log) == base_len:
                        state.emit(f"{ability.name} resolves")
                    state.check_deaths()
                    next_states.append(state)
                    continue
                branched = True
                for branch in branches:
                    branch._resolve_depth = 0  # clones carried the +1
                    branch.resolving = prev_resolving
                    if len(branch.log) == base_len:
                        branch.emit(f"{ability.name} resolves")
                    branch.check_deaths()
                    next_states.append(branch)
            states = next_states
            if not progressed:
                break
        return states if branched else None

    def _stack_response_branches(self, top) -> list["GameState"]:
        """Priority window opened while `top` (a triggered/activated ability)
        waits on the stack: gather every instant-speed response any permanent can
        make to it (Peter Parker's Camera copying it, a future stifle, ...) and
        return ONE fully-applied branch state per response — the cost already
        paid and the response already on the stack. Returns [] when nothing can
        (or wants to) respond.

        Only opens under instant-speed exploration (`instant_speed`), so ordinary
        games add no branching. Each response taps/consumes its source, so the
        branching is naturally bounded (a source responds at most once per line)."""
        if self._suppress_responses:
            return []
        if not self.instant_speed or not isinstance(top, StackAbility):
            return []
        if top.kind not in ("triggered", "activated"):
            return []
        branches: list[GameState] = []
        for perm in list(self.battlefield):
            for resp in perm.impl.stack_response_actions(self, perm):
                child = self.clone()
                if resp.apply(child):
                    branches.append(child)
        return branches

    def settle(self, branches: list["GameState"] | None = None) -> list["GameState"] | None:
        # Called from inside an atomic resolution (e.g. put_on_battlefield with
        # fire_etb=True in card code): defer — the queued abilities stay on the
        # stack and resolve once the current resolution completes. The
        # `resolving` context must survive, so no clearing here.
        if self._resolve_depth > 0:
            return branches
        states = branches or [self]
        branched = branches is not None
        out: list[GameState] = []
        for state in states:
            resolved = state.resolve_triggered_abilities()
            if resolved is None:
                state.check_deaths()
                out.append(state)
            else:
                branched = True
                out.extend(resolved)
        # Control returns to the search: nothing is resolving anymore (clears
        # the "spell"/"land_drop" contexts set by resolve_to_* / PlayLand).
        for state in out:
            state.resolving = None
        return out if branched else None

    def settle_nonbranching(self, context: str) -> None:
        # This resolution must not fan out, so close the instant-speed response
        # window for its duration (a Camera-style copy would otherwise branch it).
        prev = self._suppress_responses
        self._suppress_responses = True
        try:
            branches = self.settle()
        finally:
            self._suppress_responses = prev
        if branches is not None:
            raise RuntimeError(f"Branching triggered abilities are unsupported during {context}")

    def reset_turn_counters(self) -> None:
        self.lands_played_this_turn = 0
        self.bonus_land_drops = 0
        self.spells_cast_this_turn = 0
        self.creature_spells_cast_this_turn = 0
        self.noncreature_spells_cast_this_turn = 0
        self.cards_drawn_this_turn = 0
        self.permanent_left_battlefield_this_turn = False
        self.gy_this_turn.clear()
        self.descended_this_turn = False
        self.crimes_this_turn = 0
        self.attacked_this_turn = False
        self.left_graveyard_this_turn = False
        self.prevent_nonwolf_combat_damage = False
        self.free_casts = []
        self.cast_sorcery_as_flash = False
        self.untap_lands_end_step = 0
        self.extra_combats = 0
        self.gy_play_all = False
        self.gy_exile_replace = False
        self.storm_count = 0            # storm counts spells cast THIS turn
        self.opp_life_turn_start = self.opponent_life
        for p in self.battlefield:
            p.turn_flags.clear()

    def opponent_life_lost_this_turn(self) -> int:
        """How much life the opponent has lost since the start of this turn
        (combat damage, burn, drain, ...). Zero if they didn't lose any."""
        return max(0, self.opp_life_turn_start - self.opponent_life)

    def graveyard_plays_enabled(self) -> bool:
        """You may play lands / cast spells from your graveyard this turn
        (Yawgmoth's Will, or a static like Emet-Selch // Hades)."""
        return self.gy_play_all or any(
            p.impl.grants_gy_play_all_perm(p) for p in self.battlefield)

    def exile_replaces_graveyard(self) -> bool:
        """A card that would be put into your graveyard is exiled instead
        (Yawgmoth's Will, Emet-Selch // Hades, Valgavoth for opponents)."""
        return self.gy_exile_replace or any(
            p.impl.replaces_gy_with_exile_perm(p) for p in self.battlefield)

    def mill(self, n: int) -> None:
        """Put the top n cards of the library into the graveyard."""
        milled = []
        for _ in range(n):
            if not self.library:
                break
            card = self.library.pop(0)
            self.to_graveyard(card)
            milled.append(card.name)
        if milled:
            self.emit(f"mill {len(milled)}: {', '.join(milled)}")

    def max_land_drops(self) -> int:
        """Land plays allowed this turn: 1 + one-shot bonuses (Summer Bloom)
        + battlefield statics (Exploration, Icetill Explorer)."""
        return 1 + self.bonus_land_drops + sum(
            p.impl.extra_land_drops(self, p) for p in self.battlefield
        )

    def apply_entry_statics(self, entering: Permanent) -> None:
        """Apply immediate entry-replacement statics (e.g. Spelunking / Horizon
        Explorer's "lands you control enter untapped") to `entering`.

        Idempotent — the untap checks the permanent's current tapped state, so
        re-applying is a no-op. Called right before the frame that first shows
        the permanent (in `put_on_battlefield` and when a land is played), so a
        permanent that should enter untapped is shown untapped from the start
        and never flashes tapped-then-untapped in the replay."""
        for perm in list(self.battlefield):
            if perm is not entering and perm in self.battlefield:
                perm.impl.on_other_etb_immediate(self, perm, entering)

    def queue_entry_triggers(self, entering: list[Permanent]) -> None:
        """Apply immediate entry statics, then put all ETB abilities on the stack.

        `entering` may contain multiple permanents that entered simultaneously.
        """
        for ent in entering:
            self.apply_entry_statics(ent)

        abilities: list[StackAbility] = []
        for ent in entering:
            for perm in list(self.battlefield):
                if perm is not ent and perm in self.battlefield:
                    abilities.extend(perm.impl.other_etb_stack_items(self, perm, ent))
        for ent in entering:
            live = self.find_permanent(ent.uid)
            if live is not None:
                abilities.extend(live.impl.etb_stack_items(self, live))
        self.push_triggered_abilities(abilities)

    def fire_other_etb(self, entering: Permanent) -> None:
        """Backward-compatible single-entry wrapper for ETB trigger queuing."""
        self.queue_entry_triggers([entering])

    def queue_phase_triggers(self, phase) -> None:
        abilities: list[StackAbility] = []
        for perm in list(self.battlefield):
            abilities.extend(perm.impl.phase_stack_items(self, perm, phase))
        self.push_triggered_abilities(abilities)

    def queue_draw_triggers(self, nth_this_turn: int) -> None:
        abilities: list[StackAbility] = []
        for perm in list(self.battlefield):
            abilities.extend(perm.impl.draw_stack_items(self, perm, nth_this_turn))
        self.push_triggered_abilities(abilities)

    def queue_cast_triggers(self, card: CardData) -> None:
        abilities: list[StackAbility] = []
        for perm in list(self.battlefield):
            abilities.extend(perm.impl.cast_other_stack_items(self, perm, card))
        self.push_triggered_abilities(abilities)

    def queue_attack_triggers(self, perm: Permanent) -> None:
        self.push_triggered_abilities(perm.impl.attack_stack_items(self, perm))

    def queue_combat_damage_triggers(self, perm: Permanent, damage: int) -> None:
        self.push_triggered_abilities(perm.impl.combat_damage_stack_items(self, perm, damage))

    def queue_leave_triggers(self, perm: Permanent) -> None:
        self.push_triggered_abilities(perm.impl.leave_stack_items(self, perm))

    def queue_equipped_died_triggers(self, perm: Permanent) -> None:
        self.push_triggered_abilities(perm.impl.equipped_died_stack_items(self, perm))

    def to_graveyard(self, card: CardData) -> None:
        # Replacement: "if a card would be put into your graveyard, exile it
        # instead" (Yawgmoth's Will / Emet-Selch // Hades). Prevents casting the
        # same graveyard card twice (it leaves the graveyard for good).
        if self.exile_replaces_graveyard():
            self.exile.append(card)
            return
        self.graveyard.append(card)
        self.gy_this_turn.append(card.name)
        self.graveyard_by_turn.setdefault(self.turn, []).append(card.name)
        # Descend: a permanent card was put into your graveyard from anywhere.
        if card.is_permanent:
            self.descended_this_turn = True

    def note_crime(self, n: int = 1) -> None:
        """You committed a crime (targeted an opponent, something they control,
        or a card in their graveyard). Card effects that key off crimes
        (Forsaken Miner) read `crimes_this_turn`."""
        self.crimes_this_turn += n

    def leave_graveyard(self, card: CardData) -> None:
        """Remove a card from your graveyard (reanimation, escape, aftermath...),
        setting the 'a card left your graveyard this turn' flag (Gau)."""
        if card in self.graveyard:
            self.graveyard.remove(card)
        self.left_graveyard_this_turn = True

    def discard(self, card: CardData) -> None:
        """Discard `card` from hand: move it to the graveyard and fire the
        'whenever you discard' watchers (Inti). Batched discards should call
        once per card."""
        if card in self.hand:
            self.hand.remove(card)
        self.to_graveyard(card)
        self.emit(f"discard {card.name}")
        items: list[StackAbility] = []
        for perm in list(self.battlefield):
            items.extend(perm.impl.discard_stack_items(self, perm, 1))
        self.push_triggered_abilities(items)

    # ---- drawing (fires draw triggers) --------------------------------------
    def draw(self, n: int = 1) -> None:
        for _ in range(n):
            if not self.library:
                return
            card = self.library.pop(0)
            self.hand.append(card)
            self.cards_drawn += 1
            self.cards_drawn_this_turn += 1
            self.note_event("draw", card.name, card=card)  # attributed to the resolving effect
            nth = self.cards_drawn_this_turn
            self.queue_draw_triggers(nth)

    def damage_opponent(self, amount: int) -> int:
        """Deal `amount` NONCOMBAT damage to the opponent, applying any 'a source
        you control dealing noncombat damage to an opponent deals +N instead'
        amplifiers on the battlefield (Torture Pit). Returns the amount actually
        dealt. Card code should call this instead of `opponent_life -= n` for any
        NONCOMBAT damage (burn, death triggers, pingers) so amplifiers apply;
        combat damage stays in deal_combat_damage (a different replacement)."""
        dealt = amount
        if amount > 0:
            dealt += sum(p.impl.noncombat_damage_bonus(self, p) for p in self.battlefield)
        self.opponent_life -= dealt
        return dealt

    # ---- library search / shuffle -------------------------------------------
    def mark_known_in_library(self, *cards) -> None:
        """Record that the player knows WHERE these library cards sit (put on
        top by a Brainstorm/tutor, kept on top by a scry/surveil, bottomed by a
        mulligan...). With fake shuffling on, a "shuffle" reinserts exactly
        these cards at random spots and leaves the rest of the library in
        order. Identity-based: duplicate copies of a card share one CardData
        object, so marking one marks them all — harmless, since identical
        copies are interchangeable."""
        for c in cards:
            self.known_library_ids.add(id(c))

    def shuffle_library(self) -> None:
        """Deterministic per branch: seeded by game seed + uid counter.

        With `fake_shuffle` on, the library is NOT reordered: only the cards
        whose position the player knows (see mark_known_in_library) are pulled
        out and reinserted at random places — after a real shuffle the player
        wouldn't know where they are, so they must move — while every other
        card keeps its relative order. This keeps the library near-constant
        across the lines of play of a game."""
        rng = random.Random(self.rng_seed * 1_000_003 + self._next_uid)
        self._next_uid += 1
        if self.fake_shuffle:
            if self.known_library_ids:
                known = [c for c in self.library if id(c) in self.known_library_ids]
                rest = [c for c in self.library if id(c) not in self.known_library_ids]
                for c in known:
                    rest.insert(rng.randrange(len(rest) + 1), c)
                self.library = rest
            self.known_library_ids.clear()
            return
        rng.shuffle(self.library)
        self.known_library_ids.clear()  # nobody knows anything after a real shuffle

    def search_library(self, pred) -> list[CardData]:
        """Distinct-by-name candidates matching `pred` (branch choices)."""
        seen: set[str] = set()
        out: list[CardData] = []
        for c in self.library:
            if c.name not in seen and pred(c):
                seen.add(c.name)
                out.append(c)
        return out

    def take_from_library(self, card: CardData) -> None:
        self.library.remove(card)

    # ---- battlefield mutation ------------------------------------------------
    def put_on_battlefield(
        self, card: CardData, *, is_commander: bool = False,
        tapped: bool | None = None, token: bool = False, fire_etb: bool = True,
        announce: str | None = None, transformed: bool = False,
    ) -> Permanent:
        perm = make_permanent(self, card, is_commander=is_commander, token=token)
        # A modal DFC entering on its BACK face (an MDFC land played as your land
        # drop): flip it BEFORE recording the entry so its name / is_land / the
        # entered_by_turn + enter_battlefield event all reflect the back face.
        if transformed:
            perm.transformed = True
        if tapped is not None:
            perm.tapped = tapped
        self.battlefield.append(perm)
        self.entered_by_turn.setdefault(self.turn, []).append({
            "name": perm.name,
            "is_creature": perm.is_creature_now,
            "is_land": perm.is_land,
            "is_token": perm.is_token,
        })
        # Attributed effect event: which spell/ability put this into play. The
        # card object rides along (immutable, never serialized) so properties
        # can test any characteristic of what entered (.faces, .cmc, ...).
        self.note_event("enter_battlefield", perm.name,
                        is_land=perm.is_land, is_creature=perm.is_creature_now,
                        is_token=perm.is_token, card=perm.card)
        # Settle "enters untapped" replacements (Spelunking, Horizon Explorer)
        # BEFORE announcing, so the entry frame already shows the final tapped
        # state instead of flashing tapped first.
        self.apply_entry_statics(perm)
        # Announce the entry BEFORE any ETB triggers fire, so the replay shows
        # the permanent entering first and its triggers (landfall, Amulet, ...)
        # resolving afterwards — not the other way round.
        if announce:
            if not perm.tapped:
                # A replacement untapped it — don't let the message still say
                # "tapped" over an untapped tile.
                announce = re.sub(r"\btapped\b", "untapped", announce)
            self.emit(announce)
        if fire_etb:
            self.queue_entry_triggers([perm])
            self.settle_nonbranching(f"direct battlefield entry of {perm.name}")
        return perm

    def make_token(
        self, name: str, power: int, toughness: int, type_line: str,
        text: str | None = None, tapped: bool = False, attacking: bool = False,
        colors: list[str] | None = None,
    ) -> Permanent:
        if text is None:
            text = _TOKEN_TEXT.get(name, "")
        data = CardData(name=name, type_line=type_line, power=str(power),
                        toughness=str(toughness), oracle_text=text,
                        colors=list(colors or []))
        perm = self.put_on_battlefield(data, token=True, fire_etb=False)
        # Set tap/attack state BEFORE emitting, so a token created tapped or
        # attacking is depicted that way in its entering frame (no flash of an
        # untapped, non-attacking token first).
        if tapped:
            perm.tapped = True
        if attacking:
            perm.summoning_sick = False
            self.attackers.append(perm.uid)
        self.emit(f"create token {name} ({power}/{toughness})")
        return perm

    def make_token_copy(self, source: Permanent, *, tapped: bool = False,
                        attacking: bool = False, fire_etb: bool = True) -> Permanent:
        """Create a token that's a copy of `source` — its PRINTED characteristics
        (same underlying CardData, so same name, types, P/T, and abilities/impl,
        and its ETB fires). Counters, auras, animations and other continuous
        effects on the original are NOT copied (copiable values only). Used by
        "create a token that's a copy of target creature" effects (Mirrorpool)."""
        perm = self.put_on_battlefield(
            source.card, token=True, fire_etb=fire_etb,
            announce=f"create a token copy of {source.name}")
        perm.is_copy = True
        if tapped:
            perm.tapped = True
        if attacking:
            perm.summoning_sick = False
            self.attackers.append(perm.uid)
        return perm

    def become_copy_until_eot(self, perm: Permanent, src_card: CardData) -> None:
        """`perm` becomes a copy of `src_card` (a permanent card — e.g. one in a
        graveyard) UNTIL END OF TURN: it takes on that card's name, types, P/T
        and abilities (its `impl` is swapped in). Reverts at cleanup — the
        `becomes` marker stashes the originals, and the CLEANUP step restores
        them. Copiable values only (no counters/auras). Used by Shifting
        Woodland's delirium ability. `perm` keeps its identity (not a token)."""
        from ..cards import build_card

        perm.becomes = {
            "type_line": src_card.type_line,   # satisfies the type_line property
            "orig_card": perm.card,            # restored at cleanup
            "orig_impl": perm.impl,
        }
        # Name / P/T / abilities all come from the swapped card+impl (base_power
        # falls through to the swapped card's printed P/T since `becomes` carries
        # no power/toughness override).
        perm.card = src_card.model_copy()
        perm.impl = build_card(perm.card)

    def leaves_battlefield(self, perm: Permanent, to: str = "graveyard",
                           reason: str | None = None) -> None:
        """Move a permanent off the battlefield (graveyard/exile/hand/none).

        `reason` records WHY it left ("dies"/"sacrifice"/"destroy"/None) for the
        death/sacrifice watchers (`on_other_leave`). "Dies" is any move to a
        graveyard (to == "graveyard")."""
        if perm not in self.battlefield:
            return
        self.battlefield.remove(perm)
        self.permanent_left_battlefield_this_turn = True
        is_commander = perm.card.name in self.commander_names
        self.note_event("leave_battlefield", perm.name, to=to, reason=reason,
                        is_land=perm.is_land, is_creature=perm.is_creature_now,
                        is_token=perm.is_token, is_commander=is_commander, card=perm.card)
        # Auras attached to it die; equipment merely unattaches.
        for att in list(self.battlefield):
            if att.attached_to == perm.uid:
                if "aura" in att.type_line.lower():
                    self.leaves_battlefield(att, "graveyard")
                else:
                    att.attached_to = None
        self.queue_leave_triggers(perm)
        # "Whenever another permanent leaves / a creature dies / you sacrifice"
        # watchers on everything still in play (aristocrats: Vraan, Sephiroth...).
        watchers: list[StackAbility] = []
        for w in list(self.battlefield):
            if w.uid == perm.uid:
                continue
            watchers.extend(w.impl.other_leave_stack_items(self, w, perm, to, reason))
        self.push_triggered_abilities(watchers)
        if perm.is_token:
            return  # tokens cease to exist
        if to == "graveyard":
            self.to_graveyard(perm.card)
        elif to == "exile":
            self.exile.append(perm.card)
        elif to == "hand":
            self.hand.append(perm.card)
        elif to == "command":
            self.command_zone.append(perm.card)
        # Commander leaving play (to any zone other than the command zone): its
        # owner MAY return it to the command zone. It has already gone through
        # the destination zone above, so the dies/leave triggers queued just
        # now see it there; a branching triggered ability then models the choice
        # to leave it there or move it to the command zone.
        if is_commander and to in ("graveyard", "exile", "hand"):
            self.push_triggered_abilities([_commander_return_trigger(perm.card, to)])

    def check_deaths(self) -> None:
        """State-based check: creatures with toughness <= 0 or lethal damage die."""
        for perm in list(self.battlefield):
            if not perm.is_creature_now:
                continue
            # A creature with unknown printed toughness (None/'*') and no
            # modifiers has no known toughness to die from — skip it.
            has_mods = (
                perm.temp_toughness or perm.counters.get("+1/+1")
                or (perm.pt_impl or perm.impl).dynamic_toughness(self, perm) is not None
                or any(eq.attached_to == perm.uid for eq in self.battlefield)
            )
            known = str(perm.face.toughness or "").lstrip("-").isdigit()
            if not known and not has_mods and not perm.damage:
                continue
            tough = self.effective_toughness(perm)
            if tough <= 0 or (perm.damage >= tough and tough > 0 and perm.damage > 0):
                # Equipment "equipped creature dies" triggers (e.g. Skullclamp).
                holders = [eq for eq in self.battlefield if eq.attached_to == perm.uid]
                self.emit(f"{perm.name} dies")
                self.leaves_battlefield(perm, "graveyard", reason="dies")
                for eq in holders:
                    self.queue_equipped_died_triggers(eq)

    # ---- effective stats (counters, temp mods, equipment, dynamic P/T) ------
    def effective_power(self, perm: Permanent) -> int:
        base = (perm.pt_impl or perm.impl).dynamic_power(self, perm)
        if base is None:
            base = perm.base_power()
        val = base + perm.counters.get("+1/+1", 0) + perm.temp_power
        for eq in self.battlefield:
            if eq.attached_to == perm.uid:
                val += eq.impl.equip_mod(self, eq)[0]
        return val

    def effective_toughness(self, perm: Permanent) -> int:
        base = (perm.pt_impl or perm.impl).dynamic_toughness(self, perm)
        if base is None:
            base = perm.base_toughness()
        val = base + perm.counters.get("+1/+1", 0) + perm.temp_toughness
        for eq in self.battlefield:
            if eq.attached_to == perm.uid:
                val += eq.impl.equip_mod(self, eq)[1]
        return val

    def has_keyword(self, perm: Permanent, kw: str) -> bool:
        k = kw.lower()
        return (k in (x.lower() for x in perm.card.keywords)
                or k in perm.temp_keywords or k in perm.extra_keywords)

    # ---- energy (a pool: gained/spent, never emptied by phases) -------------
    def add_energy(self, n: int) -> None:
        self.energy += n
        self.emit(f"gain {n} energy ({{E}}×{self.energy} total)")

    def pay_energy(self, n: int) -> bool:
        if self.energy < n:
            return False
        self.energy -= n
        return True

    # ---- game events (ability / spell outcomes) -----------------------------
    def note_event(self, kind: str, name: str, detail: str | None = None, **extra) -> None:
        """Record a game event for property queries. Kinds noted by the engine:
        "cast" (a spell was cast — put on the stack — from hand/command/exile/
        graveyard), "play_land" (a land was played as a land drop),
        "activated" (an activated ability was paid and put on the stack),
        "trigger_resolved" (a triggered ability resolved), "spell_resolved"
        (a spell finished resolving), "enter_battlefield" / "leave_battlefield"
        (with is_land/is_creature/is_token flags and the destination) and
        "draw". Note that "cast"/"play_land" (the ACT of playing) are distinct
        from "enter_battlefield" (a permanent hitting the battlefield, however
        it got there). Effect events carry "via"/"via_kind" — the resolving spell or
        ability that caused them. Card implementations additionally note
        "ability_success" when the ability actually achieved its purpose
        (found a target, put a card onto the battlefield, ...)."""
        via_kind, via = self.resolving or (None, None)
        self.events.append({"turn": self.turn, "kind": kind, "name": name,
                            "detail": detail, "via": via, "via_kind": via_kind,
                            **extra})

    def events_matching(
        self,
        kind: str | None = None,
        name: str | None = None,
        turn: int | None = None,
        via: str | None = None,
        via_kind: str | None = None,
        pred=None,
    ) -> list[dict]:
        """Events filtered by kind, name / cause-name substrings
        (case-insensitive), turn, cause kind, and/or an arbitrary predicate.
        Each event: {"turn", "kind", "name", "via", "via_kind", ...}."""
        name_l = name.lower() if name else None
        via_l = via.lower() if via else None
        return [
            e for e in self.events
            if (kind is None or e["kind"] == kind)
            and (name_l is None or name_l in (e.get("name") or "").lower())
            and (via_l is None or via_l in (e.get("via") or "").lower())
            and (via_kind is None or e.get("via_kind") == via_kind)
            and (turn is None or e["turn"] == turn)
            and (pred is None or pred(e))
        ]

    def count_events(self, **filters) -> int:
        """Count events matching the `events_matching` filters."""
        return len(self.events_matching(**filters))

    def permanents_put_by(
        self,
        source: str,
        *,
        via_kind: str | None = None,
        land: bool | None = None,
        creature: bool | None = None,
        token: bool | None = None,
        name: str | None = None,
        turn: int | None = None,
    ) -> "CardList":
        """The permanents that entered the battlefield because a spell or ability
        of `source` (name substring) resolved. `via_kind` narrows the cause:
        "triggered" | "activated" | "spell" | "land_drop"; land / creature / token
        filter what entered; `name` (substring) keeps only permanents with that
        name. Returns a CardList that compares by COUNT and tests membership by
        NAME, so all of these read naturally:
          # "the commander's triggered ability put at least 2 lands into play"
          permanents_put_by(state.commander_name(), via_kind="triggered", land=True) >= 2
          # "Misty Rainforest fetched Tropical Island" (its activated ability put
          #  a permanent named Tropical Island into play)
          "Tropical Island" in permanents_put_by("Misty Rainforest", via_kind="activated")
          #  ...equivalently:
          permanents_put_by("Misty Rainforest", via_kind="activated", name="Tropical Island") >= 1"""
        name_l = name.lower() if name else None

        def ok(e):
            if land is not None and e.get("is_land") != land:
                return False
            if creature is not None and e.get("is_creature") != creature:
                return False
            if token is not None and e.get("is_token") != token:
                return False
            if name_l is not None:
                nm = (getattr(e.get("card"), "name", None) or e.get("name") or "")
                if name_l not in nm.lower():
                    return False
            return True

        return CardList(
            e["card"] for e in self.events_matching(
                kind="enter_battlefield", via=source, via_kind=via_kind, turn=turn, pred=ok)
            if e.get("card") is not None
        )

    def cards_put_by(
        self, source: str, *, via_kind: str | None = None, turn: int | None = None
    ) -> list[CardData]:
        """The CARD OBJECTS put onto the battlefield by a resolving spell or
        ability of `source` — inspect any characteristic freely (.type_line,
        .cmc, .faces / .is_double_faced, .colors, ...). e.g. "the commander's
        activated ability put a double-sided card into play" ->
        any(c.is_double_faced for c in
            cards_put_by(state.commander_name(), via_kind="activated")).
        The result also compares numerically by length, so
        `cards_put_by(...) >= 1` ("put at least one card") works too."""
        return CardList(
            e["card"] for e in self.events_matching(
                kind="enter_battlefield", via=source, via_kind=via_kind, turn=turn)
            if e.get("card") is not None
        )

    def cards_drawn_by(self, source: str, turn: int | None = None) -> int:
        """How many cards were drawn because a spell or ability of `source`
        (name substring) resolved."""
        return self.count_events(kind="draw", via=source, turn=turn)

    def cards_put_in_hand_by(
        self, source: str, *, via_kind: str | None = None, turn: int | None = None,
        min_turn: int | None = None, max_turn: int | None = None,
    ) -> "CardList":
        """The CARD OBJECTS a resolving spell or ability of `source` (name
        substring) PUT INTO YOUR HAND WITHOUT drawing them — Atraxa's reveal,
        a tutor-to-hand, "return to your hand", etc. This is NOT drawing (use
        `cards_drawn_by` for that) and NOT the current hand size (`cards_in_hand`)
        — it counts only cards this source moved into your hand. Compares
        numerically by length, so `cards_put_in_hand_by(...) >= N` works. e.g.
        "Atraxa's enter-the-battlefield ability put at least 3 cards into your
        hand" -> cards_put_in_hand_by(state.commander_name(), via_kind="triggered") >= 3."""
        pred = (self._turn_range_pred(min_turn, max_turn)
                if (min_turn is not None or max_turn is not None) else None)
        return CardList(
            e["card"] for e in self.events_matching(
                kind="put_in_hand", via=source, via_kind=via_kind, turn=turn, pred=pred)
            if e.get("card") is not None
        )

    def put_in_hand(self, card: CardData) -> None:
        """Put `card` into your hand from a non-draw effect (reveal-to-hand,
        tutor, bounce) and record a `put_in_hand` event attributed to whatever
        is currently resolving — so `cards_put_in_hand_by(source)` can count it.
        Distinct from `draw()` (drawing off the top of the library)."""
        self.hand.append(card)
        self.note_event("put_in_hand", card.name, card=card,
                        is_creature=card.is_creature, is_land=card.is_land)

    def commander_name(self) -> str:
        """The deck's (first) commander name, wherever the card currently is."""
        return self.commander_names[0] if self.commander_names else ""

    def ability_activated(self, source: str, turn: int | None = None) -> bool:
        """An activated ability of `source` (name substring) was activated."""
        return bool(self.events_matching("activated", source, turn))

    def ability_succeeded(self, source: str, turn: int | None = None) -> bool:
        """An ability of `source` achieved its purpose (implementation-noted:
        e.g. Nick Fury's power-up actually put a card onto the battlefield)."""
        return bool(self.events_matching("ability_success", source, turn))

    def ability_copied(
        self, source: str | None = None, *, by: str | None = None,
        target_kind: str | None = None, turn: int | None = None,
    ) -> int:
        """How many times an ability was COPIED (e.g. Peter Parker's Camera
        copying a triggered/activated ability). `source` (name substring) = the
        source of the COPIED ability — "Atraxa, Grand Unifier" for "copy
        Atraxa's ETB"; `by` = the copier's name (substring); `target_kind` =
        the copied ability's kind, "triggered" or "activated". Compares
        numerically, so `ability_copied(...) >= 1` ("was copied at all") works.
        e.g. "Peter Parker's Camera copies Atraxa's triggered ability" ->
          ability_copied("Atraxa", by="Peter Parker's Camera", target_kind="triggered") >= 1."""
        by_l = by.lower() if by else None

        def ok(e) -> bool:
            if target_kind is not None and e.get("target_kind") != target_kind:
                return False
            if by_l is not None and by_l not in (e.get("copied_by") or "").lower():
                return False
            return True

        return self.count_events(kind="copy_ability", name=source, turn=turn, pred=ok)

    @staticmethod
    def _turn_range_pred(min_turn: int | None, max_turn: int | None):
        def in_range(e) -> bool:
            if min_turn is not None and e["turn"] < min_turn:
                return False
            if max_turn is not None and e["turn"] > max_turn:
                return False
            return True
        return in_range

    def played_on(self, name: str, turn: int | None = None,
                  min_turn: int | None = None, max_turn: int | None = None) -> bool:
        """A card named like `name` (substring, case-insensitive) was PLAYED or
        CAST by you — a spell you cast (put on the stack) or a land you played
        (a land drop). This is the ACT of playing the card.

        IMPORTANT: this is NOT the same as the card ENTERING the battlefield.
        A permanent can enter without being played (fetched, reanimated, put
        into play by another effect, or a token); a spell can be cast and then
        countered so it never enters. Use `entered_battlefield` for "X entered
        the battlefield" and this for "X was played/cast".

        Restrict the moment with `turn` (exactly that turn) or an inclusive
        `min_turn`/`max_turn` range. Game-long event history, so this can be
        checked at ANY later moment. Examples:
          "played on turn 4"              -> played_on(name, 4)
          "cast/played before turn 4"     -> played_on(name, max_turn=3)
          "played between turns 2 and 4"  -> played_on(name, min_turn=2, max_turn=4)
        """
        in_range = self._turn_range_pred(min_turn, max_turn)
        return bool(
            self.events_matching(kind="cast", name=name, turn=turn, pred=in_range)
            or self.events_matching(kind="play_land", name=name, turn=turn, pred=in_range)
        )

    def cast_on(self, name: str, turn: int | None = None,
                min_turn: int | None = None, max_turn: int | None = None) -> bool:
        """A SPELL named like `name` was CAST (put on the stack), whether or not
        it later resolved. Lands are played, not cast — use `played_on` for
        those. See `played_on` for why this differs from entering the
        battlefield."""
        in_range = self._turn_range_pred(min_turn, max_turn)
        return bool(self.events_matching(kind="cast", name=name, turn=turn, pred=in_range))

    def cast_at_storm(self, name: str, at_least: int, turn: int | None = None) -> bool:
        """A spell named like `name` was CAST at a moment when the storm count
        (spells cast this turn, including it) was >= `at_least`. This captures the
        value AT CAST TIME — unlike `cast_on(name) and storm_count >= N`, which can
        be satisfied by reaching the storm count AFTER the spell resolved."""
        return bool(self.events_matching(
            kind="cast", name=name, turn=turn,
            pred=lambda e: e.get("storm", 0) >= at_least))

    def entered_battlefield(self, name: str, turn: int | None = None,
                            min_turn: int | None = None, max_turn: int | None = None,
                            token: bool | None = None, via_kind: str | None = None) -> bool:
        """A permanent named like `name` ENTERED the battlefield (however it got
        there — cast, played, fetched, reanimated, copied, a token...). This is
        the ETB event, distinct from `played_on`/`cast_on` (the act of playing).
        `token` filters token/non-token entries; `via_kind` narrows the cause
        ("spell" | "land_drop" | "triggered" | "activated"). Restrict the moment
        with `turn` or an inclusive `min_turn`/`max_turn` range."""
        in_range = self._turn_range_pred(min_turn, max_turn)
        return bool(self.events_matching(
            kind="enter_battlefield", name=name, turn=turn, via_kind=via_kind,
            pred=lambda e: in_range(e) and (token is None or e.get("is_token") == token)))

    def spell_resolved(self, name: str, turn: int | None = None) -> bool:
        """A spell named like `name` finished resolving (was cast and not
        countered). Distinct from `cast_on` (cast, maybe countered) and from
        `entered_battlefield` (a permanent spell that resolved DID enter, but
        an instant/sorcery resolves without entering)."""
        return bool(self.events_matching("spell_resolved", name, turn))

    def trigger_resolved(self, source: str, turn: int | None = None) -> bool:
        """A triggered ability from `source` resolved."""
        return bool(self.events_matching("trigger_resolved", source, turn))

    def commander_left_play(self, turn: int | None = None,
                            min_turn: int | None = None,
                            max_turn: int | None = None) -> bool:
        """A commander LEFT the battlefield (to any zone). In commander formats
        its owner may then return it to the command zone — see
        `commander_returned_to_command_zone`. Restrict the moment with `turn` or
        an inclusive `min_turn`/`max_turn` range."""
        in_range = self._turn_range_pred(min_turn, max_turn)
        return bool(self.events_matching(
            kind="leave_battlefield", turn=turn,
            pred=lambda e: in_range(e) and e.get("is_commander")))

    def commander_returned_to_command_zone(self, turn: int | None = None,
                                           min_turn: int | None = None,
                                           max_turn: int | None = None) -> bool:
        """A commander LEFT play and was RETURNED to the command zone (having
        first passed through the zone it left to, so leave/dies triggers saw it
        there). Restrict the moment with `turn` or an inclusive
        `min_turn`/`max_turn` range."""
        in_range = self._turn_range_pred(min_turn, max_turn)
        return bool(self.events_matching(
            kind="enter_command_zone", turn=turn, pred=in_range))

    # ==== property-facing query API (keep stable) ==========================
    def battlefield_cards(self) -> list[CardData]:
        return [p.card for p in self.battlefield]

    def count_on_battlefield(self, predicate) -> int:
        return sum(1 for p in self.battlefield if predicate(p.card))

    def has_permanent_named(self, name: str) -> bool:
        return any(p.name.lower() == name.lower() or p.card.name.lower() == name.lower()
                   for p in self.battlefield)

    def permanents_named(self, name: str) -> list[Permanent]:
        return [p for p in self.battlefield
                if p.name.lower() == name.lower() or p.card.name.lower() == name.lower()]

    def count_permanents(
        self,
        *,
        type_contains: str | None = None,
        name_contains: str | None = None,
        tapped: bool | None = None,
        transformed: bool | None = None,
        token: bool | None = None,
        commander: bool | None = None,
    ) -> int:
        """Count battlefield permanents by type line and state. Matching is
        against the ACTIVE face (a transformed/flipped DFC matches its back
        face's name and types); string filters are case-insensitive substrings,
        state filters are optional booleans. e.g. "a flipped Hero creature is
        in play" -> count_permanents(type_contains="Hero", transformed=True) >= 1.
        """
        n = 0
        for p in self.battlefield:
            if type_contains is not None and type_contains.lower() not in p.type_line.lower():
                continue
            if name_contains is not None and name_contains.lower() not in p.name.lower():
                continue
            if tapped is not None and p.tapped != tapped:
                continue
            if transformed is not None and p.transformed != transformed:
                continue
            if token is not None and p.is_token != token:
                continue
            if commander is not None and p.is_commander != commander:
                continue
            n += 1
        return n

    def commander_in_play(self) -> bool:
        return any(p.is_commander for p in self.battlefield)

    def lands_in_play(self) -> int:
        return sum(1 for p in self.battlefield if p.is_land)

    def creatures_in_play(self) -> int:
        return sum(1 for p in self.battlefield if p.is_creature_now)

    def permanents_in_play(self) -> int:
        return len(self.battlefield)

    def cards_in_hand(self) -> int:
        return len(self.hand)

    def cards_in_graveyard(self) -> int:
        return len(self.graveyard)

    def graveyard_names(self) -> list[str]:
        return [c.name for c in self.graveyard]

    def hand_names(self) -> list[str]:
        return [c.name for c in self.hand]

    def battlefield_names(self) -> list[str]:
        return [p.name for p in self.battlefield]

    def _creatures(self) -> list[Permanent]:
        return [p for p in self.battlefield if p.is_creature_now]

    def total_power(self) -> int:
        return sum(self.effective_power(p) for p in self._creatures())

    def total_toughness(self) -> int:
        return sum(self.effective_toughness(p) for p in self._creatures())

    def max_power(self) -> int:
        return max((self.effective_power(p) for p in self._creatures()), default=0)

    def max_toughness(self) -> int:
        return max((self.effective_toughness(p) for p in self._creatures()), default=0)

    def creatures_with_power_at_least(self, n: int) -> int:
        return sum(1 for p in self._creatures() if self.effective_power(p) >= n)

    # ---- per-turn HISTORY (past states) -------------------------------------
    def turns_played(self) -> int:
        """The current turn number (turn 1 is the first)."""
        return self.turn

    def graveyard_added_on(self, turn: int) -> list[str]:
        """Names of cards put into the graveyard during `turn` (any zone)."""
        return list(self.graveyard_by_turn.get(turn, ()))

    def permanents_entered_on(self, turn: int) -> list[str]:
        """Names of permanents that entered the battlefield during `turn`."""
        return [e["name"] for e in self.entered_by_turn.get(turn, ())]

    def creatures_entered_on(self, turn: int) -> list[str]:
        """Names of creatures that entered the battlefield during `turn`."""
        return [e["name"] for e in self.entered_by_turn.get(turn, ()) if e["is_creature"]]

    def lands_entered_on(self, turn: int) -> list[str]:
        """Names of lands that entered the battlefield during `turn`."""
        return [e["name"] for e in self.entered_by_turn.get(turn, ()) if e["is_land"]]

    def each_turn(self, predicate) -> bool:
        """True if `predicate(turn)` holds for EVERY turn played so far
        (turns 1..current). Use for "on each turn since the beginning..."."""
        return all(predicate(t) for t in range(1, self.turn + 1))

    def some_turn(self, predicate) -> bool:
        """True if `predicate(turn)` holds for AT LEAST ONE past/current turn."""
        return any(predicate(t) for t in range(1, self.turn + 1))

    # ---- moment comparison -------------------------------------------------
    def moment_rank(self) -> tuple[int, int]:
        return (self.turn, phase_index(self.phase))

    # ---- snapshot for the board viewer --------------------------------------
    def _perm_view(self, p: Permanent) -> dict:
        """One battlefield permanent as the board viewer consumes it."""
        view = {
            "name": "Face-down creature" if p.face_down else p.name,
            "uid": p.uid,
            "attached_to": p.attached_to,  # host uid for auras/equipment
            "is_aura": "aura" in p.type_line.lower(),
            "tapped": p.tapped,
            "sick": p.summoning_sick,
            "is_land": p.is_land,
            "is_lander": p.is_lander,
            "is_creature": p.is_creature_now,
            "commander": p.is_commander,
            "token": p.is_token,
            # Underscore-prefixed counters are internal bookkeeping
            # (e.g. "_powered_up" moved by Deadpool's text exchange) —
            # never shown as badges.
            "counters": {k: v for k, v in p.counters.items()
                         if v and not k.startswith("_")},
            "attacking": p.uid in self.attackers,
        }
        # Granted (until-end-of-turn) abilities, e.g. Cosmic Spider-Man's
        # combat buff: shown as badges for as long as they last.
        if p.temp_keywords or p.extra_keywords:
            view["granted"] = sorted(p.temp_keywords | p.extra_keywords)
        # "As it enters, choose ..." (Multiversal Passage's basic land type):
        # shown as a badge on the tile.
        if p.chosen:
            view["chosen"] = p.chosen
        if p.is_token:
            # Tokens have no card image: ship what the tile needs to render a
            # composed card face (type, textbox, P/T) tinted by its colour.
            view.update(
                type_line=p.type_line,
                text=p.card.oracle_text,
                colors=list(p.card.colors or []),
                power=self.effective_power(p) if p.is_creature_now else None,
                toughness=self.effective_toughness(p) if p.is_creature_now else None,
            )
        elif p.is_creature_now:
            impl = p.pt_impl or p.impl
            # Show the current P/T on the tile when it is ALTERED from what the
            # card art shows: a characteristic-defining ability (Barrowgoyf */*),
            # an animation (`becomes` — an animated ritual/land), or any P/T
            # modifier (counters / temp buffs / a fixed-config P/T override).
            printed_p, printed_t = _pt(p.face.power), _pt(p.face.toughness)
            eff_p, eff_t = self.effective_power(p), self.effective_toughness(p)
            if (impl.dynamic_power(self, p) is not None
                    or impl.dynamic_toughness(self, p) is not None
                    or p.becomes is not None
                    or eff_p != printed_p or eff_t != printed_t):
                view["power"] = eff_p
                view["toughness"] = eff_t
        # A recoloured permanent (Fixed-config "Set color" / a colour-changing
        # effect): ship the current colours so the tile can show them.
        if not p.is_token and p.color_override is not None:
            view["colors"] = p.colors
            view["recolored"] = True
        if p.face_down:
            view["face_down"] = True
        if p.is_copy:
            view["is_copy"] = True
        return view

    def _exile_view(self) -> list[dict]:
        """Each exiled card as {name, exiled_by?}. `exiled_by` names the source
        that exiled it WHEN that link is still meaningful — the card is playable
        from exile (`exile_playable`, source still on the battlefield) or is
        associated with a permanent via `exiled_with`. Cards exiled with no live
        source (a spell exiled and gone) carry no badge."""
        source_by_id: dict[int, str] = dict(self.exile_source)  # Fixed-config links
        for uid, card in self.exile_playable:
            perm = self.find_permanent(uid)
            if perm is not None:
                source_by_id[id(card)] = perm.name
        for perm in self.battlefield:
            for card in perm.exiled_with:
                source_by_id.setdefault(id(card), perm.name)
        out = []
        for card in self.exile:
            entry = {"name": card.name}
            src = source_by_id.get(id(card))
            if src:
                entry["exiled_by"] = src
            out.append(entry)
        return out

    def snapshot(self) -> dict:
        def stack_item_view(item):
            if isinstance(item, StackAbility):
                return item.public()
            # A spell cast as a non-front face (airbended modal back side) shows
            # the face actually being cast, so the viewer picks its image/name.
            name = item.name
            idx = self.stack_face.get(id(item))
            if idx is not None and 0 <= idx < len(item.faces):
                name = item.faces[idx].name or name
            return {
                "name": name,
                "source_name": name,
                "kind": "spell",
                "trigger": None,
                "ability": name,
            }

        return {
            "turn": self.turn,
            "phase": self.phase.value,
            "life": self.life,
            "opponent_life": self.opponent_life,
            "energy": self.energy,
            "library": len(self.library),
            "hand": [c.name for c in self.hand],
            "command_zone": [c.name for c in self.command_zone],
            "graveyard": [c.name for c in self.graveyard],
            "exile": self._exile_view(),
            # Commander tax: {name: times cast} — the recast tax is {2}×count.
            "commander_cast": {n: c for n, c in self.commander_cast_count.items() if c},
            "stack": [stack_item_view(c) for c in self.stack],
            "mana_pool": {k: v for k, v in self.mana_pool.amounts.items() if v},
            "battlefield": [self._perm_view(p) for p in self.battlefield],
            "counters": {
                "spells": self.spells_cast_this_turn,
                "noncreature": self.noncreature_spells_cast_this_turn,
                "creature": self.creature_spells_cast_this_turn,
                "lands_played": self.lands_played_this_turn,
                "drawn": self.cards_drawn_this_turn,
                "storm": self.storm_count,
            },
        }


def new_game_from_deck(deck: Deck, *, on_the_play: bool = True) -> GameState:
    """Build the pre-game state: commanders in the command zone, the rest in the
    library (unshuffled — the simulator shuffles per game)."""
    state = GameState(format_id=deck.format_id, on_the_play=on_the_play)

    identity: set[str] = set()
    for entry in deck.commanders:
        identity.update(entry.card.color_identity)
        state.command_zone.extend([entry.card] * entry.quantity)

    for entry in deck.mainboard:
        state.library.extend([entry.card] * entry.quantity)

    state.commander_color_identity = tuple(sorted(identity))
    state.commander_names = tuple(e.card.name for e in deck.commanders)
    return state


def make_permanent(
    state: GameState, card: CardData, *, is_commander: bool = False, token: bool = False
) -> Permanent:
    from ..cards import build_card

    impl = build_card(card)
    perm = Permanent(
        card=card,
        impl=impl,
        tapped=False,
        summoning_sick=True,
        is_commander=is_commander,
        is_token=token,
        transformed=impl.enters_transformed,  # back-face plays (MDFC lands)
        uid=state.new_uid(),
    )
    perm.tapped = impl.etb_tapped(state)
    # "Enters with N counters" is a replacement effect: the counters are on the
    # permanent from the moment it exists, before any trigger or board frame.
    for kind, n in impl.enters_with_counters(state).items():
        if n:
            perm.counters[kind] = perm.counters.get(kind, 0) + n
    return perm
