"""Mishra's War Machine — {7} Artifact Creature — Juggernaut 5/5, Banding.
At the beginning of your upkeep, this creature deals 3 damage to you unless you
discard a card. If it deals damage to you this way, tap it.

Upkeep branch: discard a card (one branch per distinct card in hand) to avoid the
damage, or take 3 and tap it."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import branch_over, discard
from .base import Card
from .registry import register


@register
class MishrasWarMachine(Card):
    card_name = "Mishra's War Machine"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        names, seen = [], set()
        for c in state.hand:
            if c.name not in seen:
                seen.add(c.name)
                names.append(c.name)
        options = ["take"] + [f"discard:{n}" for n in names]

        def fn(st, opt):
            if opt == "take":
                live = st.find_permanent(perm.uid)
                dealt = st.damage_self(3)
                if live is not None:
                    live.tapped = True
                st.emit(f"Mishra's War Machine: take {dealt} damage and tap ({st.life})")
                return None
            name = opt.split(":", 1)[1]
            card = next((c for c in st.hand if c.name == name), None)
            if card is not None:
                st.hand.remove(card)
                discard(st, card)
                st.emit(f"Mishra's War Machine: discard {name}")
            return None

        return branch_over(state, options, fn)
