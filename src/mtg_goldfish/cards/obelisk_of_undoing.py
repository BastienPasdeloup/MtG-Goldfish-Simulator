"""Obelisk of Undoing — {1} Artifact.
{6}, {T}: Return target permanent you both own and control to your hand.

Bounce one of your own permanents to hand (re-buy an enters-the-battlefield
effect) — one branch per distinct permanent you control; tokens returned this way
cease to exist."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class ObeliskOfUndoing(Card):
    card_name = "Obelisk of Undoing"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=6)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        seen, targets = set(), []
        for p in state.battlefield:
            if p.name not in seen:
                seen.add(p.name)
                targets.append(p.uid)
        acts = []
        for tuid in targets:
            tname = state.find_permanent(tuid).name

            def make(tuid=tuid):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    if src is None or src.tapped or not pay_cost(st, cost, exclude_uids={src.uid}):
                        return False
                    src.tapped = True
                    return True

                def resolve(st):
                    t = st.find_permanent(tuid)
                    if t is not None:
                        st.emit(f"Obelisk of Undoing: return {t.name} to hand")
                        st.leaves_battlefield(t, "hand", reason=None)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Obelisk of Undoing: {{6}}, {{T}} → return {tname} to hand",
                pay, resolve, source_name="Obelisk of Undoing",
                ability_text="Return target permanent you own and control to your hand"))
        return acts
