"""King T'Challa // Black Panther, Hope Enduring — {1}{W}{U} Legendary 3/2,
flash. "Whenever a player draws their second card each turn, you draw a card."
{4}{W}{U}: transform (sorcery). Black Panther's combat-damage draw fires via
on_combat_damage when transformed."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import transform_actions
from .base import Card
from .registry import register


@register
class KingTChalla(Card):
    card_name = "King T'Challa // Black Panther, Hope Enduring"

    def draw_stack_items(self, state, perm, nth_this_turn):
        if nth_this_turn != 2 or perm.turn_flags.get("tchalla_drew"):
            return []

        def resolve(st, uid=perm.uid, nth=nth_this_turn):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_draw_card(st, live, nth)

        return [self.stack_ability(
            source_name=perm.name,
            label="King T'Challa: second-draw trigger",
            resolve=resolve,
            trigger_text="A player drew their second card this turn",
            ability_text="Draw a card",
        )]

    def combat_damage_stack_items(self, state, perm, damage):
        if not perm.transformed:
            return []

        def resolve(st, uid=perm.uid, dealt=damage):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_combat_damage(st, live, dealt)

        return [self.stack_ability(
            source_name=perm.name,
            label="Black Panther: combat-damage trigger",
            resolve=resolve,
            trigger_text=f"{perm.name} dealt combat damage",
            ability_text="Draw a card",
        )]

    def on_draw_card(self, state, perm, nth_this_turn):
        # Fires exactly on the second draw; the bonus draw is the third, so no loop.
        if nth_this_turn == 2 and not perm.turn_flags.get("tchalla_drew"):
            perm.turn_flags["tchalla_drew"] = 1
            state.emit("King T'Challa: second card drawn this turn — draw a card")
            state.draw(1)

    def on_combat_damage(self, state, perm, damage):
        if perm.transformed:
            state.emit("Black Panther: combat damage — draw a card")
            state.draw(1)

    def battlefield_actions(self, state, perm):
        return transform_actions(
            state, perm,
            ManaCost(generic=4, pips=(("W", 1), ("U", 1))),
            "Black Panther, Hope Enduring",
        )
