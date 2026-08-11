"""Deck and card-metadata models.

`CardData` is the canonical, Scryfall-derived description of a *printing-agnostic*
card. It is intentionally decoupled from the engine's runtime card behaviour
(see `mtg_goldfish.cards`): this layer only knows facts about the card, not how
to play it.
"""
from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class DeckBoard(str, enum.Enum):
    """Which zone a deck entry belongs to at game start."""

    MAINBOARD = "mainboard"
    COMMANDER = "commander"
    COMPANION = "companion"
    SIDEBOARD = "sideboard"


class CardFace(BaseModel):
    """One face of a (possibly multi-faced) card."""

    name: str
    mana_cost: str = ""
    type_line: str = ""
    oracle_text: str = ""
    power: str | None = None
    toughness: str | None = None
    loyalty: str | None = None
    image_normal: str | None = None


class CardData(BaseModel):
    """Printing-agnostic card metadata sourced from Scryfall."""

    name: str
    mana_cost: str = ""
    cmc: float = 0.0
    type_line: str = ""
    oracle_text: str = ""
    colors: list[str] = Field(default_factory=list)
    color_identity: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    power: str | None = None
    toughness: str | None = None
    loyalty: str | None = None
    layout: str = "normal"
    image_normal: str | None = None
    faces: list[CardFace] = Field(default_factory=list)
    scryfall_id: str | None = None
    # Set code of the printing this card data came from (the earliest paper
    # printing, excluding Alpha — see ScryfallClient._oldest_raw). Used for
    # "originally printed in <set>" checks (City in a Bottle) and set-scoped logic.
    set: str = ""
    # Related token permanents this card creates (from Scryfall `all_parts`):
    # each {name, type_line, scryfall_id}. Used to show real token scans.
    token_parts: list[dict] = Field(default_factory=list)

    # ---- convenience predicates over the type line -------------------------
    def _types(self) -> set[str]:
        # Type line looks like "Legendary Creature — Elf Warrior".
        left = self.type_line.split("—")[0]
        return {t.strip().lower() for t in left.split() if t.strip()}

    @property
    def is_land(self) -> bool:
        return "land" in self._types()

    @property
    def is_creature(self) -> bool:
        return "creature" in self._types()

    @property
    def is_instant(self) -> bool:
        return "instant" in self._types()

    @property
    def is_sorcery(self) -> bool:
        return "sorcery" in self._types()

    @property
    def is_artifact(self) -> bool:
        return "artifact" in self._types()

    @property
    def is_permanent(self) -> bool:
        perm = {"land", "creature", "artifact", "enchantment", "planeswalker", "battle"}
        return bool(self._types() & perm)

    @property
    def is_legendary(self) -> bool:
        return "legendary" in self._types()

    @property
    def is_double_faced(self) -> bool:
        """Two faces (transforming or modal DFC)."""
        return len(self.faces) >= 2

    @property
    def can_be_commander(self) -> bool:
        """A legendary creature, or a card whose text grants commander status."""
        text = self.oracle_text.lower()
        if self.is_legendary and self.is_creature:
            return True
        return "can be your commander" in text

    @property
    def is_companion(self) -> bool:
        return "companion" in [k.lower() for k in self.keywords] or (
            "companion —" in self.oracle_text.lower()
        )

    @property
    def image(self) -> str | None:
        if self.image_normal:
            return self.image_normal
        for face in self.faces:
            if face.image_normal:
                return face.image_normal
        return None


class DeckEntry(BaseModel):
    quantity: int = 1
    board: DeckBoard = DeckBoard.MAINBOARD
    card: CardData


class Deck(BaseModel):
    name: str
    format_id: str = "duel_commander"
    source_url: str | None = None
    entries: list[DeckEntry] = Field(default_factory=list)

    # ---- accessors ---------------------------------------------------------
    def by_board(self, board: DeckBoard) -> list[DeckEntry]:
        return [e for e in self.entries if e.board == board]

    @property
    def commanders(self) -> list[DeckEntry]:
        return self.by_board(DeckBoard.COMMANDER)

    @property
    def companions(self) -> list[DeckEntry]:
        return self.by_board(DeckBoard.COMPANION)

    @property
    def mainboard(self) -> list[DeckEntry]:
        return self.by_board(DeckBoard.MAINBOARD)

    @property
    def total_cards(self) -> int:
        """Cards that start in the library (mainboard only)."""
        return sum(e.quantity for e in self.mainboard)

    def all_cards(self) -> list[CardData]:
        out: list[CardData] = []
        for e in self.entries:
            out.extend([e.card] * e.quantity)
        return out

    def to_public(self) -> dict[str, Any]:
        """A JSON-safe summary for the web layer."""
        return {
            "name": self.name,
            "format_id": self.format_id,
            "source_url": self.source_url,
            "total_cards": self.total_cards,
            "commanders": [e.card.name for e in self.commanders],
            "companions": [e.card.name for e in self.companions],
        }
