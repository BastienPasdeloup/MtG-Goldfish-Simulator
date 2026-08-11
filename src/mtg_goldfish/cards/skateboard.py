"""Skateboard — {1} Artifact — Equipment.
When this Equipment enters, tap target permanent.
Equipped creature gets +1/+0 and has haste.
Equip {1}.

The ETB "tap target permanent" only has your own permanents to target (a minor
self-downside a player minimises to irrelevance), so it's not modelled; +1/+0
(equip_mod) and haste (granted on equip) are. Equip is sorcery-speed."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Skateboard(Card):
    card_name = "Skateboard"

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
                board = st.find_permanent(perm.uid)
                target = st.find_permanent(uid)
                if board is None or target is None or not pay_cost(st, cost):
                    return False
                return True

            def resolve(st):
                board = st.find_permanent(perm.uid)
                target = st.find_permanent(uid)
                if board is None or target is None:
                    return None
                board.attached_to = target.uid
                target.extra_keywords.add("haste")
                st.emit(f"equip Skateboard to {name} (+1/+0, haste)")
                return None

            return CardAction.activated(
                f"equip Skateboard → {name}", pay, resolve,
                sorcery_speed=True, source_name="Skateboard", ability_text="Equip")

        return [make(t.uid, t.name) for t in targets]
