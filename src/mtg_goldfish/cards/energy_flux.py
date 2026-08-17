"""Energy Flux — {2}{U} Enchantment.
All artifacts have "At the beginning of your upkeep, sacrifice this artifact unless
you pay {2}."

The granted upkeep tax is modelled as one triggered ability PER artifact you
control (Energy Flux itself is an enchantment, untaxed): each resolves as a branch
— pay {2} to keep it, or sacrifice it (forced sacrifice when you can't pay)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class EnergyFlux(Card):
    card_name = "Energy Flux"

    def phase_stack_items(self, state, perm, phase):
        if phase != Phase.UPKEEP:
            return []
        items = []
        for art in [p for p in state.battlefield if p.is_artifact]:
            items.append(self.stack_ability(
                source_name="Energy Flux",
                label=f"Energy Flux: upkeep tax on {art.name}",
                resolve=self._tax(art.uid),
                trigger_text="Energy Flux upkeep tax",
                ability_text="Sacrifice this artifact unless you pay {2}"))
        return items

    def _tax(self, auid):
        def resolve(st):
            from ..engine.actions import can_afford, pay_cost

            a = st.find_permanent(auid)
            if a is None:
                return None
            cost = ManaCost(generic=2)
            if not can_afford(st, cost):
                st.emit(f"Energy Flux: sacrifice {a.name} (can't pay {{2}})")
                st.leaves_battlefield(a, "graveyard", reason="sacrifice")
                return None

            def fn(s2, opt):
                aa = s2.find_permanent(auid)
                if aa is None:
                    return None
                if opt == "pay" and pay_cost(s2, cost):
                    s2.emit(f"Energy Flux: pay {{2}} to keep {aa.name}")
                else:
                    s2.emit(f"Energy Flux: sacrifice {aa.name}")
                    s2.leaves_battlefield(aa, "graveyard", reason="sacrifice")
                return None

            return branch_over(st, ["pay", "sac"], fn)

        return resolve
