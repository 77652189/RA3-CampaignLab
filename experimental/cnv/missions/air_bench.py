"""Engine probe mission (air rules, checks/engine_air.py): how a Soviet Twinblade (SovietAntiGroundAircraft) flies, and
what the anti-air weapons reach (SDK SageXML, sdk/RA3ModSDK3):

  Twinblade   Locomotor SovietAntiGroundAircraftLocomotor, Speed 150, PreferredHeight 130, Geometry BOX 16 x 11 (bounding
              circle 19.4), weapons SovietAntiGroundAircraftWeapon + AutoCannon, AttackRange 150, AntiMask GROUND /
              STRUCTURE / WATER (it cannot shoot air), VisionRange 200
  gun         SovietBaseDefenseAir, POWERED, SovietBaseDefenseAirFlakCannon AttackRange 300, AntiMask AIRBORNE_VEHICLE /
              AIRBORNE_INFANTRY, BOX 10 and BOX 15 (bounding circle 21.2), VisionRange 310
  flak        SovietAntiVehicleInfantry (its SovietAntiVehicleFlakLauncher_Aircraft: AttackRange 300, AntiMask AIRBORNE_*;
              ground launcher 175), CYLINDER radius 5, VisionRange 200
  guardian    AlliedAntiVehicleVehicleTech1, cannon 150, AntiMask WATER / GROUND / STRUCTURE: no anti-air

Variants (airframe = the p1 Twinblade, NO_ATTACK unless said):
  fly_flat / fly_sea / fly_cliff   S -> E 1 200 east on the three lanes of maps/probe_air (published waypoints s, e, mid)
  gun280 gun320 gun370   the s1 gun (and an s1 power plant 150 east) idle; the Twinblade hovers d north of its centre.
                         d: 300 - 20 (inside by any measure); 300 + (21.2 + 19.4) / 2 = 320 (inside only if the range is
                         taken edge to edge); 300 + 21.2 + 19.4 + 30 = 370 (outside by any measure)
  flak280 flak312 flak354   the s1 flak trooper idle: d 300 - 20; 300 + (5 + 19.4) / 2; 300 + 5 + 19.4 + 30 (rounded)
  noaa    an s1 guardian idle, the Twinblade 100 north
  a2g     the Twinblade (may fire) at S, an s1 guardian (NO_ATTACK) 600 north, NAMED_ATTACK at Go (2 s)
Published waypoints: s, e, mid (fly); u (the unit), h (the hovering Twinblade) (B, C); s, t (a2g).
"""
from maps import probe_air
from parts import Mission

HELI, GUN, FLAK, GUARDIAN, PLANT = ('SovietAntiGroundAircraft', 'SovietBaseDefenseAir', 'SovietAntiVehicleInfantry',
                                    'AlliedAntiVehicleVehicleTech1', 'SovietPowerPlant')
FLY = ('fly_flat', 'fly_sea', 'fly_cliff')
RANGE = {'gun': (280, 320, 370), 'flak': (280, 312, 354)}
VARIANTS = FLY + tuple(f'{k}{d}' for k, ds in RANGE.items() for d in ds) + ('noaa', 'a2g', 'land_gun', 'land_takeoff', 'land_idle', 'land_atk', 'land_still', 'land_flak')


def mission(name, variant):
    m = Mission(name=name, map=probe_air, facts={'variant': VARIANTS.index(variant)})
    if variant in FLY:
        lane = variant[4:]
        m.put(HELI, f'air {lane} S', role='heli', name='UNIT - CNV Air Heli')
        m.crew('Ah', 'p1')
        s, e = f'air {lane} S', f'air {lane} E'
        for part, label, site, dx in (('s', 'S', s, 0.0), ('e', 'E', e, 0.0), ('mid', 'Mid', s, 600.0)):
            m.waypoint(part, f'CNV Air {label}', site, dx, 0.0)
    elif variant.startswith('land_'):
        # the Twinblade stays where the map put it (on the ground); u its spot, h 30 east (land_takeoff's goal)
        k = variant[5:]
        m.put(HELI, 'air B', role='heli', name='UNIT - CNV Air Heli')
        if k == 'gun':
            m.put(GUARDIAN, 'air B', 0.0, 100.0, role='tank', side='s1', name='UNIT - CNV Air Target')
        elif k in ('takeoff', 'still'):      # still: the same, but no order (control)
            m.put(GUN, 'air B', 0.0, 280.0, role='unit', side='s1', name='UNIT - CNV Air Unit')
            m.put(PLANT, 'air B', 150.0, 280.0, side='s1')
        elif k == 'flak':      # control: an s1 flak trooper 280 north, the Twinblade idle (no order, NO_ATTACK)
            m.put(FLAK, 'air B', 0.0, 280.0, role='unit', side='s1', name='UNIT - CNV Air Unit')
            m.waypoint('f', 'CNV Air F', 'air B', 0.0, 280.0)
        else:
            m.put(GUARDIAN, 'air B', 0.0, 120.0, role='tank', side='s1', name='UNIT - CNV Air Target')
        m.waypoint('u', 'CNV Air U', 'air B')
        m.waypoint('h', 'CNV Air H', 'air B', 30.0, 0.0)
        m.crew('Ah', 'p1')
    elif variant == 'a2g':
        m.put(HELI, 'air D', role='heli', name='UNIT - CNV Air Heli')
        m.put(GUARDIAN, 'air D', 0.0, 600.0, role='tank', side='s1', name='UNIT - CNV Air Target')
        m.crew('Ah', 'p1')
        m.waypoint('s', 'CNV Air S', 'air D')
        m.waypoint('t', 'CNV Air T', 'air D', 0.0, 600.0)
    else:
        kind = variant.rstrip('0123456789')
        d = 100.0 if kind == 'noaa' else float(variant[len(kind):])
        unit = {'gun': GUN, 'flak': FLAK, 'noaa': GUARDIAN}[kind]
        m.put(unit, 'air B', role='unit', side='s1', name='UNIT - CNV Air Unit')
        if kind == 'gun':
            m.put(PLANT, 'air B', 150.0, 0.0, side='s1')
        # placed 30 west and moved at Go to h, 30 east, where it hovers (d is the distance north; the centre distance
        # is d + 0.2 at 300).  The move was for a Twinblade thought to stand on the ground when placed (11-07); the
        # land_* variants (11-08) show it is an air target from the start, so the move changes nothing
        m.put(HELI, 'air B', -30.0, d, role='heli', name='UNIT - CNV Air Heli')
        m.waypoint('u', 'CNV Air U', 'air B')
        m.waypoint('h', 'CNV Air H', 'air B', 30.0, d)
        m.crew('Ah', 'p1')
    return m


MISSION = {f'air_{v}': (lambda v=v: mission('CampAir' + str(VARIANTS.index(v)), v)) for v in VARIANTS}
