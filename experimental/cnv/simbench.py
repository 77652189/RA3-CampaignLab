r"""A4's bench checks (checks/a4.py) judged by the plan simulator instead of the bench (docs/story/sim-vs-bench-a4.md).

The bench's first frame is the moment the opening scene hands the controls back, so a check's expectations count from
there; the simulator's clock starts with the mission, the scene runs ~79 s first. This runs the check's mission in the
simulator as it is -- the check's own order to the engineer builds the ice by the simulator's rules (R5: he walks
to the spot, the core; R1: the core leaves the wall, the wall melts; bench 2026-11-07 engine_life) -- shifts the
counters' readings back by the scene's length and judges the check's own expectations on them. What the simulator
has no rule for (a wall damaged, an engineer capturing) is scripted here or listed as SKIP -- never as PASS.

  python -I -X utf8 experimental/cnv/simbench.py [check ...]      -> PASS / FAIL for each, the verdict lines under it
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

LEVEL = 'a4'
SCENE = 'CNV_A4_Scene_1'     # the plan's flag: the opening scene is over (checks/a4.py AFTER)
REACH = 60.0                 # derrick: the engineer is this close to the derrick at the end of the run
REACH_RUN = 600.0


def after(secs):
    """A time in a script: `secs` after the opening scene is over (sim.parse_script's `<flag>+<time>`)."""
    return f'{SCENE}+{secs:g}'


NO_ENGINEER = ['0 删除 engineer']     # the mutation: no engineer from the start (the opening's demonstration ice too)


def nothing(m):
    return []


# check -> (the player's script as lines, the counters the simulator cannot read: each with the rule it lacks)
# A reading the simulator has no rule for is not a reading (a health of a reference nobody set is 0, which any
# "< 100" expectation takes for a hit): its expectations are listed as SKIP, never as PASS. The ice: the check's own
# order to the engineer (checks/a4.py ice_at), built by the simulator's rules R5 (he walks, the core) and R1 (it
# leaves the wall, the wall melts)
SPECS = {
    'detour': (nothing, {}),
    'queue': (nothing, {}),
    'smash': (nothing, {}),             # R2 (the reference to the nearest wall) + R3 (the ordered attack on it)
    'melt': (nothing, {}),
    'smoke': (lambda m: [], {}),
    'win': (lambda m: ['不打'], {}),
    'derrick': (nothing, {}),           # R4: the capture and the derrick's pay are the simulator's (bench 2026-11-07)
}
# win: the fight model off -- with it the check's top-up of the trucks (every frame, 15 a second) cannot hold against
# a 0.5 s tick of a dozen units' clips, and the trucks fall at 4:23 -- so the mission's wiring is judged, not the fight


# mission seconds a run goes on to (the scene's ~80 s, then the check's last expectation and a margin)
UNTIL = {'detour': 170.0, 'queue': 220.0, 'smash': 200.0, 'melt': 170.0, 'smoke': 150.0, 'win': 900.0,
         'derrick': 130.0}


def judged(t, blind):
    """The check's expectations, those on blind counters set aside: (the ones to judge, the SKIP lines)."""
    keep = [e for e in t.expect if e[0] not in blind]
    skip = [f'SKIP {e[0]}（{blind[e[0]]}）' for e in t.expect if e[0] in blind]
    return keep, skip


def run(check, script=None):
    """(status, lines): status 0 = every expectation the simulator can judge held on its readings. `script`: the
    player's lines in place of the check's own (a mutation: the player does nothing)."""
    import build
    import sim
    if check == 'derrick' and script is None:       # the check itself, then the walk to the map's own derricks
        status, lines = run(check, [])
        more, extra = reach()
        return status + more, lines + extra
    make, blind = SPECS[check]
    m, t, _ = build.resolve(LEVEL, check)
    s = sim.Sim(m, t, script=';'.join(make(m) if script is None else script)).run(UNTIL[check])
    gone = next((at for at, kind, text in s.log if kind == '过场' and text == '交还控制'), None)
    if gone is None:
        return 1, ['FAIL 开场过场没有交还控制：检查的时间对不上']
    off = int(round(gone))
    readings = [(sec - off, v) for sec, v in s.series if sec >= off]
    t.expect, skip = judged(t, blind)
    lines, status = build.report(t, readings)
    unknown = [f'不认识的动作：{k}×{v}' for k, v in s.unknown.items()]
    return status, [f'开场过场 {off} 秒结束，读数已按它前移', s.ending_line()] + lines + skip + unknown


def reach():
    """derrick: what the simulator can say of it -- not that capturing pays (the engine's: bench 2026-10-29, docs/design/
    flow/mechanics.md 工程师占油井), but that the player's engineer can walk from the start to each derrick the map
    holds (the cliff the first bench run stood on: an engineer 150 north of the start never moved)."""
    import build
    import sim
    m, t, _ = build.resolve(LEVEL, 'derrick')
    m.drop_endings()                    # the check keeps the plan's own: the trucks' loss ends the run at 2:31
    lines, status = [], 0
    for k, (x, y) in enumerate(m.map.DERRICKS):
        s = sim.Sim(m, t, script=f'{SCENE}+2 派 engineer 去 Derrick {k}')
        s.waypoints[f'Derrick {k}'] = (x, y)
        s.run(REACH_RUN)
        b = s.bodies[m.role('engineer').name]
        far = ((b.x - x) ** 2 + (b.y - y) ** 2) ** 0.5
        ok = far <= REACH
        status += not ok
        lines.append(f'{"PASS" if ok else "FAIL"} 工程师走到油井 {k} ({x:g}, {y:g})：{REACH_RUN:g} 秒后离它 {far:.0f}')
    return status, lines


def main():
    names = sys.argv[1:] or [*SPECS]
    bad = 0
    for name in names:
        status, lines = run(name)
        bad += bool(status)
        print(f'{"PASS" if not status else "FAIL"} {name}')
        print('\n'.join('    ' + x for x in lines))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
