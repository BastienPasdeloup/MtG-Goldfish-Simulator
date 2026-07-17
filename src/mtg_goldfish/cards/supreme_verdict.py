"""Supreme Verdict — {1}{W}{W}{U} Sorcery. Can't be countered. Destroy all
creatures. In a goldfish this wipes only your own board, so it is castable but
rarely a useful line."""
from .base import Card
from .registry import register


@register
class SupremeVerdict(Card):
    card_name = "Supreme Verdict"

    def on_resolve(self, state):
        wiped = [p for p in list(state.battlefield) if p.is_creature_now]
        for p in wiped:
            state.leaves_battlefield(p, "graveyard", reason="destroy")
        state.emit(f"Supreme Verdict: destroy all creatures ({len(wiped)})")
