"""Tunnel — {R} Instant. Destroy target Wall. It can't be regenerated.

Only your own Walls are available in a solitaire goldfish (one branch each). Any
regeneration shield on the target is removed first."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Tunnel(Card):
    card_name = "Tunnel"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if not p.is_creature_now or "wall" not in p.type_line.lower() or p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    tgt.counters.pop("regen_shield", None)
                    st.emit(f"Tunnel: destroy {nm}")
                    st.leaves_battlefield(tgt, "graveyard", reason="destroy")
                    return None
                return fn

            acts.append(CardAction(f"cast Tunnel → destroy {p.name}", make(p.uid, p.name)))
        return acts
