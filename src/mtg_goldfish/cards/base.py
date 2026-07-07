"""Base class for runtime card behaviour.

A `Card` binds a `CardData` (static facts) to *behaviour* the engine can invoke.
The default implementation gives you a fully functional vanilla card: lands and
mana rocks work by declaring `mana_abilities`, and permanents/spells hook their
effects via `on_etb` / `on_resolve`. Override only what a card actually does.

Card implementations live one-per-file in this package and register themselves
with `@register` (see `registry.py`).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ..deck.models import CardData
from ..engine.mana import ManaAbility, ManaCost

if TYPE_CHECKING:  # avoid import cycles; these are engine runtime types
    from ..engine.game_state import GameState, Permanent


class Card:
    """Runtime behaviour for a single card.

    Subclasses set `card_name` and are registered via `@register`. Instances
    are cheap and hold no per-game mutable state — that lives on the engine's
    `Permanent` / stack objects.
    """

    #: Exact Scryfall card name this implementation handles.
    card_name: ClassVar[str] = ""
    #: Whether this card's rules are actually modelled. `False` for the
    #: automatic fallback used when a card has no implementation yet.
    implemented: ClassVar[bool] = True

    def __init__(self, data: CardData) -> None:
        self.data = data

    # ---- static facts (delegated to CardData) ------------------------------
    @property
    def name(self) -> str:
        return self.data.name

    @property
    def mana_cost(self) -> ManaCost:
        return ManaCost.parse(self.data.mana_cost)

    @property
    def is_land(self) -> bool:
        return self.data.is_land

    @property
    def is_permanent(self) -> bool:
        return self.data.is_permanent

    @property
    def is_creature(self) -> bool:
        return self.data.is_creature

    @property
    def enters_tapped(self) -> bool:
        text = self.data.oracle_text.lower()
        if "enters tapped" not in text and "enters the battlefield tapped" not in text:
            return False
        # Shock/pain/fast lands can choose to enter untapped — assume they do
        # (optimistic for mana-availability analysis).
        if any(k in text for k in ("unless", "you may pay", "pay 2 life", "pay 3 life")):
            return False
        return True

    # ---- behaviour hooks (override as needed) ------------------------------
    def mana_abilities(self, state: "GameState") -> list[ManaAbility]:
        """Mana this card can produce while on the battlefield (untapped)."""
        return []

    def on_etb(self, state: "GameState", permanent: "Permanent") -> None:
        """Called when this card enters the battlefield."""

    def on_resolve(self, state: "GameState") -> None:
        """Called when a non-permanent spell (instant/sorcery) resolves."""

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<{type(self).__name__} {self.name!r}>"


class UnimplementedCard(Card):
    """Fallback for cards with no dedicated implementation.

    The UI renders it in red and offers to auto-implement it. For simulation it
    is treated as a **vanilla approximation** so the goldfish still does
    something useful: it can be cast/played, permanents enter the battlefield
    and count toward board state and spell tallies, but any special text is
    ignored. Unimplemented *lands* tap for one mana of any colour in the
    commander's colour identity (an optimistic default for Commander mana
    bases). Results involving unimplemented cards are therefore approximate.
    """

    implemented = False

    def mana_abilities(self, state: "GameState") -> list[ManaAbility]:
        if not self.is_land:
            return []
        identity = tuple(getattr(state, "commander_color_identity", ())) or (
            "W",
            "U",
            "B",
            "R",
            "G",
        )
        return [ManaAbility(amount=1, choices=identity)]
