"""Ashnod's Battle Gear — {2} Artifact.
You may choose not to untap this artifact during your untap step.
{2}, {T}: Target creature you control gets +2/-2 for as long as this artifact
remains tapped.

Same tapped-tied buff pattern as Tawnos's Weaponry, granting +2/-2 (via
`static_pt_bonus` while the source stays tapped). The -2 toughness can be lethal —
`check_deaths` runs after it applies."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class AshnodsBattleGear(Card):
    card_name = "Ashnod's Battle Gear"

    def static_pt_bonus(self, state, source, perm):
        if source.tapped and perm.uid == source.counters.get("_buff_target"):
            return (2, -2)
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
                        st.emit(f"Ashnod's Battle Gear: {t.name} gets +2/-2 while this stays tapped")
                        st.check_deaths()
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Ashnod's Battle Gear: {{2}}, {{T}} → {tname} gets +2/-2 (while tapped)",
                pay, resolve, source_name="Ashnod's Battle Gear",
                ability_text="Target creature you control gets +2/-2 for as long as this artifact remains tapped"))
        return acts
