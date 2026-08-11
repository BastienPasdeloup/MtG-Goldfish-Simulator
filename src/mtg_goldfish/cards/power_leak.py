"""Power Leak — {1}{U} Enchantment — Aura. Enchant enchantment.
At the beginning of the upkeep of enchanted enchantment's controller, that player
may pay any amount of mana. This Aura deals 2 damage to that player. Prevent X of
that damage, where X is the amount of mana that player paid this way.

Enchant one of your enchantments; each of your upkeeps a branch: pay {2} to
prevent all 2 damage, or take 2 (via damage_self). Self-harm — offered for
completeness."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import aura_enchant_actions, branch_over
from .base import Card
from .registry import register


@register
class PowerLeak(Card):
    card_name = "Power Leak"
    trigger_phase = Phase.UPKEEP

    def cast_actions(self, state):
        return aura_enchant_actions(
            self, state, cost="{1}{U}",
            pred=lambda p: "enchantment" in p.type_line.lower())

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)

        def fn(st, opt):
            if opt == "pay" and can_afford(st, cost) and pay_cost(st, cost):
                st.emit("Power Leak: pay {2}, prevent all 2 damage")
            else:
                dealt = st.damage_self(2, colors=("U",))
                st.emit(f"Power Leak: {dealt} damage to you")
            return None

        return branch_over(state, ["pay", "take"], fn)
