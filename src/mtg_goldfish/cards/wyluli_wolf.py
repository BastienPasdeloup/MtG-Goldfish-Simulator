"""Wyluli Wolf — {1}{G} Creature — Wolf 1/1.
{T}: Target creature gets +1/+1 until end of turn.

A repeatable pump: {T} to give one of your creatures +1/+1 for the turn (one
branch per distinct creature, including itself)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class WyluliWolf(Card):
    card_name = "Wyluli Wolf"

    def battlefield_actions(self, state, perm):
        if perm.tapped or perm.summoning_sick:
            return []
        acts = []
        seen: set[str] = set()
        for c in state.battlefield:
            if not c.is_creature_now or c.name in seen:
                continue
            seen.add(c.name)

            def make(uid, nm):
                def pay(st):
                    me = st.find_permanent(perm.uid)
                    if me is None or me.tapped or me.summoning_sick:
                        return False
                    me.tapped = True
                    return True

                def resolve(st):
                    tgt = st.find_permanent(uid)
                    if tgt is not None:
                        tgt.temp_power += 1
                        tgt.temp_toughness += 1
                        st.emit(f"Wyluli Wolf: {nm} gets +1/+1 until end of turn")
                    return None

                return CardAction.activated(
                    f"Wyluli Wolf: {{T}} — {nm} gets +1/+1",
                    pay, resolve, source_name="Wyluli Wolf",
                    ability_text="Target creature gets +1/+1 until end of turn")

            acts.append(make(c.uid, c.name))
        return acts
