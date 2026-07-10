"""Burgeoning — {G} Enchantment.
"Whenever an opponent plays a land, you may put a land from your hand onto the
battlefield." There is no opponent in a solitaire game, so the trigger never
fires — but the enchantment is still castable and enters the battlefield as a
(useless) permanent, which is the faithful behaviour."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Burgeoning(Card):
    card_name = "Burgeoning"
    # No overrides: cast via the engine default; enters as a permanent whose
    # opponent-triggered ability simply never fires.
