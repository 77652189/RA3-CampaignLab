"""D round 154: Tactic SimpleExpansion -- the AI's miner unpacks into an outpost at an Expansion target.

C's aiexpc map (missions/aiexpansion_bench.py: two ore fields, the Expansion heuristic picks the east one, bench
f151 pick 44 at (4173, 2987)) with its state's SimpleAttack swapped for retail AlliedExpansion's tactic
(SageXML SkirmishAI/States/AlliedBaseStates.xml: Tactic="SimpleExpansion" Distance="200", TeamTemplate MinUnits 1
MaxUnits 8 ... NEVER_RELEASE, ExpansionMicroManager, CreateUnits AlliedMiner 1 / 1) and one AI-owned AlliedMiner
placed at the AI's base: the named slot takes a placed unit of its template (model teams.recruit, bench aicr*), so
the AI needs no money or refinery. The four AI Guardians stay (the template's general fill: escorts).

Only Distance differs across the three builds (B's Tactic.Distance: what it governs in SimpleExpansion is the
question): aiexpse = retail 200, aiexpd50 = 50, aiexpd400 = 400. Checks: checks/engine_aisimpleexp.py.
"""
import re

from missions.aiexpansion_bench import mission as expansion_mission

MINER = 'AlliedMiner'
OUTPOST = 'AlliedOutpost'
PICK = (4173.0, 2987.0)             # bench aiexpc expc f151: pick 44 (the Expansion candidate the team goes to)


def tactic_xml(distance):
    return f'''<Tactic id="Expand" Tactic="SimpleExpansion" Distance="{distance}">
      <TeamTemplate MinUnits="1" MaxUnits="8" MinPowerAdvantage="1.0"
                    RegisteredObjectSet="SKIRMISH_AI_NORMAL_COMBAT_UNITS"
                    IncludeKindOf="CAN_ATTACK" ExcludeKindOf="AIRCRAFT SIEGE_WEAPON IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS"
                    Priority="STANDARD" ReleaseType="NEVER_RELEASE" AlwaysRecruit="false"
                    MicroManager="ExpansionMicroManager">
        <CreateUnits UnitName="{MINER}" MinUnits="1" MaxUnits="1"/>
      </TeamTemplate>
    </Tactic>'''


def mission(distance=200):
    m = expansion_mission(True)
    m.name = {200: 'CampAIExpSE', 50: 'CampAIExpD50', 400: 'CampAIExpD400'}[distance]
    filename, xml, asset = m.assets[0]
    xml, n = re.subn(r'<Tactic id="Attack".*?</Tactic>', tactic_xml(distance), xml, count=1, flags=re.S)
    assert n == 1 and 'SimpleAttack' not in xml
    m.assets[0] = filename, xml, asset
    m.put(MINER, 'east base', -200.0, -150.0, side='s1', angle=3.1416, name='UNIT - CNV AI Miner', role='ai miner')
    m.spawns |= {MINER, OUTPOST}
    m.facts['tactic distance'] = distance
    m.facts['expansion pick'] = PICK
    m.facts['miner'], m.facts['outpost'] = MINER, OUTPOST
    return m


MISSION = {'aiexpse': lambda: mission(200), 'aiexpd50': lambda: mission(50), 'aiexpd400': lambda: mission(400)}
