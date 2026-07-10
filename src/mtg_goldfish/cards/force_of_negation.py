"""Force of Negation — counter your own NONCREATURE spell (fills the graveyard).
Approximation: the free alternative cost (exile a blue card) is not modelled."""
from ._common import counterspell

ForceOfNegation = counterspell(
    "Force of Negation", target=lambda c: not c.is_creature,
)
