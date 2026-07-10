"""Riveteers Overlook — Land. ETB: sacrifice; fetch a basic
Swamp/Mountain/Forest tapped, gain 1 life (see `_common.sac_fetch_land`)."""
from ._common import sac_fetch_land

RiveteersOverlook = sac_fetch_land("Riveteers Overlook", ("Swamp", "Mountain", "Forest"))
