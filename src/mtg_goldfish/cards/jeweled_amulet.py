"""Jeweled Amulet — {0} Artifact.
{1}, {T}: Put a charge counter on this artifact. Note the type of mana spent to
pay this activation cost. Activate only if there are no charge counters on it.
{T}, Remove a charge counter from this artifact: Add one mana of its last noted
type.

A one-mana battery: charge it by paying {1} of some colour (noted on the
permanent), then later release that colour. One charge-branch per identity
colour (the colour you pay stores that colour)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class JeweledAmulet(Card):
    card_name = "Jeweled Amulet"

    def mana_abilities_perm(self, state, perm):
        # Release: {T}, Remove a charge counter: add one mana of the noted type.
        if perm.counters.get("charge", 0) >= 1 and perm.chosen:
            return [ManaAbility(amount=1, choices=(perm.chosen,))]
        return []

    def on_tap_for_mana(self, state, permanent, color):
        # Releasing the stored mana removes the charge counter.
        if permanent.counters.get("charge", 0) >= 1:
            permanent.counters["charge"] -= 1
            state.emit("Jeweled Amulet: remove a charge counter")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        # Charge: only if untapped and there are no charge counters on it.
        if perm.tapped or perm.counters.get("charge", 0) > 0:
            return []

        acts: list[CardAction] = []
        for color in any_identity_color(state):
            cost = ManaCost(pips=((color, 1),))  # pay {1} of this colour → note it
            if not can_afford(state, cost):
                continue

            def build(col, c=cost):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.tapped or p.counters.get("charge", 0) > 0:
                        return False
                    p.tapped = True
                    if not pay_cost(st, c):
                        return False
                    return True

                def resolve(st):
                    p = st.find_permanent(perm.uid)
                    if p is not None:
                        p.counters["charge"] = 1
                        p.chosen = col  # noted mana type
                        st.emit(f"Jeweled Amulet: charge (noted {{{col}}})")
                    return None

                return CardAction.activated(
                    f"Jeweled Amulet: {{1}}, {{T}} — charge (note {{{col}}})",
                    pay, resolve, source_name="Jeweled Amulet",
                    ability_text="Put a charge counter, note the mana type")

            acts.append(build(color))
        return acts
