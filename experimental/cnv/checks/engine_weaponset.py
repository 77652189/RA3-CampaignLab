"""Engine unit test: weapon-set module -- which weapon a unit fires when the weapon's ObjectStatus / ForbiddenObjectStatus
say so (engine line C round 9; docs/engine/weaponset.md). Retail writes the choice into the module: a Conscript's AK47
is forbidden under GENERIC_TOGGLE_STATE and its Molotov needs it; a Guardian's cannon is forbidden under the toggle and
its target painter (no damage) needs it; a mirage tank's cannon is replaced by the _Veteran one under WEAPON_UPGRADED_01.
The simulator read the first PRIMARY_WEAPON of each slot whatever the status.

On the range probe map, one lane each, an attacker of the player's at '<lane> gun' and a Tsunami tank of the enemy's
(JapanAntiVehicleVehicleTech1, held NO_ATTACK so it never answers) 100 north. At ORDER the attacker is told to attack it:

  base     conscript   plain (AK47)
  high     conscript   GENERIC_TOGGLE_STATE from the start (Molotov)
  order    conscript   plain; GENERIC_TOGGLE_STATE given at TOGGLE (the weapon changes in the middle of the fight)
  removed  mirage      plain (the prism cannon)
  switch   mirage      WEAPON_UPGRADED_01 from the start (the Veteran cannon)
  low      guardian    GENERIC_TOGGLE_STATE from the start (the cannon is forbidden, the target painter does no damage)

Counters: a: 基准血 / 毒瓶血 / 中途血 (the Tsunami's health in percent of the base / high / order lane); b: 棱镜血 /
老兵血 / 涂靶血 (removed / switch / low lane). Every second.

Bench: see the docstring's end (filled in when read).
"""
from maps import probe_range
from parts import Mission, Script, Test, counted

CONSCRIPT, MIRAGE, GUARD, TANK = ('SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech3',
                                  'AlliedAntiVehicleVehicleTech1', 'JapanAntiVehicleVehicleTech1')
LANES = {'base': CONSCRIPT, 'high': CONSCRIPT, 'order': CONSCRIPT, 'removed': MIRAGE, 'switch': MIRAGE, 'low': GUARD}
START_STATUS = {'high': 'GENERIC_TOGGLE_STATE', 'switch': 'WEAPON_UPGRADED_01', 'low': 'GENERIC_TOGGLE_STATE'}
ORDER, TOGGLE, RUN = 3.0, 12.0, 40.0


def _n(lane, part):
    return f'UNIT - CNV Wset {lane.title()} {part}'


def mission():
    m = Mission(name='CampWset', map=probe_range, units=[], facts={})
    for lane, tpl in LANES.items():
        m.put(tpl, f'{lane} gun', side='p1', role=f'{lane} attacker', name=_n(lane, 'Man'))
        m.put(TANK, f'{lane} gun', 0.0, 100.0, side='s1', role=f'{lane} tank', name=_n(lane, 'Tank'))
    return m


def weaponset_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    tanks = [_n(lane, 'Tank') for lane in LANES]
    t.scripts.append(Script('Test - start', [], [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1) for u in tanks] + [
        ('UNIT_CHANGE_OBJECT_STATUS', _n(lane, 'Man'), st, 1) for lane, st in START_STATUS.items()] + [
        ('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER),
        ('SET_MILLISECOND_TIMER', 'Test Toggle', TOGGLE)]))
    t.scripts += [
        Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
               [('NAMED_ATTACK_NAMED', _n(lane, 'Man'), _n(lane, 'Tank')) for lane in LANES]),
        Script('Test - toggle', [('TIMER_EXPIRED', 'Test Toggle')],
               [('UNIT_CHANGE_OBJECT_STATUS', _n('order', 'Man'), 'GENERIC_TOGGLE_STATE', 1)])]
    lines = ((('Base', '基准血'), ('High', '毒瓶血'), ('Order', '中途血')) if which == 'a' else
             (('Removed', '棱镜血'), ('Switch', '老兵血'), ('Low', '涂靶血')))
    for key, label in lines:
        counted(f'CNV_Wset_{key}Hp', label, t, health=_n(key, 'Tank'))
    t.expect = [(lines[0][1], 0, 'ever<=', 99, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_weaponset': mission}
CHECKS = {'engine_weaponset': {'a': weaponset_test, 'b': lambda m: weaponset_test(m, 'b')}}
