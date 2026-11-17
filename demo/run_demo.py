"""Headless simulation of a campaign mission's design -- no game running.

    python demo/run_demo.py            (needs: numpy, PyYAML; scipy is optional)

A mission is written as a plan (docs/story/plans/a4.md): phases, triggers, spawns, objectives, win and lose
conditions. The plan compiler turns it into the game's script/map data; the simulator below plays that data out
against a model of the world (ground, pathing, vision, units) in seconds, for several player behaviours, and a
static analysis + map lint report design problems before anyone opens the game.

Everything printed is computed from the real plan and map of mission A4 ("Sapporo snow festival").
"""
import concurrent.futures
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# the demo always runs on the public timing model (frame-rate stepping), so its numbers are the same on every machine
# and a private engine model sitting beside the repository is never loaded
os.environ['CNV_ENGINE_MODEL'] = os.path.join(ROOT, 'no-engine-model')
# the few SDK data files the compiler reads travel in the zip (sdk3/); in the repository the real SDK is used
if os.path.isdir(os.path.join(ROOT, 'sdk3')):
    os.environ['CNV_SDK'] = os.path.join(ROOT, 'sdk3')
sys.path[:0] = [HERE, os.path.join(ROOT, 'experimental', 'cnv'), os.path.join(ROOT, 'experimental', 'campaign')]

LEVEL = 'a4'
UNTIL = 900.0
PHASE_NAMES = {'会场': 'Festival', '港口生变': 'Harbour turns', '北营': 'North camp', '布防': 'Fortify',
               '最后一程': 'Last stretch'}
ENDINGS = {'赢': 'WIN', '输': 'LOSE'}


def mmss(t):
    t = int(round(t))
    return f'{t // 60}:{t % 60:02d}'


def scripts_for(offline):
    """The player behaviours, each as the simulator's script language ('<time> send <unit> to <site>', ...).
    The designed walkthrough is the plan author's own (offline.WALK); the others are what a player who ignores
    the design would do."""
    walk = offline.WALK[LEVEL]
    parts = walk.split('; ')
    return [
        ('idle: do nothing', ''),
        ('rush: ignore the convoy, send the squads north',
         '0 派 guardian 去 north base; 0 派 peacekeeper 去 north base; 0 派 javelin 去 north base'),
        ('escort only: take the convoy to the halt, then idle', '; '.join(p for p in parts if '段' not in p)),
        ('designed: escort, answer the harbour, raze the camp, fortify', walk),
    ]


def compiler():
    """The plan compiler. The plan's dubbed lines are looked up in a saved snapshot of the voice repository's answers
    (demo/voice_snapshot.py), so no other repository is needed and the timings do not depend on the machine."""
    import plan
    import voice_snapshot
    path = voice_snapshot.find()
    if path:
        voice_snapshot.install(path)
    return plan.Compiler(plan.load(LEVEL))


def play(job):
    """Run one behaviour; returns plain data (it runs in a worker process)."""
    label, script = job
    import offline
    import plan
    import sim
    t0 = time.time()
    c = compiler()
    m = c.compile()
    s = sim.Sim(m, script=offline.anchored(script, c))
    phases = {}
    step = s.step

    def watch():
        step()
        for ph in c.phases:
            if ph.name not in phases and s.flags.get(ph.flag) == 1:
                phases[ph.name] = s.t
    s.step = watch
    s.run(UNTIL if 'only' not in label else 420.0)
    kinds = {}
    for _, k, _x in s.log:
        kinds[k] = kinds.get(k, 0) + 1
    ending = None
    if s.ending:
        ending = (ENDINGS.get(s.ending[0], s.ending[0]), s.ending[1])
    return dict(label=label, ending=ending, t=s.t, wall=time.time() - t0, phases=phases, kinds=kinds,
                threat=(s.first_threat[0], s.first_threat[1].template) if s.first_threat else None,
                death=(s.first_death[0], s.first_death[1].template) if s.first_death else None,
                objectives=[t for t, k, x in s.log if k == '目标'], known=s.known_at[-1][1] if s.known_at else 0)


def analyse():
    """Static analysis of the compiled plan and the map's design lint."""
    import contract
    import parts
    import plan
    import sim
    import simstatic
    c = compiler()
    m = c.compile()
    mm = parts.merged(m, None)
    out = dict(scripts=len(mm.scripts), objects=len(mm.objects), phases=[PHASE_NAMES.get(p.name, p.name) for p in c.phases],
               objectives=len(m.objectives), levels={}, lint=contract.map_design(m))
    for lv, name in enumerate(simstatic.LEVEL_NAMES):
        r = simstatic.Reach(mm, lv)
        ends = [s for s in r.scripts if s.name in m.endings]
        won = any(s.name in r.fires and any(n == 'SET_FLAG' and a[0] == sim.WON for n, *a in s.do) for s in ends)
        lost = any(s.name in r.fires and any(n == 'SET_FLAG' and a[0] == sim.LOST for n, *a in s.do) for s in r.scripts)
        never = [s for s in r.scripts if s.name not in r.fires]
        out['levels'][name] = dict(won=won, lost=lost, never=len(never), total=len(r.scripts))
    out['wiring'] = simstatic.wiring(mm)
    out['detours'] = simstatic.long_detours(mm)
    try:
        out['landings'] = simstatic.landings(mm)
    except ImportError:                                  # scipy missing: that one check is skipped
        out['landings'] = None
    return out


def main():
    t0 = time.time()
    import offline
    jobs = scripts_for(offline)
    workers = max(1, min(len(jobs) + 1, os.cpu_count() or 1))
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
            fut = ex.submit(analyse)
            runs = list(ex.map(play, jobs))
            static = fut.result()
    except (OSError, RuntimeError, concurrent.futures.process.BrokenProcessPool):    # no worker processes here
        runs = [play(j) for j in jobs]
        static = analyse()

    print('RA3 Campaign Lab -- headless mission simulator (mission A4, "Sapporo snow festival")')
    print(f'plan -> {static["scripts"]} compiled scripts, {static["objects"]} placed objects, '
          f'{static["objectives"]} objectives, phases: {" > ".join(static["phases"])}')
    print()
    print('1. SAME MISSION, FOUR PLAYER BEHAVIOURS (simulated play, no game running)')
    for r in runs:
        end = f'{r["ending"][0]} at {mmss(r["ending"][1])}' if r['ending'] else f'no ending within {mmss(r["t"])}'
        reached = [PHASE_NAMES.get(p, p) for p in r['phases']]
        print(f'  {r["label"]}')
        print(f'      result: {end}   | phases reached: {len(reached)}/{len(static["phases"])}   | simulated in {r["wall"]:.1f} s')
    best = next((r for r in runs if r['ending'] and r['ending'][0] == 'WIN'), runs[-1])

    print()
    print('2. KEY EVENTS OF THE DESIGNED RUN (mission clock)')
    k = best['kinds']
    events = [(t, f'phase "{PHASE_NAMES.get(p, p)}" begins') for p, t in best['phases'].items()]
    if best['threat']:
        events.append((best['threat'][0], f'first enemy within 300 units of the player ({best["threat"][1]})'))
    if best['objectives']:
        events.append((best['objectives'][0], 'first objective lit'))
        events.append((best['objectives'][-1], f'last objective update ({len(best["objectives"])} updates in all)'))
    if best['ending']:
        events.append((best['ending'][1], f'ending: {best["ending"][0]}'))
    for t, text in sorted(events):
        print(f'  {mmss(t)}  {text}')
    print(f'  scripted content fired: {k.get("配音", 0)} voice lines, {k.get("出现", 0)} units spawned, '
          f'{k.get("小地图闪点", 0)} minimap pings, {k.get("镜头", 0)} camera moves, {k.get("存档", 0)} autosaves')
    if runs[0]['death']:
        print(f'  for contrast, the idle run loses its first unit at {mmss(runs[0]["death"][0])} ({runs[0]["death"][1]})'
              f' and the mission at {mmss(runs[0]["ending"][1])}')

    print()
    print('3. DESIGN CHECKS (static analysis of the plan + map lint, before anyone opens the game)')
    for name, lv in static['levels'].items():
        print(f'  difficulty {name:<6} can be won: {"yes" if lv["won"] else "NO"}   can be lost: '
              f'{"yes" if lv["lost"] else "NO"}   scripts flagged unreachable: {lv["never"]} of {lv["total"]}')
    print('  (unreachable = the model cannot fire them from the world it simulates; a list to review, not all are errors)')
    print(f'  wiring: {"ok, every flag/timer/counter waited on is set somewhere" if not static["wiring"] else str(len(static["wiring"])) + " problems"}')
    for x in static['wiring'][:3]:
        print('    ' + x)
    print(f'  long detours: {len(static["detours"])} team moves would route far round an obstacle (the game stops units '
          f'partway over ~1400 units)')
    for x in static['detours'][:2]:
        print('    ' + re.sub(r'(Soviet_\d+/\w+ |; over .*)', '', x))
    if static['landings'] is None:
        print('  amphibious landings: skipped (scipy not installed)')
    else:
        print(f'  amphibious landings: {"ok, every shore site reachable" if not static["landings"] else str(len(static["landings"])) + " unreachable"}')
    print(f'  map lint: {"ok (ramps, building sites, bridges, gaps, scenery clear of the ways)" if not static["lint"] else str(len(static["lint"])) + " findings"}')
    for x in static['lint'][:3]:
        print('    ' + x)
    print()
    print(f'total wall time {time.time() - t0:.1f} s on {workers} worker process(es)')


if __name__ == '__main__':
    main()
