"""Tetravus — {6} Artifact Creature — Construct 1/1, Flying.
Enters with three +1/+1 counters. At the beginning of your upkeep you may remove
any number of +1/+1 counters to create that many 1/1 flying Tetravite artifact
creature tokens; and you may exile any number of Tetravite tokens to put that many
+1/+1 counters back.

Enters as a 4/4 flier. Each upkeep offers one conversion — split K counters into K
tokens, or merge J tokens back into J counters (one branch per amount, plus doing
nothing)."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class Tetravus(Card):
    card_name = "Tetravus"
    trigger_phase = Phase.UPKEEP

    def enters_with_counters(self, state):
        return {"+1/+1": 3}

    def on_phase(self, state, perm, phase):
        p = state.find_permanent(perm.uid)
        if p is None:
            return None
        counters = p.counters.get("+1/+1", 0)
        tokens = [t for t in state.battlefield if t.is_token and t.name == "Tetravite"]
        options = ["nothing"]
        options += [f"split:{k}" for k in range(1, counters + 1)]
        options += [f"merge:{j}" for j in range(1, len(tokens) + 1)]
        if len(options) == 1:
            return None

        def fn(st, opt):
            live = st.find_permanent(perm.uid)
            if opt == "nothing" or live is None:
                return None
            kind, n = opt.split(":")
            n = int(n)
            if kind == "split":
                take = min(n, live.counters.get("+1/+1", 0))
                live.counters["+1/+1"] = live.counters.get("+1/+1", 0) - take
                for _ in range(take):
                    st.make_token("Tetravite", 1, 1, "Token Artifact Creature — Tetravite",
                                  text="Flying")
                st.emit(f"Tetravus: remove {take} counter(s) → {take} Tetravite token(s)")
            else:  # merge tokens back into counters
                toks = [t for t in st.battlefield if t.is_token and t.name == "Tetravite"][:n]
                for t in toks:
                    st.leaves_battlefield(t, "exile", reason=None)
                live.counters["+1/+1"] = live.counters.get("+1/+1", 0) + len(toks)
                st.emit(f"Tetravus: exile {len(toks)} token(s) → {len(toks)} counter(s)")
            return None

        return branch_over(state, options, fn)
