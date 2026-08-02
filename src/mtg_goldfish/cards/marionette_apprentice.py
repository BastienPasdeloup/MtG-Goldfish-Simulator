"""Marionette Apprentice — {1}{B} Creature 1/2.
Fabricate 1 (ETB: put a +1/+1 counter on it, or create a 1/1 Servo artifact token).
Whenever another creature or artifact you control is put into a graveyard from
the battlefield, each opponent loses 1 life."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class MarionetteApprentice(Card):
    card_name = "Marionette Apprentice"

    def on_etb(self, state, permanent):
        def fn(st, opt):
            perm = st.find_permanent(permanent.uid)
            if opt == "counter":
                if perm is not None:
                    perm.counters["+1/+1"] = perm.counters.get("+1/+1", 0) + 1
                st.emit("Marionette Apprentice: fabricate — +1/+1 counter")
            else:
                st.make_token("Servo", 1, 1, "Artifact Creature — Servo")
                st.emit("Marionette Apprentice: fabricate — 1/1 Servo")
            return None

        return branch_over(state, ["servo", "counter"], fn)

    def on_other_leave(self, state, perm, left, to, reason):
        if to != "graveyard":
            return
        if left.is_creature_now or "artifact" in left.type_line.lower():
            state.damage_opponent(1)  # noncombat -> amplifiers apply
            state.emit(f"Marionette Apprentice: opponent loses 1 ({state.opponent_life})")
