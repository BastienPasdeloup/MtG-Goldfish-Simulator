"""No More Lies — counter a spell (needs a spell on the stack; not castable in a goldfish).
(The exile clause is not modelled — the target still goes to the graveyard.)"""
from ._common import counterspell

NoMoreLies = counterspell("No More Lies")
