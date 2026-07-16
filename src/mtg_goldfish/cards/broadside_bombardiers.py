"""Broadside Bombardiers — {2}{R} Creature 2/2, menace, haste.
Boast — Sacrifice another creature or artifact: This creature deals damage equal
to 2 plus the sacrificed permanent's mana value to any target. (Only if it
attacked this turn, and only once each turn.)"""
from __future__ import annotations

from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class BroadsideBombardiers(Card):
    card_name = "Broadside Bombardiers"

    def battlefield_actions(self, state, perm):
        if not perm.turn_flags.get("attacked") or perm.turn_flags.get("boasted"):
            return []
        victims: dict[str, tuple[int, int]] = {}
        for p in state.battlefield:
            if p.uid == perm.uid:
                continue
            if p.is_creature_now or "artifact" in p.type_line.lower():
                victims.setdefault(p.name, (p.uid, int(p.card.cmc)))
        if not victims:
            return []

        acts = []
        for vname, (vuid, vmv) in victims.items():
            dmg = 2 + vmv
            for suffix, apply in damage_any_target_options(state):

                def make(vuid=vuid, apply=apply, dmg=dmg):
                    def pay(st):
                        src = st.find_permanent(perm.uid)
                        victim = st.find_permanent(vuid)
                        if src is None or victim is None or src.turn_flags.get("boasted"):
                            return False
                        src.turn_flags["boasted"] = 1
                        st.emit(f"sacrifice {victim.name} (boast)")
                        st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                        return True

                    def resolve(st):
                        apply(st, dmg)
                        return None
                    return pay, resolve

                pay, resolve = make()
                acts.append(CardAction.activated(
                    f"Broadside Bombardiers: boast sac {vname} → {dmg} dmg to {suffix}",
                    pay, resolve,
                    source_name="Broadside Bombardiers",
                    ability_text=f"Deal {dmg} damage to any target"))
        return acts
