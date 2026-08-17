"""Orcish Mechanics — {2}{R} Creature — Orc 1/1.
{T}, Sacrifice an artifact: This creature deals 2 damage to any target.

One branch per (artifact to sacrifice) × (target): the opponent, or a creature
you control."""
from __future__ import annotations

from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class OrcishMechanics(Card):
    card_name = "Orcish Mechanics"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        arts = {}
        for p in state.battlefield:
            if p.is_artifact:
                arts.setdefault(p.name, p.uid)
        if not arts:
            return []
        acts = []
        for aname, auid in arts.items():
            for suffix, apply in damage_any_target_options(state):
                def make(auid=auid, apply=apply):
                    def pay(st):
                        src = st.find_permanent(perm.uid)
                        victim = st.find_permanent(auid)
                        if src is None or victim is None or src.tapped:
                            return False
                        src.tapped = True
                        st.emit(f"Orcish Mechanics: sacrifice {victim.name}")
                        st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                        return True

                    def resolve(st):
                        apply(st, 2)
                        return None
                    return pay, resolve

                pay, resolve = make()
                acts.append(CardAction.activated(
                    f"Orcish Mechanics: {{T}}, sac {aname} → 2 damage to {suffix}",
                    pay, resolve, source_name="Orcish Mechanics",
                    ability_text="Deal 2 damage to any target"))
        return acts
