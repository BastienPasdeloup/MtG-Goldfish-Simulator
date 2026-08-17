"""Bronze Tablet — {6} Artifact. Enters tapped.
{4}, {T}: Exile this artifact and target nontoken permanent an opponent owns. That
player may pay 10 life; if they do, this goes to its owner's graveyard. Otherwise
they own this card and you own the other exiled card (ante).

The ability targets a permanent an OPPONENT owns — the phantom opponent controls
none in a goldfish, so it can never be activated (and the ante swap is out of
scope). It enters tapped (auto from its text). A fixed artifact body here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BronzeTablet(Card):
    card_name = "Bronze Tablet"
