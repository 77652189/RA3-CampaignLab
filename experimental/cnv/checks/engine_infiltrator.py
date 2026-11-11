"""Retail Allied spy enters an enemy power plant; allied plant is refused.

InfiltratorContainEnergy declares ENERGY, Amount=0.2 and EnergyDisabler.
Its default enter filter admits Allied/Japan spies, ENEMIES only. The schema
says the engine overrides the disabler's lifetime; duration is to be measured.
Rows 1/2: plant HP% + 1000 original owner + 10000 living spy.
Rows 3/4: excess=100 (+1), excess=0 (+2), excess<0 (+4), no power (+10),
has power (+100).
Bench 2026-11-10: s1-s10 11100/11100/101/101;
s11-s30 1100/11100/12/101; s31-s56 1100/11100/101/101.
Twenty seconds disabled for the single 100-energy plant; scaling unmeasured.
"""
from maps import probe_range
from parts import Mission, Script, Test, counted

ROLES = ('enemy', 'ally')


def mission():
    m = Mission(name='CampInfil', map=probe_range, units=[])
    for role, lane, side in (('enemy', 'base', 's1'), ('ally', 'high', 's2')):
        m.put('AlliedPowerPlant', lane + ' gun', side=side, role=role, name='Spy plant ' + role)
        m.put('AlliedInfiltrationInfantry', lane + ' gun', 0, -180,
              role=role + ' spy', name='Spy man ' + role)
    return m


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Spy enter', 10.0)]),
        Script('Test - enter', [('TIMER_EXPIRED', 'Spy enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name, m.role(role).name)
            for role in ROLES])]
    for role, side in zip(ROLES, ('s1', 's2')):
        c, plant, spy = 'Spy ' + role, m.role(role).name, m.role(role + ' spy').name
        counted(c, role, t, health=plant)
        for label, cond, value in (
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), plant), 1000),
                ('alive', ('NAMED_NOT_DESTROYED', spy), 10000)):
            t.scripts.append(Script('Test - ' + role + label, [cond],
                                    [('INCREMENT_COUNTER', value, c)], once=False))
    for role, side in zip(ROLES, ('s1', 's2')):
        c, player = 'Power ' + role, m.player(side)
        t.counters.append((c, role + ' power'))
        t.scripts.append(Script('Test - reset ' + c, [], [('SET_COUNTER', c, 0)], once=False))
        for k, (cond, value) in enumerate((
                (('PLAYER_EXCESS_POWER_COMPARE_VALUE', player, 2, 100), 1),
                (('PLAYER_EXCESS_POWER_COMPARE_VALUE', player, 2, 0), 2),
                (('PLAYER_EXCESS_POWER_COMPARE_VALUE', player, 0, 0), 4),
                (('PLAYER_HAS_NO_POWER', player), 10),
                (('PLAYER_HAS_POWER', player), 100))):
            t.scripts.append(Script(f'Test - {c} {k}', [cond],
                                    [('INCREMENT_COUNTER', value, c)], once=False))
    t.expect = [('enemy', 15, '==', 1100), ('ally', 0, '==', 11100),
                ('enemy power', 0, '==', 101, 7),
                ('enemy power', 15, '==', 12, 27),
                ('enemy power', 35, '==', 101), ('ally power', 0, '==', 101)]
    t.bench = [('bench_watch', dict(seconds=55, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_infiltrator': mission}


def check_ninja(m):
    """b: retail ninja ENERGY entry, enemy vs mutually allied plant.

    Same distance and isolated 100-energy grids as a. Disable firing and
    computer budgets so the ninja's weapons and repair cannot affect HP.
    Bench 2026-11-11: s1-s9 11100/11100/101/101;
    s10-s29 1100/11100/12/101; s30-s56 1100/11100/101/101.
    Twenty-second enemy outage; ally refused. Exact entry remains INFERRED.
    """
    for role in ROLES:
        spy = m.role(role + ' spy')
        spy.template = 'JapanInfiltrationInfantry'
        m.find(spy.name).template = spy.template
    return isolated_check(m)


def isolated_check(m):
    """No firing or AI repairs on either isolated grid."""
    t = check(m)
    t.scripts[0].do += [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(name).name, 'NO_ATTACK', 1)
        for role in ROLES for name in (role, role + ' spy')]
    t.scripts.insert(1, Script('Test - no repair budget', [], [
        ('PLAYER_SET_MONEY', m.player(side), 0) for side in ('s1', 's2')], once=False))
    return t


def check_soviet(m):
    """c: Allied spy vs enemy/allied retail SovietPowerPlant, each 100 energy.

    Same ENERGY/.2 configuration and enter filter as AlliedPowerPlant.
    Predict consumed enemy spy, unchanged plant HP/owner and ~20s outage;
    mutually allied plant refuses entry. Scaling/precise arrival INFERRED.
    Bench 2026-11-11: s1-s10 11100/11100/101/101;
    s11-s30 1100/11100/12/101; s31-s56 1100/11100/101/101.
    """
    for role in ROLES:
        plant = m.role(role)
        plant.template = 'SovietPowerPlant'
        m.find(plant.name).template = plant.template
    return isolated_check(m)


CHECKS = {'engine_infiltrator': {'a': check, 'b': check_ninja, 'c': check_soviet}}
