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
ValueError naming every problem, before anything is placed. Each problem is 'field path: why'."""
import math

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
