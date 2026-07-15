"""Tireless Provisioner — {2}{G} Creature — Elf Scout 3/2.
Landfall: create a Food token or a Treasure token. Approximation: always
makes a Treasure (mana ramp is the useful mode in this deck) — landfall
triggers fire deep inside land resolution and can't branch the search."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TirelessProvisioner(Card):
    card_name = "Tireless Provisioner"

    def other_etb_stack_items(self, state, perm, entering):
        if not entering.is_land:
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="Tireless Provisioner: landfall",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield",
            ability_text="Landfall — create a Treasure token",
        )]

    def on_other_etb(self, state, perm, entering):
        if entering.is_land:
            state.make_token("Treasure", 0, 0, "Token Artifact — Treasure")
            state.emit("Tireless Provisioner: landfall — Treasure token")
