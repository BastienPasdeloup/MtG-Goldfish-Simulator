"""Drain Life — {X}{1}{B} Sorcery. Spend only black mana on X.
Deals X damage to any target; you gain life equal to the damage dealt (capped by
the target's life total / toughness before the damage).

"Spend only black on X" is enforced by requiring X black pips. One branch per
(affordable X) × (target: the opponent, or one of your creatures)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class DrainLife(Card):
    card_name = "Drain Life"

    def cast_actions(self, state):
        from ..engine.actions import (available_mana_sources, begin_cast,
                                       can_afford, resolve_to_graveyard)

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(0, max(0, max_mana) + 1):
            # {X}{1}{B} with "spend only black on X" -> (X+1) black + 1 generic.
            cost = ManaCost(generic=1, pips=(("B", x + 1),))
            if not can_afford(state, cost):
                continue

            def make_opp(xx, c):
                def fn(st):
                    card = next((k for k in st.hand if k.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, c):
                        return None
                    resolve_to_graveyard(st, card)
                    before = st.opponent_life
                    dealt = st.damage_opponent(xx)
                    st.note_crime()
                    gain = min(dealt, max(0, before))
                    st.gain_life(gain)
                    st.emit(f"Drain Life: {dealt} damage to opponent, gain {gain} life")
                    return None
                return fn

            acts.append(CardAction(f"cast Drain Life (X={x}) → opponent", make_opp(x, cost)))

            seen: set[str] = set()
            for p in state.battlefield:
                if not p.is_creature_now or p.name in seen:
                    continue
                seen.add(p.name)

                def make_cr(xx, c, uid, nm):
                    def fn(st):
                        card = next((k for k in st.hand if k.name == self.card_name), None)
                        tgt = st.find_permanent(uid)
                        if card is None or tgt is None or not begin_cast(st, card, c):
                            return None
                        resolve_to_graveyard(st, card)
                        tough = st.effective_toughness(tgt)
                        st.damage_permanent(tgt, xx)
                        gain = min(xx, max(0, tough))
                        st.gain_life(gain)
                        st.emit(f"Drain Life: {xx} damage to {nm}, gain {gain} life")
                        st.check_deaths()
                        return None
                    return fn

                acts.append(CardAction(f"cast Drain Life (X={x}) → {p.name}",
                                       make_cr(x, cost, p.uid, p.name)))
        return acts
