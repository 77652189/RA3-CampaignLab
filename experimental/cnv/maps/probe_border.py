"""A probe map for the engine line's border / team / countdown tests (checks/engine_scripts4.py): probe_range's flat
level ground (CampNew18's terrain levelled) with a second border, the west half. The scenes stand clear of
probe_range's lanes (y 400, 1200-1900, 3300-3750) and of the start (1250, 2500):

  line      (2500, 2700): the second border's east edge runs through it (x 2500), north-south
  stop / guard rows   y 4300 / 4600, x 600 .. 2000: open ground west of the line

Published: SITES (probe_range's, 'line', 'stop row', 'guard row'), PLAYERS, TEAMS, BORDERS ('whole', 'west half':
MAP_SWITCH_BORDER 0 / 1).
"""
from maps import probe_range
from parts import Site

LINE_X = 2500.0
SITES = dict(probe_range.SITES)
SITES['line'] = Site(LINE_X, 2700.0, 600.0, "the west half's east edge (x 2500): a scene across the border")
SITES['stop row'] = Site(1300.0, 4300.0, 700.0, 'open ground west to east (600 .. 2000): a team sent along it')
SITES['guard row'] = Site(1300.0, 4600.0, 700.0, 'open ground west to east (600 .. 2000): a team sent to guard')
PLAYERS = probe_range.PLAYERS
OBJECTS = probe_range.OBJECTS                   # its ore node
LAYOUT = probe_range._LAYOUT                    # the level ground (the simulator's ground)
TEAMS = dict(probe_range.TEAMS, s4='Soviet_4/teamSoviet_4')    # the container has it (engine_aixfer 默 reads it)
BORDERS = {'whole': (0.0, 0.0, 5000.0, 5000.0), 'west half': (0.0, 0.0, LINE_X, 5000.0)}

terrain = probe_range.terrain
like = probe_range.like
