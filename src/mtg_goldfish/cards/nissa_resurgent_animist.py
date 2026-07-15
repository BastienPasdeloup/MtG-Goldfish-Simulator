"""Nissa, Resurgent Animist — {2}{G} Legendary Creature — Elf Scout 3/3.
Landfall: add one mana of any color. Then, if this is the second landfall to
resolve this turn, reveal until an Elf or Elemental card, put it into your
hand and the rest on the bottom (modelled as: search your library for such a
card to hand, then shuffle — the reveal order is irrelevant to the outcome)."""
from __future__ import annotations

from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class NissaResurgentAnimist(Card):
    card_name = "Nissa, Resurgent Animist"

    def other_etb_stack_items(self, state, perm, entering):
        if not entering.is_land:
            return []
        color = any_identity_color(state)[0]

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="Nissa, Resurgent Animist: landfall",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield",
            ability_text=f"Landfall — add {{{color}}}; on the second resolution this turn, search an Elf or Elemental to hand",
        )]

    def on_other_etb(self, state, perm, entering):
        if not entering.is_land:
            return
        color = any_identity_color(state)[0]
        state.mana_pool.add(color, 1)
        perm.turn_flags["landfall"] = perm.turn_flags.get("landfall", 0) + 1
        state.emit(f"Nissa: landfall — add {{{color}}}")
        if perm.turn_flags["landfall"] == 2:
            hit = next(
                (c for c in state.library
                 if c.is_creature and ("elf" in c.type_line.lower()
                                       or "elemental" in c.type_line.lower())),
                None,
            )
            if hit is not None:
                state.take_from_library(hit)
                state.shuffle_library()
                state.hand.append(hit)
                state.emit(f"Nissa: second landfall — {hit.name} to hand")
