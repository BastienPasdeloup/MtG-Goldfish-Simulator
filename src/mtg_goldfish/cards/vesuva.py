"""Vesuva — Land.
As it enters (tapped), it may enter as a copy of any land on the battlefield.
This is an "as it enters" replacement, NOT an ability on the stack: one
`etb_modes` branch per distinct land you control (the copy keeps that land's
abilities via its own implementation), plus an uncopied branch (a land with no
abilities)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Vesuva(Card):
    card_name = "Vesuva"

    def etb_tapped(self, state):
        return True

    def etb_modes(self, state):
        # One entering branch per distinct land in play, plus "uncopied".
        names = sorted({p.name for p in state.battlefield if p.is_land})
        modes = [
            {"label": f"as a copy of {n}", "tapped": True, "life": 0, "choice": n}
            for n in names
        ]
        modes.append({"label": "uncopied", "tapped": True, "life": 0, "choice": None})
        return modes

    def on_enter_choice(self, state, perm):
        # Applied the instant Vesuva enters (before its frame / any triggers),
        # so it is shown already as the copy and nothing goes on the stack.
        from .registry import build_card

        name = perm.chosen
        src = next(
            (p.card for p in state.battlefield
             if p.uid != perm.uid and p.name == name and p.is_land),
            None,
        )
        if name is None or src is None:
            return  # enters uncopied (a land with no abilities)
        perm.card = src.model_copy()
        perm.impl = build_card(perm.card)
        perm.tapped = True
