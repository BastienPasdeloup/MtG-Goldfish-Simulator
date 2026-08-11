"""Pirate Ship — {4}{U} Creature — Human Pirate 4/3.
This creature can't attack unless defending player controls an Island.
{T}: This creature deals 1 damage to any target.
When you control no Islands, sacrifice this creature.

The attack restriction depends on the opponent's Islands (never any → it can't
attack), but its {T} pinger is real (1 damage to any target). The "sacrifice if
you control no Islands" clause is checked at your upkeep (approximating the
state-trigger): with no Island of your own it is sacrificed."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


def _controls_island(state) -> bool:
    return any(p.is_land and "island" in p.type_line.lower() for p in state.battlefield)


@register
class PirateShip(Card):
    card_name = "Pirate Ship"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        if not _controls_island(state):
            p = state.find_permanent(perm.uid)
            if p is not None:
                state.emit("Pirate Ship: no Island — sacrifice")
                state.leaves_battlefield(p, "graveyard", reason="sacrifice")
        return None

    def battlefield_actions(self, state, perm):
        if perm.tapped or perm.summoning_sick:
            return []
        acts = []
        for suffix, apply in damage_any_target_options(state):
            def make(apply=apply):
                def pay(st):
                    live = st.find_permanent(perm.uid)
                    if live is None or live.tapped or live.summoning_sick:
                        return False
                    live.tapped = True
                    return True

                def resolve(st):
                    apply(st, 1)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Pirate Ship: {{T}} → 1 damage to {suffix}",
                pay, resolve, source_name="Pirate Ship",
                ability_text="Deal 1 damage to any target"))
        return acts
