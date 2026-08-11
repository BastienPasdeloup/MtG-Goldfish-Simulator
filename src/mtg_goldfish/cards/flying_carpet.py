"""Flying Carpet — {4} Artifact.
{2}, {T}: Target creature gains flying until end of turn.

Grants flying (temp_keywords) to one of your creatures for the turn — one branch
per distinct creature. Evasion is inert with no blockers, but the keyword is
genuinely granted."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class FlyingCarpet(Card):
    card_name = "Flying Carpet"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        acts = []
        seen: set[str] = set()
        for c in state.battlefield:
            if not c.is_creature_now or c.name in seen or "flying" in c.temp_keywords:
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
                        tgt.temp_keywords.add("flying")
                        st.emit(f"Flying Carpet: {nm} gains flying until end of turn")
                    return None

                return CardAction.activated(
                    f"Flying Carpet: {{2}}, {{T}} — {nm} gains flying",
                    pay, resolve, source_name="Flying Carpet",
                    ability_text="Target creature gains flying until end of turn")

            acts.append(make(c.uid, c.name))
        return acts
