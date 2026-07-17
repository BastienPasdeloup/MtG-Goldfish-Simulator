"""Den of the Bugbear — Land. Enters tapped if you control two or more other
lands. {T}: Add {R}.
{3}{R}: Becomes a 3/2 red Goblin creature until end of turn (still a land) with
"Whenever this creature attacks, create a 1/1 red Goblin token tapped and
attacking."."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import animate_land_action
from .base import Card
from .registry import register


@register
class DenOfTheBugbear(Card):
    card_name = "Den of the Bugbear"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("R",))]

    def etb_tapped(self, state):
        return sum(1 for p in state.battlefield if p.is_land) >= 2

    def battlefield_actions(self, state, perm):
        return animate_land_action(
            self, state, perm,
            cost=ManaCost(generic=3, pips=(("R", 1),)),
            type_line="Creature Land — Goblin",
            power=3, toughness=2,
            label="Den of the Bugbear: become a 3/2 Goblin",
        )

    def on_attack(self, state, perm):
        if perm.becomes is None:
            return
        state.make_token("Goblin", 1, 1, "Creature — Goblin", tapped=True, attacking=True)
        state.emit("Den of the Bugbear: create a 1/1 Goblin tapped and attacking")
