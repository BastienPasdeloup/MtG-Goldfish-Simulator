"""Tale's End — counter a legendary spell (needs a spell on the stack; not castable in a goldfish).
Approximation: countering activated/triggered abilities is not modelled."""
from ._common import counterspell

TalesEnd = counterspell(
    "Tale's End", target=lambda c: "legendary" in c.type_line.lower(),
)
