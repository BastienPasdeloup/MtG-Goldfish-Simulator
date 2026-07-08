"""Otawara, Soaring City — Legendary Land. {T}: Add {U}.
Channel — {3}{U}, Discard: return target artifact/creature/enchantment/
planeswalker to its owner's hand ({1} less per legendary creature you control).
In solitaire the only targets are your own permanents.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register


@register
class OtawaraSoaringCity(Card):
    card_name = "Otawara, Soaring City"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("U",))]

    def hand_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        legends = sum(
            1 for p in state.battlefield
            if p.is_creature_now and "legendary" in p.type_line.lower()
        )
        cost = ManaCost(generic=max(0, 3 - legends), pips=(("U", 1),))
        if not can_afford(state, cost):
            return []
        targets = [
            p for p in state.battlefield
            if any(t in p.type_line.lower()
                   for t in ("artifact", "creature", "enchantment", "planeswalker"))
        ]

        def make(uid):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                perm = st.find_permanent(uid)
                if card is None or perm is None or not pay_cost(st, cost):
                    return None
                st.hand.remove(card)
                st.to_graveyard(card)
                st.emit(f"channel Otawara (discard) — return {perm.name} to hand")
                st.leaves_battlefield(perm, "hand")
                return None
            return fn

        return [CardAction(f"channel Otawara: bounce {t.name}", make(t.uid)) for t in targets]
