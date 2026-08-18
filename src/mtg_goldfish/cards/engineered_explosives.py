"""Engineered Explosives — {X} Artifact.
Sunburst (enters with a charge counter for each color of mana spent to cast it).
{2}, Sacrifice this artifact: Destroy each nonland permanent with mana value
equal to the number of charge counters on this artifact.

The colours of mana spent aren't tracked, so sunburst is approximated as
min(X, number of colours in your commander identity) — the most a goldfish that
wants maximum counters could realistically spend. With no opponent the wrath
hits only YOUR nonland permanents of that mana value."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import any_identity_color, artifact_ability_cost, mv
from .base import Card, CardAction
from .registry import register


@register
class EngineeredExplosives(Card):
    card_name = "Engineered Explosives"

    def cast_actions(self, state):
        from ..engine.actions import available_mana_sources, begin_cast, can_afford, resolve_to_battlefield

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        colors = len(any_identity_color(state))
        acts = []
        for x in range(0, max(0, max_mana) + 1):
            cost = ManaCost(generic=x)
            if not can_afford(state, cost):
                continue
            counters = min(x, colors)  # sunburst approximation

            def make(xc, ctr):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, ManaCost(generic=xc)):
                        return None
                    return resolve_to_battlefield(st, card, marks={"charge": ctr}) or None
                return fn

            acts.append(CardAction(
                f"cast Engineered Explosives (X={x}, {counters} counter(s))",
                make(x, counters)))
        return acts

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = artifact_ability_cost(state, ManaCost(generic=2), perm)
        if not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or not pay_cost(st, cost):
                return False
            st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            n = perm.counters.get("charge", 0)
            victims = [p for p in list(st.battlefield)
                       if not p.is_land and mv(p.card) == n]
            for v in victims:
                st.emit(f"Engineered Explosives: destroy {v.name} (mv {n})")
                st.leaves_battlefield(v, "graveyard", reason="destroy")
            if not victims:
                st.emit(f"Engineered Explosives: nothing with mana value {n} to destroy")
            return None

        return [CardAction.activated(
            "Engineered Explosives: {2}, sacrifice — destroy MV = counters",
            pay, resolve, source_name="Engineered Explosives",
            ability_text="Destroy each nonland permanent with mana value = charge counters")]
