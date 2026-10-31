"""Engine probe for ADR 0010 (docs/adr/0010-question-first.md, the graybox): can the map's own scripts play the
player's side, so a "playstyle script" runs a level unattended and the counters give the verdict (win, time, losses,
money)? Read back by checks/drive.py.

Niagara map: the player's yard, a power plant and a barracks (Allied, money MONEY) at the start, three Guardians by
the base; the hawks (Soviet, s1) three Hammers at `front` (west end of the island bridge, the same bank).

  - commands: one script order each -- MOVE_NAMED_UNIT_TO, NAMED_ATTACK_NAMED, ATTACK_MOVE_TEAM_TO on the player's
    own default team (a8's assault already ran the last one, 2026-10-21);
  - production, how the player's barracks might be made to build: nothing (control), SKIRMISH_AI_START on the
    human player (what a retail mission does to wake an AI), PLAYER_ENABLE_UNIT_CONSTRUCTION;
  - run: the whole loop of a playstyle script -- every ORDER_EVERY s the team attack-moves at the enemy, every
    GIVE_EVERY s one more Guardian appears at the base (what the barracks would have made: "给兵" standing in for
    the economy), the run ends by itself (a flag stops the clock) and the readout is time, losses, the end state.

Facts: money, give every, order every.
"""
from maps import niagara
from parts import Mission

GUARDIAN, HAMMER, BARRACKS = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech1', 'AlliedBarracks'
MONEY, GIVE_EVERY, ORDER_EVERY = 6000, 20.0, 8.0


def mission(name='CampDrive', hammers=3, who='drive'):
    m = Mission(name=name, map=niagara, facts={'money': MONEY, 'give every': GIVE_EVERY, 'order every': ORDER_EVERY})
    m.spawns |= {BARRACKS, GUARDIAN, 'AlliedPowerPlant'}        # what the AI may build, the checks count
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard')
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power')
    m.put(BARRACKS, 'base factory', angle=3.1416, role='barracks')
    for k, (dx, dy) in enumerate(((0, -60), (0, 0), (0, 60))):
        m.put(GUARDIAN, 'base edge', dx, dy, name=f'UNIT - CNV {who} Guardian {k + 1}', role=f'guardian {k + 1}')
    for k in range(hammers):
        m.put(HAMMER, 'front', 0, -80 + 80 * k, side='s1', name=f'UNIT - CNV {who} Hammer {k + 1}',
              role=f'hammer {k + 1}')
    return m
