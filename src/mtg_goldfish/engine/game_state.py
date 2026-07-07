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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..deck.models import CardData, Deck
from .mana import ManaPool
from .phases import Phase, phase_index

if TYPE_CHECKING:  # imported lazily in make_permanent to avoid an import cycle
    from ..cards import Card


@dataclass
class Permanent:
    card: CardData
    impl: Card
    tapped: bool = False
    summoning_sick: bool = True
    is_commander: bool = False
    counters: dict[str, int] = field(default_factory=dict)
    uid: int = 0

    def clone(self) -> "Permanent":
        return Permanent(
            card=self.card,
            impl=self.impl,
            tapped=self.tapped,
            summoning_sick=self.summoning_sick,
            is_commander=self.is_commander,
            counters=dict(self.counters),
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

    mana_pool: ManaPool = field(default_factory=ManaPool)
    life: int = 20

    turn: int = 0
    phase: Phase = Phase.UNTAP
    on_the_play: bool = True

    # per-turn counters (reset at untap)
    lands_played_this_turn: int = 0
    spells_cast_this_turn: int = 0
    creature_spells_cast_this_turn: int = 0
    noncreature_spells_cast_this_turn: int = 0

    # game-long bookkeeping
    commander_cast_count: dict[str, int] = field(default_factory=dict)
    storm_count: int = 0
    _next_uid: int = 1
    log: list[str] = field(default_factory=list)

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
            mana_pool=self.mana_pool.copy(),
            life=self.life,
            turn=self.turn,
            phase=self.phase,
            on_the_play=self.on_the_play,
            lands_played_this_turn=self.lands_played_this_turn,
            spells_cast_this_turn=self.spells_cast_this_turn,
            creature_spells_cast_this_turn=self.creature_spells_cast_this_turn,
            noncreature_spells_cast_this_turn=self.noncreature_spells_cast_this_turn,
            commander_cast_count=dict(self.commander_cast_count),
            storm_count=self.storm_count,
            _next_uid=self._next_uid,
            log=list(self.log),
        )

    # ---- helpers -----------------------------------------------------------
    def new_uid(self) -> int:
        uid = self._next_uid
        self._next_uid += 1
        return uid

    def emit(self, message: str) -> None:
        self.log.append(f"T{self.turn} {self.phase.value}: {message}")

    def reset_turn_counters(self) -> None:
        self.lands_played_this_turn = 0
        self.spells_cast_this_turn = 0
        self.creature_spells_cast_this_turn = 0
        self.noncreature_spells_cast_this_turn = 0

    # ==== property-facing query API (keep stable) ==========================
    def battlefield_cards(self) -> list[CardData]:
        return [p.card for p in self.battlefield]

    def count_on_battlefield(self, predicate) -> int:
        return sum(1 for p in self.battlefield if predicate(p.card))

    def has_permanent_named(self, name: str) -> bool:
        return any(p.card.name.lower() == name.lower() for p in self.battlefield)

    def permanents_named(self, name: str) -> list[Permanent]:
        return [p for p in self.battlefield if p.card.name.lower() == name.lower()]

    def commander_in_play(self) -> bool:
        return any(p.is_commander for p in self.battlefield)

    def lands_in_play(self) -> int:
        return self.count_on_battlefield(lambda c: c.is_land)

    def creatures_in_play(self) -> int:
        return self.count_on_battlefield(lambda c: c.is_creature)

    def cards_in_hand(self) -> int:
        return len(self.hand)

    def hand_names(self) -> list[str]:
        return [c.name for c in self.hand]

    def battlefield_names(self) -> list[str]:
        return [p.card.name for p in self.battlefield]

    # ---- moment comparison -------------------------------------------------
    def moment_rank(self) -> tuple[int, int]:
        return (self.turn, phase_index(self.phase))


def new_game_from_deck(deck: Deck, *, on_the_play: bool = True) -> GameState:
    """Build the pre-game state: commanders in the command zone, the rest in the
    library (unshuffled — the simulator shuffles per game)."""
    state = GameState(format_id=deck.format_id, on_the_play=on_the_play)

    # Commander colour identity feeds identity-flexible mana sources.
    identity: set[str] = set()
    for entry in deck.commanders:
        identity.update(entry.card.color_identity)
        state.command_zone.extend([entry.card] * entry.quantity)

    for entry in deck.mainboard:
        state.library.extend([entry.card] * entry.quantity)

    state.commander_color_identity = tuple(sorted(identity))
    return state


def make_permanent(state: GameState, card: CardData, *, is_commander: bool = False) -> Permanent:
    from ..cards import build_card

    impl = build_card(card)
    return Permanent(
        card=card,
        impl=impl,
        tapped=impl.enters_tapped,
        summoning_sick=True,
        is_commander=is_commander,
        uid=state.new_uid(),
    )
