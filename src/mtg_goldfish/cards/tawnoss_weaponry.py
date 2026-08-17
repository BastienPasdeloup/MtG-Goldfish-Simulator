"""Tawnos's Weaponry — {2} Artifact.
You may choose not to untap this artifact during your untap step.
{2}, {T}: Target creature gets +1/+1 for as long as this artifact remains tapped.

The buff is tied to this artifact staying tapped: activating taps it and records
the target, and `static_pt_bonus` grants +1/+1 to that creature only while the
source is tapped (it ends when the artifact untaps next turn). One branch per
distinct creature you control."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class TawnossWeaponry(Card):
    card_name = "Tawnos's Weaponry"

    def static_pt_bonus(self, state, source, perm):
        if source.tapped and perm.uid == source.counters.get("_buff_target"):
            return (1, 1)
        return (0, 0)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
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
                    src = st.find_permanent(perm.uid)
                    if src is None or src.tapped or not pay_cost(st, cost, exclude_uids={src.uid}):
                        return False
                    src.tapped = True
                    return True

                def resolve(st):
                    src = st.find_permanent(perm.uid)
                    t = st.find_permanent(tuid)
                    if src is not None and t is not None:
                        src.counters["_buff_target"] = tuid
                        st.emit(f"Tawnos's Weaponry: {t.name} gets +1/+1 while this stays tapped")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Tawnos's Weaponry: {{2}}, {{T}} → {tname} gets +1/+1 (while tapped)",
                pay, resolve, source_name="Tawnos's Weaponry",
                ability_text="Target creature gets +1/+1 for as long as this artifact remains tapped"))
        return acts
