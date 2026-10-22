"""One command for the decoupled builds (parts.py): a mission, optionally with a check, assembled into a mod; with
--check also run on the bench through ra3bench and judged on the counters it reads -- PASS / FAIL as text.

  python -I -X utf8 experimental/cnv/build.py list
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
from checks import a8 as check_a8               # noqa: E402
from checks import liberty as check_lib         # noqa: E402
from missions import a8, liberty_bench          # noqa: E402

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
    'a8': (lambda: a8.mission(), {'jump': check_a8.jump, 'lose': check_a8.lose}),
    'a8_control': (lambda: a8.mission(carrier=False), {}),
    'liberty': (lambda: liberty_bench.mission(), {'jump': check_lib.jump}),
    'liberty_riders': (lambda: liberty_bench.mission(riders=True, name='CampLibR'), {'jump': check_lib.jump}),
}
PAIRS = {'liberty_ride_ab': check_lib.ride_ab, 'digits': digits}


def resolve(name, check):
    if name in PAIRS:
        m, t = PAIRS[name]()
        return m, t, m.name
    make, checks = MISSIONS[name]
    m = make()
    if not check:
        return m, None, m.name
    return m, checks[check](m), m.name + check.title()


def bench(mod, t):
    """Run the check on the bench (bench_client: start, the check's steps, the counters) -> (readings, log)."""
    steps = [['bench_start', {'mod': mod, 'look': False}]] + [[n, a] for n, a in t.bench]
    if t.counters:
        steps.append(['bench_counters', {'lines': len(t.counters)}])
    out = subprocess.run([BENCH_PY, '-I', '-X', 'utf8', CLIENT, json.dumps(steps)], capture_output=True, text=True,
                         encoding='utf-8', errors='replace', cwd=ROOT).stdout
    readings = []
    line = next((x for x in out.splitlines() if ' bench_counters ' in x), '')
    for part in line.split('=> ', 1)[-1].split(' | '):
        mm = re.match(r's(\d+): (.*)', part.strip())
        if mm:
            readings.append((int(mm.group(1)), [None if v == '?' else int(v) for v in mm.group(2).split()]))
    return readings, out


ENDED = 'ENDED'
OPS = {'==': lambda a, b: a == b, '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b, '>': lambda a, b: a > b,
       '<': lambda a, b: a < b}


def judge(t, readings):
    """Each expectation (label, from second, op, value) must hold on every reading from that second on; an op
    written 'ever==' (ever>=, ...) on at least one -- for a mission that ends (its counters go with it). Label
    ENDED: from that second some frame shows no counter at all after one that did -- the mission ended (won or
    lost: the check's scripts make it the one they test)."""
    labels = [label for _, label in t.counters]
    verdicts = []
    for label, since, op, want in t.expect:
        if label == ENDED:
            seen = [s for s, v in readings if any(x is not None for x in v)]
            gone = [s for s, v in readings if s >= since and seen and s > seen[0] and all(x is None for x in v)]
            verdicts.append((bool(gone), f'mission ended from s{since:.0f}: ' + (f'counters gone at s{gone[0]}' if gone
                                                                                 else 'counters still up')))
            continue
        k = labels.index(label)
        got = [(s, v[k]) for s, v in readings if s >= since and k < len(v)]
        if op.startswith('ever'):
            ok = any(v is not None and OPS[op[4:]](v, want) for _, v in got)
        else:
            ok = bool(got) and all(v is not None and OPS[op](v, want) for _, v in got)
        verdicts.append((ok, f'{label} {op} {want} from s{since:.0f}: ' + (' '.join(f's{s}={v}' for s, v in got) or
                                                                          'no reading')))
    return verdicts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--check', default='')
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--calibrate', action='store_true')
    a = ap.parse_args()
    if a.name == 'list':
        for n, (_, checks) in MISSIONS.items():
            print(n, 'checks:', ', '.join(checks) or '-')
        print('pairs:', ', '.join(PAIRS))
        return
    m, t, mod = resolve(a.name, a.check)
    if not a.no_build:
        out = parts.assemble(m, t, name=mod)
        if 'staging' in out:
            print('built to staging (RA3 is running): no bench run')
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
    print('counters:', ' | '.join(f's{s}: ' + ' '.join(map(str, v)) for s, v in readings),
          '(' + ', '.join(label for _, label in t.counters) + ')')
    verdicts = judge(t, readings)
    for ok, text in verdicts:
        print('PASS' if ok else 'FAIL', text)
    passed = bool(verdicts) and all(ok for ok, _ in verdicts)
    print('RESULT', 'PASS' if passed else 'FAIL' if verdicts else 'NO EXPECTATIONS')
    sys.exit(0 if passed or not verdicts else 1)


if __name__ == '__main__':
    main()
