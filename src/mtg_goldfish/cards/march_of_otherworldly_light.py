"""March of Otherworldly Light — {X}{W} Instant. Optionally exile white cards
from hand ({2} less per card); exile target artifact/creature/enchantment with
mana value ≤ X. Branches over (target, number of white cards exiled) with
X = target's mana value. Which white cards to exile is chosen deterministically
(highest mana value first) — an approximation."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class MarchOfOtherworldlyLight(Card):
    card_name = "March of Otherworldly Light"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        whites = [c for c in state.hand
                  if "W" in c.colors and c.name != self.card_name]
        targets = [
            p for p in state.battlefield
            if any(t in p.type_line.lower() for t in ("artifact", "creature", "enchantment"))
        ]
        actions = []
        for target in targets:
            x = int(target.card.cmc)
            for k in range(0, min(len(whites), (x + 1) // 2 + 1) + 1):
                cost = ManaCost(generic=max(0, x - 2 * k), pips=(("W", 1),))
                if not can_afford(state, cost):
                    continue

                def make(uid: int, kk: int, cst: ManaCost, xx: int):
                    def fn(st):
                        card = next((c for c in st.hand if c.name == self.card_name), None)
                        perm = st.find_permanent(uid)
                        if card is None or perm is None:
                            return None
                        ws = sorted(
                            [c for c in st.hand if "W" in c.colors and c.name != self.card_name],
                            key=lambda c: -c.cmc,
                        )[:kk]
                        if len(ws) < kk:
                            return None
                        for w in ws:
                            st.hand.remove(w)
                            st.exile.append(w)
                        if kk:
                            st.emit(f"March: exile {', '.join(w.name for w in ws)} from hand")
                        if not begin_cast(st, card, cst, tag=f"X={xx}"):
                            return None
                        resolve_to_graveyard(st, card)
                        st.emit(f"March of Otherworldly Light: exile {perm.name}")
                        st.leaves_battlefield(perm, "exile")
                        return None
                    return fn

                suffix = f" (exiling {k} white)" if k else ""
                actions.append(CardAction(
                    f"cast March X={x} → {target.name}{suffix}",
                    make(target.uid, k, cost, x),
                ))
        return actions
