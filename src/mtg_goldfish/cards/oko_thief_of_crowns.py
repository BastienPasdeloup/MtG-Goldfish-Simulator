"""Oko, Thief of Crowns — {1}{G}{U} Legendary Planeswalker (loyalty 4).
+2: Create a Food token.
+1: Target artifact or creature you control loses all abilities and becomes a
3/3 green Elk. (Modelled with the until-end-of-turn animation mechanism, so the
Elk reverts at cleanup — an approximation of the permanent change.)
−5: Exchange control of permanents with an opponent — no effect in a goldfish."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class OkoThiefOfCrowns(Card):
    card_name = "Oko, Thief of Crowns"

    def enters_with_counters(self, state):
        return {"loyalty": 4}

    def battlefield_actions(self, state, perm):
        if perm.turn_flags.get("pw_activated"):
            return []
        acts = []

        def plus2_pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.turn_flags.get("pw_activated"):
                return False
            p.turn_flags["pw_activated"] = 1
            p.counters["loyalty"] = p.counters.get("loyalty", 0) + 2
            return True

        def plus2_res(st):
            st.make_token("Food", 0, 0, "Artifact — Food")
            st.emit("Oko +2: create a Food token")
            return None

        acts.append(CardAction.activated(
            "Oko, Thief of Crowns: +2 (Food token)",
            plus2_pay, plus2_res, sorcery_speed=True,
            source_name=self.card_name, ability_text="+2"))

        # +1: turn one of your artifacts/creatures into a 3/3 Elk.
        seen = set()
        for target in state.battlefield:
            tl = target.type_line.lower()
            if target.uid == perm.uid or target.name in seen:
                continue
            if "artifact" not in tl and "creature" not in tl:
                continue
            seen.add(target.name)

            def make(uid):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    tgt = st.find_permanent(uid)
                    if p is None or tgt is None or p.turn_flags.get("pw_activated"):
                        return False
                    p.turn_flags["pw_activated"] = 1
                    p.counters["loyalty"] = p.counters.get("loyalty", 0) + 1
                    return True

                def res(st):
                    tgt = st.find_permanent(uid)
                    if tgt is not None:
                        tgt.becomes = {"type_line": "Creature — Elk", "power": 3,
                                       "toughness": 3}
                        st.emit(f"Oko +1: {tgt.name} becomes a 3/3 Elk")
                    return None
                return pay, res

            pay, res = make(target.uid)
            acts.append(CardAction.activated(
                f"Oko, Thief of Crowns: +1 → {target.name} becomes a 3/3 Elk",
                pay, res, sorcery_speed=True,
                source_name=self.card_name, ability_text="+1"))
        return acts
