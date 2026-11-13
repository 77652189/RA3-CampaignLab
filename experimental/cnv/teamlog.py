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
KPASS = re.compile(r'^kpass: frame=(-?\d+) team=(\S+) cand=(\S*) keep=(\S*)$')


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
    it (until 0 = none / target gone) and whether it was re-assigned (go: frame >= until) or kept its target (hold)."""
    out = []
    with open(_log(run), encoding='utf-8', errors='replace') as f:
        for line in f:
            m = KPASS.match(line.rstrip())
            if not m or (team is not None and m[2] != team):
                continue
            cand = [(int(i), ok == '1') for i, ok in (c.split(':') for c in m[3].split(',') if c)]
            keep = [(int(i), int(u), d) for i, u, d in (k.split(':') for k in m[4].split(',') if k)]
            out.append(dict(frame=int(m[1]), team=m[2], cand=cand, keep=keep))
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
