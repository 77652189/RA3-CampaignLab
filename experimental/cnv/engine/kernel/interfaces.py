"""The fixed interfaces a module implements (docs/engine/sim-modules.md 2). A module class inherits the interfaces it
implements; a caller finds modules by interface (Thing.find), never by a concrete module class or by probing for a
method. Only the core ones are here; a family's own (exits, docks, projectiles ...) come with that family. Adding a
method to an interface is an architecture change (the refactor line's)."""

SLEEP = None                # Update.update returns this: asleep until World.wake


class Interface:
    """The base of every interface."""
    __slots__ = ()


class Update(Interface):
    """Runs in one cell of the frame order: PHASE names the cell, ORDER the place among the update classes of that
    cell, RUNS_DISABLED whether it runs while its object is disabled."""
    __slots__ = ()
    PHASE = None
    ORDER = 0
    RUNS_DISABLED = False

    def update(self, frame):
        """Advance this frame; -> frames until the next run (at least 1), or SLEEP."""
        raise NotImplementedError


class Body(Interface):
    """Health, one a thing: the only writer of health. It tells the thing's Damage modules after a change."""
    __slots__ = ()

    def attempt_damage(self, amount):
        """Health down by `amount`, not below 0 (an immortal's: its floor); a PropBody takes none."""
        raise NotImplementedError

    def attempt_healing(self, amount):
        """Health up by `amount`, at most the maximum (math.inf: to full)."""
        raise NotImplementedError

    def health(self):
        raise NotImplementedError

    def max_health(self):
        raise NotImplementedError

    def set_health(self, hp, max_hp=None, tell=True):
        """The one write of health and maximum (max_hp None: kept; no floor); tell=False: being made, or dying --
        else the thing's Damage modules are told (Thing.health_moved)."""
        raise NotImplementedError

    def percent(self):
        """Health in percent of the maximum, what the scripts read (a PropBody's: 0)."""
        raise NotImplementedError

    def set_percent(self, pct):
        """A script's health in percent (not below an immortal's floor)."""
        raise NotImplementedError

    def make(self, hp, floor=None, death=None):
        """The host makes the thing (step B2b, Sim.add): health and maximum `hp`; a floor makes it immortal (a
        ManagerBody's proxy); a PropBody's death to a script kill ('dies' / 'stays')."""
        raise NotImplementedError

    def kind(self):
        """Its XML tag (ActiveBody, ImmortalBody, PropBody, ManagerBody ...)."""
        raise NotImplementedError

    def floor(self):
        """The health an immortal body holds at (1 HP; a ManagerBody proxy's 1 %)."""
        raise NotImplementedError

    def is_immortal(self):
        raise NotImplementedError

    def prop_death(self):
        """None unless a PropBody; then what a script kill does to it: 'dies' / 'stays'."""
        raise NotImplementedError

    def damage_state(self):
        """'pristine' / 'damaged' / 'really_damaged'."""
        raise NotImplementedError

    def last_damage(self):
        """(player, object name) of the damage that came last (step B3, the Generals ActiveBody's last DamageInfo):
        player None -- a script's kill, or never hit; object None -- no object of ours (a run script's hit)."""
        raise NotImplementedError

    def last_attacker(self):
        """The object of that damage itself (None as last_damage's), whatever has been made under its name since:
        the game keeps the source's id (11-19 same-name sweep)."""
        raise NotImplementedError

    def set_last_damage(self, player, by=None):
        """The one write of the last damage: every weapon, superweapon, crush and script hit names its source (the
        object that hit, or None)."""
        raise NotImplementedError

    def is_indestructible(self):
        """The Indestructible panel flag (weapons and superweapons do no damage; script damage still does)."""
        raise NotImplementedError

    def set_indestructible(self, flag):
        raise NotImplementedError

    def bits_read_until(self):
        """The frame a script's NAMED_DAMAGE killed it in (step B4a; None: not so killed): its status bits still
        read in that frame (engine_sell e); a death of any other kind reads false from the kill."""
        raise NotImplementedError

    def set_bits_read_until(self, frame):
        raise NotImplementedError


class Damage(Interface):
    """Told after its thing's health changed."""
    __slots__ = ()

    def on_damaged(self, info):
        raise NotImplementedError

    def on_healed(self, info):
        raise NotImplementedError

    def on_damage_state(self, old, new):
        raise NotImplementedError


class Die(Interface):
    """Told when its thing dies (step B4c: simbody.Life.kill, in module order, before the Destroy modules): `info` a
    module.Death; it decides itself (by the XML's death types, rank and status) whether it acts. A deletion tells
    none (Generals destroyObject skips the die modules)."""
    __slots__ = ()

    def on_die(self, info):
        raise NotImplementedError


class Destroy(Interface):
    """Told once, the moment its thing leaves the world (step B4c, the Generals onDelete): deleted, or killed (after
    the Die modules; a slow death too at the kill, not at its lie's end: decided in step B5a,
    engine/modules/slowdeath.py)."""
    __slots__ = ()

    def on_destroy(self):
        raise NotImplementedError


class SlowDeath(Interface):
    """SlowDeathBehavior (step B5a): its DestructionDelay (lies, seconds), how long this death lies (lie: the delay
    for a crush, else LINGER) and whether its attributes name no death types (is_plain: the one the body lies by);
    told of its thing's death before the Die modules (begin: `info` a module.Death; B5 review e #7)."""
    __slots__ = ()

    def begin(self, info):
        raise NotImplementedError

    def lies(self):
        raise NotImplementedError

    def lie(self):
        raise NotImplementedError

    def is_plain(self):
        raise NotImplementedError


class CreateOnDeath(Interface):
    """CreateObjectDie (step B5b): the ObjectCreationList it makes (creation_list), whether its DieMuxData takes a
    death type (takes) and a death in the air (takes_airborne: RequiredStatus / ExemptStatus against the thing's
    status, module.status_now; B5 review e #6)."""
    __slots__ = ()

    def creation_list(self):
        raise NotImplementedError

    def takes(self, death):
        raise NotImplementedError

    def takes_airborne(self, status=None):
        raise NotImplementedError


class DeathWeapon(Interface):
    """FireWeaponWhenDead (step B5c): the WeaponTemplate it fires where its thing died (death_weapon) and whether a
    death of a type sets it off (fires: InitiallyActive and its DieMuxData's death types)."""
    __slots__ = ()

    def death_weapon(self):
        raise NotImplementedError

    def fires(self, death):
        raise NotImplementedError


class Create(Interface):
    """Told once its thing is made (World.build), with the frame it was made in (step M1)."""
    __slots__ = ()

    def on_create(self, frame):
        raise NotImplementedError

    def on_build_complete(self):
        raise NotImplementedError


class Lifetime(Interface):
    """LifetimeUpdate, one a thing (step M1): the frame its thing dies of age (None: not set), and setting it from
    outside (the skirmish AI's late read of a retail lifetime, simbody.last_until)."""
    __slots__ = ()

    def die_frame(self):
        raise NotImplementedError

    def set_die_frame(self, frame):
        raise NotImplementedError


class Topple(Interface):
    """ToppleUpdate, one a thing (step M2): knocked over (is_toppled), the frame it is gone in (gone_frame, None: it
    stays), taking a crusher's knock (knock: the frame, the knocker's speed a frame) and its kill (fall_where_it_stands:
    the frame)."""
    __slots__ = ()

    def is_toppled(self):
        raise NotImplementedError

    def gone_frame(self):
        raise NotImplementedError

    def knock(self, frame, speed):
        raise NotImplementedError

    def fall_where_it_stands(self, frame):
        raise NotImplementedError


class Crush(Interface):
    """CrusherInfo, one a thing (step M3): its CrusherLevel (crusher_level: 0 crushes nothing) and CrushableLevel
    (crushable_level: None, it cannot be crushed); crushed when a crusher's level is strictly greater."""
    __slots__ = ()

    def crusher_level(self):
        raise NotImplementedError

    def crushable_level(self):
        raise NotImplementedError


class Deposit(Interface):
    """AutoDepositUpdate, one a thing (step M4): its rules (rules: bonus, amount, frames), the frame of its next
    deposit (next_frame: None, not set) and its capture (capture: the frame it is taken in; -> the bonus its taker is
    paid, the clock set an interval on)."""
    __slots__ = ()

    def rules(self):
        raise NotImplementedError

    def next_frame(self):
        raise NotImplementedError

    def capture(self, frame):
        raise NotImplementedError


class Toggle(Interface):
    """ToggleStatusSpecialAbilityUpdate, any number a thing, in its blocks' order (step M5): its rules (rules: power,
    pack, unpack, states), the index of its ToggleState now (state: 0 until a press moves it), whether a press ever
    moved it (entered) and a press (press: the frame it is pressed in; -> False when its state now takes no press --
    a DisabledType -- or a press waits out its UnpackTime; else True: its next state entered now, or once the
    UnpackTime is out, and the host told through World.toggled)."""
    __slots__ = ()

    def rules(self):
        raise NotImplementedError

    def state(self):
        raise NotImplementedError

    def entered(self):
        raise NotImplementedError

    def press(self, frame):
        raise NotImplementedError


class Suppression(Interface):
    """SuppressionUpdate, one a thing (step M6): its rules (rules: threshold, every, duration, modifier), the fields
    covering it at its last update (hits: [(end frame, value)]), whether it is suppressed (is_suppressed), the end a
    refreshed sample set (until: 0, none yet) and its next sample frame (next_sample)."""
    __slots__ = ()

    def rules(self):
        raise NotImplementedError

    def hits(self):
        raise NotImplementedError

    def is_suppressed(self):
        raise NotImplementedError

    def until(self):
        raise NotImplementedError

    def next_sample(self):
        raise NotImplementedError


class Spawn(Interface):
    """SpawnBehavior, several a thing (step M7): its module id (module_id), the drone template it keeps alive (child:
    None, not that configuration), the collector it gives on unpacking (unpack_child: None, not that one), the things
    it made (children, dead ones too), the replacements queued (refills: [(due frame, module id, template)]); taking a
    thing it made (adopt) and the death of one (child_died: its template, the frame -- a replacement queued). Its own
    thing's end is its Destroy (the queue emptied, the things it made deleted)."""
    __slots__ = ()

    def module_id(self):
        raise NotImplementedError

    def child(self):
        raise NotImplementedError

    def unpack_child(self):
        raise NotImplementedError

    def children(self):
        raise NotImplementedError

    def refills(self):
        raise NotImplementedError

    def adopt(self, child):
        raise NotImplementedError

    def child_died(self, template, frame):
        raise NotImplementedError


class Slaved(Interface):
    """SlavedUpdate, one a thing (step M7): the thing that made it (slaver: None, none), the module id it was made by
    (slaver_module: '') and that Spawn module (spawner: None); being made by one (enslave: the parent, its module)."""
    __slots__ = ()

    def enslave(self, parent, spawner):
        raise NotImplementedError

    def slaver(self):
        raise NotImplementedError

    def slaver_module(self):
        raise NotImplementedError

    def spawner(self):
        raise NotImplementedError


class Attach(Interface):
    """AttachUpdate, several a thing (step M7): its module id (module_id) and the rule an AttachNugget naming it
    sticks by (rule: {flags, range, child, parent}; False, a shape not modelled)."""
    __slots__ = ()

    def module_id(self):
        raise NotImplementedError

    def rule(self):
        raise NotImplementedError


class Upgrade(Interface):
    """Whether it is in force (the XML's triggers, conflicts and required upgrades) and what it does then. Its data
    has `trigger` (module.Trigger); the kernel (Thing.upgrades_moved) keeps its `upgraded` and calls on_upgrade when
    the held upgrades come to satisfy the trigger, on_remove when they no longer do (step K3)."""
    __slots__ = ()

    def on_upgrade(self):
        raise NotImplementedError

    def on_remove(self):
        raise NotImplementedError


class Contain(Interface):
    """GarrisonContain / ContestableGarrisonContain / TransportContain (step M14): its rules (rules: the dict the
    host's garrison reads -- tag, max, allow, own, kill, status, clearing, rule, kinds, unkinds, exclude), the
    passengers in the order they came in (passengers), one in with the status bits it was given (let_in) and out (let_out
    -> those bits), the owner before the first passenger (home / keep_home / give_home), and the upgrades a single
    passenger granted through its listener (granted / set_granted). Who may come in, the walk, the ejects and the
    REALLYDAMAGED walk-out stay with the host (simgarrison.Garrisons)."""
    __slots__ = ()

    def rules(self):
        raise NotImplementedError

    def passengers(self):
        raise NotImplementedError

    def let_in(self, thing, bits):
        raise NotImplementedError

    def let_out(self, thing):
        raise NotImplementedError

    def home(self):
        raise NotImplementedError

    def keep_home(self, owner):
        raise NotImplementedError

    def give_home(self):
        raise NotImplementedError

    def granted(self):
        raise NotImplementedError

    def set_granted(self, upgrades):
        raise NotImplementedError


class Collide(Interface):
    __slots__ = ()

    def on_collide(self, other):
        raise NotImplementedError


class Production(Interface):
    __slots__ = ()

    def queue(self, what):
        raise NotImplementedError

    def cancel(self, what):
        raise NotImplementedError

    def progress(self):
        raise NotImplementedError


class OreMiner(Interface):
    """OreMinerBehavior, one a thing (step M9): a miner's trip (trip: the collector loop's dict, None before one and
    after a move dropped it) and setting it (set_trip; simmine.Mining keeps the loop)."""
    __slots__ = ()

    def trip(self):
        raise NotImplementedError

    def set_trip(self, trip):
        raise NotImplementedError

    def head_for(self, node=None, refinery=None):
        """The trip's node or refinery picked, kept as the thing (`node` / `refinery`) and named in the trip."""
        raise NotImplementedError


class Unpack(Interface):
    """StructureUnpackUpdate, one a thing (step M10): its UnpackTime in frames (frames: 0, none), the frame its
    unpacking ends (end_frame: None, it never unpacked) and setting that end (set_end: the host works it out from the
    owner's power factor when the structure is made in the run)."""
    __slots__ = ()

    def frames(self):
        raise NotImplementedError

    def end_frame(self):
        raise NotImplementedError

    def set_end(self, frame):
        raise NotImplementedError


class Sell(Interface):
    """StructureSellUpdate, one a thing (step M10): the frame its sale deletes it (gone_frame: None, not sold) and a
    sale (start_sale: the frame it is sold in; -> the frame it goes)."""
    __slots__ = ()

    def gone_frame(self):
        raise NotImplementedError

    def start_sale(self, frame):
        raise NotImplementedError


class SpecialPower(Interface):
    """A SpecialPowerModule, several a thing (step M8; the engine's isModuleForPower / getReadyFrame / setReadyFrame):
    the SpecialPowerTemplate it serves (power), the frame its reload ends (ready_at: None, no cast started one) and a
    cast starting it anew (set_ready_at: that frame). The cast itself (cast) comes with the step that models it."""
    __slots__ = ()

    def power(self):
        raise NotImplementedError

    def ready_at(self):
        raise NotImplementedError

    def set_ready_at(self, frame):
        raise NotImplementedError

    def cast(self, target):
        raise NotImplementedError


class Freeze(Interface):
    """SecondaryDamageTracker, one a thing (step M11): its rules (rules: every, melt, cap, steps), the cold it holds
    (held), the highest step reached (stage: -1, none), a hit's cold (add: the amount) and a tick's melting (melt: the
    seconds; -> whether the step moved). The host's chill keeps the tick."""
    __slots__ = ()

    def rules(self):
        raise NotImplementedError

    def held(self):
        raise NotImplementedError

    def stage(self):
        raise NotImplementedError

    def add(self, amount):
        raise NotImplementedError

    def melt(self, dt):
        raise NotImplementedError


class LevelUp(Interface):
    """LevelUpUpgrade, several a thing, in its blocks' order (step M12): its module id (module_id), its rules (rules:
    the TriggeredBy names, LevelsToGain, LevelCap, Permanent), whether a grant has it in force (active) and setting
    that (set_active: a grant puts it in force, a removal of its trigger rearms it). The rank it gives is the thing's
    (Body.level_rank); simlevel.receive keeps the grant."""
    __slots__ = ()

    def module_id(self):
        raise NotImplementedError

    def rules(self):
        raise NotImplementedError

    def active(self):
        raise NotImplementedError

    def set_active(self, on):
        raise NotImplementedError


class Aura(Interface):
    """AttributeModifierAuraUpdate, several a thing, in its blocks' order (step M12): its rule (rules: mod, range,
    refresh, relation, include, exclude, active, needs, self), the frame of its last refresh (last_beat: None, none)
    and asking whether a refresh is due (pulse: the frame; -> True and its beat moved). The host's aura tick hangs the
    modifier."""
    __slots__ = ()

    def rules(self):
        raise NotImplementedError

    def last_beat(self):
        raise NotImplementedError

    def pulse(self, frame):
        raise NotImplementedError


class Repair(Interface):
    """RepairUpdate (step M13): its rules (rules: rate, toggleable, dead, cost), whether its block is the measured
    shape (measured: no field outside rules' read), the repair under way (job: the host's dict, None none), setting it
    (set_job), and whether a disturbed repair refused it for the run (refused / refuse). The host's Repairs keeps the
    loop: who may repair, the money, the healing."""
    __slots__ = ()

    def rules(self):
        raise NotImplementedError

    def measured(self):
        raise NotImplementedError

    def job(self):
        raise NotImplementedError

    def set_job(self, job):
        raise NotImplementedError

    def refused(self):
        raise NotImplementedError

    def refuse(self):
        raise NotImplementedError


class Assign(Interface):
    """AssignSlavesTargetObjectSpecialPower (step M13), a SpecialPower too: whether its block is the plain measured
    shape (plain: no attribute but SpecialPowerTemplate, no inner text), the target it sends its drones to heal
    (target: None, none), and a dispatch (assign: the target, the heal a second, the frame; held till the target is
    whole, or anything moves)."""
    __slots__ = ()

    def plain(self):
        raise NotImplementedError

    def target(self):
        raise NotImplementedError

    def assign(self, target, rate, frame):
        raise NotImplementedError


class Infiltrate(Interface):
    """InfiltratorContain (step M15): its rules (rules: the block's attributes as written), whether a spy has entered
    it for a measured slice (entered / mark: 'kill', 'money', 'vehicle' ...), and a blocking port's turn-away frame
    (blocked_until / block). Who may enter, the walk and the effect stay with the host (siminfiltrator.Infiltrators)."""
    __slots__ = ()

    def rules(self):
        raise NotImplementedError

    def entered(self, slice_):
        raise NotImplementedError

    def mark(self, slice_):
        raise NotImplementedError

    def blocked_until(self):
        raise NotImplementedError

    def block(self, frame):
        raise NotImplementedError


class WeaponSet(Interface):
    """WeaponSetUpdate (step W2): the weapons a thing holds now (held: [{range, dps, type, anti ...}], the template
    data's own or the modifier pass's scaled copies), its weapon slots when the lines name a status or an upgrade
    (choices: simunits.weapon_sets, None: the weapons are fixed), arming it when it is made (arm) and the host's
    modifier pass writing the held ones back (hold: the slots' pick for the status, ranges scaled). Who fires, when
    and at what stays with the host."""
    __slots__ = ()

    def held(self):
        raise NotImplementedError

    def choices(self):
        raise NotImplementedError

    def arm(self, weapons, slots):
        raise NotImplementedError

    def hold(self, weapons):
        raise NotImplementedError


class AIUpdate(Interface):
    """The command state machine (move, attack, guard, follow ...) and the movement's physics."""
    __slots__ = ()

    def command(self, order):
        raise NotImplementedError


CORE = (Update, Body, Damage, Die, Destroy, Create, Upgrade, Contain, Collide, Production, SpecialPower, AIUpdate)
FAMILY = (Lifetime, Topple, Crush, Deposit, Toggle, Suppression, Spawn, Slaved, Attach, OreMiner, Unpack, Sell, Freeze,
          LevelUp, Aura, Repair, Assign, Infiltrate, SlowDeath, CreateOnDeath,
          DeathWeapon, WeaponSet)    # a family's own, added with its step (docs/engine/sim-modules.md 2)
ONE = frozenset({Body, AIUpdate, Lifetime, Topple, Crush, Deposit, Suppression, Slaved, OreMiner, Unpack, Sell, Freeze,
                 WeaponSet})  # a thing has at most one of these: Thing.find gives it
