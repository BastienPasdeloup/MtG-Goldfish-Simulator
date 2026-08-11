"""Pestilence — {2}{B}{B} Enchantment.
At the beginning of the end step, if no creatures are on the battlefield,
sacrifice this enchantment.
{B}: This enchantment deals 1 damage to each creature and each player.

Repeatable symmetric pinger: {B} deals 1 to each creature (via damage_permanent,
so Fungusaur-style triggers fire) and 1 to each player (you via damage_self, the
opponent via damage_opponent). If it ever leaves no creatures on the battlefield,
it sacrifices itself at end step."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class Pestilence(Card):
    card_name = "Pestilence"
    trigger_phase = Phase.END_STEP

    def on_phase(self, state, perm, phase):
        if not any(p.is_creature_now for p in state.battlefield):
            p = state.find_permanent(perm.uid)
            if p is not None:
                state.emit("Pestilence: no creatures — sacrifice")
                state.leaves_battlefield(p, "graveyard", reason="sacrifice")
        return None

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("B", 1),))
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            for p in list(st.battlefield):
                if p.is_creature_now:
                    st.damage_permanent(p, 1)
            st.damage_self(1, colors=("B",))
            st.damage_opponent(1)
            st.note_crime()
            st.emit("Pestilence: 1 damage to each creature and each player")
            st.check_deaths()
            return None

        return [CardAction.activated(
            "Pestilence: {B} — 1 damage to each creature and each player",
            pay, resolve, source_name="Pestilence",
            ability_text="Deal 1 damage to each creature and each player")]
