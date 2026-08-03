"""Show and Tell — {2}{U} Sorcery. Each player may put an artifact, creature,
enchantment, or land card from their hand onto the battlefield. Against a phantom
opponent, only you do: branch over "nothing" plus each eligible hand card (put
onto the battlefield, its ETB firing) — a way to cheat a fatty into play."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register

_PUTTABLE = ("artifact", "creature", "enchantment", "land")


@register
class ShowAndTell(Card):
    card_name = "Show and Tell"

    def on_resolve(self, state):
        names, seen = [], set()
        for c in state.hand:
            tl = c.type_line.lower()
            if c.name not in seen and any(t in tl for t in _PUTTABLE):
                seen.add(c.name)
                names.append(c.name)

        def fn(st, name):
            if name is None:
                st.emit("Show and Tell: put nothing into play")
                return None
            c = next((x for x in st.hand if x.name == name), None)
            if c is None:
                return None
            st.hand.remove(c)
            perm = st.put_on_battlefield(
                c, fire_etb=False, announce=f"Show and Tell: put {name} onto the battlefield")
            st.queue_entry_triggers([perm])
            return st.settle()

        return branch_over(state, [None] + names, fn)
