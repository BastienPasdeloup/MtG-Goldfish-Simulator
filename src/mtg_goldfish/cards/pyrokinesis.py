"""Pyrokinesis — {4}{R}{R} Instant. You may exile a red card from your hand
rather than pay its mana cost. Deals 4 damage divided as you choose among any
number of target creatures. In a goldfish the targets are your own creatures
(useful to trigger deaths); the division is modelled as all 4 to one creature."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Pyrokinesis(Card):
    card_name = "Pyrokinesis"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford

        targets = {p.name: p.uid for p in state.battlefield if p.is_creature_now}
        if not targets:
            return []
        cost = self.cast_cost(state)
        red_fuel = [c for c in state.hand
                    if "R" in c.colors and c.name != self.card_name]

        def deal(st, uid):
            perm = st.find_permanent(uid)
            if perm is not None:
                perm.damage += 4
                st.emit(f"Pyrokinesis: 4 damage to {perm.name}")
                st.check_deaths()

        acts = []
        for tname, tuid in targets.items():
            if can_afford(state, cost):
                def mana_fn(st, tuid=tuid):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, cost):
                        return None
                    if card in st.stack:
                        st.stack.remove(card)
                    st.to_graveyard(card)
                    st.note_event("spell_resolved", card.name)
                    st.resolving = ("spell", card.name)
                    deal(st, tuid)
                    return None
                acts.append(CardAction(f"cast Pyrokinesis (mana) → {tname}", mana_fn))
            if red_fuel:
                def evoke_fn(st, tuid=tuid):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    fuel = sorted((c for c in st.hand
                                   if "R" in c.colors and c.name != self.card_name),
                                  key=lambda c: c.cmc)
                    if card is None or not fuel:
                        return None
                    st.hand.remove(fuel[0])
                    st.exile.append(fuel[0])
                    if not begin_cast(st, card, ManaCost(), tag="exile red card"):
                        return None
                    if card in st.stack:
                        st.stack.remove(card)
                    st.to_graveyard(card)
                    st.note_event("spell_resolved", card.name)
                    st.resolving = ("spell", card.name)
                    st.emit(f"Pyrokinesis: exile {fuel[0].name} instead of mana")
                    deal(st, tuid)
                    return None
                acts.append(CardAction(
                    f"cast Pyrokinesis (exile red) → {tname}", evoke_fn))
        return acts
