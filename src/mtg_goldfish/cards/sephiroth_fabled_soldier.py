"""Sephiroth, Fabled SOLDIER // Sephiroth, One-Winged Angel — transform DFC.
Front (3/3): on enter/attack may sacrifice another creature to draw a card;
whenever another creature dies, target opponent loses 1 and you gain 1 — the
fourth such resolution each turn transforms Sephiroth.
Back (5/5, flying): the transform grants an emblem with the same death drain
(modelled by keeping the death trigger after transforming), and its attack lets
you sacrifice any number of other creatures to draw that many cards."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class SephirothFabledSoldier(Card):
    card_name = "Sephiroth, Fabled SOLDIER // Sephiroth, One-Winged Angel"

    def _sac_one_draw(self, state, perm):
        options = [("decline", None)]
        seen = set()
        for p in state.battlefield:
            if p.is_creature_now and p.uid != perm.uid and p.name not in seen:
                seen.add(p.name)
                options.append((p.name, p.uid))
        if len(options) == 1:
            return None

        def fn(st, opt):
            _label, uid = opt
            if uid is None:
                st.emit("Sephiroth: decline sacrifice")
                return None
            v = st.find_permanent(uid)
            if v is not None:
                st.emit(f"Sephiroth: sacrifice {v.name}, draw a card")
                st.leaves_battlefield(v, "graveyard", reason="sacrifice")
                st.draw(1)
            return None

        return branch_over(state, options, fn)

    def _sac_any_draw(self, state, perm):
        others = [p for p in state.battlefield
                  if p.is_creature_now and p.uid != perm.uid]
        order = [p.uid for p in sorted(others, key=lambda p: state.effective_power(p))]
        if not order:
            return None

        def fn(st, k):
            for uid in order[:k]:
                v = st.find_permanent(uid)
                if v is not None:
                    st.emit(f"Sephiroth: sacrifice {v.name}")
                    st.leaves_battlefield(v, "graveyard", reason="sacrifice")
            if k:
                st.draw(k)
                st.emit(f"Sephiroth: drew {k} cards")
            return None

        return branch_over(state, list(range(len(order) + 1)), fn)

    def on_etb(self, state, permanent):
        return self._sac_one_draw(state, permanent)

    def on_attack(self, state, perm):
        if perm.transformed:
            return self._sac_any_draw(state, perm)
        return self._sac_one_draw(state, perm)

    def on_other_leave(self, state, perm, left, to, reason):
        if to != "graveyard" or not left.is_creature_now:
            return
        state.damage_opponent(1)  # noncombat -> amplifiers apply
        state.gain_life(1)
        state.emit(f"Sephiroth: opponent loses 1 ({state.opponent_life}), "
                   f"gain 1 ({state.life})")
        if not perm.transformed:
            perm.turn_flags["seph_deaths"] = perm.turn_flags.get("seph_deaths", 0) + 1
            if perm.turn_flags["seph_deaths"] >= 4:
                perm.transformed = True
                state.emit("Sephiroth transforms into One-Winged Angel (emblem)")
