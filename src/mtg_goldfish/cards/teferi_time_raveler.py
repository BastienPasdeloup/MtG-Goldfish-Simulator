"""Teferi, Time Raveler — {1}{W}{U} Legendary Planeswalker — Teferi (loyalty 4).
Static: each opponent can cast spells only at sorcery speed — a no-op against
    the goldfish's phantom opponent.
+1: Until your next turn, you may cast sorcery spells as though they had flash.
−3: Return up to one target artifact, creature, or enchantment to its owner's
    hand. Draw a card.

The +1 sets `GameState.cast_sorcery_as_flash` (honoured in the search's
instant-speed windows — see actions.legal_actions). The −3 branches over the
optional bounce target (or none), then always draws."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class TeferiTimeRaveler(Card):
    card_name = "Teferi, Time Raveler"

    def enters_with_counters(self, state):
        return {"loyalty": 4}

    def battlefield_actions(self, state, perm):
        if perm.turn_flags.get("pw_activated"):
            return []
        acts: list[CardAction] = []

        def _use(st, delta):
            p = st.find_permanent(perm.uid)
            if p is None or p.turn_flags.get("pw_activated"):
                return None
            if p.counters.get("loyalty", 0) + delta < 0:
                return None
            p.turn_flags["pw_activated"] = 1
            p.counters["loyalty"] = p.counters.get("loyalty", 0) + delta
            return p

        # +1 — cast sorceries as though they had flash until your next turn.
        def plus_pay(st):
            return _use(st, +1) is not None

        def plus_res(st):
            st.cast_sorcery_as_flash = True
            st.emit("Teferi, Time Raveler +1: cast sorceries as though they had flash")
            return None

        acts.append(CardAction.activated(
            "Teferi, Time Raveler: +1 (sorceries gain flash)",
            plus_pay, plus_res, sorcery_speed=True,
            source_name=self.card_name, ability_text="+1"))

        # −3 — return up to one artifact/creature/enchantment to hand; draw.
        if perm.counters.get("loyalty", 0) >= 3:
            targets: list[int] = []
            seen: set[str] = set()
            for p in state.battlefield:
                if p.uid == perm.uid or p.name in seen:
                    continue
                head = p.type_line.split("—")[0].lower()
                if not any(t in head for t in ("artifact", "creature", "enchantment")):
                    continue
                seen.add(p.name)
                targets.append(p.uid)

            def minus_pay(st):
                return _use(st, -3) is not None

            def minus_res(st, uids=tuple(targets)):
                from ._common import branch_over

                # "up to one": None = bounce nothing (just draw).
                def do(b, uid):
                    if uid is not None:
                        tp = b.find_permanent(uid)
                        if tp is not None:
                            name = tp.name
                            b.leaves_battlefield(tp, "hand")
                            b.emit(f"Teferi, Time Raveler −3: return {name} to hand")
                    b.draw(1)
                    b.emit("Teferi, Time Raveler −3: draw a card")
                    return None

                return branch_over(st, [None, *uids], do)

            acts.append(CardAction.activated(
                "Teferi, Time Raveler: −3 (bounce up to one; draw)",
                minus_pay, minus_res, sorcery_speed=True,
                source_name=self.card_name, ability_text="−3"))
        return acts
