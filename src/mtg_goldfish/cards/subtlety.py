"""Subtlety — {2}{U}{U} 3/3 flash, flying. Its ETB targets a creature or
planeswalker SPELL — nothing is ever on the stack in this solitaire engine, so
the trigger always fizzles (exact). Evoke: exile a blue card from your hand
instead of paying; sacrificed after entering."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Subtlety(Card):
    card_name = "Subtlety"

    def on_etb(self, state, permanent):
        state.emit("Subtlety: no spell to target (trigger fizzles)")
        if permanent.counters.get("evoked"):
            state.emit("Subtlety: evoke — sacrificed")
            state.leaves_battlefield(permanent, "graveyard")
        return None

    def hand_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_battlefield
        from ..engine.mana import ManaCost

        blues = sorted({c.name for c in state.hand
                        if "U" in c.colors and c.name != self.card_name})

        def make(blue_name: str):
            def pay(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                pitch = next((c for c in st.hand if c.name == blue_name), None)
                if card is None or pitch is None:
                    return False
                st.hand.remove(pitch)
                st.exile.append(pitch)
                st.emit(f"evoke Subtlety: exile {blue_name} from hand")
                if not begin_cast(st, card, ManaCost(), tag="evoke"):
                    return False
                return True

            def resolve(st):
                card = next((c for c in st.stack if c.name == self.card_name), None)
                if card is None:
                    return None
                return resolve_to_battlefield(st, card, marks={"evoked": 1}) or None

            return CardAction.activated(
                f"evoke Subtlety (exile {blue_name})",
                pay,
                resolve,
                source_name="Subtlety",
                ability_text=f"Evoke — exile {blue_name} from your hand",
            )

        return [make(b) for b in blues]
