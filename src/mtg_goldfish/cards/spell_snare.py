"""Spell Snare — counter your own spell with mana value 2 (fills the graveyard)."""
from ._common import counterspell

SpellSnare = counterspell("Spell Snare", target=lambda c: int(c.cmc) == 2)
