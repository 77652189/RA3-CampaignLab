"""K6 engine probe (ADR 0016): what a map's own team does when a script orders it as one (checks/team.py).

Three convoy trucks stand on the west field, placed on the team `Probe` (the map's Teams chunk, Mission.crew; the
objects' originalOwner), 300 west of `far` (a mark and a trigger area): the questions are whether a placed unit joins
the team, whether a whole-team order reaches a unit made on the team later, what the team's conditions read when its
members die, and whether the survivors both move.

Published (the cast): truck 1 .. 3; marks far, late (where a late member is made); the team (m.teams['Probe']).
"""
from maps import island
from parts import Mission
from units import convoy

SPEED = 25.0


def mission(name='CampTeam', crewed=True):
    """crewed=False: the trucks on the player's default team (the control: does a truck move at all here)."""
    truck = convoy.truck(speed=SPEED)
    m = Mission(name=name, map=island, units=[truck])
    props = {'originalOwner': m.crew('Probe')} if crewed else {}
    for k, dy in enumerate((-60, 0, 60), 1):
        m.put(truck.id, 'west field', dy, -300, name=f'UNIT - CNV Probe Truck {k}', role=f'truck {k}',
              angle=0.0, props=props)
    m.waypoint('far', 'CNV Probe Far', 'west field', 0, 300)      # the train bench's leg: land all the way (x -300
    m.waypoint('late', 'CNV Probe Late', 'west field', 150, -300)  # was cut by a band of water, bench 2026-11-04)
    return m


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {
    'team': lambda: mission(),
    'team_plain': lambda: mission(name='CampTeamP', crewed=False),
}
