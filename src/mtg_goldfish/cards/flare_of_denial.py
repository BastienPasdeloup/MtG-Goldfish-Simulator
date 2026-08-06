"""Flare of Denial — {1}{U}{U} Instant.
You may sacrifice a nontoken blue creature rather than pay this spell's mana cost.
Counter target spell.

A counterspell (uses the shared counterspell mechanism): in a solitaire goldfish
there is normally no spell on the stack to counter, so it is only offered (to
counter your OWN spell) under instant-speed exploration. The alternative cost
(sacrifice a blue creature) is not separately modelled — countering has no
worthwhile target in solitaire, so the free-cast variant would change nothing."""
from ._common import counterspell

counterspell("Flare of Denial")
