"""Metamorphosis Fanatic — {4}{B}{B} 4/4 Lifelink. When it enters, return up to
one target creature card from your graveyard to the battlefield with a lifelink
counter on it (modelled as granting lifelink). Miracle is cast normally here."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class MetamorphosisFanatic(Card):
    card_name = "Metamorphosis Fanatic"

    def on_etb(self, state, permanent):
        names, seen = [], set()
        for c in state.graveyard:
            if c.is_creature and c.name not in seen:
                seen.add(c.name)
                names.append(c.name)
        if not names:
            return None

        def fn(st, name):
            if name is None:
                st.emit("Metamorphosis Fanatic: return nothing")
                return None
            c = next((x for x in st.graveyard if x.name == name), None)
            if c is None:
                return None
            st.graveyard.remove(c)
            p = st.put_on_battlefield(
                c, fire_etb=False,
                announce=f"Metamorphosis Fanatic: reanimate {name} with a lifelink counter")
            p.extra_keywords.add("lifelink")
            p.counters["lifelink"] = 1
            st.queue_entry_triggers([p])
            return st.settle()

        return branch_over(state, [None] + names, fn)
