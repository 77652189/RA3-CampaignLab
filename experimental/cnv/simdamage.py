"""L3 damage: what a shot does when it lands (ADR 0029, docs/engine/sim-layers.md; docs/engine/weapons.md).

`Damage` deals each frame's aimed fire, volleys, projectile arrivals and DOTs with their warhead effects (`deal`:
DamageNugget and its siblings -- contained, secondary/freeze, suppression, EMP, lines, lift, attach, special powers,
hit modifiers, leech), keeps the incoming-fire notifications (TrackIncomingWeaponFire: `incoming_*`,
`inform_launch`, `expected_damage`) and the projectile arrivals (`queue_projectile_hit`), dispatches MetaImpact shocks
and flies the knocked bodies (`projectile_detonate`, `meta_impact_*`), melts and freezes (`chill`) and runs
HitReaction. The module functions are the stateless rules: the flank scalar, the physics ground height, suppression
sampling and death blasts. All over the world it is given (simworld.WORLD_API only).
Its host's other parts come in as `peers` (`Peers`, the names in PEERS only, read when used so a swapped-in method
still answers): the L2 body / modifier / status / locomotion calls (destroy, modify, emp_disabled, cold_of, the model
conditions, attachment_tick, knock_landing*), the same-layer can_hit / shots_due, the host's own projectile_detonate /
queue_projectile_hit (a test may intercept an arrival) and the fight state it shares (firing, volleys, the
garrison, infiltrators, sweeps, attachments, player_ups, lift_timers, suppression_fields, death_blasts, chilling, the
knock flights and holds, the EMP deadlines). This module never imports them.
Fields it owns: incoming, projectile_hits, projectile_speeds, impact_body, knock_drowns, dots, cold_on, lift_modules,
nugget_powers, hit_reaction_of.
"""
import math

import simunits
from engine.combat import dot, leech
from engine.combat import projectile as flight
from engine.combat import registry
from engine.kernel import interfaces
from engine.modules import weaponset
from simworld import GAP_WEAPON

PEERS = frozenset({'attachment_tick', 'attachments', 'can_hit', 'chilling', 'cold_of', 'death_blasts', 'destroy', 'emp_disabled', 'emp_until', 'firing', 'garrison', 'has_model_condition', 'impact_flights', 'infiltrators', 'knock_hold', 'knock_landing', 'knock_landing_vehicle', 'lift_timers', 'modify', 'player_ups', 'projectile_detonate', 'queue_projectile_hit', 'set_model_condition', 'shots_due', 'suppression_fields', 'sweeps', 'volleys'})
LAZY = frozenset({'impact_flights', 'knock_hold', 'emp_until'})     # the host makes these dicts on first use


class Peers:
    """What Damage may reach on its host (the Sim) beyond the world: the names in PEERS, read when used."""
    __slots__ = ('host',)

    def __init__(self, host):
        self.host = host

    def __getattr__(self, name):
        if name in LAZY:
            return vars(self.host).setdefault(name, {})
        if name == 'chilling':
            return getattr(self.host, 'chilling', ())                # this tick's cryo beams (fight), none yet
        if name not in PEERS:
            raise AttributeError(f'simdamage.Peers: {name} is not lent (PEERS)')
        return getattr(self.host, name)


class EffectHost:
    """The host's calls an 'effect' phase handler (engine/combat: Lift, Attach, SpecialPower, AttributeModifier) or the Sweep makes -- registry.Context.host. The
    game-data reads and their caches stay here (engine/ reads no game data); the peers are read when used."""
    __slots__ = ('damage', 'world', 'peers', 'lift_hit', 'refresh_modifiers', 'fits', 'sweep')
    # what a lift still lacks (a gap after each lift; the report is private, so its pointer stays out of engine/)
    LIFT_LANDING = ('计时释放不清状态；SoftLanding自击及修正器到期清位缺Lift接地事件，垂直运动/落地武器未接通；'
                    '见work/re/c_lift_landing_gate_report.md')

    def __init__(self, damage, world, peers):
        self.damage, self.world, self.peers = damage, world, peers
        # the peers' own calls as they are: lift_hit(caster, target, increment, maximum), refresh_modifiers(body) (the
        # host's modify), fits(body, filter) (the garrison's PassengerFilter), sweep(shooter, target, life) (Sweeps.fire)
        self.lift_hit, self.refresh_modifiers, self.fits = peers.lift_timers.hit, peers.modify, peers.garrison.fits
        self.sweep = peers.sweeps.fire

    def lift_rule(self, template):
        """The caster template's LiftObjectUpdate rule (simunits.lift_module, cached in Damage.lift_modules)."""
        cache = self.damage.lift_modules
        if template not in cache:
            cache[template] = simunits.lift_module(template, self.world.own)
        return cache[template]

    def upgrade_gate(self, by, required, forbidden):
        """(the gate's type -- simunits.upgrade_type of the upgrade named, None: no gate --, whether `by` passes it:
        the required one held and the forbidden one not, by its owner for a PLAYER gate, else by itself)."""
        if not (required or forbidden):
            return None, True
        gate = simunits.upgrade_type(required or forbidden, self.world.own)
        held = {up.lower() for up in (self.peers.player_ups.get(by.owner, ()) if gate == 'PLAYER' else by.upgrades)}
        return gate, not ((required and required.lower() not in held) or (forbidden and forbidden.lower() in held))

    def self_power(self, template, power):
        """The caster template's module of `power` (simunits.nugget_self_power, cached in Damage.nugget_powers)."""
        cache, key = self.damage.nugget_powers, (template, power)
        if key not in cache:
            cache[key] = simunits.nugget_self_power(template, power, self.world.own)
        return cache[key]

    def disguise(self, body):
        self.peers.set_model_condition(body, 'DISGUISED')

    def modifier(self, template, mid):
        """(the modifier `mid` as the template's XML reads it -- simunits.modifier, None: none --, that XML)."""
        xml = self.world.xml_of(template)
        return simunits.modifier(xml, mid), xml

    def wear(self, body, mid, frames, xml):
        """Put the modifier `mid` (of `xml`) on the body for `frames` from now and re-read its modifiers."""
        body.auras_on[mid] = (self.world.frame_now() + frames, xml)
        self.refresh_modifiers(body)

    @property
    def attachments(self):
        """The attachment chains (child serial -> (child, parent, rule)), read only."""
        return self.peers.attachments

    def attach(self, child, parent, rule):
        """Chain `child` to `parent` and place it at once (Sim.attachment_tick)."""
        self.peers.attachments[child.serial] = (child, parent, rule)
        self.peers.attachment_tick()


def flank_of(victim, attacker):
    """The side / rear scalar of a direct hit (simunits.flank) by where the attacker stands as it fires
    (docs/engine/weapons.md 4, bench engine_shot flank 40 / 40 / 42 / 44 %), UNRESISTABLE too (bench
    engine_inform_ai: the side-facing miners at 68 % after a 150 UNRESISTABLE shell of their 500)."""
    return simunits.flank(victim.armor, victim.angle, attacker.x - victim.x, attacker.y - victim.y)


def hit_scalar(victim, damage_type, attacker):
    """What one point of `damage_type` from `attacker` does to `victim` on a direct hit: its armor percent x taken
    (UNRESISTABLE: 1), x the flank (registry.Context.scalar, for the nugget handlers)."""
    return armor_scalar(victim, damage_type) * flank_of(victim, attacker)


def armor_scalar(victim, damage_type):
    """What one point of `damage_type` does to `victim` without the flank: its armor percent x taken (UNRESISTABLE:
    1) -- a passenger's (DamageContained), a DOT tick's (registry.Context.armor)."""
    return (1.0 if damage_type == 'UNRESISTABLE' else
            simunits.percent(victim.armor, damage_type) / 100.0 * victim.taken)


def straight_speed(projectile, own):
    """The projectile template's straight-line muzzle speed (map units a frame): ProjectileUpdate
    StateMachine="StraightLineProjectile"'s MoveInStraightLine MuzzleVelocity; 0 for any other flight or no file
    (registry.Context.speed, cached in Damage.projectile_speeds)."""
    try:
        xml = simunits._xml(projectile, own)
        update = next(simunits._blocks(xml or '', 'ProjectileUpdate'), ('', ''))
        movement = next(simunits._blocks(update[1] or '', 'MoveInStraightLine'), ('', ''))
        return (simunits._num(simunits._attr(movement[0], 'MuzzleVelocity'))
                if simunits._attr(update[0], 'StateMachine') == 'StraightLineProjectile' else 0)
    except (OSError, ValueError):
        return 0


def impact_ground_z(world, x, y):
    """Physics uses world z; routing heights retain mapterrain's legacy /16.

    docs/engine/terrain.md: world height = legacy height * 0.625.
    """
    import terrain_rules
    return float(terrain_rules.world(world.ground.z(x, y)))


def suppression_at(fields, b, now):
    """The suppression fields covering b in frame `now` (World.suppression_at; the sampling is
    engine/modules/suppression.py, step M6): [(end, value)] of the hits' stationary 2D fields
    (end, value, x, y, radius) still alive, within their radius of b's centre (bench 2026-11-10
    engine_suppress_probe: individual hit lifetimes)."""
    return [(end, v) for end, v, x, y, radius in fields if now < end and math.hypot(b.x - x, b.y - y) <= radius]


def suppression_tick(world, peers):
    """The suppression cell's host half, after the modules sampled: fields whose lifetime is out leave."""
    now = world.frame_now()
    peers.suppression_fields[:] = [p for p in peers.suppression_fields if now < p[0]]


def death_blast_due(world, frame, peers):
    """A death weapon going off by `frame` (simbody.Life.fire: a FireWeaponWhenDead's): every living object within its
    radius, centre to centre, whose owner stands to the dead one's as the weapon's RadiusDamageAffects takes
    (ENEMIES / NEUTRALS / ALLIES, its own owner counted an ally), loses the damage through its armor. A death it
    causes fires that one's weapon in turn (a chain of exploding props). The armour's side / rear scalar
    (simunits.flank) by where the blast is from the victim; a crashing wreck resting on its victim's centre
    counts as coming in along its fall (bench 11-12 engine_crash_face; INFERRED: the wreck's last point a hair
    short of the landing), a still one as at the same place (front)."""
    for d in [d for d in peers.death_blasts if d[0] <= frame]:
        peers.death_blasts.remove(d)
        _, x, y, dmg, typ, reach, affects, owner, by, *rest = d
        ally, ground_only, approach = tuple(rest) + (1.0, False, None)[len(rest):]
        for t in world.living():
            if math.hypot(t.x - x, t.y - y) > reach or frame < t.immune_until or t.shielded or t.indestructible:
                continue
            if ground_only and t.surface == 'air':
                continue                    # a crash on the ground; the planes 175 over it are out of its 20
            rel = world.relation(owner, t.owner)
            if (rel + 'S' if rel == 'NEUTRAL' else rel) not in affects:
                continue
            armor = 1.0 if typ == 'UNRESISTABLE' else simunits.percent(t.armor, typ) / 100.0 * t.taken
            if rel == 'ALLIES':
                armor *= ally
            dx, dy = x - t.x, y - t.y
            if math.hypot(dx, dy) < 1e-6 and approach:
                dx, dy = -approach[0], -approach[1]
            armor *= simunits.flank(t.armor, t.angle, dx, dy)
            if dmg * armor <= 0:
                continue
            t.damage(dmg * armor)
            t.set_last_damage(owner, by)
            if t.hp <= 0 and t.alive:
                if world.first_death is None:
                    world.first_death = (world.t, t, by)
                peers.destroy(t, f'被 {world.label(by)} 的死亡武器炸掉')


class Damage:
    def __init__(self):
        self.incoming = {}               # target.serial -> [(source, weapon key, damage, hit, expiry)]
        self.projectile_hits = []        # (frame, target, damage, attacker, weapon, centre): arrivals to come
        self.projectile_speeds = {}      # projectile template -> its straight-line muzzle speed (0: not one)
        self.impact_body = {}            # template -> (MetaImpact body height, ShockwaveResistance)
        self.knock_drowns = set()        # body.serial of knocked vehicles that drown where they land
        self.dots = []                   # running DOTNugget ticks
        self.cold_on = {}                # body.serial -> (body, last freezer): bodies with cold to melt
        self.lift_modules = {}           # caster template -> simunits.lift_module
        self.nugget_powers = {}          # (caster template, power) -> simunits.nugget_self_power
        self.hit_reaction_of = {}        # template -> simunits.hit_reaction

    def incoming_add(self, world, target, source, key, damage, hit, expiry):
        """Record one observed/predicted notification on a tracking target."""
        if '<TrackIncomingWeaponFireBehavior' not in world.xml_of(target.template):
            return
        table = self.incoming
        table.setdefault(target.serial, []).append((source, key, damage, hit, expiry))

    def incoming_hit(self, target, source, key):
        """Damage notification deletes matching source + weapon entries."""
        table = self.incoming
        rows = table.get(target.serial, [])
        rows[:] = [r for r in rows if r[:2] != (source, key)]

    def expected_damage(self, world, target, behind, ahead, now=None):
        """Micro damage callback, seconds -> ceil frames; no facing multiplier.

        This slice supplies incoming damage only. History remains a gap; the
        miner's TrackDamage.InstantWeaponsOnly path is not inferred from HP loss.
        INFERRED query policy: keep entries on expiry, remove strictly after.
        This is not the engine's autonomous table-cleanup schedule: the
        engine_inform_expiry probe retains expired rows until later frames.
        See work/re/c_inform_expiry_report.md; query output is not measured.
        """
        now = world.frame_now() if now is None else now
        rows = self.incoming.get(target.serial, [])
        rows[:] = [r for r in rows if now <= r[4]]
        if behind:
            world.gap(GAP_WEAPON, 'InformTargetNugget', '历史伤害入口未接；当前只提供来弹预计伤害')
        return sum(r[2] for r in rows if r[3] <= now + math.ceil(ahead * simunits.LIFE_FPS)) if ahead > 0 else 0.0

    def inform_launch(self, world, target, attacker, weapon, count=1):
        """Ordinary launch notification. INFERRED: centre positions, time scale 1.

        WeaponSpeed is units/second, independent of projectile muzzle speed.
        The default fudge factors deliberately predict earlier than collision.
        """
        if not weapon.get('inform'):
            return
        speed = weapon.get('weapon_speed', 999999.0) / simunits.LIFE_FPS
        distance = math.dist((attacker.x, attacker.y, attacker.z or 0),
                             (target.x, target.y, target.z or 0))
        duration = distance / speed if speed >= 1e-4 else 0.0
        armor = 1.0 if weapon['type'] == 'UNRESISTABLE' else simunits.percent(target.armor, weapon['type']) / 100 * target.taken
        for effect in weapon.get('inform', []):
            recipients = [target]
            if effect.get('radius', 0) > 0:
                # engine_inform_radius: neighbours receive the primary's tuple,
                # even though the single-target warhead never damages them.
                # INFERRED boundary: centre sphere; extents/height/other armour
                # and relation eligibility remain gaps, not retail coverage.
                recipients = [b for b in world.living()
                              if math.dist((b.x, b.y, b.z or 0),
                                           (target.x, target.y, target.z or 0)) <= effect['radius']]
            for recipient in recipients:
                for _ in range(count):
                    self.incoming_add(world, recipient, attacker.serial, weapon.get('weapon_key'),
                                      weapon['dmg'] * attacker.dealt * armor,
                                      world.frame_now() + int(duration * effect['min']),
                                      world.frame_now() + int(duration * effect['max'] + 0.99))

    def projectile_speed(self, world, projectile):
        """straight_speed, read once a template (projectile_speeds)."""
        speeds = self.projectile_speeds
        if projectile not in speeds:
            speeds[projectile] = straight_speed(projectile, world.own)
        return speeds[projectile]

    def queue_projectile_hit(self, when, target, damage, attacker, weapon, centre=None):
        """A projectile's arrival event (engine/combat/projectile.py queue), also usable to replay a collision."""
        flight.queue(self.projectile_hits, when, target, damage, attacker, weapon, centre)

    def projectile_detonate(self, world, weapon, target, centre, attacker, peers):
        """Dispatch the non-damage payload of a projectile arrival."""
        if not weapon.get('meta_impacts'):
            return
        if centre is None and target.alive:
            height = simunits.meta_impact_body(target.template, world.own)
            if height is not None:
                centre = (target.x, target.y, impact_ground_z(world, target.x, target.y) + height/2)
        if centre is None:
            world.gap(GAP_WEAPON, 'MetaImpactNugget', '缺少弹体实际爆心，未派发冲击')
        else:
            self.meta_impact_detonate(world, weapon, centre, attacker, peers)

    def meta_impact_detonate(self, world, weapon, centre, attacker, peers):
        """Dispatch ordinary immediate warhead shocks, separately from damage radius.

        First slice: default Physics, grounded bodies, landings on level, lower or higher ground (Physics P3: a landing
        moved off the water, a vehicle's drowning, knock_landing / knock_landing_vehicle). Other cases
        stay explicit gaps; no airborne relaunch. After landing the body keeps still meta_impact_landing_hold frames
        (meta_impact_tick: knock_hold, read by move).
        INFERRED selection: feet-centre sphere. Sickle relation uses the launcher; arc remains a gap.
        The whole nugget therefore retains its unmodeled registration.
        """
        import terrain_rules
        flights = peers.impact_flights
        cache = self.impact_body
        for effect in weapon.get('meta_impacts', []):
            if effect['radius'] <= 0:
                world.gap(GAP_WEAPON, 'MetaImpactNugget', '非正冲击半径的选人范围未建模')
                continue
            target_filter = effect.get('target_filter')
            magnetic = target_filter and target_filter.get('magnetic_ground')
            if target_filter and not magnetic and attacker is None:
                world.gap(GAP_WEAPON, 'MetaImpactNugget', '筛选缺少发射者关系，未派发冲击')
                continue
            for b in world.living():
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
                        world.gap(GAP_WEAPON, 'MetaImpactNugget', '磁力筛选的飞机资格尚未对拍')
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
                ground = impact_ground_z(world, b.x, b.y)
                position = (b.x, b.y, ground if b.z is None else b.z)
                if math.dist(position, centre) > effect['radius']:
                    continue
                if b.template not in cache:
                    cache[b.template] = (simunits.meta_impact_body(b.template, world.own),
                                         simunits.meta_impact_resistance(b.template, world.own))
                height, resistance = cache[b.template]
                if effect['amount'] < resistance:
                    # Physics P3 gate (bench 11-11, engine_knock_water gate89/90/91): under the body's
                    # ShockwaveResistance, no shock at all (no ra3ext `shock` line); equal to it still flies
                    world.used.add('knock resistance gate')
                    continue
                if height is None or not grounded or b.serial in peers.attachments or b.serial in flights:
                    world.gap(GAP_WEAPON, 'MetaImpactNugget', '仅默认Physics的未附着地面起飞已接通；筛选/重入待核')
                    continue
                velocity = simunits.meta_impact_velocity(effect, position, centre, height, detonation=True)
                end = simunits.meta_impact_ground_launch(position, velocity)['landing']
                landing, drowns = None, False
                if 'INFANTRY' not in b.kinds:
                    landing = peers.knock_landing_vehicle(end)
                    if landing is None:
                        continue
                    drowns = world.ground.drowns(landing[0], landing[1])
                elif not world.ground.stand(b.surface, end[0], end[1]):
                    landing = peers.knock_landing(b, end)
                    if landing is None:
                        continue
                points = simunits.meta_impact_trajectory(position, velocity, landing)
                if len(points) < 2:
                    continue
                if drowns:
                    # gone the frame it lands, whatever the curve passes over (tank: the wet one 178, the direct
                    # hit 192 = 173 + its points - 1; meta_impact_tick)
                    self.knock_drowns.add(b.serial)
                    world.used.add('knock landing drowns')
                else:
                    # the curve may cross lower ground (far: over the trench to the far bank), end lower (ramp:
                    # down the slope) or higher (climb: up the table's ramp, simunits.meta_impact_trajectory); one
                    # off its landing's ground (a man's own landing on other ground) or dipping into the terrain
                    # needs the engine's height queries
                    end_ground = impact_ground_z(world, *points[-1][:2])
                    if (abs(points[-1][2] - end_ground) > 1e-5 or
                            any(z < terrain_rules.world(world.ground.z_smooth(x, y)) - 1e-5 for x, y, z in points)):
                        world.gap(GAP_WEAPON, 'MetaImpactNugget', '坡地轨迹和地形查询未建模')
                        continue
                flights[b.serial] = (b, world.frame_now(), points)
                b.z = position[2]
                world.used.add('meta impact')

    def meta_impact_tick(self, world, peers):
        """Advance each active trajectory by one sample per simulation frame."""
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
                if key in self.knock_drowns:
                    self.knock_drowns.discard(key)
                    peers.destroy(b, '击飞落水')     # Ground.drowns: gone the frame it lands
                    world.change()
                    continue
                # on the ground: lies, then gets up (Physics ShockStunnedTime + ShockStandingTime); a kept move
                # order resumes after it (bench 11-11 engine_knock_probe stand)
                peers.knock_hold[key] = world.frame_now() + simunits.meta_impact_landing_hold()
            world.change()

    def deal(self, world, dt, peers):
        """R6: `dt` seconds of the aimed fire (`fight`) from shooters and at targets still alive. With the engine model
        once a frame, after that frame's scripts (Generals GameLogic::update runs the script engine before the objects'
        updates): a script's health top-up (UNIT_SET_HEALTH every frame, the a4 checks' trucks) lands before the
        frame's damage, so only a frame's fire of the whole maximum kills (A4 win: bench 2026-11-07 against the 0.5 s
        tick that killed the trucks at 4:23). Bodies at 0 die, the last hit their killer's."""
        peers.lift_timers.tick()
        hurt = {}
        leech_events = {}       # the frame's leech claims (engine/combat/leech), paid after the damage
        host = EffectHost(self, world, peers)       # the 'effect' phase's calls (engine/combat)

        def gap(tag, why):
            world.gap(GAP_WEAPON, tag, why)
        self.meta_impact_tick(world, peers)
        for hit in flight.due(self.projectile_hits, world.frame_now()):     # shells fired before land first
            flight.arrive(hit, hurt, peers.projectile_detonate, self.incoming_hit)
        # A cached aim is not permission to fire after a script/modifier stops
        # the shooter. Keep its order; expiry lets fight select it again.
        # Existing-order evidence: work/re/d50_scramble_expiry3.md.
        # INFERRED: exact within-tick stop phase; the bench has coarse snapshots.
        for t, rate, by in peers.firing:
            if (t.alive and by.alive and 'NO_ATTACK' not in by.status and not peers.emp_disabled(by)
                    and not peers.infiltrators.attack_blocked(by)
                    and world.t >= weaponset.gate(by, t) - 1e-9):
                h = hurt.setdefault(t.serial, [t, 0.0, by])
                h[1] += rate * dt
                h[2] = by
        for t, w, by in peers.volleys:           # engine line C round 2: a shot lands when its clock says (shots_due)
            if (t.alive and by.alive and 'NO_ATTACK' not in by.status and not peers.emp_disabled(by)
                    and not peers.infiltrators.attack_blocked(by)
                    and world.t >= weaponset.gate(by, t) - 1e-9):
                n = peers.shots_due(by, w, dt)
                if n:
                    self.inform_launch(world, t, by, w, n)
                    # the volley's nugget handlers (engine/combat, registry.ORDER): a launch may take it over
                    ctx = registry.Context(world, by, t, w, n, hurt, scalar=hit_scalar, armor=armor_scalar,
                                           speed=lambda p: self.projectile_speed(world, p), frames=simunits._frames,
                                           gap=gap, queue_hit=peers.queue_projectile_hit,
                                           detonate=peers.projectile_detonate, clear_notice=self.incoming_hit,
                                           can_hit=peers.can_hit, held=peers.garrison.held, cold_of=peers.cold_of,
                                           dots=self.dots, mark_cold=self.mark_cold,
                                           suppression_fields=peers.suppression_fields,
                                           emp_until=lambda: peers.emp_until, claims=leech_events, host=host)
                    if registry.run('launch', ctx):
                        continue
                    projectile = w.get('projectile')
                    if not projectile:
                        self.incoming_hit(t, by.serial, w.get('weapon_key'))
                    registry.run('hit', ctx)      # the DOT, passengers, cold, suppression, EMP, sweep (registry.ORDER)
                    registry.run('aim', ctx)              # a dynamic line picks the victims (LineDamage)
                    for victim in ctx.victims:
                        h = hurt.setdefault(victim.serial, [victim, 0.0, by])
                        ctx.victim = victim
                        registry.run('victim', ctx)       # its damage, the leech claims, the strip (registry.ORDER)
                        h[2] = by
                    registry.run('effect', ctx)           # the lift, the attachment, the power, the modifier (registry.ORDER)
        self.dots[:] = dot.tick(self.dots, world.frame_now(), hurt, armor_scalar, gap)    # the frame-end DOT ledger
        for t, dmg, by in hurt.values():
            if world.frame_now() < t.immune_until or t.shielded or t.indestructible:
                continue
            before_hp = t.hp
            t.damage(dmg)
            self.hit_reaction_damage(world, t, before_hp - t.hp, peers)
            leech.refund(leech_events.get(t.serial), t, before_hp, gap)
            t.set_last_damage(by.owner, by)
            if t.hp <= 0 and t.alive:
                if world.first_death is None:
                    world.first_death = (world.t, t, by)
                peers.destroy(t, f'被 {world.label(by)} 打掉')
        self.chill(world, dt, peers)

    def mark_cold(self, target, by):
        """`by` is the one of record for the cold `target` took this frame (cold_on, read by chill;
        registry.Context.mark_cold: SecondaryDamage)."""
        self.cold_on[target.serial] = (target, by)

    def hit_reaction_damage(self, world, target, damage, peers):
        """E172 gun-hit condition only; rotation/animation are unmodelled.

        INFERRED: start/refresh the SDK lifetime on positive applied damage,
        using the common expiry store. The bench asserts ever-on and final
        clear, not the precise first/last frame or repeated-hit refresh rule.
        Script health changes, death blasts and other damage paths are gaps.
        """
        if damage <= 0 or target.hp <= 0:
            return
        cache = self.hit_reaction_of
        if target.template not in cache:
            cache[target.template] = simunits.hit_reaction(target.template, world.own)
        rule = cache[target.template]
        if (rule and rule['seconds'] > 0 and rule['required'] <= set(target.status)
                and not rule['forbidden'] & set(target.status)):
            peers.set_model_condition(target, 'HIT_REACTION', rule['seconds'])
            world.used.add('hit reaction')
            world.guessed.add('HitReactionBehavior: exact timing/refresh INFERRED; rotation unmodelled')

    def chill(self, world, dt, peers):
        """`dt` seconds of the cryo beams aimed this tick (fight's `chilling`) and of melting (ALIGN 'freeze'): the
        cold goes up by the beams' rate, down by DissipateAmount / UpdateDuration, stays within 0 .. cap x max health;
        a change of the highest step reached re-sets the body (modify); a DIE_ON_ENTER step kills."""
        cold = self.cold_on
        for t, rate, by in peers.chilling:
            if not (t.alive and by.alive) or peers.emp_disabled(by) or t.shielded:     # shielded: the Iron Curtain (the nugget's filter)
                continue
            if peers.cold_of(t)[0] is None:
                continue
            t.find(interfaces.Freeze).add(rate * dt)      # engine/modules/freeze.py (step M11)
            cold[t.serial] = (t, by)
        for k, (t, by) in list(cold.items()):
            tr = peers.cold_of(t)[0]
            if not t.alive:
                del cold[k]
                continue
            m = t.find(interfaces.Freeze)
            moved = m.melt(dt)
            step = m.stage()
            if m.held() <= 0:
                del cold[k]
            if moved:
                peers.modify(t)
                if step >= 0:
                    world.note('冷冻', f'{world.label(t)} 冷冻到第 {step + 1} 档（{tr["steps"][step][0]:.0%} 生命值）')
                if step >= 0 and tr['steps'][step][4] and t.alive:
                    peers.destroy(t, f'被 {world.label(by)} 冻死')
