"""Dwarven Weaponsmith — {1}{R} Creature — Dwarf Artificer 1/1.
{T}, Sacrifice an artifact: Put a +1/+1 counter on target creature. Activate only
during your upkeep.

One branch per (artifact to sacrifice) × (creature to receive the counter);
upkeep only."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class DwarvenWeaponsmith(Card):
    card_name = "Dwarven Weaponsmith"

    def battlefield_actions(self, state, perm):
        if perm.tapped or state.phase != Phase.UPKEEP:
            return []
        arts = {}
        for p in state.battlefield:
            if p.is_artifact:
                arts.setdefault(p.name, p.uid)
        creatures = {}
        for p in state.battlefield:
            if p.is_creature_now:
                creatures.setdefault(p.name, p.uid)
        if not arts or not creatures:
            return []
        acts = []
        for aname, auid in arts.items():
            for cname, cuid in creatures.items():
                def make(auid=auid, cuid=cuid):
                    def pay(st):
                        src = st.find_permanent(perm.uid)
                        victim = st.find_permanent(auid)
                        if src is None or victim is None or src.tapped:
                            return False
                        src.tapped = True
                        st.emit(f"Dwarven Weaponsmith: sacrifice {victim.name}")
                        st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                        return True

                    def resolve(st):
                        t = st.find_permanent(cuid)
                        if t is not None:
                            t.counters["+1/+1"] = t.counters.get("+1/+1", 0) + 1
                            st.emit(f"Dwarven Weaponsmith: +1/+1 counter on {t.name}")
                        return None
                    return pay, resolve

                pay, resolve = make()
                acts.append(CardAction.activated(
                    f"Dwarven Weaponsmith: {{T}}, sac {aname} → +1/+1 counter on {cname}",
                    pay, resolve, source_name="Dwarven Weaponsmith",
                    ability_text="Put a +1/+1 counter on target creature"))
        return acts
