"""Engine unit test: status-bits upgrade module -- an upgrade the unit gets sets an ObjectStatus bit (engine line C round 10;
docs/engine/weaponset.md). Retail: the 30-odd unit templates carry the status-bits upgrade module (`StatusToSet=WEAPON_UPGRADED_0x`
`TriggeredBy Upgrade_Veterancy_HEROIC`) (mirage tank / conscript: _01, guardian: _02); the weapon sets then choose by that
bit (engine_weaponset). The simulator has the code (`simunits.status_bits`: the held upgrades' bits; INFERRED, never
read on the bench) and the probe asks four things: does the script's NAMED_RECEIVE_UPGRADE of the veterancy upgrade
set the bit, does it change the fire, does a late grant do the same from then on, does NAMED_REMOVE_UPGRADE take it back.

On the range probe map, one lane each (the lane names are the map's; the units are the probe's):
  base     mirage tank   no upgrade                                      (control)
  high     mirage tank   Upgrade_Veterancy_HEROIC at s0                  (_01 set: the Veteran cannon)
  order    mirage tank   Upgrade_Veterancy_HEROIC at LATE (8 s)          (the bit set in the middle of the fight)
  removed  mirage tank   HEROIC at s0, NAMED_REMOVE_UPGRADE at LATE      (is the bit cleared again?)
  switch   conscript     HEROIC at s0                                    (_01 set, nothing chooses by it: status only)
  low      guardian      HEROIC at s0                                    (_02 set, not _01: status only)
Each attacker is told at ORDER (3 s) to attack a Tsunami tank 100 north of it (the enemy's, NO_ATTACK, never answers).

Counters: a: 基准血 / 英雄血 / 晚血 / 去血 (the Tsunami's health in percent, base / high / order / removed lane, every
second); b: 英雄位 / 晚位 / 去位 -- 1 while the lane's mirage tank (high / order / removed) reads WEAPON_UPGRADED_01 via
UNIT_HAS_OBJECT_STATUS, else 0; 兵守位 = 1 x (conscript reads _01) + 10 x (guardian reads _02) + 100 x (guardian reads
_01, the wrong bit: should stay 0). Sampled every 0.5 s.

Bench 2026-11-09 (docs/engine/weaponset.md; StatusBitsUpgrade registered): b s1-s6 = 1 0 1 11, s7-s41 = 1 1 0 11 (the grant
sets the bit, a late grant sets it from then on, a removal clears it; the conscript reads _01, the guardian _02 and not
_01) -- as the simulator predicted. a = 47 34 47 34 from s1 on (the mirage tank's one shot: 200 / 250 of 380 hp, then
no more; the late grant came after the fight had stopped, so it changes nothing).
"""
from maps import probe_range
from parts import Mission, Script, Test, counted, status

CONSCRIPT, MIRAGE, GUARD, TANK = ('SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech3',
                                  'AlliedAntiVehicleVehicleTech1', 'JapanAntiVehicleVehicleTech1')
LANES = {'base': MIRAGE, 'high': MIRAGE, 'order': MIRAGE, 'removed': MIRAGE, 'switch': CONSCRIPT, 'low': GUARD}
HEROIC = 'Upgrade_Veterancy_HEROIC'
BIT = {'high': 'WEAPON_UPGRADED_01', 'order': 'WEAPON_UPGRADED_01', 'removed': 'WEAPON_UPGRADED_01',
       'switch': 'WEAPON_UPGRADED_01', 'low': 'WEAPON_UPGRADED_02'}
ORDER, LATE, RUN = 3.0, 8.0, 40.0


def _n(lane, part):
    return f'UNIT - CNV Sbits {lane.title()} {part}'


def mission():
    m = Mission(name='CampSbits', map=probe_range, units=[], facts={})
    for lane, tpl in LANES.items():
        m.put(tpl, f'{lane} gun', side='p1', role=f'{lane} attacker', name=_n(lane, 'Man'))
        m.put(TANK, f'{lane} gun', 0.0, 100.0, side='s1', role=f'{lane} tank', name=_n(lane, 'Tank'))
    return m


def statusbits_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    tanks = [_n(lane, 'Tank') for lane in LANES]
    early = [lane for lane in LANES if lane not in ('base', 'order')]
    t.scripts.append(Script('Test - start', [], [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1) for u in tanks] + [
        ('NAMED_RECEIVE_UPGRADE', HEROIC, _n(lane, 'Man')) for lane in early] + [
        ('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER),
        ('SET_MILLISECOND_TIMER', 'Test Late', LATE)]))
    t.scripts += [
        Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
               [('NAMED_ATTACK_NAMED', _n(lane, 'Man'), _n(lane, 'Tank')) for lane in LANES]),
        Script('Test - late', [('TIMER_EXPIRED', 'Test Late')],
               [('NAMED_RECEIVE_UPGRADE', HEROIC, _n('order', 'Man')),
                ('NAMED_REMOVE_UPGRADE', HEROIC, _n('removed', 'Man'))])]
    if which == 'a':
        for key, label in (('Base', '基准血'), ('High', '英雄血'), ('Order', '晚血'), ('Removed', '去血')):
            counted(f'CNV_Sbits_{key}Hp', label, t, health=_n(key, 'Tank'))
        t.expect = [('基准血', 0, 'ever<=', 99, RUN)]
    else:
        for key, label in (('High', '英雄位'), ('Order', '晚位'), ('Removed', '去位')):
            c = f'CNV_Sbits_{key}Bit'
            t.counters.append((c, label))
            t.scripts += [
                Script(f'Test - bit {key} zero', [], [('SET_COUNTER', c, 0)], once=False),
                Script(f'Test - bit {key} seen', [('UNIT_HAS_OBJECT_STATUS', _n(key, 'Man'), status(BIT[key.lower()]))],
                       [('SET_COUNTER', c, 1)], once=False)]
        t.counters.append(('CNV_Sbits_Other', '兵守位'))
        t.scripts += [Script('Test - bit other zero', [], [('SET_COUNTER', 'CNV_Sbits_Other', 0)], once=False)] + [
            Script(f'Test - bit other {k}', [('UNIT_HAS_OBJECT_STATUS', _n(lane, 'Man'), status(bit))],
                   [('INCREMENT_COUNTER', step, 'CNV_Sbits_Other')], once=False)
            for k, (lane, bit, step) in enumerate((('switch', 'WEAPON_UPGRADED_01', 1), ('low', 'WEAPON_UPGRADED_02', 10),
                                                   ('low', 'WEAPON_UPGRADED_01', 100)))]
        t.expect = [('英雄位', 0, 'ever>=', 0, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_statusbits': mission}
CHECKS = {'engine_statusbits': {'a': statusbits_test, 'b': lambda m: statusbits_test(m, 'b')}}
