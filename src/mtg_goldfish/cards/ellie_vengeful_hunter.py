"""Ellie, Vengeful Hunter — {1}{B}{R} Legendary Creature 3/1. Partner—Survivors.
Pay 2 life, Sacrifice another creature: Ellie deals 2 damage to target player and
gains indestructible until end of turn."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class EllieVengefulHunter(Card):
    card_name = "Ellie, Vengeful Hunter"

    def battlefield_actions(self, state, perm):
        if state.life <= 2:
            return []
        victims: dict[str, int] = {}
        for p in state.battlefield:
            if p.uid != perm.uid and p.is_creature_now:
                victims.setdefault(p.name, p.uid)
        if not victims:
            return []

        acts = []
        for vname, vuid in victims.items():

            def make(vuid=vuid):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    victim = st.find_permanent(vuid)
                    if src is None or victim is None or st.life <= 2:
                        return False
                    st.life -= 2
                    st.emit(f"Ellie: pay 2 life ({st.life}), sacrifice {victim.name}")
                    st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                    return True

                def resolve(st):
                    src = st.find_permanent(perm.uid)
                    st.damage_opponent(2)  # noncombat -> amplifiers apply
                    st.note_crime()
                    if src is not None:
                        src.temp_keywords.add("indestructible")
                    st.emit(f"Ellie: 2 damage to opponent ({st.opponent_life}), "
                            f"gains indestructible")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Ellie, Vengeful Hunter: sac {vname} → 2 dmg to opponent",
                pay, resolve,
                source_name="Ellie, Vengeful Hunter",
                ability_text="Deal 2 damage to target player; gain indestructible"))
        return acts
