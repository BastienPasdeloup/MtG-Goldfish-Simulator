"""Flash — {1}{U} Instant. You may put a creature card from your hand onto the
battlefield. If you do, sacrifice it unless you pay its mana cost reduced by {2}.

A combo enabler: the creature enters (its ETB fires) and then you either pay the
reduced cost to keep it, or let it be sacrificed to the graveyard (reanimation
fuel). Branch over each creature in hand × keep/sacrifice."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Flash(Card):
    card_name = "Flash"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, pay_cost, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []
        acts, seen = [], set()
        for c in state.hand:
            if not c.is_creature or c.name in seen:
                continue
            seen.add(c.name)

            def make(name=c.name):
                def fn(st):
                    flash = next((x for x in st.hand if x.name == self.card_name), None)
                    creature = next((x for x in st.hand if x.name == name), None)
                    if flash is None or creature is None or not begin_cast(st, flash, cost):
                        return None
                    resolve_to_graveyard(st, flash)
                    st.hand.remove(creature)
                    perm = st.put_on_battlefield(
                        creature, fire_etb=False,
                        announce=f"Flash: put {name} onto the battlefield")
                    uid = perm.uid
                    st.queue_entry_triggers([perm])
                    etb = st.settle()
                    states = etb if etb is not None else [st]
                    # reduced cost = the creature's mana cost with {2} less generic
                    from ..engine.actions import _impl
                    base = _impl(creature).cast_cost(st)
                    reduced = ManaCost(generic=max(0, base.generic - 2), pips=base.pips)
                    out = []
                    for s in states:
                        # keep line: pay the reduced cost (if able)
                        keep = s.clone()
                        if keep.find_permanent(uid) is not None and pay_cost(keep, reduced):
                            keep.emit(f"Flash: pay {name}'s cost reduced by {{2}} — keep it")
                            out.append(keep)
                        # sacrifice line
                        sac = s.clone()
                        victim = sac.find_permanent(uid)
                        if victim is not None:
                            sac.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                            sac.emit(f"Flash: sacrifice {name}")
                        out.append(sac)
                    return out
                return fn

            acts.append(CardAction(f"cast Flash → {c.name}", make()))
        return acts
