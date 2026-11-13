"""E143: minimal CircularDamageUpdate consumer, land with no ONLY_ON_WATER flag.

Data prediction: Lifetime controls expansion, SweepWeapon supplies damage. Three
stationary Hammers at 50/100/150 from the carrier count frames to first damage;
the aimed Hammer at 450 receives only a 200 MAGIC shot marker. Checks a/b/c/d:
normal, remove activation, remove module, hold FiringDuration for Lifetime. This does not measure
retail water eligibility, moving centres, death, repeat activation or FX.
"""
from maps import probe_range
from parts import Mission, Script, Test
from checks.engine_shot import shot_v4, _nuggets
from checks.engine_missile import target, TARGET_ID, _sub1

ORDER, RUN = 8.0, 15.0
LABELS = ('近', '中', '远', '瞄')


def mission():
    return Mission(name='CampCircular', map=probe_range, units=[target()], ext=False)


def probe(m, activate=True, module=True, life=1.0, hold=False):
    hit = ('<WeaponTemplate id="CNV_CircleHit"><Nuggets>'
           '<DamageNugget Damage="500" DamageType="MAGIC" DeathType="NORMAL"/>'
           '</Nuggets></WeaponTemplate>')
    nuggets = ['<DamageNugget Damage="200" DamageType="MAGIC" DeathType="NORMAL"/>']
    if activate:
        nuggets.append(f'<ActivateCircularDamageNugget Lifetime="{life:g}s"/>')
    u = shot_v4('CNV_Circle', _nuggets(*nuggets), extra=hit, reload=6.0)
    if hold:
        u.xml = _sub1(u.xml, '<FiringDuration\n\t\t\tMinSeconds="0s"\n\t\t\tMaxSeconds="0s"',
                      '<FiringDuration MinSeconds="1s" MaxSeconds="1s"')
    if module:
        u.xml = _sub1(u.xml, '<Behaviors>', '''<Behaviors>
            <CircularDamageUpdate id="ModuleTag_Circle" MaxRadius="175" ArcDistance="50"
                SweepWeapon="CNV_CircleHit">
                <ObjectFilter Rule="ANY" Relationship="ENEMIES" Include="VEHICLE"/>
            </CircularDamageUpdate>''')
    u.link.append('WeaponTemplate:CNV_CircleHit')
    m.units.append(u)
    shooter = 'UNIT - Circle Source'
    m.put(u.id, 'base gun', side='p1', role='circle source', name=shooter)
    names = [f'UNIT - Circle Target {k}' for k in range(4)]
    for k, distance in enumerate((50.0, 100.0, 150.0, 450.0)):
        m.put(TARGET_ID, 'base gun', 0.0, distance, side='s1', role=f'circle target {k}', name=names[k])
    t = Test()
    t.scripts.append(Script('Test - Circle setup', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
                            + [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in [shooter] + names]
                            + [('SET_MILLISECOND_TIMER', 'Circle Order', ORDER)]))
    t.scripts.append(Script('Test - Circle order', [('TIMER_EXPIRED', 'Circle Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', shooter, 'NO_ATTACK', 0),
                             ('NAMED_ATTACK_NAMED', shooter, names[-1]), ('SET_FLAG', 'Circle Ordered', 1)]))
    for k, (name, label) in enumerate(zip(names, LABELS)):
        counter = f'CNV_Circle_{k}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - Circle count {k}', [('FLAG', 'Circle Ordered', 1),
                                                    ('UNIT_HEALTH', name, 2, 100)],
                                [('INCREMENT_COUNTER', 1, counter)], once=False))
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_circular': mission}
CHECKS = {'engine_circular': {'a': probe, 'b': lambda m: probe(m, activate=False),
                             'c': lambda m: probe(m, module=False), 'd': lambda m: probe(m, hold=True)}}
