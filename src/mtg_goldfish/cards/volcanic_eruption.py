"""Volcanic Eruption — {X}{U}{U}{U} Sorcery.
Destroy X target Mountains. Volcanic Eruption deals damage to each creature and
each player equal to the number of Mountains put into a graveyard this way.

Only your own Mountains are available. One branch per affordable X: destroy up to
X of your Mountains, then deal that many damage to each creature (damage_permanent)
and each player (you via damage_self, the opponent via damage_opponent)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class VolcanicEruption(Card):
    card_name = "Volcanic Eruption"

    def cast_actions(self, state):
        from ..engine.actions import (available_mana_sources, begin_cast,
                                       can_afford, resolve_to_graveyard)

        mountains = sum(1 for p in state.battlefield
                        if p.is_land and "mountain" in p.type_line.lower())
        if mountains == 0:
            return []
        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(1, min(mountains, max(0, max_mana)) + 1):
            cost = ManaCost(generic=x, pips=(("U", 1), ("U", 1), ("U", 1)))
            if not can_afford(state, cost):
                continue

            def make(xx, c=cost):
                def fn(st):
                    card = next((k for k in st.hand if k.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, c):
                        return None
                    resolve_to_graveyard(st, card)
                    mtns = [p for p in st.battlefield
                            if p.is_land and "mountain" in p.type_line.lower()][:xx]
                    for m in mtns:
                        st.leaves_battlefield(m, "graveyard", reason="destroy")
                    n = len(mtns)
                    for p in list(st.battlefield):
                        if p.is_creature_now:
                            st.damage_permanent(p, n)
                    st.damage_self(n, colors=("U",))
                    st.damage_opponent(n)
                    st.note_crime()
                    st.emit(f"Volcanic Eruption: destroy {n} Mountains, {n} to each creature and player")
                    st.check_deaths()
                    return None
                return fn

            acts.append(CardAction(f"cast Volcanic Eruption (X={x})", make(x)))
        return acts
