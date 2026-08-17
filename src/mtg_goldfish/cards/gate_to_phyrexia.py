"""Gate to Phyrexia — {B}{B} Enchantment.
Sacrifice a creature: Destroy target artifact. Activate only during your upkeep
and only once each turn.

Upkeep-only, once per turn: sacrifice a creature to destroy an artifact (your own
in a goldfish) — one branch per (creature to sacrifice) × (artifact to destroy)."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class GateToPhyrexia(Card):
    card_name = "Gate to Phyrexia"

    def battlefield_actions(self, state, perm):
        if state.phase != Phase.UPKEEP or perm.turn_flags.get("gate_used"):
            return []
        creatures = {}
        for p in state.battlefield:
            if p.is_creature_now:
                creatures.setdefault(p.name, p.uid)
        arts = {}
        for p in state.battlefield:
            if p.is_artifact:
                arts.setdefault(p.name, p.uid)
        if not creatures or not arts:
            return []
        acts = []
        for cname, cuid in creatures.items():
            for aname, auid in arts.items():
                def make(cuid=cuid, auid=auid):
                    def pay(st):
                        src = st.find_permanent(perm.uid)
                        victim = st.find_permanent(cuid)
                        if src is None or victim is None or src.turn_flags.get("gate_used"):
                            return False
                        src.turn_flags["gate_used"] = 1
                        st.emit(f"Gate to Phyrexia: sacrifice {victim.name}")
                        st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                        return True

                    def resolve(st):
                        t = st.find_permanent(auid)
                        if t is not None:
                            st.emit(f"Gate to Phyrexia: destroy {t.name}")
                            st.leaves_battlefield(t, "graveyard", reason="destroy")
                            st.check_deaths()
                        return None
                    return pay, resolve

                pay, resolve = make()
                acts.append(CardAction.activated(
                    f"Gate to Phyrexia: sac {cname} → destroy {aname}",
                    pay, resolve, source_name="Gate to Phyrexia",
                    ability_text="Sacrifice a creature: destroy target artifact"))
        return acts
