"""Read target health, arrival, home and survival for the delayed-guard pair.

Model prediction before measurement: both thresholds retreat with target HP64;
the high lane still fails the model's reach predicate despite shooting.
The high-lane finishing expectation is the competing hypothesis, retained as
a diagnostic FAIL if disproved, never tuned to the measurement.

MEASURED: low target HP59, home4/live4; high HP34, home0/live0,
stable capture s39-55. High finishes neither target nor return: its original
kill expectation remains FAIL. Thresholds distinguish outcomes, but the
model retreats in both lanes (HP64/home3/live3); strict replay xfails and
GUESSED inventory remain. See work/re/c_alpha_close_report.md.
"""
from checks import engine_airetreat as ar
from parts import counted


def probe(m):
    t = ar.a(m, 'airet')
    counted('CNV_AlClose_HP', '目标血量', t, health=m.facts['alpha target'])
    t.expect = [('目标血量', 1, '==', 70, 29), ('到远厂', 15, 'ever>=', 1, 29)]
    if m.facts['alpha high']:
        t.expect.append(('目标血量', 30, 'ever<=', 1, 65))
    else:
        t.expect.append(('步兵在家', 35, 'ever>=', 1, 65))
    t.bench = [('bench_watch', dict(seconds=66, every=2, sheet=False, lines=4))]
    return t


def observe(m):
    """Check observer equivalence against the original measured plateaus.

    D81 fixed the observer overhead and added a shared logic-frame anchor.
    Record changes plus a one-second heartbeat to cover the guard/Alpha
    confrontation. Qualify both lanes before using their internal states;
    never shift the clock to fit the original bench. E99 reproduced both plateaus;
    the high lane required RA3_BENCH_SPEED=1 to sustain 15 logic frames per
    sampled second. See work/re/e99_alpha_observer.md.
    """
    t = probe(m)
    hp, home, live = (34, 0, 0) if m.facts['alpha high'] else (59, 4, 4)
    t.expect = [('目标血量', 1, '==', 70, 29), ('到远厂', 17, '==', 4, 27)]
    t.expect += [(label, 39, '==', value, 55) for label, value in
                 (('目标血量', hp), ('步兵在家', home), ('步兵数', live))]
    return t


CHECKS = {b: {'a': probe} for b in ('aialcloselo', 'aialclosehi')}
CHECKS.update({b: {'a': observe} for b in ('aialobslo', 'aialobshi')})
