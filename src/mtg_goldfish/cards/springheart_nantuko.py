"""Springheart Nantuko — {1}{G} Enchantment Creature — Insect Monk 1/1.
Bestow {1}{G}. Enchanted creature gets +1/+1.
Landfall — Whenever a land you control enters, you may pay {1}{G} if attached to
a creature you control. If you do, create a token that's a copy of that creature.
If you didn't create a token this way, create a 1/1 green Insect creature token.

Cast as a plain 1/1 creature (bestow-from-hand onto a creature is a branch). The
landfall BRANCHES when attached: one line pays {1}{G} for a full token copy of
the enchanted creature (via GameState.make_token_copy), the other makes the 1/1
Insect. Unattached (or can't pay) → the 1/1 Insect."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import aura_on_creature_bestow_actions, branch_over
from .base import Card
from .registry import register

_LANDFALL_COST = ManaCost(generic=1, pips=(("G", 1),))


@register
class SpringheartNantuko(Card):
    card_name = "Springheart Nantuko"

    def cast_actions(self, state):
        # Default cast (as a 1/1 creature) plus bestow onto each creature.
        from ..engine.actions import CastDefault, can_afford
        acts = []
        if can_afford(state, self.cast_cost(state)):
            acts.append(CastDefault(self.card_name))
        acts += aura_on_creature_bestow_actions(self, state, bestow_cost="{1}{G}")
        return acts

    def equip_mod(self, state, perm):
        return (1, 1) if perm.counters.get("bestowed") else (0, 0)

    def other_etb_stack_items(self, state, perm, entering):
        # Landfall fires on every land you control entering — whether or not
        # Springheart is attached (the "may pay to copy" only applies when it is).
        if not entering.is_land:
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_other_etb(st, live, st.find_permanent(entering_uid))

        return [self.stack_ability(
            source_name=perm.name,
            label="Springheart Nantuko: landfall",
            resolve=resolve,
            trigger_text="A land you control entered the battlefield",
            ability_text="Landfall — copy the enchanted creature ({1}{G}) or make a 1/1 Insect",
        )]

    def _make_insect(self, state):
        state.make_token("Insect", 1, 1, "Token Creature — Insect", colors=["G"])
        state.emit("Springheart Nantuko: landfall — 1/1 Insect token")

    def on_other_etb(self, state, perm, entering):
        from ..engine.actions import can_afford, pay_cost

        host = (state.find_permanent(perm.attached_to)
                if perm.attached_to is not None else None)
        if host is None or not host.is_creature_now or not can_afford(state, _LANDFALL_COST):
            self._make_insect(state)
            return None
        # A land entering during an ATOMIC resolution (direct put_on_battlefield
        # → settle_nonbranching, which sets _suppress_responses) cannot branch
        # here. Take the no-pay default (the 1/1 Insect) — a safe under-choice.
        # The common land-entry paths (PlayLand, fetch) settle branching, so the
        # copy/Insect choice is offered there.
        if getattr(state, "_suppress_responses", False):
            self._make_insect(state)
            return None

        # Attached to a creature you control: MAY pay {1}{G} to copy it, else Insect.
        def choose(st, pay_to_copy):
            if not pay_to_copy:
                self._make_insect(st)
                return None
            h = st.find_permanent(host.uid)
            if h is None or not pay_cost(st, _LANDFALL_COST):
                self._make_insect(st)  # host gone / couldn't pay after all
                return None
            st.emit(f"Springheart Nantuko: landfall — pay {{1}}{{G}}, copy {h.name}")
            st.make_token_copy(h)
            return None

        return branch_over(state, [True, False], choose)
