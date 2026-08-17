"""Shatterstorm — {2}{R}{R} Sorcery. Destroy all artifacts. They can't be regenerated.

Destroys every artifact you control (the phantom opponent has none); pops any
regeneration shield first so "can't be regenerated" is honoured."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Shatterstorm(Card):
    card_name = "Shatterstorm"

    def on_resolve(self, state):
        arts = [p for p in list(state.battlefield) if p.is_artifact]
        for p in arts:
            live = state.find_permanent(p.uid)
            if live is None:
                continue
            live.counters.pop("regen_shield", None)  # can't be regenerated
            state.emit(f"Shatterstorm: destroy {live.name}")
            state.leaves_battlefield(live, "graveyard", reason="destroy")
        state.check_deaths()
