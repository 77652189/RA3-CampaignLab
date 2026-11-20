"""Battlefield (step S 11d, work/re/sim_split/snapshot.md 5; ADR 0034 6): a run's visible state as plain JSON that
another engine could read and place -- not the exact snapshot (simsnap), which goes back only onto the same run's
host. Format `battlefield/1`:

  format    'battlefield/1'
  map       the map module's short name (the mission's `map.__name__` last part, e.g. 'probe_range')
  t, frame  the source's clock at the cut: seconds and logic frames (15 a second, simunits.LIFE_FPS)
  players   {player: {money, sciences, science_points, upgrades, power: {made, used}, relations}}; relations the
            explicit directed overrides {other listed player: 'Enemy' | 'Neutral' | 'Friend'}, the map's defaults
            left out
  things    [{id, template, owner, x, y, z, angle, hp, max_hp, status, upgrades, level, contains, home, queue,
            clocks, team}]: id unique (a body's name); z null = on the ground (not 0); angle radians; level from 1; contains
            the ids of the things inside it, in order; home null or the owner a garrisoned building goes back to
            when its last passenger is out (the one it had before its first: a building holding passengers only,
            not a transport, which keeps its owner); queue its jobs in the queue's order [{template, progress, paid,
            full}]: progress 0..1, paid the money paid for it so far (a whole number), full null or the logic frame
            (the file's `frame` clock, not after it; before 0 too -- a job full at the cut, placed onto a run at
            frame 0, filled before it) it filled -- progress 1 then, waiting to come out; clocks its timed modules
            in the order made [{module: XML tag, its fields (CLOCKS)}], each field a logic frame on the file's clock
            or null (autoheal's hurt a bool): AutoHealBehavior mend (its next mend), ok (its last mend's delay out),
            hurt (a hurt since its last run); LifetimeUpdate dies; StructureSellUpdate gone (sold: deleted then);
            StructureUnpackUpdate unpacked (unpacking until then); missing in a file from before step 10 (NO_CLOCKS)
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
differs (an explicit height, a rank or a max health the host does not give, a status bit the host derives). Players and the script are not touched.

Step 4 places the players: `place_players(sim, doc)` refuses a file whose players the host cannot take (preflight
with things=False: the map, each listed player one with a protocol book, each protocol one the host's data defines),
then gives each listed player the file's money (PLAYER_SET_MONEY), protocols and points as they are -- held, nothing
paid, the rank the generic rank protocols say (simtech.Book.place) -- the player upgrades the host does not hold yet
(GIVE_PLAYER_UPGRADE) and the directed relations (PLAYER_RELATES_PLAYER); it reads each player back as the export
does, power recomputed from the host's living things, and returns ['players.<p>.<field>: why', ...] for what differs.
`place(sim, doc)` is steps 3 and 4 in the order a run has them: the players' upgrades first (a thing made after one
is made with it, as the source's was), then the things, then the players read back (their power is the things').

Step 5 places the script's state: `place_script(sim, doc)` makes the host's four tables the file's -- each flag, each
counter (a stopped timer is one: its frames left kept, as STOP_TIMER keeps them), each objective's status and each
running timer -- written into the tables themselves, not through the script's actions: placing runs no script, notes
nothing on the timeline and decides no ending (a won or lost flag is placed and named). A timer's deadline is in the
file's seconds (`t` its clock): the host holds the frames left from the cut, round((deadline - t) x the host's frame
rate), so it runs out as many frames after the placing as the source's did after the cut, whatever the host's own clock
reads; one out before the cut is held as just out (-1, as the executor keeps it). Preflight refuses a deadline whose
frames left are no whole number on the host (a finite deadline so far from the cut that x the frame rate it is infinite:
script.timers.<name> named), and the four tables are all worked out before any is written (a placing stopped part way
leaves the host's as they were). It reads the tables back on the
file's clock (a running timer's deadline = t + frames left / frame rate, as the export reads it at the cut) and returns
['script.<table>.<name>: why', ...] for what differs. `place` does it last.

Step 6 places the crews, within place_things: once every thing is made (the passengers and what holds them both), each
thing's `contains` goes into it in the file's order as the script's instant garrison puts them (simgarrison.Garrisons.
put, script: no relation asked, no room -- the source's script may have put six into a five-place house), so what
being inside gives is the host's own: the passenger at its holder's spot carrying the bits the holder gives it (and
none of them held as a script's: they go when it comes out), a garrisoned building owned by its first passenger, a
single passenger's listener upgrades granted to the building (to be taken back when it leaves). Only then are angles,
upgrades, status and health set (a building given a listener's upgrade before its passenger would keep it after).
Preflight refuses a file whose holder's template has no garrison or transport in the host's data, and a home on one
with no garrison; a passenger the host's rules keep out (its PassengerFilter) is named by the read back, standing
where the file has it. A garrisoned building's home is set once its passengers are in (the put keeps the file's
owner, the first passenger's, as the one before): emptied, it goes back to the file's home, as the source's did; a
file's null home on a building holding passengers is named by the read back (the host's goes back to the owner the
file gives it).

Step 7 places the factories' jobs, within place_things after the things are set (a factory's upgrades give its menu):
each job goes into its thing's queue in the file's order as the host's own order would have put it (Sim.order_build:
a unit its menu builds, an upgrade its buttons buy), with the file's progress (per cent, float32, as the host keeps
it) and what was paid (no money moves now: the host's production pays the rest frame by frame, as the source's would
have), so a half-built scout goes on from half, paying only what is left (never refunded; a full one paid short
pays its rest before it comes out); a full job waits to come out as many
frames after its filling as on the source (full in the host's frames = full - the file's frame + the host's). A job
the host's factory does not build (a construction yard's structures: the host has no such queue; a unit its menu
lacks) is not placed and named by its field path, the jobs behind it placed; what was paid over the host's cost is
named too. What the file does not carry: a build ban a script set (the export names each job the source held for one:
placed, it goes on) and a player's hold on a job (the host models none).

Step 9 carries the skirmish AI's yards: a yard builds its structures in the AI's own queue (simai Brain.yard_q: the
simulator's yards have none), so with the run's AI (`export(obs, ai)`: simai.SimAI.yard_jobs) a yard's queue lists
them after its own jobs, its structures' then its defences', each a row as any job; placed with the host's AI
(`place(sim, doc, ai)`: SimAI.put_yard_jobs, the brains made as its next tick would), each goes into the AI's queue at
the file's progress and paid, and its production pays the rest (a refinery half built goes on from half). With no AI
on the host, or none running the yard's owner, the structure is not placed and named by its path. The rest of the
AI's state is not carried (NOT_CARRIED): a placed AI starts its plans anew.

Step 10 carries the modules' timers, within place_things last: each thing's clocks go into its timed modules
(engine.kernel.interfaces.Clocked) -- the k-th row of a tag into its k-th module of that tag -- moved onto the host's
clock (a frame + the host's frame - the file's), each module woken as its own setter wakes it: a hurt Apocalypse
mends as many frames after the cut as on the source, a lifetime ends, a sold plant goes, an unpacking one gives power
at the same frame. A lifetime the host's thing lacks (one the source attached late: simbody.last_until) is attached;
another tag it lacks is named by the read back. Set after the health (the host's set_hp tells its autoheal of a hurt)
and the upgrades (one granting an autoheal sets its first mend).

Step 8 is the round trip: `round_trip(host, doc)` places an export onto an empty run of its map, exports the host and
reads that on the file's clock (`rebase`: the cut, a running timer's deadline and a full job's frame moved by the
clocks' difference), then compares field by field -- a thing by its id, named by its place in the file (one only on
the host by "things: 'id'"), a player's field (power by part), a script table's entry, the things' order, the
NOT_CARRIED gaps (a host holds no ban: its own gaps are its own) -- and gives each differing field path with the
placing's gap that names it (the same field, one it is in, or a part of it), None where none does. It holds when no
path has None."""
import math
import struct

import engine.objects.body as simbody
import engine.objects.garrison as simgarrison
import engine.orders.order as simorder
import engine.players.tech as simtech
import engine.data.units as simunits
from engine.script.common import LOST, WON
from engine.world.handle import CIV
from engine.kernel import interfaces
from engine.ports.observe import Observe

FORMAT = 'battlefield/1'
TOP = ('format', 'map', 't', 'frame', 'players', 'things', 'script', 'gaps')
PLAYER = ('money', 'sciences', 'science_points', 'upgrades', 'power', 'relations')
POWER = ('made', 'used')
THING = ('id', 'template', 'owner', 'x', 'y', 'z', 'angle', 'hp', 'max_hp', 'status', 'upgrades', 'level',
         'contains', 'home', 'queue', 'clocks', 'team')
JOB = ('template', 'progress', 'paid', 'full')
CLOCKS = {'AutoHealBehavior': ('mend', 'ok', 'hurt'), 'LifetimeUpdate': ('dies',), 'StructureSellUpdate': ('gone',),
          'StructureUnpackUpdate': ('unpacked',)}       # a timed module's fields (step 10): frames but hurt
FLAGS = ('hurt',)
NO_CLOCKS = 'not in the file (written before step 10): its timed modules run as the host made them'
_FRAMES = {f for fields in CLOCKS.values() for f in fields if f not in FLAGS}
SCRIPT = ('flags', 'counters', 'timers', 'objectives')
RELATIONS = ('Enemy', 'Neutral', 'Friend')
OBJECTIVES = (0, 1, 2, 3)


def _number(v):
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return False
    try:
        return math.isfinite(v)
    except OverflowError:       # a whole number too large for a float (10**309)
        return False


def _whole(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _name(v):
    return isinstance(v, str) and v != ''


def _keys(obj, want, path, bad, optional=()):
    """Whether `obj` is a dict, the keys of `want` it misses (but `optional`'s) and the unknown ones named; the caller
    checks each field it has (one missing or broken field hides no other)."""
    if not isinstance(obj, dict):
        bad.append(f'{path or "the file"}: not an object ({type(obj).__name__})')
        return False
    missing = [k for k in want if k not in obj and k not in optional]
    extra = sorted(str(k) for k in obj if k not in want)
    if missing:
        bad.append(f'{path or "the file"}: missing {", ".join(missing)}')
    if extra:
        bad.append(f'{path or "the file"}: unknown {", ".join(extra)}')
    return True


def _table(v, path, bad):
    """A dict whose keys are names (a script's table, a player's relations): its bad keys named; whether a dict."""
    if not isinstance(v, dict):
        bad.append(f'{path}: not an object')
        return False
    for k in v:
        if not _name(k):
            bad.append(f'{path}: a key not a name ({k!r})')
    return True


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
    if not _name(name):
        bad.append(f'players: a key not a name ({name!r})')
    if not _keys(p, PLAYER, path, bad):
        return
    if 'money' in p:
        _finite(p['money'], f'{path}.money', bad, 0)
    if 'sciences' in p:
        _names(p['sciences'], f'{path}.sciences', bad, unique=True)
    if 'science_points' in p and (not _whole(p['science_points']) or p['science_points'] < 0):
        bad.append(f'{path}.science_points: not a whole number >= 0 ({p["science_points"]!r})')
    if 'upgrades' in p:
        _names(p['upgrades'], f'{path}.upgrades', bad, unique=True)
    if 'power' in p and _keys(p['power'], POWER, f'{path}.power', bad):
        for k in POWER:
            if k in p['power']:
                _finite(p['power'][k], f'{path}.power.{k}', bad, 0)
    rel = p.get('relations')
    if 'relations' not in p or not _table(rel, f'{path}.relations', bad):
        return
    for other, value in rel.items():
        at = f'{path}.relations.{other}'
        if value not in RELATIONS:
            bad.append(f'{at}: {value!r} not one of {", ".join(RELATIONS)}')
        if other == name:
            bad.append(f'{at}: a player toward itself')
        elif other not in listed:
            bad.append(f'{at}: not a listed player')


def _thing(i, t, bad, frame=None):
    """One thing's shape; `frame` the file's (a full job's frame is not after it), None when it is broken."""
    path = f'things[{i}]'
    if not _keys(t, THING, path, bad, optional=('clocks',)):  # a file from before step 10 has no clocks
        return
    for k in ('id', 'template', 'owner'):
        if k in t and not _name(t[k]):
            bad.append(f'{path}.{k}: not a name ({t[k]!r})')
    for k in ('x', 'y', 'angle'):
        if k in t:
            _finite(t[k], f'{path}.{k}', bad)
    if t.get('z') is not None:
        _finite(t['z'], f'{path}.z', bad)
    if 'max_hp' in t and _finite(t['max_hp'], f'{path}.max_hp', bad) and t['max_hp'] <= 0:
        bad.append(f'{path}.max_hp: {t["max_hp"]!r} not > 0')
    if 'hp' in t and _finite(t['hp'], f'{path}.hp', bad, 0) and _number(t.get('max_hp')) and t['hp'] > t['max_hp']:
        bad.append(f'{path}.hp: {t["hp"]!r} over max_hp {t["max_hp"]!r}')
    for k in ('status', 'upgrades'):
        if k in t:
            _names(t[k], f'{path}.{k}', bad, unique=True)
    if 'level' in t and (not _whole(t['level']) or t['level'] < 1):
        bad.append(f'{path}.level: not a whole number >= 1 ({t["level"]!r})')
    if 'contains' in t:
        _names(t['contains'], f'{path}.contains', bad)
    if t.get('home') is not None and not _name(t['home']):
        bad.append(f'{path}.home: not null or a name ({t["home"]!r})')
    elif t.get('home') is not None and isinstance(t.get('contains'), list) and not t['contains']:
        bad.append(f'{path}.home: {t["home"]!r} with no passengers (a home is where an emptied building goes back)')
    if 'team' in t and not isinstance(t['team'], str):
        bad.append(f'{path}.team: not a string ({t["team"]!r})')
    _clocks(path, t, bad)
    if 'queue' not in t:
        return
    if not isinstance(t['queue'], list):
        bad.append(f'{path}.queue: not a list')
        return
    for j, job in enumerate(t['queue']):
        at = f'{path}.queue[{j}]'
        if not _keys(job, JOB, at, bad):
            continue
        if 'template' in job and not _name(job['template']):
            bad.append(f'{at}.template: not a name ({job["template"]!r})')
        progress = 'progress' in job and _finite(job['progress'], f'{at}.progress', bad, 0, 1)
        if 'paid' in job and (not _whole(job['paid']) or job['paid'] < 0):
            bad.append(f'{at}.paid: not a whole number >= 0 ({job["paid"]!r})')
        if 'full' not in job:
            continue
        full = job['full']
        if full is not None and not _whole(full):
            bad.append(f'{at}.full: not null or a whole number ({full!r})')
        elif full is not None and frame is not None and full > frame:
            bad.append(f'{at}.full: {full!r} after the file\'s frame {frame!r}')
        elif progress and (full is not None) != (job['progress'] == 1):
            bad.append(f'{at}.full: {full!r} with progress {job["progress"]!r} (a job is full at progress 1, '
                       f'and names the frame it filled)')


def _clocks(path, t, bad):
    """A thing's clocks: a list of rows, each a known tag's fields (CLOCKS) -- a frame null or a whole number, a flag a
    bool."""
    if 'clocks' not in t:
        return
    if not isinstance(t['clocks'], list):
        bad.append(f'{path}.clocks: not a list')
        return
    for k, row in enumerate(t['clocks']):
        at = f'{path}.clocks[{k}]'
        tag = row.get('module') if isinstance(row, dict) else None
        if not isinstance(tag, str) or tag not in CLOCKS:
            bad.append(f'{at}.module: not one of {sorted(CLOCKS)} ({tag!r})')
            continue
        if not _keys(row, ('module',) + CLOCKS[tag], at, bad):
            continue
        for f in (f for f in CLOCKS[tag] if f in row):
            v = row[f]
            if f in FLAGS and not isinstance(v, bool):
                bad.append(f'{at}.{f}: not a bool ({v!r})')
            elif f not in FLAGS and v is not None and not _whole(v):
                bad.append(f'{at}.{f}: not null or a whole number ({v!r})')


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
    ok = {k: k in s and _table(s[k], f'script.{k}', bad) for k in SCRIPT}
    if ok['flags']:
        for k, v in s['flags'].items():
            if not isinstance(v, bool):
                bad.append(f'script.flags.{k}: not true / false ({v!r})')
    for part in ('counters', 'timers'):
        if ok[part]:
            for k, v in s[part].items():
                _finite(v, f'script.{part}.{k}', bad)
    if ok['counters'] and ok['timers']:
        for k in sorted(set(s['counters']) & set(s['timers']), key=str):     # the executor keeps both in one table
            bad.append(f'script.timers.{k}: also a counter')
    if ok['objectives']:
        for k, v in s['objectives'].items():
            if not _whole(v) or v not in OBJECTIVES:
                bad.append(f'script.objectives.{k}: {v!r} not one of 0 hidden, 1 shown, 2 done, 3 failed')


def check(doc):
    """The file's shape, whole: ['field path: why', ...], empty when it holds. Nothing about a host."""
    bad = []
    if not _keys(doc, TOP, '', bad):
        return bad
    if 'format' in doc and doc['format'] != FORMAT:
        bad.append(f'format: {doc["format"]!r}, this reads {FORMAT!r}')
    if 'map' in doc and not _name(doc['map']):
        bad.append(f'map: not a name ({doc["map"]!r})')
    if 't' in doc:
        _finite(doc['t'], 't', bad, 0)
    if 'frame' in doc and (not _whole(doc['frame']) or doc['frame'] < 0):
        bad.append(f'frame: not a whole number >= 0 ({doc["frame"]!r})')
    players = doc.get('players')
    if 'players' not in doc:
        pass
    elif not isinstance(players, dict):
        bad.append('players: not an object')
    else:
        for name, p in players.items():
            _player(name, p, players, bad)
    things = doc.get('things')
    if 'things' not in doc:
        pass
    elif not isinstance(things, list):
        bad.append('things: not a list')
    else:
        seen = {}
        frame = doc['frame'] if _whole(doc.get('frame')) else None
        for i, t in enumerate(things):
            _thing(i, t, bad, frame)
            tid = t.get('id') if isinstance(t, dict) else None
            if isinstance(tid, str):
                if tid in seen:
                    bad.append(f'things[{i}].id: {tid!r} also things[{seen[tid]}]')
                else:
                    seen[tid] = i
        _crews(things, bad)
    if 'script' in doc:
        _script(doc['script'], bad)
    if 'gaps' in doc:
        _names(doc['gaps'], 'gaps', bad)
        if doc['gaps'] == []:
            bad.append('gaps: empty (a file names what it leaves out)')
    return bad


def known(template, own=None):
    """Whether the host's data defines `template`: a mission's own unit, else what simunits.stats reads of it without
    the mission (a template no data defines reads defaults only: 'guessed' all)."""
    if (own or {}).get(template):
        return True
    return simunits.stats(template)['guessed'] != ['all']


def upgrade(name, own=None):
    """Whether `name` is an upgrade the host's data defines (a mission's declaration, else retail upgrade.xml)."""
    return simunits.upgrade_type(name, own) != ''


def holds(template, own=None):
    """Whether the host's data gives `template` a garrison or a transport hold (a GarrisonContain,
    ContestableGarrisonContain or TransportContain block)."""
    return any(simunits.module_blocks(template, tag, own) for tag in simgarrison.TAGS + simgarrison.TRANSPORT)


def garrisons(template, own=None):
    """Whether the host's data gives `template` a garrison (GarrisonContain / ContestableGarrisonContain): a building
    that is its first passenger's and goes back when emptied."""
    return any(simunits.module_blocks(template, tag, own) for tag in simgarrison.TAGS)


def map_name(sim):
    """The host's map as a Battlefield file names it: the map module's short name."""
    return sim.m.map.__name__.rsplit('.', 1)[-1]


def preflight(sim, doc, things=True):
    """check(doc) and the host `sim` the file goes onto (an empty run of the same map): the map, each listed player
    one the host has with a protocol book (a playable one) and each protocol it holds one the host's data defines;
    with `things`, each thing's owner one the host has (its players or the neutral side), each template and queued
    template one its data defines, no id a living thing of the host holds. ['field path: why', ...], empty when it
    holds."""
    bad = check(doc)
    if not isinstance(doc, dict):
        return bad
    here = map_name(sim)
    if isinstance(doc.get('map'), str) and doc['map'] != here:
        bad.append(f'map: {doc["map"]!r}, the host is {here!r}')
    hosts = set(sim.players.values())
    if isinstance(doc.get('players'), dict):
        for name, p in doc['players'].items():
            if name not in hosts:
                bad.append(f'players.{name}: not a player of the host')
            elif name not in sim.books:
                bad.append(f'players.{name}: the host keeps no protocols for it (not a playable player)')
            sciences = p.get('sciences') if isinstance(p, dict) else None
            for i, s in enumerate(sciences if isinstance(sciences, list) else ()):
                if _name(s) and s.lower() not in simtech.protocols():
                    bad.append(f'players.{name}.sciences[{i}]: {s!r} not a protocol of the host\'s data')
            rel = p.get('relations') if isinstance(p, dict) else None
            for other, r in (rel.items() if isinstance(rel, dict) else ()):
                if _start(sim.m).get((name, other)) == r:
                    bad.append(f'players.{name}.relations.{other}: {r!r} the map\'s own (a file lists what differs)')
    script = doc.get('script')
    timers = script.get('timers') if isinstance(script, dict) else None
    for k, d in (timers.items() if isinstance(timers, dict) and _number(doc.get('t')) else ()):
        if _number(d) and not math.isfinite((d - doc['t']) * sim.fps):
            bad.append(f'script.timers.{k}: {d!r} is {d - doc["t"]!r} s from the cut, no whole number of the '
                       f'host\'s frames')
    if not things:
        return bad
    own = getattr(sim, 'own', None)
    for i, t in enumerate(doc.get('things') if isinstance(doc.get('things'), list) else ()):
        if not isinstance(t, dict):
            continue
        owner = t.get('owner')
        for k in ('owner', 'home'):
            who = t.get(k)
            if isinstance(who, str) and who and who not in hosts and who != CIV:
                bad.append(f'things[{i}].{k}: {who!r} not a player of the host')
        if _name(t.get('template')) and _name(t.get('home')) and known(t['template'], own) and not garrisons(
                t['template'], own):
            bad.append(f'things[{i}].home: a {t["template"]} has no garrison in the host\'s data (a transport keeps '
                       f'its owner)')
        if _name(t.get('template')) and not known(t['template'], own):
            bad.append(f'things[{i}].template: {t["template"]!r} not defined in the host\'s data')
        elif _name(t.get('template')) and t.get('contains') and not holds(t['template'], own):
            bad.append(f'things[{i}].contains: a {t["template"]} holds nothing in the host\'s data (no garrison or '
                       f'transport)')
        for j, job in enumerate(t.get('queue') if isinstance(t.get('queue'), list) else ()):
            if isinstance(job, dict) and _name(job.get('template')) and not (
                    known(job['template'], own) or upgrade(job['template'], own)):
                bad.append(f'things[{i}].queue[{j}].template: {job["template"]!r} not defined in the host\'s data')
        tid = t.get('id')
        body = sim.bodies.get(tid) if isinstance(tid, str) else None
        if body is not None and body.alive:
            bad.append(f'things[{i}].id: {tid!r} a living thing of the host holds')
    return bad


def refuse(sim, doc, things=True):
    """A ValueError naming every problem preflight finds, before anything is placed."""
    bad = preflight(sim, doc, things)
    if bad:
        raise ValueError(f'simbattlefield: not placed ({len(bad)}): ' + '; '.join(bad))


# What battlefield/1 never carries (snapshot.md 5; bf_pack/census.md): the exact snapshot (simsnap) has them, a file
# placed onto another engine starts them anew.
NOT_CARRIED = (
    'shots in flight and pending hits',
    'paths, goals and orders under way',
    "modules' timers but autoheal's, lifetime's, a sale's and unpacking's (a deposit's next payment, a toggle's "
    "waiting press, a spy's blocked port, an aura's beat, suppression, toppling, a repair under way)",
    'reload, aim and fire gates',
    'special power cooldowns (a thing\'s and the player\'s)',
    "the skirmish AI's state but its yards' queues (which players it runs, its teams and plans, the units it waits "
    "to order, a yard's rest the frame after it set one down, a pause): a yard's structures go to the host's AI of "
    "its owner",
    "the script executor's history (which scripts ran, subroutines, its random state, when an interval script is due)",
    'which counters the screen shows (DISPLAY_COUNTER) and which things an objective marks',
    "a run's ending (a won or lost flag is placed, the host does not end on it)",
    'a thing\'s experience toward its next level, and when each upgrade came',
    "a player's experience toward its next rank (a placed player starts its rank anew)",
    "a player's protocol locks and point cap, and a power its scripts added (they set them)",
    'build bans a script set (ALLOW_DISALLOW_ONE_BUILDING, unit construction disabled): a job the source held '
    'for one goes on where placed (each such job named)',
    "a player's hold on a job (the host models none)",
    'harvesters\' loads and trips',
    'passengers on their way in, being ejected or in the air after it',
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


def _job_rows(jobs, shift=0):
    """Observe.jobs as a file's queue, a full job's frame moved by `shift` (the host's frame onto the file's)."""
    return [{'template': t, 'progress': p, 'paid': paid, 'full': None if full is None else full + shift}
            for t, p, paid, full, _ in jobs]


def _jobs(obs, ai, b):
    """Thing b's jobs as Observe.jobs gives them, then (with the run's skirmish AI `ai`) the structures the AI has
    queued at it, a yard (simai.SimAI.yard_jobs: never held -- the AI's own queue holds for no ban)."""
    own = list(obs.jobs(b))
    return own + [(t, p, paid, full, False) for t, p, paid, full in ai.yard_jobs(b)] if ai is not None else own


def _clock_rows(obs, b, shift=0):
    """Observe.clocks as a file's clocks, each frame moved by `shift` (the host's frame onto the file's)."""
    return [dict({f: v + shift if f in _FRAMES and v is not None else v for f, v in values.items()}, module=tag)
            for tag, values in obs.clocks(b)]


def _export_thing(obs, b, ai=None):
    return dict(_own_fields(b), contains=obs.contents(b), home=obs.home(b), queue=_job_rows(_jobs(obs, ai, b)),
                clocks=_clock_rows(obs, b))


def _held(obs, things):
    """['things[i].queue[j]: ...'] for each job the source holds for a ban (the file does not carry the ban)."""
    out = []
    for i, b in enumerate(things):
        for j, (t, _, _, _, held) in enumerate(obs.jobs(b)):
            if held:
                out.append(f'things[{i}].queue[{j}]: {t} held by a build ban the file does not carry (placed, it '
                           f'goes on)')
    return out


def _player_row(money, tech, upgrades, power):
    """A player's fields but its relations: money, (protocols, points), player upgrades, (made, used)."""
    return {'money': money, 'sciences': tech[0], 'science_points': tech[1], 'upgrades': upgrades,
            'power': {'made': power[0], 'used': power[1]}, 'relations': {}}


def _start(mission):
    """The map's own directed relations (a host starts from these)."""
    return getattr(mission, 'relations', None) or {}


def _relations(players, pairs, start):
    """The explicit directed relations `pairs` that differ from the map's own, into each listed player's row; the
    ones toward or of a player not listed as ['a -> b r', ...]."""
    dropped = []
    for (a, b), r in sorted(pairs.items()):
        if start.get((a, b)) == r:
            continue
        if a in players and b in players and a != b:
            players[a]['relations'][b] = r
        else:
            dropped.append(f'{a} -> {b} {r}')
    return dropped


def export(obs, ai=None):
    """The run `obs` (an engine.ports.observe.Observe) reads, as a battlefield/1 file: every playable player, every
    living thing, the script's tables; relations the explicit directed ones that differ from the map's own (the host
    starts from those) toward a listed player -- one toward any other is named in `gaps`. `ai`: the run's skirmish AI
    (simai.SimAI), whose yards' queues go into each yard's (step 9); without it a yard's structures are not read."""
    players = {}
    for p in sorted(set(obs.players().values())):
        tech = obs.sciences(p)
        if tech is not None:
            players[p] = _player_row(obs.money().get(p, 0), tech, obs.player_upgrades(p), obs.power(p))
    dropped = _relations(players, obs.relations(), _start(obs.mission()))
    living = [b for b in obs.things() if b.alive]                       # in the order they were made
    things = [_export_thing(obs, b, ai) for b in living]
    script = {'flags': {k: bool(v) for k, v in obs.flags().items()}, 'counters': dict(obs.counters()), 'timers': dict(obs.timers()),
              'objectives': dict(obs.objectives())}
    gaps = list(NOT_CARRIED) + _held(obs, living)
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
    'contains': "a passenger the host's rules keep out (its PassengerFilter) stands where the file has it",
    'owner': "a garrisoned building is its first passenger's",
    'home': "a garrisoned building holding passengers goes back to the owner before its first (the file's null: the "
            "owner the file gives it); one the host's filter emptied has none",
    'queue': "a job the host's factory does not build (or no AI of the host takes) is not placed; paid is held to the "
             "host's cost; progress is the host's per cent (float32), a job not full kept below 100; a yard's "
             "structures read after its own jobs, its structures' before its defences'",
    'clocks': "a timed module the host's thing lacks (its template's data has none) keeps no clock; one the file "
              "does not list keeps the host's own",
}


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


def place_things(sim, doc, ai=None):
    """The file's things onto the host `sim` (an empty run of its map; refuse first): see the module's step 3.
    ['field path: why', ...] for what is not placed as the file has it, empty when every thing reads back whole.
    `ai`: the host's skirmish AI (simai.SimAI on `sim`), which takes a yard's structures (step 9)."""
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
            _unmake(sim, b)
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
        placed.append((i, row, b))
    for b in spare.values():                # made alongside, not in the file: the source has none
        if b.alive:
            _unmake(sim, b)
    _put_crews(sim, placed)
    for _, row, b in placed:                # after the crews: what a passenger gives its holder is the host's
        _set_thing(sim, b, row)
    shift = sim.frame_now() - doc['frame']  # a file's frame onto the host's
    for i, row, b in placed:                # after the upgrades: a factory's menu may come with one
        gaps += _set_jobs(sim, i, row, b, shift, ai)
    for _, row, b in placed:                # after health and upgrades: they set an autoheal's own (step 10)
        if 'clocks' in row:
            _set_clocks(sim, row, b, shift)
    sim.reblock()
    sim.change()
    obs = Observe(sim)
    for i, row, b in placed:
        got = _plain(dict(_own_fields(b), contains=[p.name for p in sim.garrison.held(b)], home=obs.home(b),
                          queue=_job_rows(_jobs(obs, ai, b), -shift), clocks=_clock_rows(obs, b, -shift)))
        for k in THING:
            if k not in row:                # clocks, in a file from before step 10
                gaps.append(f'things[{i}].{k}: {NO_CLOCKS}')
            elif got[k] != row[k]:
                gaps.append(f'things[{i}].{k}: {row[k]!r} in the file, the host reads {got[k]!r}'
                            + (f' -- {WHY[k]}' if k in WHY else ''))
    mine = {b.serial for _, _, b in placed}
    for b in obs.things():                  # the host's living things are the file's, none besides (read as export does)
        if b.alive and b.serial not in mine:
            gaps.append(f'things: {b.name!r} (a {b.owner} {b.template}) living on the host, not in the file')
    return gaps


def _set_clocks(sim, row, b, shift):
    """The file's clocks into b's timed modules, the k-th row of a tag into its k-th module of that tag, each frame
    moved by `shift`; a lifetime it lacks attached (simbody.last_until), a row of another tag it lacks left (the read
    back names it)."""
    mods = {}
    for m in b.find(interfaces.Clocked) if b.modules else ():
        mods.setdefault(type(m).TAGS[0], []).append(m)
    seen = {}
    for clock in row['clocks']:
        tag = clock['module']
        k = seen[tag] = seen.get(tag, -1) + 1
        values = {f: clock[f] + shift if f in _FRAMES and clock[f] is not None else clock[f] for f in CLOCKS[tag]}
        have = mods.get(tag, ())
        if k < len(have):
            have[k].set_clocks(values)
        elif tag == 'LifetimeUpdate' and k == 0 and values['dies'] is not None:
            simbody.last_until(sim, b, values['dies'])


def _f32(x):
    """x as a single float (the host keeps a job's progress so: sim.f32)."""
    return struct.unpack('f', struct.pack('f', x))[0]


# The float32 just below 100 per cent: a job the file has not full, whose progress rounds to 100 (0.999999999).
BELOW_100 = struct.unpack('f', struct.pack('I', struct.unpack('I', struct.pack('f', 100.0))[0] - 1))[0]


def _set_jobs(sim, i, row, b, shift, ai=None):
    """The file's jobs of thing i into its queue as Sim.order_build would have queued them, at the file's progress and
    paid (no money moves now), a full one at its frame on the host's clock -- a structure at a yard into the host's
    skirmish AI's queue of it (`ai`, step 9); ['things[i].queue[j]: ...'] for a job the host's factory does not build
    or no AI of the host takes (not placed) and one paid over the host's cost."""
    sim.queues.pop(b.serial, None)
    if not row['queue']:
        return []
    gaps, jobs, yard = [], [], []
    ups = dict(simunits.upgrade_menu(b.template, sim.own, b.upgrades))
    units = simunits.menu(b.template, sim.own, b.upgrades)
    for j, job in enumerate(row['queue']):
        t = job['template']
        if t in ups:
            cost, secs = simunits.upgrade_cost(t)
            made = {'template': t, 'upgrade': t, 'kind': ups[t]}
        elif t in units:
            cost, secs = simunits.production(t, sim.own)
            made = {'template': t}
        elif ai is not None:                        # the AI's (a yard's structure): its own queue, below
            yard.append((j, job))
            continue
        else:
            gaps.append(f'things[{i}].queue[{j}]: a {b.template} builds no {t} in the host\'s data (not placed)')
            continue
        gaps += _over(i, j, job, cost)
        made.update(owner=b.owner, cost=cost, secs=secs, progress=_pct(job),
                    paid=min(job['paid'], cost), full=None if job['full'] is None else job['full'] + shift)
        jobs.append(made)
    if jobs:
        sim.queues[b.serial] = jobs
        sim.used.add('production')
    if yard:
        costs = [simunits.production(job['template'], sim.own)[0] for _, job in yard]
        whys = ai.put_yard_jobs(b, [{'template': job['template'], 'progress': _pct(job), 'paid': min(job['paid'], c),
                                     'full': None if job['full'] is None else job['full'] + shift}
                                    for (_, job), c in zip(yard, costs)])
        for (j, job), c, why in zip(yard, costs, whys):
            gaps += [f'things[{i}].queue[{j}]: {job["template"]} not placed -- {why}'] if why else _over(i, j, job, c)
    return gaps


def _pct(job):
    """A job's progress as the host keeps it: per cent, float32; one not full in the file kept below 100 (it fills on
    the host's next step)."""
    pct = _f32(job['progress'] * 100.0)
    return BELOW_100 if job['full'] is None and pct >= 100.0 else pct


def _over(i, j, job, cost):
    return [f'things[{i}].queue[{j}].paid: {job["paid"]!r} over the host\'s cost {cost!r} (held to it)'] \
        if job['paid'] > cost else []


def _unmake(sim, b):
    """A thing the placing made alongside another and the file has not, taken out of the host whole -- by the thing,
    not its name (a script's reference of that name may point at another): out of the world (its modules out of the
    schedule), its name and the references to it forgotten. Not a death or a script's delete: nothing told, no corpse
    left for a script to find (the source never had it); not ended either (a thing ends through Life.kill / delete:
    this one never began on the source) -- as simsmall.small_world clears a map's own."""
    sim.world.drop(b)
    if sim.bodies.get(b.name) is b:
        del sim.bodies[b.name]
    for ref in [r for r, o in sim.refs.items() if o is b]:
        del sim.refs[ref]
    sim.world.invalidate_living()


def _put_crews(sim, placed):
    """Each placed thing's `contains` put into it, in order, as the script's instant garrison does, then a garrisoned
    building's home the file's (the put kept the file's owner as the one before); a null home, or one on a building
    the host's filter left empty, the read back names."""
    bodies = {row['id']: b for _, row, b in placed}
    for _, row, g in placed:
        for c in row['contains']:
            sim.garrison.put(bodies[c], g, script=True)
        if row['home'] is not None:
            sim.garrison.set_home(g, row['home'])


# Why a placed player's field reads other than the file's, where the host cannot give it (step 4).
WHY_PLAYER = {
    'power': "the host's own: what its living things make and use now (a power a script added is not carried)",
    'upgrades': 'a player upgrade the host holds is not taken off',
    'relations': 'a relation the host set over the map\'s own is not taken off',
}


def _set_players(sim, doc):
    """Each listed player given the file's money, protocols and points, player upgrades and relations."""
    for p, row in sorted(doc['players'].items()):
        if sim.money.get(p, 0) != row['money']:
            sim.act('PLAYER_SET_MONEY', [p, row['money']], LABEL)
        book = sim.books[p]
        if sorted(book.owned) != sorted(s.lower() for s in row['sciences']) or book.points != row['science_points']:
            book.place(row['sciences'], row['science_points'])      # held as they are: none bought again
            sim.used.add('protocols')
        held = sim.player_ups.get(p, ())
        for up in row['upgrades']:
            if up not in held:
                sim.act('GIVE_PLAYER_UPGRADE', [p, up], LABEL)
        for other, r in sorted(row['relations'].items()):
            if sim.relations.get((p, other)) != r:
                sim.act('PLAYER_RELATES_PLAYER', [p, other, r], LABEL)
    sim.change()


def _read_players(sim, doc):
    """The listed players read back as the export reads them, ['players.<p>.<field>: why', ...] where they differ."""
    got = {p: _player_row(sim.money.get(p, 0), (sorted(sim.books[p].owned), sim.books[p].points),
                          sorted(sim.player_ups.get(p, ())), sim.power(p)) for p in doc['players']}
    _relations(got, sim.relations, _start(sim.m))
    gaps = []
    for p, row in sorted(doc['players'].items()):
        have = _plain(got[p])
        for k in PLAYER:
            for sub in (POWER if k == 'power' else (None,)):
                want, read = (row[k], have[k]) if sub is None else (row[k][sub], have[k][sub])
                if read != want:
                    gaps.append(f'players.{p}.{k}{"." + sub if sub else ""}: {want!r} in the file, the host reads '
                                f'{read!r}' + (f' -- {WHY_PLAYER[k]}' if k in WHY_PLAYER else ''))
    return gaps


def place_players(sim, doc):
    """The file's players onto the host `sim` (its map's run): see the module's step 4. ['field path: why', ...] for
    what does not read back as the file has it (power: placed the things first, or use `place`)."""
    refuse(sim, doc, things=False)
    _set_players(sim, doc)
    return _read_players(sim, doc)


# Why a placed script table reads other than the file's (step 5).
WHY_SCRIPT = {
    'timers': "a deadline is held to the host's frame (round((deadline - t) x its frame rate)), and one out before the "
              'cut as just out (-1 frames left, as the executor keeps it)',
}
ENDINGS = (WON, LOST)


def _frames_left(sim, doc, deadline):
    """A running timer's frames left on the host: its time after the file's cut in the host's frames, -1 at least."""
    return max(-1, round((deadline - doc['t']) * sim.fps))


def _set_script(sim, doc):
    """The host's flags, counter-and-timer table and objectives made the file's, written as they are (no action):
    all worked out first, then written, so one that cannot be leaves the host's as they were."""
    s = doc['script']
    rows = [(k, [v, False]) for k, v in sorted(s['counters'].items())]
    rows += [(k, [_frames_left(sim, doc, d), True]) for k, d in sorted(s['timers'].items())]
    flags = [(k, int(v)) for k, v in sorted(s['flags'].items())]     # as SET_FLAG keeps it: 0 / 1
    objectives = sorted(s['objectives'].items())
    table = sim.executor.counters           # one table: name -> [value, is a running timer] (simexec.Counters)
    for k in list(table):
        del table[k]
    for k, row in rows:
        table[k] = row
    for k in list(sim.flags):
        del sim.flags[k]
    for k, v in flags:
        sim.flags[k] = v
    sim.objectives.clear()
    sim.objectives.update(objectives)
    sim.change()


def _read_script(sim, doc):
    """The tables read back on the file's clock, ['script.<table>.<name>: why', ...] where they differ from it."""
    table = sim.executor.counters
    got = {'flags': {k: bool(v) for k, v in sim.flags.items()},
           'counters': {k: c[0] for k, c in table.items() if not c[1]},
           'timers': {k: doc['t'] + c[0] / sim.fps for k, c in table.items() if c[1]},
           'objectives': dict(sim.objectives)}
    gaps = []
    for part in SCRIPT:
        want, have = doc['script'][part], _plain(got[part])
        for k in sorted(set(want) | set(have)):
            if have.get(k) != want.get(k):
                gaps.append(f'script.{part}.{k}: {want.get(k)!r} in the file, the host reads {have.get(k)!r}'
                            + (f' -- {WHY_SCRIPT[part]}' if part in WHY_SCRIPT else ''))
    for k in ENDINGS:
        if doc['script']['flags'].get(k):
            gaps.append(f'script.flags.{k}: placed, the host does not end on it (placing decides no ending)')
    return gaps


def place_script(sim, doc):
    """The file's script state onto the host `sim` (its map's run): see the module's step 5. ['field path: why', ...]
    for what does not read back as the file has it, and a won or lost flag placed."""
    refuse(sim, doc, things=False)
    _set_script(sim, doc)
    return _read_script(sim, doc)


def place(sim, doc, ai=None):
    """Steps 3 to 5 onto the host `sim` (an empty run of the file's map): the players' state, the things, the players
    read back, the script's state. ['field path: why', ...] as place_things, place_players and place_script give
    them. `ai`: the host's skirmish AI, as place_things takes it."""
    refuse(sim, doc)
    _set_players(sim, doc)
    gaps = place_things(sim, doc, ai)
    gaps += _read_players(sim, doc)
    _set_script(sim, doc)
    return gaps + _read_script(sim, doc)


def rebase(doc, t, frame):
    """An export `doc` moved onto another clock (a copy): its cut at (`t`, `frame`), a running timer's deadline and a
    full job's frame as many seconds / frames after the new cut as after its own (the host's export read on the
    file's clock)."""
    dt, df = t - doc['t'], frame - doc['frame']
    out = dict(doc, t=t, frame=frame)
    out['script'] = dict(doc['script'], timers={k: d + dt for k, d in doc['script']['timers'].items()})
    out['things'] = [dict(row, queue=[dict(j, full=None if j['full'] is None else j['full'] + df)
                                      for j in row['queue']],
                          clocks=[{f: v + df if f in _FRAMES and v is not None else v for f, v in c.items()}
                                  for c in row['clocks']]) for row in doc['things']]
    return out


def _parts(a, b):
    """The field paths where the export `b` differs from the file `a` (both on one clock): a thing paired by its id
    and named by its place in `a` (one only in `b` as "things: 'id'"), a player's field (power by part), a script
    table's entry, the order of the things in common; gaps by NOT_CARRIED only (the host holds no ban, its own
    gaps are its own)."""
    out = [k for k in ('format', 'map', 't', 'frame') if a[k] != b[k]]
    n = len(NOT_CARRIED)
    if a['gaps'][:n] != b['gaps'][:n]:
        out.append('gaps')
    for p in sorted(set(a['players']) | set(b['players'])):
        pa, pb = a['players'].get(p), b['players'].get(p)
        if pa is None or pb is None:
            out.append(f'players.{p}')
            continue
        for k in PLAYER:
            if k == 'power':
                out += [f'players.{p}.power.{s}' for s in POWER if pa[k][s] != pb[k][s]]
            elif pa[k] != pb[k]:
                out.append(f'players.{p}.{k}')
    for part in SCRIPT:
        sa, sb = a['script'][part], b['script'][part]
        out += [f'script.{part}.{k}' for k in sorted(set(sa) | set(sb), key=str) if sa.get(k) != sb.get(k)]
    at = {row['id']: i for i, row in enumerate(a['things'])}
    got = {row['id']: row for row in b['things']}
    for i, row in enumerate(a['things']):
        other = got.get(row['id'])
        if other is None:
            out.append(f'things[{i}]')
            continue
        out += [f'things[{i}].{k}' for k in THING if row.get(k) != other.get(k)]   # clocks may be missing
    out += [f'things: {row["id"]!r}' for row in b['things'] if row['id'] not in at]
    common = [row['id'] for row in b['things'] if row['id'] in at]
    if common != sorted(common, key=at.get):
        out.append('things')
    return out


def _covers(gap, path):
    """Whether a placing's gap ('field path: why') names `path`: the same field, one it is in, or a part of it (a
    job of a thing's queue); a thing only on the host by its "things: 'id'" line."""
    where = gap.split(': ', 1)[0]
    if path.startswith('things: '):
        return gap.startswith(path)
    if where in ('', 'things') or path == 'things':
        return False
    return any(x == y or x.startswith(y) and x[len(y)] in '.[' for x, y in ((path, where), (where, path)))


def round_trip(host, doc, ai=None):
    """Step 8, the round trip: `doc` (an export) placed onto `host` (an empty run of its map; `ai` its skirmish AI,
    which takes and gives back the yards' structures), the host exported and read on the file's clock; [(field path,
    the placing's gap naming it or None), ...] for each field that differs -- the round trip holds when every
    difference has its gap (none None)."""
    gaps = place(host, doc, ai)
    back = export(Observe(host), ai)
    back = rebase(back, doc['t'], doc['frame'])
    return [(path, next((g for g in gaps if _covers(g, path)), None)) for path in _parts(doc, back)]
