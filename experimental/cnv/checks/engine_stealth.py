"""Engine unit test: stealth and detection (ADR 0019 layer 2; docs/engine/stealth.md) -- the mirage tank's aura, a
garrisoned building's stealth, a scout's detection, and what an attack order does against a hidden target.

On the range probe map, one lane each. In every lane a Guardian tank of the player's (AlliedAntiVehicleVehicleTech1,
480 health) at '<lane> gun', a mirage tank of the player's (AlliedAntiVehicleVehicleTech3: InvisibilityBroadcastUpdate
175, 0.2 s, while it carries GENERIC_TOGGLE_STATE) 100 south of it, and an enemy Tsunami tank (JapanAntiVehicleVehicleTech1) 150 north. Everybody is held
with NO_ATTACK; the mirage tanks are UNATTACKABLE as well (a tank that may not shoot its target takes the next).
At ORDER the Tsunamis are freed and told to attack the Guardian (the house in the low lane). The aura is switched by
script (UNIT_CHANGE_OBJECT_STATUS GENERIC_TOGGLE_STATE):

  base     aura     on throughout
  high     plain    off throughout (the Tsunami's pace against a Guardian)
  order    toggle   on; ACT off; ACT2 on again
  removed  scout    on, and an enemy Soviet scout (SovietScoutInfantry: StealthDetectorUpdate 301, 0.4 s) 150 east
                    of the Guardian; ACT the scout deleted
  switch   late     off; ACT on (the Tsunami has been shooting since ORDER)
  low      houses   no tanks: two of retail's AM_Apartments_01 600 apart (InvisibilityBehavior with
                    StealthGarrisonInvisibilityTemplate: RequiredStatus GARRISON_CAN_STEALTH), a conscript of the
                    player's into each at GARRISON; HIDE the west one given GARRISON_CAN_STEALTH; a Tsunami at each

Counters (four lines fit; two checks read different lanes, the mission is the same):
  a: 隐形位  STEALTHED on the base Guardian (1), the order Guardian (10), the hidden house (100), the scout lane's
             Guardian (1000); 光环血 / 对照血 / 开关血 the base / high / order Guardian's health in percent
  b: 揭露血 / 后隐血 the removed / switch Guardian's; 隐楼血 / 明楼血 the hidden / plain house's

  c: 探测位  DETECTED (1), INVISIBLE_DETECTED (10), INVISIBLE_DETECTED_BY_FRIEND (100) on the scout lane's Guardian,
             BROADCASTING_INVISIBILITY on the base mirage (1000); 楼位 GARRISON_CAN_STEALTH on the hidden (1) / plain
             (10) house, STEALTHED on the hidden house (100), ENCLOSED on its conscript (1000); 开关位
             GENERIC_TOGGLE_STATE on the switch / order / base mirage (1 / 10 / 100), BROADCASTING_INVISIBILITY on
             the switch one (1000); 揭露血. Every 0.5 s.  d: c with the order at 9 s.

Bench 11-05 (round 40; the bench's seconds ~1 s ahead of the timers; docs/engine/stealth.md):
  a CampStealthA_mcp_1105_185256: 隐形位 0 throughout; 光环血 100; 对照血 91 at s4 .. 4; 开关血 95 at s10 .. 54 from s15.
  b CampStealthB_mcp_1105_185454: 揭露血 95 at s6 .. 66 from s10; 后隐血 95 at s4 .. 50 from s10; 隐楼血 = 明楼血
    (98 at s4 .. 45).
  c CampStealthC_mcp_1105_185830: 探测位 10 from s5.2 to s9; 楼位 1000 -> 1001; 开关位 110 -> 101 (s9) -> 111 (s15).
  d CampStealthD_mcp_1105_190133: 探测位 10 from s5.2 again; 揭露血 95 at s8.
So against the model (RA3-EngineModel stealth.py, round 38; tools/objsidebyside.py --weapons;
tests/test_objects_bench.py): the aura by script, the order kept on a hidden target and the fire stopping when it
hides agree; the scout reveals only from ~6 s into the mission (the model: its first scan), GARRISON_CAN_STEALTH by
script does not hide the house (the model: hidden), STEALTHED / BROADCASTING_INVISIBILITY never read (the model sets
both), INVISIBLE_DETECTED does (the model never) -- three strict xfails.
Round 42 (read how the manager applies its result): the state is re-evaluated only by an entry, a detector's mark
or something running out, never by a script's status change; INVISIBLE_DETECTED only on hidden -> visible; neither
STEALTHED nor BROADCASTING_INVISIBILITY is set. The model now agrees on all three (the scout's case with the bench's
draw: its first scan before the aura's first pass); one strict xfail left: the scout lane stops one shot later.
"""
from maps import probe_range
from model import status
from parts import Mission, Script, Test, counted

GUARD, MIRAGE, TANK, SCOUT = ('AlliedAntiVehicleVehicleTech1', 'AlliedAntiVehicleVehicleTech3',
                                'JapanAntiVehicleVehicleTech1', 'SovietScoutInfantry')
HOUSE, MAN = 'AM_Apartments_01', 'SovietAntiInfantryInfantry'
GARRISON, HIDE, ORDER, ACT, ACT2, RUN = 2.0, 3.0, 5.0, 11.0, 17.0, 24.0
TANK_LANES = ('base', 'high', 'order', 'removed', 'switch')
AURA_AT_START = ('base', 'order', 'removed')
HOUSES = {'hidden': 0.0, 'plain': 600.0}       # the low lane's two houses, dx from its gun


def _n(lane, part):
    return f'UNIT - CNV Stealth {lane.title()} {part}'


def mission():
    m = Mission(name='CampStealth', map=probe_range, units=[], facts={})
    for lane in TANK_LANES:
        site = f'{lane} gun'
        m.put(GUARD, site, side='p1', role=f'{lane} guardian', name=_n(lane, 'Guardian'))
        m.put(MIRAGE, site, 0.0, -100.0, side='p1', role=f'{lane} mirage', name=_n(lane, 'Mirage'))
        m.put(TANK, site, 0.0, 150.0, side='s1', role=f'{lane} tank', name=_n(lane, 'Tank'))
    m.put(SCOUT, 'removed gun', 150.0, 0.0, side='s1', role='removed scout', name=_n('removed', 'Scout'))
    for h, dx in HOUSES.items():
        m.put(HOUSE, 'low gun', dx, 0.0, side='civ', role=f'{h} house', name=_n(h, 'House'))
        m.put(MAN, 'low gun', dx, -100.0, side='p1', role=f'{h} man', name=_n(h, 'Man'))
        m.put(TANK, 'low gun', dx, 150.0, side='s1', role=f'{h} tank', name=_n(h, 'Tank'))
    return m


def _aura(lane, on):
    return ('UNIT_CHANGE_OBJECT_STATUS', _n(lane, 'Mirage'), 'GENERIC_TOGGLE_STATE', 1 if on else 0)


def _bits(t, c, label, rows):
    """One counter line: the step added while that object carries that status (rows: (step, lane, part, status))."""
    t.counters.append((c, label))
    t.scripts.append(Script(f'Test - {c} zero', [], [('SET_COUNTER', c, 0)], once=False))
    t.scripts += [Script(f'Test - {c} {k}', [('UNIT_HAS_OBJECT_STATUS', _n(lane, part), status(st))],
                         [('INCREMENT_COUNTER', step, c)], once=False) for k, (step, lane, part, st) in enumerate(rows)]


def stealth_test(m, which='a', order=ORDER):
    t = Test()
    p1 = m.player('p1')
    tanks = [_n(lane, 'Tank') for lane in TANK_LANES] + [_n(h, 'Tank') for h in HOUSES]
    held = ([_n(lane, p) for lane in TANK_LANES for p in ('Guardian', 'Mirage')] + tanks + [_n('removed', 'Scout')]
            + [_n(h, p) for h in HOUSES for p in ('House', 'Man')])
    t.scripts.append(Script('Test - start', [], [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1) for u in held] + [
        ('UNIT_CHANGE_OBJECT_STATUS', _n(lane, 'Mirage'), 'UNATTACKABLE', 1) for lane in TANK_LANES] + [
        _aura(lane, True) for lane in AURA_AT_START] + [
        ('MAP_REVEAL_ALL_PERM', p1)] + [
        ('SET_MILLISECOND_TIMER', f'Test {k}', v) for k, v in
        (('Garrison', GARRISON), ('Hide', HIDE), ('Order', order), ('Act', ACT), ('Act2', ACT2))]))
    targets = [(_n(lane, 'Tank'), _n(lane, 'Guardian')) for lane in TANK_LANES] + [
        (_n(h, 'Tank'), _n(h, 'House')) for h in HOUSES]
    t.scripts += [
        Script('Test - garrison', [('TIMER_EXPIRED', 'Test Garrison')],
               [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', _n(h, 'Man'), _n(h, 'House')) for h in HOUSES]),
        Script('Test - hide', [('TIMER_EXPIRED', 'Test Hide')],
               [('UNIT_CHANGE_OBJECT_STATUS', _n('hidden', 'House'), 'GARRISON_CAN_STEALTH', 1)]),
        Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
               [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 0) for u in tanks]
               + [('NAMED_ATTACK_NAMED', a, b) for a, b in targets]),
        Script('Test - act', [('TIMER_EXPIRED', 'Test Act')],
               [_aura('order', False), _aura('switch', True), ('NAMED_DELETE', _n('removed', 'Scout'))]),
        Script('Test - act2', [('TIMER_EXPIRED', 'Test Act2')], [_aura('order', True)])]
    if which == 'a':
        _bits(t, 'CNV_Stealth_Bits', '隐形位', [(1, 'base', 'Guardian', 'STEALTHED'), (10, 'order', 'Guardian', 'STEALTHED'),
                                              (100, 'hidden', 'House', 'STEALTHED'),
                                              (1000, 'removed', 'Guardian', 'STEALTHED')])
        lines = (('Base', '光环血', _n('base', 'Guardian')), ('High', '对照血', _n('high', 'Guardian')),
                 ('Order', '开关血', _n('order', 'Guardian')))
    elif which == 'b':
        lines = (('Removed', '揭露血', _n('removed', 'Guardian')), ('Switch', '后隐血', _n('switch', 'Guardian')),
                 ('Hidden', '隐楼血', _n('hidden', 'House')), ('Plain', '明楼血', _n('plain', 'House')))
    else:                                   # c: the bits the scout, the script and the aura leave
        _bits(t, 'CNV_Stealth_Seen', '探测位', [(1, 'removed', 'Guardian', 'DETECTED'),
                                              (10, 'removed', 'Guardian', 'INVISIBLE_DETECTED'),
                                              (100, 'removed', 'Guardian', 'INVISIBLE_DETECTED_BY_FRIEND'),
                                              (1000, 'base', 'Mirage', 'BROADCASTING_INVISIBILITY')])
        _bits(t, 'CNV_Stealth_House', '楼位', [(1, 'hidden', 'House', 'GARRISON_CAN_STEALTH'),
                                             (10, 'plain', 'House', 'GARRISON_CAN_STEALTH'),
                                             (100, 'hidden', 'House', 'STEALTHED'),
                                             (1000, 'hidden', 'Man', 'ENCLOSED')])
        _bits(t, 'CNV_Stealth_Aura', '开关位', [(1, 'switch', 'Mirage', 'GENERIC_TOGGLE_STATE'),
                                              (10, 'order', 'Mirage', 'GENERIC_TOGGLE_STATE'),
                                              (100, 'base', 'Mirage', 'GENERIC_TOGGLE_STATE'),
                                              (1000, 'switch', 'Mirage', 'BROADCASTING_INVISIBILITY')])
        lines = (('Removed', '揭露血', _n('removed', 'Guardian')),)
    for key, label, u in lines:
        counted(f'CNV_Stealth_{key}Hp', label, t, health=u)
    first = {'a': '对照血', 'b': '明楼血', 'c': '揭露血'}[which]     # the Tsunami hits what it sees
    t.expect = [(first, 0, 'ever<=', 99, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=0.5 if which == 'c' else 1, sheet=False,
                                    lines=len(t.counters)))]
    return t


MISSION = {'engine_stealth': mission}
CHECKS = {'engine_stealth': {'a': stealth_test,                    # the mod's name CampStealthA: 12 characters
                             'b': lambda m: stealth_test(m, 'b'), 'c': lambda m: stealth_test(m, 'c'),
                             'd': lambda m: stealth_test(m, 'c', order=9.0)}}   # c with the order 4 s later
