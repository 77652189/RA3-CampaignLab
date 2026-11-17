"""Named facing contrast; predictions/evidence: work/re/c_facewp_report.md.

Two Guardians start east, ordered north/west at 4s (swapped in b); a third
stays untouched east. Read actual hull heading from teamlog.states().hd,
not from unchanged position. Exact turning timing remains a gap.
MEASURED: a human host publishes no team headings; b AI host publishes ids
12/13/14 (alpha/beta/control) on its default team, not the named empty crews.
b f1..46: 0/0/0; f76..226: -180/117/0; 24 stable samples in the replay.
Both runs have 25 displayed samples with alive mask 7. The b turn itself
f61..68 is retained privately; exact order phase is not claimed by this replay.
"""
import os

import labpaths
from maps import probe_border
from parts import Mission, Script, Test, Unit
from checks import engine_scripts8 as s8

TANK = 'AlliedAntiVehicleVehicleTech1'
HOST = 'CNVFaceHost'
ROLES = ('alpha', 'beta', 'control')


def mission(side='p1'):
    source = os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', 'AlliedPowerPlant.xml')
    with open(source, encoding='utf-8') as f:
        xml = f.read()
    xml = xml.replace('id="AlliedPowerPlant"', f'id="{HOST}"')
    xml = xml.replace('EditorName="AlliedPowerPlant"', f'EditorName="{HOST}"')
    xml = xml.replace('<Behaviors>', '<Behaviors>\n'
        '<DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>')
    unit = Unit(HOST, xml, names=dict(unit=HOST),
                what='电厂复制体，只用 CNVTeams 记录所属玩家队伍的真实朝向',
                params=dict(of='AlliedPowerPlant', every=15))
    m = Mission(name='CampFaceWP', map=probe_border, units=[unit], facts={}, ext=True)
    m.put(HOST, 'stop row', -500., -3000., side=side, role='observer')
    for k, role in enumerate(ROLES):
        crew = m.crew('Face'+role.title(), side=side)
        m.put(TANK, 'stop row', 200.+500.*k, -1800., angle=0.,
              side=side, role=role, name='CNV Face '+role, props={'originalOwner': crew})
    m.waypoint('north', 'CNV Face North', 'stop row', 200., -800.)
    m.waypoint('west', 'CNV Face West', 'stop row', -800., -1800.)
    return m


def check(m, which):
    t = Test()
    t.scripts.append(Script('Test - face hold', [], [
        ('UNIT_ALLOW_AI_AUTOACQUIRE', m.role(r).name, 0) for r in ROLES]))
    directions = ('north', 'west') if which == 'a' else ('west', 'north')
    s8.at(t, 'face order', 4., [
        ('NAMED_FACE_WAYPOINT', m.role(r).name, m.mark(d))
        for r, d in zip(ROLES, directions)])
    s8.total(t, 'CNV_FW_Alive', '存活位', [
        (1 << k, ('NAMED_NOT_DESTROYED', m.role(r).name))
        for k, r in enumerate(ROLES)])
    s8.frames(t, 'CNV_FW_Frame', '逻辑帧', [])
    t.expect = [('存活位', 0., '==', 7)]
    s8.watch(t, 12., .5)
    return t


MISSION = {'engine_facewp': mission, 'engine_facewpai': lambda: mission('s1')}
CHECKS = {'engine_facewp': {'a': lambda m: check(m, 'a')},
          'engine_facewpai': {'b': lambda m: check(m, 'b')}}
