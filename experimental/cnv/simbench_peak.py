"""The peak-load benchmark (ADR 0034 item 10, docs/engine/sim-modules.md 9.3): how fast one world runs a skirmish's
busiest stretch, in one process.

    python -X utf8 experimental/cnv/simbench_peak.py                 # 60 s of the scene, the result to work/logs/perf
    python -X utf8 experimental/cnv/simbench_peak.py --secs 20 --units 100 --no-model

The scene (until the S step's exact snapshots give a real one): the island, two players (Player_1 Allied against
Soviet_1), each a whole base (yard, three power plants, barracks, war factory, refinery by an ore node, airfield)
and an army of `units` (infantry, vehicles, aircraft, five kinds) drawn up 500 apart in the middle, both
attack-moving to the centre while their factories work through 100 queued units on a million credits. It is placed
by list (as simsmall.small_world), so it is the same each run. The run: `secs` simulated seconds by Sim.advance in
10 s slices, its wall time (no build, no imports) and each frame cell's share (simloop.timed), the first-frame cell
split into its aura / fight / move. The armies thin out as they fight, so the whole run's multiple flatters the
peak: `worst` (the slowest slice, the first) is the one to hold above real time.

Result: {'rev', 'units', 'secs', 'model', 'build', 'wall', 'multiple' (simulated / wall seconds: > 1 is faster than
real time), 'worst', 'slices' (each slice's multiple), 'bodies', 'alive', 'made', 'cells', 'inside'} printed and
written to <out>/peak_<rev>.json."""
import sim  # noqa: I001  (first: it puts experimental/cnv and campaign on the path)
import argparse
import json
import os
import subprocess
import sys
import time

import simloop
import simsmall

HERE = os.path.dirname(os.path.abspath(__file__))
SECS, UNITS = 60.0, 300
QUEUED, MONEY = 100, 1_000_000                # queued a side: more than 60 s builds, so the factories never stop
SLICE = 10.0                                  # seconds a slice: the peak is the slowest (the armies thin out)
CENTRE = (2500.0, 2350.0)
# side, player, its base's x, the way it faces (+1 east), its army: kinds it builds and fields in turn
SIDES = (
    ('Allied', 'Player_1', 1000.0, 1, ('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry',
                                       'AlliedAntiInfantryVehicle_Ground', 'AlliedAntiAirVehicleTech1',
                                       'AlliedAntiGroundAircraft')),
    ('Soviet', 'Soviet_1', 4000.0, -1, ('SovietAntiInfantryInfantry', 'SovietAntiVehicleInfantry',
                                        'SovietAntiInfantryVehicle', 'SovietAntiAirShip_Ground',
                                        'SovietAntiGroundAircraft')),
)
BASE = ('ConstructionYard', 'PowerPlant', 'PowerPlant', 'PowerPlant', 'Barracks', 'WarFactory', 'Refinery',
        'Airfield', None)                    # None: the refinery's ore node (the civilians')
ROWS_OF, SPACE, GAP = 25, 30.0, 500.0         # an army: rows of 25, 30 apart; the two fronts GAP apart
INSIDE = ('aura_tick', 'fight', 'move')       # the first-frame cell's parts, timed apart


def objects(units=UNITS):
    """The scene's placement: (name, template, owner, x, y), bases then armies."""
    out = []
    for side, owner, x, way, army in SIDES:
        for i, kind in enumerate(BASE):
            t = f'{side}{kind}' if kind else 'OreNode'
            out.append((f'{owner}_b{i}', t, 'Civilian' if kind is None else owner,
                        x - way * 100 + (i % 3) * 140 * way, 2000.0 + (i // 3) * 170))
        front = CENTRE[0] - way * GAP / 2
        for i in range(units):
            r, c = divmod(i, ROWS_OF)
            out.append((f'{owner}_u{i}', army[i % len(army)], owner, front - way * r * SPACE,
                        CENTRE[1] - SPACE * ROWS_OF / 2 + c * SPACE))
    return out


def scene(units=UNITS, model=True):
    """The scene's Sim: placed, paid, its factories queued, both armies attack-moving to the centre."""
    s = simsmall.small_world(objects(units), model=model)
    for _, owner, _, _, army in SIDES:
        s.money[owner] = MONEY
        for k in range(QUEUED):
            s.order_build(owner, army[k % len(army)])
    for _, owner, _, _, _ in SIDES:
        s.order_group([b for b in s.bodies.values() if b.owner == owner and b.name.startswith(owner + '_u')],
                      CENTRE, True)
    return s


def _clock(s, name, totals):
    """s.<name> timed into totals[name] (an instance attribute over the method, this Sim only)."""
    plain = getattr(s, name)

    def timed(*a, **k):
        t0 = time.perf_counter()
        try:
            return plain(*a, **k)
        finally:
            totals[name] = totals.get(name, 0.0) + time.perf_counter() - t0
    setattr(s, name, timed)


def rev():
    try:
        return subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=HERE, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return 'unknown'


def run(secs=SECS, units=UNITS, model=True):
    """The benchmark: the scene, then `secs` simulated seconds, timed. Returns the result dict (module doc)."""
    t0 = time.perf_counter()
    s = scene(units, model)
    build = time.perf_counter() - t0
    start = len(s.bodies)
    cells, inside = {}, {}
    for name in INSIDE:
        _clock(s, name, inside)
    frame = simloop.timed(cells)
    s.step = lambda: simloop.step(s, frame)
    slices, done = [], 0.0
    while done < secs - 1e-9:
        step = min(SLICE, secs - done)
        t0 = time.perf_counter()
        s.advance(int(round(step * s.fps)))
        slices.append((step, time.perf_counter() - t0))
        done += step
    wall = sum(w for _, w in slices)
    owners = [owner for _, owner, *_ in SIDES]
    return {'rev': rev(), 'units': units, 'secs': secs, 'model': s.eng is not None, 'build': round(build, 2),
            'wall': round(wall, 2), 'multiple': round(secs / wall, 3),
            'worst': round(min(n / w for n, w in slices), 3), 'slices': [round(n / w, 3) for n, w in slices],
            'bodies': len(s.bodies),
            'alive': {o: sum(1 for b in s.bodies.values() if b.alive and b.owner == o) for o in owners},
            'made': len(s.bodies) - start,
            'cells': {k: round(v, 3) for k, v in sorted(cells.items(), key=lambda kv: -kv[1])},
            'inside': {k: round(v, 3) for k, v in sorted(inside.items(), key=lambda kv: -kv[1])}}


def logs_dir():
    """work/logs/perf of this checkout, or of the main one (a worktree without its own work/)."""
    root = os.path.dirname(os.path.dirname(HERE))
    if not os.path.isdir(os.path.join(root, 'work')):
        try:
            common = subprocess.run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], cwd=HERE,
                                    capture_output=True, text=True, check=True).stdout.strip()
            root = os.path.dirname(common)
        except (OSError, subprocess.CalledProcessError):
            pass
    return os.path.join(root, 'work', 'logs', 'perf')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--secs', type=float, default=SECS)
    ap.add_argument('--units', type=int, default=UNITS, help='each side\'s army')
    ap.add_argument('--no-model', action='store_true', help='without the private engine model')
    ap.add_argument('--out', default=None, help='folder for peak_<rev>.json (default work/logs/perf)')
    a = ap.parse_args()
    # a timing: the whole of the machine's CPU tokens (cpupool, T5), so other lines' jobs do not share its cores
    import importlib.util
    spec = importlib.util.spec_from_file_location('_cpupool', os.path.join(os.path.dirname(HERE), 'testbench', 'cpupool.py'))
    cpupool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cpupool)
    with cpupool.hold(1, 'simbench_peak', exclusive=True):
        r = run(a.secs, a.units, not a.no_model)
    out = a.out or logs_dir()
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f'peak_{r["rev"]}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    print(f'{r["secs"]:g} s, {r["units"]} a side, model {r["model"]}: wall {r["wall"]:.1f} s = '
          f'{r["multiple"]:.2f}x real time, the slowest {SLICE:g} s {r["worst"]:.2f}x '
          f'({" ".join("%.2f" % m for m in r["slices"])}); bodies {r["bodies"]} (made {r["made"]}), alive {r["alive"]}')
    for k, v in list(r['cells'].items())[:8]:
        print(f'   {k:18} {v:8.2f} s {v / r["wall"]:6.1%}')
    print('   tick_first:', ', '.join(f'{k} {v:.2f} s' for k, v in r['inside'].items()))
    print('->', path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
