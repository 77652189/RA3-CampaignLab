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
70 s (aitowerstate: the own budget above, no opener). aitowerfoe (round 71): as aitowerstate, plus FOES of the
player's Guardian tanks (HOLD_FIRE) 600 south of the AI plant -- does the build state (BEST_UNIT_EXPECTED) build once
there is an enemy army, and round which building (the opener's turret stood round the yard). aitowerdep: as
aitowerfoe, but an opener that only deposits 1000 to DEFENSE (no Build order; retail budgets kept) -- is the script's
money just never in the accounts? Round 133 (handoff-b section 125's table): aitowerinc -- as aitowerstate, plus an
AI refinery on the east ore and a miner (does a share need income?); aitoweropen -- as aitowerstate, plus an opener
of one empty Time 0s order, own budget kept (does a share fund nothing before an opening is done?). Round 135
(handoff-b section 137's table): aitowerinc10 -- as aitowerinc, but DEFENSE 10% / PRODUCTION 90% (does the share
borrow against its income -- a turret soon after the wake -- or wait for 10% of the money to reach 800?). Readings in
checks/engine_aitower.py.
Facts: wake at, money.
"""
import resources
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
FOE = 'AlliedAntiVehicleVehicleTech1'       # Guardian tank
FOES = 4
FOE_DY = AI_PLANT_DY - 600.0                # 600 south of the AI plant (1050 from the yard)
HOLD_FIRE = 3
RICH, RICH_WATCH = 20000, 150.0             # aitowerinc10r: the bank 20000 at the wake
CHEAT_WATCH = 90.0                          # aicheat*: ~7 miner trips after the wake
CHEAT = {'aicheat2': (('200%', 'MEDIUM'),),
         'aicheat1': (('300%', 'EASY HARD BRUTAL'), ('100%', 'MEDIUM'))}


INC10_WATCH = 420.0                         # aitowerinc10 (DEFENSE 10%): long enough for a second turret
# B round 178 (work/re d122_ai_rules.md 1, R1-R3): two budget states of the probe's own, in this list order:
# (id, heuristic, DEFENSE %); heuristic = a ConstantHeuristic Weight, or 'opening' (OpeningMoveHeuristic
# Complete=false: holds until the opening is done). DEFENSE 100 % buys turrets with the bank; PRODUCTION 100 % buys
# nothing (no unit build state left), so a turret says which state runs.
BS_DEF, BS_PROD = 'CNVBsDef', 'CNVBsProd'
BSETS = {'aibsmax': ((BS_DEF, '0.4', 100), (BS_PROD, '0.6', 0)),      # R1: the larger, though second -> 0 turrets
         'aibstie': ((BS_DEF, '0.5', 100), (BS_PROD, '0.5', 0)),      # R2: a tie -> the earlier -> turrets
         'aibszero': ((BS_DEF, '0', 100), (BS_PROD, 'opening', 0))}   # R3: PROD until the opening ends, then all 0
ZERO_OPENING = 40.0                         # aibszero: the opener's one Time order, 40 s after the wake


def _budget(defense=50, bid=BUDGET_ID, heuristic=None):
    if heuristic == 'opening':
        h = '<OpeningMoveHeuristic Complete="false"/>'
    else:
        h = '<ConstantHeuristic/>' if heuristic is None else f'<ConstantHeuristic Weight="{heuristic}"/>'
    return f'''  <AIBudgetStateDefinition id="{bid}">
    <Heuristic>
      {h}
    </Heuristic>
    <Budget>
      <AccountShare Account="PRODUCTION" Percent="{100 - defense}%"/>
      <AccountShare Account="DEFENSE" Percent="{defense}%"/>
      <AccountShare Account="SLUSH_FUND" Percent="0%"/>
    </Budget>
  </AIBudgetStateDefinition>'''


def _opener(build=True, empty=False, wait=0):
    # as retail AIOpener_A08_AlliedSpecialForces: a deposit, then the build; the trailing Time order ends the opening.
    # build=False: the deposit only, to DEFENSE (the build state spends it, if it builds at all)
    # empty=True: one Time 0s order and nothing else -- an opening that is done at once
    account = 'PRODUCTION' if build else 'DEFENSE'
    order = [f'    <Order Build="{TURRET}" />'] if build else []
    # wait (aibszero): the empty opener's one Time order -- the opening is done that many seconds after the wake
    body = ([f'    <Order Time="{wait:g}s"/>'] if empty else
            [f'    <Order Time="0s" Account="{account}" Deposit="{OPENER_DEPOSIT}" />', *order, '    <Order Time="90s"/>'])
    return '\n'.join([f'  <SkirmishOpeningMove id="{OPENER}" Side="PlayerTemplate:Allies">', *body,
                      '  </SkirmishOpeningMove>'])


def personality_xml(compactness, opener=False, build=True, empty=False, defense=50, cheat=(), state=BUDGET_ID,
                    bsets=(), wait=0):
    # bsets (aibs*): ((id, heuristic, DEFENSE %), ...) -- several own budget states, their BudgetState lines in order
    # empty=True: the empty opener (_opener) with this probe's own budget, not the retail ones
    # cheat: ((Percentage, Difficulty), ...) -- the personality's own ResourceMultiplierCheat lines (aicheat*)
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
    removed += ['    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>']
    first = [f'    <OpeningMove Name="{OPENER}" Weight="100%">', '      <Heuristic>',
             '        <ConstantHeuristic/>', '      </Heuristic>', '    </OpeningMove>'] if opener or empty else []
    if opener:                              # retail budgets kept; the opening move first (as 1AlliedBalanced's)
        own, budget = [], []
    else:
        removed += [f'    <BudgetState id="{k}" xai:joinAction="Remove"/>' for k in BUDGETS]
        # state (aibsprod): the line's State names another budget definition than the own one (still declared)
        own, budget = [_budget(defense)], [f'    <BudgetState id="{BUDGET_ID}" State="{state}"/>']
        if bsets:
            own = [_budget(d, b, h) for b, h, d in bsets]
            budget = [f'    <BudgetState id="{b}" State="{b}"/>' for b, _, _ in bsets]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
        '  </Includes>',
        *own,
        *([_opener(build, empty, wait)] if opener or empty else []),
        f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}"'
        f' BaseCompactness="{compactness}">',
        *first,
        *removed,
        *budget,
        *[f'    <ResourceMultiplierCheat Percentage="{p}" Difficulty="{d}"/>' for p, d in cheat],
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, compactness, opener=True, foes=0, build=True, empty=False, refinery=False, defense=50,
            watch=None, money=MONEY, cheat=(), state=BUDGET_ID, bsets=(), wait=0):
    facts = {'wake at': WAKE_AT, 'money': money}
    if wait:
        facts['opening'] = wait             # engine_aitower i: the opening is done this long after the wake
    if watch:
        facts['watch'] = watch              # how long checks/engine_aitower.py e watches after the wake
    m = Mission(name=name, map=resources.measured(niagara), facts=facts)
    m.cnv_compactness = compactness         # the check says the model's radius by it
    m.cnv_turret = TURRET                   # what the check counts (checks ask the mission, not this module)
    # the income multiplier predicted at the bench's MEDIUM: the MEDIUM line's Percentage (engine_aitower g)
    m.cnv_state = state                     # engine_aitower h: which budget definition the one BudgetState names
    m.cnv_bsets = bsets                     # engine_aitower i: the budget states, in list order
    m.cnv_cheat = next((float(p.rstrip('%')) / 100 for p, d in cheat if 'MEDIUM' in d.split()), 1.0)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(compactness, opener, build, empty, defense, cheat, state,
                                                   bsets, wait),
                      f'AIPersonalityDefinition:{PID}'))
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put(PLANT, 'east base', 0.0, AI_PLANT_DY, side='s1', name='UNIT - CNV AI Plant', role='ai plant')
    m.put(PLANT, 'east base', 0.0, ENEMY_DY, name='UNIT - CNV AI Enemy Plant', role='enemy plant')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.spawns |= {TURRET}
    if refinery:                            # income: the AI's refinery on the east ore and a miner by it
        m.put('AlliedRefinery', 'east refinery', side='s1', name='UNIT - CNV AI Refinery', role='ai refinery')
        m.put('AlliedMiner', 'east refinery', -150.0, 150.0, side='s1', name='UNIT - CNV AI Miner', role='ai miner')
    base = 'CNV AI Base'
    foe = [f'UNIT - CNV AI Foe {k}' for k in range(foes)]
    for k, n in enumerate(foe):
        m.put(FOE, 'east base', 60.0 * k - 30.0 * (foes - 1), FOE_DY, name=n, role=f'foe {k}')
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]
               + [('UNIT_SET_STANCE', n, HOLD_FIRE) for n in foe]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, money)])]
    return m


MISSION = {'aitower50': lambda: mission('CampAITow50', 0.5),
           'aitower75': lambda: mission('CampAITow75', 0.75),
           'aitower100': lambda: mission('CampAITow100', 1.0),
           'aitowerstate': lambda: mission('CampAITowState', 0.5, opener=False),
           'aitowerfoe': lambda: mission('CampAITowFoe', 0.5, opener=False, foes=FOES),
           'aitowerdep': lambda: mission('CampAITowDep', 0.5, foes=FOES, build=False),
           'aitowerinc': lambda: mission('CampAITowInc', 0.5, opener=False, refinery=True),
           'aitoweropen': lambda: mission('CampAITowOpen', 0.5, opener=False, empty=True),
           'aitowerinc10': lambda: mission('CampAITowInc10', 0.5, opener=False, refinery=True, defense=10,
                                           watch=INC10_WATCH),
           'aitowerinc5': lambda: mission('CampAITowInc5', 0.5, opener=False, refinery=True, defense=5,
                                          watch=INC10_WATCH),
           # round 136: as aitowerinc10 with 20000 at the wake -- does the bank count at all (10 % = 2000: 2 turrets)?
           'aitowerinc10r': lambda: mission('CampAITowRich', 0.5, opener=False, refinery=True, defense=10,
                                            watch=RICH_WATCH, money=RICH),
           # B round 172: ResourceMultiplierCheat on the miner's income (DEFENSE 0 %: nothing is bought, the money
           # only grows). The bench runs MEDIUM (engine_aidiff). aicheat2: a MEDIUM 200 % line; aicheat1: the retail
           # values' other side -- a 300 % line for EASY HARD BRUTAL (not MEDIUM: skipped) and a MEDIUM 100 % one
           # B round 173: BudgetState.State -- as aitowerinc (own budget DEFENSE 50 % still declared), the one
           # BudgetState line naming retail ProductionOnlyBudget (opening done -> PRODUCTION 100 %, DEFENSE 0 %)
           'aibsprod': lambda: mission('CampAIBSProd', 0.5, opener=False, refinery=True, watch=RICH_WATCH,
                                       money=RICH, state='ProductionOnlyBudget'),
           # B round 178: which budget state runs (d122 R1-R3) -- as aibsprod (refinery, 20000), two own states
           'aibsmax': lambda: mission('CampAIBSMax', 0.5, opener=False, refinery=True, watch=RICH_WATCH, money=RICH,
                                      bsets=BSETS['aibsmax']),
           'aibstie': lambda: mission('CampAIBSTie', 0.5, opener=False, refinery=True, watch=RICH_WATCH, money=RICH,
                                      bsets=BSETS['aibstie']),
           'aibszero': lambda: mission('CampAIBSZero', 0.5, opener=False, empty=True, refinery=True,
                                       watch=RICH_WATCH, money=RICH, bsets=BSETS['aibszero'], wait=ZERO_OPENING),
           'aicheat2': lambda: mission('CampAICheat2', 0.5, opener=False, refinery=True, defense=0,
                                       watch=CHEAT_WATCH, cheat=CHEAT['aicheat2']),
           'aicheat1': lambda: mission('CampAICheat1', 0.5, opener=False, refinery=True, defense=0,
                                       watch=CHEAT_WATCH, cheat=CHEAT['aicheat1'])}
