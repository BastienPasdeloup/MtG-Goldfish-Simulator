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
from typing import TYPE_CHECKING

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
    stack: list[CardData] = field(default_factory=list)
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

    def reset_turn_counters(self) -> None:
        self.lands_played_this_turn = 0
        self.spells_cast_this_turn = 0
        self.creature_spells_cast_this_turn = 0
        self.noncreature_spells_cast_this_turn = 0
        self.cards_drawn_this_turn = 0
        self.permanent_left_battlefield_this_turn = False
        self.gy_this_turn.clear()
        for p in self.battlefield:
            p.turn_flags.clear()

    def to_graveyard(self, card: CardData) -> None:
        self.graveyard.append(card)
        self.gy_this_turn.append(card.name)

    # ---- drawing (fires draw triggers) --------------------------------------
    def draw(self, n: int = 1) -> None:
        for _ in range(n):
            if not self.library:
                return
            self.hand.append(self.library.pop(0))
            self.cards_drawn += 1
            self.cards_drawn_this_turn += 1
            nth = self.cards_drawn_this_turn
            for perm in list(self.battlefield):
                perm.impl.on_draw_card(self, perm, nth)

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
    ) -> Permanent:
        perm = make_permanent(self, card, is_commander=is_commander, token=token)
        if tapped is not None:
            perm.tapped = tapped
        self.battlefield.append(perm)
        if fire_etb:
            perm.impl.on_etb(self, perm)
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
        # Unattach any equipment pointing at it.
        for eq in self.battlefield:
            if eq.attached_to == perm.uid:
                eq.attached_to = None
        perm.impl.on_leave(self, perm)
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
                    eq.impl.on_equipped_died(self, eq)

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

    # ---- moment comparison -------------------------------------------------
    def moment_rank(self) -> tuple[int, int]:
        return (self.turn, phase_index(self.phase))

    # ---- snapshot for the board viewer --------------------------------------
    def snapshot(self) -> dict:
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
            "stack": [c.name for c in self.stack],
            "mana_pool": {k: v for k, v in self.mana_pool.amounts.items() if v},
            "battlefield": [
                {
                    "name": p.name,
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
        uid=state.new_uid(),
    )
    perm.tapped = impl.etb_tapped(state)
    return perm
