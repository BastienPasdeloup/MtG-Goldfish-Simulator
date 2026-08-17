"""Urza's Avenger — {6} Artifact Creature — Shapeshifter 4/4.
{0}: This creature gets -1/-1 and gains your choice of banding, flying, first
strike, or trample until end of turn.

A free, repeatable ability: one branch per keyword. The -1/-1 (temp) is a real
cost; the keywords are mostly cosmetic in a goldfish (no blockers), but the search
may still shrink it, so it's offered."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register

_KEYWORDS = ("banding", "flying", "first strike", "trample")


@register
class UrzasAvenger(Card):
    card_name = "Urza's Avenger"

    def battlefield_actions(self, state, perm):
        acts = []
        for kw in _KEYWORDS:
            def make(kw=kw):
                def pay(st):
                    return True  # {0}

                def resolve(st):
                    p = st.find_permanent(perm.uid)
                    if p is not None:
                        p.temp_power -= 1
                        p.temp_toughness -= 1
                        p.temp_keywords.add(kw)
                        st.emit(f"Urza's Avenger: -1/-1 and gains {kw} until end of turn")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Urza's Avenger: {{0}} — -1/-1 and gain {kw}",
                pay, resolve, source_name="Urza's Avenger",
                ability_text="-1/-1 and gains a keyword until end of turn"))
        return acts
