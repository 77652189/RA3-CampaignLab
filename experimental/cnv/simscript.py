"""L6 script vocabulary (ADR 0029, docs/engine/sim-layers.md): the name sets and spellings the script actions and
conditions share, moved out of sim.py so the action files (simact_*) can read them without importing sim. sim
re-exports each (`sim.TEAM_COMMANDS` still works)."""
import re

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
