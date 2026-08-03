"""Saw in Half — {2}{B} Instant. Destroy target creature. If that creature dies
this way, its controller creates two tokens that are copies of it, except their
power/toughness are each half (rounded up) of that creature's power/toughness.

Per the rulings: the tokens copy the PRINTED characteristics (a characteristic-
defining P/T is NOT copied — the explicit half P/T applies instead), their
enters-the-battlefield abilities DO trigger, and no tokens are made if the
creature doesn't actually reach the graveyard (indestructible, or a replacement
sends it to exile — e.g. under Yawgmoth's Will / Hades).

Against a phantom opponent the only targets are your own creatures — Saw in Half
on a creature with a strong ETB (Archon of Cruelty, Lord of Change, ...) doubles
that ETB while binning the original for reanimation."""
from __future__ import annotations

import math

from .base import Card, CardAction
from .registry import register


@register
class SawInHalf(Card):
    card_name = "Saw in Half"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []
        targets, seen = [], set()
        for p in state.battlefield:
            if p.is_creature_now and p.name not in seen:
                seen.add(p.name)
                targets.append((p.uid, p.name))

        acts = []
        for uid, tname in targets:
            def make(uid=uid, tname=tname):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    target = st.find_permanent(uid)
                    if card is None or target is None or not begin_cast(st, card, cost):
                        return None
                    resolve_to_graveyard(st, card)
                    src_card = target.card
                    half_p = max(0, math.ceil(max(0, st.effective_power(target)) / 2))
                    half_t = max(0, math.ceil(max(0, st.effective_toughness(target)) / 2))
                    was_token = target.is_token
                    st.leaves_battlefield(target, "graveyard", reason="destroy")
                    # "If that creature dies this way" — only if it reached the
                    # graveyard (a replacement to exile, or indestructible, stops it).
                    died = was_token or (src_card in st.graveyard)
                    if not died:
                        st.emit(f"Saw in Half: {tname} did not die — no tokens")
                        return None
                    toks = []
                    for _ in range(2):
                        t = st.put_on_battlefield(
                            src_card, token=True, fire_etb=False,
                            announce=f"Saw in Half: token copy of {tname} ({half_p}/{half_t})")
                        t.becomes = {"type_line": t.type_line, "power": half_p,
                                     "toughness": half_t, "permanent": True}
                        toks.append(t)
                    st.queue_entry_triggers(toks)
                    return st.settle()
                return fn

            acts.append(CardAction(f"cast Saw in Half → {tname}", make()))
        return acts
