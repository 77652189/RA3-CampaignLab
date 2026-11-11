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
from maps import niagara
from parts import Mission, Script

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
                'escort': 'EscortMCV_StaticDefense_0_0'}
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


def new_pk():
    """The Peacekeeper (SDK Allied/Units/AlliedAntiInfantryInfantry.xml) under NEW_PK, nothing else changed: the way a
    level's own unit reaches the game (its own template, built from a copied barracks)."""
    import os
    import labpaths
    from parts import Unit
    path = os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', 'AlliedAntiInfantryInfantry.xml')
    x = open(path, encoding='utf-8').read()
    for old in ('id="AlliedAntiInfantryInfantry"', 'EditorName="AlliedAntiInfantryInfantry"'):
        assert x.count(old) == 1, old
        x = x.replace(old, old.replace('AlliedAntiInfantryInfantry', NEW_PK))
    return Unit(NEW_PK, x, what='对照：原版维和换了 id（AI 会不会造"我们的"单位）')


def new_xml():
    """1AlliedBalanced plus one build state of its own (CNVNewBuild: ConstantHeuristic, BuildEntry NEW_PK FEWEST_UNIT,
    the shape of SDK States/AlliedBaseStates.xml AlliedBarracksBuildState_FEWEST) -- what a level's personality would
    need to list for the AI to build a unit of ours (B handoff 126)."""
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        f'    <Include type="all" source="DATA:CNVUnits/Data/{NEW_PK}.xml" />',
        '  </Includes>',
        f'  <AIBuildStateDefinition id="{NEW_STATE}">',
        '    <Heuristic>',
        '      <ConstantHeuristic/>',
        '    </Heuristic>',
        f'    <BuildEntry Build="{NEW_PK}" Heuristic="FEWEST_UNIT"/>',
        '  </AIBuildStateDefinition>',
        f'  <AIPersonalityDefinition id="{NEW_PID}" PersonalityType="{NEW_PID}" inheritFrom="1AlliedBalanced">',
        f'    <BuildState id="{NEW_STATE}" State="{NEW_STATE}" Difficulty="EASY MEDIUM HARD BRUTAL"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


ARMY_INF, ARMY_VEH = 'SovietAntiInfantryInfantry', 'SovietAntiVehicleVehicleTech1'   # conscript / Hammer tank
ARMY_N = 10                            # aiskvinf / aiskvveh (check z): what the player owns, idle behind its yard


def mission(name='CampAISkirm', money=MONEY, jav=False, lib=True, expire=None, umod=None, account=None,
            buffer=None, new=None, army=None):
    m = Mission(name=name, map=ai_map(niagara, lib), facts={'wake at': WAKE_AT, 'money': money})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
    if expire is not None:               # aiskexp (check q): the same AI with SecondsTillTargetsExpire = expire
        m.facts['targets expire'] = expire
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{EXPIRE_PID}'
        m.assets.append((f'{EXPIRE_PID}.xml', expire_xml(expire), f'AIPersonalityDefinition:{EXPIRE_PID}'))
    if umod is not None:                 # aiskmod (check u): the same AI with the umod units' UnitModifier at 0
        m.facts['zeroed'] = len(umod)
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{UMOD_PID}'
        m.assets.append((f'{UMOD_PID}.xml', umod_xml(umod), f'AIPersonalityDefinition:{UMOD_PID}'))
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
            m.assets.append((f'{NEW_PID}.xml', new_xml(), f'AIPersonalityDefinition:{NEW_PID}'))
        m.put(NEW_BARRACKS, 'east base', NEW_AT[0], NEW_AT[1], side='s1', angle=3.1416, name='UNIT - CNV AI New Barracks',
              role='ai new barracks')
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
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
MISSION = {'aiskirm': mission, 'aiskirmlow': lambda: mission('CampAISkLow', money=15000),
           'aiskirm20': lambda: mission('CampAISk20', money=20000),    # check d: the first tower's time vs 50000
           'aiskjav': lambda: mission('CampAISkJav', jav=True),
           'aiskirmnl': lambda: mission('CampAISkNoLib', lib=False),
           'aiskexp': lambda: mission('CampAISkExp', expire=12.0),
           'aiskmod': lambda: mission('CampAISkMod', umod=UMOD_ZERO),     # check q: SecondsTillTargetsExpire 12, not 5   # s1 without the container's Lib_Skirmish_Setup
           'aiskacp': lambda: mission('CampAISkAcP', account='PRODUCTION'),    # check v: the rebuilt AI, retail Account
           'aiskacd': lambda: mission('CampAISkAcD', account='DEFENSE'),
           'aiskpw0': lambda: mission('CampAISkPw0', buffer=0),       # check x: DesiredExcessPowerBuffer 0 (retail 100)
           'aiskpw3': lambda: mission('CampAISkPw300', buffer=300),   # check x: 300
           'aisknew': lambda: mission('CampAISkNew', new=False),      # check y: a barracks of s1's builds our unit too
           'aisknew2': lambda: mission('CampAISkNew2', new=True),     # check y: + a build state listing it
           'aiskvinf': lambda: mission('CampAISkVInf', army=ARMY_INF),   # check z: the player owns 10 conscripts
           'aiskvveh': lambda: mission('CampAISkVVeh', army=ARMY_VEH)}   # check z: 10 Hammer tanks
