"""Wishclaw Talisman — {1} Artifact, enters with three wish counters.
{1}, {T}, Remove a wish counter: Search your library for a card, put it into your
hand, then shuffle. An opponent gains control of this artifact. Activate only
during your turn.

Against a phantom opponent, "an opponent gains control" means you lose the
artifact after using it — so it is a one-shot tutor (it leaves your control the
first time you crack it)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import tutor_to_hand_branches
from .base import Card, CardAction
from .registry import register

_COST = ManaCost(generic=1)


@register
class WishclawTalisman(Card):
    card_name = "Wishclaw Talisman"

    def enters_with_counters(self, state):
        return {"wish": 3}

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.tapped or not perm.counters.get("wish") or not can_afford(state, _COST):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not p.counters.get("wish"):
                return False
            if not pay_cost(st, _COST):
                return False
            p.tapped = True
            p.counters["wish"] -= 1
            return True

        def resolve(st):
            p = st.find_permanent(perm.uid)
            branches = tutor_to_hand_branches(st, lambda c: True)
            # An opponent gains control: it leaves your battlefield after use.
            def hand_off(s):
                live = s.find_permanent(perm.uid)
                if live is not None:
                    s.leaves_battlefield(live, "none")
                    s.emit("Wishclaw Talisman: an opponent gains control (leaves play)")
            if branches is None:
                hand_off(st)
                return None
            for b in branches:
                hand_off(b)
            return branches

        return [CardAction.activated(
            "Wishclaw Talisman: {1}, {T}, remove a wish counter — tutor", pay, resolve,
            sorcery_speed=True, source_name="Wishclaw Talisman",
            ability_text="Search your library for a card, put it into your hand")]
