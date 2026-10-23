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


def turrets(name='CampLibT', n=2):
    """Deck turrets, A against B: two carriers 450 apart on the west field, A's turrets with retail's weapons, B's
    with our all-round copies (reach 300); their own drones out of play (range 1) and an enemy Hammer 120 north of
    each -- it cannot shoot back at aircraft. Published (the cast): carrier A / B, hammer A / B."""
    m = Mission(name=name, map=island)
    for k, dx, fixed in (('A', -150.0, False), ('B', 300.0, True)):
        t = lib.turret(f'CNV_LibTurret{k}', fixed=fixed)
        c = lib.liberty(f'CNV_Liberty_{k}', tag=k, drone_range=1, turrets=n, turret_id=t.id)
        m.units += [c, t]
        m.put(c.id, 'west field', dx, -60, name=f'UNIT - CNV Liberty {k}', role=f'carrier {k}')
        m.put('SovietAntiVehicleVehicleTech1', 'west field', dx, 60, side='s1', name=f'UNIT - CNV Hammer {k}',
              role=f'hammer {k}')
    return m


def loose(name='CampLibL'):
    """The bisect when no deck turret fired: turrets placed on the map on their own (no SlavedUpdate, no carrier;
    bench 2026-10-22: neither the fixed weapons nor retail's fired so, nor with a WeaponCategory, on BaseObject or
    BaseVehicle), both with the fixed weapons; C with a target chooser that picks targets (UnitAITargetChooserData
    CanPickDynamicTargets, the armoured train's fix), D without, an enemy Hammer 100 north of each.
    Published (the cast): turret C / D, hammer C / D."""
    m = Mission(name=name, map=island)
    for k, dx, chooser in (('C', -150.0, True), ('D', 300.0, False)):
        t = lib.turret(f'CNV_LibTurret{k}', slaved=False, chooser=chooser)
        m.units.append(t)
        m.put(t.id, 'west field', dx, -40, name=f'UNIT - CNV Turret {k}', role=f'turret {k}')
        m.put('SovietAntiVehicleVehicleTech1', 'west field', dx, 60, side='s1', name=f'UNIT - CNV Hammer {k}',
              role=f'hammer {k}')
    return m


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
