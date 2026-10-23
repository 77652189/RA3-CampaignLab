"""The paper crane's bench scene: the flier on the west field, an enemy Guardian on the east field (1800 away, in the
shroud), a point 700 short of it to stop at -- inside the crane's 900, outside a retail flier's 500.

retail=True: retail's Twinblade flies instead (the control). Published (the cast): scout, target; marks stop.
"""
from maps import island
from parts import Mission
from units import crane as cr

SHORT = 700.0


AA = 'AlliedAntiAirVehicleTech1'                # the IFV, missiles up
BEAR = 'SovietScoutInfantry'                    # the war bear: a stealth detector (300)


def hide(name='CampCraneH', **unit):
    """Two cranes on the west field, each sent over two enemy IFVs 300 apart (A west, B east); B's IFVs have a war
    bear with them. Published (the cast): crane A, crane B; marks over A, over B."""
    u = cr.crane(**unit)
    m = Mission(name=name, map=island, units=[u])
    for k, dx in (('A', -100.0), ('B', 300.0)):
        m.put(u.id, 'west field', dx, -350, name=f'UNIT - CNV Crane {k}', role=f'crane {k}')
        for j, sx in enumerate((-30, 30)):
            m.put(AA, 'west field', dx + sx, 100, side='s1', name=f'UNIT - CNV AA {k}{j + 1}', role=f'aa {k} {j + 1}')
        m.waypoint(f'over {k}', f'CNV Crane Over {k}', 'west field', dx, 100)
    m.put(BEAR, 'west field', 300, 140, side='s1', name='UNIT - CNV Bear', role='bear')
    return m


def mission(name='CampCrane', retail=False, **unit):
    u = cr.crane(**unit)
    m = Mission(name=name, map=island, units=[] if retail else [u])
    m.put('SovietAntiGroundAircraft' if retail else u.id, 'west field', 100, 0, name='UNIT - CNV Scout', role='scout')
    m.put('AlliedAntiVehicleVehicleTech1', 'east field', 0, 0, side='s1', name='UNIT - CNV Target', role='target')
    m.waypoint('stop', 'CNV Crane Stop', 'east field', -SHORT, 0)
    return m
