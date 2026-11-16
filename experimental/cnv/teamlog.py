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
                  r"(?:pri=-?\d+ )?slot=(\d+) team=(\S+) active=(\d+) n=(\d+)(?: \(no member call\))? ids=(\S*)$")
END = re.compile(r'^teams: frame=(-?\d+)(?: full=([01]))? .* protos=(\d+) teams=(\d+)$')


def _log(run):
    return run if os.path.isfile(run) else os.path.join(run, 'ra3ext.log')


def path_evaluations(run):
    """D108 PathToTarget evaluations, one row per actual call; no forward fill.

    Keep early-return sentinels (-1) distinct from failed path searches (0).
    Conditions and path codes are raw observations, not decoded movement rules.
    Process tokens are deliberately omitted. Evidence: work/re/d108_pathtotarget.md.
    """
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith('ptt: '):
                continue
            d = dict(re.findall(r'(\w+)=(\S+)', line))
            row = {k: int(d[k]) for k in ('frame', 'exists', 'surf', 'cond', 'set14', 'path', 'code')}
            row.update(key=d['key'], locomotors=int(d['loco'].split(':', 1)[0]),
                       result=float(d['res']), why=d['why'])
            for source, target in (('obase', 'own_base'), ('ebase', 'enemy_base')):
                ident, point = d[source].split('@', 1)
                row[target] = (int(ident), tuple(map(float, point.split(':'))))
            for source, target in (('opt', 'own_point'), ('ept', 'enemy_point')):
                row[target] = tuple(map(float, d[source].split(':')))
            out.append(row)
    return out


def build_picks(run):
    """D103 factory picks in log order. Factory tokens distinguish facilities;
    object is an unverified observer field, often zero. Template/asset are
    opaque tokens. filter is bool, or None when not asked (upgrade/defense).
    """
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith('bpick: '):
                continue
            d = dict(re.findall(r'(\w+)=(\S+)', line))
            out.append(dict(frame=int(d['frame']), factory=d['fac'], object=int(d['obj']),
                            template=d['tmpl'], asset=d['a'], score=float(d['score']),
                            filter=None if d['flt'] == '-' else d['flt'] == '1'))
    return out


def build_orders(run):
    """D103 direct factory order attempts (including unsuccessful attempts).
    site distinguishes the unit and structure/defense paths. picks is the
    same-pass candidate snapshot, not a reconstructed last-known pick table.
    """
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith('border: '):
                continue
            d = dict(re.findall(r'(\w+)=(\S+)', line))
            picks = []
            for item in d.get('picks', '').split(','):
                if item:
                    obj, template, score, flt = item.split(':')
                    picks.append(dict(object=int(obj), template=template, score=float(score),
                                      filter=None if flt in ('-', '-1') else flt == '1'))
            out.append(dict(frame=int(d['frame']), site=d['site'], factory=d['fac'], object=int(d['obj']),
                            template=d['tmpl'], asset=d['a'], ok=d['ok'] == '1', picks=picks))
    return out


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
            hashed = _hashed(name)
            want.append(hashed)
            # The engine prints the state hash without leading zeroes.
            # Keep padded names readable too (older fixtures and callers).
            head, sep, rest = hashed.partition('_')
            short = (head.lstrip('0') or '0') + sep + rest
            if short != hashed:
                want.append(short + ('' if sep else '_'))
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


BASE = re.compile(r'^base: frame=(-?\d+) i=(\d+) id=(\d+) own=(\d+) flags=0x([0-9a-f]+) anchor=(\S+) pos=(\S+):(\S+) '
                  r'ctr=(\S+):(\S+) nb=(\d+) bld=(\S*) hit=(-?\d+)$')
BASES = re.compile(r'^bases: frame=(-?\d+) mgr=\S+ n=(\d+)$')
BSEL = re.compile(r'^bsel: frame=(-?\d+)(?: use=(\S+))? ra=\S+ crit=(\S+) ref=(\S+) pick=(-?\d+) model=(-?\d+) cand=(\S*)$')
# AIBaseType bits as the game keeps them on a base (D round 98; XSD order), and AIBaseSortingOrder numbers
BASE_TYPES = ('MAIN_BASE', 'EXPANSION', 'CAPTURED', 'POINT_CENTERED', 'LAND_CENTERED', 'UNDER_ATTACK', 'ENEMIES_IN_BASE',
              'OLDEST_OF_TYPE', 'MOST_RECENT_OF_TYPE', 'NO_BUILD_RADIUS')
SORT_ORDERS = ('PREFER_OLDEST', 'PREFER_NEWEST', 'PREFER_SMALLEST', 'PREFER_LARGEST', 'PREFER_MOST_RECENTLY_ATTACKED',
               'PREFER_LEAST_RECENTLY_ATTACKED', 'PREFER_CLOSEST')


def base_types(flags):
    """The AIBaseType names set in a base's flags."""
    return [n for i, n in enumerate(BASE_TYPES) if flags >> i & 1]


def bases(run):
    """[(frame, [base dict, ...]), ...]: the host owner's AI base table (D round 98), written by CNVTeams when the table
    changed and on each beat; `bases:` closes a sample. A base dict: frame, i (table order), id (the base id -- the age
    SortOrder compares: smaller = older), flags, types, anchor (object id, None when 0), anchor_xy (None when gone),
    pos (x, y), ctr (x, y; bench 11-13 reads (-0.8, -0.6) -- a direction, not a centre: unknown), nb (buildings), bld
    (their ids), hit (the under-attack-until frame)."""
    out, cur = [], []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip()
            m = BASE.match(line)
            if m:
                a = m[6].rstrip('!')
                aid, _, axy = a.partition('@')
                fl = int(m[5], 16)
                cur.append(dict(frame=int(m[1]), i=int(m[2]), id=int(m[3]), flags=fl, types=base_types(fl),
                                anchor=int(aid) or None,
                                anchor_xy=tuple(float(v) for v in axy.split(':')) if axy else None,
                                pos=(float(m[7]), float(m[8])), ctr=(float(m[9]), float(m[10])), nb=int(m[11]),
                                bld=[int(v) for v in m[12].split(',') if v], hit=int(m[13])))
                continue
            m = BASES.match(line)
            if m:
                out.append((int(m[1]), cur))
                cur = []
    return out


def bases_at(run, frame):
    """The base table of the last sample at or before `frame` ([] before the first)."""
    got = [b for f, b in bases(run) if f <= frame]
    return got[-1] if got else []


def base_choices(run, use=None):
    """The AI's base choices (D round 98: every call of the game's base pick for the host's AI, one line per caller when
    its criteria / point / pick / table changed, else once a beat). A dict: frame, use (target = the target heuristics'
    BaseSelection, e.g. Expansion; home, retreat, reactive, nearby, ignore, place; '?' other), crit (None = the default
    {exclude CAPTURED, PREFER_NEWEST}) else dict required / excluded / preferred / not_preferred (flag ints) and sort
    (a SORT_ORDERS name), ref ((x, y) or None), pick (base id, None = none chosen), model (the same rules re-done in the
    probe: equal to pick unless the reading is wrong), cand [(base id, flags, ok, score)] -- ok '1' passes, 'r' misses
    a required type, 'x' has an excluded one; score = preferred count - not-preferred count."""
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            m = BSEL.match(line.rstrip())
            if not m or (use is not None and (m[2] or '?') != use):   # logs before use=: all '?'
                continue
            if m[3] == 'default':
                crit = None
            else:
                r, x, p, n, s = m[3].split(':')
                s = int(s)
                crit = dict(required=int(r, 16), excluded=int(x, 16), preferred=int(p, 16), not_preferred=int(n, 16),
                            sort=SORT_ORDERS[s] if s < len(SORT_ORDERS) else str(s))
            cand = []
            for c in m[7].split(','):
                if c:
                    i, fl, ok, sc = c.split(':')
                    cand.append((int(i), int(fl, 16), ok, int(sc)))
            out.append(dict(frame=int(m[1]), use=m[2] or '?', crit=crit,
                            ref=None if m[4] == '-' else tuple(float(v) for v in m[4].split(':')),
                            pick=None if m[5] == '-1' else int(m[5]), model=None if m[6] == '-1' else int(m[6]),
                            cand=cand))
    return out


# D round 102: the micro manager's per-member target orders and their TimeToKeepTarget clock (E121)
KASSIGN = re.compile(r'^kassign: frame=(-?\d+) team=(\S+) mstate=(-?\d+) src=(\S+) ra=\S+ mem=(\d+) tgt=(\d+) '
                     r'flag=(\d+) ret=(\d+) w=([01]) prev=(\S+) start=(-?\d+) until=(-?\d+) keep=(-?\d+) '
                     r'min=(\S+) max=(\S+) n=(\d+)$')
KPASS = re.compile(r'^kpass: frame=(-?\d+) team=(\S+) cand=(\S*) keep=(\S*)(?: why=(\S*))?$')


def target_orders(run, team=None):
    """Each "order this member to attack X" the host's AI teams gave (D round 102). A dict: frame, team, mstate (the
    team's micro state then), src (score = state 2's per-member scoring, all = state 6's whole-team target, siege =
    state 4, '?' another path), mem, tgt (object ids), flag, ret (the game's result: 0 refused / already on it, 2 crush,
    3 attack, 5 capture, 1 other), wrote (the call wrote the keep record), prev ((target, until) of the record before
    the call, None = none), start (the frame the keep started), until (its expiry frame, -1 = no record), keep (until -
    start frames), min / max (TimeToKeepTargetMin / Max seconds), folded (identical calls since the last line --
    state 6 re-orders every member each pass; those are counted, not written)."""
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            m = KASSIGN.match(line.rstrip())
            if not m or (team is not None and m[2] != team):
                continue
            pt, _, pu = m[10].partition(':')
            out.append(dict(frame=int(m[1]), team=m[2], mstate=int(m[3]), src=m[4], mem=int(m[5]), tgt=int(m[6]),
                            flag=int(m[7]), ret=int(m[8]), wrote=m[9] == '1',
                            prev=None if m[10] == '-' else (int(pt), int(pu)), start=int(m[11]), until=int(m[12]),
                            keep=int(m[13]), min=float(m[14]), max=float(m[15]), folded=int(m[16])))
    return out


def keep_passes(run, team=None):
    """State 2's scoring passes (D round 102), one dict per written pass (change-only, plus one a beat): frame, team,
    cand [(target id, eligible)] -- every hostile-list entry and the game's own filter verdict, the candidates the
    members are scored against -- and keep [(member id, until, 'go'|'hold')]: each member's keep record as the pass read
    it (until 0 = none / target gone) and whether it was re-assigned (go: frame >= until) or kept its target (hold);
    why [(member id, recorded target id, reason)] (D round 104, [] in older logs) -- why that read gave what it gave:
    'ok' (the record's until), 'norec' (no record: cleared), 't0' (record without target), 'gone' (the target id is no
    longer in the object map), 'dead' (the target is still there but flagged dead). The old target's eligibility this
    pass is its cand entry (absent = not in the hostile list)."""
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            m = KPASS.match(line.rstrip())
            if not m or (team is not None and m[2] != team):
                continue
            cand = [(int(i), ok == '1') for i, ok in (c.split(':') for c in m[3].split(',') if c)]
            keep = [(int(i), int(u), d) for i, u, d in (k.split(':') for k in m[4].split(',') if k)]
            why = [(int(i), int(t), r) for i, t, r in (k.split(':') for k in (m[5] or '').split(',') if k)]
            out.append(dict(frame=int(m[1]), team=m[2], cand=cand, keep=keep, why=why))
    return out


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


def expansion_candidates(run):
    """D104 ore-table snapshots; reasons are raw observer tokens.

    candidates retain table order, state, used/capacity (-1 means not read),
    coordinates and rejection/best reason. pick is the final ore id, not the
    last running-best reason. These are separate from base_choices.
    """
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith('expc: '):
                continue
            d = dict(re.findall(r'(\w+)=(\S+)', line))
            candidates = []
            for item in d.get('cand', '').split(','):
                if not item:
                    continue
                oid, rest = item.split('@', 1)
                x, y, state, occupancy, reason = rest.split(':')
                used, capacity = map(int, occupancy.split('/'))
                candidates.append(dict(id=int(oid), point=(float(x), float(y)),
                                       state=int(state), used=used, capacity=capacity,
                                       reason=reason))
            out.append(dict(frame=int(d['frame']), centre=tuple(map(float, d['ctr'].split(':'))),
                            min_distance=float(d['mind']), pick=None if d['pick'] == '-1' else int(d['pick']),
                            count=int(d['n']), candidates=candidates))
    return out


SORTS = ('Distance', 'ThreatToGround', 'ThreatToAir', 'ThreatToWater', 'Random', 'ClosestToEnemy')


def _state_id(sid):
    """The sid field as 8 lower-case hex; None when absent or not hex (public logs write sid=redacted)."""
    try:
        return f"{int(sid, 16):08x}"
    except (TypeError, ValueError):
        return None


def target_picks(run, brain=None):
    """D158 strategic target picks: one row per call of a target heuristic's find (ra3ext `tgt:` lines).

    Row: frame, brain (which AI player; every AI on the map is logged), slot (the AI target manager's slot index),
    state (an opaque per-run token of the run's strategic state), state_id (D159: the state's id as 8 lower-case hex,
    the same FastHash of the lower-case state name the AI's team names start with -- match with state_hash(name);
    None in logs from before round 159), index (which of the state's TargetHeuristics, by its place in the state's
    list; None when not found / old logs), heuristic (class token), sort (SortType name), found, target (object
    id or None), point (x, y), and candidates in the order the game filtered them: id, point, ok (the game's own
    filter verdict), why (the checks the candidate fails, computed by the observer apart from the game: [] none;
    tokens uniq stat dead x471 hide vital forbid area other -- see docs/engine/know-how.md), enemy / distance
    (ClosestToEnemy: the nearest enemy object found for it and the 2D distance), threat (ThreatTo* sorts).
    Lines are change-only (same content again only after a 450-frame beat): a missing frame is not a missing call.
    """
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith('tgt: '):
                continue
            d = dict(re.findall(r'(\w+)=(\S+)', line.split(' cand=')[0]))
            sid = d['state']
            if brain is not None and d['brain'] != brain:
                continue
            cands = []
            tail = line.rstrip('\n').split(' cand=', 1)
            for item in (tail[1].split(' ')[0].split(',') if len(tail) > 1 else []):
                if not item or item == '-':
                    continue
                oid, rest = item.split('@', 1)
                x, y, ok, why, *extra = rest.split(':')
                e = dict(kv.split('=', 1) for kv in extra if '=' in kv)
                cands.append(dict(id=int(oid), point=(float(x), float(y)), ok=ok == '1',
                                  why=[] if why == '-' else why.split('+'),
                                  enemy=int(e['e']) if 'e' in e else None,
                                  distance=float(e['d']) if 'd' in e else None,
                                  threat=float(e['t']) if 't' in e else None))
            tid, tpt = d['target'].split('@', 1)
            sort = int(d['sort'])
            hi = int(d['hi']) if 'hi' in d else -1
            out.append(dict(frame=int(d['frame']), brain=d['brain'], slot=int(d['slot']), state=sid,
                            state_id=_state_id(d.get('sid')),
                            index=None if hi < 0 else hi, heuristic=d['vt'],
                            sort=SORTS[sort] if 0 <= sort < len(SORTS) else sort, found=d['found'] == '1',
                            target=None if tid == '-1' else int(tid),
                            point=tuple(map(float, tpt.split(':'))), count=int(d['n']),
                            more=int(re.search(r' more=(\d+)', line).group(1)) if ' more=' in line else 0,
                            candidates=cands))
            ps = _point_search(line)
            if ps is not None:                  # D166: only on Point rows (older recorded rows stay equal)
                out[-1]['point_search'] = ps
    return out


def _point_search(line):
    """D166: the Point heuristic's own fields of a `tgt:` line, row key point_search (absent on other heuristics / older logs).

    point (x, y, z): the slot's picked point (target id stays 0 -- the old `target=0@0:0` is not a point);
    new: written by this call (else an older pick kept); base / anchor: the base 0x-selection chose by the heuristic's
    BaseSelection (base id, its anchor object id; None = no base -> nothing picked); origin: that base's centre, the
    search origin; range: SearchRange; mask: Location bits (1 water, 2 land); tries: random tries made (max 40, stops
    at 10 kept); candidates: every try inside the map, in order: point, ok (the game's Location verdict = kept),
    threat (ThreatTo* sorts, kept ones only). The tries are random (angle uniform, radius uniform over the disc).
    """
    m = re.search(r' pt=(\S+) new=(\d) base=(-?\d+):(-?\d+)@(\S+?):(\S+) r=(\S+) mask=([0-9a-f]+) tries=(\d+) pc=(\S+)',
                  line)
    if not m:
        return None
    cands = []
    for item in ([] if m.group(10) == '-' else m.group(10).split(',')):
        x, y, ok, *extra = item.split(':')
        t = dict(kv.split('=', 1) for kv in extra if '=' in kv)
        cands.append(dict(point=(float(x), float(y)), ok=ok == '1', threat=float(t['t']) if 't' in t else None))
    base, anchor = int(m.group(3)), int(m.group(4))
    return dict(point=tuple(map(float, m.group(1).split(':'))), new=m.group(2) == '1',
                base=None if base < 0 else base, anchor=None if base < 0 else anchor,
                origin=(float(m.group(5)), float(m.group(6))), range=float(m.group(7)), mask=int(m.group(8), 16),
                tries=int(m.group(9)), candidates=cands)


def state_hash(name):
    """D159: a strategic state's id as target_picks gives it (8 lower-case hex): FastHash of the lower-case name."""
    import sagehash
    return f'{sagehash.fast_hash_many([name.lower()])[name.lower()]:08x}'


def income_evals(run, brain=None):
    """D159 IncomeAdvantageHeuristic evaluations, the same frame (ra3ext `inc:` lines): one row per evaluation.

    Row: frame, brain, own / enemy (player index; enemy None when the game found none), own_in / enemy_in (each
    side's raw input, the float the heuristic reads before its x 1/90 on both sides), value / above (the asset's
    Value and Above), result (the heuristic's 0.0 / 1.0), why ('early' = no priority module / enemy, 'zero' = both
    inputs 0 -> 1, else 'ratio=R' = own / enemy, 9999 when the enemy's input is not above 0).
    own_q / enemy_q: the side's tracker, three neighbouring floats (own_in = own_q[1]).
    Lines are change-only per AI (same content again only after a 450-frame beat).
    D160 bench (aiskxo: a harvesting skirmish AI, money 50000): own_in moved in ore-deposit steps (+112 / +120 / +114
    / +16 / +18) and also fell (-120); own_q[2] never fell; own_q[0] stayed 0; neither is the balance. What the input
    is (a windowed income, INFERRED) is still open: work/re/d160_income.md.
    """
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith('inc: '):
                continue
            d = dict(re.findall(r'(\w+)=(\S+)', line))
            if brain is not None and d['brain'] != brain:
                continue
            own, eny = (int(d[k].split('@')[0]) for k in ('own', 'eny'))
            out.append(dict(frame=int(d['frame']), brain=d['brain'], own=None if own < 0 else own,
                            enemy=None if eny < 0 else eny, own_in=float(d['oin']), enemy_in=float(d['eni']),
                            value=float(d['value']), above=d['above'] == '1', result=float(d['res']), why=d['why'],
                            own_q=tuple(float(x) for x in d['oq'].split(':')),
                            enemy_q=tuple(float(x) for x in d['eq'].split(':'))))
    return out


def under_attack(run, obj=None):
    """D161 "under attack" per object (ra3ext `ua:` lines) -- AITargetingHeuristic UnderAttack's facts.

    The game's rule (read, work/re/d161_underattack.md): an object is under attack while frame <= last hit frame +
    5 s x 15 (x game speed) = `win`; the hit's source does NOT have to exist any more. Only friendly heuristics
    (FriendlyStructure / FriendlyUnit) apply UnderAttack.
    Returns {'episodes': [...], 'gates': [...]}.
    episode: obj, own (player index), set (first hit frame), prev (the hit before it, -1 = never), last (last hit
      frame), clear (first frame no longer under attack = last + win + 1; None if the log ends inside the window),
      src (last hit's source object id), src_alive (it still resolved when the clear was written), hits, win, srcs
      (every source in order), inferred (True: ra3ext never wrote the clear -- it writes one only at the next hit
      anywhere -- and the log runs past last + win, so clear is last + win + 1 by the rule and src_alive is None).
    gate: one row per change of the game's own UnderAttack test on a candidate (change-only per object, beat 450):
      frame, obj, secs, win, last, src, alive, path ('b' = body record; 'a' = the container path, not read),
      result (the game's answer) and expect (last != -1 and frame <= last + win).
    """
    episodes, gates, open_, end = [], [], {}, -1
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            fm = re.search(r'\bframe=(\d+)', line)
            if fm:
                end = max(end, int(fm.group(1)))
            if not line.startswith('ua: '):
                continue
            d = dict(re.findall(r'(\w+)=(\S+)', line))
            o = int(d['obj'])
            if obj is not None and o != obj:
                continue
            ev, frame = d['ev'], int(d['frame'])
            if ev == 'set':
                e = dict(obj=o, own=int(d['own']), set=int(d['last']), prev=int(d['prev']), last=int(d['last']),
                         clear=None, src=int(d['src']), src_alive=None, hits=None, win=int(d['win']),
                         srcs=[int(d['src'])], inferred=False)
                episodes.append(e)
                open_[o] = e
            elif ev == 'src' and o in open_:
                open_[o]['last'], open_[o]['src'] = int(d['last']), int(d['src'])
                open_[o]['srcs'].append(int(d['src']))
            elif ev == 'clr' and o in open_:
                e = open_.pop(o)
                e.update(last=int(d['last']), clear=int(d['at']), src=int(d['src']), src_alive=d['alive'] == '1',
                         hits=int(d['hits']))
            elif ev == 'gate':
                last, win = int(d['last']), int(d['win'])
                gates.append(dict(frame=frame, obj=o, secs=int(d['secs']), win=win, last=last, src=int(d['src']),
                                  alive=d['alive'] == '1', path=d['path'], result=d['res'] == '1',
                                  expect=last != -1 and frame <= last + win))
    for e in open_.values():
        if end > e['last'] + e['win']:
            e.update(clear=e['last'] + e['win'] + 1, inferred=True)
    return dict(episodes=episodes, gates=gates)


# D165 dock phase names per machine (state tables read from the machines' defineState lists; work/re/d165_dock.md).
# top = the miner's AI machine; withnode / deliver = its dock sub-machines (ore node / refinery); node = the ore
# node's own machine. 9998 = the sub-machine finished, 9999 = it failed.
DOCK_STATES = {
    'top': {2000: 'LocateNode', 2002: 'IdleNode', 105: 'DockWithNode', 2001: 'LocateRefinery',
            2003: 'IdleRefinery', 14: 'DeliverOre'},
    'withnode': {2001: 'CanGoDirect', 2010: 'BestBone', 2011: 'MoveQueue', 2012: 'UpdateQueue', 2000: 'SetPad0',
                 2002: 'MovePad0', 2003: 'UpdatePad0', 2004: 'SetPad1', 2005: 'MovePad1', 2006: 'UpdatePad1',
                 2009: 'WaitLoad', 2007: 'SetPad2', 2008: 'MovePad2', 9998: 'done', 9999: 'fail'},
    'deliver': {2002: 'CanGoDirect', 2003: 'BestBone', 2004: 'MoveQueue', 2005: 'UpdateQueue', 2006: 'SetPad0',
                2007: 'MovePad0', 2008: 'UpdatePad0', 2009: 'SetPad1', 2010: 'MovePad1', 2011: 'UpdatePad1',
                2001: 'Unload', 2012: 'SetPad2', 2013: 'MovePad2', 2014: 'KillMiner', 9998: 'done', 9999: 'fail'},
    'node': {2002: 'WaitForMiner', 2003: 'Load', 2004: 'MoveToExtract', 2000: 'Extract', 2001: 'MoveToDeliver'},
}


def dock_phases(run, obj=None):
    """D165 ore miner / ore node / refinery state changes (ra3ext `dock:` lines), one row per setState.

    Row: frame, obj, kind ('top' / 'withnode' / 'deliver' / 'node' / 'dock' / 'other'), old, new (state ids; 999999 =
    no state before), old_name / new_name (DOCK_STATES, None when not in the table), goal (the machine's goal object
    id), pos (where obj stands in the goal's QueueDock: 0..2 pads, 1000+i waiting list, 2000 not in it, -1 no goal /
    the goal has no QueueDock), cargo (the miner's load; -1 not a miner).
    Also returns the run's first-chance faults (ra3ext `exc:` lines): {'phases': [...], 'faults': [...]}, fault rows
    frame, code, eip, addr, rw (0 read, 1 write, 8 execute).
    """
    phases, faults = [], []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.startswith('exc: '):
                d = dict(re.findall(r'(\w+)=(\S+)', line))
                faults.append(dict(frame=int(d['frame']), code=d['code'], eip=d['eip'], addr=d['addr'],
                                   rw=int(d['rw'])))
                continue
            if not line.startswith('dock: '):
                continue
            d = dict(re.findall(r'(\w+)=(\S+)', line))
            o = int(d['obj'])
            if obj is not None and o != obj:
                continue
            names = DOCK_STATES.get(d['kind'], {})
            old, new = int(d['old']), int(d['new'])
            phases.append(dict(frame=int(d['frame']), obj=o, kind=d['kind'], old=old, new=new,
                               old_name=names.get(old), new_name=names.get(new), goal=int(d['goal']),
                               pos=int(d['pos']), cargo=int(d['cargo'])))
    return dict(phases=phases, faults=faults)
