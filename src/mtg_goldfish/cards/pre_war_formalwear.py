"""Pre-War Formalwear — {2}{W} Artifact — Equipment. ETB: return target
creature card with mana value ≤3 from your graveyard to the battlefield and
attach this to it (branch; fizzles with no target). Equipped creature gets
+2/+2 and vigilance. Equip {3}."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over, enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class PreWarFormalwear(Card):
    card_name = "Pre-War Formalwear"

    def equip_mod(self, state, perm):
        return (2, 2)

    def on_etb(self, state, permanent):
        targets = sorted({c.name for c in state.graveyard if c.is_creature and c.cmc <= 3})
        if not targets:
            return None

        def apply(st, name: str):
            card = next(c for c in st.graveyard if c.name == name)
            st.graveyard.remove(card)
            newp = enter_battlefield(
                st,
                card,
                announce=f"Pre-War Formalwear: return {name} to the battlefield",
            )
            me = st.find_permanent(permanent.uid)
            if me is not None:
                me.attached_to = newp.uid
            st.emit(f"Pre-War Formalwear: attach to {name} (+2/+2)")
            return None

        return branch_over(state, targets, apply)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3)
        if not can_afford(state, cost):
            return []
        targets = [p for p in state.battlefield
                   if p.is_creature_now and p.uid != perm.attached_to]

        def make(uid: int, target_name: str):
            def pay(st):
                me = st.find_permanent(perm.uid)
                t = st.find_permanent(uid)
                if me is None or t is None or not pay_cost(st, cost):
                    return False
                return True

            def resolve(st):
                me = st.find_permanent(perm.uid)
                t = st.find_permanent(uid)
                if me is None or t is None:
                    return None
                me.attached_to = t.uid
                st.emit(f"equip Pre-War Formalwear to {t.name} (+2/+2)")
                return None
            return CardAction.activated(
                f"equip Pre-War Formalwear → {target_name}",
                pay,
                resolve,
                source_name="Pre-War Formalwear",
                ability_text="Equip",
            )

        return [make(t.uid, t.name) for t in targets]
