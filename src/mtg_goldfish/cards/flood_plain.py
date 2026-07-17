"""Flood Plain — slow fetchland: enters tapped; {T}, Sacrifice: search a Plains
or Island card onto the battlefield, then shuffle."""
from ._common import slow_fetch_land

slow_fetch_land("Flood Plain", ("Plains", "Island"))
