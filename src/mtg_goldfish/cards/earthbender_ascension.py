"""Earthbender Ascension — {2}{G} Enchantment.
ETB: search your library for a basic land, put it onto the battlefield tapped
(branch). Landfall: put a quest counter on it; at four or more, put a +1/+1
counter on a creature you control (deterministic: the commander if present,
else the first creature; trample-until-eot is not tracked).
Approximation: the ETB "earthbend 2" (land becomes a creature) is skipped."""
from __future__ import annotations

from ._common import tutor_to_battlefield_branches
from .base import Card
from .registry import register


@register
class EarthbenderAscension(Card):
    card_name = "Earthbender Ascension"

    def on_etb(self, state, permanent):
        return tutor_to_battlefield_branches(
            state, lambda c: c.is_land and "basic" in c.type_line.lower(),
            tapped=True, note=" (Earthbender Ascension)",
        )

    def other_etb_stack_items(self, state, perm, entering):
        if "land" not in entering.type_line.lower():
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="Earthbender Ascension: landfall",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield",
            ability_text="Landfall — put a quest counter on Earthbender Ascension",
        )]

    def on_other_etb(self, state, perm, entering):
        if "land" not in entering.type_line.lower():
            return
        perm.counters["quest"] = perm.counters.get("quest", 0) + 1
        if perm.counters["quest"] >= 4:
            target = next(
                (p for p in state.battlefield if p.is_commander and p.is_creature_now),
                next((p for p in state.battlefield if p.is_creature_now), None),
            )
            if target is not None:
                target.counters["+1/+1"] = target.counters.get("+1/+1", 0) + 1
                state.emit(f"Earthbender Ascension: +1/+1 counter on {target.name}")
