"""El-Hajjâj — {1}{B}{B} Creature — Human Wizard 1/1.
Whenever this creature deals damage, you gain that much life.

Modelled as lifelink (granted on entry): in a solitaire goldfish El-Hajjâj only
ever deals COMBAT damage — to the opponent — and lifelink gains you that much,
which is exactly this trigger for the modelled cases."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ElHajjaj(Card):
    card_name = "El-Hajjâj"

    def on_etb(self, state, permanent):
        permanent.extra_keywords.add("lifelink")
