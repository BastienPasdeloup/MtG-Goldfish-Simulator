"""Heritage Reclamation — {1}{G} Instant. Choose one — destroy target artifact;
destroy target enchantment; or exile up to one target card from a graveyard and
draw a card. Only your own permanents are legal in a goldfish."""
from __future__ import annotations

from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class HeritageReclamation(Card):
    card_name = "Heritage Reclamation"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []
        acts = []

        # Mode 3: exile up to one graveyard card, draw a card (always available).
        def gy_mode(st_ignored=None):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                names = ["(none)"] + sorted({c.name for c in st.graveyard})

                def pick(s, name):
                    if name != "(none)":
                        c = next((x for x in s.graveyard if x.name == name), None)
                        if c is not None:
                            s.leave_graveyard(c)
                            s.exile.append(c)
                            s.emit(f"Heritage Reclamation: exile {name}")
                    s.draw(1)
                    return None

                return branch_over(st, names, pick)
            return fn

        acts.append(CardAction("cast Heritage Reclamation (exile GY card, draw)",
                               gy_mode()))

        # Modes 1/2: destroy a target artifact / enchantment you control.
        def destroy_mode(uid, kind):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                target = st.find_permanent(uid)
                if card is None or target is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                st.emit(f"Heritage Reclamation: destroy {target.name}")
                st.leaves_battlefield(target, "graveyard", reason="destroy")
                return None
            return fn

        for p in state.battlefield:
            tl = p.type_line.lower()
            if "artifact" in tl:
                acts.append(CardAction(
                    f"cast Heritage Reclamation → destroy {p.name}",
                    destroy_mode(p.uid, "artifact")))
            elif "enchantment" in tl:
                acts.append(CardAction(
                    f"cast Heritage Reclamation → destroy {p.name}",
                    destroy_mode(p.uid, "enchantment")))
        return acts
