"""Engine probe: an opening's <Order Time=...> -- from when is the time counted (read back by checks/engine_aiotime.py;
private ai/opening.py Opening.step: "a Time order waits until that many seconds have passed since the opening began").

aiopen_bench's map and wake (Niagara, s1 Allied with one yard at the east base, woken at 10 s with 50000), but the
personality is the probe's own: AlliedCoopBasePersonality (no OpeningMove of its own, OpeningMoveBudget inherited),
every inherited strategic state removed, one OpeningMove of the probe's SkirmishOpeningMove CNVOpenTime:
  Build AlliedPowerPlant / Time 30s / Build AlliedPowerPlant / Time 20s / Build AlliedPowerPlant
A power plant takes ~153 frames (aiopen f1-f3). Mission seconds of the three plants under each reading of Time:
  since the wake (the model)        ~20 / ~50 / ~60   (the 20s point has passed: the third goes in at once)
  since the previous Time order     ~20 / ~50 / ~70
  since the mission start           ~20 / ~40 / ~50

Facts: wake at, money.
"""
from maps import niagara
from missions.aistate_bench import BASE, INHERITED
from parts import Mission, Script

WAKE_AT, MONEY = 10.0, 50000
PID, MOVE = 'CNVOpenT', 'CNVOpenTime'
PLANT = 'AlliedPowerPlant'
ORDERS = (('Build', PLANT), ('Time', '30s'), ('Build', PLANT), ('Time', '20s'), ('Build', PLANT))


def personality_xml(pid=PID, orders=ORDERS):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
        '  </Includes>',
        f'  <SkirmishOpeningMove id="{MOVE}" Side="PlayerTemplate:Allies">',
        *[f'    <Order {k}="{v}" />' for k, v in orders],
        '  </SkirmishOpeningMove>',
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
        f'    <OpeningMove Name="{MOVE}" Weight="100%" Difficulty="EASY MEDIUM HARD BRUTAL"/>',
        *removed,
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name='CampAIOTime'):
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT, 'money': MONEY})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(), f'AIPersonalityDefinition:{PID}'))
    m.spawns |= {PLANT}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, MONEY)])]
    return m


MISSION = {'aiotime': mission}
