"""Memory Lapse — counter your own spell; put it on top of your library.
Lets you re-draw a spell next turn (does not fill the graveyard)."""
from ._common import counterspell

MemoryLapse = counterspell("Memory Lapse", dest="library_top")
