"""Mental Misstep — counter a spell with mana value 1 (needs a spell on the stack; not castable in a goldfish).
Approximation: the Phyrexian-blue alternative cost is not modelled."""
from ._common import counterspell

MentalMisstep = counterspell("Mental Misstep", target=lambda c: int(c.cmc) == 1)
