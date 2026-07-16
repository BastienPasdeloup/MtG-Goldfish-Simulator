"""Rotten Reunion — {B} Instant. Exile up to one target card from a graveyard.
Create a 2/2 black Zombie creature token with decayed. Flashback {1}{B}."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card, CardAction
from .registry import register

_DECAY_TEXT = ("Decayed (can't block; when it attacks, sacrifice it at end of "
               "combat).")


def _resolve_effect(state):
    gy_options = [("none", None)]
    seen = set()
    for c in state.graveyard:
        if c.name not in seen:
            seen.add(c.name)
            gy_options.append((c.name, c.name))

    def fn(st, opt):
        _label, name = opt
        if name is not None:
            c = next((x for x in st.graveyard if x.name == name), None)
            if c is not None:
                st.leave_graveyard(c)
                st.exile.append(c)
                st.emit(f"Rotten Reunion: exile {name} from graveyard")
        tok = st.make_token("Zombie", 2, 2, "Creature — Zombie", text=_DECAY_TEXT)
        tok.counters["decayed"] = 1
        st.emit("Rotten Reunion: create a 2/2 decayed Zombie")
        return None

    return branch_over(state, gy_options, fn)


@register
class RottenReunion(Card):
    card_name = "Rotten Reunion"

    def on_resolve(self, state):
        return _resolve_effect(state)

    def graveyard_actions(self, state):
        from ..engine.actions import begin_cast, can_afford

        cost = ManaCost(generic=1, pips=(("B", 1),))
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
            st.exile.append(card)  # flashback exiles instead of graveyard
            st.emit("Rotten Reunion resolves (flashback) — exiled")
            return _resolve_effect(st)

        return [CardAction("cast Rotten Reunion (flashback)", fn)]
