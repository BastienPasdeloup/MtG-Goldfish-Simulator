"""Unsummon — {U} Instant. Return target creature to its owner's hand.

Bounce one of your creatures back to hand (one branch each) — useful to re-use an
ETB or to save a creature from death."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Unsummon(Card):
    card_name = "Unsummon"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if not p.is_creature_now or p.name in seen or p.is_token:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    st.emit(f"Unsummon: return {nm} to hand")
                    st.leaves_battlefield(tgt, "hand", reason="bounce")
                    return None
                return fn

            acts.append(CardAction(f"cast Unsummon → return {p.name}", make(p.uid, p.name)))
        return acts
