"""Tendrils of Agony — {2}{B}{B} Sorcery. Target player loses 2 life and you gain
2 life. Storm — copy it for each spell cast before it this turn. Modelled as
(spells cast this turn, including Tendrils) instances of "drain 2"."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TendrilsOfAgony(Card):
    card_name = "Tendrils of Agony"

    def on_resolve(self, state):
        # spells_cast_this_turn already counts Tendrils itself (the original) plus
        # every spell cast before it this turn (each a copy).
        n = max(1, state.spells_cast_this_turn)
        state.opponent_life -= 2 * n
        state.life += 2 * n
        state.note_crime()
        state.emit(f"Tendrils of Agony: storm {n} — opponent loses {2 * n}, you gain "
                   f"{2 * n} (you {state.life}, opp {state.opponent_life})")
        return None
