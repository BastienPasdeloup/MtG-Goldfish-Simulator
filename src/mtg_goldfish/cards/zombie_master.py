"""Zombie Master — {1}{B}{B} Creature — Zombie 2/3.
Other Zombie creatures have swampwalk.
Other Zombies have "{B}: Regenerate this permanent."

Swampwalk is evasion (inert). The granted regeneration ability is modelled by
offering, from Zombie Master, a "{B}: regenerate <other Zombie>" action for each
other Zombie you control (banks a regen shield on it)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class ZombieMaster(Card):
    card_name = "Zombie Master"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("B", 1),))
        if not can_afford(state, cost):
            return []
        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if (p.uid == perm.uid or not p.is_creature_now
                    or "zombie" not in p.type_line.lower()
                    or p.counters.get("regen_shield") or p.name in seen):
                continue
            seen.add(p.name)

            def make(uid, nm):
                def pay(st):
                    return pay_cost(st, cost)

                def resolve(st):
                    tgt = st.find_permanent(uid)
                    if tgt is not None:
                        tgt.counters["regen_shield"] = 1
                        st.emit(f"Zombie Master: regeneration shield on {nm}")
                    return None

                return CardAction.activated(
                    f"Zombie Master: {{B}} — regenerate {nm}",
                    pay, resolve, source_name="Zombie Master",
                    ability_text="Regenerate target Zombie")

            acts.append(make(p.uid, p.name))
        return acts
