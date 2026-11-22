"""L0 world handle (ADR 0029, docs/engine/sim-layers.md): what a subsystem moved out of sim.py may use of the world.

A subsystem gets the world as an argument (`world`) and touches only the names in WORLD_API on it -- object
registry, frame time, the template data handle, relations, the audit set and gap log. Rules of other subsystems are
reached through their own functions, never through the world. tests/test_sim_layers.py holds every layered module to
this list. (Today the world is the Sim itself; the list is the contract that lets L0 move out of it later without
touching the subsystems.) The minimal world for rule tests is simsmall.small_world.
"""

CIV = 'PlyrCivilian'   # the neutral side: owns the map's scenery and civilians; pays and is paid nothing
GRID = 20.0            # routing cells (world units): the ground's grid (sim.Ground) and the orders' arrival slack
DT = 0.5               # seconds a tick (simloop.DT, sim.DT)

WORLD_API = frozenset({
    'bodies',          # name -> Body, every body made (dead too), in the order made
    'living',          # () -> the bodies alive now, in bodies' order
    'world',           # the kernel World (engine/kernel/world.py): a module attached late (simbody.last_until)
    'own',             # the template data handle (simunits)
    'xml_of',          # template -> its XML (the mission's own, else retail; '' where none), kept
    'fps',             # engine frames a second
    'frame_now',       # the engine frame now
    'relations',       # (player, player) -> 'Friend' / 'Enemy' / 'Neutral'
    'used',            # the audit set: rules the run leaned on (append only)
    'gap',             # an unmodelled rule met (Sim.gap)
    'guessed',         # the audit set of guessed template data a run leaned on (append only)
    'note',            # (kind, text) -> a line in the run's log
    'label',           # body -> its name as the log shows it (its cast role, else name, else template)
    'point',           # a waypoint / area / site / mark / named object / '@x,y' -> its (x, y), None where none
    'ground',          # the pathing grid (within / route)
    'frame_movers',    # name -> Body moved frame by frame (simlocomotion.go_to registers it, the moving cell drives)
    'topples',         # the bodies a way may push over (simlocomotion.go_to reads them)
    'eng',             # the private engine model's handle, None without it
    'executor',        # the script executor (engine/ports/scripts.py): a sequential script's steps are its actions
    'change',          # () -> note that something changed now (last_change)
    't',               # the run's time now, seconds
    'kills',           # (killer's player, killer's name, template, name) by weapon, append only
    'add',             # make a body (the registry)
    'blocks',          # does a body block the ground's paths
    'reblock',         # re-read the blocked ground
    'body',            # a script's object name -> its Body (a reference followed, dead or not), None where none
    'acting',          # a sequential script's step written with <This Object>: the unit's name -> the unit, one step
                       # long (simseq._as_itself; body and point read it before the references)
    'relation',        # (player, player) -> 'ALLIES' / 'ENEMIES' / 'NEUTRAL'
    'hostile',         # (body, body) -> does the first take the second as an enemy (team overrides first)
    'who',             # player -> its name as the log shows it
    'waypoints',       # the map's waypoint name -> (x, y) (an order may add a spot of its own)
    'areas',           # the map's trigger area name -> its polygon
    'mm',              # the merged map: its waypoint labels and links (the paths)
    'enemy',           # (player a, player b) -> a takes b as an enemy
    'human',           # the human player
    'm',               # the mission (sides, assets, cast)
    'players',         # the map's side -> its player
    'shot_clock',      # the run's opt-in frame clock (a setting, read only)
    'first_death',     # (t, body, killer): the run's first death, set once (None before)
})

# Sim.gap's kinds: what a run met and the simulator does not act on (any layer reports one). The names are
# simcoverage.py's (the level line's static register; it imports sim, so they are spelled here too) plus 状态 (a status
# bit an upgrade sets; a script's bit is a 脚本动作 under its refined name, as simcoverage reports it)
GAP_WEAPON, GAP_UPGRADE, GAP_ACTION, GAP_CONDITION, GAP_COMMAND, GAP_STATUS = \
    '武器', '升级', '脚本动作', '脚本条件', '命令', '状态'


class FrameClock:
    """The world's frame clock: `frame`, the engine frame now. One object a run (Sim.clock): the engine model's engine
    where it is (its step moves it on), else this one, moved on by the public executor before each frame's scripts
    (engine/script/executor.py `clock`). Every reader of the frame reads it (Sim.frame_now, simloop.step), with the
    model or without, so the cells after the scripts one see the next frame either way."""
    __slots__ = ('frame',)

    def __init__(self, frame=0):
        self.frame = frame


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


def held(world, b):
    """b while the world still holds it under its name, else None: a thing picked earlier and kept (an attacker, a
    miner, a node) that has since left the world -- a thing made under its name took its place -- is gone, as one
    removed is (11-19 same-name sweep: kept by the thing, never looked up again by its name)."""
    return b if b is not None and world.bodies.get(b.name) is b else None


def free_key(world, make, n, taken=()):
    """The first internal key make(n), make(n + 1), ... nothing still holds: not a living thing (Sim.add refuses its
    name) nor a dead one the schedule still runs a module of (review 1119y P2 #3: a key written straight into bodies,
    as the unpack archive does, would leave that module held with its thing gone -- a snapshot fails). A dead one with
    nothing scheduled may be taken again, as Sim.add lets it. `taken`: names still to come, kept free too (the map
    load's named objects placed after this one: review 1120aa, 1119y #4's rest; a spawned / unpacked child passes
    bodies, stepping over a deleted one too: review 1120hh). Every key the simulator makes up goes
    through here (tests/guards/test_free_key.py)."""
    seq = world.world.schedule.seq
    while make(n) in taken or (b := world.bodies.get(make(n))) is not None and (
            b.alive or any(m in seq for m in getattr(b, 'modules', ()))):
        n += 1
    return make(n)


def load_keys(world, objects):
    """(object, key) for each map object in turn, as the load places them: its own name, else '#k' (k its index) or
    the next free key that is none of the names in this load (review 1120aa, 1119y #4's rest: a named one placed later
    would push it out of the world). Lazy: each key is taken against the bodies the ones before have made."""
    names = {o.name for o in objects if o.name}
    for k, o in enumerate(objects):
        yield o, o.name or free_key(world, '#{}'.format, k, names)


def free_name(world, head, tail):
    """The internal key a thing made without a name of its own goes under, f'{head} {n} {tail}': n the count of
    bodies, as ever, else the next free one (free_key; review 1119w P2 #1 / #3: bodies shrink as things are deleted,
    so the count can come round to a key still held)."""
    return free_key(world, lambda n: f'{head} {n} {tail}', len(world.bodies))


def mmss(t):
    return f'{int(t // 60)}:{int(t % 60):02d}'
