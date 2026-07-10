"""Cabaretti Courtyard — Land. ETB: sacrifice; fetch a basic
Mountain/Forest/Plains tapped, gain 1 life (see `_common.sac_fetch_land`)."""
from ._common import sac_fetch_land

CabarettiCourtyard = sac_fetch_land("Cabaretti Courtyard", ("Mountain", "Forest", "Plains"))
