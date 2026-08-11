"""Northern Paladin — {2}{W}{W} Creature — Human Knight 3/3.
{W}{W}, {T}: Destroy target black permanent.

A 3/3 with a {W}{W},{T} destroy-black ability. Only your own black permanents are
available in a solitaire goldfish (rarely worth it, but the ability is offered).
One branch per distinct black permanent you control."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class NorthernPaladin(Card):
    card_name = "Northern Paladin"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.tapped or perm.summoning_sick:
            return []
        cost = ManaCost(pips=(("W", 1), ("W", 1)))
        if not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if "B" not in p.colors or p.name in seen:
                continue
            seen.add(p.name)

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
                        st.emit(f"Northern Paladin: destroy {nm}")
                        st.leaves_battlefield(tgt, "graveyard", reason="destroy")
                    return None

                return CardAction.activated(
                    f"Northern Paladin: {{W}}{{W}}, {{T}} — destroy {nm}",
                    pay, resolve, source_name="Northern Paladin",
                    ability_text="Destroy target black permanent")

            acts.append(make(p.uid, p.name))
        return acts
