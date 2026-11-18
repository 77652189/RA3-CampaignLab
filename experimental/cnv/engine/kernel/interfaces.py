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

    def attempt_damage(self, info):
        raise NotImplementedError

    def attempt_healing(self, info):
        raise NotImplementedError

    def health(self):
        raise NotImplementedError

    def max_health(self):
        raise NotImplementedError

    def damage_state(self):
        """'pristine' / 'damaged' / 'really_damaged'."""
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
    """Told when its thing dies; it decides itself (by the XML's death types, rank and status) whether it acts."""
    __slots__ = ()

    def on_die(self, info):
        raise NotImplementedError


class Destroy(Interface):
    """Told once, the moment its thing leaves the world."""
    __slots__ = ()

    def on_destroy(self):
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
    thing it made (adopt), the death of one (child_died: its template, the frame -- a replacement queued) and its own
    thing's death (parent_died: the queue emptied)."""
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

    def parent_died(self):
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
    __slots__ = ()

    def can_take(self, thing):
        raise NotImplementedError

    def take(self, thing):
        raise NotImplementedError

    def release(self, thing):
        raise NotImplementedError

    def members(self):
        raise NotImplementedError

    def on_container_died(self):
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


class AIUpdate(Interface):
    """The command state machine (move, attack, guard, follow ...) and the movement's physics."""
    __slots__ = ()

    def command(self, order):
        raise NotImplementedError


CORE = (Update, Body, Damage, Die, Destroy, Create, Upgrade, Contain, Collide, Production, SpecialPower, AIUpdate)
FAMILY = (Lifetime, Topple, Crush, Deposit, Toggle, Suppression, Spawn, Slaved, Attach, OreMiner, Unpack, Sell, Freeze,
          LevelUp, Aura)    # a family's own, added with its step (docs/engine/sim-modules.md 2)
ONE = frozenset({Body, AIUpdate, Lifetime, Topple, Crush, Deposit, Suppression, Slaved, OreMiner, Unpack, Sell, Freeze})  # a thing has at most one of these: Thing.find gives it
