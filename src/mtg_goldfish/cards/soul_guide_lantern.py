"""Soul-Guide Lantern — {1} Artifact.
When this artifact enters, exile target card from a graveyard.
{T}, Sacrifice this artifact: Exile each opponent's graveyard.
{1}, {T}, Sacrifice this artifact: Draw a card.

The opponent-graveyard exile is a no-op (no opponent). The ETB exile is mandatory
if there's a legal target in your graveyard; it takes the least useful card
(prefer a nonartifact, so Emry keeps her artifacts). The draw ability is the
useful mode."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class SoulGuideLantern(Card):
    card_name = "Soul-Guide Lantern"

    def on_etb(self, state, permanent):
        # "Exile target card from a graveyard" — only your graveyard exists.
        if not state.graveyard:
            return None
        # Prefer to exile a nonartifact (keep artifacts for Emry); else the
        # lowest-mana-value card.
        pool = [c for c in state.graveyard if not c.is_artifact] or list(state.graveyard)
        victim = min(pool, key=lambda c: (c.cmc, c.name))
        state.graveyard.remove(victim)
        state.exile.append(victim)
        state.emit(f"Soul-Guide Lantern: exile {victim.name} from your graveyard")
        return None

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
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
            st.emit("Soul-Guide Lantern: draw a card")
            st.draw(1)
            return None

        return [CardAction.activated(
            "Soul-Guide Lantern: {1}, {T}, sacrifice — draw a card",
            pay, resolve, source_name="Soul-Guide Lantern",
            ability_text="Draw a card")]
