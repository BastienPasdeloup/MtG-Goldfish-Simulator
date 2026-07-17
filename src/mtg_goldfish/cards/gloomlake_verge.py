"""Gloomlake Verge — verge land: {T}: Add {U}; {T}: Add {B} only if you control
an Island or a Swamp."""
from ._common import verge_land

verge_land("Gloomlake Verge", "U", "B", ("Island", "Swamp"))
