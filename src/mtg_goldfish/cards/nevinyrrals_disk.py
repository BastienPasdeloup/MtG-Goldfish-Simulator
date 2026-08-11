"""Nevinyrral's Disk — {4} Artifact.
This artifact enters tapped.
{1}, {T}: Destroy all artifacts, creatures, and enchantments.

A symmetric board wipe — in a solitaire goldfish it destroys YOUR artifacts,
creatures, and enchantments (respecting indestructible/regeneration). Enters
tapped (auto-detected), so it can first activate the turn after it enters."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class NevinyrralsDisk(Card):
    card_name = "Nevinyrral's Disk"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            targets = [p for p in st.battlefield
                       if p.is_artifact or p.is_creature_now
                       or "enchantment" in p.type_line.lower()]
            for p in targets:
                st.leaves_battlefield(p, "graveyard", reason="destroy")
            st.emit(f"Nevinyrral's Disk: destroy all artifacts/creatures/enchantments ({len(targets)})")
            return None

        return [CardAction.activated(
            "Nevinyrral's Disk: {1}, {T} — destroy all artifacts, creatures, enchantments",
            pay, resolve, source_name="Nevinyrral's Disk",
            ability_text="Destroy all artifacts, creatures, and enchantments")]
