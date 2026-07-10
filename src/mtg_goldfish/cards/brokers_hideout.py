"""Brokers Hideout — Land. ETB: sacrifice; fetch a basic Forest/Plains/Island
tapped, gain 1 life (see `_common.sac_fetch_land`)."""
from ._common import sac_fetch_land

BrokersHideout = sac_fetch_land("Brokers Hideout", ("Forest", "Plains", "Island"))
