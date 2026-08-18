"""Inventors' Fair — Legendary Land.
At the beginning of your upkeep, if you control three or more artifacts, you
gain 1 life.
{T}: Add {C}.
{4}, {T}, Sacrifice Inventors' Fair: Search your library for an artifact card,
reveal it, put it into your hand, then shuffle. Activate only if you control
three or more artifacts."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class InventorsFair(Card):
    card_name = "Inventors' Fair"
    trigger_phase = Phase.UPKEEP

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def _artifact_count(self, state):
        return sum(1 for p in state.battlefield if p.is_artifact)

    def on_phase(self, state, perm, phase):
        # "At the beginning of your upkeep, if you control 3+ artifacts, gain 1 life."
        if self._artifact_count(state) >= 3:
            state.gain_life(1)
            state.emit("Inventors' Fair: gain 1 life (3+ artifacts)")
        return None

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost
        from ._common import artifact_ability_cost

        cost = artifact_ability_cost(state, ManaCost(generic=4), perm)
        if perm.tapped or self._artifact_count(state) < 3 or not can_afford(state, cost):
            return []

        seen: set[str] = set()
        acts: list[CardAction] = []
        for target in state.search_library(lambda c: c.is_artifact):
            if target.name in seen:
                continue
            seen.add(target.name)

            def build(name):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.tapped or self._artifact_count(st) < 3:
                        return False
                    p.tapped = True
                    if not pay_cost(st, cost):
                        return False
                    st.leaves_battlefield(p, "graveyard", reason="sacrifice")
                    return True

                def resolve(st):
                    card = next((c for c in st.library if c.name == name), None)
                    if card is None:
                        return None
                    st.take_from_library(card)
                    st.hand.append(card)
                    st.shuffle_library()
                    st.emit(f"Inventors' Fair: search up {name} to hand — shuffle")
                    return None

                return CardAction.activated(
                    f"Inventors' Fair: {{4}}, {{T}}, sacrifice — search up {name}",
                    pay, resolve, source_name="Inventors' Fair",
                    ability_text="Search your library for an artifact card, put it into your hand")

            acts.append(build(target.name))
        return acts
