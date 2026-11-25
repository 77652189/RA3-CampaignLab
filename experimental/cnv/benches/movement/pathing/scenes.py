"""Standalone scenes for the movement and pathing benches."""


FENCE_RINGS = {                                       # name: (template, piece length, offset from the west field, open)
    'wood': ('TH_JapanFence01', 21.0, (-230.0, 230.0), False),
    'stone': ('OK_StoneFence01', 31.0, (230.0, 230.0), False),
    'palace': ('MJ_PalaceWall01', 60.0, (-230.0, -230.0), False),
    'open': ('TH_JapanFence01', 21.0, (230.0, -230.0), True),
}


REROUTE_WARRIOR = 'JapanAntiInfantryInfantry'


REROUTE_SQUAD = 5


REROUTE_ANGLE = 0.0


def reroute_bridges():
    from maps import festival

    return {k: ((p[0] + q[0]) / 2, p[1]) for k, (p, q) in zip(('middle', 'north', 'south'), festival.BRIDGES)}


def engine_air():
    """Engine probe mission (air rules, benches/movement/pathing/checks.py#engine_air): how a Soviet Twinblade (SovietAntiGroundAircraft) flies, and
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
    return dict(MISSION=MISSION)


def blackcanyon():
    """A2's map (maps/blackcanyon.py) bare, for the bench questions its draft left (checks/blackcanyon.py)."""
    from maps import blackcanyon
    from parts import Mission
    from units import unsellable

    SPAWNS = {'SovietAntiNavyShipTech1', 'SovietAntiAirShip', 'SovietAntiVehicleVehicleTech1',
              'SovietAntiVehicleVehicleTech2'}                    # what the checks count


    def mission(name='CampCanyon'):
        # the dam sections' plant the player cannot sell (checks/blackcanyon.py lock)
        return Mission(name=name, map=blackcanyon, spawns=SPAWNS, units=[unsellable.copy('AlliedPowerPlant')])


    MISSION = {'canyon': mission}
    return dict(MISSION=MISSION)


def fence():
    """Do a courtyard's fences bar infantry? (A4 redesign, docs/design/a4-redesign.md: the plazas as flat courtyards closed
    by houses, walls and lanterns, one gate; plans/a4.md 待办.) On the festival map's west field, four square rings of
    retail Japanese-town props, each closed but the control: TH_JapanFence01 (Tokyo Harbor's wooden fence, a destructible
    prop), OK_StoneFence01 (Osaka's stone fence, a crushable obstacle), MJ_PalaceWall01 (Mount Fuji's palace wall, a
    structure), and TH_JapanFence01 again with one side left open (the control: the soldiers can get in, the count
    works). Three peacekeepers of the player's stand outside each; fence in checks.py sends them to the middle.

    Published (the cast): soldier <ring> 1-3 (the rings: RINGS); marks inside <ring>; facts ring (half-side).
    """
    import math

    from maps import festival
    from parts import Mission

    HALF = 110.0                                    # a ring's half-side
    RINGS = FENCE_RINGS


    SOLDIER = 'AlliedAntiInfantryInfantry'


    def ring(m, name, tmpl, length, dx, dy, open_side):
        """Pieces round a square of HALF about (dx, dy) off the west field, each side from corner to corner (a piece
        every 0.9 of its length, so they overlap); open_side: the south side left out."""
        n = math.ceil(2 * HALF / (0.9 * length))
        step = 2 * HALF / n
        for k in range(n + 1):
            u = -HALF + step * k
            sides = [(u, HALF, 0.0), (-HALF, u, math.pi / 2), (HALF, u, math.pi / 2)]
            if not open_side:
                sides.append((u, -HALF, 0.0))
            for x, y, a in sides:
                m.put(tmpl, 'west field', dx + x, dy + y, side='civ', angle=a)
        for j in range(3):
            m.put(SOLDIER, 'west field', dx - 40 + 40 * j, dy - HALF - 120, name=f'UNIT - CNV Fence {name} {j + 1}',
                  role=f'soldier {name} {j + 1}', angle=1.5708)
        m.waypoint(f'inside {name}', f'CNV Fence Inside {name}', 'west field', dx, dy)


    def mission(name='CampFence'):
        m = Mission(name=name, map=festival)
        for k, (tmpl, length, (dx, dy), open_side) in RINGS.items():
            ring(m, k, tmpl, length, dx, dy, open_side)
        m.facts.update({'ring': HALF})
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'fence': lambda: mission(),
    }
    return dict(MISSION=MISSION)


def engine_formation_player():
    """Engine line D 92: the player's formation switches on the bench (benches/movement/pathing/checks.py#engine_formation_player `s`).

    CampFormS = the probe mission CampFormP (two lanes of two Guardian tanks + two Peacekeepers, CNVProbe copies) with both
    switches on every unit (units/formation.py: 同速 / 密集 toggles next to their own buttons) and CNVSync's host for the
    player. Published facts: 'sync command' / 'dense command' (NAMED_USE_COMMANDBUTTON_ABILITY presses them).
    """
    from units import formation
    from .checks import FORMATION_LANES as LANES, FORMATION_X0 as X0, engine_formation_player

    probe_mission = engine_formation_player()['MISSION']['engine_formation_player']
    HOST = 'CNVSyncHost'


    def sync_mission():
        m = probe_mission()
        m.name = 'CampFormS'
        m.units = [formation.switches(u) for u in m.units] + [formation.host(HOST)]
        m.put(HOST, 'pace start', X0 - 500.0 - 250.0, LANES['plain'] - 1200.0 - 300.0, role='sync host',
              name='UNIT - CNV Form Sync Host')
        m.facts['sync command'] = formation.ids('sync')['command']
        m.facts['dense command'] = formation.ids('dense')['command']
        return m


    MISSION = {'engine_formation_sync': sync_mission}
    return dict(MISSION=MISSION)


def jammer():
    """The jammer's bench scene on the west field (east of its middle: the west edge is shallows): ours 100 east of a
    north-south lane, an enemy Mecha Tengu at the lane's south end, a goal at its north end -- 458 of the 750 between
    them lie within the jammer's 250.

    Published (the cast): jammer, mech; marks goal.
    """
    from maps import island
    from parts import Mission
    from units import jammer as ja

    X = 100.0
    MECH = 'JapanAntiInfantryVehicle'               # the Mecha Tengu


    def mission(name='CampJam', side='s1', mech=MECH, **unit):
        """side: whose the mech is -- s1 (the enemy) or p1 (ours: the jammer slows friends too); mech: its template
        (a flier, to ask whether the jam reaches aircraft)."""
        u = ja.jammer(**unit)
        m = Mission(name=name, map=island, units=[u])
        m.put(u.id, 'west field', X + 100, 0, name='UNIT - CNV Jammer', role='jammer')
        m.put(mech, 'west field', X, -350, side=side, name='UNIT - CNV Mech', role='mech', angle=1.5708)
        m.waypoint('goal', 'CNV Jam Goal', 'west field', X, 400)
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'jammer': lambda: mission(),
        'jammer_own': lambda: mission(name='CampJamOwn', side='p1'),
        'jammer_air': lambda: mission(name='CampJamAir', mech='SovietAntiGroundAircraft'),
        'jammer_jet': lambda: mission(name='CampJamJet', mech='SovietFighterAircraft'),
        'jammer_kirov': lambda: mission(name='CampJamKir', mech='SovietBomberAircraft'),
    }
    return dict(MISSION=MISSION)


def engine_land():
    """Engine probe mission: which way an amphibious transport takes to a shore point behind a quay (benches/movement/pathing/checks.py#engine_land;
    the simulator's rule R7, docs/story/sim-vs-bench-a4.md: the A4 bench landed the Ghost King ~12 s after the horn,
    the simulator ~29 s -- its transport found the quay too high and went round by the southern slip, 2420 long, where
    the straight way is 630).

    A4's map (sapporo) as A4's horn uses it: the transport (JapanLightTransportVehicle) made at the sea point (4750,
    2900) and sent to the beach site (4120, 2900), on the quay 120 above the water.
    """
    from maps import sapporo
    from parts import Mission, Script

    BOAT = 'JapanLightTransportVehicle'
    SEA, SHORE = (4750.0, 2900.0), (4120.0, 2900.0)


    def mission():
        m = Mission(name='CampLand', map=sapporo, facts={})
        m.waypoints['CNV Land Sea'], m.marks['sea'] = SEA, 'CNV Land Sea'
        m.waypoints['CNV Land Shore'], m.marks['shore'] = SHORE, 'CNV Land Shore'
        # the game's start camera is off the map's view (K5): cut it to the quay, held inside the 'whole' border's view
        m.waypoints['CNV Land View'], m.views['CNV Land View'] = (3940.0, 2970.0), (950.0, 540.0, 4050.0, 4460.0)
        m.scripts.append(Script('CNV Land - camera', [], [('MOVE_CAMERA_TO', 'CNV Land View', 0.1, 0.0, 0.0, 0.0)]))
        return m


    MISSION = {'engine_land': mission}
    return dict(MISSION=MISSION)


def lock():
    """The lock gate's bench scene (A5 / S5, Panama): on the festival map's canal, between its middle and north bridges,
    a gate (a never-melting wall the map places across the water) and an Allied ship south of it; the goal is north of
    the gate. Does a structure on the water bar a ship, and does deleting it let the ship through?

    Published (the cast): gate, ship; marks goal.
    """
    from maps import festival
    from parts import Mission
    from missions.lock_bench import gate_unit

    X = sum(festival.CANAL) / 2                      # the canal's middle
    GATE_Y, SHIP_Y, GOAL_Y = 3000.0, 2750.0, 3250.0
    SHIP = 'AlliedAntiNavyShipTech1'                # the assault destroyer


    def mission(name='CampLock', gate=True):
        u = gate_unit()
        m = Mission(name=name, map=festival, units=[u])
        if gate:
            m.put(u.id, 'island', X - 2500, GATE_Y - 2500, side='neutral', name='UNIT - CNV Lock Gate', role='gate',
                  angle=0.0)
        m.put(SHIP, 'island', X - 2500, SHIP_Y - 2500, name='UNIT - CNV Lock Ship', role='ship', angle=1.5708)
        m.waypoint('goal', 'CNV Lock Goal', 'island', X - 2500, GOAL_Y - 2500)
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'lock': lambda: mission(),
    }
    return dict(MISSION=MISSION)


def engine_pace_placed():
    """出动 + 齐步 on the bench (plan.py pace_placed, docs/engine/pathing.md 5b): two Tsunami tanks (75) and two Imperial
    Warriors (50) placed at the harbour on the festival map from the start, sent off together at SEND to the west field
    (down the road, ~2 850). Built twice: `paceplaced` with 齐步 (the tanks placed as their 67 % paced copies, granted the
    upgrade as they are sent, released inside the west field's area) and `paceplacedn` without (the plain tanks). The
    player's yard is on the north base, out of the road's sight; the enemy's barracks on the north camp.

    Published (the cast): tank 1 / 2, foot 1 / 2, yard, camp; facts: send at.
    """
    import plan

    SEND = 30.0


    def plan_dict(together):
        return {
            '关卡': 'pp', '名字': '齐步出动试验', '地图': 'festival',
            '阵营': {'我': '盟军', '敌': '帝国'},
            '开局': {'资金': 5000, '部队': [
                {'单位': '建造厂', '在': 'north base', '角色': 'yard'},
                {'单位': '兵营', '在': 'north camp', '阵营': '敌', '角色': 'camp'},
                {'单位': '帝国武士', '数量': 2, '在': 'harbour', '阵营': '敌', '角色': 'foot'},
                {'单位': '海啸坦克', '数量': 2, '在': 'harbour', '阵营': '敌', '角色': 'tank'}]},
            '规则': [{'当': f'开局 + {SEND:g}',
                    '做': [{'出动': ['foot', 'tank'], '打': 'west field', '齐步': '是' if together else '否'}]}],
            '段': [{'名字': '一'}],
        }


    def mission(together=True):
        name = 'CampPacePl' if together else 'CampPacePlN'
        m = plan.Compiler(plan_dict(together), name).compile()
        m.facts['send at'] = SEND
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'paceplaced': lambda: mission(True),
        'paceplacedn': lambda: mission(False),
    }
    return dict(MISSION=MISSION)


def reroute():
    """An ice wall across one way: do the troops on it go round by another? (A4 redesign, docs/design/a4-redesign.md, phase
    3's "冰从封门变成改道".) On the festival map: the canal's three bridges (middle on the road, north, south) are the only
    ways west from the harbour; their east ends sit on the quay, a strip of land between the canal and the sea. A Japanese
    squad (five imperial warriors: the tsunami tank swims, bench 2026-10-27) stands on the quay north of the middle
    bridge; reroute in checks.py sends it west, a never-melting ice wall across the quay between it and the middle bridge
    (canal to sea): the middle bridge is shut to it, the north one open.

    Bench 2026-10-27, a wall on the middle bridge itself stopped nobody, at the deck's middle or its east end: the warriors
    walked through it (the bridge object's own way over ignores what stands on it; its deck is drawn much longer than
    festival.BRIDGES, ~3615 to ~4090).

    Published (the cast): warrior 1-5 (the enemy's); marks goal (the west field), wall (on the quay); the wall's unit and
    its angle (ANGLE); bridges() their middles.
    """
    from maps import festival
    from parts import Mission
    from units import icewall as iw

    WARRIOR = REROUTE_WARRIOR


    SQUAD = REROUTE_SQUAD


    # the quay at the middle bridge (bench map 2026-10-27): the canal's east edge x ~3823, the sea from ~4167; the deck
    # ~80 either side of the road
    QUAY = (3823.0, 4167.0)
    WALL_Y, THICK = 2650.0, 120.0       # across the quay north of the deck (the wall along x)
    SQUAD_X, SQUAD_Y = 3880.0, 2800.0               # on the quay's road north of the wall


    def wall_unit():
        # a little longer than the quay is wide: canal edge to sea, no gap
        return iw.wall(id='CNV_RerouteWall', length=QUAY[1] - QUAY[0] + 40, thick=THICK, lifetime=None, health=5000,
                       what='改道测试的冰墙：横在中桥北边的码头上，从运河边到海边，不化、不打碎')


    def mission(name='CampDetour'):
        m = Mission(name=name, map=festival, units=[wall_unit()])
        hx, hy = m.site('harbour')
        for j in range(1, SQUAD + 1):
            m.put(WARRIOR, 'harbour', SQUAD_X - hx + 40 * ((j - 1) % 2), SQUAD_Y - hy + 40 * (j - 1), side='s1',
                  name=f'UNIT - CNV Reroute Warrior {j}', role=f'warrior {j}', angle=3.1416)
        m.waypoint('goal', 'CNV Reroute Goal', 'west field')
        m.waypoint('wall', 'CNV Reroute Wall', 'harbour', sum(QUAY) / 2 - hx, WALL_Y - hy)
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'reroute': lambda: mission(),
    }
    return dict(MISSION=MISSION)


def engine_spots():
    """Engine probe for sim.HOLD_SPOTS (benches/movement/pathing/checks.py#engine_spots; work/re/handoff.md round 113): three convoy trucks, each
    on a team of its own (a4's staggered convoy, 分批: devices/convoy.py), sent to one waypoint -- do they stand apart?

    Island map, west field (offsets from 'west field'): truck 1-3 (units/convoy.truck, speed 50, the player's) at
    (-50, -150) / (-50, 0) / (-50, 150), facing east, on crews T1-T3; mark `spot` at (+500, 0), ~550 east of them
    (at -250 they stood in the sea, bench 11-09: the west field's shore is east of what its site says; scripts1's tanks
    drove from -50 to +600).
    Published (the cast): truck 1-3; mark spot; teams T1-T3.
    """
    from maps import island
    from parts import Mission
    from units import convoy

    START_X, SPOT_X = -50.0, 500.0
    ROWS = (-150.0, 0.0, 150.0)


    def mission(name='CampSpots'):
        u = convoy.truck(speed=50.0)
        m = Mission(name=name, map=island, units=[u])
        for k, dy in enumerate(ROWS, 1):
            m.put(u.id, 'west field', START_X, dy, angle=0.0, name=f'UNIT - CNV Spots Truck {k}', role=f'truck {k}',
                  props={'originalOwner': m.crew(f'T{k}')})
        m.waypoint('spot', 'CNV Spots Spot', 'west field', SPOT_X, 0.0)
        return m


    MISSION = {'engine_spots': mission}
    return dict(MISSION=MISSION)


def train():
    """The armoured train's bench scene on the west field: a track of three legs (north 600, east 300, south 600) from
    the train's start, and -- with enemies=True -- three enemy conscripts 150 east of the first leg's far end, 500 from
    the start: out of reach until it drives past.

    Published (the cast): train, enemy (with enemies); marks stop 1 .. 3 (the track's waypoints, in order), astray (a
    point off the track, where a player might send it).
    """
    from maps import island
    from parts import Mission
    from units import train as tr

    TRACK = [(0, 300), (300, 300), (300, -300)]     # from the start at (0, -300), west field offsets
    X = 0.0


    def mission(name='CampTrain', enemies=False, **unit):
        u = tr.train(**unit)
        m = Mission(name=name, map=island, units=[u])
        m.put(u.id, 'west field', X, -300, name='UNIT - CNV Train', role='train', angle=1.5708)
        for k, (dx, dy) in enumerate(TRACK):
            m.waypoint(f'stop {k + 1}', f'CNV Train Stop {k + 1}', 'west field', X + dx, dy)
        m.waypoint('astray', 'CNV Train Astray', 'west field', X - 300, -100)      # off the track, west of the first leg
        if enemies:
            for dy in (160, 200, 240):
                m.put('SovietAntiInfantryInfantry', 'west field', X + 150, dy, side='s1', role='enemy')
        return m


    def braked(name='CampTrainB', **unit):
        """The brake, and fire: three conscripts far off north-east (600 from the train) and a point 150 east of its start
        to send them to; the start is a mark too. Published (the cast): train, enemy 1 .. 3; marks stop 1 .. 3, start,
        by start."""
        m = mission(name=name, **unit)
        for k, dy in enumerate((-40, 0, 40)):
            m.put('SovietAntiInfantryInfantry', 'west field', X + 300, 200 + dy, side='s1',
                  name=f'UNIT - CNV Enemy {k + 1}', role=f'enemy {k + 1}')
        m.waypoint('start', 'CNV Train Start', 'west field', X, -300)
        m.waypoint('by start', 'CNV Train By Start', 'west field', X + 150, -300)
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'train': lambda: mission(),
        'train_braked': lambda: braked(),
        'train_fight': lambda: mission(name='CampTrainF', enemies=True),
    }
    return dict(MISSION=MISSION)


def engine_waypath():
    """Engine probe for the waypoint paths (*_FOLLOW_WAYPOINTS; engine_waypath in checks.py; work/re/handoff.md round 143):
    three convoy trucks in the west field, the ground spots/scripts1 drove on (spots_bench.py).

    Island map, offsets from 'west field': truck 1-3 (units/convoy.truck, speed 50, the player's) at (-50, -150) /
    (-50, 0) / (-50, 150), facing east, truck 1 alone on crew W1, 2 and 3 on crew W23; marks A (+150, -150), B (+450,
    -150), C (+450, +150) -- an L the paths run along (the checks label them: the paths are each check's own) -- and N
    (+420, -40), by B, where truck 1 is first sent to join a path there.
    Published (the cast): truck 1-3; marks A, B, C, N; teams W1, W23.
    """
    from maps import island
    from parts import Mission
    from units import convoy
    from missions.waypath_bench import MARKS, ROWS, START_X


    def mission(name='CampPath'):              # + the check's name: 15 characters at most ('CampPathExact')
        u = convoy.truck(speed=50.0)
        m = Mission(name=name, map=island, units=[u])
        for k, dy in enumerate(ROWS, 1):
            m.put(u.id, 'west field', START_X, dy, angle=0.0, name=f'UNIT - CNV Waypath Truck {k}', role=f'truck {k}',
                  props={'originalOwner': m.crew('W1' if k == 1 else 'W23')})
        for part, (dx, dy) in MARKS.items():
            m.waypoint(part, f'CNV Waypath {part}', 'west field', dx, dy)
        return m


    MISSION = {'engine_waypath': mission}
    return dict(MISSION=MISSION)


BENCHES = (
    engine_air, blackcanyon, fence, engine_formation_player, jammer,
    engine_land, lock, engine_pace_placed, reroute, engine_spots,
    train, engine_waypath,
)
