"""Economic infiltration pads: two isolated refineries facing their ore."""
import resources
from maps import probe_range

FIELDS = [*probe_range.FIELDS, resources.Field('enemy', 800.0, 400.0, 45.0, 0),
          resources.Field('ally', 2300.0, 400.0, 45.0, 0)]
SITES = {**probe_range.SITES, **resources.sites(FIELDS)}
OBJECTS = resources.objects(FIELDS)
PLAYERS = probe_range.PLAYERS
TEAMS = probe_range.TEAMS
terrain = probe_range.terrain
ground = probe_range.ground
like = probe_range.like
