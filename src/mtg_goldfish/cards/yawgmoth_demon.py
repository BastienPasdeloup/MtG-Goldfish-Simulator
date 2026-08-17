"""Yawgmoth Demon — {4}{B}{B} Creature — Phyrexian Demon 6/6, Flying, First strike.
At the beginning of your upkeep, you may sacrifice an artifact. If you don't, tap
this creature and it deals 2 damage to you.

Upkeep branch: sacrifice one of your artifacts (one branch each), or decline and
take the 2 damage + tap."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class YawgmothDemon(Card):
    card_name = "Yawgmoth Demon"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        arts = {}
        for p in state.battlefield:
            if p.is_artifact:
                arts.setdefault(p.name, p.uid)
        options = ["decline"] + [f"sac:{uid}" for uid in arts.values()]

        def fn(st, opt):
            if opt == "decline":
                live = st.find_permanent(perm.uid)
                if live is not None:
                    live.tapped = True
                dealt = st.damage_self(2)
                st.emit(f"Yawgmoth Demon: no sacrifice — tap and take {dealt} damage ({st.life})")
                return None
            uid = int(opt.split(":", 1)[1])
            victim = st.find_permanent(uid)
            if victim is not None:
                st.emit(f"Yawgmoth Demon: sacrifice {victim.name}")
                st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
            return None

        return branch_over(state, options, fn)
