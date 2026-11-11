"""One command for the decoupled builds (parts.py): a mission, optionally with a check, assembled into a mod; with
--check also run on the bench through ra3bench and judged on the counters it reads -- PASS / FAIL as text.

  python -I -X utf8 experimental/cnv/build.py list
  python -I -X utf8 experimental/cnv/build.py a8 --check assault --show   (interfaces + contract, nothing built)
  python -I -X utf8 experimental/cnv/build.py a8                      -> Mods/CampA8 (the mission as played)
  python -I -X utf8 experimental/cnv/build.py a8 --check jump         -> Mods/CampA8Jump, bench run, verdict
  python -I -X utf8 experimental/cnv/build.py liberty_ride_ab --check    (two variants on one map)
  ... --no-build: run the check on the mod already built
  python -I -X utf8 experimental/cnv/build.py digits --calibrate      (once: the digit templates for the counters)
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import parts                                    # noqa: E402  (puts experimental/campaign on the path)
import langs                                    # noqa: E402

BENCH_PY = os.path.join(os.path.dirname(ROOT), 'envs', 'bench_mcp', 'Scripts', 'python.exe')
CLIENT = os.path.join(ROOT, 'experimental', 'testbench', 'bench_client.py')

# The builds are not listed here: every mission and check module declares its own (registry.py). MISSIONS: build name ->
# (mission(), {check name: check(mission) -> Test}); PAIRS: a build that is a (mission, test) pair outright.
# An edition of a level (langs.py) is its own name: a4_intl (CampA4En) next to a4 (CampA4); `build.py a4 --lang intl`
# is that name, and ra3bench's cnv_check takes it as it is
import registry                                # noqa: E402
_REG = registry.get()
MISSIONS = {n: (make, _REG.checks.get(n, {})) for n, make in _REG.builds.items()}
PAIRS = _REG.pairs

LEVELS = ('a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'j3', 'j4', 'j5', 'j7', 's2', 's5', 's6')                          # campaign levels: each has a card in docs/story/levels.md (the rest:
                                                # A/B controls and bench scenes)


CAMPAIGN = 'campaign'                           # build.py campaign --shell [--lang intl]: CampShell / CampShellEn, I16


def campaign_levels(lang='zh'):
    """({slot: mission}, fallback slots) of every Allied level (LEVELS a1..a9) in the edition `lang`: its own edition
    where it has one, else the Chinese one (a fallback slot) -- said, never silently (langs.py), as a MISSING line."""
    import shell
    out, missing, fallback = {}, [], set()
    for name in (n for n in LEVELS if n.startswith('a')):
        own = name if lang == 'zh' else f'{name}_{lang}'
        m = MISSIONS[own if own in MISSIONS else name][0]()
        if own not in MISSIONS:
            missing.append(f'{name}: no {lang} edition (built as {name}, the Chinese one)')
            fallback.add(shell.slot_of(m.name))
        if missing_report(m):
            print(missing_report(m))
        out[shell.slot_of(m.name)] = m
    if missing:
        print(f'MISSING in the {lang} campaign ({len(missing)}):\n  ' + '\n  '.join(missing))
    return out, fallback


def campaign(lang='zh'):
    import package
    levels, fallback = campaign_levels(lang)
    return package.assemble_campaign(levels, lang=lang, fallback=fallback)


def resolve(name, check):
    if name in PAIRS:
        m, t = PAIRS[name]()
        return m, t, m.name
    make, checks = MISSIONS[name]
    m = make()
    if not check:
        return m, None, m.name
    return m, checks[check](m), m.name + check.title()


def missing_report(m):
    """What the mission's edition lacks (audio, subtitle text, a translation of a plan string), one per line: never
    silently missing (langs.py). Empty text when nothing is."""
    gone = getattr(m, 'missing', [])
    return (f'MISSING in {m.name} ({len(gone)}):\n  ' + '\n  '.join(gone)) if gone else ''


def listing():
    """Every build: its mod name, and per check the counters it shows and what it expects of them."""
    out = []
    builds = [(n, c) for n, (_, checks) in MISSIONS.items() for c in [''] + list(checks)] + [(p, '') for p in PAIRS]
    for n, c in builds:
        _, t, mod = resolve(n, c)
        head = f'{n}' + (f' --check {c}' if c else '') + f' -> {mod}'
        if t is None:
            out.append(head + ' (the mission as played)')
            continue
        exp = '; '.join(describe(e) for e in t.expect) or 'nothing'
        out.append(f'{head}: counters {[label for _, label in t.counters]}; expects {exp}')
    return '\n'.join(out)


def show(name, check=''):
    """A build's interfaces as text -- what each layer publishes to the next, and whether the build keeps to it:
    the map's sites and players, each unit's abilities, the mission's cast and endings, the check's counters and
    expectations, then contract() over the whole (offline, nothing built)."""
    m, t, mod = resolve(name, check)
    mp = m.map
    out = [f'{name}' + (f' --check {check}' if check else '') + f' -> {mod}, on map {mp.__name__.split(".")[-1]}']
    out.append('map sites: ' + '; '.join(f'{k} ({s.x:g}, {s.y:g}' + (f', r {s.r:g}' if s.r else '') + f'): {s.what}'
                                         for k, s in mp.SITES.items()))
    if getattr(mp, 'STRONGPOINTS', None):
        out.append('map strongpoints: ' + '; '.join(f'{k} = {o.template} "{o.name}" ({o.x:g}, {o.y:g})'
                                                    for k, o in mp.STRONGPOINTS.items()))
    out.append('map players: ' + ', '.join(f'{k} {v}' for k, v in mp.PLAYERS.items()) +
               '; teams: ' + ', '.join(f'{k} {v}' for k, v in mp.TEAMS.items()))
    for u in m.units:
        out.append(f'unit {u.id}: {u.what or "?"}; abilities ' +
                   (', '.join(f'{k} = {v}' for k, v in u.abilities.items()) or 'none') +
                   (f'; params {u.params}' if u.params else ''))
    if m.cast:
        out.append('cast: ' + '; '.join(f'{k} = {r.template}' + (f' "{r.name}"' if r.name else '') +
                                        f' ({r.side}, {", ".join(r.sites) or "?"})' for k, r in m.cast.items()))
    if m.marks:
        out.append('marks: ' + '; '.join(f'{k} = "{w}" ({m.waypoints[w][0]:g}, {m.waypoints[w][1]:g})'
                                         for k, w in m.marks.items()))
    if m.facts:
        out.append('facts: ' + '; '.join(f'{k} = {v:g}' for k, v in m.facts.items()))
    if m.endings:
        out.append('endings: ' + ', '.join(m.endings))
    if m.objectives:
        out.append('objectives: ' + '; '.join(('bonus ' if g.bonus else '') + m.strings.get(g.title, g.title) +
                                              (f' (markers: {", ".join(g.show)})' if g.show else '')
                                              for g in m.objectives))
    if name in MISSIONS:
        out.append('checks: ' + (', '.join(MISSIONS[name][1]) or 'none'))
    if t is not None:
        out.append(f'check: counters {[label for _, label in t.counters]}; expects ' +
                   ('; '.join(describe(e) for e in t.expect) or 'nothing'))
    broken = parts.contract(parts.merged(m, t))
    out.append('contract: ' + ('ok' if not broken else f'{len(broken)} problems\n  ' + '\n  '.join(broken)))
    return '\n'.join(out)


def describe(e):
    label, since, op, want, *until = e
    return (f'{label} {op} {want}'.replace(' None', '') + f' from s{since:g}' +
            (f' until s{until[0]:g}' if until else ''))


WATCH_MAX = 120.0                       # bench_watch's longest single run


def steps(mod, t):
    """The ra3bench calls that run the check: start, the check's own steps, the counters read as text."""
    out = [['bench_start', {'mod': mod, 'look': False}]]
    for n, a in t.bench:
        left = a.get('seconds', 0) if n == 'bench_watch' else 0
        while left > WATCH_MAX:             # one watch runs at most 120 s (bench 2026-10-23: j4 lose asked 153)
            out.append([n, dict(a, seconds=WATCH_MAX)])
            left -= WATCH_MAX
        out.append([n, dict(a, seconds=left) if n == 'bench_watch' else a])
    if t.counters:
        out.append(['bench_counters', {'lines': len(t.counters)}])
    return out


def parse_counters(text):
    """bench_counters' text ('s3: 6 0 5 | s6: ...') -> [(second, [value or None, ...])]."""
    readings = []
    for part in text.split(' | '):
        mm = re.match(r's(\d+): (.*)', part.strip())
        if mm:
            readings.append((int(mm.group(1)), [None if v == '?' else int(v) for v in mm.group(2).split()]))
    return readings


def bench(mod, t):
    """Run the check on the bench (bench_client: start, the check's steps, the counters) -> (readings, log)."""
    out = subprocess.run([BENCH_PY, '-I', '-X', 'utf8', CLIENT, json.dumps(steps(mod, t))], capture_output=True,
                         text=True, encoding='utf-8', errors='replace', cwd=ROOT).stdout
    line = next((x for x in out.splitlines() if ' bench_counters ' in x), '')
    return parse_counters(line.split('=> ', 1)[-1]), out


def runs(pairs, show=str):
    """[(second, value)] with repeats folded: 's1-s6: a | s12: b | s17-s290: c' (a long run of the same reading is
    one entry, not fifty)."""
    out = []
    for s, v in pairs:
        if out and out[-1][2] == v:
            out[-1][1] = s
        else:
            out.append([s, s, v])
    return ' | '.join((f's{a}' if a == b else f's{a}-s{b}') + f': {show(v)}' for a, b, v in out)


def report(t, readings):
    """The readings and the verdicts as lines; exit status 0 = all pass (or nothing expected), 1 = a FAIL."""
    lines = ['counters (' + ', '.join(label for _, label in t.counters) + '): ' +
             runs(readings, lambda v: ' '.join('?' if x is None else str(x) for x in v))]
    verdicts = judge(t, readings)
    lines += [('PASS ' if ok else 'FAIL ') + text for ok, text in verdicts]
    passed = bool(verdicts) and all(ok for ok, _ in verdicts)
    lines.append('RESULT ' + ('PASS' if passed else 'FAIL' if verdicts else 'NO EXPECTATIONS'))
    return lines, 0 if passed or not verdicts else 1


ENDED = 'ENDED'
OPS = {'==': lambda a, b: a == b, '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b, '>': lambda a, b: a > b,
       '<': lambda a, b: a < b}


def judge(t, readings):
    """Each expectation (label, from second, op, value[, until second]) must hold on every reading from that second
    on (and before `until`); an op written 'ever==' (ever>=, ...) on at least one -- for a mission that ends (its
    counters go with it). Label ENDED: from that second some frame shows no counter at all after one that did -- the
    mission ended (won or lost: the check's scripts make it the one they test); with `until`, it ended before then."""
    labels = [label for _, label in t.counters]
    verdicts = []
    for e in t.expect:
        label, since, op, want, *until = e
        if label == ENDED:
            seen = [s for s, v in readings if any(x is not None for x in v)]
            gone = [s for s, v in readings if s >= since and seen and s > seen[0] and all(x is None for x in v)]
            ok = bool(gone) and (not until or gone[0] < until[0])
            verdicts.append((ok, f'mission ended from s{since:.0f}' + (f' before s{until[0]:.0f}' if until else '')
                             + ': ' + (f'counters gone at s{gone[0]}' if gone else 'counters still up')))
            continue
        k, end = labels.index(label), until[0] if until else float('inf')
        got = [(s, v[k]) for s, v in readings if since <= s < end and k < len(v)]
        if op.startswith('ever'):
            ok = any(v is not None and OPS[op[4:]](v, want) for _, v in got)
        else:
            # a reading missing between two that are there was covered for a moment (bench 2026-10-25: the rank-up
            # chevrons over the counters at s323 of two AI runs); missing to the end is the mission gone -- a fail --
            # unless another counter still reads in those frames: then it is still running, this one covered (bench
            # 2026-10-26, A7 east on the redrawn map: the chevrons stayed from s327 to the end over the short lines)
            up = {s for s, v in readings if any(x is not None for x in v)}
            last = max((j for j, (_, v) in enumerate(got) if v is not None), default=-1)
            covered = last >= 0 and all(s in up for s, _ in got[last + 1:])
            ok = bool(got) and covered and all(v is None or OPS[op](v, want) for _, v in got)
        verdicts.append((ok, describe(e) + ': ' + (runs(got) or 'no reading')))
    return verdicts


def parse(argv=None):
    """build.py's arguments (tests/test_architecture.py G8: --shell --check is one of them)."""
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--check', default='')
    ap.add_argument('--lang', default='zh', choices=sorted(langs.EDITIONS),
                    help='the edition: zh = Chinese subtitles and dub (CampA4), intl = English subtitles, each side '
                         'dubbed in its language (CampA4En); what it lacks is listed')
    ap.add_argument('--shell', action='store_true',
                    help='the campaign shell (shell.py, ADR 0014): the mission in its slot of the Allied campaign, the other '
                         'eight slots placeholders, with our own campaign front end, as the mod CampShell (CampShellEn with '
                         '--lang intl; experimental/cnv/launcher.py starts either); with --check the check rides on it as '
                         'a layer (package.check_layer) and the mod is CampShellT / CampShellEnT, the bench walking the '
                         'chapter list into the slot')
    ap.add_argument('--unit', action='store_true',
                    help='with --shell --check: a check that acts on the level (contract.observes lists how) built on the '
                         'shell all the same, as a device unit test (机关单测, not acceptance): the mod CampShellU / '
                         'CampShellEnU, never the acceptance CampShellT')
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--calibrate', action='store_true')
    ap.add_argument('--plan', action='store_true', help='(ra3bench cnv_check) build, then print the bench steps as '
                                                         'one JSON line instead of running them')
    ap.add_argument('--judge', metavar='COUNTERS', help="(ra3bench cnv_check) judge bench_counters' text")
    ap.add_argument('--show', action='store_true', help="the build's interfaces and the contract check, nothing built")
    ap.add_argument('--preview', action='store_true', help='only the map, written to work/maps/<mod>.map in seconds '
                                                           '(no compile, no game): for mapstudy / maprender')
    return ap.parse_args(argv)


TEST_SUFFIX = 'T'                       # a check on the shell: CampShellT / CampShellEnT, beside the release CampShell
UNIT_SUFFIX = 'U'                       # a device unit test on the shell (--unit): CampShellU / CampShellEnU
UNIT_NOTE = '机关单测，不算验收 (device unit test on the shell: the check acts on the level, contract.observes)'


def main():
    a = parse()
    if a.name == 'list':
        print(listing())
        return
    if a.name == CAMPAIGN:
        if not a.shell or a.check:
            sys.exit(f'build: {CAMPAIGN} is the campaign shell with every Allied level: --shell, no --check')
        out = campaign(a.lang)
        print('built to staging (RA3 is running)' if 'staging' in out else f'-> {out}')
        return
    if a.lang != 'zh':
        a.name = f'{a.name}_{a.lang}'
        if a.name not in MISSIONS:
            sys.exit(f'build: no {a.lang} edition of {a.name.rsplit("_", 1)[0]} (builds: {sorted(MISSIONS)})')
    if a.show:
        text = show(a.name, a.check)
        print(text)
        sys.exit(0 if text.endswith('contract: ok') else 1)
    m, t, mod = resolve(a.name, a.check)
    if a.shell:
        import shell
        # CampShell / CampShellEn; with a check CampShellT / CampShellEnT, so the release build installed stays as it is
        # (a device unit test: CampShellU / CampShellEnU). Only a check that only observes rides on the shell as
        # acceptance (ADR 0016: test edition = release edition + observation)
        mod = shell.NAME + langs.edition(a.lang)['suffix']
        if t is not None:
            import contract
            acts = contract.observes(m, t)
            if acts and not a.unit:
                sys.exit('build: the check does more than observe, so it cannot ride on the shell as acceptance '
                         '(--unit builds it as a device unit test):\n  ' + '\n  '.join(acts))
            mod += UNIT_SUFFIX if a.unit else TEST_SUFFIX
            if a.unit:
                print(UNIT_NOTE)
    if missing_report(m):
        print(missing_report(m))
    if a.preview:
        import contract                         # the map's own design lint first (it needs no map file): the one every
        problems = contract.map_design(m)       # build runs (contract.contract), K4e
        print('LINT ' + ('ok' if not problems else '; '.join(problems)))
        path = parts.preview(m, t, out=os.path.join((os.environ.get('CNV_WORK') or os.path.join(ROOT, 'work')), 'maps', mod + '.map'))
        print('PREVIEW ' + path)
        return
    if a.judge is not None:
        lines, status = report(t, parse_counters(a.judge))
        print('\n'.join(([UNIT_NOTE] if a.unit else []) + lines))
        sys.exit(status)
    if not a.no_build:
        if a.shell and t is not None:        # the check as a layer on the shell (ADR 0016 phase 2): only adds
            import package
            out = parts.assemble(m, None, name=mod, shell=a.lang, layers=(package.check_layer(m, t),))
        else:
            out = parts.assemble(m, t, name=mod, shell=a.lang if a.shell else False)
        if 'staging' in out:
            print('built to staging (RA3 is running): no bench run')
            if a.plan:
                print('PLAN ' + json.dumps({'mod': mod, 'staged': True}))
            return
    if a.plan:
        print('PLAN ' + json.dumps({'mod': mod, 'steps': steps(mod, t) if t else []}, ensure_ascii=False))
        return
    if not (a.check or a.calibrate or a.name in PAIRS) or t is None:
        return
    readings, log = bench(mod, t)
    print('\n'.join(x for x in log.splitlines() if 'bench_watch' in x or 'BENCH' in x or 'bench_stop' in x)[:1500])
    if a.calibrate:
        run = re.search(r'frames archived in (\S+?);', log).group(1)
        last = sorted(f for f in os.listdir(run) if f[:4].isdigit())[-1]
        sys.path.insert(0, os.path.join(ROOT, 'experimental', 'testbench'))
        from PIL import Image
        import counters
        print('digits read back:', counters.calibrate(Image.open(os.path.join(run, last)).convert('RGB')))
        return
    lines, status = report(t, readings)
    print('\n'.join(([UNIT_NOTE] if a.unit else []) + lines))
    sys.exit(status)


if __name__ == '__main__':
    main()
