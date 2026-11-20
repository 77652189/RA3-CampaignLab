"""Battlefield (step S 11d, work/re/sim_split/snapshot.md 5; ADR 0034 6): a run's visible state as plain JSON that
another engine could read and place -- not the exact snapshot (simsnap), which goes back only onto the same run's
host. Format `battlefield/1`:

  format    'battlefield/1'
  map       the map module's short name (the mission's `map.__name__` last part, e.g. 'probe_range')
  t, frame  the source's clock at the cut: seconds and logic frames (15 a second, simunits.LIFE_FPS)
  players   {player: {money, sciences, science_points, upgrades, power: {made, used}, relations}}; relations the
            explicit directed overrides {other listed player: 'Enemy' | 'Neutral' | 'Friend'}, the map's defaults
            left out
  things    [{id, template, owner, x, y, z, angle, hp, max_hp, status, upgrades, level, contains, queue, team}]:
            id unique (a body's name); z null = on the ground (not 0); angle radians; level from 1; contains the
            ids of the things inside it, in order; queue [{template, progress}] with progress 0..1
  script    {flags: {name: bool}, counters: {name: number}, timers: {name: deadline in t's seconds},
            objectives: {name: 0 hidden / 1 shown / 2 done / 3 failed}}
  gaps      [what this file leaves out, in words]: a state not listed is not carried

Step 1 (bf_pack/plan.md) is the contract: `check(doc)` its shape alone; `preflight(sim, doc)` that and the host the
file is to be placed onto -- an empty Sim of the same map (simsmall.small_world(model=False, map=...)): the map,
the players and owners it has, the templates its data defines, no living thing of an id; `refuse(sim, doc)` a
ValueError naming every problem, before anything is placed. Each problem is 'field path: why'.

Step 2 is the export: `export(obs)` reads a run through its observation port only (engine/ports/observe.py: the
readers a game adapter can give too) into a file `check` passes -- every playable player (one with protocols), every
living thing in the order they were made, the script's four tables; keys sorted, lists in a stable order, plain JSON
values. Reading changes nothing in the world.

Step 3 places the things: `place_things(sim, doc)` refuses a file preflight does not pass, then makes each thing as the
map load does (complete, not unpacking), in the file's order (the export's: a maker before what it made), and sets its
angle, team, upgrades (a creation upgrade gives the rank, simlevel), status and health; what a placed thing makes
alongside it (a refinery's collector, a factory's drones) is the file's thing of that name when one is listed, of the
same template and owner, moved to the file's spot, and taken out when none is; then the way is blocked anew. It reads
every placed thing back through the export's own reader and returns ['field path: why', ...] for each field that
differs (an explicit height, a rank or a max health the host does not give, a status bit the host derives) and for
what later steps place (crews, factory jobs). Players and the script are not touched."""
import math

import simorder
import simunits
from simworld import CIV

FORMAT = 'battlefield/1'
TOP = ('format', 'map', 't', 'frame', 'players', 'things', 'script', 'gaps')
PLAYER = ('money', 'sciences', 'science_points', 'upgrades', 'power', 'relations')
POWER = ('made', 'used')
THING = ('id', 'template', 'owner', 'x', 'y', 'z', 'angle', 'hp', 'max_hp', 'status', 'upgrades', 'level',
         'contains', 'queue', 'team')
JOB = ('template', 'progress')
SCRIPT = ('flags', 'counters', 'timers', 'objectives')
RELATIONS = ('Enemy', 'Neutral', 'Friend')
OBJECTIVES = (0, 1, 2, 3)


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _whole(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _name(v):
    return isinstance(v, str) and v != ''


def _keys(obj, want, path, bad):
    """Whether `obj` is a dict of exactly the keys `want`; the missing and the unknown named."""
    if not isinstance(obj, dict):
        bad.append(f'{path or "the file"}: not an object ({type(obj).__name__})')
        return False
    missing = [k for k in want if k not in obj]
    extra = sorted(str(k) for k in obj if k not in want)
    if missing:
        bad.append(f'{path or "the file"}: missing {", ".join(missing)}')
    if extra:
        bad.append(f'{path or "the file"}: unknown {", ".join(extra)}')
    return not missing


def _names(v, path, bad, unique=False):
    """A list of non-empty strings (each once, if `unique`)."""
    if not isinstance(v, list):
        bad.append(f'{path}: not a list')
        return
    for i, s in enumerate(v):
        if not _name(s):
            bad.append(f'{path}[{i}]: not a name ({s!r})')
    if unique:
        seen = set()
        for s in v:
            if not isinstance(s, str):
                continue
            if s in seen:
                bad.append(f'{path}: {s!r} twice')
            seen.add(s)


def _finite(v, path, bad, low=None, high=None):
    if not _number(v):
        bad.append(f'{path}: not a finite number ({v!r})')
        return False
    if low is not None and v < low or high is not None and v > high:
        bad.append(f'{path}: {v!r} outside [{low}, {high if high is not None else "inf"}]')
        return False
    return True


def _player(name, p, listed, bad):
    path = f'players.{name}'
    if not _keys(p, PLAYER, path, bad):
        return
    _finite(p['money'], f'{path}.money', bad, 0)
    _names(p['sciences'], f'{path}.sciences', bad, unique=True)
    if not _whole(p['science_points']) or p['science_points'] < 0:
        bad.append(f'{path}.science_points: not a whole number >= 0 ({p["science_points"]!r})')
    _names(p['upgrades'], f'{path}.upgrades', bad, unique=True)
    if _keys(p['power'], POWER, f'{path}.power', bad):
        for k in POWER:
            _finite(p['power'][k], f'{path}.power.{k}', bad, 0)
    rel = p['relations']
    if not isinstance(rel, dict):
        bad.append(f'{path}.relations: not an object')
        return
    for other, value in rel.items():
        at = f'{path}.relations.{other}'
        if value not in RELATIONS:
            bad.append(f'{at}: {value!r} not one of {", ".join(RELATIONS)}')
        if other == name:
            bad.append(f'{at}: a player toward itself')
        elif other not in listed:
            bad.append(f'{at}: not a listed player')


def _thing(i, t, bad):
    path = f'things[{i}]'
    if not _keys(t, THING, path, bad):
        return
    for k in ('id', 'template', 'owner'):
        if not _name(t[k]):
            bad.append(f'{path}.{k}: not a name ({t[k]!r})')
    for k in ('x', 'y', 'angle'):
        _finite(t[k], f'{path}.{k}', bad)
    if t['z'] is not None:
        _finite(t['z'], f'{path}.z', bad)
    if _finite(t['max_hp'], f'{path}.max_hp', bad) and t['max_hp'] <= 0:
        bad.append(f'{path}.max_hp: {t["max_hp"]!r} not > 0')
    if _finite(t['hp'], f'{path}.hp', bad, 0) and _number(t['max_hp']) and t['hp'] > t['max_hp']:
        bad.append(f'{path}.hp: {t["hp"]!r} over max_hp {t["max_hp"]!r}')
    _names(t['status'], f'{path}.status', bad, unique=True)
    _names(t['upgrades'], f'{path}.upgrades', bad, unique=True)
    if not _whole(t['level']) or t['level'] < 1:
        bad.append(f'{path}.level: not a whole number >= 1 ({t["level"]!r})')
    _names(t['contains'], f'{path}.contains', bad)
    if not isinstance(t['team'], str):
        bad.append(f'{path}.team: not a string ({t["team"]!r})')
    if not isinstance(t['queue'], list):
        bad.append(f'{path}.queue: not a list')
        return
    for j, job in enumerate(t['queue']):
        at = f'{path}.queue[{j}]'
        if _keys(job, JOB, at, bad):
            if not _name(job['template']):
                bad.append(f'{at}.template: not a name ({job["template"]!r})')
            _finite(job['progress'], f'{at}.progress', bad, 0, 1)


def _crews(things, bad):
    """contains: ids listed, not itself, each passenger in one place only, no thing inside what it holds."""
    ids = {t['id'] for t in things if isinstance(t, dict) and isinstance(t.get('id'), str)}
    held_by = {}
    inside = {}
    for i, t in enumerate(things):
        if not (isinstance(t, dict) and isinstance(t.get('id'), str) and isinstance(t.get('contains'), list)):
            continue
        for j, c in enumerate(t['contains']):
            at = f'things[{i}].contains[{j}]'
            if not isinstance(c, str):
                continue
            if c == t['id']:
                bad.append(f'{at}: the thing itself')
            elif c not in ids:
                bad.append(f'{at}: {c!r} not a listed thing')
            elif c in held_by:
                bad.append(f'{at}: {c!r} already inside {held_by[c]!r}')
            else:
                held_by[c] = t['id']
                inside.setdefault(t['id'], []).append(c)
    for start in sorted(held_by):
        seen, at = {start}, start
        while at in held_by:
            at = held_by[at]
            if at in seen:
                bad.append(f'things: {start!r} is inside itself through {at!r}')
                break
            seen.add(at)


def _script(s, bad):
    if not _keys(s, SCRIPT, 'script', bad):
        return
    for k in SCRIPT:
        if not isinstance(s[k], dict):
            bad.append(f'script.{k}: not an object')
    if isinstance(s['flags'], dict):
        for k, v in s['flags'].items():
            if not isinstance(v, bool):
                bad.append(f'script.flags.{k}: not true / false ({v!r})')
    for part in ('counters', 'timers'):
        if isinstance(s[part], dict):
            for k, v in s[part].items():
                _finite(v, f'script.{part}.{k}', bad)
    if isinstance(s['counters'], dict) and isinstance(s['timers'], dict):
        for k in sorted(set(s['counters']) & set(s['timers'])):     # the executor keeps both in one table
            bad.append(f'script.timers.{k}: also a counter')
    if isinstance(s['objectives'], dict):
        for k, v in s['objectives'].items():
            if not _whole(v) or v not in OBJECTIVES:
                bad.append(f'script.objectives.{k}: {v!r} not one of 0 hidden, 1 shown, 2 done, 3 failed')


def check(doc):
    """The file's shape, whole: ['field path: why', ...], empty when it holds. Nothing about a host."""
    bad = []
    if not _keys(doc, TOP, '', bad):
        return bad
    if doc['format'] != FORMAT:
        bad.append(f'format: {doc["format"]!r}, this reads {FORMAT!r}')
    if not _name(doc['map']):
        bad.append(f'map: not a name ({doc["map"]!r})')
    _finite(doc['t'], 't', bad, 0)
    if not _whole(doc['frame']) or doc['frame'] < 0:
        bad.append(f'frame: not a whole number >= 0 ({doc["frame"]!r})')
    players = doc['players']
    if not isinstance(players, dict):
        bad.append('players: not an object')
    else:
        for name, p in players.items():
            _player(name, p, players, bad)
    things = doc['things']
    if not isinstance(things, list):
        bad.append('things: not a list')
    else:
        seen = {}
        for i, t in enumerate(things):
            _thing(i, t, bad)
            tid = t.get('id') if isinstance(t, dict) else None
            if isinstance(tid, str):
                if tid in seen:
                    bad.append(f'things[{i}].id: {tid!r} also things[{seen[tid]}]')
                else:
                    seen[tid] = i
        _crews(things, bad)
    _script(doc['script'], bad)
    _names(doc['gaps'], 'gaps', bad)
    return bad


def known(template, own=None):
    """Whether the host's data defines `template`: a mission's own unit, else what simunits.stats reads of it without
    the mission (a template no data defines reads defaults only: 'guessed' all)."""
    if (own or {}).get(template):
        return True
    return simunits.stats(template)['guessed'] != ['all']


def map_name(sim):
    """The host's map as a Battlefield file names it: the map module's short name."""
    return sim.m.map.__name__.rsplit('.', 1)[-1]


def preflight(sim, doc):
    """check(doc) and the host `sim` the file goes onto (an empty run of the same map): the map, each listed player
    and each thing's owner one the host has (its players or the neutral side), each template and queued template
    one its data defines, no id a living thing of the host holds. ['field path: why', ...], empty when it holds."""
    bad = check(doc)
    if not isinstance(doc, dict):
        return bad
    here = map_name(sim)
    if isinstance(doc.get('map'), str) and doc['map'] != here:
        bad.append(f'map: {doc["map"]!r}, the host is {here!r}')
    hosts = set(sim.players.values())
    if isinstance(doc.get('players'), dict):
        for name in doc['players']:
            if name not in hosts:
                bad.append(f'players.{name}: not a player of the host')
    own = getattr(sim, 'own', None)
    for i, t in enumerate(doc.get('things') if isinstance(doc.get('things'), list) else ()):
        if not isinstance(t, dict):
            continue
        owner = t.get('owner')
        if isinstance(owner, str) and owner and owner not in hosts and owner != CIV:
            bad.append(f'things[{i}].owner: {owner!r} not a player of the host')
        if _name(t.get('template')) and not known(t['template'], own):
            bad.append(f'things[{i}].template: {t["template"]!r} not defined in the host\'s data')
        for j, job in enumerate(t.get('queue') if isinstance(t.get('queue'), list) else ()):
            if isinstance(job, dict) and _name(job.get('template')) and not known(job['template'], own):
                bad.append(f'things[{i}].queue[{j}].template: {job["template"]!r} not defined in the host\'s data')
        tid = t.get('id')
        body = sim.bodies.get(tid) if isinstance(tid, str) else None
        if body is not None and body.alive:
            bad.append(f'things[{i}].id: {tid!r} a living thing of the host holds')
    return bad


def refuse(sim, doc):
    """A ValueError naming every problem preflight finds, before anything is placed."""
    bad = preflight(sim, doc)
    if bad:
        raise ValueError(f'simbattlefield: not placed ({len(bad)}): ' + '; '.join(bad))


# What battlefield/1 never carries (snapshot.md 5; bf_pack/census.md): the exact snapshot (simsnap) has them, a file
# placed onto another engine starts them anew.
NOT_CARRIED = (
    'shots in flight and pending hits',
    'paths, goals and orders under way',
    "modules' timers (autoheal, lifetime, sale, unpacking) and when each wakes",
    'reload, aim and fire gates',
    'special power cooldowns (a thing\'s and the player\'s)',
    'the skirmish AI\'s state (teams, build queues, plans)',
    "the script executor's history (which scripts ran, subroutines, its random state)",
    'a thing\'s experience toward its next level, and when each upgrade came',
    'what a job in a queue was paid so far',
    'harvesters\' loads and trips',
    'team instances beyond each thing\'s team name',
)


def _plain(v):
    """A JSON value of the world's own (float32 and the like read as float, tuples as lists)."""
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, int):
        return int(v)
    if isinstance(v, float) or hasattr(v, '__float__'):
        return float(v)
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in sorted(v.items())}
    raise TypeError(f'simbattlefield: {v!r} is not a JSON value')


def _own_fields(b):
    """A thing's fields of its own (all but contains and queue, which its host's parts hold)."""
    return {'id': b.name, 'template': b.template, 'owner': b.owner, 'x': b.x, 'y': b.y, 'z': b.z, 'angle': b.angle,
            'hp': b.hp, 'max_hp': b.max_hp, 'status': sorted(b.status), 'upgrades': sorted(b.upgrades),
            'level': b.level_rank, 'team': b.team or ''}


def _export_thing(obs, b):
    return dict(_own_fields(b), contains=obs.contents(b),
                queue=[{'template': t, 'progress': p} for t, p in obs.queue(b)])


def export(obs):
    """The run `obs` (an engine.ports.observe.Observe) reads, as a battlefield/1 file: every playable player, every
    living thing, the script's tables; relations the explicit directed ones that differ from the map's own (the host
    starts from those) toward a listed player -- one toward any other is named in `gaps`."""
    players = {}
    for p in sorted(set(obs.players().values())):
        tech = obs.sciences(p)
        if tech is None:
            continue
        made, used = obs.power(p)
        players[p] = {'money': obs.money().get(p, 0), 'sciences': tech[0], 'science_points': tech[1],
                      'upgrades': obs.player_upgrades(p), 'power': {'made': made, 'used': used}, 'relations': {}}
    start = getattr(obs.mission(), 'relations', None) or {}
    dropped = []
    for (a, b), r in sorted(obs.relations().items()):
        if start.get((a, b)) == r:
            continue
        if a in players and b in players and a != b:
            players[a]['relations'][b] = r
        else:
            dropped.append(f'{a} -> {b} {r}')
    things = [_export_thing(obs, b) for b in obs.things() if b.alive]     # living, in the order they were made
    script = {'flags': dict(obs.flags()), 'counters': dict(obs.counters()), 'timers': dict(obs.timers()),
              'objectives': dict(obs.objectives())}
    gaps = list(NOT_CARRIED)
    if dropped:
        gaps.append('relations toward or of a player not listed: ' + ', '.join(dropped))
    return _plain({'format': FORMAT, 'map': obs.mission().map.__name__.rsplit('.', 1)[-1], 't': obs.t,
                   'frame': obs.frame(), 'players': players, 'things': things, 'script': script, 'gaps': gaps})


LABEL = 'Battlefield'       # the script name the placing's writes go under (the script's own actions: status, delete)

# Why a placed thing's field reads other than the file's, where the host cannot give it (step 3).
WHY = {
    'z': 'an explicit height is not placed: the thing stands on the ground',
    'level': 'a rank comes from creation upgrades only (simlevel); combat experience is not carried',
    'max_hp': "the host's own of the template, its upgrades and rank, kept",
    'hp': "the file's share of the max health kept",
    'status': 'a bit the host derives (upgrades, toggles) is not taken off',
    'upgrades': 'a creation upgrade gives its rank\'s veterancy upgrades too',
}
LATER = {'contains': 'crews are not placed yet (bf_pack plan step 6)',
         'queue': 'factory jobs are not placed yet (bf_pack plan step 7)'}


def _set_thing(sim, b, row):
    """A made thing given the file's angle, upgrades, status and health (its spot, owner and team made with it)."""
    b.angle = float(row['angle'])                   # as the map load puts it (Sim.__init__)
    for up in row['upgrades']:
        if up not in b.upgrades:                    # a creation upgrade may have given the later ones already
            sim.give_upgrade(b, up)
    want = set(row['status'])
    for bit in sorted(want - b.status):             # a bit the host does not derive: held as a script's
        sim.act('UNIT_CHANGE_OBJECT_STATUS', [b.name, bit, True], LABEL)
    for bit in sorted(b.script_status - want):      # a startup bit the file has not (a wall's)
        sim.act('UNIT_CHANGE_OBJECT_STATUS', [b.name, bit, False], LABEL)
    hp =row['hp'] if b.max_hp == row['max_hp'] else row['hp'] / row['max_hp'] * b.max_hp
    b.set_hp(min(hp, b.max_hp), tell=False)         # no damage told: nothing hit it


def place_things(sim, doc):
    """The file's things onto the host `sim` (an empty run of its map; refuse first): see the module's step 3.
    ['field path: why', ...] for what is not placed as the file has it, empty when every thing reads back whole."""
    refuse(sim, doc)
    spare = {}          # name -> a thing made alongside a placed one, until the file's of that name takes it
    placed = []
    gaps = []
    for i, row in enumerate(doc['things']):
        b = spare.pop(row['id'], None)
        if b is not None and not b.alive:
            b = None
        if b is not None and (b.template, b.owner) != (row['template'], row['owner']):
            gaps.append(f'things[{i}]: the host made {row["id"]!r} alongside its maker, a {b.owner} {b.template}; '
                        f'taken out, the file\'s placed instead')
            sim.act('NAMED_DELETE', [b.name], LABEL)
            b = None
        if b is None:
            before = dict(sim.bodies)
            b = sim.add(row['id'], row['template'], row['owner'], row['x'], row['y'], at=sim.t, team=row['team'])
            spare.update((name, o) for name, o in sim.bodies.items() if o is not b and before.get(name) is not o)
        else:
            b.x, b.y = float(row['x']), float(row['y'])
            simorder.stand(b)
            b.team = row['team']
        if row['team']:
            sim.active.add(row['team'])     # a team a thing is in has an instance (its number is not carried)
        _set_thing(sim, b, row)
        placed.append((i, row, b))
    for name, b in spare.items():           # made alongside, not in the file: the source has none
        if b.alive:
            sim.act('NAMED_DELETE', [name], LABEL)
    sim.reblock()
    sim.change()
    for i, row, b in placed:
        got = _plain(_own_fields(b))
        for k in THING:
            if k in LATER and row[k]:
                gaps.append(f'things[{i}].{k}: {LATER[k]}')
            elif k not in LATER and got[k] != row[k]:
                gaps.append(f'things[{i}].{k}: {row[k]!r} in the file, the host reads {got[k]!r}'
                            + (f' -- {WHY[k]}' if k in WHY else ''))
    return gaps
