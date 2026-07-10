"""Detective's Phoenix — {2}{R} Enchantment Creature 2/2, flying, haste.
Castable normally. Bestow from the graveyard ({R} + collect evidence 6):
attaches to one of your creatures (+2/+2, flying, haste). Approximations:
evidence cards are exiled largest-mana-value-first (not enumerated), and the
"becomes a creature when unattached" clause is not modelled."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class DetectivesPhoenix(Card):
    card_name = "Detective's Phoenix"

    def equip_mod(self, state, perm):
        return (2, 2)

    def graveyard_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("R", 1),))
        if not can_afford(state, cost):
            return []
        others = [c for c in state.graveyard if c.name != self.card_name]
        if sum(int(c.cmc) for c in others) < 6:
            return []
        creatures = [p for p in state.battlefield if p.is_creature_now]

        def make(uid: int):
            def fn(st):
                card = next((c for c in st.graveyard if c.name == self.card_name), None)
                target = st.find_permanent(uid)
                if card is None or target is None or not pay_cost(st, cost):
                    return None
                # Collect evidence 6: exile graveyard cards, largest mv first.
                pool = sorted((c for c in st.graveyard if c.name != self.card_name),
                              key=lambda c: -c.cmc)
                total, used = 0, []
                for c in pool:
                    if total >= 6:
                        break
                    used.append(c)
                    total += int(c.cmc)
                if total < 6:
                    return None
                for c in used:
                    st.graveyard.remove(c)
                    st.exile.append(c)
                st.graveyard.remove(card)
                st.stack.append(card)
                st.spells_cast_this_turn += 1
                st.noncreature_spells_cast_this_turn += 1  # cast as an Aura
                st.storm_count += 1
                st.emit(f"bestow Detective's Phoenix from graveyard (evidence {total})")
                st.stack.remove(card)
                perm = st.put_on_battlefield(card, fire_etb=False)
                perm.attached_to = target.uid
                st.emit(f"Detective's Phoenix attached to {target.name} (+2/+2)")
                return None
            return fn

        # Label starts with "cast " so CardAction.apply treats this as a spell
        # cast (pay + resolve immediately) rather than an activated ability —
        # otherwise the whole cost would wrongly be paid at resolution.
        return [CardAction(f"cast Detective's Phoenix (bestow) → {c.name}", make(c.uid))
                for c in creatures]
