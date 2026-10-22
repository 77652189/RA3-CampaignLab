"""The Liberty's bench map (was make_campnew38.py's scene, CampNew38): the carrier south, three Hammers 450 north,
Guardians under its deck and one outside it, a war factory and a power plant. riders=True: the deck riders
(CNV_LibRider) in place of the Guardians, and the deck factory builds riders.

Published (the cast): carrier, crew (the Guardians or the riders), hammer, factory, power; all on the island's
west field (the start camera sees it) and base sites.
"""
from maps import island
from parts import Mission
from units import liberty as lib

CARRIER = 'UNIT - CNV Liberty'


def mission(riders=False, ride_flags=lib.RIDE_FLAGS, tag='', name='CampLiberty'):
    rider = lib.rider(f'CNV_LibRider{tag and "_" + tag}', parent=f'CNV_Liberty{tag and "_" + tag}',
                      flags=ride_flags) if riders else None
    crew = rider.id if riders else 'AlliedAntiVehicleVehicleTech1'
    unit = lib.liberty(f'CNV_Liberty{tag and "_" + tag}', tag=tag, factory=crew, riders=rider and rider.id)
    m = Mission(name=name, map=island, units=[unit] + ([rider] if riders else []))
    m.put('AlliedWarFactory', 'base factory', angle=3.1416, role='factory')
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power')
    m.put(unit.id, 'west field', 0, -60, name=CARRIER, role='carrier')
    for dx, dy in ((-60, 0), (60, 0), (0, -60), (-330, 0)):
        m.put(crew, 'west field', dx, dy - 60, role='crew')
    for dx in (-80, 0, 80):
        m.put('SovietAntiVehicleVehicleTech1', 'west field', dx, 390, side='s1', role='hammer')
    return m
