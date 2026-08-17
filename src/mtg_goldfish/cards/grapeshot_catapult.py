"""Grapeshot Catapult — {4} Artifact Creature — Construct 2/3.
{T}: This creature deals 1 damage to target creature with flying.

Legal targets are your own creatures with flying (the phantom opponent has none),
so it mostly matters as an on-board pinger of your fliers — one branch each."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class GrapeshotCatapult(Card):
    card_name = "Grapeshot Catapult"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        seen, targets = set(), []
        for p in state.battlefield:
            if p.is_creature_now and state.has_keyword(p, "flying") and p.name not in seen:
                seen.add(p.name)
                targets.append(p.uid)
        acts = []
        for tuid in targets:
            tname = state.find_permanent(tuid).name

            def make(tuid=tuid):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.tapped:
                        return False
                    p.tapped = True
                    return True

                def resolve(st):
                    t = st.find_permanent(tuid)
                    if t is not None:
                        st.damage_permanent(t, 1)
                        st.emit(f"Grapeshot Catapult: 1 damage to {t.name}")
                        st.check_deaths()
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Grapeshot Catapult: {{T}} → 1 damage to {tname}",
                pay, resolve, source_name="Grapeshot Catapult",
                ability_text="Deal 1 damage to target creature with flying"))
        return acts
