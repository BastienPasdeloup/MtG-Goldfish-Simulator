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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from ..deck.models import CardData, Deck
from .mana import ManaPool
from .phases import Phase, phase_index

if TYPE_CHECKING:  # imported lazily in make_permanent to avoid an import cycle
    from ..cards import Card


def _pt(value: str | None) -> int:
    """Parse a power/toughness string to an int; non-numeric (e.g. '*') -> 0."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


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
    damage: int = 0                     # marked damage, cleared at cleanup
    attached_to: int | None = None      # equipment: uid of the equipped creature
    exiled_with: list[CardData] = field(default_factory=list)  # e.g. Parallax Wave
    chosen: str | None = None           # "as ~ enters, choose ..." (Multiversal Passage)
    uid: int = 0

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
        return self.face.type_line or self.card.type_line

    @property
    def is_creature_now(self) -> bool:
        return "creature" in self.type_line.split("—")[0].lower()

    def base_power(self) -> int:
        return _pt(self.face.power)

    def base_toughness(self) -> int:
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
            damage=self.damage,
            attached_to=self.attached_to,
            exiled_with=list(self.exiled_with),
            chosen=self.chosen,
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

    mana_pool: ManaPool = field(default_factory=ManaPool)
    life: int = 20
    opponent_life: int = 20   # phantom opponent for combat damage / Bolt etc.

    turn: int = 0
    phase: Phase = Phase.UNTAP
    on_the_play: bool = True
    rng_seed: int = 0         # drives deterministic mid-game shuffles

    # per-turn counters (reset at untap)
    lands_played_this_turn: int = 0
    bonus_land_drops: int = 0  # one-shot extras this turn (Summer Bloom)
    spells_cast_this_turn: int = 0
    creature_spells_cast_this_turn: int = 0
    noncreature_spells_cast_this_turn: int = 0
    cards_drawn_this_turn: int = 0
    permanent_left_battlefield_this_turn: bool = False  # revolt
    gy_this_turn: list[str] = field(default_factory=list)  # names put in GY this turn

    # game-long bookkeeping
    cards_drawn: int = 0
    commander_cast_count: dict[str, int] = field(default_factory=dict)
    storm_count: int = 0
    attackers: list[int] = field(default_factory=list)  # uids attacking this turn
    _next_uid: int = 1
    log: list[dict] = field(default_factory=list)

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
            mana_pool=self.mana_pool.copy(),
            life=self.life,
            opponent_life=self.opponent_life,
            turn=self.turn,
            phase=self.phase,
            on_the_play=self.on_the_play,
            rng_seed=self.rng_seed,
            lands_played_this_turn=self.lands_played_this_turn,
            bonus_land_drops=self.bonus_land_drops,
            spells_cast_this_turn=self.spells_cast_this_turn,
            creature_spells_cast_this_turn=self.creature_spells_cast_this_turn,
            noncreature_spells_cast_this_turn=self.noncreature_spells_cast_this_turn,
            cards_drawn_this_turn=self.cards_drawn_this_turn,
            permanent_left_battlefield_this_turn=self.permanent_left_battlefield_this_turn,
            gy_this_turn=list(self.gy_this_turn),
            cards_drawn=self.cards_drawn,
            commander_cast_count=dict(self.commander_cast_count),
            storm_count=self.storm_count,
            attackers=list(self.attackers),
            _next_uid=self._next_uid,
            log=list(self.log),
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
                ability = state.stack.pop()
                # The ability's effects apply the moment it resolves: pop it,
                # run the effect, and let the effect's own emit be the single
                # replay frame (stack popped + effects applied together). Only
                # if the effect emitted nothing do we add a fallback frame.
                base_len = len(state.log)
                branches = ability.resolve(state)
                if branches is None:
                    if len(state.log) == base_len:
                        state.emit(f"{ability.name} resolves")
                    state.check_deaths()
                    next_states.append(state)
                    continue
                branched = True
                for branch in branches:
                    if len(branch.log) == base_len:
                        branch.emit(f"{ability.name} resolves")
                    branch.check_deaths()
                    next_states.append(branch)
            states = next_states
            if not progressed:
                break
        return states if branched else None

    def settle(self, branches: list["GameState"] | None = None) -> list["GameState"] | None:
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
        return out if branched else None

    def settle_nonbranching(self, context: str) -> None:
        branches = self.settle()
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
        for p in self.battlefield:
            p.turn_flags.clear()

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

    def queue_entry_triggers(self, entering: list[Permanent]) -> None:
        """Apply immediate entry statics, then put all ETB abilities on the stack.

        `entering` may contain multiple permanents that entered simultaneously.
        """
        for ent in entering:
            for perm in list(self.battlefield):
                if perm is not ent and perm in self.battlefield:
                    perm.impl.on_other_etb_immediate(self, perm, ent)

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
        self.graveyard.append(card)
        self.gy_this_turn.append(card.name)
        self.graveyard_by_turn.setdefault(self.turn, []).append(card.name)

    # ---- drawing (fires draw triggers) --------------------------------------
    def draw(self, n: int = 1) -> None:
        for _ in range(n):
            if not self.library:
                return
            self.hand.append(self.library.pop(0))
            self.cards_drawn += 1
            self.cards_drawn_this_turn += 1
            nth = self.cards_drawn_this_turn
            self.queue_draw_triggers(nth)

    # ---- library search / shuffle -------------------------------------------
    def shuffle_library(self) -> None:
        """Deterministic per branch: seeded by game seed + uid counter."""
        rng = random.Random(self.rng_seed * 1_000_003 + self._next_uid)
        self._next_uid += 1
        rng.shuffle(self.library)

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
        announce: str | None = None,
    ) -> Permanent:
        perm = make_permanent(self, card, is_commander=is_commander, token=token)
        if tapped is not None:
            perm.tapped = tapped
        self.battlefield.append(perm)
        self.entered_by_turn.setdefault(self.turn, []).append({
            "name": perm.name,
            "is_creature": perm.is_creature_now,
            "is_land": "land" in perm.type_line.lower(),
            "is_token": perm.is_token,
        })
        # Announce the entry BEFORE any ETB triggers fire, so the replay shows
        # the permanent entering first and its triggers (landfall, Amulet, ...)
        # resolving afterwards — not the other way round.
        if announce:
            self.emit(announce)
        if fire_etb:
            self.queue_entry_triggers([perm])
            self.settle_nonbranching(f"direct battlefield entry of {perm.name}")
        return perm

    def make_token(self, name: str, power: int, toughness: int, type_line: str) -> Permanent:
        data = CardData(name=name, type_line=type_line, power=str(power), toughness=str(toughness))
        perm = self.put_on_battlefield(data, token=True, fire_etb=False)
        self.emit(f"create token {name} ({power}/{toughness})")
        return perm

    def leaves_battlefield(self, perm: Permanent, to: str = "graveyard") -> None:
        """Move a permanent off the battlefield (graveyard/exile/hand/none)."""
        if perm not in self.battlefield:
            return
        self.battlefield.remove(perm)
        self.permanent_left_battlefield_this_turn = True
        # Auras attached to it die; equipment merely unattaches.
        for att in list(self.battlefield):
            if att.attached_to == perm.uid:
                if "aura" in att.type_line.lower():
                    self.leaves_battlefield(att, "graveyard")
                else:
                    att.attached_to = None
        self.queue_leave_triggers(perm)
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

    def check_deaths(self) -> None:
        """State-based check: creatures with toughness <= 0 or lethal damage die."""
        for perm in list(self.battlefield):
            if not perm.is_creature_now:
                continue
            # A creature with unknown printed toughness (None/'*') and no
            # modifiers has no known toughness to die from — skip it.
            has_mods = (
                perm.temp_toughness or perm.counters.get("+1/+1")
                or perm.impl.dynamic_toughness(self, perm) is not None
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
                self.leaves_battlefield(perm, "graveyard")
                for eq in holders:
                    self.queue_equipped_died_triggers(eq)

    # ---- effective stats (counters, temp mods, equipment, dynamic P/T) ------
    def effective_power(self, perm: Permanent) -> int:
        base = perm.impl.dynamic_power(self, perm)
        if base is None:
            base = perm.base_power()
        val = base + perm.counters.get("+1/+1", 0) + perm.temp_power
        for eq in self.battlefield:
            if eq.attached_to == perm.uid:
                val += eq.impl.equip_mod(self, eq)[0]
        return val

    def effective_toughness(self, perm: Permanent) -> int:
        base = perm.impl.dynamic_toughness(self, perm)
        if base is None:
            base = perm.base_toughness()
        val = base + perm.counters.get("+1/+1", 0) + perm.temp_toughness
        for eq in self.battlefield:
            if eq.attached_to == perm.uid:
                val += eq.impl.equip_mod(self, eq)[1]
        return val

    def has_keyword(self, perm: Permanent, kw: str) -> bool:
        return kw.lower() in [k.lower() for k in perm.card.keywords]

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

    def commander_in_play(self) -> bool:
        return any(p.is_commander for p in self.battlefield)

    def lands_in_play(self) -> int:
        return sum(1 for p in self.battlefield if "land" in p.type_line.lower())

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
    def snapshot(self) -> dict:
        def stack_item_view(item):
            if isinstance(item, StackAbility):
                return item.public()
            return {
                "name": item.name,
                "source_name": item.name,
                "kind": "spell",
                "trigger": None,
                "ability": item.name,
            }

        return {
            "turn": self.turn,
            "phase": self.phase.value,
            "life": self.life,
            "opponent_life": self.opponent_life,
            "library": len(self.library),
            "hand": [c.name for c in self.hand],
            "command_zone": [c.name for c in self.command_zone],
            "graveyard": [c.name for c in self.graveyard],
            "exile": [c.name for c in self.exile],
            "stack": [stack_item_view(c) for c in self.stack],
            "mana_pool": {k: v for k, v in self.mana_pool.amounts.items() if v},
            "battlefield": [
                {
                    "name": p.name,
                    "uid": p.uid,
                    "attached_to": p.attached_to,  # host uid for auras/equipment
                    "is_aura": "aura" in p.type_line.lower(),
                    "tapped": p.tapped,
                    "sick": p.summoning_sick,
                    "is_land": "land" in p.type_line.lower(),
                    "is_creature": p.is_creature_now,
                    "commander": p.is_commander,
                    "token": p.is_token,
                    "counters": {k: v for k, v in p.counters.items() if v},
                    "attacking": p.uid in self.attackers,
                }
                for p in self.battlefield
            ],
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
