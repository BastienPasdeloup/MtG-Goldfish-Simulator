"""Memory Deluge — {2}{U}{U} Instant. Look at the top X cards (X = mana spent),
put two into your hand and the rest on the bottom. Flashback {5}{U}{U}.
Approximated as look-4 (hardcast) / look-7 (flashback), keep two."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import dig_choose
from .base import Card, CardAction
from .registry import register


@register
class MemoryDeluge(Card):
    card_name = "Memory Deluge"

    def on_resolve(self, state):
        return dig_choose(state, 4, 2, rest="bottom", source="Memory Deluge")

    def graveyard_actions(self, state):
        from ..engine.actions import begin_cast, can_afford

        cost = ManaCost(generic=5, pips=(("U", 2),))
        if not can_afford(state, cost):
            return []

        def fn(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None or not begin_cast(st, card, cost, zone=st.graveyard,
                                              tag="flashback"):
                return None
            if card in st.stack:
                st.stack.remove(card)
            st.note_event("spell_resolved", card.name)
            st.resolving = ("spell", card.name)
            st.exile.append(card)  # flashback exiles
            st.emit("Memory Deluge resolves (flashback) — exiled")
            return dig_choose(st, 7, 2, rest="bottom", source="Memory Deluge")

        return [CardAction("cast Memory Deluge (flashback)", fn)]
