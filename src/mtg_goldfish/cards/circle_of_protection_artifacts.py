"""Circle of Protection: Artifacts — {1}{W} Enchantment.
{2}: The next time an artifact source of your choice would deal damage to you this
turn, prevent that damage.

Each activation banks one "prevent the next artifact-damage instance" shield
(`state.artifact_prevent_instances`), consumed by `damage_self(by_artifact=True)`."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class CircleOfProtectionArtifacts(Card):
    card_name = "Circle of Protection: Artifacts"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            st.artifact_prevent_instances += 1
            st.emit("Circle of Protection: Artifacts — prevent the next artifact damage this turn")
            return None

        return [CardAction.activated(
            "Circle of Protection: Artifacts: {2} — prevent the next artifact damage",
            pay, resolve, source_name="Circle of Protection: Artifacts",
            ability_text="Prevent the next artifact-source damage to you this turn")]
