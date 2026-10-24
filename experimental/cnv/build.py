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
from checks import a4 as check_a4               # noqa: E402
from checks import a7 as check_a7               # noqa: E402
from checks import j4 as check_j4               # noqa: E402
from checks import a8 as check_a8               # noqa: E402
from checks import beacon as check_bea          # noqa: E402
from checks import burrower as check_bur        # noqa: E402
from checks import clone as check_clo           # noqa: E402
from checks import combo as check_com           # noqa: E402
from checks import crane as check_cra           # noqa: E402
from checks import icewall as check_ice         # noqa: E402
from checks import tesla as check_tes           # noqa: E402
from checks import jammer as check_jam          # noqa: E402
from checks import liberty as check_lib         # noqa: E402
from checks import shikigami as check_shi       # noqa: E402
from checks import train as check_tra           # noqa: E402
from units import tesla as units_tesla          # noqa: E402
from missions import a4, a7, a8, j4, beacon_bench, burrow_bench, clone_bench, combo_bench, crane_bench, icewall_bench, jammer_bench, liberty_bench, shikigami_bench, \
    tesla_bench, train_bench                                # noqa: E402

BENCH_PY = os.path.join(os.path.dirname(ROOT), 'envs', 'bench_mcp', 'Scripts', 'python.exe')
CLIENT = os.path.join(ROOT, 'experimental', 'testbench', 'bench_client.py')


def digits():
    """A map that shows counters.CALIBRATION (every digit once), whose frame gives the counter reader's templates."""
    from maps import island
    values = [1234, 5678, 90]                   # experimental/testbench/counters.py CALIBRATION
    m = parts.Mission(name='CampDigits', map=island)
    t = parts.Test(counters=[(f'Digit {k}', '校准') for k in range(len(values))])
    t.scripts.append(parts.Script('Digits', [], [('SET_COUNTER', f'Digit {k}', v) for k, v in enumerate(values)]))
    t.bench = [('bench_watch', dict(seconds=3, every=3, sheet=False))]
    return m, t


# name -> mission(); checks: name -> check(mission) -> Test; or a build that is a (mission, test) pair outright
MISSIONS = {
    'a4': (lambda: a4.mission(), {'seal': check_a4.seal, 'placed': check_a4.placed, 'smash': check_a4.smash,
                                  'ambush': check_a4.ambush, 'win': check_a4.win, 'lose': check_a4.lose,
                                  'idle': check_a4.idle}),
    'j4': (lambda: j4.mission(), {'breach': check_j4.breach, 'play': check_j4.play, 'lose': check_j4.lose}),
    'a7': (lambda: a7.mission(), {'jumps': check_a7.jumps, 'power': check_a7.power, 'win': check_a7.win}),
    'a8': (lambda: a8.mission(), {'jump': check_a8.jump, 'lose': check_a8.lose, 'assault': check_a8.assault}),
    'a8_control': (lambda: a8.mission(carrier=False, name='CampA8C'), {'assault': check_a8.assault}),
    'liberty': (lambda: liberty_bench.mission(), {'jump': check_lib.jump, 'open': check_lib.jump_open}),
    'liberty_turrets': (lambda: liberty_bench.turrets(), {'fire': check_lib.deck_turrets}),
    'liberty_loose': (lambda: liberty_bench.loose(), {'fire': check_lib.loose_turrets}),
    'liberty_riders': (lambda: liberty_bench.mission(riders=True, name='CampLibR'), {'jump': check_lib.jump}),
    'burrower': (lambda: burrow_bench.mission(), {'pass': check_bur.burrow_pass, 'drop': check_bur.deliver}),
    'beacon': (lambda: beacon_bench.mission(), {'pull': check_bea.pull, 'still': check_bea.still}),
    'combo': (lambda: combo_bench.mission(), {'join': check_com.join}),
    'combo_breach': (lambda: combo_bench.breach(), {'breach': check_com.breach}),
    'combo_spare': (lambda: combo_bench.spare(), {'spare': check_com.spare}),
    'tesla': (lambda: tesla_bench.mission(), {'fight': check_tes.fight}),
    'tesla_surge': (lambda: tesla_bench.surge(), {'surge': check_tes.surge}),
    'tesla_surge_retail': (lambda: tesla_bench.surge(name='CampTslR', fire=False), {'surge': check_tes.surge}),
    'ice_block': (lambda: icewall_bench.block(), {'block': check_ice.block}),
    'ice_turns': (lambda: icewall_bench.turns(), {'turns': check_ice.turns}),
    'ice_freeze': (lambda: icewall_bench.freeze(), {'freeze': check_ice.freeze}),
    'ice_build': (lambda: icewall_bench.freeze(name='CampIceV', builder=True), {'built': check_ice.built}),
    'ice_spawn': (lambda: icewall_bench.freeze(name='CampIceO', spawn='CNV_TeslaTank', extra=[units_tesla.tesla()]),
                  {'built': check_ice.built}),
    'jammer': (lambda: jammer_bench.mission(), {'jam': check_jam.jam, 'free': check_jam.free}),
    'jammer_own': (lambda: jammer_bench.mission(name='CampJamOwn', side='p1'), {'jam': check_jam.jam}),
    'shikigami': (lambda: shikigami_bench.mission(), {'cover': check_shi.cover}),
    'shikigami_shells': (lambda: shikigami_bench.shells(), {'bend': check_shi.bend}),
    'crane': (lambda: crane_bench.mission(), {'spot': check_cra.spot}),
    'crane_hide': (lambda: crane_bench.hide(), {'hide': check_cra.hide}),
    'crane_retail': (lambda: crane_bench.mission(name='CampCraneR', retail=True), {'blind': check_cra.blind}),
    'train': (lambda: train_bench.mission(), {'run': check_tra.run, 'brake': check_tra.brake,
                                              'astray': check_tra.astray}),
    'train_braked': (lambda: train_bench.braked(), {'fire': check_tra.braked_fire}),
    'train_fight': (lambda: train_bench.mission(name='CampTrainF', enemies=True), {'fight': check_tra.fight}),
    'ice_smash': (lambda: icewall_bench.smash(), {'smash': check_ice.smash}),
    'clone': (lambda: clone_bench.mission(), {'hold': check_clo.hold, 'free': check_clo.free}),
    'clone_any': (lambda: clone_bench.mission(name='CampCloneA', picky=False), {'free': check_clo.free_any}),
}
LEVELS = ('a4', 'a7', 'a8', 'j4')                          # campaign levels: each has a card in docs/story/levels.md (the rest:
                                                # A/B controls and bench scenes)


def kinds():
    """A probe of the counting itself: 3 Guardians and 2 buildings of ours, counted four ways at once -- by KindOf
    in an area (VEHICLE, STRUCTURE), by template in an area, by template owned. Should read 3 2 3 3 (the a8 assault's
    KindOf counts read 20 for 12 vehicles, 2026-10-21)."""
    from maps import island
    guardian = 'AlliedAntiVehicleVehicleTech1'
    m = parts.Mission(name='CampKinds', map=island)
    for dx in (-60, 0, 60):
        m.put(guardian, 'west field', dx, -60, role='guardian')
    m.put('AlliedWarFactory', 'base factory', angle=3.1416, role='factory')
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power')
    t = parts.Test()
    whole = m.where('island')
    t.areas['Test Whole Island'] = parts.square(whole.x, whole.y, whole.r + 300)
    parts.counted('Test Kind V', '类别车辆', t, kind=parts.kindof('VEHICLE'), area='Test Whole Island')
    parts.counted('Test Kind S', '类别建筑', t, kind=parts.kindof('STRUCTURE'), area='Test Whole Island')
    parts.counted('Test Type A', '型号区域', t, template=guardian, area='Test Whole Island')
    parts.counted('Test Type O', '型号拥有', t, template=guardian)
    t.expect += [('类别车辆', 3, '==', 3), ('类别建筑', 3, '==', 2), ('型号区域', 3, '==', 3), ('型号拥有', 3, '==', 3)]
    t.bench = [('bench_watch', dict(seconds=6, every=3, sheet=False))]
    return m, t


PAIRS = {'liberty_ride_ab': check_lib.ride_ab, 'digits': digits, 'kinds': kinds}


def resolve(name, check):
    if name in PAIRS:
        m, t = PAIRS[name]()
        return m, t, m.name
    make, checks = MISSIONS[name]
    m = make()
    if not check:
        return m, None, m.name
    return m, checks[check](m), m.name + check.title()


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
    mission ended (won or lost: the check's scripts make it the one they test)."""
    labels = [label for _, label in t.counters]
    verdicts = []
    for e in t.expect:
        label, since, op, want, *until = e
        if label == ENDED:
            seen = [s for s, v in readings if any(x is not None for x in v)]
            gone = [s for s, v in readings if s >= since and seen and s > seen[0] and all(x is None for x in v)]
            verdicts.append((bool(gone), f'mission ended from s{since:.0f}: ' + (f'counters gone at s{gone[0]}' if gone
                                                                                 else 'counters still up')))
            continue
        k, end = labels.index(label), until[0] if until else float('inf')
        got = [(s, v[k]) for s, v in readings if since <= s < end and k < len(v)]
        if op.startswith('ever'):
            ok = any(v is not None and OPS[op[4:]](v, want) for _, v in got)
        else:
            ok = bool(got) and all(v is not None and OPS[op](v, want) for _, v in got)
        verdicts.append((ok, describe(e) + ': ' + (runs(got) or 'no reading')))
    return verdicts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--check', default='')
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--calibrate', action='store_true')
    ap.add_argument('--plan', action='store_true', help='(ra3bench cnv_check) build, then print the bench steps as '
                                                         'one JSON line instead of running them')
    ap.add_argument('--judge', metavar='COUNTERS', help="(ra3bench cnv_check) judge bench_counters' text")
    ap.add_argument('--show', action='store_true', help="the build's interfaces and the contract check, nothing built")
    ap.add_argument('--preview', action='store_true', help='only the map, written to work/maps/<mod>.map in seconds '
                                                           '(no compile, no game): for mapstudy / maprender')
    a = ap.parse_args()
    if a.name == 'list':
        print(listing())
        return
    if a.show:
        text = show(a.name, a.check)
        print(text)
        sys.exit(0 if text.endswith('contract: ok') else 1)
    m, t, mod = resolve(a.name, a.check)
    if a.preview:
        if hasattr(m.map, 'LAYOUT'):            # the map's own design lint first: it needs no map file
            import platmap
            problems = platmap.lint(m.map.LAYOUT, m.map.SITES, getattr(m.map, 'OBJECTS', []))
            print('LINT ' + ('ok' if not problems else '; '.join(problems)))
        path = parts.preview(m, t, out=os.path.join(ROOT, 'work', 'maps', mod + '.map'))
        print('PREVIEW ' + path)
        return
    if a.judge is not None:
        lines, status = report(t, parse_counters(a.judge))
        print('\n'.join(lines))
        sys.exit(status)
    if not a.no_build:
        out = parts.assemble(m, t, name=mod)
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
    print('\n'.join(lines))
    sys.exit(status)


if __name__ == '__main__':
    main()
