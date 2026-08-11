"""Stone of Erech — {1} Legendary Artifact.
If a creature an opponent controls would die, exile it instead.
{2}, {T}, Sacrifice Stone of Erech: Exile target player's graveyard. Draw a card.

The static only affects opponents (no goldfish effect). The ability's draw is the
value; it also exiles a graveyard — targeting yourself costs you your graveyard
(a downside for Emry the search weighs against the card)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class StoneOfErech(Card):
    card_name = "Stone of Erech"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            p.tapped = True
            st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            keep = next((c for c in st.graveyard if c.name == "Stone of Erech"), None)
            exiled = [c for c in list(st.graveyard) if c is not keep]
            for c in exiled:
                st.graveyard.remove(c)
                st.exile.append(c)
            st.emit(f"Stone of Erech: exile your graveyard ({len(exiled)} card(s)), draw a card")
            st.draw(1)
            return None

        return [CardAction.activated(
            "Stone of Erech: {2}, {T}, sacrifice — exile a graveyard, draw a card",
            pay, resolve, source_name="Stone of Erech",
            ability_text="Exile target player's graveyard; draw a card")]
