"""Metallic Rebuke — {2}{U} Instant. Improvise.
Counter target spell unless its controller pays {3}.

A counterspell (uses the shared counterspell mechanism): with no opponent spells
on the stack in a solitaire game, it's only offered to counter your OWN spell
under instant-speed exploration. Improvise (which would cheapen its own cast) is
immaterial there, so it isn't separately modelled."""
from ._common import counterspell

counterspell("Metallic Rebuke")
