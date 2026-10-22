"""The Liberty's bench map (was make_campnew38.py's scene, CampNew38): the carrier south, three Hammers 450 north,
Guardians under its deck and one outside it, a war factory and a power plant. riders=True: the deck riders
(CNV_LibRider) in place of the Guardians, and the deck factory builds riders."""
from maps import island
from parts import Mission, Obj
from units import liberty as lib

A = (1180.0, 2375.0)                             # make_campnew28's anchor: the start camera sees it
CARRIER_AT = (A[0], A[1] - 60)
CARRIER = 'UNIT - CNV Liberty'


def mission(riders=False, ride_flags=lib.RIDE_FLAGS, tag='', name='CampLiberty'):
    rider = lib.rider(f'CNV_LibRider{tag and "_" + tag}', parent=f'CNV_Liberty{tag and "_" + tag}',
                      flags=ride_flags) if riders else None
    crew = rider.id if riders else 'AlliedAntiVehicleVehicleTech1'
    unit = lib.liberty(f'CNV_Liberty{tag and "_" + tag}', tag=tag, factory=crew, riders=rider and rider.id)
    m = Mission(name=name, map=island, units=[unit] + ([rider] if riders else []), names=unit.names)
    m.names['crew'] = crew
    m.objects += [Obj('AlliedWarFactory', island.START[0] + 300, island.START[1] + 60, angle=3.1416),
                  Obj('AlliedPowerPlant', island.START[0] + 300, island.START[1] - 140, angle=0.0),
                  Obj(unit.id, *CARRIER_AT, name=CARRIER)]
    m.objects += [Obj(crew, CARRIER_AT[0] + dx, CARRIER_AT[1] + dy) for dx, dy in ((-60, 0), (60, 0), (0, -60), (-330, 0))]
    m.objects += [Obj('SovietAntiVehicleVehicleTech1', A[0] + dx, A[1] + 390, side='s1') for dx in (-80, 0, 80)]
    return m
