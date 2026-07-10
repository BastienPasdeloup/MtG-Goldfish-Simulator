"""Tale's End — counter your own legendary spell (fills the graveyard).
Approximation: countering activated/triggered abilities is not modelled."""
from ._common import counterspell

TalesEnd = counterspell(
    "Tale's End", target=lambda c: "legendary" in c.type_line.lower(),
)
