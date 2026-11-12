"""K4 (ADR 0016 phase 4): where ore, refineries and oil go, as relations -- never as coordinates typed into a map.

Measured on the 40 retail campaign maps (work/retailref, 2026-11-04; retail_objects 'Refinery|OreNode|OilDerrick'):
  - A refinery faces its ore: the node it mines stands straight ahead of it, 180 away (138 of 171 refineries exactly
    (180, 0) in the refinery's own frame, the rest 150..240). Every retail refinery's angle is 45 + k*90, so the ore
    lies on a diagonal.
  - The node faces back: its angle is the refinery's + 180 (heidelberg, gibraltar, north sea: all six pairs). The
    miner docks at the node's front; a node turned away makes it drive round (bench round 174, engine_mining
    mineturn<k>: a trip 151 at retail's facing, 186 at 45 off, 241 at 90, 323 at 180) -- a map's income halves.
  - A pair is two nodes 120..200 apart (median 161); the second stands ~150 to the side of the first, ahead of the
    refinery the same 175. Ore is single (153 groups) or paired (75); three or more together is rare (10).
  - Oil is not part of a base: 4% of retail derricks stand within 400 of a construction yard (5th percentile 497,
    median 1687). A derrick is a prize outside the camps, the enemy's included.
  - A base mines near it: the player's nearest group is 310..970 from the start (map-language.md section 3).

A map declares FIELDS (Field: a refinery pad, which way it faces, the base it serves) and DERRICKS; this module makes
the pad sites and the ore and oil objects from them. contract.py holds the finished objects to the same relations
(ore_faces_refinery, ore_in_groups, oil_off_the_camps, base_has_ore), so a hand-placed node is caught too.
"""
import dataclasses
import math

from model import Obj, Site

AXIS = 180.0            # the node a refinery mines: straight ahead, this far (retail median; 105..240)
AXIS_SLACK = 40.0       # how far off that spot a node may stand and still be the one the refinery faces
PAIR_GAP = 150.0        # the second node of a pair: this far to the side of the first
PAIR_MAX = 300.0        # nodes of one group stand at most this far apart (retail pairs 120..437, 90% under 300)
GROUP_MAX = 2           # nodes in one group (retail: 228 of 238 groups are one or two)
OIL_CLEAR = 400.0       # a derrick stands at least this far from any base (retail 96%)
BASE_ORE = 1000.0       # a base has a group of ore within this far (map-language.md: 开局 1000 以内有一组矿)
PAD = 200.0             # the square a refinery pad keeps flat when it serves a base

DIAGONALS = (45.0, 135.0, 225.0, 315.0)       # retail's refinery angles, degrees


@dataclasses.dataclass
class Field:
    """A refinery pad and the ore it faces. (x, y): the pad; facing: degrees, a retail angle (45 + k*90); twin: +1 / -1
    a second node to that side of the first, 0 a single node. base: the site of the construction yard it serves ('' for
    a free field), owner: 'p1' / 's1' / '' of that base."""
    name: str
    x: float
    y: float
    facing: float
    twin: int = 1
    base: str = ''
    owner: str = ''
    build: float = 0.0              # > 0 (PAD): a refinery is built here, by a mission or the player: this square stays flat

    def __post_init__(self):
        if self.facing % 90.0 != 45.0:
            raise ValueError(f'field {self.name!r}: a refinery faces 45 + k*90 degrees (retail), not {self.facing:g}')
        if self.twin not in (-1, 0, 1):
            raise ValueError(f'field {self.name!r}: twin is -1, 0 or +1')


def front(f):
    """The node straight ahead of the pad."""
    a = math.radians(f.facing)
    return f.x + AXIS * math.cos(a), f.y + AXIS * math.sin(a)


def nodes(f):
    """The pad's ore: the front node, then the one beside it for a pair."""
    a = math.radians(f.facing)
    x, y = front(f)
    out = [(x, y)]
    if f.twin:
        out.append((x - f.twin * PAIR_GAP * math.sin(a), y + f.twin * PAIR_GAP * math.cos(a)))
    return [(round(px, 1), round(py, 1)) for px, py in out]


def sites(fields):
    """One site per field, `<name> refinery`: the pad, facing set (a mission places a refinery on it by that name and
    the refinery turns to face its ore, model.Mission.put)."""
    out = {}
    for f in fields:
        out[f'{f.name} refinery'] = Site(
            f.x, f.y, 0.0, f"a refinery's pad facing its ore ({AXIS:g} straight ahead, as retail)"
            + (f'; it serves {f.base}' if f.base else ''), build=f.build, facing=math.radians(f.facing))
    return out


RETAIL = 'retail'      # nodes face their refinery (angle = its facing + 180): every map's default
MEASURED = 'measured'  # nodes at angle 0, as the generator put them before round 175: the geometry the benches
                       # measured on niagara and the probe maps were read on (their readings are not taken again)


def node_angle(f, facing=RETAIL):
    """Radians: the angle of the pad's nodes -- facing back at the refinery (RETAIL), or 0 (MEASURED)."""
    if facing == MEASURED:
        return 0.0
    if facing != RETAIL:
        raise ValueError(f'node facing is {RETAIL!r} or {MEASURED!r}, not {facing!r}')
    return math.radians((f.facing + 180.0) % 360.0)


def objects(fields, derricks=(), node_facing=RETAIL):
    """The map's ore and oil: the fields' nodes (facing their refinery; node_facing=MEASURED: at 0, a bench map's
    old geometry), the derricks (x, y) as given."""
    out = [Obj('OreNode', x, y, side='neutral', angle=node_angle(f, node_facing), site='map')
           for f in fields for x, y in nodes(f)]
    out += [Obj('OilDerrick', x, y, side='neutral', angle=0.0, site='map') for x, y in derricks]
    return out


_MEASURED = {}


def measured(mod):
    """`mod` (a map module) with its ore nodes at angle 0 and NODES = MEASURED: the geometry a bench was measured on
    before the generator turned nodes to face their refinery (round 175). A bench mission whose readings depend on it
    takes its map through here; everything else (the campaign, new benches) gets retail's facing. One copy per map,
    the module's name kept (builds name files by the mission, model asserts name the map by it)."""
    import dataclasses
    import types
    if getattr(mod, 'NODES', RETAIL) == MEASURED:
        return mod
    if id(mod) not in _MEASURED:
        cp = types.ModuleType(mod.__name__)
        cp.__dict__.update({k: v for k, v in vars(mod).items() if not k.startswith('__')})
        cp.OBJECTS = [dataclasses.replace(o, angle=0.0) if o.template == 'OreNode' else o for o in mod.OBJECTS]
        cp.NODES = MEASURED
        _MEASURED[id(mod)] = (mod, cp)
    return _MEASURED[id(mod)][1]


def bases(fields):
    """{base site name: owner} of the bases the fields serve."""
    return {f.base: f.owner for f in fields if f.base}
