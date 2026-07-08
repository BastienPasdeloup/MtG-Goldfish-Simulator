"""Lion Sash — {1}{W} Artifact Creature — Equipment Cat 1/1.
{W}: exile target card from a graveyard; if it was a permanent card, +1/+1
counter (branch per distinct graveyard card). Equipped creature gets +1/+1 per
counter on Lion Sash. Reconfigure {2} attaches it (it stops being a creature —
type change not modelled beyond the attachment)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class LionSash(Card):
    card_name = "Lion Sash"

    def equip_mod(self, state, perm):
        n = perm.counters.get("+1/+1", 0)
        return (n, n)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        actions: list[CardAction] = []
        cost_w = ManaCost(pips=(("W", 1),))
        if can_afford(state, cost_w):
            seen: set[str] = set()
            for card in state.graveyard:
                if card.name in seen:
                    continue
                seen.add(card.name)

                def make(name: str):
                    def fn(st):
                        p = st.find_permanent(perm.uid)
                        c = next((x for x in st.graveyard if x.name == name), None)
                        if p is None or c is None or not pay_cost(st, cost_w):
                            return None
                        st.graveyard.remove(c)
                        st.exile.append(c)
                        if c.is_permanent:
                            p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + 1
                        st.emit(f"Lion Sash: exile {name} from graveyard"
                                + (" (+1/+1)" if c.is_permanent else ""))
                        return None
                    return fn

                actions.append(CardAction(f"Lion Sash: exile {card.name} from GY", make(card.name)))

        # Reconfigure {2}: attach to a creature you control (sorcery speed).
        cost_r = ManaCost(generic=2)
        if perm.attached_to is None and can_afford(state, cost_r):
            for target in state.battlefield:
                if not target.is_creature_now or target.uid == perm.uid:
                    continue

                def make_att(uid: int):
                    def fn(st):
                        p = st.find_permanent(perm.uid)
                        t = st.find_permanent(uid)
                        if p is None or t is None or not pay_cost(st, cost_r):
                            return None
                        p.attached_to = t.uid
                        st.emit(f"reconfigure Lion Sash onto {t.name}")
                        return None
                    return fn

                actions.append(CardAction(f"reconfigure Lion Sash → {target.name}",
                                          make_att(target.uid)))
        return actions
