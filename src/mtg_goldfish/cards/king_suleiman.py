"""King Suleiman — {1}{W} Creature — Human Noble 1/1.
{T}: Destroy target Djinn or Efreet.

Only your own Djinns/Efreet are available in a solitaire goldfish (rarely worth
it, but the ability is offered) — one branch per distinct Djinn/Efreet you
control."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class KingSuleiman(Card):
    card_name = "King Suleiman"

    def battlefield_actions(self, state, perm):
        if perm.tapped or perm.summoning_sick:
            return []
        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            tl = p.type_line.lower()
            if not p.is_creature_now or ("djinn" not in tl and "efreet" not in tl) or p.name in seen:
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
                        st.emit(f"King Suleiman: destroy {nm}")
                        st.leaves_battlefield(tgt, "graveyard", reason="destroy")
                    return None

                return CardAction.activated(
                    f"King Suleiman: {{T}} — destroy {nm}",
                    pay, resolve, source_name="King Suleiman",
                    ability_text="Destroy target Djinn or Efreet")

            acts.append(make(p.uid, p.name))
        return acts
