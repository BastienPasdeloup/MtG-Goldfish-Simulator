"""Glacial Chasm — Land.
No mana. ETB: sacrifice a land (branch). Creatures you control can't attack.
Cumulative upkeep — pay 2 life per age counter or sacrifice it.
Approximation: "prevent all damage dealt to you" is a no-op (no opponent)."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class GlacialChasm(Card):
    card_name = "Glacial Chasm"

    prevents_attacks = True

    def phase_stack_items(self, state, perm, phase):
        if phase != Phase.UPKEEP:
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_phase(st, live, Phase.UPKEEP)

        return [self.stack_ability(
            source_name=perm.name,
            label="Glacial Chasm: cumulative upkeep",
            resolve=resolve,
            trigger_text="Beginning of your upkeep",
            ability_text="Cumulative upkeep — pay 2 life for each age counter or sacrifice Glacial Chasm",
        )]

    def on_etb(self, state, permanent):
        lands = {}
        for p in state.battlefield:
            if p.uid != permanent.uid and "land" in p.type_line.lower() and p.name not in lands:
                lands[p.name] = p.uid
        if not lands:
            return None

        def fn(st, uid):
            p = st.find_permanent(uid)
            if p is not None:
                st.emit(f"Glacial Chasm: sacrifice {p.name}")
                st.leaves_battlefield(p, "graveyard")

        return branch_over(state, list(lands.values()), fn)

    def on_phase(self, state, perm, phase):
        if phase != Phase.UPKEEP:
            return
        perm.counters["age"] = perm.counters.get("age", 0) + 1
        cost = 2 * perm.counters["age"]
        if state.life > cost:
            state.life -= cost
            state.emit(f"Glacial Chasm: cumulative upkeep — pay {cost} life")
        else:
            state.emit("Glacial Chasm: can't pay cumulative upkeep — sacrifice")
            state.leaves_battlefield(perm, "graveyard")
