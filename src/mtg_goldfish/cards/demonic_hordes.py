"""Demonic Hordes — {3}{B}{B}{B} Creature — Demon 5/5.
{T}: Destroy target land.
At the beginning of your upkeep, unless you pay {B}{B}{B}, tap this creature and
sacrifice a land of an opponent's choice.

The {T} destroy-land ability only has your own (or no) lands to target — never
worth using — so it isn't offered. The upkeep tax is modelled: pay {B}{B}{B} if
you can (keeping the beater), otherwise it taps and you sacrifice a land (the
opponent picks your worst — approximated by sacrificing one)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class DemonicHordes(Card):
    card_name = "Demonic Hordes"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("B", 1), ("B", 1), ("B", 1)))
        if can_afford(state, cost) and pay_cost(state, cost):
            state.emit("Demonic Hordes: pay {B}{B}{B} (kept)")
            return None
        p = state.find_permanent(perm.uid)
        if p is not None:
            p.tapped = True
        lands = [q for q in state.battlefield if q.is_land]
        if lands:
            victim = lands[0]  # opponent's choice -> a land (approximate)
            state.emit(f"Demonic Hordes: tapped, sacrifice {victim.name}")
            state.leaves_battlefield(victim, "graveyard", reason="sacrifice")
        else:
            state.emit("Demonic Hordes: tapped (no land to sacrifice)")
        return None
