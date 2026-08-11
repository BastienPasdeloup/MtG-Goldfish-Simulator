"""Dwarven Demolition Team — {2}{R} Creature — Dwarf 1/1.
{T}: Destroy target Wall.

Aimed at an opponent's Wall; only your own Walls are available to target here (a
downside), but the ability is offered — one branch per distinct Wall you
control."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class DwarvenDemolitionTeam(Card):
    card_name = "Dwarven Demolition Team"

    def battlefield_actions(self, state, perm):
        if perm.tapped or (perm.summoning_sick and not state.has_keyword(perm, "Haste")):
            return []
        acts = []
        seen = set()
        for p in state.battlefield:
            if not (p.is_creature_now and "wall" in p.type_line.lower()) or p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    if src is None or src.tapped:
                        return False
                    src.tapped = True
                    return True

                def resolve(st):
                    t = st.find_permanent(uid)
                    if t is not None:
                        st.emit(f"Dwarven Demolition Team: destroy {nm}")
                        st.leaves_battlefield(t, "graveyard", reason="destroy")
                    return None

                return CardAction.activated(
                    f"Dwarven Demolition Team: {{T}} — destroy {nm}",
                    pay, resolve, source_name="Dwarven Demolition Team",
                    ability_text="Destroy target Wall")

            acts.append(make(p.uid, p.name))
        return acts
