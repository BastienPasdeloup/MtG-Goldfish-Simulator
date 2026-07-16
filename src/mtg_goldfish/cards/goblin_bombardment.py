"""Goblin Bombardment — {1}{R} Enchantment.
Sacrifice a creature: Goblin Bombardment deals 1 damage to any target
(the opponent, or one of your creatures — a branch per victim/target pair)."""
from __future__ import annotations

from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class GoblinBombardment(Card):
    card_name = "Goblin Bombardment"

    def battlefield_actions(self, state, perm):
        victims: dict[str, int] = {}
        for p in state.battlefield:
            if p.is_creature_now:
                victims.setdefault(p.name, p.uid)
        if not victims:
            return []

        acts = []
        for vname, vuid in victims.items():
            for suffix, apply in damage_any_target_options(state):

                def make(vuid=vuid, apply=apply):
                    def pay(st):
                        victim = st.find_permanent(vuid)
                        if victim is None:
                            return False
                        st.emit(f"sacrifice {victim.name}")
                        st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                        return True

                    def resolve(st):
                        apply(st, 1)
                        return None
                    return pay, resolve

                pay, resolve = make()
                acts.append(CardAction.activated(
                    f"Goblin Bombardment: sac {vname} → 1 dmg to {suffix}",
                    pay, resolve,
                    source_name="Goblin Bombardment",
                    ability_text="Deal 1 damage to any target"))
        return acts
