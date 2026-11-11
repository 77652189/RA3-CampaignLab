"""Engine probe: the skirmish AI team's EnterGarrisons (engine line B, layer 4; read back by
checks/engine_aigarrison.py; program: work/re l4_micro_engage.md 1.7 -- the turret-order routine, called in team states 2 / 4 / 5
only; model: RA3-EngineModel ra3model/ai/tactics.py, simai.Brain).

airetreat_bench's airet0 (12 of the player's Peacekeepers round the far plant, RetreatPowerAdvantage 0: the team
fights there, state 2, and dies) with one of retail's civilian apartments (AM_Apartments_01, neutral, 5 infantry;
docs/engine/garrison.md) on the team's way in:
  aigar1    the house 200 north of the far plant (where the team stands to fight, within 150), EnterGarrisons true
            (retail MEDIUM) -> the model: the team's Peacekeepers go into the house (it turns the AI's) and leave the team
  aigar0    the same, EnterGarrisons false -> nobody goes in
  aigarfar  EnterGarrisons true, the house 450 SOUTH (behind the plant from the team's way in; beyond 150 of the fight)
            -> nobody. (First made 450 north, on the way in: the northernmost fighter stood within 150 of it and one
            Peacekeeper went in at s20 -- per member, as the model has it, but not the 'too far' case.)
Facts: wake at, house (name).
"""
from missions import airetreat_bench as ar

HOUSE = 'AM_Apartments_01'
HOUSE_NAME = 'UNIT - CNV AI House'
NEAR, FAR = 200.0, -450.0                # north (+) of the far plant (3700, 2400); the AI's base is north (3850, 3400)
EAST = 0.0                               # towards the team's line from its base
# Round 121 (engine A): was 40, the house then stood on a grass tuft of niagara's scenery (CC_GRASS06 at 3733, 2599;
# tests/test_maps.py test_nothing_a_build_places_stands_on_scenery). The round-66 bench readings were at EAST 40.


def mission(mod, north, enter):
    m = ar.mission(mod, guards=ar.GUARDS, RetreatPowerAdvantage='0.0', EnterGarrisons=enter)
    m.put(HOUSE, 'carrier home', EAST, north, side='civ', name=HOUSE_NAME, role='house')
    m.facts['house'] = HOUSE_NAME
    return m


MISSION = {
    'aigar1': lambda: mission('CampAIGar1', NEAR, 'true'),
    'aigar0': lambda: mission('CampAIGar0', NEAR, 'false'),
    'aigarfar': lambda: mission('CampAIGarFar', FAR, 'true'),
}
