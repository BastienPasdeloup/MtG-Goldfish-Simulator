"""Sheoldred's Edict — {1}{B} Instant. Each opponent sacrifices a creature /
token / planeswalker of their choice. Against a phantom opponent this does
nothing; it is castable but has no effect in a goldfish."""
from .base import Card
from .registry import register


@register
class SheoldredsEdict(Card):
    card_name = "Sheoldred's Edict"

    def on_resolve(self, state):
        state.emit("Sheoldred's Edict: opponent has nothing to sacrifice (goldfish)")
