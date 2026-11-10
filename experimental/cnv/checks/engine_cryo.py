"""Engine unit test: the freeze (SecondaryDamageTracker, ADR 0019 layer 3; engine line C round 7) -- how fast a cryo
beam freezes a tank, how long it stays frozen once the beam is gone. The simulator's rule (Sim.chill, INFERRED from the
SDK data, never benched): the cryocopter's beam adds 75 cold a second, the tracker melts 25 a second (BaseVehicle:
DissipateAmount 25 per UpdateDuration, cap 200 % of max health), the highest step reached by Fraction of max health
applies its modifier, 1.0 = UNDER_FROZEN (stopped, silent, armour CryoBeamFrozenArmor). For a Hammer (550 health):
frozen after 550 / (75 - 25) = 11 s of beam; kept to 200 % = 1100 cold, so after the beam ends it melts 25 a second.

On the Niagara map's west field (as engine_heal; the sim has no ground for probe_range): retail's cryocopter (AlliedSupportAircraft) and a retail Hammer (SovietAntiVehicleVehicleTech1,
the enemy's, NO_ATTACK so it only stands), ordered at ORDER to be attacked. The copter is deleted by script at STOP
(a beam that has run `STOP - ORDER` seconds). Variants (one a check; the idle copters are deleted at the start):
  one   one copter
  two   two copters (twice the beam)

Counters: 先冻 = frames from the order until UNDER_FROZEN is first seen; 冻住 = frames UNDER_FROZEN is set in all;
化冰 = of those, the frames after the copter was deleted (the melt time). The reading is the frame count the script
saw (docs/engine/weapons.md 1: one more than the frame it happened).

Bench 11-09 (round 7, first built on probe_range; work/bench_results/engine_cryo__<variant>.json keeps the latest run):
  one  先冻 139, 冻住 705, 化冰 334     two  先冻 79, 冻住 765, 化冰 334
-> frozen until 844 frames after the order whatever the beam (STOP + melt), melting 334 frames = (1100 - 550) / 25 a
second: the 200 % cap and the 25 a second are right. The simulator (Niagara) reads one 189 / 652 / 331, two 90 / 751 /
331: the same ending, a slower copter flight. tests/test_simbench.py::test_cryo_*.

Sim's answer (before the bench): one: 先冻 ~ 165 + the copter's flight (11 s of beam), then it melts (1100 - 550)/25 =
22 s when the beam ran long enough to fill the cap; two: 先冻 ~ 90 (550 / 125 = 4.4 s of beam).
"""
from maps import niagara
from model import status
from parts import Mission, Script, Test

COPTER, TANK = 'AlliedSupportAircraft', 'SovietAntiVehicleVehicleTech1'
ORDER, STOP, RUN = 6.0, 40.0, 90.0
VARIANTS = {'one': 1, 'two': 2}


def mission():
    m = Mission(name='CampCryo', map=niagara, units=[], facts={})
    m.put(TANK, 'west field', -120.0, 560.0, side='s1', role='cryo tank', name='UNIT - CNV Cryo Tank')
    for k in range(2):
        m.put(COPTER, 'west field', -180.0 + 120.0 * k, 160.0, side='p1', role=f'cryo copter {k}',
              name=f'UNIT - CNV Cryo Copter {k}')
    return m


def cryo_test(m, k):
    n = VARIANTS[k]
    t = Test()
    tank = m.role('cryo tank').name
    copters = [m.role(f'cryo copter {i}').name for i in range(2)]
    frozen = ('UNIT_HAS_OBJECT_STATUS', tank, status('UNDER_FROZEN'))
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('UNIT_CHANGE_OBJECT_STATUS', tank, 'NO_ATTACK', 1)]
    start += [('NAMED_DELETE', c) for c in copters[n:]]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER), ('SET_MILLISECOND_TIMER', 'Test Stop', STOP)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('NAMED_ATTACK_NAMED', c, tank) for c in copters[:n]] + [('SET_FLAG', 'Test Ordered', 1)]))
    t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'Test Stop')],
                            [('NAMED_DELETE', c) for c in copters[:n]] + [('SET_FLAG', 'Test Stopped', 1)]))
    t.scripts.append(Script('Test - seen', [frozen], [('SET_FLAG', 'Test Seen', 1)]))
    rows = [('CNV_Cryo_First', '先冻', [('FLAG', 'Test Ordered', 1), ('FLAG', 'Test Seen', 0)]),
            ('CNV_Cryo_Held', '冻住', [frozen]),
            ('CNV_Cryo_Melt', '化冰', [('FLAG', 'Test Stopped', 1), frozen])]
    for c, label, cond in rows:
        t.counters.append((c, label))
        t.scripts.append(Script(f'Test - {c}', cond, [('INCREMENT_COUNTER', 1, c)], once=False))
    t.expect = [('冻住', 0, 'ever>=', 1, RUN - 1)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_cryo': mission}
CHECKS = {'engine_cryo': {k: (lambda m, k=k: cryo_test(m, k)) for k in VARIANTS}}
