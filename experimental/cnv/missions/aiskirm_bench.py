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
# the pool 'defaultSkirmishTeam' + player (0x87e320) and a strategic state's instances '%s_%s_%u_%u' (0x8d8f25:
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


def mission(name='CampAISkirm', money=MONEY, jav=False, lib=True):
    m = Mission(name=name, map=ai_map(niagara, lib), facts={'wake at': WAKE_AT, 'money': money})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.put('AlliedWarFactory', 'base factory', angle=3.1416, role='player factory')
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='player power')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
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
           'aiskjav': lambda: mission('CampAISkJav', jav=True),
           'aiskirmnl': lambda: mission('CampAISkNoLib', lib=False)}   # s1 without the container's Lib_Skirmish_Setup
