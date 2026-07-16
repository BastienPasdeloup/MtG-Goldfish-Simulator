"""Flare of Malice — {2}{B}{B} Instant. You may sacrifice a nontoken black
creature rather than pay its mana cost. Each opponent sacrifices a creature or
planeswalker with the greatest mana value they control.
Against a phantom opponent the effect does nothing; the relevant goldfish line is
the alternative cost (sacrificing a black creature feeds your death triggers)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class FlareOfMalice(Card):
    card_name = "Flare of Malice"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        actions = []
        cost = self.cast_cost(state)
        if can_afford(state, cost):
            def mana_fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                st.emit("Flare of Malice: opponent has no creatures to sacrifice")
                return None
            actions.append(CardAction("cast Flare of Malice (mana)", mana_fn))

        victims = {p.name: p.uid for p in state.battlefield
                   if p.is_creature_now and not p.is_token and "B" in p.card.colors}
        for vname, vuid in victims.items():
            def sac_fn(st, vuid=vuid):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                victim = st.find_permanent(vuid)
                if card is None or victim is None:
                    return None
                st.emit(f"sacrifice {victim.name} (Flare of Malice)")
                st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                if not begin_cast(st, card, ManaCost(), tag="sac black creature"):
                    return None
                resolve_to_graveyard(st, card)
                st.emit("Flare of Malice: opponent has no creatures to sacrifice")
                return None
            actions.append(CardAction(
                f"cast Flare of Malice (sacrifice {vname})", sac_fn))
        return actions
