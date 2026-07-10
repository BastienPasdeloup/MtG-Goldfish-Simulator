"""Mental Misstep — counter your own spell with mana value 1 (fills the graveyard).
Approximation: the Phyrexian-blue alternative cost is not modelled."""
from ._common import counterspell

MentalMisstep = counterspell("Mental Misstep", target=lambda c: int(c.cmc) == 1)
