"""Wrath of the Skies — {X}{W}{W} Sorcery. You get X energy, then pay any amount
of energy; destroy each artifact, creature, and enchantment with mana value ≤ the
energy paid. In a goldfish this only wipes your own board; a single representative
X (enough to clear it) is offered."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class WrathOfTheSkies(Card):
    card_name = "Wrath of the Skies"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        hittable = [p for p in state.battlefield if p.is_creature_now
                    or any(t in p.type_line.lower() for t in ("artifact", "enchantment"))]
        if not hittable:
            return []
        x = max(int(p.card.cmc) for p in hittable)
        cost = ManaCost(generic=x, pips=(("W", 2),))
        if not can_afford(state, cost):
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not begin_cast(st, card, cost):
                return None
            resolve_to_graveyard(st, card)
            st.add_energy(x)
            st.pay_energy(x)
            for p in list(st.battlefield):
                is_hit = p.is_creature_now or any(
                    t in p.type_line.lower() for t in ("artifact", "enchantment"))
                if is_hit and int(p.card.cmc) <= x:
                    st.emit(f"Wrath of the Skies: destroy {p.name}")
                    st.leaves_battlefield(p, "graveyard", reason="destroy")
            st.emit(f"Wrath of the Skies: X={x}, destroy mv≤{x}")
            return None

        return [CardAction(f"cast Wrath of the Skies (X={x})", fn)]
