"""Cling to Dust — {B} Instant. Exile target card from a graveyard; if it was a
creature card, gain 3 life, otherwise draw a card. Escape—{3}{B}, exile five
other cards from your graveyard."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card, CardAction
from .registry import register


def _effect(state):
    names = sorted({c.name for c in state.graveyard})
    if not names:
        return None

    def fn(st, name):
        c = next((x for x in st.graveyard if x.name == name), None)
        if c is None:
            return None
        st.leave_graveyard(c)
        st.exile.append(c)
        if c.is_creature:
            st.gain_life(3)
            st.emit(f"Cling to Dust: exile {name} (creature) — gain 3 life")
        else:
            # Draw BEFORE emitting so the replay frame's snapshot shows the drawn
            # card in hand (draw() emits nothing on its own).
            st.draw(1)
            st.emit(f"Cling to Dust: exile {name} — draw a card")
        return None

    return branch_over(state, names, fn)


@register
class ClingToDust(Card):
    card_name = "Cling to Dust"

    def on_resolve(self, state):
        return _effect(state)

    def graveyard_actions(self, state):
        from ..engine.actions import begin_cast, can_afford

        cost = ManaCost(generic=3, pips=(("B", 1),))
        others = [c for c in state.graveyard if c.name != self.card_name]
        if len(others) < 5 or not can_afford(state, cost):
            return []

        def fn(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            fuel = [c for c in st.graveyard if c.name != self.card_name][:5]
            if card is None or len(fuel) < 5 or not begin_cast(
                    st, card, cost, zone=st.graveyard, tag="escape"):
                return None
            for c in fuel:
                st.leave_graveyard(c)
                st.exile.append(c)
            if card in st.stack:
                st.stack.remove(card)
            st.note_event("spell_resolved", card.name)
            st.resolving = ("spell", card.name)
            st.to_graveyard(card)  # a resolved instant goes to the graveyard
            st.emit("Cling to Dust (escape) resolves")
            return _effect(st)

        return [CardAction("cast Cling to Dust (escape)", fn)]
