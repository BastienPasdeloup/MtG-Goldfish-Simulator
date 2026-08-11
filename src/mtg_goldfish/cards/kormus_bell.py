"""Kormus Bell — {4} Artifact.
All Swamps are 1/1 black creatures that are still lands.

Continuous global animate: every Swamp becomes a 1/1 black creature (still a land,
still taps for {B}) while Kormus Bell is in play — so your Swamps can attack and
can die to damage / board wipes."""
from ._common import global_land_animator

global_land_animator("Kormus Bell", "Swamp", "B")
