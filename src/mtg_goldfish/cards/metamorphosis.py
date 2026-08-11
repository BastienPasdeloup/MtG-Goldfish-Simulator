"""Metamorphosis — {G} Sorcery.
As an additional cost to cast this spell, sacrifice a creature.
Add X mana of any one color, where X is 1 plus the sacrificed creature's mana
value. Spend this mana only to cast creature spells.

A ritual: sacrifice a creature (additional cost) to add (1 + its mana value) mana
of one chosen colour. One branch per (creature to sacrifice × colour). The
"spend only on creature spells" restriction isn't enforced (a benign
over-approximation — the mana just goes into the pool)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register

_COLORS = ("W", "U", "B", "R", "G")


@register
class Metamorphosis(Card):
    card_name = "Metamorphosis"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        creatures = []
        seen: set[str] = set()
        for p in state.battlefield:
            if p.is_creature_now and p.name not in seen:
                seen.add(p.name)
                creatures.append((p.uid, p.name, int(p.card.cmc or 0)))

        acts = []
        for uid, nm, mv in creatures:
            amount = 1 + mv
            for color in _COLORS:
                def make(uid=uid, nm=nm, amount=amount, color=color):
                    def fn(st):
                        card = next((c for c in st.hand if c.name == self.card_name), None)
                        victim = st.find_permanent(uid)
                        if card is None or victim is None or not begin_cast(st, card, self.mana_cost):
                            return None
                        resolve_to_graveyard(st, card)
                        st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                        st.mana_pool.add(color, amount)
                        st.emit(f"Metamorphosis: sacrifice {nm}, add {amount} {{{color}}}")
                        return None
                    return fn

                acts.append(CardAction(
                    f"cast Metamorphosis (sac {nm}) → {amount} {{{color}}}", make()))
        return acts
