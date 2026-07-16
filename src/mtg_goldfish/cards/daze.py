"""Daze — counter a spell (needs a spell on the stack; not castable in a goldfish). See `_common.counterspell`."""
from ._common import counterspell

Daze = counterspell("Daze", note="Approximation: the alternative cost (return an Island) is not modelled.")
