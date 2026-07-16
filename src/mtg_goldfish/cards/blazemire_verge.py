"""Blazemire Verge — verge land: {T}: Add {B}; {T}: Add {R} only if you control
a Swamp or a Mountain."""
from ._common import verge_land

verge_land("Blazemire Verge", "B", "R", ("Swamp", "Mountain"))
