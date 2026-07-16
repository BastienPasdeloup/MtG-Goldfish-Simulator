"""Spymaster's Vault — Land. Enters tapped unless you control a Swamp. {T}: Add {B}.
{B}, {T}: Target creature you control connives X, where X is the number of
creatures that died this turn (draw X, discard X, +1/+1 per nonland discarded).

Approximation: the target is the creature you control with the greatest power,
and the X discards are chosen deterministically (lands first, then the
highest-mana-value cards) rather than branched."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register


def _creatures_died_this_turn(state) -> int:
    return sum(
        1 for e in state.events
        if e["turn"] == state.turn and e["kind"] == "leave_battlefield"
        and e.get("is_creature") and e.get("to") == "graveyard"
    )


@register
class SpymastersVault(Card):
    card_name = "Spymaster's Vault"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("B",))]

    def etb_tapped(self, state):
        from ._common import perm_has_subtype
        return not any(p.is_land and perm_has_subtype(p, ("Swamp",))
                       for p in state.battlefield)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("B", 1),))
        x = _creatures_died_this_turn(state)
        if perm.tapped or x <= 0 or not can_afford(state, cost):
            return []
        creatures = [p for p in state.battlefield if p.is_creature_now]
        if not creatures:
            return []
        target = max(creatures, key=lambda p: state.effective_power(p))

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            p.tapped = True
            return True

        def resolve(st, uid=target.uid, n=x):
            tgt = st.find_permanent(uid)
            if tgt is None:
                return None
            st.draw(n)
            # Discard n cards: lands first, then the highest-mana-value cards.
            to_discard = sorted(
                st.hand, key=lambda c: (not c.is_land, c.cmc), reverse=True
            )[:n]
            nonland = 0
            for c in to_discard:
                st.hand.remove(c)
                st.to_graveyard(c)
                if not c.is_land:
                    nonland += 1
            if nonland:
                tgt.counters["+1/+1"] = tgt.counters.get("+1/+1", 0) + nonland
            st.emit(f"Spymaster's Vault: {tgt.name} connives {n} "
                    f"(+{nonland}/+{nonland})")
            return None

        return [CardAction.activated(
            f"Spymaster's Vault: {target.name} connives {x}",
            pay,
            resolve,
            source_name="Spymaster's Vault",
            ability_text=f"Target creature connives {x}",
        )]
