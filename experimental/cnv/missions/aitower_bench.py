"""Engine probe: where a skirmish AI puts a base defence tower (read back by checks/engine_aitower.py; engine line A,
layer 4 block 5, RA3-EngineModel ra3model/ai/defense.py tower_site / tower_centre / tower_spots).

The enemy (s1, Allied) runs a personality of this probe's own: the Allied co-op base with every inherited strategic
state removed (as aitarget_bench.py), the build state AlliedNeededUnits removed (only AlliedDefenseBuildState is
left: Multigunner turrets), the four inherited budget states removed and one of its own, always on (ConstantHeuristic),
PRODUCTION 50% / DEFENSE 50% (which account pays for a tower is not read -- either share buys one at the wake money).
Its BaseCompactness is the build's.
  AI     the yard on the east base, a power plant 450 south of it (the AI building nearest the enemy)
  enemy  the player's power plant 1250 south of the yard (800 south of the AI's plant: the nearest enemy to both), the
         player's yard on the west bank ~2700 away
Read (l4_defense2.md 2.1-2.3): the tower's centre is the AI building nearest an enemy (the plant, not the yard), the
first angle points from the base centre to its nearest enemy (south), the radius is (BaseCompactness +- 0.05) x 500.
So the first tower should stand south of the AI plant, 250 / 375 / 475-500 from it for 0.5 / 0.75 / 1.0.
Builds: aitower50 (0.5, the Allied co-op default), aitower75, aitower100 -- these build the turret by an opening move
(a deposit of 1000 to PRODUCTION, then AlliedBaseDefense; retail budgets kept): the build state alone built nothing in
70 s (aitowerstate: the own budget above, no opener). Readings in checks/engine_aitower.py.
Facts: wake at, money.
"""
from maps import niagara
from missions import aistate_bench as ab
from parts import Mission, Script

WAKE_AT = 10.0
MONEY = 1700                                # 2 x 800 + 100: a tower from either account at 50%
PID = 'CNVTowerTest'
TURRET = 'AlliedBaseDefense'
PLANT = 'AlliedPowerPlant'
YARD_AT = (3850.0, 3400.0)                  # niagara 'east base'
AI_PLANT_DY = -450.0
ENEMY_DY = -1250.0
BUDGETS = ('CoopBudget', 'DefenseBudget', 'HeavyDefenseBudget', 'OpeningMoveBudget')
BUDGET_ID = 'CNVTowerBudget'
OPENER = 'CNVTowerOpener'
OPENER_DEPOSIT = 1000


def _budget():
    return f'''  <AIBudgetStateDefinition id="{BUDGET_ID}">
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <Budget>
      <AccountShare Account="PRODUCTION" Percent="50%"/>
      <AccountShare Account="DEFENSE" Percent="50%"/>
      <AccountShare Account="SLUSH_FUND" Percent="0%"/>
    </Budget>
  </AIBudgetStateDefinition>'''


def _opener():
    # as retail AIOpener_A08_AlliedSpecialForces: a deposit, then the build; the trailing Time order ends the opening
    return f'''  <SkirmishOpeningMove id="{OPENER}" Side="PlayerTemplate:Allies">
    <Order Time="0s" Account="PRODUCTION" Deposit="{OPENER_DEPOSIT}" />
    <Order Build="{TURRET}" />
    <Order Time="90s"/>
  </SkirmishOpeningMove>'''


def personality_xml(compactness, opener=False):
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
    removed += ['    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>']
    if opener:                              # retail budgets kept; the opening move first (as 1AlliedBalanced's)
        first = [f'    <OpeningMove Name="{OPENER}" Weight="100%">', '      <Heuristic>',
                 '        <ConstantHeuristic/>', '      </Heuristic>', '    </OpeningMove>']
        own, budget = [], []
    else:
        first = []
        removed += [f'    <BudgetState id="{k}" xai:joinAction="Remove"/>' for k in BUDGETS]
        own, budget = [_budget()], [f'    <BudgetState id="{BUDGET_ID}" State="{BUDGET_ID}"/>']
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
        '  </Includes>',
        *own,
        *([_opener()] if opener else []),
        f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}"'
        f' BaseCompactness="{compactness}">',
        *first,
        *removed,
        *budget,
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, compactness, opener=True):
    m = Mission(name=name, map=niagara, facts={'wake at': WAKE_AT, 'money': MONEY})
    m.cnv_compactness = compactness         # the check says the model's radius by it
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(compactness, opener), f'AIPersonalityDefinition:{PID}'))
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put(PLANT, 'east base', 0.0, AI_PLANT_DY, side='s1', name='UNIT - CNV AI Plant', role='ai plant')
    m.put(PLANT, 'east base', 0.0, ENEMY_DY, name='UNIT - CNV AI Enemy Plant', role='enemy plant')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.spawns |= {TURRET}
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, MONEY)])]
    return m


MISSION = {'aitower50': lambda: mission('CampAITow50', 0.5),
           'aitower75': lambda: mission('CampAITow75', 0.75),
           'aitower100': lambda: mission('CampAITow100', 1.0),
           'aitowerstate': lambda: mission('CampAITowState', 0.5, opener=False)}
