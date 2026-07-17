"""Jace, Wielder of Mysteries — {1}{U}{U}{U} Legendary Planeswalker (loyalty 4).
+1: Target player mills two cards; draw a card. (You mill yourself — feeding
delve/escape/graveyard value.)
−8: Draw seven cards.
The "win the game if you'd draw from an empty library" static is not modelled
(the goldfish does not resolve decking)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class JaceWielderOfMysteries(Card):
    card_name = "Jace, Wielder of Mysteries"

    def enters_with_counters(self, state):
        return {"loyalty": 4}

    def battlefield_actions(self, state, perm):
        if perm.turn_flags.get("pw_activated"):
            return []
        acts = []

        def plus_pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.turn_flags.get("pw_activated"):
                return False
            p.turn_flags["pw_activated"] = 1
            p.counters["loyalty"] = p.counters.get("loyalty", 0) + 1
            return True

        def plus_res(st):
            st.mill(2)
            st.draw(1)
            st.emit("Jace +1: mill two, draw a card")
            return None

        acts.append(CardAction.activated(
            "Jace, Wielder of Mysteries: +1 (mill 2, draw 1)",
            plus_pay, plus_res, sorcery_speed=True,
            source_name=self.card_name, ability_text="+1"))

        if perm.counters.get("loyalty", 0) >= 8:
            def ult_pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.turn_flags.get("pw_activated") or p.counters.get("loyalty", 0) < 8:
                    return False
                p.turn_flags["pw_activated"] = 1
                p.counters["loyalty"] -= 8
                return True

            def ult_res(st):
                st.draw(7)
                st.emit("Jace −8: draw seven cards")
                return None

            acts.append(CardAction.activated(
                "Jace, Wielder of Mysteries: −8 (draw 7)",
                ult_pay, ult_res, sorcery_speed=True,
                source_name=self.card_name, ability_text="−8"))
        return acts
