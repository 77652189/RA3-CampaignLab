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


def check_japan(m):
    """d: Allied spy vs enemy/allied retail JapanPowerPlant, each 100 energy.

    Same ENERGY/.2 configuration as a/c. Predict enemy consumption, unchanged
    plant HP/owner and ~20s outage; mutually allied plant refuses entry.
    Precise arrival and other energy amounts remain INFERRED.
    Bench 2026-11-11: s1-s10 11100/11100/101/101;
    s12-s30 1100/11100/12/101; s31-s60 1100/11100/101/101.
    Sample s11 absent; stable windows support approximately twenty seconds.
    """
    for role in ROLES:
        plant = m.role(role)
        plant.template = 'JapanPowerPlant'
        m.find(plant.name).template = plant.template
    return isolated_check(m)


DISABLER, PLANT, TOWER, TANK = ('EnergyDisabler', 'AlliedPowerPlant', 'AlliedBaseDefenseAdvanced',
                                'SovietAntiVehicleVehicleTech3')
RUN = {'e': 60, 'f': 70, 'g': 45, 'h': 50, 'i': 50, 'j': 60}


def plant(uid, amount='0.2', energy='100'):
    """Retail AlliedPowerPlant renamed, its ENERGY rule inlined with `amount` and its EnergyProduction `energy`."""
    import re
    from pathlib import Path
    import labpaths
    from parts import Unit
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures' / (PLANT + '.xml')).read_text(encoding='utf-8')
    for a, b in ((f'id="{PLANT}"', f'id="{uid}"'), (f'EditorName="{PLANT}"', f'EditorName="{uid}"'),
                 ('EnergyProduction="100"', f'EnergyProduction="{energy}"')):
        assert xml.count(a) == 1, a
        xml = xml.replace(a, b)
    xml, n = re.subn(r'<xi:include\s+href="DATA:Includes/InfiltratorContainEnergy.xml"\s*/>',
                     f'<InfiltratorContain id="ModuleTag_InfiltratorContain" Effect="ENERGY" Amount="{amount}" '
                     f'ObjectRef="{DISABLER}" StructureFilter="InfiltrationEnergyStructuresFilter" />', xml)
    assert n == 1, n
    return Unit(uid, xml)


def power_mission():
    """A6 (11-25): s1's lone grid -- a plant (+100) on 'power 1' and a spectrum tower (-75, POWERED) on the base lane;
    the player's Apocalypse 300 north of the tower (NO_ATTACK) and a spy by the plant."""
    m = Mission(name='CampInfPw', map=probe_range, units=[plant('CNV_InfPwHalf', amount='0.1'),
                                                         plant('CNV_InfPwDouble', energy='200')])
    m.spawns |= {DISABLER, DISABLER.lower()}
    m.put(PLANT, 'power 1', side='s1', role='plant', name='Spy plant')
    m.put(TOWER, 'base gun', side='s1', role='tower', name='Spy tower')
    m.put(TANK, 'base gun', 0, 300, role='tank', name='Spy tank')
    m.put('AlliedInfiltrationInfantry', 'power 1', 0, -180, role='spy', name='Spy man')
    return m


def power_check(m, v):
    """e spawn: 10 s CREATE_NAMED EnergyDisabler on s1's team, kept. f beat: the same every 20 s from 10 s, NAMED_DELETE
    6 s after each (a repeating TIMER_EXPIRED pair). g emp: NAMED_SET_DISABLED plant EMP 1 at 10 s, 0 at 25 s. h spy:
    the spy enters the plant at 10 s (retail). i: h with the plant's Amount 0.1; j: h with EnergyProduction 200.
    Lines: hits (frames the tank was hurt, healed back each time), power bits (excess 25 +1, 0 +2, <0 +4, no power
    +10, has power +100), s1's and the player's EnergyDisabler count."""
    t = Test()
    s1, p = m.player('s1'), m.player('p1')
    if v in 'ij':
        m.find('Spy plant').template = m.role('plant').template = 'CNV_InfPwHalf' if v == 'i' else 'CNV_InfPwDouble'
    t.waypoints['Test Disabler'] = (3300.0, 1700.0)
    made = ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'UNIT - Spy disabler', DISABLER, m.team('s1'), 'Test Disabler')
    go = {'e': [made],
          'f': [made, ('SET_MILLISECOND_TIMER', 'Spy beat', 20.0), ('SET_MILLISECOND_TIMER', 'Spy off', 6.0)],
          'g': [('NAMED_SET_DISABLED', 'Spy plant', 'EMP', 1), ('SET_MILLISECOND_TIMER', 'Spy off', 15.0)]}.get(
        v, [('NAMED_GARRISON_SPECIFIC_BUILDING', 'Spy man', 'Spy plant')])
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p), ('UNIT_CHANGE_OBJECT_STATUS', 'Spy tank', 'NO_ATTACK', 1),
        ('UNIT_CHANGE_OBJECT_STATUS', 'Spy man', 'NO_ATTACK', 1), ('SET_MILLISECOND_TIMER', 'Spy beat', 10.0)]),
        Script('Test - no repair budget', [], [('PLAYER_SET_MONEY', s1, 0)], once=False),
        Script('Test - beat', [('TIMER_EXPIRED', 'Spy beat')], go, once=v != 'f')]
    if v in 'fg':
        off = [('NAMED_DELETE', 'UNIT - Spy disabler')] if v == 'f' else [('NAMED_SET_DISABLED', 'Spy plant', 'EMP', 0)]
        t.scripts.append(Script('Test - off', [('TIMER_EXPIRED', 'Spy off')], off, once=v != 'f'))
    t.counters.append(('Spy hits', 'hits'))
    t.scripts.append(Script('Test - hit', [('UNIT_HEALTH', 'Spy tank', 0, 100)],
                            [('INCREMENT_COUNTER', 1, 'Spy hits'), ('UNIT_SET_HEALTH', 'Spy tank', 100.0)], once=False))
    t.counters.append(('Spy power', 'power'))
    t.scripts.append(Script('Test - reset power', [], [('SET_COUNTER', 'Spy power', 0)], once=False))
    for k, (cond, value) in enumerate(((('PLAYER_EXCESS_POWER_COMPARE_VALUE', s1, 2, 25), 1),
                                       (('PLAYER_EXCESS_POWER_COMPARE_VALUE', s1, 2, 0), 2),
                                       (('PLAYER_EXCESS_POWER_COMPARE_VALUE', s1, 0, 0), 4),
                                       (('PLAYER_HAS_NO_POWER', s1), 10), (('PLAYER_HAS_POWER', s1), 100))):
        t.scripts.append(Script(f'Test - power {k}', [cond], [('INCREMENT_COUNTER', value, 'Spy power')], once=False))
    counted('Spy dis s1', 'disabler s1', t, template=DISABLER, player=s1)
    counted('Spy dis p1', 'disabler p1', t, template=DISABLER, player=p)
    t.bench = [('bench_watch', dict(seconds=RUN[v], every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_infiltrator': mission, 'engine_infilpow': power_mission}
CHECKS = {'engine_infiltrator': {'a': check, 'b': check_ninja, 'c': check_soviet, 'd': check_japan},
          'engine_infilpow': {v: (lambda m, v=v: power_check(m, v)) for v in RUN}}
