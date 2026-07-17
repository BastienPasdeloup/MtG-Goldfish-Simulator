"""Gitaxian Probe — {U/P} Sorcery. Look at a player's hand; draw a card. The
hand-peek is irrelevant in a goldfish; it is a free (or 2-life) cantrip."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class GitaxianProbe(Card):
    card_name = "Gitaxian Probe"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        def make(cost, life, tag):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost, extra_life=life):
                    return None
                resolve_to_graveyard(st, card)
                st.draw(1)
                st.emit(f"Gitaxian Probe ({tag}): draw a card")
                return None
            return fn

        acts = []
        u = ManaCost(pips=(("U", 1),))
        if can_afford(state, u):
            acts.append(CardAction("cast Gitaxian Probe ({U})", make(u, 0, "{U}")))
        if state.life > 2:
            acts.append(CardAction("cast Gitaxian Probe (2 life)",
                                   make(ManaCost(), 2, "2 life")))
        return acts
