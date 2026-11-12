"""Read the AI's teams off a bench run's ra3ext.log (engine line D round 68; the game side is ra3ext's CNVTeams module,
carrier `<DeletionUpdate id="ModuleTag_CNVTeams" MinFrames=EVERY MaxFrames=LINES/>` on an object the AI player owns;
checks/engine_aiteams.py places one).

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
END = re.compile(r'^teams: frame=(-?\d+) .* protos=(\d+) teams=(\d+)$')


def _log(run):
    return run if os.path.isfile(run) else os.path.join(run, 'ra3ext.log')


def samples(run):
    """[(frame, [team dict, ...]), ...] in log order; a team dict has frame, list, proto, names, release, slot, team,
    active, n, ids ([(id, x, y)])."""
    out, cur = [], []
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
                out.append((int(m[1]), cur))
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
        except (ImportError, OSError, AssertionError):
            pass
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
