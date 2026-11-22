"""L6 script vocabulary (ADR 0029, docs/engine/sim-layers.md): the name sets and spellings the script actions and
conditions share, moved out of sim.py so the action files (simact_*) can read them without importing sim. sim
re-exports each (`sim.TEAM_COMMANDS` still works)."""
import re

from engine.world.handle import same_team

SHOW_FLAG = re.compile(r'CNV_\w+_Show_\d+')       # ctx.Talk.show: a 功能 line's caption is asked for
SCENE_FLAG = re.compile(r'CNV_\w+_InScene')       # ctx.Talk.scening
WON, LOST = 'Mission Won', 'Mission Lost'
# actions that change nothing the scripts ask about: logged on the timeline (the player sees or hears them)
SHOWN = {'SHOW_MILITARY_CAPTION': '通报', 'CAMPAIGN_CREATE_AUTO_SAVE': '存档', 'PATH_MUSIC_PLAY_EVENT': '音乐',
         'PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM': '战况音乐', 'NAMED_FLASH': '闪烁', 'NAMED_SHOW_INFOBOX': '信息框',
         'OBJECT_CREATE_RADAR_EVENT': '小地图闪点', 'PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT': '原版播报',
         'PLAY_SOUND_EFFECT': '配音', 'MOVIE_PLAY_RADAR': '头像'}
IGNORED = {'DISPLAY_COUNTER', 'HIDE_COUNTER',
           'CAMERA_LETTERBOX_BEGIN', 'CAMERA_LETTERBOX_END',
           'SET_COOP_AI_COMMAND_UI_ENABLED'}

TEAM_FOLLOWS = ('TEAM_FOLLOW_WAYPOINTS', 'TEAM_FOLLOW_WAYPOINTS_EXACT', 'TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS',
                'TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT')      # Sim.order_follow
TEAM_COMMANDS = ('MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO', 'TEAM_ATTACK_NAMED', 'TEAM_GUARD_AREA', 'TEAM_STOP') \
    + TEAM_FOLLOWS                                                  # E3: need a live team
# a script's power or button by itself, as simcoverage.refined names it
BUTTON_ACTIONS = ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY',
                  'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED')
# a condition's comparison argument (0 <, 1 <=, 2 ==, 3 >=, 4 >, 5 !=)
CMP = {0: lambda a, b: a < b, 1: lambda a, b: a <= b, 2: lambda a, b: a == b, 3: lambda a, b: a >= b,
       4: lambda a, b: a > b, 5: lambda a, b: a != b}
# RA3's own actions and conditions (docs/engine/script-semantics.md 6: in neither source): run as we understand them,
# each run that uses one lists it under 'ra3 only'
RA3_ONLY = {'ATTACK_MOVE_NAMED_UNIT_TO', 'ATTACK_MOVE_TEAM_TO', 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION',
            'UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION', 'UNIT_TELEPORT_TO_WAYPOINT', 'UNIT_GUARD_AREA',
            'UNIT_SET_HEALTH', 'NAMED_SET_MAX_HEALTH', 'UNIT_CHANGE_OBJECT_STATUS',
            'SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', 'SET_MISSION_OBJECTIVE_STATUS', 'LINK_MISSION_OBJECTIVE_TO_OBJECT',
            'LINK_MISSION_OBJECTIVE_TO_WAYPOINT', 'CAMPAIGN_CREATE_AUTO_SAVE', 'MOVE_CAMERA_TO_NAMED',
            'PLAYER_SET_PLAYER_POWER_POINTS', 'PLAYER_SET_MAX_PLAYER_POWER_POINTS', 'SET_PLAYER_MONEY_TO_COUNTER',
            'SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', 'ALLOW_DISALLOW_ONE_BUILDING', 'ALLOW_DISALLOW_ONE_UPGRADE',
            'SKIRMISH_AI_MAKE_BASE', 'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', 'SKIRMISH_AI_TRANSFER_ALL', 'SKIRMISH_AI_USE_REBUILD_SYSTEM',
            'SKIRMISH_AI_USE_REPAIRS', 'UNIT_AI_TRANSFER_ALL', 'PATH_MUSIC_PLAY_EVENT', 'SKIRMISH_AI_START',
            'PLAYER_TOGGLE_SKIRMISH_AI',
            'PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM', 'CAMERA_ENTERED_AREA',
            'PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', 'SET_COUNTER_TO_COUNTER', 'COUNTER_MATH_COUNTER',
            'COUNTER_MATH_VALUE'}
# AssetTypeLocomotorTemplate.xsd's Surface, in order: TEAM_INSIDE_AREA_*'s third argument is an index into it (D 119)
SURFACES = ('GROUND', 'WATER', 'CLIFF', 'AIR', 'RUBBLE', 'OBSTACLE', 'IMPASSABLE', 'DEEP_WATER')
# a script's relation argument (its name, or the index retail writes) -> Sim.relation's word (D 115 5, INFERRED order)
RELATION_OF = {'Enemy': 'ENEMIES', 0: 'ENEMIES', 'Neutral': 'NEUTRAL', 1: 'NEUTRAL', 'Friend': 'ALLIES', 2: 'ALLIES'}


def refined(name, a):
    """An action's name told apart by what it is told to do where that matters: the status bit, the power, the button
    (simcoverage.refined's spelling: NAME:ARG)."""
    if name == 'UNIT_CHANGE_OBJECT_STATUS' and len(a) > 1:
        return f'{name}:{a[1][2] if isinstance(a[1], tuple) else a[1]}'
    if name in BUTTON_ACTIONS and len(a) > 1:
        return f'{name}:{a[1]}'
    return name


def team_crew(sim, team, every=False):
    """The team the game finds by this name, looked up without making it (D 115): its living members (the oldest
    instance's, as Sim.members; every instance's with `every`, as TEAM_HAS_UNITS), None when none goes by it -- an
    AI's (Sim.named_team) with no instance now (bench 11-11 aiskirm:m: a ..._0_0 team's TEAM_COMPARE_NUM_MEMBERS
    == n held for no n until made), a map / script team nobody joined (team_active; INFERRED for the conditions D
    115 did not read). Every team action / condition asking whether the team is there asks here (review 1121pp #1
    and its class: an AI tactic team turned away as no map team)."""
    named = sim.named_team(team)
    if named is not None:
        if not named[0]:
            sim.used.add('ai team absent')
        return named[1] if named[0] else None
    if not sim.team_active(team):
        return None
    return [b for b in sim.bodies.values() if b.alive and same_team(b.team, team)] if every else sim.members(team)
