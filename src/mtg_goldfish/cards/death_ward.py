"""Death Ward — {W} Instant. Regenerate target creature.
Grants a regeneration shield (see GameState._survives_destruction): the next time
that creature would be destroyed (by lethal damage or a destroy effect) it is
saved instead. One branch per creature you control."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class DeathWard(Card):
    card_name = "Death Ward"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen = set()
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
                    tgt.counters["regen_shield"] = tgt.counters.get("regen_shield", 0) + 1
                    st.emit(f"Death Ward: regeneration shield on {nm}")
                    return None
                return fn

            acts.append(CardAction(f"cast Death Ward → {p.name}", make(p.uid, p.name)))
        return acts
