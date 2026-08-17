"""Coral Helm — {3} Artifact.
{3}, Discard a card at random: Target creature gets +2/+2 until end of turn.

The random discard isn't a player choice, so a single card is discarded to model
it; one branch per distinct creature you control to buff."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import discard
from .base import Card, CardAction
from .registry import register


@register
class CoralHelm(Card):
    card_name = "Coral Helm"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3)
        if not state.hand or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        seen, targets = set(), []
        for p in state.battlefield:
            if p.is_creature_now and p.name not in seen:
                seen.add(p.name)
                targets.append(p.uid)
        acts = []
        for tuid in targets:
            tname = state.find_permanent(tuid).name

            def make(tuid=tuid):
                def pay(st):
                    if not st.hand or not pay_cost(st, cost, exclude_uids={perm.uid}):
                        return False
                    card = st.hand[0]  # discarded "at random" (not a choice)
                    st.hand.remove(card)
                    discard(st, card)
                    st.emit(f"Coral Helm: discard {card.name} at random")
                    return True

                def resolve(st):
                    t = st.find_permanent(tuid)
                    if t is not None:
                        t.temp_power += 2
                        t.temp_toughness += 2
                        st.emit(f"Coral Helm: {t.name} gets +2/+2")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Coral Helm: {{3}}, discard at random → {tname} gets +2/+2",
                pay, resolve, source_name="Coral Helm",
                ability_text="Target creature gets +2/+2 until end of turn"))
        return acts
