"""Teferi, Hero of Dominaria — {3}{W}{U} Legendary Planeswalker — Teferi (loyalty 4).
+1: Draw a card. At the beginning of the next end step, untap up to two lands.
−3: Put target nonland permanent into its owner's library third from the top.
−8: Emblem "whenever you draw a card, exile target permanent an opponent
    controls" — a documented no-op against the goldfish's phantom opponent.

The +1's delayed untap is applied by the END_STEP step entry via
`GameState.untap_lands_end_step`. Each loyalty ability is once per turn and
sorcery-speed (planeswalker abilities)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class TeferiHeroOfDominaria(Card):
    card_name = "Teferi, Hero of Dominaria"

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

        # +1 — draw a card; untap up to two lands at the next end step.
        def plus_pay(st):
            return _use(st, +1) is not None

        def plus_res(st):
            st.draw(1)
            st.untap_lands_end_step += 2
            st.emit("Teferi, Hero of Dominaria +1: draw a card; untap up to two "
                    "lands at end step")
            return None

        acts.append(CardAction.activated(
            "Teferi, Hero of Dominaria: +1 (draw; untap 2 lands at end step)",
            plus_pay, plus_res, sorcery_speed=True,
            source_name=self.card_name, ability_text="+1"))

        # −3 — tuck a target nonland permanent third from the top of its library.
        # Against the goldfish only your own permanents exist; branch over them.
        if perm.counters.get("loyalty", 0) >= 3:
            targets: list[int] = []
            seen: set[str] = set()
            for p in state.battlefield:
                if p.is_land or p.uid == perm.uid or p.name in seen:
                    continue
                seen.add(p.name)
                targets.append(p.uid)
            if targets:
                def minus_pay(st):
                    return _use(st, -3) is not None

                def minus_res(st, uids=tuple(targets)):
                    from ._common import branch_over

                    def do(b, uid):
                        tp = b.find_permanent(uid)
                        if tp is None:
                            return None
                        card = tp.card
                        b.leaves_battlefield(tp, "library")
                        # Third from the top (index 2), or as deep as possible.
                        pos = min(2, len(b.library))
                        b.library.insert(pos, card)
                        b.mark_known_in_library(card)
                        b.emit(f"Teferi, Hero of Dominaria −3: {card.name} "
                               f"third from the top of the library")
                        return None

                    return branch_over(st, list(uids), do)

                acts.append(CardAction.activated(
                    "Teferi, Hero of Dominaria: −3 (tuck a nonland permanent)",
                    minus_pay, minus_res, sorcery_speed=True,
                    source_name=self.card_name, ability_text="−3"))

        # −8 — emblem; nothing to exile against a phantom opponent (no-op).
        if perm.counters.get("loyalty", 0) >= 8:
            def ult_pay(st):
                return _use(st, -8) is not None

            def ult_res(st):
                st.emit("Teferi, Hero of Dominaria −8: emblem (no opponent — no effect)")
                return None

            acts.append(CardAction.activated(
                "Teferi, Hero of Dominaria: −8 (emblem)",
                ult_pay, ult_res, sorcery_speed=True,
                source_name=self.card_name, ability_text="−8"))
        return acts
