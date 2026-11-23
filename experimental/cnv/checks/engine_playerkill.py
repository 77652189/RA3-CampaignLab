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


PK = 'alliedantiinfantryinfantry'     # the Peacekeeper an Allied structure's death leaves (REQUIRES_LIVE_PLAYER)


def allied():
    """Review xx #2: s4's and s5's plants are Allied (their BuildingDestruction list leaves a Peacekeeper only while
    the owner is a live player). s4 is cleared by PLAYER_KILL at 5 s and 9 s, s5's plant by NAMED_KILL at 5 s (does a
    script death leave one at all); p1's Soviet plant stays."""
    m = Mission(name='CampPKAllied', map=probe_border, units=[], facts={})
    for k, (side, template) in enumerate((('p1', 'SovietPowerPlant'), ('s4', 'AlliedPowerPlant'),
                                          ('s5', 'AlliedPowerPlant'))):
        m.put(template, 'stop row', -200.+k*1500., -2300., side=side, role=side, name='CNV PKAllied '+side)
    m.spawns |= {PK}
    return m


def check_allied(m):
    t = Test()
    s8.at(t, 'kill player', 5., [('PLAYER_KILL', m.player('s4')), ('NAMED_KILL', m.role('s5').name)])
    s8.at(t, 'kill again', 9., [('PLAYER_KILL', m.player('s4'))])
    s8.total(t, 'CNV_PKA_Plant', '电厂位', [(2**k, ('NAMED_NOT_DESTROYED', m.role(side).name))
                                         for k, side in enumerate(('p1', 's4', 's5'))])
    for side in ('s4', 's5'):           # counted with the dying (PLAYER_HAS_OBJECT_COMPARISON), up to 2
        s8.total(t, 'CNV_PKA_'+side, side+' 维和兵', [(1, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(side), 3, n, PK))
                                                     for n in (1, 2)])
    s8.frames(t, 'CNV_PKA_Frame', '逻辑帧', [])
    s8.watch(t, 16., .5)
    return t


MISSION = {'engine_playerkill': mission, 'engine_pkallied': allied}
CHECKS = {'engine_playerkill': {'a': check}, 'engine_pkallied': {'a': check_allied}}
