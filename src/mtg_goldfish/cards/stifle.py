"""Stifle — {U} Instant. Counter target activated or triggered ability. In a
solitaire game there is no opponent ability to counter (and countering your own
is never useful), so it is never castable."""
from __future__ import annotations

from ._common import uncastable_spell

uncastable_spell("Stifle", "no opponent activated/triggered ability to target")
