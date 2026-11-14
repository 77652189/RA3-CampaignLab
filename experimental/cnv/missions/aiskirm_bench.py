"""A small skirmish for the skirmish AI in the simulator (simai.py, tests/test_simai.py): the AI builds, makes units,
teams them up and goes out.

Same Niagara map and wake as aiopen_bench.py: the enemy (s1) is Allied with the stock AlliedBalanced personality, one
construction yard at the east base, woken at WAKE_AT the retail way with MONEY. Unlike aiopen the player has a base
worth attacking -- a yard, a war factory and a power plant on the west bank -- so the AI's attack states have
structures to pick (RequireUniqueTarget heuristics take one each) and its teams somewhere to go. No player units, no
scripts beyond the wake. Not run on the bench yet (no check): the readings it would give are the opening's
(aiopen) and when the first attack team leaves / reaches the west bank.

Facts: wake at, money.
"""
import os

import labpaths
import resources
from maps import niagara
from parts import Mission, Script, Unit

JAV = 'AlliedAntiVehicleInfantry'
OUT_DIST = 1200.0                    # aiskjav's OUT: straight south of the yard on open grass (as aidefense_bench)
WAKE_AT, MONEY = 10.0, 50000        # the simulator's miners gather nothing: the AI lives on this
PERSONALITY = 'AIPersonalityDefinition:1AlliedBalanced'


# the AI's own teams, by the engine's names (published so checks may count them; nothing is written into the map):
# the pool 'defaultSkirmishTeam' + player (work/re/l4_states.md) and a strategic state's instances '%s_%s_%u_%u' (work/re/l4_states.md:
# state, a tactic string, two indices -- the tactic's id or its type is what checks g / h tell apart)
AI_TEAMS = {'pool': 'Soviet_1/defaultSkirmishTeamSoviet_1',
            'defense type': 'Soviet_1/LandDefense_MEDIUM_StaticDefense_0_0',
            'defense id': 'Soviet_1/LandDefense_MEDIUM_Defense_0_0',
            'attack type': 'Soviet_1/BalancedAttackGround_MEDIUM_DefenseAvoidanceAttack_0_0',
            'attack id': 'Soviet_1/BalancedAttackGround_MEDIUM_Attack_0_0'}
INDICES = ('0_1', '1_0', '0_2', '1_1')  # the other instances checks i / j count ('<state>_<type>_<a>_<b>')
AI_TEAMS.update({f'{k} {i}': v[:-len('0_0')] + i for k in ('defense type', 'attack type') for i in INDICES
                 for v in [AI_TEAMS[k]]})
# other strategic states 1AlliedBalanced runs at MEDIUM (SDK States/*.xml: state -> its tactic types), checks k / l
OTHER_STATES = {'overwhelm': 'BalancedAttackOverwhelm_MEDIUM_DefenseAvoidanceAttack_0_0',
                'bal defense': 'BalancedDefense_StaticDefense_0_0',
                'cleanup': 'BalancedCleanup_SimpleAttack_0_0',
                'cleanup 0_1': 'BalancedCleanup_SimpleAttack_0_1',
                'emergency': 'LandEmergencyDefense_MEDIUM_SimpleAttack_0_0',
                'scout': 'AlliedScout_DefenseAvoidanceAttack_0_0',
                'scout 2': 'AlliedScout_DefenseAvoidanceAttack_1_0',
                'escort': 'EscortMCV_StaticDefense_0_0',
                # Tactic id/type "Engineer"; the engine's name word is EngineerTactic (C's team log, aiskirm_m.txt)
                'capture tech': 'AlliedCaptureTech_MEDIUM_EngineerTactic_0_0'}
AI_TEAMS.update({k: 'Soviet_1/' + v for k, v in OTHER_STATES.items()})


def ai_map(base, library=True, player='Soviet_1'):
    """`base` (a map module) with AI_TEAMS published; library=False also empties `player`'s script library list: the
    container gives Player_2 and Soviet_1/2/3 Lib_Skirmish_Setup, whose start-up scripts (MAKE_BASE,
    UNIT_AI_TRANSFER_ALL, USE_REPAIRS 1 ...) run at frame 0, before this mission's own wake (handoff.md round 135).
    Same trick as engine_scripts9 _libraries."""
    import types
    import mapstudy
    mod = types.ModuleType(base.__name__)
    mod.__dict__.update({k: v for k, v in vars(base).items() if not k.startswith('__')})
    mod.TEAMS = dict(base.TEAMS, **{f'ai {k}': v for k, v in AI_TEAMS.items()})
    if not library:
        mod.LIBRARIES = dict(getattr(base, 'LIBRARIES', {}), **{player: ()})    # what model.libraries reads (line A)

        def terrain(m):
            base.terrain(m)
            names = [''] + list(mapstudy.players(m))
            libs = [n for _, n in m.walk() if n.name == 'LibraryMaps']
            libs[names.index(player)].head = bytes(4)
        mod.terrain = terrain
    return mod


EXPIRE_PID = 'CNVExpire'              # aiskexp: 1AlliedBalanced with SecondsTillTargetsExpire changed (Base writes 5)


def expire_xml(secs):
    """A personality = 1AlliedBalanced (SDK Personalities/AlliedBalanced.xml) with SecondsTillTargetsExpire=`secs`
    (XSD default 15, BasePersonality.xml writes 5): the slot re-pick interval of l4_states.md 1.2."""
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{EXPIRE_PID}" PersonalityType="{EXPIRE_PID}" inheritFrom="1AlliedBalanced"'
        f' SecondsTillTargetsExpire="{secs:g}"/>',
        '</AssetDeclaration>', ''])


POWER_PID = 'CNVPower'                # aiskpw0 / aiskpw3: 1AlliedBalanced with DesiredExcessPowerBuffer changed (x)


def power_xml(buffer):
    """A personality = 1AlliedBalanced with DesiredExcessPowerBuffer=`buffer` (XSD default 0; BasePersonality.xml
    writes 100, DefaultPersonality.xml 10). B handoff 123: after the opening (power 250 = yard 50 + two plants, drain
    175) the AI builds a 3rd and 4th AlliedPowerPlant; the buffer is the candidate for NonPathDependentStructure's
    POWER line."""
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{POWER_PID}" PersonalityType="{POWER_PID}" inheritFrom="1AlliedBalanced"'
        f' DesiredExcessPowerBuffer="{buffer}"/>',
        '</AssetDeclaration>', ''])


PT_PID, PT_TYPE = 'CNVPtId', 'CNVPtType'   # aiskpt / aiskpti (check pt): a personality's id and its PersonalityType


def ptype_xml(write_type=True):
    """aiskpt: 1AlliedBalanced under the id PT_PID whose PersonalityType is PT_TYPE (not its id: in retail and our
    own data the two are always the same); aiskpti: the same id with no PersonalityType written (does it inherit
    1AlliedBalanced's?). D59 (work/re/d59_b_fields.md 1): PLAYER_IS_HUMAN_OR_AI_PERSONALITY compares the AI's
    PersonalityType, not the asset id."""
    ptype = f' PersonalityType="{PT_TYPE}"' if write_type else ''
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{PT_PID}"{ptype} inheritFrom="1AlliedBalanced"/>',
        '</AssetDeclaration>', ''])


MT_PID, MT_STATE = 'CNVMinT', 'CNVMinTBuild'   # aiskmt / aiskmto (check mt): BuildEntry.MinTime on a TECH entry
MT_TECH = 'AlliedTechStructure'       # TECH, needs an airfield + a refinery (SDK Allied/Structures, GameDependency)
MT_TIMES = {'aiskmt': (150, 151), 'aiskmto': (250, 151)}   # build -> (MinTime, ForceTime), seconds
MT_CONST = ('AlliedBaseDefense', 300)   # aiskmtc: the state's one entry is this tower, CONSTANT Score 300
MT_OWNED = (('AlliedAirfield', 'east airfield'), ('AlliedRefinery', 'east refinery'))   # s1's from s0, by site
# + three power plants (+300): without them the opening's buildings and these two draw 275 against 250 and the
# tech building's 75 never passes the power gate (work/re/l4_buildstate.md "电力门"; first aiskmt run, B handoff 154)
MT_POWER = ((-300.0, -150.0), (-300.0, -350.0), (-500.0, -250.0))   # from the east base (D's aiskcapp spots + one)
MT_POWER_MORE = ((-500.0, -450.0), (-700.0, -150.0), (-700.0, -350.0))   # aiskmt0 (D82 G1): three more


def mintime_xml(min_time, force_time, build=MT_TECH, const=MT_CONST[0], score=MT_CONST[1], power_adv=None):
    """1AlliedBalanced plus one ConstantHeuristic build state of its own with one entry MT_TECH TECH MinTime /
    ForceTime (retail writes MinTime on TECH / UPGRADE_TECH entries only, SDK States/AlliedBaseStates.xml; ForceTime
    is the XSD's, default 99999s). D59 (work/re/d59_b_fields.md 3): t = seconds since the AI woke; t < MinTime -> 0,
    t > ForceTime -> 200 (forced), between -> 140 or 0 by efficiency. aiskmto writes ForceTime < MinTime: which gate
    comes first? The stock tech state (MinTime 360 s at MEDIUM) cannot build it earlier. min_time None (aiskmtc,
    H2 of B handoff 154): the entry is MT_CONST instead -- a building with no prerequisite at a constant 300: does
    a building entry of the AI's own state reach the yard at all? build: aiskmtt puts the TECH entry (MinTime 200 /
    ForceTime 201) on that same tower -- TECH's own gate without the tech building's prerequisites. const: the
    CONSTANT entry's building (aiskmtk: the tech building itself at CONSTANT 300 -- past TECH's evaluator, does the
    yard's general gate take it? D round 82)."""
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        '  </Includes>',
        f'  <AIBuildStateDefinition id="{MT_STATE}">',
        '    <Heuristic>',
        '      <ConstantHeuristic/>',
        '    </Heuristic>',
        (f'    <BuildEntry Build="{const}" Heuristic="CONSTANT" Score="{score}"/>' if min_time is None else
         f'    <BuildEntry Build="{build}" Heuristic="TECH" MinTime="{min_time}s" ForceTime="{force_time}s"/>'),
        '  </AIBuildStateDefinition>',
        f'  <AIPersonalityDefinition id="{MT_PID}" PersonalityType="{MT_PID}" inheritFrom="1AlliedBalanced"'
        + ('' if power_adv is None else f' BuildTechMinPowerAdvantage="{power_adv}"') + '>',
        f'    <BuildState id="{MT_STATE}" State="{MT_STATE}" Difficulty="EASY MEDIUM HARD BRUTAL"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


UMOD_PID = 'CNVUMod'                  # aiskmod: 1AlliedBalanced plus UnitModifier lines (check u)
UMOD_ZERO = ('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry')   # Peacekeeper, Javelin soldier


def umod_xml(zero):
    """A personality = 1AlliedBalanced with <UnitModifier Unit=x OffensiveModifier=0 DefensiveModifier=0/> for each x
    in `zero` (all difficulties). The model (private ai/teams.py UnitBuilder, l4_unitbuilder.md 6 / round 35): the
    modifier scales only the builder's score (work/re/l4_unitbuilder.md), which shapes the draw only under a UnitBuilderUnitChoiceStrategy -- no
    SDK personality has one, so the barracks still draws the zeroed units uniformly."""
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{UMOD_PID}" PersonalityType="{UMOD_PID}" inheritFrom="1AlliedBalanced">',
        *[f'    <UnitModifier Unit="{u}" OffensiveModifier="0" DefensiveModifier="0"/>' for u in zero],
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


ACCT_PID = 'CNVAcct'                  # aiskacp / aiskacd: 1AlliedBalanced rebuilt with its opening's Account changed
# 1AlliedBalanced's own strategic-state lines (SDK Personalities/AlliedBalanced.xml lines 46-68, copied as written)
BALANCED_STATES = (
    ('BalancedDefense', 'EASY MEDIUM HARD BRUTAL'), ('BalancedCleanup', 'EASY MEDIUM HARD'),
    ('AlliedScout', 'MEDIUM HARD BRUTAL'), ('ACVHarrassment', 'HARD BRUTAL'),
    ('BalancedAttackGround', 'HARD BRUTAL'), ('BalancedAttackWater', 'HARD BRUTAL'),
    ('BalancedAttackOverwhelm', 'HARD BRUTAL'), ('BalancedAttackGround_MEDIUM', 'MEDIUM'),
    ('BalancedAttackWater_MEDIUM', 'MEDIUM'), ('BalancedAttackOverwhelm_MEDIUM', 'MEDIUM'),
    ('BalancedAttackGround_EASY', 'EASY'), ('BalancedAttackWater_EASY', 'EASY'))
# retail AlliedStandard (SDK OpeningMoves/AlliedOpeningMoves.xml), the Time 10s line's Account left to the variant
STANDARD = ('<Order Build="AlliedBarracks" />', None, '<Order Build="AlliedPowerPlant" />',
            '<Order Build="AlliedRefinery" />', '<Order Build="AlliedRefinery" />', '<Order Build="AlliedPowerPlant" />',
            '<Order Build="AlliedWarFactory" />', *['<Order Build="AlliedAntiInfantryVehicle_Ground" />'] * 3,
            '<Order Time="120s" />')


def acct_xml(account):
    """1AlliedBalanced rebuilt on its parent AlliedCoopBaseSkirmishPersonality (which has no OpeningMove), with one
    opening = retail AlliedStandard except `<Order Time="10s" Account=account Deposit="2000"/>` (retail: PRODUCTION).
    Rebuilt, not inheritFrom 1AlliedBalanced: its five OpeningMove lines have no id to remove. The model (private
    ai/player.py UNIT_ACCOUNT): the barracks spends the PRODUCTION account only; the opening's budget gives it 0 %, so a
    DEFENSE deposit leaves the barracks idle until the opening ends (~120 s after the wake)."""
    orders = [o or f'<Order Time="10s" Account="{account}" Deposit="2000" />' for o in STANDARD]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedCoopBaseSkirmishPersonality.xml" />',
        '  </Includes>',
        '  <SkirmishOpeningMove id="CNVAcctOpen" Side="PlayerTemplate:Allies">',
        *[f'    {o}' for o in orders],
        '  </SkirmishOpeningMove>',
        f'  <AIPersonalityDefinition id="{ACCT_PID}" PersonalityType="{ACCT_PID}"'
        ' inheritFrom="AlliedCoopBaseSkirmishPersonality" SkirmishPersonality="true">',
        '    <OpeningMove Name="CNVAcctOpen" Weight="100%" Difficulty="EASY MEDIUM HARD BRUTAL"/>',
        '    <StrategicState id="Cleanup" xai:joinAction="Remove"/>',
        *[f'    <StrategicState id="{s}" State="{s}" Difficulty="{d}"/>' for s, d in BALANCED_STATES],
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


NEW_PK = 'CNVNewPK'                   # aisknew / aisknew2 (check y): retail Peacekeeper under a new id = "a unit of ours"
NEW_BARRACKS = 'CNVAIBarracks'        # retail AlliedBarracks copied with a NEW_PK button (units/production.py), s1's
NEW_PID, NEW_STATE = 'CNVNew', 'CNVNewBuild'
NEW_AT = (0.0, 300.0)                 # the copied barracks, from the east base (clear of the yard)


DEAR_PK = 'CNVDearPK'                 # aiskcu / aiskcs (check yc): the Peacekeeper at build cost DEAR_COST, a unit that is
DEAR_BARRACKS = 'CNVAIBarracks2'      # never affordable, built from a second copied barracks; the personality lists it
DEAR_COST = 100000                    # in the build state, aiskcs also counts it as a structure for build purposes
DEAR_AT = (-300.0, 300.0)             # the second copied barracks, from the east base (clear of the first and the yard)


def new_pk(uid=NEW_PK, cost=None):
    """The Peacekeeper (SDK Allied/Units/AlliedAntiInfantryInfantry.xml) under NEW_PK, nothing else changed: the way a
    level's own unit reaches the game (its own template, built from a copied barracks). uid / cost (aiskcu, aiskcs):
    another id, and the build cost's Amount replaced."""
    import os
    import labpaths
    from parts import Unit
    path = os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', 'AlliedAntiInfantryInfantry.xml')
    x = open(path, encoding='utf-8').read()
    for old in ('id="AlliedAntiInfantryInfantry"', 'EditorName="AlliedAntiInfantryInfantry"'):
        assert x.count(old) == 1, old
        x = x.replace(old, old.replace('AlliedAntiInfantryInfantry', uid))
    if cost is not None:
        old = '<BuildCost Account="=$ACCOUNT_ORE" Amount="200"/>'
        assert x.count(old) == 1, old
        x = x.replace(old, old.replace('"200"', f'"{cost}"'))
    return Unit(uid, x, what='对照：原版维和换了 id（AI 会不会造"我们的"单位）')


# aiskblk* (check y): the new state's NEW_PK entry gets a BlockIfThingNearFactory filter (SDK States/AlliedBaseStates.xml
# writes it on the barracks' BEST_UNIT_EXPECTED entries: Rule ANY Relationship ENEMIES, IncludeThing dogs / bears),
# here NEUTRAL so nobody fights the blocker; build -> (blocker template, its distance north of the copied barracks)
BLOCK = {'near': ('SovietScoutInfantry', 120.0),      # bear radius 5: inside the default 150
         'far': ('SovietScoutInfantry', 400.0),       # outside
         'radius': ('AlliedPowerPlant', 190.0)}       # centre outside 150, inside 150 + the plant's ~54 circle


OFF_FLAG = 'CNVNever'                 # aiskoff (check y): a flag no script sets -> the new state's heuristic is 0


def new_xml(cap=None, block=None, off=False, dear=None, unitcap=None):
    """1AlliedBalanced plus one build state of its own (CNVNewBuild: ConstantHeuristic, BuildEntry NEW_PK FEWEST_UNIT,
    the shape of SDK States/AlliedBaseStates.xml AlliedBarracksBuildState_FEWEST) -- what a level's personality would
    need to list for the AI to build a unit of ours (B handoff 126). cap (aiskcap): + a SpecificUnitCap on NEW_PK at
    all four difficulties, a unit no parent personality caps (after the BuildState lines, as retail writes them).
    off (aiskoff): the heuristic is a ScriptedFlagHeuristic on a flag nobody sets (0 for good) -- NEW_PK stays listed
    in a build state that never builds, so a new Peacekeeper can only come from the unit builder (B handoff 151).
    dear (aiskcu / aiskcs): the state has a second entry DEAR_PK CONSTANT 1; dear == 'cs' also writes the personality's
    CountAsStructureForBuildPurposesFilter as BasePersonality.xml does, plus IncludeThing DEAR_PK (xsd: after the
    BuildState / SpecificUnitCap lines). unitcap (aiskucn): UnitCap lines (Cap, Difficulty), before the BuildState
    line as the xsd orders them."""
    caps = [] if cap is None else [
        f'    <SpecificUnitCap Unit="{NEW_PK}" Cap="{cap}" Difficulty="EASY MEDIUM HARD BRUTAL"/>']
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        f'    <Include type="all" source="DATA:CNVUnits/Data/{NEW_PK}.xml" />',
        *([f'    <Include type="all" source="DATA:CNVUnits/Data/{DEAR_PK}.xml" />'] if dear else []),
        '  </Includes>',
        f'  <AIBuildStateDefinition id="{NEW_STATE}">',
        '    <Heuristic>',
        f'      <ScriptedFlagHeuristic FlagName="{OFF_FLAG}"/>' if off else '      <ConstantHeuristic/>',
        '    </Heuristic>',
        *([f'    <BuildEntry Build="{NEW_PK}" Heuristic="FEWEST_UNIT"/>'] if block is None else [
            f'    <BuildEntry Build="{NEW_PK}" Heuristic="FEWEST_UNIT">',
            '      <BlockIfThingNearFactory Rule="ANY" Relationship="NEUTRAL">',
            f'        <IncludeThing>{BLOCK[block][0]}</IncludeThing>',
            '      </BlockIfThingNearFactory>',
            '    </BuildEntry>']),
        *([f'    <BuildEntry Build="{DEAR_PK}" Heuristic="CONSTANT" Score="1"/>'] if dear else []),
        '  </AIBuildStateDefinition>',
        f'  <AIPersonalityDefinition id="{NEW_PID}" PersonalityType="{NEW_PID}" inheritFrom="1AlliedBalanced">',
        *[f'    <UnitCap Cap="{c}" Difficulty="{d}"/>' for c, d in (unitcap or ())],
        f'    <BuildState id="{NEW_STATE}" State="{NEW_STATE}" Difficulty="EASY MEDIUM HARD BRUTAL"/>',
        *caps,
        *(['    <CountAsStructureForBuildPurposesFilter Rule="ANY" Include="STRUCTURE UNPACKS_INTO_BUILDING">',
           '      <ExcludeThing>AlliedMiner</ExcludeThing>',
           '      <ExcludeThing>SovietSurveyor</ExcludeThing>',
           '      <ExcludeThing>JapanRefineryEgg</ExcludeThing>',
           f'      <IncludeThing>{DEAR_PK}</IncludeThing>',
           '    </CountAsStructureForBuildPurposesFilter>'] if dear == 'cs' else []),
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


NEW_JAV = 'CNVNewJav'                 # aiskrand / aiskdiff (check s): the Javelin soldier under a new id, the same way
RAND_PID, RAND_STATE = 'CNVRand', 'CNVRandBuild'
DIFF_PID = 'CNVDiff'


def new_jav():
    """The Javelin soldier (SDK Allied/Units/AlliedAntiVehicleInfantry.xml) under NEW_JAV, as new_pk."""
    import os
    import labpaths
    from parts import Unit
    path = os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', 'AlliedAntiVehicleInfantry.xml')
    x = open(path, encoding='utf-8').read()
    for old in ('id="AlliedAntiVehicleInfantry"', 'EditorName="AlliedAntiVehicleInfantry"'):
        assert x.count(old) == 1, old
        x = x.replace(old, old.replace('AlliedAntiVehicleInfantry', NEW_JAV))
    return Unit(NEW_JAV, x, what='对照：原版标枪换了 id（随机打分 / 难度门）')


def _two_new_xml(pid, states):
    """1AlliedBalanced plus build states of its own: states = [(id, difficulty, [BuildEntry attribute strings])]."""
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
           '  <Tags></Tags>',
           '  <Includes>',
           '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
           f'    <Include type="all" source="DATA:CNVUnits/Data/{NEW_PK}.xml" />',
           f'    <Include type="all" source="DATA:CNVUnits/Data/{NEW_JAV}.xml" />',
           '  </Includes>']
    for sid, _, entries in states:
        out += [f'  <AIBuildStateDefinition id="{sid}">', '    <Heuristic>', '      <ConstantHeuristic/>',
                '    </Heuristic>', *[f'    <BuildEntry {e}/>' for e in entries], '  </AIBuildStateDefinition>']
    out.append(f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="1AlliedBalanced">')
    out += [f'    <BuildState id="{sid}" State="{sid}" Difficulty="{d}"/>' for sid, d, _ in states]
    out += ['  </AIPersonalityDefinition>', '</AssetDeclaration>', '']
    return '\n'.join(out)


def rand_xml():
    """aiskrand: one ConstantHeuristic state, NEW_PK RANDOM_UNIT 0%..30% and NEW_JAV RANDOM_UNIT "30".."100" -- the
    second written without '%' as retail AlliedBarracksBuildState_RANDOM is (SDK States/AlliedBaseStates.xml), so
    the bench tells whether a bare 30 is 30 % or 30 (never under a [0, 1) roll)."""
    return _two_new_xml(RAND_PID, [(RAND_STATE, 'EASY MEDIUM HARD BRUTAL',
                                    [f'Build="{NEW_PK}" Heuristic="RANDOM_UNIT" PercentLow="0%" PercentHigh="30%"',
                                     f'Build="{NEW_JAV}" Heuristic="RANDOM_UNIT" PercentLow="30" PercentHigh="100"'])])


def diff_xml():
    """aiskdiff: NEW_PK FEWEST_UNIT in a state hung at HARD only, NEW_JAV FEWEST_UNIT in one hung at MEDIUM only
    (the bench's skirmish AI plays MEDIUM): BuildState.Difficulty gates the state."""
    return _two_new_xml(DIFF_PID, [('CNVHardBuild', 'HARD', [f'Build="{NEW_PK}" Heuristic="FEWEST_UNIT"']),
                                   ('CNVMedBuild', 'MEDIUM', [f'Build="{NEW_JAV}" Heuristic="FEWEST_UNIT"'])])


AIDATA = 'AIData:AIData'              # aiskad / aiskfon / aiskfof (check a / fm): the global AIData under its retail id
AIDATA_RUNS = {'aiskad': {'TeamSeconds': '100000', 'MaxRecruitDistance': '1.0'},   # canary: no team should form
               'aiskfon': {'UseFormations': 'true'},     # retail's value, through the same override (the control)
               'aiskfof': {'UseFormations': 'false'}}


def aidata_xml(changes):
    """The SDK's SkirmishAI/AIData.xml (id AIData, in global.xml) with the attributes of `changes` rewritten: compiled
    into the map stream and linked over retail's (Mission.replaces -> make_campnew7.OVERRIDE)."""
    import re
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'SkirmishAI', 'AIData.xml'), encoding='utf-8') as f:
        xml = f.read()
    for k, v in changes.items():
        xml, n = re.subn(rf'(\s{k}=)"[^"]*"', rf'\1"{v}"', xml)
        assert n == 1, (k, n)
    return xml


UC_PID = 'CNVUnitCap'                 # aiskuc (check uc): 1AlliedBalanced plus two UnitCap lines
UC_CAPS = ((3, 'MEDIUM'), (1, 'EASY HARD BRUTAL'))   # the bench plays MEDIUM: 3 counts, 1 must be skipped


def unitcap_xml(caps=UC_CAPS):
    """1AlliedBalanced plus UnitCap lines (no SDK parent of it writes one; AlliedCoopBaseCampaignPersonality writes
    Cap 100 at all four). Engine (work/re l4_unitbuilder.md 1, l4_buildstate.md): the smallest Cap of the lines whose
    difficulty bit matches; the unit builder and the build states' unit entries both stop while the AI owns strictly
    more units than it; structures are not capped."""
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{UC_PID}" PersonalityType="{UC_PID}" inheritFrom="1AlliedBalanced">',
        *[f'    <UnitCap Cap="{c}" Difficulty="{d}"/>' for c, d in caps],
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


INERT_PID = 'CNVInert'                # aiskinb (check ib): 1AlliedBalanced with seven fields read as acting nowhere
# the seven personality fields D read as not acting in the 27 levels (work/re d126 section 2, d127 section 2), each at
# an extreme value; 1AlliedBalanced's own (BasePersonality.xml) in the comment. EmergencyManagerHandleConyardInDanger-
# AtDifficulty stays unwritten (empty in all 94 personalities: the gate D read as closing the three ConyardInDanger).
INERT = (('ConyardInDangerEmergencyUnderAttackTime', '1000s'),     # 5s
         ('ConyardInDangerEmergencyHealthPercent', '100%'),        # 70%
         ('ConyardInDangerEmergencyEngineerDistance', '5000.0'),   # 175.0
         ('HoldObjectBeaconRadius', '5000.0'),                     # 300 (XSD default)
         ('ResourceNodeValueRemainingForExpansion', '1000000'),    # 22000
         ('DefaultThreatFindRadius', '5000.0'),                    # 300.0
         ('MaxWallDestroyTimeToCountAsGoThroughWalls', '1000s'))   # 10s


def inert_xml():
    """1AlliedBalanced with every INERT field at its extreme: if none acts, the run reads as stock aiskirm's."""
    attrs = ' '.join(f'{k}="{v}"' for k, v in INERT)
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{INERT_PID}" PersonalityType="{INERT_PID}" inheritFrom="1AlliedBalanced"'
        f' {attrs}/>',
        '</AssetDeclaration>', ''])


SIDE_PID = 'CNVSideX'                 # aisksd1 / aisksd2 (check sd): work/re d123_side.md 3, S1 / S2
SIDE_FACTION = 'PlayerTemplate:Japan'   # s1's faction: neither CNVSideX's own Side (Soviet) nor what it may inherit
SIDE_JAPAN = ('1JapanBalanced', '2JapanAmbushDivision', '3JapanFleetCommand', '2JapanMechaWarfare')


def side_xml(skirmish):
    """1AlliedBalanced (a SkirmishPersonality) as CNVSideX with Side Soviet only and SkirmishPersonality written
    false (S1: the gate closed, as all 27 retail missions) or true (S2: the Side is checked against s1's Japan)."""
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{SIDE_PID}" PersonalityType="{SIDE_PID}" inheritFrom="1AlliedBalanced"'
        f' SkirmishPersonality="{str(bool(skirmish)).lower()}">',
        '    <Side>Soviet</Side>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


ARMY_INF, ARMY_VEH ='SovietAntiInfantryInfantry', 'SovietAntiVehicleVehicleTech1'   # conscript / Hammer tank
ARMY_N = 10                            # aiskvinf / aiskvveh (check z): what the player owns, idle behind its yard


def mission(name='CampAISkirm', money=MONEY, jav=False, lib=True, expire=None, umod=None, account=None,
            buffer=None, new=None, army=None, two=None, observe=False, cap=None, block=None, off=False,
            ptype=None, mintime=None, aidata=None, dear=None, dear_cost=DEAR_COST, power_more=None, mt_secs=300.0,
            carrier=None, unitcap=None, inert=False, power_adv=None, side=None):
    m = Mission(name=name, map=ai_map(resources.measured(niagara), lib), facts={'wake at': WAKE_AT, 'money': money})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
    if side == 'none':                   # aisksd4 (check sd, d123 S4): s1 with no aiPersonality at all
        m.facts['side case'] = 4
        del m.sides['s1']['aiPersonality']
    elif side is not None:               # aisksd1 / aisksd2 (check sd, d123 S1 / S2): CNVSideX on a Japanese s1
        m.facts['side case'] = 2 if side else 1
        m.sides['s1'] = {'playerFaction': SIDE_FACTION, 'aiPersonality': f'AIPersonalityDefinition:{SIDE_PID}'}
        m.assets.append((f'{SIDE_PID}.xml', side_xml(side), f'AIPersonalityDefinition:{SIDE_PID}'))
    if aidata is not None:               # aiskad / aiskfon / aiskfof: the global AIData overridden in the map stream
        m.facts['use formations'] = int(aidata.get('UseFormations', 'true') == 'true')
        m.assets.append(('CNVAIData.xml', aidata_xml(aidata), AIDATA))
        m.replaces.append(AIDATA)
    if expire is not None:               # aiskexp (check q): the same AI with SecondsTillTargetsExpire = expire
        m.facts['targets expire'] = expire
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{EXPIRE_PID}'
        m.assets.append((f'{EXPIRE_PID}.xml', expire_xml(expire), f'AIPersonalityDefinition:{EXPIRE_PID}'))
    if umod is not None:                 # aiskmod (check u): the same AI with the umod units' UnitModifier at 0
        m.facts['zeroed'] = len(umod)
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{UMOD_PID}'
        m.assets.append((f'{UMOD_PID}.xml', umod_xml(umod), f'AIPersonalityDefinition:{UMOD_PID}'))
    if ptype is not None:                # aiskpt / aiskpti (check pt): id CNVPtId, PersonalityType CNVPtType / unwritten
        m.facts['type written'] = int(ptype)
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{PT_PID}'
        m.assets.append((f'{PT_PID}.xml', ptype_xml(ptype), f'AIPersonalityDefinition:{PT_PID}'))
    if mintime is not None:              # aiskmt / aiskmto (check mt): a TECH entry with MinTime / ForceTime
        lo, hi, build, const, score = (*mintime, *(MT_TECH, *MT_CONST)[len(mintime) - 2:])
        m.facts['min time'], m.facts['force time'], m.facts['build'], m.facts['const'] = lo, hi, build, const
        m.facts['score'], m.facts['mt secs'] = score, mt_secs   # aiskmt20: watched 600 s after the wake
        if power_adv is not None:        # aiskmtp: BuildTechMinPowerAdvantage written on the personality
            m.facts['power advantage'] = power_adv
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{MT_PID}'
        m.assets.append((f'{MT_PID}.xml', mintime_xml(lo, hi, build, const, score, power_adv),
                         f'AIPersonalityDefinition:{MT_PID}'))
        for k, (tpl, site) in enumerate(MT_OWNED):
            m.put(tpl, site, side='s1', name=f'UNIT - CNV AI Owned {k}', role=f'ai owned {k}')
        more = lo == 0 if power_more is None else power_more   # aiskmt03: TECH 0/1 with the three plants only
        m.facts['plants'] = len(MT_POWER) + (len(MT_POWER_MORE) if more else 0)
        for k, (x, y) in enumerate(MT_POWER + (MT_POWER_MORE if more else ())):
            m.put('AlliedPowerPlant', 'east base', x, y, side='s1', angle=0.0, name=f'UNIT - CNV AI Power {k}',
                  role=f'ai power {k}')
    if unitcap is not None:              # aiskuc (check uc): UnitCap lines
        m.facts['unit cap'] = min(c for c, d in unitcap if 'MEDIUM' in d.split())
        if not new:                      # aiskucn: the lines go into CNVNew (new_xml) instead
            m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{UC_PID}'
            m.assets.append((f'{UC_PID}.xml', unitcap_xml(unitcap), f'AIPersonalityDefinition:{UC_PID}'))
    if inert:                            # aiskinb (check ib): the seven INERT fields at extremes
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{INERT_PID}'
        m.assets.append((f'{INERT_PID}.xml', inert_xml(), f'AIPersonalityDefinition:{INERT_PID}'))
    if buffer is not None:               # aiskpw0 / aiskpw3 (check x): DesiredExcessPowerBuffer = buffer
        m.facts['power buffer'] = buffer
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{POWER_PID}'
        m.assets.append((f'{POWER_PID}.xml', power_xml(buffer), f'AIPersonalityDefinition:{POWER_PID}'))
    if account is not None:              # aiskacp / aiskacd (check v): the opening's Deposit into `account`
        m.facts['production deposit'] = int(account == 'PRODUCTION')   # facts are numbers
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{ACCT_PID}'
        m.assets.append((f'{ACCT_PID}.xml', acct_xml(account), f'AIPersonalityDefinition:{ACCT_PID}'))
    if new is not None:                  # aisknew / aisknew2 (check y): s1 owns a barracks that builds NEW_PK too
        from units import production
        pk = new_pk()
        m.units += [pk, production.building('AlliedBarracks', [pk.id], NEW_BARRACKS)]
        m.facts['own build state'] = int(new)
        if new:                          # aisknew2: the personality lists NEW_PK in a build state of its own
            m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{NEW_PID}'
            if cap is not None:          # aiskcap (check y): + SpecificUnitCap NEW_PK = cap
                m.facts['new cap'] = cap
            if block is not None:        # aiskblk* (check y): + a BlockIfThingNearFactory, a neutral blocker
                thing, dist = BLOCK[block]
                m.facts['block distance'] = dist
                m.facts['block radius'] = int(block == 'radius')
                m.spawns.add(thing)
                m.put(thing, 'east base', NEW_AT[0], NEW_AT[1] + dist, side='neutral', angle=0.0,
                      name='UNIT - CNV AI Blocker', role='ai blocker')
            if off:                      # aiskoff (check y): the state never scores, NEW_PK still listed
                m.facts['state off'] = 1
            if dear:                     # aiskcu / aiskcs (check yc): the unaffordable unit, a second barracks building it
                m.facts['dear counts as structure'] = int(dear == 'cs')
                dpk = new_pk(DEAR_PK, dear_cost)
                m.units += [dpk, production.building('AlliedBarracks', [dpk.id], DEAR_BARRACKS)]
                m.put(DEAR_BARRACKS, 'east base', DEAR_AT[0], DEAR_AT[1], side='s1', angle=3.1416,
                      name='UNIT - CNV AI Dear Barracks', role='ai dear barracks')
            m.assets.append((f'{NEW_PID}.xml', new_xml(cap, block, off, dear, unitcap),
                             f'AIPersonalityDefinition:{NEW_PID}'))
        m.put(NEW_BARRACKS, 'east base', NEW_AT[0], NEW_AT[1], side='s1', angle=3.1416, name='UNIT - CNV AI New Barracks',
              role='ai new barracks')
    if two is not None:                  # aiskrand / aiskdiff (check s): a copied barracks building NEW_PK and NEW_JAV
        from units import production
        pk, jav = new_pk(), new_jav()
        m.units += [pk, jav, production.building('AlliedBarracks', [pk.id, jav.id], NEW_BARRACKS)]
        pid, xml = {'rand': (RAND_PID, rand_xml), 'diff': (DIFF_PID, diff_xml)}[two]
        m.facts['difficulty gate'] = int(two == 'diff')
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{pid}'
        m.assets.append((f'{pid}.xml', xml(), f'AIPersonalityDefinition:{pid}'))
        m.put(NEW_BARRACKS, 'east base', NEW_AT[0], NEW_AT[1], side='s1', angle=3.1416, name='UNIT - CNV AI New Barracks',
              role='ai new barracks')
    s1 = m.player('s1')
    yard = 'AlliedConstructionYard'
    if carrier == 'ext':                 # aiskxo (D round 105): the stock yard, ra3ext loaded, no CNVTeams host
        m.ext = True
    if observe or carrier == 'name':
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures',
                               'AlliedConstructionYard.xml'), encoding='utf-8') as f:
            xml = f.read()
        assert xml.count('<Behaviors>') == 1 and xml.count('id="AlliedConstructionYard"') == 1
    if observe:
        # Observe on the existing yard: no extra structure, power or AI candidate. D round 105: the yard keeps its
        # retail id (recompiled over retail's with the passive CNVTeams behavior added) -- a renamed copy
        # (CNVSkirmTeamsYard, before) changed the AI: retail data names AlliedConstructionYard (AlliedPowerPlant's
        # GameDependency, the budget states' ObjectOfTypeExists, ...), and aiskxn (the rename alone, no ra3ext) kept
        # AlliedScout dogless like the carrier while aiskxo (ra3ext, no host) matched stock. The player's yard gets
        # the behavior too; ra3ext's CNVTeams skips a host whose owner has no AI.
        xml = xml.replace('<Behaviors>', '<Behaviors>\n'
                          '  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>')
        link = f'GameObject:{yard}'
        m.assets.append(('CNVSkirmTeamsYard.xml', xml, link))
        m.replaces.append(link)
        m.ext = True
        m.name += 'C'  # keep the opt-in carrier's mod separate from the stock bench
    if carrier == 'name':
        # aiskxn (D round 105): the old carrier's rename alone -- a copy under its own id, no behavior, no ra3ext.
        yard = 'CNVSkirmTeamsYard'
        xml = xml.replace('id="AlliedConstructionYard"', f'id="{yard}"')
        m.units.append(Unit(yard, xml, names=dict(unit=yard), what='原建造厂改名复制（对照）', params=dict(every=15)))
    m.put(yard, 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.put('AlliedWarFactory', 'base factory', angle=3.1416, role='player factory')
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='player power')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    if army is not None:                 # aiskvinf / aiskvveh (check z): the player owns ARMY_N of `army` at home
        m.facts['player vehicles'] = int(army == ARMY_VEH)
        m.spawns.add(army)
        for k in range(ARMY_N):
            m.put(army, 'base yard', -150.0 - 60.0 * (k % 5), -150.0 + 60.0 * (k // 5), angle=0.0,
                  role=f'player army {k}')
    if jav:                              # aiskjav: one named Javelin soldier of s1's, 100 west of the yard (check e)
        m.spawns.add(JAV)
        m.put(JAV, 'east base', -100.0, 0.0, side='s1', angle=3.1416, name='UNIT - CNV AI Jav', role='ai jav')
        m.waypoint('out', 'CNV AI Out', 'east base', 0.0, -OUT_DIST)
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, money)])]
    return m


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {'aiskirm': mission, 'aiskirmc': lambda: mission(observe=True),
           'aiskxn': lambda: mission('CampAISkXN', carrier='name'),   # D 105: the carrier's rename alone
           'aiskxo': lambda: mission('CampAISkXO', carrier='ext'),    # D 105: ra3ext loaded, stock yard, no host
           'aiskirmlow': lambda: mission('CampAISkLow', money=15000),
           'aiskirm20': lambda: mission('CampAISk20', money=20000),    # check d: the first tower's time vs 50000
           'aiskjav': lambda: mission('CampAISkJav', jav=True),
           'aiskirmnl': lambda: mission('CampAISkNoLib', lib=False),
           'aiskexp': lambda: mission('CampAISkExp', expire=12.0),
           'aiskuc': lambda: mission('CampAISkUC', unitcap=UC_CAPS),   # check uc: UnitCap 3 MEDIUM, 1 others
           # D 124 U1: Cap 7 -- do the miners count (the army stops 1-2 lower than with miners left out)?
           'aiskuc7': lambda: mission('CampAISkUC7', unitcap=((7, 'MEDIUM'), (1, 'EASY HARD BRUTAL'))),
           # D 124 U2 (check ucn): aisknew2 + UnitCap 3 MEDIUM -- does the cap hold the build state's unit too?
           'aiskucn': lambda: mission('CampAISkUCN', new=True, unitcap=((3, 'MEDIUM'),)),
           'aiskinb': lambda: mission('CampAISkInB', inert=True),   # check ib: seven inert fields vs aiskirm ib
           'aiskmod': lambda: mission('CampAISkMod', umod=UMOD_ZERO),     # check q: SecondsTillTargetsExpire 12, not 5   # s1 without the container's Lib_Skirmish_Setup
           'aiskacp': lambda: mission('CampAISkAcP', account='PRODUCTION'),    # check v: the rebuilt AI, retail Account
           'aiskacd': lambda: mission('CampAISkAcD', account='DEFENSE'),
           'aiskpw0': lambda: mission('CampAISkPw0', buffer=0),       # check x: DesiredExcessPowerBuffer 0 (retail 100)
           'aiskpw3': lambda: mission('CampAISkPw300', buffer=300),   # check x: 300
           'aisknew': lambda: mission('CampAISkNew', new=False),      # check y: a barracks of s1's builds our unit too
           'aisknew2': lambda: mission('CampAISkNew2', new=True),     # check y: + a build state listing it
           'aiskcap': lambda: mission('CampAISkCap', new=True, cap=2),   # check y: + SpecificUnitCap 2 on it
           'aiskblkn': lambda: mission('CampAISkBlkN', new=True, block='near'),    # check y: blocker 120 away
           'aiskblkf': lambda: mission('CampAISkBlkF', new=True, block='far'),     # check y: 400 away
           'aiskblkr': lambda: mission('CampAISkBlkR', new=True, block='radius'),  # check y: a plant at 190
           'aiskoff': lambda: mission('CampAISkOff', new=True, off=True),   # check y: the state's heuristic 0
           'aiskcu': lambda: mission('CampAISkCU', new=True, dear='cu'),   # check yc: + a 100000-cost unit, filter retail
           'aiskcs': lambda: mission('CampAISkCS', new=True, dear='cs'),   # check yc: + the filter counts it as structure
           'aiskcu3': lambda: mission('CampAISkCU3', new=True, dear='cu', dear_cost=30000),   # check ycm: cu at 30000
           'aiskpt': lambda: mission('CampAISkPt', ptype=True),      # check pt: PersonalityType != id
           'aiskpti': lambda: mission('CampAISkPtI', ptype=False),   # check pt: PersonalityType not written
           'aisksd1': lambda: mission('CampAISkSd1', side=False),    # check sd: Side Soviet, Japan s1, gate closed
           'aisksd2': lambda: mission('CampAISkSd2', side=True),     # check sd: the same, SkirmishPersonality true
           'aisksd4': lambda: mission('CampAISkSd4', side='none'),   # check sd: s1 without an aiPersonality
           'aiskmt': lambda: mission('CampAISkMT', mintime=MT_TIMES['aiskmt']),      # check mt: MinTime 150 Force 151
           'aiskmto': lambda: mission('CampAISkMTO', mintime=MT_TIMES['aiskmto']),   # check mt: MinTime 250 Force 151
           'aiskmt0': lambda: mission('CampAISkMT0', mintime=(0, 1)),   # check mt: TECH 0/1, 6 plants (D82 G1 + G2)
           'aiskmt03': lambda: mission('CampAISkMT03', mintime=(0, 1), power_more=False),   # mt: TECH 0/1, 3 plants
           'aiskmt2': lambda: mission('CampAISkMT2', mintime=(200, 201), power_more=True),  # mt: TECH 200/201, 6
           'aiskmt20': lambda: mission('CampAISkMT20', mintime=(20, 22), power_more=True, mt_secs=600.0),  # 20/22
           # (20 / 21 compiled a map stream whose hash began d1 fb: the game took it for RefPack and crashed)
           'aiskmt14': lambda: mission('CampAISkMT14', mintime=(140, 142), power_more=True, mt_secs=600.0),
           'aiskmt16': lambda: mission('CampAISkMT16', mintime=(160, 162), power_more=True, mt_secs=600.0),
           'aiskmt15': lambda: mission('CampAISkMT15', mintime=(150, 152), power_more=True, mt_secs=600.0),  # G2e
           'aiskmt40': lambda: mission('CampAISkMT40', mintime=(400, 402), power_more=True, mt_secs=780.0),  # G2e
           # aiskmt40 with BuildTechMinPowerAdvantage 1000 (retail 1.25): does the f5857 tech building still come?
           'aiskmtp': lambda: mission('CampAISkMTP', mintime=(400, 402), power_more=True, mt_secs=780.0,
                                      power_adv=1000),
           'aiskmt99': lambda: mission('CampAISkMT99', mintime=(1000, 1002), power_more=True, mt_secs=780.0),
           'aiskmtc': lambda: mission('CampAISkMTC', mintime=(None, None)),          # check mt: CONSTANT 300 tower
           'aiskmtt': lambda: mission('CampAISkMTT', mintime=(200, 201, MT_CONST[0])),   # check mt: TECH 200/201 tower
           'aiskmtk': lambda: mission('CampAISkMTK', mintime=(None, None, MT_TECH, MT_TECH)),   # mt: CONSTANT 300 tech
           'aiskmtl': lambda: mission('CampAISkMTL', mintime=(None, None, MT_TECH, MT_TECH, 200)),   # mt: CONST 200 tech
           'aiskrand': lambda: mission('CampAISkRand', two='rand'),   # check s: RANDOM_UNIT 0%-30% / bare 30-100
           'aiskdiff': lambda: mission('CampAISkDiff', two='diff'),   # check s: a HARD-only state at MEDIUM
           'aiskvinf': lambda: mission('CampAISkVInf', army=ARMY_INF),   # check z: the player owns 10 conscripts
           'aiskvveh': lambda: mission('CampAISkVVeh', army=ARMY_VEH),   # check z: 10 Hammer tanks
           'aiskad': lambda: mission('CampAISkAD', aidata=AIDATA_RUNS['aiskad']),      # check a: AIData canary
           'aiskfon': lambda: mission('CampAISkFOn', aidata=AIDATA_RUNS['aiskfon']),   # check fm: UseFormations true
           'aiskfof': lambda: mission('CampAISkFOff', aidata=AIDATA_RUNS['aiskfof'])}  # check fm: false
