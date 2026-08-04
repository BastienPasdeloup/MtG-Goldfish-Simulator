"""Astral Dragon — {6}{U}{U} 4/4 Flying Dragon. Project Image — When it enters,
create two tokens that are copies of target NONCREATURE permanent, except they're
3/3 Dragon creatures in addition to their other types, and they have flying.

Per the rulings: the tokens copy the printed characteristics of the noncreature
permanent (so a copied land still taps for mana, a copied artifact keeps its
abilities) plus become 3/3 flying Dragons; their enters-the-battlefield abilities
DO trigger; an Aura can't be targeted. Against a phantom opponent the targets are
your own noncreature permanents (branch over each distinct one)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


def _dragonize(type_line: str) -> str:
    head, sep, tail = type_line.partition("—")
    head = head.rstrip()
    if "creature" not in head.lower():
        head = head + " Creature"
    if sep:
        subs = tail.strip()
        if "dragon" not in subs.lower():
            subs = (subs + " Dragon").strip()
        return f"{head} — {subs}"
    return f"{head} — Dragon"


@register
class AstralDragon(Card):
    card_name = "Astral Dragon"

    def on_etb(self, state, permanent):
        targets, seen = [], set()
        for p in state.battlefield:
            tl = p.type_line.lower()
            if (not p.is_creature_now and "aura" not in tl and p.name not in seen):
                seen.add(p.name)
                targets.append((p.uid, p.name))
        if not targets:
            state.emit("Astral Dragon: no noncreature permanent to copy")
            return None

        def fn(st, target):
            uid, name = target
            src = st.find_permanent(uid)
            if src is None:
                return None
            toks = []
            for _ in range(2):
                t = st.put_on_battlefield(
                    src.card, token=True, fire_etb=False,
                    announce=f"Astral Dragon: 3/3 flying Dragon copy of {name}")
                t.becomes = {"type_line": _dragonize(t.type_line), "power": 3,
                             "toughness": 3, "permanent": True}
                t.extra_keywords.add("flying")
                t.is_copy = True
                toks.append(t)
            st.queue_entry_triggers(toks)
            return st.settle()

        return branch_over(state, targets, fn)
