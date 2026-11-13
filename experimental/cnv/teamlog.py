"""Read the AI's teams off a bench run's ra3ext.log (engine line D round 68; the game side is ra3ext's CNVTeams module,
carrier `<DeletionUpdate id="ModuleTag_CNVTeams" MinFrames=EVERY MaxFrames=LINES/>` on an object the AI player owns;
missions/aiteams_bench.py places one).

Every EVERY frames the module writes one `team:` line per team the host's owner has, then one `teams:` line (the end of
that sample):

  team: frame=F list=L proto=P name1='..' name2='..' rel=R slot=S team=T active=A n=N ids=id@x:y,...
  teams: frame=F player=.. index=I ai=.. protos=K teams=M

A team is found by its template's name (either of the two names the prototype carries). Use:

  from teamlog import samples, team_size, team_sizes, members
  team_size(run, 'CNVStateTF', 646)        # the largest such team's member count at the last sample <= 646 (3)
  members(run, 'CNVStateTF_SimpleAttack', 646)     # [[(id, x, y), ...] per team]

A strategic state's team is named by the state's id (hashed the AI's way, see _hashed) or by the logged name itself
('7203be5f_SimpleAttack_0_0'); map / player teams by their own name ('teamSoviet_1'). The first name is the owner.

`run` is a run folder (work/testbench/runs/<run>) or the log file itself. Frames are game frames (15 per second).
"""
import os
import re

LINE = re.compile(r"^team: frame=(-?\d+) list=(\d+) proto=(\S+) name1='([^']*)' name2='([^']*)' rel=(-?\d+) "
                  r"slot=(\d+) team=(\S+) active=(\d+) n=(\d+)(?: \(no member call\))? ids=(\S*)$")
END = re.compile(r'^teams: frame=(-?\d+)(?: full=([01]))? .* protos=(\d+) teams=(\d+)$')


def _log(run):
    return run if os.path.isfile(run) else os.path.join(run, 'ra3ext.log')


def samples(run):
    """[(frame, [team dict, ...]), ...] in log order, each the whole set of teams at that frame; a team dict has frame
    (the frame its line was written), list, proto, names, release, slot, team, active, n, ids ([(id, x, y)]).

    Since D round 81 CNVTeams looks every frame and writes only the teams that changed (members, active, the tstate
    fields but secs), all of them every MinFrames frames and whenever the set changes; `teams: ... full=0/1` closes
    each sample. A full sample replaces the set, a partial one updates it (logs before round 81: always full).
    Positions and secs of an unchanged team are those of its last line."""
    out, cur, live = [], [], {}
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip()
            m = LINE.match(line)
            if m:
                ids = [tuple(int(float(v)) for v in re.split('[@:]', x)) for x in m[11].split(',') if x]
                cur.append(dict(frame=int(m[1]), list=int(m[2]), proto=m[3], names=(m[4], m[5]), release=int(m[6]),
                                slot=int(m[7]), team=m[8], active=int(m[9]), n=int(m[10]), ids=ids))
                continue
            m = END.match(line)
            if m:
                if m[2] is None:     # a log before round 81: every sample whole, kept as written (redacted logs
                    live = {}        # repeat one team token, so keying by it would merge distinct teams)
                    out.append((int(m[1]), cur))
                    cur = []
                    continue
                if m[2] != '0':
                    live = {}
                live.update((t['team'], t) for t in cur)
                out.append((int(m[1]), list(live.values())))
                cur = []
    return out


def _hashed(name):
    """The AI names a strategic state's teams '<FastHash(state id, lower case) as 8 hex>_<Tactic>_<i>_<j>' (bench
    11-12: CNVStateTF -> '7203be5f_SimpleAttack_0_0'); the map's TEAMS name is 'CNVStateTF_SimpleAttack_0_0'."""
    import sagehash
    head, _, rest = name.partition('_')
    h = sagehash.fast_hash_many([head.lower()])[head.lower()]
    return (f'{h:08x}' + ('_' + rest if rest else '')).lower()


def _wants(name):
    """The lower-case names a query matches: itself, and (for a state id) its hashed form -- hashed once per query."""
    want = [name.lower()]
    if not re.match('[0-9a-f]{8}_', want[0]):
        try:
            want.append(_hashed(name))
        except (ImportError, OSError, AssertionError) as e:   # e.g. experimental/campaign not on the path
            import warnings
            warnings.warn(f'teamlog: state id {name!r} not hashed ({e}); only literal names match')
    return want


def _named(team, wants):
    return any(n.lower() == w or n.lower().startswith(w) for n in team['names'] if n for w in wants)


def at(run, frame):
    """The teams of the last sample at or before `frame` ([] when none yet)."""
    best = []
    for f, teams in samples(run):
        if f > frame:
            break
        best = teams
    return best


def members(run, name, frame):
    """Member lists [(id, x, y), ...] of each team whose template is `name` (exact, or the name's start) at `frame`."""
    w = _wants(name)
    return [t['ids'] for t in at(run, frame) if _named(t, w)]


def team_sizes(run, name, frame):
    w = _wants(name)
    return [t['n'] for t in at(run, frame) if _named(t, w)]


def team_size(run, name, frame):
    """The largest member count among the teams named `name` at `frame`; 0 when there is none."""
    return max(team_sizes(run, name, frame), default=0)


TSTATE = re.compile(r'^tstate: frame=(-?\d+) team=(\S+) mstate=(-?\d+) prev=(-?\d+) secs=(\S+) tgt=(-?\d+) '
                    r'chosen=(-?\d+) tact=(-?\d+) idle=(-?\d+) ready=(-?\d+) mem=(\S*)'
                    r'(?: dest=(\S*))?(?: aim=(\S*) hd=(\S*))?(?: at=(\S+))?$')
CMD = re.compile(r'^cmd: frame=(-?\d+) msg=(\S+) type=([0-9a-f]+) player=(\d+) n=(\d+) args=(\S*)(?: src=(\S+))?$')
AES = re.compile(r'^aes: frame=(-?\d+) call=(\d+) team=(\S+) x=(\S+) y=(\S+) r=(\S+) outer=(\S+) mode=(\d+) '
                 r'since=(-?\d+) gate=(-?\d+)$')
AESEND = re.compile(r'^aesend: frame=(-?\d+) call=(\d+) mode=(\d+) since=(-?\d+) sent=(\d+)$')


def _dest(s):
    out = {}
    for x in (s or '').split(','):
        if '@' in x:
            i, _, p = x.partition('@')
            out[int(i)] = tuple(float(v) for v in p.split(':'))
    return out


def _aim(s):
    """`id>target@x:y` / `id>target!` (target id not in the game's object map: gone) / `id>0` (none) ->
    {member id: (target id, (x, y) or None)}."""
    out = {}
    for x in (s or '').split(','):
        if '>' not in x:
            continue
        i, _, rest = x.partition('>')
        t, _, p = rest.rstrip('!').partition('@')
        out[int(i)] = (int(t), tuple(float(v) for v in p.split(':')) if p else None)
    return out


def _hd(s):
    return {int(i): float(d) for i, _, d in (x.partition(':') for x in (s or '').split(',') if ':' in x)}


def _arg(a):
    k, _, v = a.partition(':')
    k = int(k)
    if ':' in v:                                    # kind 7 (or 3): a position x:y:z
        return tuple(float(x) for x in v.split(':'))
    return float(v) if k == 1 else int(v)


def states(run):
    """Engine line D round 78: {team pointer: [state dict, ...]} -- one per sample, written right after that team's
    `team:` line. A state dict: frame, team, mstate (the team's micro state: 8 idle / default, 6 enemy, 1 retreat,
    2..5 gather, 7, 9), prev, secs (seconds in it), tgt / chosen / tact (object ids: current target, chosen target,
    tactical target; -1 none), idle (team idle timeout), ready (the game's team-ready test: 1 / 0; -1 = not read),
    mem [(id, ai state id, unit ready 1/0)], dest {id: (x, y)} each member's AI goal position ({} in older logs),
    aim {id: (target id, (x, y) or None)} each member's AI goal object (0 = none; None position = the id is no longer
    in the game's object map) and where it is, hd {id: degrees} the body heading (atan2 of the hull's forward axis,
    0 = +x, 90 = +y) -- both D round 86, {} in older logs; a new target or a 10-degree turn writes a sample between
    beats; at = None for the regular sample, 'aes' for the snapshot taken as the aesthetics manager is entered (the state its
    decision sees; D round 83). Join to the team's name with team_states()."""
    out = {}
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            m = TSTATE.match(line.rstrip())
            if m:
                mem = [tuple(int(v) for v in x.split(':')) for x in m[11].split(',') if x]
                out.setdefault(m[2], []).append(dict(
                    frame=int(m[1]), team=m[2], mstate=int(m[3]), prev=int(m[4]), secs=float(m[5]), tgt=int(m[6]),
                    chosen=int(m[7]), tact=int(m[8]), idle=int(m[9]), ready=int(m[10]), mem=mem,
                    dest=_dest(m[12]), aim=_aim(m[13]), hd=_hd(m[14]), at=m[15]))
    return out


def aesthetics(run):
    """[call dict, ...] in order, one per call of the engine's aesthetics manager (the StaticDefense /
    ReactiveDefense station picker; D round 83): frame, call (its number), team, centre (x, y), r (Distance), outer,
    mode / since before the call (enemy mode 0/1; the idle-timer start frame, 0 = not started), gate (the
    tactic-ready test it makes: 1/0, -1 not read), mode_after / since_after, sent (messages it queued), state (the
    team's tstate dict as the call was entered, or None), orders [(frame, type, args)] its messages (src=aes:call)."""
    calls, by = [], {}
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip()
            m = AES.match(line)
            if m:
                c = dict(frame=int(m[1]), call=int(m[2]), team=m[3], centre=(float(m[4]), float(m[5])),
                         r=float(m[6]), outer=float(m[7]), mode=int(m[8]), since=int(m[9]), gate=int(m[10]),
                         mode_after=None, since_after=None, sent=None, state=None, orders=[])
                calls.append(c)
                by[c['call']] = c
                continue
            m = AESEND.match(line)
            if m and int(m[2]) in by:
                by[int(m[2])].update(mode_after=int(m[3]), since_after=int(m[4]), sent=int(m[5]))
                continue
            m = CMD.match(line)
            if m and m[7] and m[7].startswith('aes:') and int(m[7][4:]) in by:
                by[int(m[7][4:])]['orders'].append((int(m[1]), int(m[3], 16), [_arg(a) for a in m[6].split(',') if a]))
    for p, ss in states(run).items():
        for s in ss:
            if s['at'] == 'aes':
                hit = [c for c in calls if c['team'] == p and c['frame'] == s['frame'] and c['state'] is None]
                if hit:
                    hit[0]['state'] = s
    return calls


def team_states(run, name):
    """[state dict, ...] in frame order for every team whose template is `name` (as members())."""
    w = _wants(name)
    ptrs = {t['team'] for _, teams in samples(run) for t in teams if _named(t, w)}
    return sorted((s for p, ss in states(run).items() if p in ptrs for s in ss), key=lambda s: s['frame'])


def state_at(run, name, frame):
    """The last state dict of a team named `name` at or before `frame` (None when none)."""
    best = None
    for s in team_states(run, name):
        if s['frame'] > frame:
            break
        best = s
    return best


def commands(run, types=None):
    """[(frame, type, args), ...]: the messages the host owner's player put on the game's command list (AI orders),
    each once, at the frame it was first seen (the frame it was issued). type is the message number (0x1f5 select by
    id, 0x1fb select a team, 0x214 move / attack-move to a point, 0x22c formation move, 0x210 target an object, ...);
    args a list: int, float, or (x, y, z) for a position. `types` keeps only those numbers."""
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            m = CMD.match(line.rstrip())
            if m and (types is None or int(m[3], 16) in types):
                out.append((int(m[1]), int(m[3], 16), [_arg(a) for a in m[6].split(',') if a]))
    return out


def last_command(run, frame, types=(0x214, 0x22c, 0x210)):
    """The last order (frame, type, args) of the given types issued at or before `frame`; None when none."""
    best = None
    for c in commands(run, types):
        if c[0] > frame:
            break
        best = c
    return best


def bench_frames(run):
    """[(second, frame), ...] of the run's saved bench frames (index.json; D round 81): `second` is the bench's
    mission second -- wall time x the rate it asked for, NOT logic time (a slowed game runs fewer frames per bench
    second) -- and `frame` the logic frame ra3ext's shared clock showed when the frame was saved (the frame= of every
    ra3ext line; None without ra3ext or in older runs). The common anchor for bench counters and log lines."""
    import json
    with open(os.path.join(os.path.dirname(_log(run)), 'index.json'), encoding='utf-8') as f:
        return [(x['second'], x.get('frame')) for x in json.load(f)['frames'] if x.get('second') is not None]


def frame_at_second(run, second):
    """The logic frame of the bench frame saved at `second` (the nearest one; None when no frame carries one)."""
    got = [(abs(s - second), f) for s, f in bench_frames(run) if f is not None]
    return min(got)[1] if got else None


def names(run):
    """Every template name seen with a team, and the frames it was seen at (first, last)."""
    seen = {}
    for f, teams in samples(run):
        for t in teams:
            k = ' | '.join(t['names'])
            seen[k] = (seen.get(k, (f, f))[0], f)
    return seen


if __name__ == '__main__':
    import sys
    run, *rest = sys.argv[1:]
    if not rest:
        for k, (a, b) in names(run).items():
            print(f'{a:6d}..{b:6d}  {k}')
    else:
        w = _wants(rest[0])
        for f, teams in samples(run):
            hit = [t for t in teams if _named(t, w)]
            if hit:
                print(f, [(t['n'], t['active'], t['release']) for t in hit])
