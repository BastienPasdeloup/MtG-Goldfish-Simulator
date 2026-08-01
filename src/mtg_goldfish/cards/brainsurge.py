"""Brainsurge — {2}{U} Instant. Draw four cards, then put two cards from your
hand on top of your library in any order.

Really draws four into your hand and then puts back TWO cards chosen from the
WHOLE hand (which may be cards you already held, not just the four just drawn),
in a chosen order — the top card is drawn next. Branch over the ordered pair of
cards put back (deduped by name, capped) so the search can keep the best four
and set up the top of the library. Net +2 cards."""
from ._common import branch_over
from .base import Card
from .registry import register

# Bound the put-back fan-out (ordered distinct-name pairs) on a large hand.
_MAX_PUTBACK = 40


@register
class Brainsurge(Card):
    card_name = "Brainsurge"

    def on_resolve(self, state):
        state.draw(4)
        state.emit("Brainsurge: draw four")
        if len(state.hand) < 2:
            return None
        # Ordered (top, second) index pairs, deduped by the card NAMES so two
        # copies of the same card don't multiply the branching. `top` ends up on
        # top of the library (drawn next); `second` just beneath it.
        options: list[tuple[int, int]] = []
        seen: set[tuple[str, str]] = set()
        hand = state.hand
        for a in range(len(hand)):
            for b in range(len(hand)):
                if a == b:
                    continue
                key = (hand[a].name, hand[b].name)
                if key in seen:
                    continue
                seen.add(key)
                options.append((a, b))
                if len(options) >= _MAX_PUTBACK:
                    break
            if len(options) >= _MAX_PUTBACK:
                break

        def fn(st, opt):
            a, b = opt
            top_card, second_card = st.hand[a], st.hand[b]
            st.hand[:] = [c for i, c in enumerate(st.hand) if i != a and i != b]
            st.library[:0] = [top_card, second_card]  # top_card is drawn first
            st.mark_known_in_library(top_card, second_card)
            st.emit(f"Brainsurge: put {top_card.name}, {second_card.name} back on top")
            return None

        return branch_over(state, options, fn)
