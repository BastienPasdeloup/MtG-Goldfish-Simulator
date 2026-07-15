"""Skullclamp — {1} Artifact — Equipment. Equipped creature gets +1/-1;
whenever equipped creature dies, draw two cards. Equip {1}."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Skullclamp(Card):
    card_name = "Skullclamp"

    def equip_mod(self, state, perm):
        return (1, -1)

    def on_equipped_died(self, state, perm):
        state.emit("Skullclamp: equipped creature died — draw two cards")
        state.draw(2)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return []
        targets = [
            p for p in state.battlefield
            if p.is_creature_now and p.uid != perm.attached_to and p.uid != perm.uid
        ]

        def make(uid: int):
            def pay(st):
                clamp = st.find_permanent(perm.uid)
                target = st.find_permanent(uid)
                if clamp is None or target is None or not pay_cost(st, cost):
                    return False
                return True

            def resolve(st):
                clamp = st.find_permanent(perm.uid)
                target = st.find_permanent(uid)
                if clamp is None or target is None:
                    return None
                clamp.attached_to = target.uid
                st.emit(f"equip Skullclamp to {target.name} (+1/-1)")
                st.check_deaths()  # 1-toughness creatures die -> draw 2
                return None
            return CardAction.activated(
                f"equip Skullclamp → {state.find_permanent(uid).name if state.find_permanent(uid) else uid}",
                pay,
                resolve,
                sorcery_speed=True,  # equip: only as a sorcery
                source_name="Skullclamp",
                ability_text="Equip",
            )

        return [make(t.uid) for t in targets]
