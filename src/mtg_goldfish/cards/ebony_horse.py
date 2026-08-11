"""Ebony Horse — {3} Artifact.
{2}, {T}: Untap target attacking creature you control. Prevent all combat damage
that would be dealt to and dealt by that creature this turn.

Untaps one of your attacking creatures (e.g. a non-vigilance attacker, so it's back
up to block / use a tap ability) and removes it from combat so it deals no combat
damage this turn — modelled by untapping it and removing it from `attackers`. One
branch per attacking creature."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class EbonyHorse(Card):
    card_name = "Ebony Horse"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        acts = []
        seen: set[str] = set()
        for c in state.battlefield:
            if c.uid not in state.attackers or c.name in seen:
                continue
            seen.add(c.name)

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
                        tgt.tapped = False
                        if tgt.uid in st.attackers:
                            st.attackers.remove(tgt.uid)  # its combat damage is prevented
                        st.emit(f"Ebony Horse: untap {nm}, prevent its combat damage")
                    return None

                return CardAction.activated(
                    f"Ebony Horse: {{2}}, {{T}} — untap attacking {nm}",
                    pay, resolve, source_name="Ebony Horse",
                    ability_text="Untap target attacking creature; prevent its combat damage")

            acts.append(make(c.uid, c.name))
        return acts
