"""Lavaspur Boots — {1} Artifact — Equipment.
Equipped creature gets +1/+0 and has haste and ward {1}.
Equip {1}.

Ward is a no-op with no opponent; +1/+0 (equip_mod) and haste (granted on equip)
are modelled. Equip is sorcery-speed, one branch per creature you control."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class LavaspurBoots(Card):
    card_name = "Lavaspur Boots"

    def equip_mod(self, state, perm):
        return (1, 0)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return []
        targets = [p for p in state.battlefield
                   if p.is_creature_now and p.uid != perm.attached_to]

        def make(uid, name):
            def pay(st):
                boots = st.find_permanent(perm.uid)
                target = st.find_permanent(uid)
                if boots is None or target is None or not pay_cost(st, cost):
                    return False
                return True

            def resolve(st):
                boots = st.find_permanent(perm.uid)
                target = st.find_permanent(uid)
                if boots is None or target is None:
                    return None
                boots.attached_to = target.uid
                target.extra_keywords.add("haste")  # equipped creature has haste
                st.emit(f"equip Lavaspur Boots to {name} (+1/+0, haste)")
                return None

            return CardAction.activated(
                f"equip Lavaspur Boots → {name}", pay, resolve,
                sorcery_speed=True, source_name="Lavaspur Boots", ability_text="Equip")

        return [make(t.uid, t.name) for t in targets]
