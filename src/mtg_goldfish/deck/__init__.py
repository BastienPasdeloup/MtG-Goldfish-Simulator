"""Deck import and card metadata (Moxfield + MTGTop8 + Scryfall)."""
from .importer import fetch_deck_signature, import_deck
from .models import CardData, CardFace, Deck, DeckEntry, DeckBoard
from .moxfield import MoxfieldError, deck_signature, import_moxfield_deck
from .mtgtop8 import MTGTop8Error, import_mtgtop8_deck
from .scryfall import ScryfallClient, ScryfallError

__all__ = [
    "CardData",
    "CardFace",
    "Deck",
    "DeckEntry",
    "DeckBoard",
    "MoxfieldError",
    "MTGTop8Error",
    "import_moxfield_deck",
    "import_mtgtop8_deck",
    "import_deck",
    "deck_signature",
    "fetch_deck_signature",
    "ScryfallClient",
    "ScryfallError",
]
