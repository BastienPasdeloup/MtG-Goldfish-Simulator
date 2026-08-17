"""Detonate — {X}{R} Sorcery.
Destroy target artifact with mana value X. It can't be regenerated. Detonate deals
X damage to that artifact's controller.

X is fixed by the chosen target's mana value: one branch per distinct artifact you
control, each paying {mv}{R} and dealing that much damage to you (its controller)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import mv
from .base import Card, CardAction
from .registry import register


@register
class Detonate(Card):
    card_name = "Detonate"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        seen, targets = set(), []
        for p in state.battlefield:
            if p.is_artifact and p.name not in seen:
                seen.add(p.name)
                targets.append(p.uid)
        acts = []
        for tuid in targets:
            t0 = state.find_permanent(tuid)
            x = mv(t0.card)
            cost = ManaCost(generic=x, pips=(("R", 1),))
            if not can_afford(state, cost):
                continue

            def make(tuid=tuid, cost=cost, x=x):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, cost):
                        return None
                    resolve_to_graveyard(st, card)
                    t = st.find_permanent(tuid)
                    if t is not None:
                        t.counters.pop("regen_shield", None)
                        st.emit(f"Detonate: destroy {t.name}")
                        st.leaves_battlefield(t, "graveyard", reason="destroy")
                        if x > 0:
                            st.damage_self(x)
                            st.emit(f"Detonate: {x} damage to you ({st.life})")
                        st.check_deaths()
                    return None
                return fn

            acts.append(CardAction(
                f"cast Detonate (X={x}) → destroy {t0.name}", make()))
        return acts
