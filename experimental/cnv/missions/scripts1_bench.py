"""Engine probe mission (inventory batch 1, checks/engine_scripts1.py): the script names work/re/l2_scripts1.md read --
TEAM_TRANSFER_TO_PLAYER, UNIT_IDLE_FOR_SECONDS, TEAM_HUNT / NAMED_HUNT, TEAM_USE_COMMANDBUTTON_ABILITY and the
conditions PLAYER_IS_HUMAN_OR_AI_PERSONALITY, UNIT_HAS_OBJECT_STATUS, HAS_FINISHED_AUDIO / _VIDEO.

Island map. West field (offsets from 'west field'):
  go 1, go 2     the player's Guardians on crew Go at (-50, -100) / (-50, 0), facing east; mark `far` 650 east of
                 them (+600, -50), `home` where they stand (-50, -50) (at -300 they stood in the sea: bench 11-08)
  idle 1, idle 2 the player's Guardians (not on a crew) at (-50, 150) / (-50, 250); mark `far2` (+600, 200)
  pk 1, pk 2     the player's Peacekeepers on crew Pk at (-100, -300) / (0, -300)
East field (offsets from 'east field', ~1800 from the west field): the enemy (s1, Soviet_1, no AI) Guardians
  hunt 1, hunt 2 on crew Hunt at (0, -60) / (0, 60); `lone`, alone at 'east 1' -- marks `ehome`, `lhome` where they stand
Published (the cast): go 1-2, idle 1-2, pk 1-2, hunt 1-2, lone; marks far, far2, home, ehome, lhome; teams Go, Pk, Hunt.
"""
from maps import island
from parts import Mission

TANK, PK = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'


def _n(part):
    return f'UNIT - CNV S1 {part}'


def mission(name='CampScr1'):
    m = Mission(name=name, map=island, units=[], facts={})
    m.spawns |= {TANK, PK}
    go, pk, hunt = m.crew('Go'), m.crew('Pk'), m.crew('Hunt', 's1')
    for k, dy in enumerate((-100.0, 0.0), 1):
        m.put(TANK, 'west field', -50.0, dy, angle=0.0, name=_n(f'Go {k}'), role=f'go {k}', props={'originalOwner': go})
    for k, dy in enumerate((150.0, 250.0), 1):
        m.put(TANK, 'west field', -50.0, dy, angle=0.0, name=_n(f'Idle {k}'), role=f'idle {k}')
    for k, dx in enumerate((-100.0, 0.0), 1):
        m.put(PK, 'west field', dx, -300.0, angle=0.0, name=_n(f'Pk {k}'), role=f'pk {k}', props={'originalOwner': pk})
    for k, dy in enumerate((-60.0, 60.0), 1):
        m.put(TANK, 'east field', 0.0, dy, side='s1', angle=3.1416, name=_n(f'Hunt {k}'), role=f'hunt {k}',
              props={'originalOwner': hunt})
    m.put(TANK, 'east 1', side='s1', angle=3.1416, name=_n('Lone'), role='lone')
    m.waypoint('far', 'CNV S1 Far', 'west field', 600.0, -50.0)
    m.waypoint('home', 'CNV S1 Home', 'west field', -50.0, -50.0)
    m.waypoint('far2', 'CNV S1 Far2', 'west field', 600.0, 200.0)
    m.waypoint('ehome', 'CNV S1 EHome', 'east field')
    m.waypoint('lhome', 'CNV S1 LHome', 'east 1')
    return m


MISSION = {'engine_scripts1': mission}
