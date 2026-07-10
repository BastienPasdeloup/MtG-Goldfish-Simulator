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
            def pay(st):
                me = st.find_permanent(perm.uid)
                target = st.find_permanent(uid)
                if me is None or target is None or not pay_cost(st, cost):
                    return False
                st.emit("sacrifice Cathar Commando")
                st.leaves_battlefield(me, "graveyard")
                return True

            def resolve(st):
                target = st.find_permanent(uid)
                if target is None:
                    return None
                st.emit(f"Cathar Commando: destroy {target.name}")
                st.leaves_battlefield(target, "graveyard")
                return None
            return CardAction.activated(
                f"Cathar Commando: sac, destroy {state.find_permanent(uid).name if state.find_permanent(uid) else uid}",
                pay,
                resolve,
                source_name="Cathar Commando",
                ability_text="Destroy target artifact or enchantment",
            )

        return [make(t.uid) for t in targets]
