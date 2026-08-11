"""Cyclopean Tomb — {4} Artifact.
{2}, {T}: Put a mire counter on target non-Swamp land. That land is a Swamp for as
long as it has a mire counter on it. Activate only during your upkeep.
When this artifact is put into a graveyard from the battlefield, at the beginning
of each of your upkeeps for the rest of the game, remove all mire counters ...

The core is modelled: {2}, {T} turns one of your non-Swamp lands into a Swamp
(mana_override "B" + a mire counter) — real black fixing. One branch per distinct
non-Swamp land. The "only during your upkeep" restriction and the rest-of-game
un-miring after it dies are not modelled (both simplifications favour the search
only mildly)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class CyclopeanTomb(Card):
    card_name = "Cyclopean Tomb"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        acts = []
        seen: set[str] = set()
        for land in state.battlefield:
            if (not land.is_land or "swamp" in land.type_line.lower()
                    or land.mana_override == "B" or land.name in seen):
                continue
            seen.add(land.name)

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
                        tgt.mana_override = "B"
                        tgt.counters["mire"] = tgt.counters.get("mire", 0) + 1
                        st.emit(f"Cyclopean Tomb: {nm} becomes a Swamp (mire counter)")
                    return None

                return CardAction.activated(
                    f"Cyclopean Tomb: {{2}}, {{T}} — {nm} becomes a Swamp",
                    pay, resolve, source_name="Cyclopean Tomb",
                    ability_text="Target non-Swamp land becomes a Swamp")

            acts.append(make(land.uid, land.name))
        return acts
