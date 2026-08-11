"""Berserk — {G} Instant.
Cast this spell only before the combat damage step.
Target creature gains trample and gets +X/+0 until end of turn, where X is its
power. At the beginning of the next end step, destroy that creature if it
attacked this turn.

Cast on one of your creatures (one branch each): it doubles its power for the
turn (temp +power/+0) and gains trample; it is destroyed at end step iff it
attacked (see the END_STEP `end_step_destroy` handling). The 'only before combat
damage' timing isn't enforced — the search only casts it when it helps."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Berserk(Card):
    card_name = "Berserk"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if not p.is_creature_now or p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    pw = st.effective_power(tgt)
                    tgt.temp_power += pw            # +X/+0, X = its power (doubles it)
                    tgt.temp_keywords.add("trample")
                    tgt.counters["end_step_destroy"] = 1
                    st.emit(f"Berserk: {nm} gets +{pw}/+0 and trample "
                            f"(destroyed at end step if it attacked)")
                    return None
                return fn

            acts.append(CardAction(f"cast Berserk → {p.name}", make(p.uid, p.name)))
        return acts
