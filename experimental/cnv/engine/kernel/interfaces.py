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
FAMILY = (Lifetime,)                    # a family's own, added with its step (docs/engine/sim-modules.md 2)
ONE = frozenset({Body, AIUpdate, Lifetime})     # a thing has at most one of these: Thing.find gives it, not a tuple
