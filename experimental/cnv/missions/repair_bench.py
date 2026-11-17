"""RepairUpdate through a woken AI, with funded / zero-credit controls.

Prediction from the data and D's repair analysis: a 1000 HP, cost-800 plant
starting at half health gains 10 HP/s; total cost is about 100 (the missing
fraction enters twice). No build states, combat or income can spend money.
CNVProbe reads repair activation and accumulators; it does not start repair.
The legacy engine_repair:a UI activation diagnostic is kept separately.

Bench 2026-11-11 E48: starting funded with 10000 and no later money reset
reaches 100/50/9900 at s49 and remains there. The read-only probe reports
active at frame 5, cost=200, r=1/1500; stopped at frame 756.
E41's late funding failed because the no-economy AI latch was already set.
Zero-credit control measures that latch, not inability to pay an active repair.
Unmeasured repair configurations and player input remain separate gaps.
E49 repairq:a starts at 25% health: cost=300, active frame 5 to 1131;
the bench reaches 100/50/9775 at s74 and holds through s103.
E51 repairt:a starts at 75% health: cost=100, active frame 5 to 381;
the bench reaches 100/50/9975 at s24 and holds through s51.
"""
from pathlib import Path

import labpaths
from maps import probe_range
from missions import aistate_bench as ab
from parts import Mission, Script, Unit

PROBE = 'CNV_RepairPlant'
PID = 'CNVRepairAI'
WAKE = 10.0


def probe_plant():
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedPowerPlant.xml').read_text(encoding='utf-8')
    assert xml.count('id="AlliedPowerPlant"') == xml.count('<Behaviors>') == 1
    xml = xml.replace('id="AlliedPowerPlant"', f'id="{PROBE}"', 1)
    xml = xml.replace('<Behaviors>', '<Behaviors>\n'
                      '      <DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="150" MaxFrames="2000"/>', 1)
    return Unit(PROBE, xml, names=dict(unit=PROBE), what='原版电厂复制，附只读维修探针', params=dict(of='AlliedPowerPlant'))


def personality_xml(repair_at='EASY MEDIUM HARD BRUTAL'):
    removed = '\n'.join(f'    <StrategicState id="{key}" xai:joinAction="Remove"/>' for key in ab.INHERITED)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xai="uri:ea.com:eala:asset:instance">
  <Includes><Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml"/></Includes>
  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}"
    RepairBuildingsAtDifficulty="{repair_at}">
{removed}
    <BuildState id="AlliedDefenseBuildState" xai:joinAction="Remove"/>
    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>
  </AIPersonalityDefinition>
</AssetDeclaration>
'''


def mission(funded, initial_health=50, repair_at=None):
    name = {25: 'CampRepQ', 75: 'CampRepT'}.get(initial_health, 'CampRepAI' if funded else 'CampRepZero')
    if repair_at is not None:            # repairoff / repairmed: RepairBuildingsAtDifficulty "" / "MEDIUM"
        name = 'CampRepMed' if repair_at else 'CampRepOff'
    facts = {'funded': funded, 'initial health': initial_health, 'wake at': WAKE,
             'repairs at medium': int(repair_at is None or 'MEDIUM' in repair_at.split())}
    m = Mission(name=name, map=probe_range, units=[probe_plant()], facts=facts, ext=True)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies',
                     'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    xml = personality_xml() if repair_at is None else personality_xml(repair_at)
    m.assets.append((PID + '.xml', xml, f'AIPersonalityDefinition:{PID}'))
    m.put('AlliedConstructionYard', 'high gun', side='s1', name='Repair AI Yard', role='ai yard')
    m.put(PROBE, 'high at 450', side='s1', name='Repair AI Plant', role='repair')
    m.put('AlliedPowerPlant', 'base gun', name='Repair Control', role='control')
    m.waypoint('ai base', 'Repair AI Base', 'high gun')
    ai = m.player('s1')
    m.scripts = [
        Script('Repair start', [], [('PLAYER_SET_MONEY', ai, 10000 if funded else 0),
                                    ('UNIT_SET_HEALTH', m.role('repair').name, float(initial_health)),
                                    ('UNIT_SET_HEALTH', m.role('control').name, 50.0),
                                    ('SET_MILLISECOND_TIMER', 'Repair Wake', WAKE)]),
        Script('Repair wake', [('TIMER_EXPIRED', 'Repair Wake')],
               [('UNIT_AI_TRANSFER_ALL', ai, 1), ('SKIRMISH_AI_MAKE_BASE', ai, m.mark('ai base')),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', ai, 0), ('SKIRMISH_AI_USE_REPAIRS', ai, 1)])]
    return m


MISSION = {'repairai': lambda: mission(True), 'repairzero': lambda: mission(False),
           'repairq': lambda: mission(True, 25), 'repairt': lambda: mission(True, 75),
           'repairoff': lambda: mission(True, repair_at=''), 'repairmed': lambda: mission(True, repair_at='MEDIUM')}
