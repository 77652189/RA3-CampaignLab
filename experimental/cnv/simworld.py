"""L0 world handle (ADR 0029, docs/engine/sim-layers.md): what a subsystem moved out of sim.py may use of the world.

A subsystem gets the world as an argument (`world`) and touches only the names in WORLD_API on it -- object
registry, frame time, the template data handle, relations, the audit set and gap log. Rules of other subsystems are
reached through their own functions, never through the world. tests/test_sim_layers.py holds every layered module to
this list. (Today the world is the Sim itself; the list is the contract that lets L0 move out of it later without
touching the subsystems.) The minimal world for rule tests is simsmall.small_world.
"""

CIV = 'PlyrCivilian'   # the neutral side: owns the map's scenery and civilians; pays and is paid nothing

WORLD_API = frozenset({
    'bodies',          # name -> Body, every body made (dead too), in the order made
    'living',          # () -> the bodies alive now, in bodies' order
    'own',             # the template data handle (simunits)
    'fps',             # engine frames a second
    'frame_now',       # the engine frame now
    'relations',       # (player, player) -> 'Friend' / 'Enemy' / 'Neutral'
    'used',            # the audit set: rules the run leaned on (append only)
    'gap',             # an unmodelled rule met (Sim.gap)
})

# Sim.gap's kinds: what a run met and the simulator does not act on (any layer reports one). The names are
# simcoverage.py's (the level line's static register; it imports sim, so they are spelled here too) plus 状态 (a status
# bit an upgrade sets; a script's bit is a 脚本动作 under its refined name, as simcoverage reports it)
GAP_WEAPON, GAP_UPGRADE, GAP_ACTION, GAP_CONDITION, GAP_COMMAND, GAP_STATUS = \
    '武器', '升级', '脚本动作', '脚本条件', '命令', '状态'


def inside(pts, x, y):
    """Point in polygon (even-odd)."""
    c, n = False, len(pts)
    for k in range(n):
        (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def same_team(have, asked):
    """A team as a script names it: 'player/team' or the bare team name (the game looks either up: work/re
    l2_scripts1.md 1); a body's team is kept as 'player/team' where the map or the script gave the player."""
    return have == asked or ('/' not in asked and have.split('/', 1)[-1] == asked)


def mmss(t):
    return f'{int(t // 60)}:{int(t % 60):02d}'
