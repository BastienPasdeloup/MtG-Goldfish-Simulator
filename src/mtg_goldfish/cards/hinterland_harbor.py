"""Hinterland Harbor — check land: tapped unless you control a Forest or an
Island. Taps for {G} or {U}."""
from ._common import check_land

check_land("Hinterland Harbor", ("G", "U"), ("Forest", "Island"))
