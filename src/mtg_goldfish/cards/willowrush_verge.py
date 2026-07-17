"""Willowrush Verge — verge land: {T}: Add {U}; {T}: Add {G} only if you control
a Forest or an Island."""
from ._common import verge_land

verge_land("Willowrush Verge", "U", "G", ("Forest", "Island"))
