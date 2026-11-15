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


def mission(distance=200, placed=True):
    m = expansion_mission(True)
    m.name = {200: 'CampAIExpSE', 50: 'CampAIExpD50', 400: 'CampAIExpD400'}[distance]
    filename, xml, asset = m.assets[0]
    xml, n = re.subn(r'<Tactic id="Attack".*?</Tactic>', tactic_xml(distance), xml, count=1, flags=re.S)
    assert n == 1 and 'SimpleAttack' not in xml
    m.assets[0] = filename, xml, asset
    if placed:
        m.put(MINER, 'east base', -200.0, -150.0, side='s1', angle=3.1416, name='UNIT - CNV AI Miner',
              role='ai miner')
    m.spawns |= {MINER, OUTPOST}
    m.facts['tactic distance'] = distance
    m.facts['expansion pick'] = PICK
    m.facts['miner'], m.facts['outpost'] = MINER, OUTPOST
    return m


# D round 155 (d154's H1): the AI builds its miner itself. No placed miner; s1 owns a refinery (it makes the
# AlliedMiner) by the bluff ore (the map's lint wants a refinery within 250 of a node; the bluff is the candidate
# the Expansion pick passes over, so its free miner harvests far from the east pick) and a power plant north, gets BUILT_MONEY at the wake and an opener of this probe's
# own that only deposits BUILT_DEPOSIT to PRODUCTION (aiteamfilter_bench's aiar* opener without its Builds); the
# build state AlliedNeededUnits (retail's miner top-up) removed, so a miner made comes from the team's CreateUnits.
BUILT_MONEY, BUILT_DEPOSIT = 10000, 5000
OPENER = 'CNVSExpOpener'
PLANT_DY = 400.0


def built(distance=200, build=False):
    m = mission(distance, placed=False)
    m.name = f'CampAIExp{"B" if build else "H"}{distance}'
    filename, xml, asset = m.assets[0]
    opener = '\n'.join([f'  <SkirmishOpeningMove id="{OPENER}" Side="PlayerTemplate:Allies">',
                        f'    <Order Time="0s" Account="PRODUCTION" Deposit="{BUILT_DEPOSIT}" />',
                        *([f'    <Order Build="{MINER}" />'] if build else []),
                        '    <Order Time="5s"/>', '  </SkirmishOpeningMove>', ''])
    first = '\n'.join([f'    <OpeningMove Name="{OPENER}" Weight="100%">', '      <Heuristic>',
                       '        <ConstantHeuristic/>', '      </Heuristic>', '    </OpeningMove>',
                       '    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>', ''])
    xml, n = re.subn(r'(  <AIPersonalityDefinition [^>]*>\n)', lambda g: opener + g.group(1) + first, xml, count=1)
    assert n == 1
    m.assets[0] = filename, xml, asset
    m.put('AlliedRefinery', 'bluff refinery', side='s1', name='UNIT - CNV AI Refinery', role='ai refinery')
    m.put('AlliedPowerPlant', 'east base', 0.0, PLANT_DY, side='s1', name='UNIT - CNV AI Plant', role='ai plant')
    s1 = m.player('s1')
    wake, = [s for s in m.scripts if s.name == 'CNV AI - Wake']
    wake.do = [(a[0], a[1], BUILT_MONEY) if a[0] == 'PLAYER_SET_MONEY' else a for a in wake.do]
    assert ('PLAYER_SET_MONEY', s1, BUILT_MONEY) in wake.do
    m.facts['ai builds miner'] = True
    m.facts['opener builds miner'] = build
    return m


# D round 156 (d155's H4): the same probe, its opener also orders one AlliedMiner (aiteamfilter_bench's aiar* form)
# -- is a miner built after the SimpleExpansion team exists taken into it? One build, retail Distance 200.
MISSION = {'aiexpse': lambda: mission(200), 'aiexpd50': lambda: mission(50), 'aiexpd400': lambda: mission(400),
           'aiexph200': lambda: built(200), 'aiexph50': lambda: built(50), 'aiexph400': lambda: built(400),
           'aiexpb200': lambda: built(200, build=True), 'aiexpb50': lambda: built(50, build=True),
           'aiexpb400': lambda: built(400, build=True)}
