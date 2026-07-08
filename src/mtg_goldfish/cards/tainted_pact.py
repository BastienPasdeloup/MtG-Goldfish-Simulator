"""Tainted Pact — {1}{B} Instant. Exile the top card; you may put it into your
hand unless it shares a name with a card exiled this way; repeat until you keep
one or exile two same-named cards. Deterministic given the (known) library
order — each stopping point is a branch; hitting a duplicate name ends it."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TaintedPact(Card):
    card_name = "Tainted Pact"

    def on_resolve(self, state):
        branches = []
        seen: set[str] = set()
        # Branch k = decline the first k cards, keep card k+1 (if allowed).
        for k in range(len(state.library)):
            name = state.library[k].name
            if name in seen:
                # Two same-named cards exiled: the process would stop here with
                # nothing kept — that terminal outcome is its own branch.
                b = state.clone()
                for _ in range(k + 1):
                    b.exile.append(b.library.pop(0))
                b.emit(f"Tainted Pact: hit duplicate {name} — {k + 1} cards exiled, none kept")
                branches.append(b)
                break
            seen.add(name)
            b = state.clone()
            for _ in range(k):
                b.exile.append(b.library.pop(0))
            kept = b.library.pop(0)
            b.hand.append(kept)
            b.emit(f"Tainted Pact: exiled {k}, kept {kept.name}")
            branches.append(b)
        return branches or None
