"""Engine unit test: the Athena cannon's real damage (OCL strike: AlliedAntiStructureVehicle -> OCL_AthenaCannon ->
a CannonEffect object that fires AthenaCannonWeapon after 0.1 s and again when it dies at 2 s).

Niagara map, 'west field': a player Athena and an enemy (s1) Soviet advanced power plant (MaxHealth 4000,
SovietAdvancedPowerPlantArmor -> BaseFactionStructureArmor: EXPLOSIVE 125 %), 300 apart (weapon range 200-500). One
second in the Athena is ordered to attack it. Counters: 帧数 frames since Go, 血量 the building's health in percent
(1 % = 40 hp).

Read 2026-11-08 (`a`, PASS): first loss at frame 49; each round takes ~19 % (750 hp = ~600 raw) over ~30 frames (the
effect's 2 s, a hit every frame), rounds start at frames 49 / 125 / 207 / 284 / 360 (~80 frames = ~5.3 s = pre-attack 2
+ firing 2 + reload 1.1). simunits.ocl_round gives 620 a round, the fight 121.6 raw/s (bench ~113).
"""
import resources
from maps import niagara
from parts import Mission, Script, Test

ATHENA, BARRACKS = 'AlliedAntiStructureVehicle', 'SovietPowerPlantAdvanced'
RUN = 40.0
SITE = ('west field', -120.0, 260.0)


def _n(p):
    return f'UNIT - CNV Ocl {p}'


def mission():
    m = Mission(name='CampOcl', map=resources.measured(niagara), units=[], facts={})
    m.put(ATHENA, SITE[0], SITE[1], SITE[2], angle=0.0, role='athena', name=_n('Athena'))
    m.put(BARRACKS, SITE[0], SITE[1], SITE[2] + 300.0, side='s1', angle=0.0, role='barracks', name=_n('Barracks'))
    return m


def ocl_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                                 ('UNIT_CHANGE_OBJECT_STATUS', _n('Barracks'), 'NO_ATTACK', 1),
                                                 ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                            [('NAMED_ATTACK_NAMED', _n('Athena'), _n('Barracks')), ('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.counters.append(('CNV_Ocl_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Ocl_Frames')], once=False))
    t.counters.append(('CNV_Ocl_Health', '血量'))
    t.scripts.append(Script('Test - health', [going], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', _n('Barracks'),
                                                        'CNV_Ocl_Health')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_ocl': mission}
CHECKS = {'engine_ocl': {'a': lambda m: ocl_test(m, 'a')}}
