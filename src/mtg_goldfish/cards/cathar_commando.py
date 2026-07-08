"""Cathar Commando — {1}{W} 3/1 Flash. {1}, Sacrifice: destroy target artifact
or enchantment (only your own exist in solitaire)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class CatharCommando(Card):
    card_name = "Cathar Commando"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return []
        targets = [
            p for p in state.battlefield
            if p.uid != perm.uid
            and any(t in p.type_line.lower() for t in ("artifact", "enchantment"))
        ]

        def make(uid: int):
            def fn(st):
                me = st.find_permanent(perm.uid)
                target = st.find_permanent(uid)
                if me is None or target is None or not pay_cost(st, cost):
                    return None
                st.emit(f"sacrifice Cathar Commando: destroy {target.name}")
                st.leaves_battlefield(me, "graveyard")
                st.leaves_battlefield(target, "graveyard")
                return None
            return fn

        return [CardAction(f"Cathar Commando: sac, destroy {t.name}", make(t.uid))
                for t in targets]
