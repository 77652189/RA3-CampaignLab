"""Engine probe: when the skirmish AI's micro manager makes Imperial Warriors use their Bonzai charge (RUSH_ATTACK;
read back by checks/engine_aimicro.py; engine line B).

The data (SDK LogicCommand Command_JapanAntiInfantryInfantryBonzai): AISpecialPowerInfo Heuristic RUSH_ATTACK,
MICRO_MANAGER, TargetObjectInclude INFANTRY, HealthFraction 0.8, Distance 100, UseToCounterGarrison. The charge
(SpecialPower_JapanAntiInfantryInfantryBonzai, ReloadTime 30 s) puts AttributeModifier_..Bonzai on the warrior for 10 s:
ObjectStatus WEAPON_UPGRADED_02 (the check reads it with UNIT_HAS_OBJECT_STATUS), speed 150 %. The warrior's gun
(JapanAntiInfantryInfantryWeapon) has AttackRange 150, the charge sword 20.
The model (RA3-EngineModel ra3model/ai/micro.py rush): fire when the target is INFANTRY and (own health < 0.8 of max,
or the target within weapon range and < 100 away, 2D).

The enemy (s1, Allied faction -- the micro manager reads the unit's command set, not the faction) runs a personality
of this probe's own, as aidefense_bench.py: the Allied co-op base with every inherited strategic state removed and one
state, always on, StaticDefense of its yard (Distance 400, UseAestheticsManager false) with a team of exactly the two
warriors and MicroManager = the build's (StandardMicroManager: UpdateTime 0.5 s, no delays; _MEDIUM: 2 s, team delay
2..8 s after a fire). Two warriors stand 200 west of the s1 yard, 100 apart north-south, facing west; one player
engineer (unarmed infantry; the check keeps it at full health) stands D west of each warrior (the other engineer is
>= 134 away). Money 0. The AI wakes at WAKE_AT (the retail wake set, as aispecial_bench.py).
The warriors start as the player's (friends of the engineers, nothing fights) and are handed to s1 at HAND_AT, one
second after the wake: the program registers a unit's AISpecialPowerInfo only when it is made or changes hands while
the AI brain is not paused (work/re l4_specials.md), and aimicpre -- the warriors s1's from the start, the
AI asleep then -- never charged in 60 s.
Builds:
  aimicpre    D = 90,  StandardMicroManager, the warriors s1's from the start (no hand-over)
  aimicnear   D = 90,  StandardMicroManager            (in range and < 100: the model fires at the first round)
  aimicmed    D = 90,  StandardMicroManager_MEDIUM     (one fire, then a 2..8 s team delay before the other)
  aimicfar    D = 140, StandardMicroManager            (in range but >= 100: the model never fires)
  aimichurt   D = 140, StandardMicroManager, the warriors at 70 % health from the start (health < 0.8: fires)
  aimicmade   D = 90,  StandardMicroManager, no warriors placed: the script creates them on s1's team at HAND_AT
              (the AI awake) -- does a unit made after the wake charge where the handed-over ones did not?
  aimichunt   as aimicmade, but the team's tactic is a Targetless Hunt (as aistate_bench.py aihunt) instead of
              StaticDefense: does the micro manager run only under some tactics? (no: never recruited, see aitoggle)
  aimicxfer   as aimicmade, the script runs UNIT_AI_TRANSFER_ALL again right after making them (work/re
              l4_micro_gate.md: the recruiters refuse units on teamSoviet_1; the wake's transfer saw only the units then)
  aimicnearx  as aimicnear (hand-over), UNIT_AI_TRANSFER_ALL again right after the hand-over
  aimicbuilt  no warriors placed: the AI builds them itself (round 19) -- s1 owns a Japanese barracks (JapanBarracks)
              400 south of its yard and a power plant 400 north; an opening move of this probe's own (OPENER: a
              deposit of 1000 to PRODUCTION, then two warriors; the build state AlliedNeededUnits removed, retail
              budgets kept, as aitower_bench.py), money BUILT_MONEY at the wake. The units are unnamed: the check
              counts them by player (template owned, objects with the charge status). Two player conscripts (kept at
              full health) stand 400 south of the barracks and attack-move to it once s1 owns two warriors (the
              warriors get hurt: under 0.8 health the model fires whatever the distance). l4_micro_gate.md: the
              recruiters take units on the AI's default team; script-made ones sit on teamSoviet_1.
  aimicbuilth as aimicbuilt, the team a Targetless Hunt, no conscripts: are the built warriors recruited at all
              (they walk off) -- the by-player count cannot tell whose team a unit is on.
  aimicbuiltf as aimicbuilth with the conscripts (round 20): the Hunt team has recruited the warriors (builth) and
              now meets infantry and gets hurt -- in a running team, a target, under 0.8 health: do they charge?
Facts: wake at, hand at, distance, health, hunt (1: the Hunt tactic), built (1: the AI builds them), foes (1: built,
with the conscripts).
"""
from maps import niagara
from missions import aistate_bench as ab
from parts import Mission, Script

WAKE_AT = 10.0
HAND_AT = 11.0     # the warriors change hands (p1 -> s1) one second after the wake
PID = 'CNVMicroTest'
WARRIOR, ENGINEER = 'JapanAntiInfantryInfantry', 'AlliedEngineer'
WEST, APART = 200.0, 100.0


HUNT_HEAD = '''  <AIStrategicStateDefinition id="CNVStateMicro">
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <Tactic id="Hunt" Tactic="Hunt" Targetless="true">
'''
DEFEND_HEAD = '''  <AIStrategicStateDefinition id="CNVStateMicro" MaxTargets="1">
    <Heuristic>
      <ConstantHeuristic/>
    </Heuristic>
    <TargetHeuristic TargetHeuristic="FriendlyLandStructureHeuristic"/>
    <Tactic id="Defend" Tactic="StaticDefense" EndBehavior="DISBAND" Distance="400" UpdateTime="1s"
            CombatLeashSlack="1.5" UseAestheticsManager="false">
'''


def _state(micro, unit=WARRIOR, tactic='StaticDefense'):
    """tactic 'Hunt' (round 18): the attacking control, as aistate_bench.py _hunt (Targetless, no target heuristic)."""
    head = HUNT_HEAD if tactic == 'Hunt' else DEFEND_HEAD
    return head + f'''      <TeamTemplate MinUnits="2" MaxUnits="2" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"
                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="{micro}">
        <ObjectFilter Rule="ANY">
          <IncludeThing>{unit}</IncludeThing>
        </ObjectFilter>
      </TeamTemplate>
    </Tactic>
  </AIStrategicStateDefinition>'''


BUILT_MONEY = 2000
OPENER = 'CNVMicroOpener'
OPENER_DEPOSIT = 1000
BARRACKS_DY, PLANT_DY = -400.0, 400.0     # built: s1's factory south of its yard, its power plant north
CONSCRIPT = 'SovietAntiInfantryInfantry'
CONSCRIPT_DY = -80.0   # built: off the tree YP_Tree02 (3776, 2613) one stood on at 2 * BARRACKS_DY (test_maps)


def _opener(unit, n=2):
    # as aitower_bench.py (retail AIOpener_A08_AlliedSpecialForces): a deposit, the builds; the Time order ends it
    return [f'  <SkirmishOpeningMove id="{OPENER}" Side="PlayerTemplate:Allies">',
            f'    <Order Time="0s" Account="PRODUCTION" Deposit="{OPENER_DEPOSIT}" />',
            *[f'    <Order Build="{unit}" />'] * n, '    <Order Time="90s"/>', '  </SkirmishOpeningMove>']


SPOW_ID = 'CNVMicroSpow'


def _spow_xml(use, engage=True):
    """B round 113 (UseSpecialPowers): StandardMicroManager with its chain (Base) flattened -- the type cannot be
    inherited from (aitarget_bench._micro_xml) -- only UseSpecialPowers set by the build; round 115: and
    EngageHostileTargets (aimicengoff)."""
    return f'''  <AIMicroManagerData id="{SPOW_ID}" UpdateTime="0.5s" MaxTeamIdleTime="15s"
    MaxTeamIdleDistanceChange="50.0" MaxUnitIdleTime="10s" MaxUnitIdleDistanceChange="30.0"
    EnemySearchDistanceVisionMultiplier="1.8" MinTimeToKeepTempVisionRangeBonus="10s" SiegeWeaponBuffer="1.5"
    DodgeThreatsReactionTimeMin="0.5s" DodgeThreatsReactionTimeMax="0.5s" GatherTempVisionRangeBonus="1.5"
    RetreatTempVisionRangeBonus="1.5" MaxSecondaryDamageFraction="1.3" EngageHostileTargets="{'true' if engage else 'false'}"
    EngagePassiveTargets="true" EngageTacticalTarget="true" RetreatPowerAdvantage="0.2"
    RetreatMinDistanceFromBase="900.0" RetreatMinDistanceToFallback="500.0" AlphaStrikeTargetHealthPct="0.5"
    AlphaStrikeTargetTimeToKill="4.0" Crush="true" EnterGarrisons="true" EnterGarrisonableStructureDistance="150"
    EnterBaseDefensesWhenIdle="false" PullbackInjured="true" PullbackInjuredHealthPct="0.35" ReverseMove="true"
    DodgeThreats="true" UseSpecialPowers="{'true' if use else 'false'}">
    <RetreatBaseCriteria PreferredNotBaseTypes="CAPTURED" SortOrder="PREFER_CLOSEST"/>
    <IgnoreTargets Rule="ANY" Include="TIME_BOMB"/>
  </AIMicroManagerData>'''


def personality_xml(micro, unit=WARRIOR, tactic='StaticDefense', built=False, spow=None, engage=True):
    """built (round 19): the AI builds two `unit`s itself by an opening move. spow (round 113): None, or the
    UseSpecialPowers of this probe's own flattened StandardMicroManager (micro must then be SPOW_ID)."""
    removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
    first = []
    if built:
        removed += ['    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>']
        first = [f'    <OpeningMove Name="{OPENER}" Weight="100%">', '      <Heuristic>',
                 '        <ConstantHeuristic/>', '      </Heuristic>', '    </OpeningMove>']
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
        '  </Includes>',
        *([_spow_xml(spow, engage)] if spow is not None else []),
        _state(micro, unit, tactic),
        *(_opener(unit) if built else []),
        f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}">',
        *first,
        *removed,
        '    <StrategicState id="CNVStateMicro" State="CNVStateMicro"/>',
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, dist, micro='StandardMicroManager', health=100.0, hand=True, made=False, tactic='StaticDefense',
            xfer=False):
    facts = {'wake at': WAKE_AT, 'hand at': HAND_AT if hand or made else 0.0, 'distance': dist, 'health': health,
             'hunt': float(tactic == 'Hunt')}
    m = Mission(name=name, map=niagara, facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    m.assets.append((f'{PID}.xml', personality_xml(micro, tactic=tactic), f'AIPersonalityDefinition:{PID}'))
    m.cnv_units = (WARRIOR,)
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.spawns |= {WARRIOR}
    start, made_ = [], []
    m.cnv_named = {}       # part -> name of a unit the mission's scripts create (no cast role); the checks read it
    for k in range(2):
        dy = APART * (k - 0.5)
        w = f'UNIT - CNV AM Warrior {k + 1}'
        if made:           # created on s1's team by the script at HAND_AT, the AI awake
            m.waypoint(f'warrior {k + 1} spot', f'CNV AM Warrior Spot {k + 1}', 'east base', -WEST, dy)
            made_.append(w)
            m.cnv_named[f'warrior {k + 1}'] = w
        else:
            m.put(WARRIOR, 'east base', -WEST, dy, side='p1' if hand else 's1', angle=3.1416, name=w,
                  role=f'warrior {k + 1}')
        m.put(ENGINEER, 'east base', -WEST - dist, dy, name=f'UNIT - CNV AM Engineer {k + 1}',
              role=f'engineer {k + 1}')
        if health < 100.0:
            start.append(('UNIT_SET_HEALTH', w, health))
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                      *([('SET_MILLISECOND_TIMER', 'CNV AI Hand', HAND_AT)] if hand or made else []),
                                      *start]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
    # xfer: hand the new units to the AI brain again after they are made / change hands (round 18, l4_micro_gate.md:
    # the recruiters refuse a unit whose team is not the AI's own -- teamSoviet_1 -- and the wake's transfer saw only
    # the units there at the wake)
    again = [('UNIT_AI_TRANSFER_ALL', s1, 1)] if xfer else []
    if made:
        m.scripts.append(Script('CNV AI - Make', [('TIMER_EXPIRED', 'CNV AI Hand')],
                                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', w, WARRIOR, m.team('s1'),
                                  m.mark(f'warrior {k + 1} spot')) for k, w in enumerate(made_)] + again))
    elif hand:
        m.scripts.append(Script('CNV AI - Hand', [('TIMER_EXPIRED', 'CNV AI Hand')],
                                [('NAMED_TRANSFER_OWNERSHIP_PLAYER', r.name, s1) for r in m.roles('warrior')] + again))
    return m


def built_base(m, factory, money=BUILT_MONEY):
    """Round 19, the AI builds its units itself: s1's yard, `factory` south of it, a power plant north, the player's
    yard; a control spot west of the yard (the check makes a named unit there at the end) and the wake scripts."""
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put(factory, 'east base', 0, BARRACKS_DY, side='s1', name='UNIT - CNV AI Factory', role='ai factory')
    m.put('AlliedPowerPlant', 'east base', 0, PLANT_DY, side='s1', name='UNIT - CNV AI Plant', role='ai plant')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.waypoint('factory spot', 'CNV AI Factory Spot', 'east base', 0, BARRACKS_DY)
    m.waypoint('control spot', 'CNV AI Control Spot', 'east base', -WEST, 0)
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, money)]),
        # how many of the unit s1 owns, every frame (the mission's own counter; the check shows its own)
        Script('CNV AI - Owned', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', m.cnv_units[0], s1, 'CNV_AI_Owned')],
               once=False)]


def built(name, tactic='StaticDefense', foes=None, spow=None, engage=True):
    """tactic 'Hunt' (aimicbuilth): a membership test -- a Targetless Hunt team that takes the built warriors walks
    them off (the check counts them home round the barracks); no conscripts. foes (default: not Hunt) puts the
    conscripts in (aimicbuiltf: Hunt and conscripts -- recruited, with something to fight). spow (round 113,
    aimicspon / aimicspoff): the team's micro manager is SPOW_ID with UseSpecialPowers = spow; engage (round 115,
    aimicengoff): its EngageHostileTargets."""
    hunt = tactic == 'Hunt'
    foes = not hunt if foes is None else foes
    facts = {'wake at': WAKE_AT, 'hand at': 0.0, 'distance': 0.0, 'health': 100.0, 'hunt': float(hunt), 'built': 1.0,
             'foes': float(foes)}
    m = Mission(name=name, map=niagara, facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
    micro = 'StandardMicroManager' if spow is None else SPOW_ID
    if spow is not None:
        facts['use powers'] = float(spow)
        facts['engage hostile'] = float(engage)
    m.assets.append((f'{PID}.xml', personality_xml(micro, tactic=tactic, built=True, spow=spow, engage=engage),
                     f'AIPersonalityDefinition:{PID}'))
    m.cnv_units = (WARRIOR,)
    m.spawns |= {WARRIOR}
    built_base(m, 'JapanBarracks')
    if not foes:
        return m
    names = []
    for k in range(2):
        n = f'UNIT - CNV AM Conscript {k + 1}'
        names.append(n)
        m.put(CONSCRIPT, 'east base', APART * (k - 0.5), 2 * BARRACKS_DY + CONSCRIPT_DY, name=n,
              role=f'conscript {k + 1}')
    m.scripts.append(Script('CNV AM - Go', [('COUNTER', 'CNV_AI_Owned', 3, 2)],
                            m.order('attack_move', names, m.mark('factory spot'), 'p1')))
    return m


def dodge(name, enabled):
    """DodgeThreats only: recruited warriors fighting the same immortal conscripts.

    Native precision-strike beacon at 30 s, lifetime 4 s, DodgeSafetyDistance 200.
    No aircraft/bomb is dispatched: the beacon itself deals no damage or knockback.
    The check samples a published square before/during the beacon; this is not an
    exact reaction-time or safety-circle boundary measurement.
    """
    m = built(name, tactic='Hunt', foes=True, spow=False)
    m.assets = [(path, text.replace('DodgeThreats="true"',
                                   f'DodgeThreats="{str(enabled).lower()}"')
                          .replace('PullbackInjured="true"', 'PullbackInjured="false"'), key)
                for path, text, key in m.assets]
    m.facts.update({'dodge enabled': float(enabled), 'threat at': 30.0, 'threat lifetime': 4.0,
                    'sample half size': 150.0})
    m.cnv_named = {'beacon': 'CNV Dodge Beacon'}
    m.waypoint('dodge spot', 'CNV Dodge Spot', 'east base', 0, BARRACKS_DY - 100)
    m.spawns.add('AlliedPrecisionStrikeBeacon')
    m.scripts.append(Script('CNV Dodge - timer', [], [('SET_MILLISECOND_TIMER', 'CNV Dodge At', 30.0)]))
    m.scripts.append(Script('CNV Dodge - beacon', [('TIMER_EXPIRED', 'CNV Dodge At')],
                            [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', m.cnv_named['beacon'],
                              'AlliedPrecisionStrikeBeacon', m.team('p1'), m.mark('dodge spot'))]))
    return m


MISSION = {'aidodgeon': lambda: dodge('CampAIDodgeOn', True),
           'aidodgeoff': lambda: dodge('CampAIDodgeOff', False),
           'aimicbuilt': lambda: built('CampAIMicBuilt'),
           'aimicbuilth': lambda: built('CampAIMicBltH', tactic='Hunt'),
           'aimicbuiltf': lambda: built('CampAIMicBltF', tactic='Hunt', foes=True),
           'aimicspon': lambda: built('CampAIMicSpOn', tactic='Hunt', foes=True, spow=True),
           'aimicspoff': lambda: built('CampAIMicSpOff', tactic='Hunt', foes=True, spow=False),
           'aimicengoff': lambda: built('CampAIMicEgOff', tactic='Hunt', foes=True, spow=True, engage=False),
           'aimicpre':lambda: mission('CampAIMicPre', 90.0, hand=False),
           'aimicnear': lambda: mission('CampAIMicNear', 90.0),
           'aimicmed': lambda: mission('CampAIMicMed', 90.0, 'StandardMicroManager_MEDIUM'),
           'aimicfar': lambda: mission('CampAIMicFar', 140.0),
           'aimichurt': lambda: mission('CampAIMicHurt', 140.0, health=70.0),
           'aimicmade': lambda: mission('CampAIMicMade', 90.0, hand=False, made=True),
           'aimichunt': lambda: mission('CampAIMicHunt', 90.0, hand=False, made=True, tactic='Hunt'),
           'aimicxfer': lambda: mission('CampAIMicXfer', 90.0, hand=False, made=True, xfer=True),
           'aimicnearx': lambda: mission('CampAIMicNearX', 90.0, xfer=True)}
