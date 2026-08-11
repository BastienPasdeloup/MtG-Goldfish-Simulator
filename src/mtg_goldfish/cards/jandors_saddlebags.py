"""Jandor's Saddlebags — {2} Artifact.
{3}, {T}: Untap target creature.

Untaps one of your creatures (e.g. to re-use a {T} ability, or after it attacked)
— one branch per distinct tapped creature."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class JandorsSaddlebags(Card):
    card_name = "Jandor's Saddlebags"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        acts = []
        seen: set[str] = set()
        for c in state.battlefield:
            if not c.is_creature_now or not c.tapped or c.name in seen:
                continue
            seen.add(c.name)

            def make(uid, nm):
                def pay(st):
                    me = st.find_permanent(perm.uid)
                    if me is None or me.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                        return False
                    me.tapped = True
                    return True

                def resolve(st):
                    tgt = st.find_permanent(uid)
                    if tgt is not None:
                        tgt.tapped = False
                        st.emit(f"Jandor's Saddlebags: untap {nm}")
                    return None

                return CardAction.activated(
                    f"Jandor's Saddlebags: {{3}}, {{T}} — untap {nm}",
                    pay, resolve, source_name="Jandor's Saddlebags",
                    ability_text="Untap target creature")

            acts.append(make(c.uid, c.name))
        return acts
