"""Drowned Catacomb — check land: tapped unless you control an Island or a
Swamp. Taps for {U} or {B}."""
from ._common import check_land

check_land("Drowned Catacomb", ("U", "B"), ("Island", "Swamp"))
