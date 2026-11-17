"""L6 script vocabulary (ADR 0029, docs/engine/sim-layers.md): the name sets and spellings the script actions and
conditions share, moved out of sim.py so the action files (simact_*) can read them without importing sim. sim
re-exports each (`sim.TEAM_COMMANDS` still works)."""
import re

SHOW_FLAG = re.compile(r'CNV_\w+_Show_\d+')       # ctx.Talk.show: a 功能 line's caption is asked for
SCENE_FLAG = re.compile(r'CNV_\w+_InScene')       # ctx.Talk.scening
WON, LOST = 'Mission Won', 'Mission Lost'

TEAM_FOLLOWS = ('TEAM_FOLLOW_WAYPOINTS', 'TEAM_FOLLOW_WAYPOINTS_EXACT', 'TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS',
                'TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT')      # Sim.order_follow
TEAM_COMMANDS = ('MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO', 'TEAM_ATTACK_NAMED', 'TEAM_GUARD_AREA', 'TEAM_STOP') \
    + TEAM_FOLLOWS                                                  # E3: need a live team
# a script's power or button by itself, as simcoverage.refined names it
BUTTON_ACTIONS = ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY',
                  'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED')


def refined(name, a):
    """An action's name told apart by what it is told to do where that matters: the status bit, the power, the button
    (simcoverage.refined's spelling: NAME:ARG)."""
    if name == 'UNIT_CHANGE_OBJECT_STATUS' and len(a) > 1:
        return f'{name}:{a[1][2] if isinstance(a[1], tuple) else a[1]}'
    if name in BUTTON_ACTIONS and len(a) > 1:
        return f'{name}:{a[1]}'
    return name
