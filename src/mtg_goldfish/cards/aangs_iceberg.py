"""Aang's Iceberg — {2}{W} Enchantment, flash. When it enters, exile up to one
other target nonland permanent until this leaves the battlefield (blink your own
permanent to re-use its ETB). Waterbend {3}: Sacrifice it; if you do, scry 2."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over, enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class AangsIceberg(Card):
    card_name = "Aang's Iceberg"

    def on_etb(self, state, permanent):
        options = [("none", None)]
        seen = set()
        for p in state.battlefield:
            if p.uid != permanent.uid and not p.is_land and p.name not in seen and not p.is_token:
                seen.add(p.name)
                options.append((p.name, p.uid))
        if len(options) == 1:
            return None

        def fn(st, opt):
            _label, uid = opt
            me = st.find_permanent(permanent.uid)
            if uid is None or me is None:
                return None
            target = st.find_permanent(uid)
            if target is not None:
                me.exiled_with.append(target.card)
                st.emit(f"Aang's Iceberg: exile {target.name} until it leaves")
                st.leaves_battlefield(target, "exile")
            return None

        return branch_over(state, options, fn)

    def on_leave(self, state, permanent):
        for c in permanent.exiled_with:
            if c in state.exile:
                state.exile.remove(c)
            enter_battlefield(state, c, announce=f"Aang's Iceberg leaves: return {c.name}")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3)
        if not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or not pay_cost(st, cost):
                return False
            st.emit("Aang's Iceberg: waterbend — sacrifice")
            st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            top = st.library[:2]
            if not top:
                return None
            combos = [()]
            for _ in top:
                combos = [c + (b,) for c in combos for b in (False, True)]

            def scry(s, to_bottom):
                pool = s.library[:len(to_bottom)]
                del s.library[:len(to_bottom)]
                keep = [c for i, c in enumerate(pool) if not to_bottom[i]]
                bottom = [c for i, c in enumerate(pool) if to_bottom[i]]
                s.library[:0] = keep
                s.library.extend(bottom)
                s.emit(f"Aang's Iceberg: scry 2 — bottom {len(bottom)}")
                return None

            return branch_over(st, combos, scry)

        return [CardAction.activated(
            "Aang's Iceberg: waterbend {3}, sacrifice — scry 2",
            pay, resolve, source_name="Aang's Iceberg",
            ability_text="Sacrifice; scry 2")]
