"""L3 damage: what a shot does when it lands (ADR 0029, docs/engine/sim-layers.md; docs/engine/weapons.md).

`Damage` deals each frame's aimed fire, volleys, projectile arrivals and DOTs with their warhead effects (`deal`:
DamageNugget and its siblings -- contained, secondary/freeze, suppression, EMP, lines, lift, attach, special powers,
hit modifiers, leech), keeps the incoming-fire notifications (TrackIncomingWeaponFire: `incoming_*`,
`inform_launch`, `expected_damage`) and the projectile arrivals (`queue_projectile_hit`), dispatches MetaImpact shocks
and flies the knocked bodies (`projectile_detonate`, `meta_impact_*`), melts and freezes (`chill`) and runs
HitReaction. The module functions are the stateless rules: the flank scalar, the physics ground height, suppression
sampling and death blasts. All over the world it is given (simworld.WORLD_API only).
Its host's other parts come in as `peers` (`Peers`, the names in PEERS only, read when used so a swapped-in method
still answers): the L2 body / modifier / status / locomotion calls (emp_disabled, cold_of, the model
conditions, attachment_tick), the same-layer can_hit / shots_due, the host's own projectile_detonate /
queue_projectile_hit (a test may intercept an arrival) and the fight state it shares (firing, volleys, the
garrison, infiltrators, sweeps, attachments, player_ups, lift_timers, suppression_fields, death_blasts, chilling, the
knock flights and holds, the EMP deadlines). This module never imports them.
Fields it owns: incoming, projectile_hits, projectile_speeds, impact_body, knock_drowns, dots, cold_on, lift_modules,
nugget_powers, hit_reaction_of.
"""
import math
import re

import engine.data.units as simunits
from engine.combat import dot, leech, meta_impact
from engine.combat import projectile as flight
from engine.combat import registry
from engine.combat.range import in_range
from engine.kernel import interfaces
import engine.objects.modifier as simmodifier
from engine.modules import weaponset
from engine.world.handle import GAP_WEAPON

PEERS = frozenset({'attachment_tick', 'attachments', 'can_hit', 'chilling', 'cold_of', 'death_blasts', 'emp_disabled', 'emp_until', 'firing', 'garrison', 'has_model_condition', 'impact_flights', 'infiltrators', 'knock_hold', 'lift_timers', 'player_ups', 'projectile_detonate', 'queue_projectile_hit', 'set_model_condition', 'shots_due', 'suppression_fields', 'sweeps', 'volleys'})
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
    """The host's calls an 'effect' phase handler (engine/combat: Lift, Attach, SpecialPower, AttributeModifier), the Sweep or the MetaImpact makes -- registry.Context.host. The
    game-data reads and their caches stay here (engine/ reads no game data); the peers are read when used."""
    __slots__ = ('damage', 'world', 'peers', 'lift_hit', 'refresh_modifiers', 'fits', 'sweep', 'gap',
                 'velocity', 'ground_launch', 'trajectory', 'landing_hold')
    # what a lift still lacks (a gap after each lift; the report is private, so its pointer stays out of engine/)
    LIFT_LANDING = ('计时释放不清状态；SoftLanding自击及修正器到期清位缺Lift接地事件，垂直运动/落地武器未接通；'
                    '见work/re/c_lift_landing_gate_report.md')

    def __init__(self, damage, world, peers):
        self.damage, self.world, self.peers = damage, world, peers
        # the peers' own calls as they are: lift_hit(caster, target, increment, maximum), refresh_modifiers(body) (the
        # modifiers' re-read, simmodifier.modify), fits(body, filter) (the garrison's PassengerFilter), sweep(shooter, target, life) (Sweeps.fire)
        self.lift_hit, self.refresh_modifiers, self.fits = peers.lift_timers.hit, lambda b: simmodifier.modify(world, b), \
            peers.garrison.fits
        self.sweep = peers.sweeps.fire
        self.gap = lambda tag, why: world.gap(GAP_WEAPON, tag, why)
        # MetaImpact's flight physics as simunits reads them (engine/combat/meta_impact)
        self.velocity, self.ground_launch = simunits.meta_impact_velocity, simunits.meta_impact_ground_launch
        self.trajectory, self.landing_hold = simunits.meta_impact_trajectory, simunits.meta_impact_landing_hold

    def body_of(self, template):
        """(MetaImpact body height, ShockwaveResistance) of the template (simunits, cached in Damage.impact_body)."""
        cache, own = self.damage.impact_body, self.world.own
        if template not in cache:
            cache[template] = (simunits.meta_impact_body(template, own), simunits.meta_impact_resistance(template, own))
        return cache[template]

    @property
    def knock_drowns(self):
        """Damage's book of knocked vehicles that drown where they land (add / discard only)."""
        return self.damage.knock_drowns

    def ground_z(self, x, y):
        return impact_ground_z(self.world, x, y)

    def smooth_z(self, x, y):
        """The smoothed terrain's world height (a knocked curve dipping under it is a gap)."""
        import terrain_rules
        return terrain_rules.world(self.world.ground.z_smooth(x, y))

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


def taper_of(w, victim, attacker):
    """The continuous fire's share of weapon w's damage that reaches `victim` (combat/damage.tapered; 1 without)."""
    from engine.combat.damage import tapered
    return tapered(w['dmg'], w['taper'], attacker, victim) / w['dmg'] if w.get('taper') and w['dmg'] else 1.0


def hit_scalar(victim, damage_type, attacker):
    """What one point of `damage_type` from `attacker` does to `victim` on a direct hit: its armor percent x taken
    (UNRESISTABLE: 1), x the flank (registry.Context.scalar, for the nugget handlers)."""
    return armor_scalar(victim, damage_type) * flank_of(victim, attacker)


def armor_scalar(victim, damage_type):
    """What one point of `damage_type` does to `victim` without the flank: its armor percent x taken (UNRESISTABLE:
    1) -- a passenger's (DamageContained), a DOT tick's (registry.Context.armor)."""
    return (1.0 if damage_type == 'UNRESISTABLE' else
            simunits.percent(victim.armor, damage_type) / 100.0 * victim.taken)


def mend(world, dt, fires):
    """A HEALING gun (ABD_RepairWeapon, the engineer's in a multigunner turret: Garrisons.secondary) mends the nearest
    hurt friendly ground vehicle in its reach by its rate x the armor's HEALING percent. Bench engine_secondrep_e r: a
    Guardian 40 off from 50 to 100 % in about 7 s (37.5 a second), one 150 off and an empty turret's do not.
    INFERRED: the nearest first, its AttributeModifier_UnderRepair, REPAIR_ALLIES_WHEN_IDLE (fights before mending?).
    A host that may not fire (`fires`, deal's test: NO_ATTACK, EMP, an infiltrator's block) mends nothing (review 109 #2)."""
    live = world.living()
    for a in live:
        for w in a.weapons:
            if w.get('type') != 'HEALING' or not fires(a):
                continue
            hurt = [t for t in live if t is not a and t.hp < t.max_hp and 'VEHICLE' in t.kinds
                    and t.surface != 'air' and world.relation(a.owner, t.owner) == 'ALLIES' and in_range(a, t, w)]
            if hurt:
                t = min(hurt, key=lambda t: math.hypot(t.x - a.x, t.y - a.y))
                t.mend(w['dps'] * dt * simunits.percent(t.armor, 'HEALING') / 100.0)


def straight_speed(projectile, own):
    """The projectile template's flight (registry.Context.speed, cached in Damage.projectile_speeds): ProjectileUpdate
    StateMachine="StraightLineProjectile"'s MoveInStraightLine MuzzleVelocity (map units a frame); flight.BEZIER for a
    BezierProjectile; flight.NO_FLIGHT for a template of its own (no inheritFrom) with no flight module at all (bench
    E168 engine_bezier_e: the rocket without its BezierProjectile never reaches its victim); 0 for any other flight or
    no file. The first flight module up the inheritFrom chain answers, comments not counted (review 1121mm #4)."""
    try:
        xml = ''
        for _, text in simunits.xml_chain(projectile, own):
            xml = re.sub(r'<!--.*?-->', '', text or '', flags=re.S)
            if '<BezierProjectile' in xml:
                return flight.BEZIER
            update = next(simunits._blocks(xml, 'ProjectileUpdate'), None)
            if update:
                movement = next(simunits._blocks(update[1], 'MoveInStraightLine'), ('', ''))
                return (simunits._num(simunits._attr(movement[0], 'MuzzleVelocity'))
                        if simunits._attr(update[0], 'StateMachine') == 'StraightLineProjectile' else 0)
        return flight.NO_FLIGHT if xml and 'inheritFrom=' not in xml else 0
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


def _filter(p, rel, t):
    """A ParalyzeNugget's SpecialObjectFilter (simunits.special_weapon) takes `t`, standing `rel` to the firer: its
    Relationship, its IncludeThing, else by Rule (ANY one of Include, ALL of them, NONE: nothing -- INFERRED, bench
    engine_fwupdate: the short circuit's NONE nugget held no conscript), none of Exclude, ExcludeThing,
    StatusBitFlagsExclude."""
    if p['relation'] and rel.rstrip('S') not in {w.rstrip('S') for w in p['relation'].split()}:
        return False
    if t.template.lower() in p['exclude'] or t.kinds & p['unkinds'] or p['status_exclude'] & set(t.status):
        return False
    rule = p['rule'] == 'ANY' and t.kinds & p['include'] or p['rule'] == 'ALL' and p['include'] <= t.kinds
    return bool(rule) or t.template.lower() in p['things']


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
        ally, ground_only, approach, structure, pulse = tuple(rest) + (1.0, False, None, 1.0, None)[len(rest):]
        for t in world.living():
            if math.hypot(t.x - x, t.y - y) > reach:
                continue
            rel = world.relation(owner, t.owner)
            if pulse is not None:       # an EMP pulse (simbody.Life.fire): what its filter takes stands still
                if t is not by and _filter(pulse, rel, t):
                    book = peers.emp_until
                    book[t.serial] = max(book.get(t.serial, 0), frame + simunits._frames(pulse['seconds']))
                continue
            if frame < t.immune_until or t.shielded or t.indestructible:
                continue
            if ground_only and t.surface == 'air':
                continue                    # a crash on the ground; the planes 175 over it are out of its 20
            if (rel + 'S' if rel == 'NEUTRAL' else rel) not in affects:
                continue
            armor = 1.0 if typ == 'UNRESISTABLE' else simunits.percent(t.armor, typ) / 100.0 * t.taken
            if rel == 'ALLIES':
                armor *= ally
            if 'STRUCTURE' in t.kinds:      # a STRUCTURE DamageScalarDetails (the AI's precision strike: AI_POWERS)
                armor *= structure
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
                world.world.kill(t, f'被 {world.label(by)} 的死亡武器炸掉')


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
        """Dispatch the non-damage payload of a projectile arrival (engine/combat/meta_impact.detonate)."""
        meta_impact.detonate(EffectHost(self, world, peers), weapon, target, centre, attacker)

    def meta_impact_detonate(self, world, weapon, centre, attacker, peers):
        """A warhead's shocks at `centre` (engine/combat/meta_impact.launch)."""
        meta_impact.launch(EffectHost(self, world, peers), weapon, centre, attacker)

    def meta_impact_tick(self, world, peers):
        """Each knocked body one trajectory sample on (engine/combat/meta_impact.tick)."""
        meta_impact.tick(EffectHost(self, world, peers))

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
        meta_impact.tick(host)
        for hit in flight.due(self.projectile_hits, world.frame_now()):     # shells fired before land first
            flight.arrive(hit, hurt, peers.projectile_detonate, self.incoming_hit)
        # A cached aim is not permission to fire after a script/modifier stops
        # the shooter. Keep its order; expiry lets fight select it again.
        # Existing-order evidence: work/re/d50_scramble_expiry3.md.
        # INFERRED: exact within-tick stop phase; the bench has coarse snapshots.
        def fires(by):          # the repair gun's too (mend; review 109 #2)
            return by.alive and 'NO_ATTACK' not in by.status and not peers.emp_disabled(by) and \
                not peers.infiltrators.attack_blocked(by)
        for t, rate, by in peers.firing:
            if t.alive and fires(by) and world.t >= weaponset.gate(by, t) - 1e-9:
                h = hurt.setdefault(t.serial, [t, 0.0, by])
                h[1] += rate * dt
                h[2] = by
        for t, w, by in peers.volleys:           # engine line C round 2: a shot lands when its clock says (shots_due)
            if t.alive and fires(by) and world.t >= weaponset.gate(by, t) - 1e-9:
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
                                           emp_until=lambda: peers.emp_until, claims=leech_events, host=host,
                                           boost=weaponset.boost(by, w))
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
            self.hit_reaction_damage(world, t, before_hp - t.hp, peers, by)
            leech.refund(leech_events.get(t.serial), t, before_hp, gap)
            t.set_last_damage(by.owner, by)
            if t.hp <= 0 and t.alive:
                if world.first_death is None:
                    world.first_death = (world.t, t, by)
                world.world.kill(t, f'被 {world.label(by)} 打掉')
        self.chill(world, dt, peers)
        mend(world, dt, fires)

    def mark_cold(self, target, by):
        """`by` is the one of record for the cold `target` took this frame (cold_on, read by chill;
        registry.Context.mark_cold: SecondaryDamage)."""
        self.cold_on[target.serial] = (target, by)

    def hit_reaction_damage(self, world, target, damage, peers, by):
        """E172 gun-hit condition; RotateToSourceWhenDamaged turns a standing target (no way, no live goal) to
        `by` at its turn rate (engine_hitreaction_r: shielded, a back hit once, then front hits). Animation unmodelled.

        INFERRED: start/refresh the SDK lifetime on positive applied damage,
        using the common expiry store. The bench asserts ever-on and final
        clear, not the precise first/last frame or repeated-hit refresh rule.
        Turning only when the reaction plays, and the idle test, are INFERRED.
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
            if rule['rotate'] and not target.path and not getattr(target.goal, 'alive', False):
                target.face = math.atan2(by.y - target.y, by.x - target.x)
            world.used.add('hit reaction')
            world.guessed.add('HitReactionBehavior: exact timing/refresh INFERRED')

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
                simmodifier.modify(world, t)
                if step >= 0:
                    world.note('冷冻', f'{world.label(t)} 冷冻到第 {step + 1} 档（{tr["steps"][step][0]:.0%} 生命值）')
                if step >= 0 and tr['steps'][step][4] and t.alive:
                    world.world.kill(t, f'被 {world.label(by)} 冻死')
