"""Force of Negation — counter a NONCREATURE spell (needs a spell on the stack; not castable in a goldfish).
Approximation: the free alternative cost (exile a blue card) is not modelled."""
from ._common import counterspell

ForceOfNegation = counterspell(
    "Force of Negation", target=lambda c: not c.is_creature,
)
