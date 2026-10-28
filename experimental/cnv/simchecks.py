r"""The bench checks that are wiring only -- what the scripts do with what the player did, not what the engine does
(a fight, a wall that bars, an AI that builds) -- in the plan simulator's version (sim.py): run in seconds on every
plan edit; the bench versions stay for the engine and for the last alignment.

Each: (level, check) -> what the player does (the simulator's script; the check's own test scripts run too), the
ending it must come to ('赢' / '输' / None: none within the run), and whether the check's own counter expectations
hold too (counters: only where they are wiring; mission seconds, as the bench's since 4aed60f). Checks left out
lean on the engine (sim.ALIGN lists what the simulator only assumes).

  python -I -X utf8 experimental/cnv/simchecks.py            -> one line each, PASS / FAIL
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

UNTIL = 900.0

CHECKS = {
    # A4: the stops, the harbour cleared, the ambushes out of the sculptures on time (the check's scripts act)
    ('a4', 'stop'): dict(script='', ending=None, counters=True),
    # (不打: the fight model off -- these test the scripts' wiring, not who wins a fight; with it the ambush takes
    # the trucks and the level is lost before the counters are read)
    ('a4', 'harbour'): dict(script='不打', ending=None, counters=True),
    ('a4', 'placed'): dict(script='', ending=None, counters=True),
    ('a4', 'smash'): dict(script='不打', ending=None, counters=True),
    ('a4', 'ambush'): dict(script='不打', ending=None, counters=True),
    # A5: the gates hold the fleet till the guards are dead, then it sails and two at the sea win
    ('a5', 'hold'): dict(script='', ending=None, counters=True),
    ('a5', 'win'): dict(script='', ending='赢', counters=True),
    # A7: the nag repeats, the gate's guard is reinforced on revenge and on the pincer
    ('a7', 'nag'): dict(script='', ending=None, counters=True),
    ('a7', 'revenge'): dict(script='', ending=None, counters=True),
    ('a7', 'pincer'): dict(script='', ending=None, counters=True),
    # J3: led round the hill and up the back way, out again -- won; Yuriko down -- lost
    ('j3', 'run'): dict(script='', ending='赢', counters=True),
    ('j3', 'lose'): dict(script='30 摧毁 yuriko', ending='输', counters=False),
    # J4: nothing done, the convoy reaches the exit -- lost
    ('j4', 'lose'): dict(script='', ending='输', counters=True),
    # J5: held to the end -- won; Yuriko down -- lost
    ('j5', 'hold'): dict(script='不打', ending='赢', counters=False),     # the check heals every frame, a tick
                                                                         # (0.5 s) of the fight is more
    ('j5', 'lose'): dict(script='60 摧毁 yuriko', ending='输', counters=False),
    # J7: the tower razed -- won at once; nothing done, the countdown out -- lost
    ('j7', 'win'): dict(script='', ending='赢', counters=False),
    ('j7', 'late'): dict(script='', ending='输', counters=False),
    # S2: the cryo train stopped at the river station -- won; nothing done, it gets away -- lost
    ('s2', 'catch'): dict(script='', ending='赢', counters=True),
    ('s2', 'escape'): dict(script='', ending='输', counters=True),
    # S5: the control room taken, the gates shut, the fleet held, the hold out -- won; nothing done -- lost
    ('s5', 'trap'): dict(script='', ending='赢', counters=True),
    ('s5', 'escape'): dict(script='', ending='输', counters=False),
    # S6: held to the launch -- won; the tower razed -- lost
    ('s6', 'hold'): dict(script='', ending='赢', counters=False),
    ('s6', 'lose'): dict(script='120 摧毁 launch tower', ending='输', counters=False),
}


def run(level, check):
    """(passed, lines) for one check's simulator version."""
    import build
    import sim
    spec = CHECKS[(level, check)]
    m, t, _ = build.resolve(level, check)
    s = sim.Sim(m, t, script=spec['script']).run(UNTIL)
    lines, ok = [s.ending_line()], True
    got = s.ending[0] if s.ending else None
    if got != spec['ending']:
        ok = False
        lines.append(f'FAIL 结局应该是 {spec["ending"] or "不结束"}，推演是 {got or "不结束"}')
    if spec['counters'] and t.expect:
        judged, status = build.report(t, s.series)
        lines += judged
        ok = ok and status == 0
    return ok, lines


def main():
    bad = 0
    for level, check in CHECKS:
        ok, lines = run(level, check)
        bad += not ok
        print(f'{"PASS" if ok else "FAIL"} {level} {check}: {lines[0]}')
        for x in lines[1:]:
            if x.startswith('FAIL'):
                print('   ', x)
    print(f'{len(CHECKS) - bad}/{len(CHECKS)} passed')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
