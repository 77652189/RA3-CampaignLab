"""MetaImpactNugget (step N3e): a warhead's shocks knock grounded bodies into flight. Its context is the collision's
(weapon, attacker, centre), apart from the frame's volleys, so it is not in registry.ORDER: the host calls detonate at a
projectile's arrival (or launch at a known centre) and tick once a frame before the frame's arrivals land. `host` is
combat.host.EffectHost: the world, the peers (impact_flights, knock_hold, attachments, has_model_condition,
destroy), gap, and the game-data reads (body_of, ground_z, smooth_z, velocity, ground_launch,
trajectory, landing_hold) with the drowning book knock_drowns (Damage's)."""
import math

TAG = 'MetaImpactNugget'


def detonate(host, weapon, target, centre, attacker):
    """Dispatch the non-damage payload of a projectile arrival: no centre -> a living target's half height."""
    if not weapon.get('meta_impacts'):
        return
    if centre is None and target.alive:
        height = host.body_of(target.template)[0]
        if height is not None:
            centre = (target.x, target.y, host.ground_z(target.x, target.y) + height/2)
    if centre is None:
        host.gap(TAG, '缺少弹体实际爆心，未派发冲击')
    else:
        launch(host, weapon, centre, attacker)


def fire_at_self(host, weapon, attacker, target):
    """An instant DamageDealtAtSelfPosition shot's shocks (A363, the retail shotgun; bench engine_knock_self): the
    centre is the shooter's feet, the arc about its line to the target. INFERRED: the shooter itself never takes its
    own shock (bench: the shooter stood at the centre unshocked; self or relation not told apart)."""
    centre = (attacker.x, attacker.y, host.ground_z(attacker.x, attacker.y) if attacker.z is None else attacker.z)
    launch(host, weapon, centre, attacker, axis=(target.x - attacker.x, target.y - attacker.y))


def launch(host, weapon, centre, attacker, axis=None):
    """Dispatch ordinary immediate warhead shocks, separately from damage radius.

    First slice: default Physics, grounded bodies, landings on level, lower or higher ground (Physics P3: a landing
    moved off the water, a vehicle's drowning: Ground.landing / drowns). Other cases
    stay explicit gaps; no airborne relaunch. After landing the body keeps still landing_hold frames
    (tick: knock_hold, read by move).
    INFERRED selection: feet-centre sphere. Sickle relation uses the launcher. An arc (the shotgun's) keeps the
    bodies whose bearing from the centre is within arc / 2 of `axis` (INFERRED half; bench 0 deg in, 39 deg out);
    without an axis (a projectile's detonation: engine_knock_arc b, the axis unmeasured) it is a gap.
    The whole nugget therefore retains its unmodeled registration.
    """
    world, peers, gap = host.world, host.peers, host.gap
    flights = peers.impact_flights
    for effect in weapon.get('meta_impacts', []):
        if effect['radius'] <= 0:
            gap(TAG, '非正冲击半径的选人范围未建模')
            continue
        arc = effect.get('arc')
        if arc is not None and axis is None:
            gap(TAG, 'Arc 只量过射手脚下为圆心的瞬发写法；弹体爆心的弧轴未量')
            continue
        target_filter = effect.get('target_filter')
        magnetic = target_filter and target_filter.get('magnetic_ground')
        if target_filter and not magnetic and attacker is None:
            gap(TAG, '筛选缺少发射者关系，未派发冲击')
            continue
        for b in world.living():
            if axis is not None and b is attacker:
                continue
            # CampKOG a/b: the explicit forbidden object-status field.
            # Only the isolated measured spelling is parsed by simunits.
            if any(flag in b.status for flag in effect.get('forbidden_status', [])):
                continue
            # CampKFilter: amphibious Terror Drone is grounded on this land
            # site. Water launches remain outside the measured slice.
            grounded = b.surface == 'ground' or (b.surface == 'both'
                        and world.ground.stand('ground', b.x, b.y))
            if magnetic:
                # CampKFilter a/b: explicit identities override INFANTRY,
                # but UNDER_IRON_CURTAIN wins over explicit inclusion.
                # Airborne eligibility remains a gap, never a kind-only guess.
                if not grounded or 'AIRCRAFT' in b.kinds:
                    gap(TAG, '磁力筛选的飞机资格尚未对拍')
                    continue
                if ('UNDER_IRON_CURTAIN' in b.status or ('INFANTRY' in b.kinds
                        and b.template not in target_filter['include_templates'])):
                    continue
            elif target_filter and target_filter.get('rush_infantry'):
                # CampKKG a/b: independently measured kind/status gates.
                if 'INFANTRY' not in b.kinds:
                    continue
            elif target_filter:
                # CampKSG a/b: NO_COLLISIONS rejects only when the XML
                # excludes it; no independent status gate in this slice.
                if (world.relation(attacker.owner, b.owner) != target_filter['relation']
                        or 'INFANTRY' not in b.kinds
                        or any(s in b.status for s in target_filter.get('status_exclude', []))):
                    continue
                if any(peers.has_model_condition(b, c) for c in target_filter['forbidden']):
                    continue
                # INFERRED: Physics flights / landing hold represent the three
                # forbidden knock states; their native bit timing is still a gap.
                if b.serial in flights or peers.knock_hold.get(b.serial, -1) > world.frame_now():
                    continue
            position = (b.x, b.y, host.ground_z(b.x, b.y) if b.z is None else b.z)
            if math.dist(position, centre) > effect['radius']:
                continue
            if arc is not None:
                dx, dy = b.x - centre[0], b.y - centre[1]
                if math.hypot(dx, dy) > 1e-6 and abs(math.degrees(
                        math.atan2(axis[0]*dy - axis[1]*dx, axis[0]*dx + axis[1]*dy))) > arc / 2:
                    continue
            if effect.get('forbid_flailing') and b.serial in flights:   # INFERRED: STUNNED_FLAILING = in flight
                continue
            height, resistance = host.body_of(b.template)
            if effect['amount'] < resistance:
                # Physics P3 gate (bench 11-11, engine_knock_water gate89/90/91): under the body's
                # ShockwaveResistance, no shock at all (no ra3ext `shock` line); equal to it still flies
                world.used.add('knock resistance gate')
                continue
            if height is None or not grounded or b.serial in peers.attachments or b.serial in flights:
                gap(TAG, '仅默认Physics的未附着地面起飞已接通；筛选/重入待核')
                continue
            velocity = host.velocity(effect, position, centre, height, detonation=True)
            end = host.ground_launch(position, velocity)['landing']
            landing, drowns, vehicle = None, False, 'INFANTRY' not in b.kinds
            if vehicle or not world.ground.stand(b.surface, end[0], end[1]):
                spot = world.ground.landing(end[0], end[1], None if vehicle else b.surface)
                if spot is None:
                    gap(TAG, '击飞落点附近没有能站的格')
                    continue
                if spot[2]:
                    world.used.add('knock landing moved')
                landing = (spot[0], spot[1], host.ground_z(spot[0], spot[1]))
                drowns = vehicle and world.ground.drowns(spot[0], spot[1])
            points = host.trajectory(position, velocity, landing)
            if len(points) < 2:
                continue
            if drowns:
                # gone the frame it lands, whatever the curve passes over (tank: the wet one 178, the direct
                # hit 192 = 173 + its points - 1; tick)
                host.knock_drowns.add(b.serial)
                world.used.add('knock landing drowns')
            else:
                # the curve may cross lower ground (far: over the trench to the far bank), end lower (ramp:
                # down the slope) or higher (climb: up the table's ramp, simunits.meta_impact_trajectory); one
                # off its landing's ground (a man's own landing on other ground) or dipping into the terrain
                # needs the engine's height queries
                if (abs(points[-1][2] - host.ground_z(*points[-1][:2])) > 1e-5 or
                        any(z < host.smooth_z(x, y) - 1e-5 for x, y, z in points)):
                    gap(TAG, '坡地轨迹和地形查询未建模')
                    continue
            flights[b.serial] = (b, world.frame_now(), points)
            b.z = position[2]
            world.used.add('meta impact')


def tick(host):
    """Advance each active trajectory by one sample per simulation frame."""
    world, peers = host.world, host.peers
    flights = peers.impact_flights
    for key, (b, start, points) in list(flights.items()):
        if not b.alive:
            flights.pop(key)
            continue
        k = min(len(points)-1, max(0, world.frame_now()-start))
        b.x, b.y, b.z = points[k]
        if k == len(points)-1:
            flights.pop(key)
            b.z = None
            if key in host.knock_drowns:
                host.knock_drowns.discard(key)
                world.world.kill(b, '击飞落水')     # Ground.drowns: gone the frame it lands
                world.change()
                continue
            # on the ground: lies, then gets up (Physics ShockStunnedTime + ShockStandingTime); a kept move
            # order resumes after it (bench 11-11 engine_knock_probe stand)
            peers.knock_hold[key] = world.frame_now() + host.landing_hold()
        world.change()
