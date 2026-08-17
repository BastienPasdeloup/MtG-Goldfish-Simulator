"""Xenic Poltergeist — {1}{B}{B} Creature — Spirit 1/1.
{T}: Until your next upkeep, target noncreature artifact becomes an artifact
creature with power and toughness each equal to its mana value.

Animates one of your noncreature artifacts (a mana rock into an attacker), P/T =
its mana value, via a `becomes` override. Modelled as lasting until end of turn
(cleared at cleanup) — the turn you'd attack with it, which is one upkeep short of
"until your next upkeep" but functionally the same window in a goldfish. One
branch per distinct noncreature artifact you control."""
from __future__ import annotations

from ._common import mv
from .base import Card, CardAction
from .registry import register


@register
class XenicPoltergeist(Card):
    card_name = "Xenic Poltergeist"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        seen, targets = set(), []
        for p in state.battlefield:
            if p.is_artifact and not p.is_creature_now and p.name not in seen:
                seen.add(p.name)
                targets.append(p.uid)
        acts = []
        for tuid in targets:
            t0 = state.find_permanent(tuid)
            n = mv(t0.card)

            def make(tuid=tuid, n=n, tname=t0.name):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    if src is None or src.tapped:
                        return False
                    src.tapped = True
                    return True

                def resolve(st):
                    t = st.find_permanent(tuid)
                    if t is not None:
                        t.becomes = {"type_line": "Artifact Creature", "power": n,
                                     "toughness": n, "permanent": False}
                        st.emit(f"Xenic Poltergeist: {tname} becomes a {n}/{n} artifact creature")
                        st.check_deaths()
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Xenic Poltergeist: {{T}} → animate {t0.name} ({n}/{n})",
                pay, resolve, source_name="Xenic Poltergeist",
                ability_text="Target noncreature artifact becomes an artifact creature with P/T = its mana value"))
        return acts
