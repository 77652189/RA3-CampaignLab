"""Adapter for the campaign writer's bare imports."""

from experimental.campaign import labpaths
from experimental.campaign.mapscript import MapFile  # bootstraps the writer's imports

import mapterrain
import newmap
import terrain_rules as rules
from platmap import BRIDGE_DECK, CONTAINER, RAMP_MAX, bridge

# The existing vectorized noise keeps the campaign writer's rounding and RNG order.
noise_field = newmap._noise_field
