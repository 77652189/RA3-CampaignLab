"""L2 specials (ADR 0029, docs/engine/sim-layers.md): a body's own special abilities and a superweapon's hits landing.

`Specials` runs an ActivateModuleSpecialPower on self (`self_power_press`), a MovementSpecialPower's rush
(`movement_power_press`), a ProjectileSelf leap (`leap_press`), a WeaponFireSpecialAbilityUpdate (`wfire_press` /
`start` / `wfire_due`), what those leave running out (`self_power_due`) and a superweapon's hits (`blast_due`), over the
world it is given (simworld.WORLD_API only). The peers it needs are handed in by the caller (Sim.self_power_press /
... / Sim.blast_due): the modifiers' re-set (`modify`, L2), a body's route (`send`, L2 simlocomotion), its death
(`destroy`, L2 simbody), who stands still till when (`emp_until`: () -> the {body.serial: frame} book, made on first
use), the queues other blocks share (the superweapon `blasts` a script casts, the `casts` a script condition reads,
the `death_blasts` L3 fires), the players' upgrades (`player_ups`, L4), how two owners stand (`relation`), the fight's
first death (`first_death(body, killer)`), and L3's detonation and ground height for a leap's landing (`detonate`,
`ground_z`) -- this module never imports them.
Fields it owns: its own `wfires`, `leaps_due`, `leap_ground_hits`, `movement_due`, `self_bits_due`.
"""
import math

import simunits
from simpower import hit_at
from simworld import CIV, GAP_WEAPON

WFIRE_LAG = 0                  # frames between a weapon-fire ability's UnpackTime and its weapon (engine_wfire)
WFIRE_REAIM = 20                # a target this far off the spot its caster walks to: the caster re-aimed (INFERRED)
# a TargetType NONE ability (the bear's roar) pressed _ON_NAMED: it goes off this much later once the caster is up to
# the target (engine_acts_wet RN 60 off / RF 300 off both a reading or so behind the plain roar: INFERRED, fitted).
# Refitted in A round 253 once the bears no longer chase in the opening frame (IDLE_SCAN_FROM): acts_mix passes for
# any lag 0-31, acts_wet for 15-20 (14: C4 out of its hold a reading early; 21: the roars' cast count a reading
# late); the band's middle taken. (Before, 16-28 / 22 was fitted on that opening walk, engine_dam showed none.)
NONE_TARGET_LAG = 18


class Specials:
    def __init__(self):
        self.wfires = []               # a WeaponFireSpecialAbilityUpdate press waiting to go off (wfire_due)
        self.leaps_due = []            # (landing frame, body, point): a ProjectileSelf leap in the air
        self.leap_ground_hits = []     # (frame, body, weapon, centre): a landed leap's ground weapon to go off
        self.movement_due = {}         # body name -> (end frame, body, bits, old speed): a MovementSpecialPower on
        self.self_bits_due = []        # (frame, body, bits): a self power's trigger / shield bits to drop

    def blast_due(self, world, frame, blasts, first_death, destroy):
        """A superweapon's hits landing by `frame` (SUPERWEAPON_HITS): every living object, friend or foe, within the
        table's reach loses the damage read off its centre distance (linear between the measured distances)."""
        for d in [d for d in blasts if d[0] <= frame]:
            blasts.remove(d)
            _, x, y, table, owner, by = d
            for t in world.living():
                dmg = hit_at(table, math.hypot(t.x - x, t.y - y))
                if dmg <= 0 or frame < t.immune_until or t.shielded or t.indestructible:
                    continue
                t.damage(dmg)
                t.set_last_damage(owner, by.name)
                if t.hp <= 0 and t.alive:
                    first_death(t, by)
                    destroy(t, f'被 {world.label(by)} 的超武打掉')

    def movement_power_press(self, world, b, button, point, modify, send):
        """E171: in-range static waypoint rush; ordinary path movement with SDK speed.

        INFERRED: status/speed last Duration from the press, expiry stops movement;
        the bench proves activation, displacement and final exit, not those exact
        boundaries. Turning/acceleration, collision and repeated orders remain gaps.
        """
        sp = simunits.movement_power(b.template, button, world.own)
        distance = math.hypot(point[0] - b.x, point[1] - b.y)
        if distance < sp['minimum'] or (sp['maximum'] and distance > sp['maximum']):
            world.guessed.add('MovementSpecialPower: out-of-range approach unmodelled')
            return False
        jobs = self.movement_due
        if b.name in jobs:
            world.guessed.add('MovementSpecialPower: repeated press unmodelled')
            return False
        now = world.frame_now()
        new = sp['bits'] - b.script_status
        old_speed = b.base['speed'] if b.base is not None else b.speed
        jobs[b.name] = (now + sp['duration'], b, new, old_speed)
        b.script_status |= new
        speed = simunits.locomotor_speed(b.template, world.own, sp['locomotor']) if sp['locomotor'] else None
        if speed is not None and b.base is not None:
            b.base['speed'] = speed
        xml = world.xml_of(b.template)
        mod = simunits.modifier(xml, sp['modifier']) if sp['modifier'] else None
        if mod and mod['frames']:
            b.auras_on[sp['modifier']] = (now + mod['frames'], xml)
        modify(b)
        b.goal, b.mode = None, 'move'
        send(b, point)
        world.used.add('movement special power')
        world.guessed.add('MovementSpecialPower: exact phase timing, cooldown and collisions unmodelled')
        return True

    def self_power_press(self, world, b, button, modify):
        """An ActivateModuleSpecialPower on self (simunits.self_module_power): its AttributeModifier hangs on b for its
        Duration from the press (b.auras_on, so modify() takes its bits and SPEED and drops them when it runs out); the
        power's SpecialAbilityUpdate SetObjectStatusOnTrigger bits through its PackTime (engine_acts_mix SB / EA)."""
        sp = simunits.self_module_power(b.template, button, world.own)
        xml = world.xml_of(b.template)
        mod = simunits.modifier(xml, sp['modifier'])
        now = world.frame_now()
        world.used.add('self power')
        if mod and mod['frames']:
            b.auras_on[sp['modifier']] = (now + mod['frames'], xml)
        if sp['trigger'] and sp['pack']:
            new = sp['trigger'] - b.script_status
            b.script_status |= new
            self.self_bits_due.append((now + sp['pack'], b, new))
        for bits, duration in sp.get('shields', ()):
            # E153 engine_activate: only the linked consumer's status lifetime.
            # Projectile interception, damage cap and early termination remain gaps.
            # INFERRED: overlapping/repeated activations use the same bit ownership
            # convention as the existing pack phase; only a single press is measured.
            world.guessed.add('ShieldSphereUpdate: projectile absorption and early termination unmodelled')
            new = bits - b.script_status
            b.script_status |= new
            self.self_bits_due.append((now + duration, b, new))
        modify(b)
        world.note('技能', f'{world.label(b)} 按 {button}：{sp["modifier"]}')
        return True

    def leap_press(self, world, b, button, p, send, emp_until):
        """A WeaponFireSpecialAbilityUpdate whose weapon is ProjectileSelf (the Sickle's leap, AT_WAYPOINT): b stands
        its UnpackTime, then flies to the point at the WeaponSpeed and lands there (engine_acts_mix LP: 250 off, in its
        square by the second reading after the press). Beyond StartAbilityRange: drives there instead (INFERRED, not
        measured: FAIL_WITH_INVALID_APPROACH)."""
        ab = simunits.weapon_fire_ability(b.template, button, world.own)
        speed = simunits.self_projectile_speed(ab['weapon'], world.own)
        d = math.hypot(p[0] - b.x, p[1] - b.y)
        world.used.add('weapon fire ability')
        if d > ab['range']:
            world.note('技能', f'{world.label(b)} 按 {button}：超出 {ab["range"]:.0f}，开过去')
            b.goal, b.mode = None, 'move'
            send(b, p)
            return True
        land = world.frame_now() + ab['unpack'] + int(math.ceil(d / speed * simunits.LIFE_FPS))
        b.path, b.dest = [], None
        deadlines = emp_until()       # holds still till it lands (INFERRED)
        deadlines[b.serial] = max(deadlines.get(b.serial, 0), land)
        self.leaps_due.append((land, b, p))
        world.note('技能', f'{world.label(b)} 按 {button} 跳到 ({p[0]:.0f}, {p[1]:.0f})')
        return True

    def self_power_due(self, world, frame, modify, detonate, ground_z):
        for job in list(self.leap_ground_hits):
            due, b, weapon, centre = job
            if frame >= due:
                self.leap_ground_hits.remove(job)
                if b.alive:
                    detonate(weapon, b, centre, b)
                    world.used.add('leap ground hit')
        movement = self.movement_due
        for key, (due, b, bits, old_speed) in list(movement.items()):
            if frame >= due:
                del movement[key]
                b.script_status.difference_update(bits)
                if b.base is not None:
                    b.base['speed'] = old_speed
                b.path, b.dest = [], None
                modify(b)
        for job in list(self.leaps_due):
            if frame >= job[0]:
                self.leaps_due.remove(job)
                if job[1].alive:
                    b = job[1]
                    b.x, b.y = job[2]
                    ground_weapon = simunits.self_projectile_ground_weapon(b.template, world.own)
                    if ground_weapon:
                        # CampKSickle a/b: first grounded probe f114, shock f115.
                        # Position/time of the leap itself remain INFERRED.
                        weapon = simunits.weapon_table(world.own).get(ground_weapon)
                        if weapon is None:
                            world.gap(GAP_WEAPON, ground_weapon, '跳跃落地武器未解析')
                        else:
                            centre = (b.x, b.y, ground_z(b.x, b.y))
                            self.leap_ground_hits.append(
                                (frame + 1, b, weapon, centre))
                            if weapon.get('dmg') or weapon.get('damage'):
                                world.gap(GAP_WEAPON, ground_weapon, '落地伤害筛选及衰减未对拍，仅派发冲击')
                    world.change()
        due = self.self_bits_due
        for job in list(due or ()):
            if frame >= job[0]:
                due.remove(job)
                job[1].script_status.difference_update(job[2])
                modify(job[1])

    def wfire_press(self, world, b, button, target, send, emp_until):
        """A WeaponFireSpecialAbilityUpdate's button (simunits.weapon_fire_ability; bench 11-11 engine_wfire): the
        caster walks to within StartAbilityRange of a named target first, then stands UnpackTime and the SpecialWeapon
        goes off once (wfire_due); it stands on through PackTime when BUSY_DURING_PACK, FreezeAfterTriggerDuration
        always. A target gone or missing: nothing."""
        ab = simunits.weapon_fire_ability(b.template, button, world.own)
        t = world.body(target) if target else None
        if target and not (t and t.alive):
            world.note('技能', f'{world.label(b)} 按 {button}：目标 {target} 不在')
            return False
        world.used.add('weapon fire ability')
        job = dict(by=b, ab=ab, eff=simunits.special_weapon(ab['weapon'], world.own), target=t, button=button,
                   fire_at=None)
        if t and simunits.power_target_type(simunits.command_power(button, world.own)) == 'NONE':
            job['lag'] = NONE_TARGET_LAG
        self.wfires.append(job)
        world.note('技能', f'{world.label(b)} 按 {button}' + (f' 对 {world.label(t)}' if t else ''))
        if t and math.hypot(t.x - b.x, t.y - b.y) - t.radius > ab['range']:
            b.goal, b.mode = None, 'move'
            send(b, (t.x, t.y))
        else:
            self.start(world, job, emp_until)
        return True

    def start(self, world, job, emp_until):
        b, ab = job['by'], job['ab']
        now = world.frame_now()
        job['fire_at'] = now + ab['unpack'] + WFIRE_LAG + job.get('lag', 0)
        b.path, b.dest = [], None
        hold = job['fire_at'] + max(ab['freeze'], ab['pack'] if ab['busy_pack'] else 0)
        deadlines = emp_until()       # stands still (INFERRED: as EMP'd)
        deadlines[b.serial] = max(deadlines.get(b.serial, 0), hold)

    def wfire_due(self, world, frame, casts, death_blasts, player_ups, relation, send, emp_until):
        """The weapon-fire abilities going off by `frame` (wfire_press): the weapon's DamageNuggets as a death blast
        round the caster (radius, delay, RadiusDamageAffects), its ParalyzeNuggets on the target (radius 0) or on
        what the filter takes within the radius: EMP pauses it (emp_until), UNMANNED hands a vehicle to the
        civilian side (the pilot shot out)."""
        for job in list(self.wfires):
            b, ab, t = job['by'], job['ab'], job['target']
            if not b.alive or (t is not None and not t.alive):
                self.wfires.remove(job)
                continue
            if job['fire_at'] is None:
                # the range to the target's edge (INFERRED: engine_wfire far, 74 frames; to its centre 81)
                if math.hypot(t.x - b.x, t.y - b.y) - t.radius <= ab['range']:
                    self.start(world, job, emp_until)
                elif not b.path or (b.dest is not None and
                                    math.hypot(t.x - b.dest[0], t.y - b.dest[1]) > WFIRE_REAIM):
                    # the target walked off the spot the caster was sent to: after it where it is now (a01's
                    # intro bears, StartAbilityRange 0, sent at Peacekeepers that set off on a path 10 s later
                    # never got there to roar; INFERRED: re-aimed once it is a path node off)
                    send(b, (t.x, t.y))
                continue
            if frame < job['fire_at']:
                continue
            self.wfires.remove(job)
            # engine_acts_wet (round 226): each bear's roar seen cast once by PLAYER_TRIGGERED_SPECIAL_POWER, the
            # ones pressed _ON_NAMED when the bear has walked up to its target
            casts.append((frame, b.owner, ab['power'].lower(), b.name, None))
            eff = job['eff']
            for dmg, typ, reach, after in eff['damage']:
                death_blasts.append((frame + simunits._frames(after), b.x, b.y, dmg, typ, reach,
                                     eff['affects'], b.owner, b))
            ups = {u.lower() for u in b.upgrades | player_ups.get(b.owner, set())}
            for p in eff['paralyze']:
                if (p['required_upgrade'] and p['required_upgrade'].lower() not in ups) or \
                        (p['forbidden_upgrade'] and p['forbidden_upgrade'].lower() in ups):
                    continue
                pool = [t] if t is not None and not p['radius'] else \
                    [o for o in world.living() if math.hypot(o.x - b.x, o.y - b.y) <= p['radius']]
                for o in pool:
                    if o is b or (p['include'] and not o.kinds & p['include']) or o.template.lower() in p['exclude']:
                        continue
                    if p['relation'] and relation(b.owner, o.owner) != p['relation']:
                        continue
                    if p['kind'] == 'EMP':
                        deadlines = emp_until()
                        deadlines[o.serial] = max(deadlines.get(o.serial, 0), frame + simunits._frames(p['seconds']))
                    elif p['kind'] == 'UNMANNED' and o.owner != CIV:
                        o.owner, o.path, o.dest, o.goal = CIV, [], None, None
                        world.note('易主', f'{world.label(o)} 的驾驶员被打掉，归中立')
                        world.change()
                    else:
                        world.gap(GAP_WEAPON, 'ParalyzeNugget', f'{p["kind"]} 没模拟')
            world.note('技能', f'{world.label(b)} 的 {ab["weapon"]} 打出')
