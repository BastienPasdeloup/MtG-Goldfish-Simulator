"""Aether Spellbomb — {1} Artifact.
{U}, Sacrifice this artifact: Return target creature to its owner's hand.
{1}, Sacrifice this artifact: Draw a card.

Neither ability taps the Spellbomb. In a solitaire game the bounce can only
target your OWN creatures (one branch each) — rarely useful but faithful; the
draw mode is the usual one."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class AetherSpellbomb(Card):
    card_name = "Aether Spellbomb"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        acts: list[CardAction] = []

        # {1}, Sacrifice: Draw a card.
        draw_cost = ManaCost(generic=1)
        if can_afford(state, draw_cost):
            def pay_draw(st):
                p = st.find_permanent(perm.uid)
                if p is None or not pay_cost(st, draw_cost):
                    return False
                st.leaves_battlefield(p, "graveyard", reason="sacrifice")
                return True

            def resolve_draw(st):
                st.emit("Aether Spellbomb: draw a card")
                st.draw(1)
                return None

            acts.append(CardAction.activated(
                "Aether Spellbomb: {1}, sacrifice — draw a card",
                pay_draw, resolve_draw, source_name="Aether Spellbomb",
                ability_text="Draw a card"))

        # {U}, Sacrifice: Return target creature to its owner's hand.
        bounce_cost = ManaCost(pips=(("U", 1),))
        if can_afford(state, bounce_cost):
            seen: set[str] = set()
            for target in state.battlefield:
                if not target.is_creature_now or target.is_token or target.name in seen:
                    continue
                seen.add(target.name)

                def build(vuid, vname):
                    def pay(st):
                        p = st.find_permanent(perm.uid)
                        victim = st.find_permanent(vuid)
                        if p is None or victim is None or not pay_cost(st, bounce_cost):
                            return False
                        st.leaves_battlefield(p, "graveyard", reason="sacrifice")
                        return True

                    def resolve(st):
                        victim = st.find_permanent(vuid)
                        if victim is not None:
                            st.leaves_battlefield(victim, "hand")
                            st.emit(f"Aether Spellbomb: return {vname} to hand")
                        return None

                    return CardAction.activated(
                        f"Aether Spellbomb: {{U}}, sacrifice — return {vname} to hand",
                        pay, resolve, source_name="Aether Spellbomb",
                        ability_text="Return target creature to its owner's hand")

                acts.append(build(target.uid, target.name))
        return acts
