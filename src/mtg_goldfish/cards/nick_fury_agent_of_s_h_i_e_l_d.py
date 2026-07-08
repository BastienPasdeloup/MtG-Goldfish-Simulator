"""Nick Fury, Agent of S.H.I.E.L.D. — {W} Legendary Creature 2/1 (commander).

Power-up — {W}{U}{B}{R}{G}: put two +1/+1 counters on Nick Fury, then look at
the top seven cards; you may put a Hero, Equipment or Vehicle card from among
them onto the battlefield; the rest go to the bottom in a random order.
Activate only once (per permanent). The cost is reduced by his mana cost ({W})
if he entered this turn; Advancing the Spirit lets the first power-up each
turn cost {0} instead.

Not modelled: "you may transform it" for a double-faced card put onto the
battlefield this way (it enters front face)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


def _powerup_cost(state, perm) -> tuple[ManaCost, str]:
    # Advancing the Spirit: pay {0} for the first power-up ability each turn.
    for p in state.battlefield:
        if p.card.name == "Advancing the Spirit" and not p.turn_flags.get("powerup_free_used"):
            return ManaCost(), "free via Advancing the Spirit"
    if perm.summoning_sick:  # entered this turn: reduce by his mana cost ({W})
        return ManaCost(pips=(("U", 1), ("B", 1), ("R", 1), ("G", 1))), "reduced {U}{B}{R}{G}"
    return ManaCost(pips=(("W", 1), ("U", 1), ("B", 1), ("R", 1), ("G", 1))), "{W}{U}{B}{R}{G}"


def _is_puttable(card) -> bool:
    return any(t in card.type_line for t in ("Hero", "Equipment", "Vehicle"))


@register
class NickFury(Card):
    card_name = "Nick Fury, Agent of S.H.I.E.L.D."

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.counters.get("powered_up"):
            return []
        cost, tag = _powerup_cost(state, perm)
        if not can_afford(state, cost):
            return []

        top7 = state.library[:7]
        choices: list[str | None] = [None]
        seen: set[str] = set()
        for c in top7:
            if _is_puttable(c) and c.name not in seen:
                seen.add(c.name)
                choices.append(c.name)

        def make(put_name: str | None):
            def fn(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.counters.get("powered_up"):
                    return None
                c, t = _powerup_cost(st, p)
                if not pay_cost(st, c):
                    return None
                if t == "free via Advancing the Spirit":
                    for adv in st.battlefield:
                        if adv.card.name == "Advancing the Spirit":
                            adv.turn_flags["powerup_free_used"] = 1
                            break
                p.counters["powered_up"] = 1
                p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + 2
                st.emit(f"Power-up Nick Fury ({t}): +2 counters, look at top 7")
                seven = st.library[:7]
                del st.library[: len(seven)]
                branches = None
                if put_name is not None:
                    chosen = next((c2 for c2 in seven if c2.name == put_name), None)
                    if chosen is not None:
                        seven.remove(chosen)
                        newp = st.put_on_battlefield(chosen, fire_etb=False)
                        st.emit(f"Power-up: put {chosen.name} onto the battlefield")
                        branches = newp.impl.on_etb(st, newp)
                # Rest to the bottom in a random (deterministic-seeded) order.
                rng_cards = list(seven)
                import random as _r
                _r.Random(st.rng_seed * 7919 + st._next_uid).shuffle(rng_cards)
                st._next_uid += 1
                st.library.extend(rng_cards)
                st.check_deaths()
                return branches
            return fn

        out = []
        for name in choices:
            label = f"Power-up Nick Fury ({tag})" + (f" → put {name}" if name else " → put nothing")
            out.append(CardAction(label, make(name)))
        return out
