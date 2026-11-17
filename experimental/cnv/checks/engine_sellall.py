"""PLAYER_SELL_EVERYTHING ownership/refund probe; work/re/c_sellall_report.md.

Before bench prediction: 3s empty Soviet_6, 5s sell target, 9s repeat.
Allied power plants cost 800: target receives 400 once; its plant carries
SOLD then disappears, all three Guardians and other owners' plants remain.
a targets Soviet_4; b targets Player_1. Counters: weighted balances
(p1 + 10*s4 + 100*s5), living mask (units 1/2/4, plants 8/16/32),
plant SOLD mask (1/2/4), logic frame. Initial 222000/63/0/frame;
predicted final a 226000/47/0/frame, b 222400/55/0/frame.
"""
from maps import probe_border
from parts import Mission, Script, Test, status
from checks import engine_scripts8 as s8

SIDES = ('p1', 's4', 's5')


def mission():
    m = Mission(name='CampSellAll', map=probe_border, units=[], facts={})
    for k, side in enumerate(SIDES):
        for kind, template, dx in (('unit', 'AlliedAntiVehicleVehicleTech1', 0.),
                                   ('plant', 'AlliedPowerPlant', 300.)):
            role = side+' '+kind
            m.put(template, 'stop row', -500.+k*1500.+dx, -2300., side=side,
                  role=role, name='CNV SellAll '+role)
    return m


def check(m, which):
    t = Test()
    target = 's4' if which == 'a' else 'p1'
    t.scripts.append(Script('Test - SellAll init', [], [
        ('PLAYER_SET_MONEY', m.player(side), 2000) for side in SIDES] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(side+' '+kind).name, status('NO_ATTACK'), 1)
        for side in SIDES for kind in ('unit', 'plant')]))
    s8.at(t, 'sell empty player', 3., [('PLAYER_SELL_EVERYTHING', m.player('s6'))])
    s8.at(t, 'sell target player', 5., [('PLAYER_SELL_EVERYTHING', m.player(target))])
    s8.at(t, 'sell target again', 9., [('PLAYER_SELL_EVERYTHING', m.player(target))])
    t.counters.append(('CNV_SA_Money', '资金码'))
    t.scripts.append(Script('Test - SellAll money', [], [
        ('SET_COUNTER', 'CNV_SA_Money', 0)] + [
        action for k, side in enumerate(SIDES) for action in (
            ('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), 'CNV_SA_Tmp'),
            ('COUNTER_MATH_VALUE', 'CNV_SA_Tmp', 2, 10**k),
            ('COUNTER_MATH_COUNTER', 'CNV_SA_Money', 0, 'CNV_SA_Tmp'))], once=False))
    s8.total(t, 'CNV_SA_Alive', '存活位', [
        (2**(k+3*j), ('NAMED_NOT_DESTROYED', m.role(side+' '+kind).name))
        for j, kind in enumerate(('unit', 'plant')) for k, side in enumerate(SIDES)])
    s8.total(t, 'CNV_SA_Sold', '出售位', [
        (2**k, ('UNIT_HAS_OBJECT_STATUS', m.role(side+' plant').name, status('SOLD')))
        for k, side in enumerate(SIDES)])
    s8.frames(t, 'CNV_SA_Frame', '逻辑帧', [])
    s8.watch(t, 16., .25)
    return t


MISSION = {'engine_sellall': mission}
CHECKS = {'engine_sellall': {w: (lambda m, w=w: check(m, w)) for w in 'ab'}}
