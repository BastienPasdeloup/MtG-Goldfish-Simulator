"""Primal Clay — {4} Artifact Creature — Shapeshifter */*.
As this creature enters, it becomes your choice of a 3/3 artifact creature, a 2/2
artifact creature with flying, or a 1/6 Wall artifact creature with defender.

Three ETB branches, each fixing the body via a permanent `becomes` override plus
the granted keyword."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class PrimalClay(Card):
    card_name = "Primal Clay"

    def enter_choices(self, state, perm):
        options = [
            ("3/3", "Artifact Creature — Shapeshifter", 3, 3, []),
            ("2/2 flying", "Artifact Creature — Shapeshifter", 2, 2, ["flying"]),
            ("1/6 Wall defender", "Artifact Creature — Wall", 1, 6, ["defender"]),
        ]

        def fn(st, opt):
            label, tl, p, t, kws = opt
            me = st.find_permanent(perm.uid)
            if me is None:
                return None
            me.becomes = {"type_line": tl, "power": p, "toughness": t, "permanent": True}
            for kw in kws:
                me.extra_keywords.add(kw)
            st.emit(f"Primal Clay enters as a {label}")
            return None

        return branch_over(state, options, fn)
