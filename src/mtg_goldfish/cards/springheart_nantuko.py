"""Springheart Nantuko — {1}{G} Enchantment Creature — Insect Monk 1/1.
Bestow {1}{G}. Landfall: if attached to a creature, you may pay {1}{G} to
copy that creature; otherwise create a 1/1 Insect. Cast as a plain creature
(bestow-from-hand onto a creature is a branch). Approximation: the landfall
copy is skipped; landfall while unattached makes the 1/1 Insect."""
from __future__ import annotations

from ._common import aura_on_creature_bestow_actions
from .base import Card
from .registry import register


@register
class SpringheartNantuko(Card):
    card_name = "Springheart Nantuko"

    def cast_actions(self, state):
        # Default cast (as a 1/1 creature) plus bestow onto each creature.
        from ..engine.actions import CastDefault, can_afford
        acts = []
        if can_afford(state, self.cast_cost(state)):
            acts.append(CastDefault(self.card_name))
        acts += aura_on_creature_bestow_actions(self, state, bestow_cost="{1}{G}")
        return acts

    def equip_mod(self, state, perm):
        return (1, 1) if perm.counters.get("bestowed") else (0, 0)

    def other_etb_stack_items(self, state, perm, entering):
        if "land" not in entering.type_line.lower() or perm.attached_to is not None:
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="Springheart Nantuko: landfall",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield",
            ability_text="Landfall — create a 1/1 Insect token",
        )]

    def on_other_etb(self, state, perm, entering):
        if "land" not in entering.type_line.lower():
            return
        if perm.attached_to is None:
            state.make_token("Insect", 1, 1, "Token Creature — Insect")
            state.emit("Springheart Nantuko: landfall — 1/1 Insect token")
