"""Staff of Zegon — {4} Artifact.
{3}, {T}: Target creature gets -2/-0 until end of turn.

One branch per distinct creature you control (the only legal targets in a
goldfish); a defensive/self-symmetric shrink."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class StaffOfZegon(Card):
    card_name = "Staff of Zegon"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
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
                    live = st.find_permanent(perm.uid)
                    if live is None or live.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                        return False
                    live.tapped = True
                    return True

                def resolve(st):
                    t = st.find_permanent(tuid)
                    if t is not None:
                        t.temp_power -= 2
                        st.emit(f"Staff of Zegon: {t.name} gets -2/-0")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Staff of Zegon: {{3}}, {{T}} → {tname} gets -2/-0",
                pay, resolve, source_name="Staff of Zegon",
                ability_text="Target creature gets -2/-0 until end of turn"))
        return acts
