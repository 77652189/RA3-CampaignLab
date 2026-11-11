"""EngageTacticalTarget on/off, with hostile/passive acquisition disabled.

Prediction before bench: the on team receives explicit attacks on the nearest
power plant, the off team only attack-moves to its point. The unarmed plant
cannot provoke retaliation. At 40 s on has damaged it, off leaves it at 100%.
Both retain four Peacekeepers. This tests dispatch, not exact firing timing.

Bench 2026-11-11: aitacon:a / aitacoff:a PASS (one run each). On reads
100% through s12, 84% at s13, 0% from s22 through s43; off stays 100%
through s48. Both retain four infantry. Replay: tests/test_engage_tactical.py.
Only an object target in range, with passive/hostile dispatch disabled, is
covered; point targets, competing enemies and the exact scan boundary are not.
"""
from maps import niagara
from missions import aitarget_bench as ab
from parts import Mission, Script


def mission(enabled):
    m = Mission(name='CampTacOn' if enabled else 'CampTacOff', map=niagara,
                facts={'wake at': ab.WAKE_AT, 'tactical enabled': float(enabled)})
    xml = ab.personality_xml('ClosestStructureHeuristic', 'SimpleAttack', idle=15)
    xml = xml.replace('EngageHostileTargets="true"', 'EngageHostileTargets="false"')
    xml = xml.replace('EngagePassiveTargets="true"', 'EngagePassiveTargets="false"')
    xml = xml.replace('EngageTacticalTarget="true"',
                      f'EngageTacticalTarget="{str(enabled).lower()}"')
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies',
                     'aiPersonality': f'AIPersonalityDefinition:{ab.PID}'}
    m.assets.append((f'{ab.PID}.xml', xml, f'AIPersonalityDefinition:{ab.PID}'))
    m.cnv_units = (ab.INF,)
    m.put('AlliedConstructionYard', 'east base', side='s1', name='Tac AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='Tac Player Yard', role='player yard')
    m.put('AlliedPowerPlant', 'east base', -450, 0, name='Tac Plant', role='target')
    for k in range(4):
        m.put(ab.INF, 'east base', -260, -90 + 60 * k, side='s1',
              name=f'Tac Infantry {k + 1}', role=f'infantry {k + 1}', angle=3.1416)
    m.spawns.add(ab.INF)
    m.waypoint('ai base', 'Tac Base', 'east base')
    s1 = m.player('s1')
    m.scripts = [
        Script('Tac start', [], [('PLAYER_SET_MONEY', s1, 0),
                                ('SET_MILLISECOND_TIMER', 'Tac Wake', ab.WAKE_AT)]),
        Script('Tac wake', [('TIMER_EXPIRED', 'Tac Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, m.mark('ai base')),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20),
                ('SKIRMISH_AI_USE_REPAIRS', s1, 0), ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0),
                ('PLAYER_SET_MONEY', s1, 0)])]
    return m


MISSION = {'aitacon': lambda: mission(True), 'aitacoff': lambda: mission(False)}
