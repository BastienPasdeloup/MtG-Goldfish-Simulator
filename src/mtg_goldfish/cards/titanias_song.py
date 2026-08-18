"""Titania's Song — {3}{G} Enchantment.
Each noncreature artifact loses all abilities and becomes an artifact creature with
power and toughness each equal to its mana value. If this enchantment leaves the
battlefield, this effect continues until end of turn.

A continuous static: every noncreature artifact you control is animated to a P/T =
mana-value creature via a permanent `becomes` carrying `lose_abilities` (the engine
suppresses its mana / activated / triggered abilities). Artifacts entering later are
animated immediately (`on_other_etb_immediate`). A 0-mana artifact becomes 0/0 and
dies. When the last Titania's Song leaves the effect ends (the printed "until end of
turn" tail is approximated as immediate)."""
from __future__ import annotations

from ._common import mv
from .base import Card
from .registry import register


def _animate(state, p) -> None:
    if not p.is_artifact or p.is_creature_now:
        return
    if p.becomes and p.becomes.get("animated_by") == "Titania's Song":
        return
    n = mv(p.card)
    p.becomes = {"type_line": "Artifact Creature", "power": n, "toughness": n,
                 "permanent": True, "lose_abilities": True, "animated_by": "Titania's Song"}


@register
class TitaniasSong(Card):
    card_name = "Titania's Song"

    def on_etb(self, state, perm):
        for p in list(state.battlefield):
            if p.uid != perm.uid:
                _animate(state, p)
        state.emit("Titania's Song: noncreature artifacts become creatures (P/T = mana value)")
        state.check_deaths()

    def on_other_etb_immediate(self, state, perm, entering):
        _animate(state, entering)

    def on_leave(self, state, permanent):
        # Another Titania's Song keeps the effect going.
        if any(o.name == "Titania's Song" and o.uid != permanent.uid for o in state.battlefield):
            return
        for p in list(state.battlefield):
            if p.becomes and p.becomes.get("animated_by") == "Titania's Song":
                p.becomes = None
        state.emit("Titania's Song leaves: artifacts revert")
        state.check_deaths()
