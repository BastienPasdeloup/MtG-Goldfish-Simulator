"""Nick Fury, Agent of S.H.I.E.L.D. — {W} Legendary Creature 2/1 (commander).

Power-up — {W}{U}{B}{R}{G}: put two +1/+1 counters on Nick Fury, then look at
the top seven cards; you may put a Hero CREATURE, Equipment or Vehicle card
from among them onto the battlefield; the rest go to the bottom in a random
order. Activate only once (per permanent). The cost is reduced by his mana
cost ({W}) if he entered this turn; Advancing the Spirit lets the first
power-up each turn cost {0} instead.

A double-faced card put this way enters on its FRONT face and transforms as
part of the same resolution (NOT a triggered ability); the front face's ETB
triggers go on the stack and resolve after the power-up has fully resolved."""
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


def _power_up_spent(perm) -> bool:
    """"Activate only once." — tracked PER PERMANENT: a creature that gains
    the power-up via Deadpool's text-box exchange may activate it even if the
    original creature already used its own."""
    return bool(perm.counters.get("powered_up"))


def _is_puttable(card) -> bool:
    """A Hero CREATURE, an Equipment, or a Vehicle. For double-faced cards the
    card's characteristics off the battlefield are its FRONT face's."""
    tl = (card.faces[0].type_line if card.faces else "") or card.type_line
    if "Equipment" in tl or "Vehicle" in tl:
        return True
    return "Hero" in tl and "Creature" in tl


@register
class NickFury(Card):
    card_name = "Nick Fury, Agent of S.H.I.E.L.D."

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if _power_up_spent(perm):
            return []
        cost, tag = _powerup_cost(state, perm)
        if not can_afford(state, cost):
            return []

        top7 = state.library[:7]
        # Puttable targets first, "put nothing" last: the first satisfying
        # line found (shown in the replay) then actually uses the ability.
        choices: list[str | None] = []
        seen: set[str] = set()
        for c in top7:
            if _is_puttable(c) and c.name not in seen:
                seen.add(c.name)
                choices.append(c.name)
        choices.append(None)

        def make(put_name: str | None):
            def pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or _power_up_spent(p):
                    return False
                c, t = _powerup_cost(st, p)
                if not pay_cost(st, c):
                    return False
                if t == "free via Advancing the Spirit":
                    for adv in st.battlefield:
                        if adv.card.name == "Advancing the Spirit":
                            adv.turn_flags["powerup_free_used"] = 1
                            break
                p.counters["powered_up"] = 1  # "Activate only once."
                st.emit(f"Power-up {p.name} ({t})")
                return True

            def resolve(st):
                p = st.find_permanent(perm.uid)
                if p is None:
                    return None
                p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + 2
                st.emit(f"Power-up {p.name}: +2 counters, look at top 7")
                seven = st.library[:7]
                del st.library[: len(seven)]
                newp = chosen = None
                if put_name is not None:
                    chosen = next((c2 for c2 in seven if c2.name == put_name), None)
                    if chosen is not None:
                        seven.remove(chosen)
                        newp = st.put_on_battlefield(chosen, fire_etb=False)
                        # Property-visible: the power-up found a target and put
                        # it into play — state.ability_succeeded("Nick Fury").
                        # Attributed to the PERMANENT's name: after Deadpool's
                        # text exchange the ability belongs to Deadpool.
                        st.note_event("ability_success", p.name,
                                      detail=f"put {chosen.name} onto the battlefield")
                        st.emit(f"Power-up: put {chosen.name} onto the battlefield")
                # Rest to the bottom in a random (deterministic-seeded) order —
                # before any entry trigger resolves, like the printed ability.
                rng_cards = list(seven)
                import random as _r
                _r.Random(st.rng_seed * 7919 + st._next_uid).shuffle(rng_cards)
                st._next_uid += 1
                st.library.extend(rng_cards)
                branches = None
                if newp is not None:
                    # "As it enters" choices fan out first (e.g. Deadpool's
                    # text-box exchange) — part of entering, not a trigger.
                    branches = newp.impl.enter_choices(st, newp)
                    for s in (branches or [st]):
                        live = s.find_permanent(newp.uid)
                        if live is None:
                            continue
                        # The FRONT face's ETB (and other permanents' "another
                        # permanent entered" triggers) go on the stack now, but
                        # only START resolving once this whole ability has
                        # finished resolving (resolutions are atomic).
                        s.queue_entry_triggers([live])
                        if chosen.is_double_faced and not live.transformed:
                            # Transforming is PART of this resolution — not a
                            # triggered ability.
                            front = live.name
                            live.transformed = True
                            s.emit(f"Power-up: {front} transforms into {live.name}")
                st.check_deaths()
                return branches
            return pay, resolve

        out = []
        for name in choices:
            # Label/source follow the PERMANENT holding the text box — after
            # Deadpool's exchange the power-up is Deadpool's, under his name.
            label = f"Power-up {perm.name} ({tag})" + (f" → put {name}" if name else " → put nothing")
            pay, resolve = make(name)
            out.append(CardAction.activated(
                label,
                pay,
                resolve,
                source_name=perm.name,
                ability_text="Power-up — +2 +1/+1 counters; look at the top seven",
            ))
        return out
