"""Library of Leng — {1} Artifact.
You have no maximum hand size.
If an effect causes you to discard a card, discard it, but you may put it on top
of your library instead of into your graveyard.

Both clauses are near-inert in a solitaire goldfish (the search rarely reaches a
cleanup discard, and discard-to-library is a marginal replacement). The artifact
is still cast and enters (counting toward artifact/permanent counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class LibraryOfLeng(Card):
    card_name = "Library of Leng"
