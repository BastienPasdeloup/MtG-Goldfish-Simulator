"""Time Vault — {2} Artifact.
This artifact enters tapped.
This artifact doesn't untap during your untap step.
If you would begin your turn while this artifact is tapped, you may skip that turn
instead. If you do, untap this artifact.
{T}: Take an extra turn after this one.

Enters tapped and never untaps on its own (skips_untap). {T} queues an extra turn.
The "skip a turn to untap it" clause is not modelled (skipping a turn is strictly
bad in a goldfish); instead an external untapper (Twiddle, etc.) re-enables it —
the classic Time Vault combo."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class TimeVault(Card):
    card_name = "Time Vault"

    def skips_untap(self, state, perm):
        return True

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return False
            p.tapped = True
            return True

        def resolve(st):
            st.extra_turns += 1
            st.emit("Time Vault: take an extra turn")
            return None

        return [CardAction.activated(
            "Time Vault: {T} — take an extra turn",
            pay, resolve, source_name="Time Vault",
            ability_text="Take an extra turn after this one")]
