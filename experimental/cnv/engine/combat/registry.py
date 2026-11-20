"""The nugget handlers' register (step N1): @nugget(kind, phase) on a handler class registers one instance of it.

A handler has `payload(weapon)` -- its part of the resolved weapon dict (simunits._resolve; None: the weapon has none)
-- and `apply(context, payload)`; a 'launch' handler returns True when it took the hit over (the host then skips the
rest of that volley). `effects(weapon)` is the weapon's [(kind, payload)] in ORDER; `run(phase, context)` applies the
context's effects of one phase in that order. ORDER is the one place the order is written: a kind registers only
under its (kind, phase) pair there, and each kind once."""
import types

# (kind, phase) in the order the host runs them: a launch takes the hit over or not (ProjectileNugget), an aim picks
# the victims (LineDamageNugget), a victim effect runs once for each victim (DamageNugget)
ORDER = (('Projectile', 'launch'), ('LineDamage', 'aim'), ('Damage', 'victim'))

_HANDLERS = {}
HANDLERS = types.MappingProxyType(_HANDLERS)


def nugget(kind, phase):
    """Class decorator: register one instance of a handler class for the nugget `kind`, run in `phase`."""
    def register(cls):
        if (kind, phase) not in ORDER:
            raise ValueError(f'{kind} / {phase} is not in registry.ORDER')
        if kind in _HANDLERS:
            raise ValueError(f'{kind} is registered twice ({type(_HANDLERS[kind]).__name__}, {cls.__name__})')
        cls.kind, cls.phase = kind, phase
        _HANDLERS[kind] = cls()
        return cls
    return register


def effects(weapon):
    """The weapon's effects [(kind, payload)], in ORDER (a kind with no handler registered is an error)."""
    out = []
    for kind, _ in ORDER:
        payload = _HANDLERS[kind].payload(weapon)
        if payload is not None:
            out.append((kind, payload))
    return out


def run(phase, context):
    """Apply the context's effects of `phase`, in ORDER; True as soon as one takes the hit over."""
    for kind, payload in context.effects:
        handler = _HANDLERS[kind]
        if handler.phase == phase and handler.apply(context, payload):
            return True
    return False


def accumulate(hurt, victim, amount, by):
    """Add `amount` to this frame's damage of `victim` (hurt: serial -> [body, damage, attacker], in first-hit order;
    a new entry's attacker is `by`, an old one keeps its own). The entry."""
    h = hurt.setdefault(victim.serial, [victim, 0.0, by])
    h[1] += amount
    return h


class Context:
    """One volley as its host sees it this frame: the world, the shooter `by`, the aimed `target`, the resolved
    `weapon`, the shots `n`, this frame's damage `hurt` (add) and the host's rules and calls a handler may make (the
    rules read the game data, which this package does not): `scalar(victim, type, attacker)` (armor x taken x flank,
    hit), `speed(projectile)` (straight-line muzzle speed, 0: none), `gap(tag, why)`, `queue_hit` / `detonate` (the
    host's arrival queue and MetaImpact dispatch, swappable), `clear_notice` (the target's incoming-fire
    notification) and `can_hit`. `victims` starts as [target] (an aim may change it); `victim` is the one a victim
    effect runs for."""
    __slots__ = ('world', 'by', 'target', 'weapon', 'n', 'hurt', 'scalar', 'speed', 'gap', 'queue_hit', 'detonate',
                 'clear_notice', 'can_hit', 'effects', 'victims', 'victim')

    def __init__(self, world, by, target, weapon, n, hurt, *, scalar, speed, gap, queue_hit, detonate, clear_notice,
                 can_hit):
        self.world, self.by, self.target, self.weapon, self.n, self.hurt = world, by, target, weapon, n, hurt
        self.scalar, self.speed, self.gap = scalar, speed, gap
        self.queue_hit, self.detonate, self.clear_notice, self.can_hit = queue_hit, detonate, clear_notice, can_hit
        self.effects = effects(weapon)
        self.victims = [target]
        self.victim = None

    def add(self, victim, amount):
        """This frame's damage of `victim` grows by `amount` (accumulate, the shooter for a new entry)."""
        return accumulate(self.hurt, victim, amount, self.by)

    def hit(self, victim, damage_type):
        """What one point of `damage_type` from the shooter does to `victim` (the host's scalar)."""
        return self.scalar(victim, damage_type, self.by)
