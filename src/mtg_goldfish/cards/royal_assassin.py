"""Royal Assassin — {1}{B}{B} Creature — Human Assassin 1/1.
{T}: Destroy target tapped creature.

Only your own tapped creatures are available in a solitaire goldfish (rarely worth
it, but the ability is offered) — one branch per distinct tapped creature.
Respects indestructible/regeneration."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class RoyalAssassin(Card):
    card_name = "Royal Assassin"

    def battlefield_actions(self, state, perm):
        if perm.tapped or perm.summoning_sick:
            return []
        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if not p.is_creature_now or not p.tapped or p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def pay(st):
                    me = st.find_permanent(perm.uid)
                    if me is None or me.tapped or me.summoning_sick:
                        return False
                    me.tapped = True
                    return True

                def resolve(st):
                    tgt = st.find_permanent(uid)
                    if tgt is not None:
                        st.emit(f"Royal Assassin: destroy {nm}")
                        st.leaves_battlefield(tgt, "graveyard", reason="destroy")
                    return None

                return CardAction.activated(
                    f"Royal Assassin: {{T}} — destroy tapped {nm}",
                    pay, resolve, source_name="Royal Assassin",
                    ability_text="Destroy target tapped creature")

            acts.append(make(p.uid, p.name))
        return acts
