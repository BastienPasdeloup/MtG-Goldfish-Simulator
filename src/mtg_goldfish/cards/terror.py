"""Terror — {1}{B} Instant.
Destroy target nonartifact, nonblack creature. It can't be regenerated.

Only your own creatures are available in a solitaire goldfish (one branch per
distinct nonartifact, nonblack creature). Any regeneration shield on the target is
removed first ("can't be regenerated")."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Terror(Card):
    card_name = "Terror"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if not p.is_creature_now or p.is_artifact or "B" in p.colors or p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    tgt.counters.pop("regen_shield", None)  # can't be regenerated
                    st.emit(f"Terror: destroy {nm}")
                    st.leaves_battlefield(tgt, "graveyard", reason="destroy")
                    return None
                return fn

            acts.append(CardAction(f"cast Terror → destroy {p.name}", make(p.uid, p.name)))
        return acts
