"""PLAYER_KILL ownership contrast; evidence: work/re/c_playerkill_report.md.

Prediction before bench: at 5s kill Soviet_4, leaving Player_1/Soviet_5
units and buildings alive (masks 7 -> 5). Kill empty Soviet_6 at 3s;
repeat Soviet_4 at 9s. Four displayed counters: unit alive mask,
building alive mask, dying mask (units bits 1/2/4, buildings 8/16/32),
logic frame. No player defeat condition exists in script_catalog.json;
object death is the measured slice, player elimination remains a gap.
MEASURED A: f45/61/75 7/7/0/frame; f83/152/287 5/5/0/frame.
"""
from maps import probe_border
from parts import Mission, Script, Test, status
from checks import engine_scripts8 as s8

SIDES = ('p1', 's4', 's5')


def mission():
    m = Mission(name='CampPlayerKill', map=probe_border, units=[], facts={})
    for k, side in enumerate(SIDES):
        for kind, template, dx in (('unit', 'AlliedAntiVehicleVehicleTech1', 0.),
                                   ('plant', 'SovietPowerPlant', 300.)):
            role = side+' '+kind
            m.put(template, 'stop row', -500.+k*1500.+dx, -2300., side=side,
                  role=role, name='CNV PlayerKill '+role)
    return m


def check(m):
    t = Test()
    t.scripts.append(Script('Test - PlayerKill hold', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(side+' '+kind).name, status('NO_ATTACK'), 1)
        for side in SIDES for kind in ('unit', 'plant')]))
    s8.at(t, 'kill empty player', 3., [('PLAYER_KILL', m.player('s6'))])
    s8.at(t, 'kill target player', 5., [('PLAYER_KILL', m.player('s4'))])
    s8.at(t, 'kill target again', 9., [('PLAYER_KILL', m.player('s4'))])
    for kind, label in (('unit', '单位位'), ('plant', '建筑位')):
        s8.total(t, 'CNV_PK_'+kind, label, [
            (2**k, ('NAMED_NOT_DESTROYED', m.role(side+' '+kind).name))
            for k, side in enumerate(SIDES)])
    s8.total(t, 'CNV_PK_Dying', '死亡位', [
        (2**(k+3*j), ('NAMED_DYING', m.role(side+' '+kind).name))
        for j, kind in enumerate(('unit', 'plant')) for k, side in enumerate(SIDES)])
    s8.frames(t, 'CNV_PK_Frame', '逻辑帧', [])
    s8.watch(t, 16., .5)
    return t


MISSION = {'engine_playerkill': mission}
CHECKS = {'engine_playerkill': {'a': check}}
