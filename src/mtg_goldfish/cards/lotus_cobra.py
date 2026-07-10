"""Lotus Cobra — {1}{G} Creature — Snake 2/1.
Landfall: add one mana of any color (identity — goes to the pool, usable
this phase; the payment planner does not anticipate it)."""
from __future__ import annotations

from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class LotusCobra(Card):
    card_name = "Lotus Cobra"

    def other_etb_stack_items(self, state, perm, entering):
        if "land" not in entering.type_line.lower():
            return []
        color = any_identity_color(state)[0]

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="Lotus Cobra: landfall",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield",
            ability_text=f"Landfall — add {{{color}}}",
        )]

    def on_other_etb(self, state, perm, entering):
        if "land" in entering.type_line.lower():
            color = any_identity_color(state)[0]
            state.mana_pool.add(color, 1)
            state.emit(f"Lotus Cobra: landfall — add {{{color}}}")
