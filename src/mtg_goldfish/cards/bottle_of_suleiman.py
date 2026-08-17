"""Bottle of Suleiman — {4} Artifact.
{1}, Sacrifice this artifact: Flip a coin. If you win, create a 5/5 colorless
Djinn artifact creature token with flying. If you lose, this artifact deals 5
damage to you.

The coin flip is modelled as a branch: heads → a 5/5 flying Djinn token; tails →
5 damage to you. Costs {1} and sacrificing the Bottle."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class BottleOfSuleiman(Card):
    card_name = "Bottle of Suleiman"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            me = st.find_permanent(perm.uid)
            if me is None or not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            st.leaves_battlefield(me, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            def fn(s, opt):
                if opt == "heads":
                    tok = s.make_token("Djinn", 5, 5, "Artifact Creature — Djinn", text="Flying")
                    tok.extra_keywords.add("flying")
                    s.emit("Bottle of Suleiman: won the flip — 5/5 flying Djinn")
                else:
                    dealt = s.damage_self(5, by_artifact=True)
                    s.emit(f"Bottle of Suleiman: lost the flip — {dealt} damage to you")
                return None
            return st.settle(branch_over(st, ["heads", "tails"], fn))

        return [CardAction.activated(
            "Bottle of Suleiman: {1}, Sacrifice — flip a coin (Djinn / 5 to you)",
            pay, resolve, source_name="Bottle of Suleiman",
            ability_text="Flip a coin: 5/5 flying Djinn, or 5 damage to you")]
