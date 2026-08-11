"""Diamond Valley — Land.
{T}, Sacrifice a creature: You gain life equal to the sacrificed creature's
toughness.

A sacrifice outlet + lifegain: {T} and sac one of your creatures to gain its
toughness in life (one branch per creature)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class DiamondValley(Card):
    card_name = "Diamond Valley"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        acts = []
        seen: set[str] = set()
        for c in state.battlefield:
            if not c.is_creature_now or c.name in seen:
                continue
            seen.add(c.name)

            def make(uid, nm):
                def pay(st):
                    me = st.find_permanent(perm.uid)
                    victim = st.find_permanent(uid)
                    if me is None or me.tapped or victim is None:
                        return False
                    me.tapped = True
                    gain = st.effective_toughness(victim)
                    st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                    st.gain_life(max(0, gain))
                    st.emit(f"Diamond Valley: sacrifice {nm}, gain {max(0, gain)} life")
                    return True

                def resolve(st):
                    return None

                return CardAction.activated(
                    f"Diamond Valley: {{T}}, sacrifice {nm} — gain life",
                    pay, resolve, source_name="Diamond Valley",
                    ability_text="Gain life equal to the sacrificed creature's toughness")

            acts.append(make(c.uid, c.name))
        return acts
