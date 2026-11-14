"""Injection tools on the bench (engine line D round 135; ADR 0027): "注入看" -- read what the game's insides did.

ra3ext (the injected dll, work/re/ext) already logs the AI's insides into each run's ra3ext.log: orders entering the
command queue, a team handing an order to a member, a member's target and AI state changing, the team's micro state,
team assignments, threat picks. This module turns those lines into one kind of record, whatever line they came from:

  frame, kind, unit (object id, or 'team:<id>'), what (in words), source (which piece of the program did it)

so a check / a test / the ra3bench tool `inject_look` asks "which orders did unit 3171 get after frame 290, and from
where" instead of every reader writing its own log parser.

  from inject import look, text
  print(text(look(run, kinds=('command',), frames=(290, 400))))
  # f302 3171 command 移动(倒车)到 (3622.3, 3361.5) <- ReverseMove

Program names: a line carries the raw place in the program it came from; the place -> name table is private
(work/re/inject_names.json, the red line: no program addresses in public files) and read at run time. A place not in
the table shows as itself, only on screen. Kinds a map wants recorded are declared by name (KINDS); ra3ext logs them
whenever the map carries its host (missions/aiteams_bench.py host_unit, Mission.ext).

"注入摆" (round 135b): set something at frame N. A mission / check lists plan lines in Part.inject (built with pos());
the build writes them next to ra3ext.allow (package.mark_plan), the bench copies them into the run folder before the
start (harness.hand_plan), and the map's CNVCmd host (missions/aiteams_bench.py host_unit(cmd=True)) runs each at its
frame and logs a 'poke:' line, read back here as kind 'poke'. Ops so far: pos (an object by its map script name moved
to x, y, its height kept). A result that needed a poke rests on a placed start, not the mission's own: say so.
"""
import json
import os
import re
from dataclasses import dataclass

# kind -> (log line prefix, what it is). The map declares kinds by these names.
KINDS = {
    'command': ('cmd:', 'an order entering the command queue (AI or script), with the unit it was given to'),
    'dispatch': ('dcmd:', 'a team handing an order to one member'),
    'goal': ('goal:', "a member's target changing"),
    'state': ('sst:', "a member's AI state changing"),
    'team': ('tstate:', "the team's micro state, target or tactical target changing"),
    'assign': ('kassign:', 'the team assigning a member a target'),
    'threat': ('thr:', 'a member picking a threat'),
    'poke': ('poke:', 'a plan line carried out ("注入摆", pos())'),
}


def pos(frame, name, x, y):
    """The plan line: at logic frame `frame` move the object with map script name `name` to (x, y), height kept."""
    assert int(frame) == frame >= 0, frame
    assert name and name.isascii() and name == name.strip() and '\n' not in name and "'" not in name, name
    return f'at {int(frame)} pos {name} {float(x):.1f} {float(y):.1f}'

# message numbers (protocol words, teamlog.commands) in words; an unknown one shows as its number
ORDERS = {0x1f5: '选中', 0x1fb: '选整队', 0x214: '移到', 0x22c: '编队移到', 0x20d: '对象加点', 0x210: '对目标（攻击 / 进驻）',
          0x236: '移动(倒车)到'}

NAMES = os.path.join('re', 'inject_names.json')


@dataclass
class Event:
    frame: int
    kind: str
    unit: str
    what: str
    source: str        # raw place in the program ('?' if the line has none); name it with source_name


def _work():
    """labpaths.WORK (a worktree without its own work/ uses the main checkout's), loaded by path: no sys.path change."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'labpaths', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'campaign', 'labpaths.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.WORK


def source_names(path=None):
    """{raw place: program name} from the private table (work/re/inject_names.json), {} without it."""
    path = path or os.path.join(_work(), NAMES)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith('_')}


def source_name(ev, names):
    return names.get(ev.source, ev.source)


def _fields(line):
    return dict(re.findall(r'(\w+)=(\S+)', line))


def _args(s):
    """'7:3622.3:3361.5:212.5,4:3171' -> [(7, ['3622.3', '3361.5', '212.5']), (4, ['3171'])]."""
    out = []
    for a in filter(None, s.split(',')):
        k, *v = a.split(':')
        out.append((int(k), v))
    return out


def _order(t, args):
    word = ORDERS.get(t, f'消息 {t:#x}')
    for k, v in args:
        if k == 7:
            word += f' ({float(v[0]):.1f}, {float(v[1]):.1f})'
        elif k == 4 and v[0] != '0':
            word += f' 对象 {v[0]}'
    return word


def _source(d):
    return d.get('src') if d.get('src', '?') not in ('?', 'score', 'all', 'q') else d.get('ra', '?')


def look(run, kinds=None, unit=None, frames=None):
    """The records of `run` (a run folder or its ra3ext.log), log order. kinds: names of KINDS (None = all);
    unit: an object id (int or str) to keep only its records; frames: (first, last) inclusive."""
    kinds = tuple(kinds or KINDS)
    bad = [k for k in kinds if k not in KINDS]
    assert not bad, f'unknown kinds {bad}; known: {sorted(KINDS)}'
    log = run if os.path.isfile(run) else os.path.join(run, 'ra3ext.log')
    picked = {KINDS[k][0]: k for k in kinds}
    selection, last_team = {}, {}       # player -> selected ids (the select order before an AI order names the unit)
    team_names = {}
    out = []
    with open(log, encoding='utf-8', errors='replace') as f:
        for line in f:
            prefix = line.split(' ', 1)[0]
            if prefix == 'team:':           # the team's template name, for its tstate lines
                m = re.search(r"name2='([^']*)' .*team=(\S+)", line)
                if m:
                    team_names[m.group(2)] = m.group(1)
                continue
            if prefix not in picked and prefix != 'cmd:':
                continue
            d = _fields(line)
            if 'frame' not in d:
                continue
            fr = int(d['frame'])
            kind = picked.get(prefix)
            ev = None
            if prefix == 'cmd:':
                if 'type' not in d:         # CNVCmd's own lines (listening, at ... queued, set ...): no order
                    continue
                t, args, pl = int(d['type'], 16), _args(d.get('args', '')), d.get('player', '?')
                if t == 0x1f5:      # select by id: first bool = a new selection
                    ids = [v[0] for k, v in args if k == 4]
                    if args and args[0] == (2, ['1']):
                        selection[pl] = []
                    selection.setdefault(pl, []).extend(ids)
                    continue
                if t == 0x1fb:
                    selection[pl] = [f'team:{v[0]}' for k, v in args if k in (0, 4)]
                    continue
                if kind:
                    ev = Event(fr, kind, ','.join(selection.get(pl, [])) or '?', _order(t, args), _source(d))
            elif kind == 'dispatch':
                ev = Event(fr, kind, d.get('mem', '?'), f"队伍下令 类型 {d.get('type', '?')} 状态 {d.get('st', '?')}",
                           d.get('ra', '?'))
            elif kind == 'goal':
                ev = Event(fr, kind, d.get('mem', '?'), f"目标 {d.get('old')} -> {d.get('new')}", d.get('ra', '?'))
            elif kind == 'state':
                ev = Event(fr, kind, d.get('mem', '?'), f"AI 状态 {d.get('old')} -> {d.get('new')}", d.get('ra', '?'))
            elif kind == 'assign':
                ev = Event(fr, kind, d.get('mem', '?'), f"分配目标 {d.get('tgt')} (队伍状态 {d.get('mstate')})",
                           _source(d))
            elif kind == 'poke':
                nm = re.search(r"name='([^']*)'", line)
                nm = nm.group(1) if nm else '?'
                what = (f"摆 {nm} 没找到" if d.get('id') == '-1'
                        else f"摆 {nm} {d.get('was', '?').replace(':', ',')} -> {d.get('now', '?').replace(':', ',')}")
                ev = Event(fr, kind, d.get('id', '?'), what, '?')
            elif kind == 'threat':
                ev = Event(fr, kind, d.get('mem', '?'), f"挑威胁 {d.get('pick')}", _source(d))
            elif kind == 'team':
                key = (d.get('mstate'), d.get('tgt'), d.get('tact'))
                if last_team.get(d.get('team')) == key:
                    continue
                last_team[d.get('team')] = key
                ev = Event(fr, kind, f"team:{team_names.get(d.get('team'), d.get('team'))}",
                           f'队伍状态 {key[0]} 目标 {key[1]} 战术目标 {key[2]} 成员 {_members(d.get("mem", ""))}', '?')
            if ev is None:
                continue
            if frames and not frames[0] <= fr <= frames[1]:
                continue
            if unit is not None and str(unit) not in ev.unit.split(','):
                continue
            out.append(ev)
    return out


def _members(mem):
    return ','.join(m.split(':')[0] for m in mem.split(',') if m) or '-'


def text(events, names=None, cap=200):
    """One line per record: 'f<frame> <unit> <kind> <what> <- <program>'; at most `cap` lines (and a count after)."""
    names = source_names() if names is None else names
    lines = [f'f{e.frame} {e.unit} {e.kind} {e.what}' + (f' <- {source_name(e, names)}' if e.source != '?' else '')
             for e in events]
    more = len(lines) - cap
    return '\n'.join(lines[:cap] + ([f'... {more} more'] if more > 0 else [])) or '(no records)'
