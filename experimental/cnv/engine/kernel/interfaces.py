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


class SpecialPower(Interface):
    __slots__ = ()

    def ready_at(self):
        raise NotImplementedError

    def cast(self, target):
        raise NotImplementedError


class AIUpdate(Interface):
    """The command state machine (move, attack, guard, follow ...) and the movement's physics."""
    __slots__ = ()

    def command(self, order):
        raise NotImplementedError


CORE = (Update, Body, Damage, Die, Destroy, Create, Upgrade, Contain, Collide, Production, SpecialPower, AIUpdate)
FAMILY = (Lifetime, Topple, Crush, Deposit, Toggle, Suppression)    # a family's own, added with its step (docs/engine/sim-modules.md 2)
ONE = frozenset({Body, AIUpdate, Lifetime, Topple, Crush, Deposit, Suppression})  # a thing has at most one of these: Thing.find gives it
