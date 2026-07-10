"""Basim Ibn Ishaq — {U}{B} 2/2. Whenever you cast a historic spell (artifact,
legendary, or Saga), draw a card — once each turn. Combat damage: +1/+1 counter."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BasimIbnIshaq(Card):
    card_name = "Basim Ibn Ishaq"

    def cast_other_stack_items(self, state, perm, card):
        if perm.turn_flags.get("basim_drew"):
            return []
        tl = card.type_line.lower()
        if not ("artifact" in tl or "legendary" in tl or "saga" in tl):
            return []

        def resolve(st, uid=perm.uid, cast_card=card):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_cast_other(st, live, cast_card)

        return [self.stack_ability(
            source_name=perm.name,
            label="Basim Ibn Ishaq: historic trigger",
            resolve=resolve,
            trigger_text=f"You cast {card.name}, a historic spell",
            ability_text="Draw a card",
        )]

    def on_cast_other(self, state, perm, card):
        if perm.turn_flags.get("basim_drew"):
            return
        tl = card.type_line.lower()
        if "artifact" in tl or "legendary" in tl or "saga" in tl:
            perm.turn_flags["basim_drew"] = 1
            state.emit("Basim Ibn Ishaq: historic spell cast — draw a card")
            state.draw(1)

    def on_combat_damage(self, state, perm, damage):
        perm.counters["+1/+1"] = perm.counters.get("+1/+1", 0) + 1
        state.emit("Basim Ibn Ishaq: +1/+1 counter")
