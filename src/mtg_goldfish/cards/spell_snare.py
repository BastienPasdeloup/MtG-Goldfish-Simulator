"""Spell Snare — counter a spell with mana value 2 (needs a spell on the stack; not castable in a goldfish)."""
from ._common import counterspell

SpellSnare = counterspell("Spell Snare", target=lambda c: int(c.cmc) == 2)
