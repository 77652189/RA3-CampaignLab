"""L2 body: health lost by itself, death and removal (ADR 0029, docs/engine/sim-layers.md; bench docs/engine/sell.md).

`Life` kills a body (`kill`: its Die modules told -- its spawn's refill, its garrison, its FireWeaponWhenDead's weapon
(`fire`) and an aircraft's falling wreck (`create`, `air_crash`) queued as death blasts) or deletes it (`delete`: no death) -- the one entry each (step B4b) --, sells a structure
(`sell`: the refund; its StructureSellUpdate module deletes it later, as a lifetime's and a toppled prop's modules end
theirs -- the expire cell's modules since steps M1, M2, M10) and runs LoseHealthUpdate (`lose_health`), over the world
it is given (simworld.WORLD_API only). The peers it needs are handed in by the caller (Sim.destroy / delete / sell / lose_health): the garrison (simgarrison, L2), the
death-blast queue (L2 queues, L3's death_blast_due fires them), the ground's height, the template's toggles and the
modifiers (L2), `destroy` itself for a lifetime's death, and the money's `credit` (L4) for a sale's refund -- this
module never imports them.
Fields it owns: its own `lose_of`; on a body `alive`, `deleted`, `died_at`.
Two entries for the skirmish AI, which writes no body field itself: `last_until` (a lifetime the reader missed) and
`fill` (the stats of a body simunits does not know, from the model's library).
"""
import importlib
import math

import simunits
from engine.kernel import interfaces, module

SELL_PERCENT = 0.5              # SellPercentage (SDK default); SellTime: engine/modules/sell.py
HOVER_DRIFT = 0.2               # a frame: a hovering plane's velocity (air_crash)


class Life:
    def __init__(self):
        self.lose_of = {}              # template -> simunits.lose_health rule
        self.blasts_of = {}            # death weapon -> simunits.weapon_blasts (the world's own templates are fixed)

    def create(self, world, b, ocl, airborne, death_blasts, ground_z):
        """The kernel's make (World.create) for a CreateObjectDie (engine/modules/createobjectdie.py, step B5b): a
        death in the air makes its wrecks fall (air_crash), a death of age leaves its list's objects (leave)."""
        if airborne:
            self.air_crash(world, b, ocl, death_blasts, ground_z)
        else:
            self.leave(world, b, ocl)

    def leave(self, world, b, ocl):
        """What a death of age leaves (b killed, NAMED_DESTROYED, gone from areas at once -- bench 2026-11-07
        engine_life, no body lingers): each object its ObjectCreationList lists made where it stood, that frame, its
        owner's, team's and facing (the ice core's wall)."""
        for tmpl in simunits.ocl_objects(ocl, world.own):
            n = world.add(f'#left {len(world.bodies)} of {b.name}', tmpl, b.owner, b.x, b.y, by=b.name, at=world.t)
            n.team, n.angle = b.team, b.angle
            world.note('留下', f'{tmpl}（{world.label(b)} 寿命到了）')
            if world.blocks(n):
                world.reblock()

    def sell(self, world, b, garrison, modify, credit):
        """SELL_OBJECT (bench 2026-11-06 engine_sell, docs/engine/sell.md): a living structure that is not unpacking
        and not already sold is paid at once -- round(round(cost x 50%) x health share) -- and carries SOLD; 30 frames
        later it is deleted (no death, no ruin); meanwhile it still counts as power and can still be killed (then the
        money stays paid and it is just dead). Anything else: nothing happens. Not read: a template's RefundValue,
        NOT_SELLABLE, the factory's queue. Only a template with a StructureSellUpdate sells (up its inheritFrom
        chain, the template data port simunits.module_blocks; in the SDK only BaseStructure.xml has one;
        bench 11-17 engine_garrison del: SELL_OBJECT on a civilian house, which has none, leaves it standing, unsold,
        owned and still manned, no refund). The garrison empties in the sale's frame (simgarrison; bench 11-17
        engine_sell g: a SovietBunker's peacekeeper ENCLOSED 9 frames, out from the sale on)."""
        if b is None or not b.alive or 'STRUCTURE' not in b.kinds:
            return
        m = b.find(interfaces.Sell)             # StructureSellUpdate (engine/modules/sell.py, step M10)
        if m is None or m.gone_frame() is not None:
            return
        garrison.empty(b)
        if b.unpack_end is not None and world.frame_now() < b.unpack_end:
            return                                                  # engine_sell c: refused while it unpacks
        world.used.add('sell')
        cost = simunits.production(b.template, world.own)[0]
        refund = math.floor(math.floor(cost * SELL_PERCENT + 0.5) * (b.hp / b.max_hp if b.max_hp else 1.0) + 0.5)
        credit(b.owner, refund)
        b.script_status.add('SOLD')
        modify(b)
        m.start_sale(world.frame_now())
        world.note('出售', f'{world.label(b)}（退 {refund}）')

    def kill(self, world, b, why, death='NORMAL', cause=''):
        """The one death entry (Sim.destroy, step B4b): b killed -- its Die modules told (module.Death, `death` its
        death type: a crush's CRUSHED lies its SlowDeath out; `cause` 'lifetime' a death of age: its CreateObjectDie
        leaves its list, World.create; an aircraft's makes its wreck fall; its FireWeaponWhenDead fires, World.fire),
        then its Destroy modules (_out); an immortal body takes lethal damage instead, and a prop that cannot die falls
        or stays."""
        if not b.alive:
            return
        if b.immortal:
            # Object::kill (also script KILL, crushing etc.) is lethal damage;
            # only direct deletion bypasses the body's internalChangeHealth.
            b.damage(b.max_hp)
            return
        if b.prop and (b.topple or b.prop == 'stays'):
            # engine_propbody b (bench 11-10): a killed topple prop falls where it stands (no fall time) and is gone
            # its delay later, never dying (expire; 61 / 121 frames counted with the kill's); a PropBody with nothing
            # to take its death stays for good
            if b.topple:
                b.find(interfaces.Topple).fall_where_it_stands(world.frame_now())
            return
        self._out(world, b, why, False, death, cause)
        b.set_hp(0.0, tell=False)
        self._gone(world, b, why, False)

    def fire(self, world, b, weapon, death_blasts):
        """The kernel's fire (World.fire) for a FireWeaponWhenDead (engine/modules/fireweaponwhendead.py, step B5c;
        bench 11-05 engine_spawn_refill): each DamageNugget of the WeaponTemplate `weapon` (simunits.weapon_blasts)
        queued to go off where b died, its delay after, as b's (simdamage.death_blast_due)."""
        for dmg, typ, reach, after, affects, ally in self.blasts(world, weapon):
            world.used.add('death weapon')
            death_blasts.append((world.frame_now() + simunits._frames(after), b.x, b.y, dmg, typ, reach,
                                 affects, b.owner, b, ally, False))

    def delete(self, world, b, why):
        """The one deletion entry (Sim.delete, step B4b): b taken out, no death -- no lethal damage, no death weapon,
        no Die module told; its Destroy modules take its spawned children and passengers with it (_out)."""
        if b.alive:
            self._out(world, b, why, True)
            self._gone(world, b, why, True)

    def _out(self, world, b, why, delete, death='NORMAL', cause=''):
        """What a death and a deletion share: b out of the fight -- the only write of a body's alive / deleted /
        died_at (guard 10, tests/guards/test_kernel.py) -- then its modules told, the one broadcast of a thing's end
        (step B4c, the private model's Object.die then destroyObject): a death tells its Die modules (module.Death),
        both tell its Destroy modules, each in module order -- the SpawnBehavior's queue emptied and its children
        deleted, the SlavedUpdate's maker told of the death, the Contain's passengers out (World.vacate)."""
        b.alive, b.deleted, b.path, b.died_at = False, delete, [], world.t
        if not delete and b.last_by is not None and b.last_hit is not None:
            world.kills.append((b.last_hit, b.last_by, b.template, b.name))     # cond_retail: who killed what
        if not delete:
            info = module.Death(world.frame_now(), why, death, cause)
            for m in b.find(interfaces.Die):
                m.on_die(info)
        for m in b.find(interfaces.Destroy):
            m.on_destroy()

    def _gone(self, world, b, why, delete):
        world.note('删除' if delete else '摧毁', f'{world.label(b)}（{why}）')
        world.change()
        if world.blocks(b):
            world.reblock()

    def air_crash(self, world, b, ocl, death_blasts, ground_z):
        """Physics P5 (checks/engine_crash_fall.py): an aircraft killed in the air is gone at once and its airborne
        CreateObjectDie (engine/modules/createobjectdie.py: its list `ocl`, simunits.ocl_wrecks) makes a wreck
        LIKE_EXISTING with its velocity x the OCL's VelocityScale;
        a wreck that falls (KillWhenRestingOnGround) dies where it comes to rest (simunits.crash_frames: the fall's
        curve, its own GravityMultiplier) and its FireWeaponWhenDead goes off there (the Apollo's / MiG's
        NormalAircraftDeathWeapon: 150 EXPLOSIVE radius 20, allies 50 %), on the ground only. The plane is at its
        locomotor's PreferredHeight over the ground (simunits.fly_height; bench 174.94), flying at its speed towards
        its path's next point, else still (a hovering one). Of a CHOOSE_ONE list (the game draws one: the Apollo's
        Collapse or Dying) the first that falls and has a weapon (INFERRED choice: the crash that can hurt, the run
        repeatable). INFERRED: level ground (the landing's own height not looked up), the death on the frame it rests,
        the nugget's MetaImpact (ShockWave 50, radius 50) not dispatched."""
        got = simunits.ocl_wrecks(ocl, world.own)
        if not got:
            return
        choose, wrecks = got
        blasts = {w['template']: self.wreck_blasts(world, w['template']) for w in wrecks}
        hits = [w for w in wrecks if w['falls'] and blasts[w['template']]]
        if choose and len(wrecks) > 1:
            world.used.add('crash choice')
            hits = hits[:1]
        if not hits:
            return
        ground = ground_z(b.x, b.y)
        z = b.z if b.z is not None else ground + simunits.fly_height(b.template, world.own)
        # still (hovering): HOVER_DRIFT along its facing (bench 11-12 engine_crash_hit: both hovering Apollos' wrecks
        # logged v (0.1, 0, 0) = 0.5 x 0.2 facing east; INFERRED for other planes and facings)
        vx, vy = HOVER_DRIFT * math.cos(b.angle), HOVER_DRIFT * math.sin(b.angle)
        if b.path and b.speed > 0 and not b.engaged:
            tx, ty = b.path[0]
            d = math.hypot(tx - b.x, ty - b.y)
            if d > 0:
                vx, vy = (tx - b.x) / d * b.speed / simunits.LIFE_FPS, (ty - b.y) / d * b.speed / simunits.LIFE_FPS
        for w in hits:
            frames, end = simunits.crash_frames((b.x, b.y, z), (vx * w['scale'], vy * w['scale'], 0.0), ground,
                                                w['gravity'])
            if abs(ground_z(end[0], end[1]) - ground) > 1e-3:
                world.gap('Physics', w['template'], '坠机残骸落到不同高度的地面：落点和时刻按起点地面算')
            world.used.add('air crash')
            for dmg, typ, reach, after, affects, ally in blasts[w['template']]:
                death_blasts.append((world.frame_now() + frames + simunits._frames(after), end[0], end[1], dmg,
                                     typ, reach, affects, b.owner, b, ally, True, (end[0] - b.x, end[1] - b.y)))

    def blasts(self, world, weapon):
        """A death weapon's DamageNuggets (simunits.weapon_blasts), read once a world."""
        if weapon not in self.blasts_of:
            self.blasts_of[weapon] = simunits.weapon_blasts(weapon, world.own)
        return self.blasts_of[weapon]

    def wreck_blasts(self, world, template):
        """A falling wreck's death weapons, the wreck being no thing in the simulator: the DamageNuggets (blasts) of
        the DeathWeapon of each FireWeaponWhenDead of its template (World.data_of: the module's own parse,
        engine/modules/fireweaponwhendead.py) that a NORMAL death of a thing with no status sets off (INFERRED: a
        wreck resting on the ground, KillWhenRestingOnGround, dies NORMAL), in module order."""
        return [n for d in world.world.data_of(template, 'FireWeaponWhenDead') if d.fires('NORMAL')
                for n in self.blasts(world, d.weapon)]

    def lose_health(self, world, frame, toggles_of):
        """LoseHealthUpdate gated by an ObjectStatusValidation (simunits.lose_health): DamagePerSecond / fps a frame
        while the body's own toggle (its ToggleState's bits) carries every RequiredStatus and it has no ForbiddenStatus
        (engine_acts_tgl KV: the Kirov's afterburners, pressed, drained 200/s). A script's UNIT_CHANGE_OBJECT_STATUS bit
        alone starts nothing (E146 engine_objectbatch a / b: the dreadnought's drain on a tank, GENERIC_TOGGLE_STATE
        given by script at 8 s and read back true, held 100 % to s25 with HealthTrigger 101 % and 0 % alike) --
        INFERRED that the press is what wakes the update; the host (aircraft against tank) was not separated."""
        cache = self.lose_of
        for b in world.bodies.values():
            if not b.alive:
                continue
            if b.template not in cache:
                cache[b.template] = simunits.lose_health(b.template, world.own)
            rule = cache[b.template]
            if not (rule and rule[0]) or rule[2] & set(b.status):
                continue
            toggled = set()
            for i, tm in enumerate(toggles_of(b)):
                toggled |= tm['states'][b.toggle_at.get(i, 0) % len(tm['states'])]['status']
            if rule[1] <= toggled & set(b.status):
                b.damage(rule[0] / world.fps)
                world.used.add('lose health')


def last_until(world, b, frame):
    """A lifetime the template data port left out (retail LifetimeUpdate, simunits.OWN_ONLY), set from outside: the
    body dies at `frame` as any other (engine/modules/lifetime.py), its module attached now when it has none. The
    skirmish AI's dodge read of a retail fixed LifetimeUpdate does this (simai.Brain.micro_team; INFERRED: the frame
    it first sees the body as its birth)."""
    m = b.find(interfaces.Lifetime) if b.modules else None
    if m is None:
        m = world.world.attach(b, 'LifetimeUpdate')
    m.set_die_frame(frame)


def fill(b, lib, own):
    """A body simunits knows nothing of (its table misses the second GameObject of a file, such as the Riptide's
    AlliedAntiInfantryVehicle_Ground the war factory's button makes: speed 0, no KindOf -- HOOKS 6): KindOf and
    speed from the model's library `lib`, health / armour / weapons from the template of the name without its last
    '_' part when simunits knows that one (INFERRED: the same unit). The skirmish AI calls it for what its factories
    made (simai.Brain.unit_due); `own` is the world's own templates (WORLD_API own)."""
    if 'all' not in (b.guessed or []):
        return
    tpl = lib.template(b.template)
    if tpl is None:
        return
    ro = importlib.import_module('ra3model.objects.runoffmap')
    b.kinds = frozenset(tpl.kinds)
    b.speed = float(ro.normal_speed(lib, tpl) or 0.0)
    b.surface = 'both' if 'AMPHIBIOUS' in tpl.kinds else 'air' if 'AIRCRAFT' in tpl.kinds else b.surface
    base = b.template.rsplit('_', 1)[0]
    if base != b.template:
        st, f = simunits.stats(base, own), simunits.fight(base, own)
        if f['hp']:
            b.set_hp(f['hp'], f['hp'], tell=False)
            b.armor, b.weapons = f['armor'], f['weapons']
        b.surface, b.sight = st['surface'], st['vision'] or b.sight
    b.guessed = ['all: simai.fill']
