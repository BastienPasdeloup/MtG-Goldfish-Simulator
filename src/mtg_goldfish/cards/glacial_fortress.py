"""Glacial Fortress — check land: tapped unless you control a Plains or an
Island. Taps for {W} or {U}."""
from ._common import check_land

check_land("Glacial Fortress", ("W", "U"), ("Plains", "Island"))
