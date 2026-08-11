"""Ley Druid — {2}{G} Creature — Human Druid 1/1.
{T}: Untap target land.

Untapping one of your tapped lands is real pseudo-ramp (frees the land to tap for
mana again this turn). One branch per distinct tapped land."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class LeyDruid(Card):
    card_name = "Ley Druid"

    def battlefield_actions(self, state, perm):
        if perm.tapped or perm.summoning_sick:
            return []
        acts = []
        seen: set[str] = set()
        for land in state.battlefield:
            if not land.is_land or not land.tapped or land.name in seen:
                continue
            seen.add(land.name)

            def make(uid, nm):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.tapped:
                        return False
                    p.tapped = True
                    return True

                def resolve(st):
                    tgt = st.find_permanent(uid)
                    if tgt is not None:
                        tgt.tapped = False
                        st.emit(f"Ley Druid: untap {nm}")
                    return None

                return CardAction.activated(
                    f"Ley Druid: {{T}} — untap {nm}",
                    pay, resolve, source_name="Ley Druid",
                    ability_text="untap target land")

            acts.append(make(land.uid, land.name))
        return acts
