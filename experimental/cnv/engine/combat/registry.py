"""The nugget handlers' register (step N1): @nugget(kind, phase) on a handler class registers one instance of it.

A handler has `payload(weapon)` -- its part of the resolved weapon dict (simunits._resolve; None: the weapon has none)
-- and `apply(context, payload)`; a 'launch' handler returns True when it took the hit over (the host then skips the
rest of that volley). `effects(weapon)` is the weapon's [(kind, payload)] in ORDER; `run(phase, context)` applies the
context's effects of one phase in that order. ORDER is the one place the order is written: a kind registers only
under its (kind, phase) pair there, and each kind once."""
import types

# (kind, phase) in the order the host runs them: a launch takes the hit over or not (ProjectileNugget); a direct hit's
# effects on the aimed target, once a volley: the DOT booked, the passengers hit, the cold, the suppression fields,
# the EMP (step N2b: DOT / DamageContained / SecondaryDamage / Suppression / ParalyzeNugget), the shooter's sweeping
# line (N3d: ActivateLinearDamageNugget); an aim picks the victims
# (LineDamageNugget); a victim effect runs once for each victim: its damage, then the leech claims on it, then the
# strip (step N2a: Leech*DamageNugget, StripMaxHealthPercentDamageNugget); an effect runs once a volley, after the
# victims' damage is added and before the frame's damage is dealt, on the aimed target only (step N3a: the lift, the
# attachment; N3b: the caster's power on itself; N3c: the weapon's modifier on the target)
ORDER = (('Projectile', 'launch'), ('DOT', 'hit'), ('DamageContained', 'hit'), ('SecondaryDamage', 'hit'),
         ('Suppression', 'hit'), ('Paralyze', 'hit'), ('Sweep', 'hit'), ('LineDamage', 'aim'), ('Damage', 'victim'),
         ('LeechPercentMaxHealth', 'victim'), ('LeechHealth', 'victim'), ('StripMaxHealthPercent', 'victim'),
         ('Lift', 'effect'), ('Attach', 'effect'), ('Grapple', 'effect'), ('SpecialPower', 'effect'),
         ('AttributeModifier', 'effect'))

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


def standing(world, owner, t):
    """How t stands to `owner` as RadiusDamageAffects / an ObjectFilter's Relationship spell it: ALLIES, ENEMIES,
    NEUTRALS (combat's one entry to the host's relation)."""
    rel = world.relation(owner, t.owner)
    return rel + 'S' if rel == 'NEUTRAL' else rel


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
    hit), `armor(victim, type)` (armor x taken, no flank: a passenger's, a DOT tick's), `speed(projectile)`
    (straight-line muzzle speed, 0: none), `frames(seconds)` (the host's frame count of a time), `gap(tag, why)`,
    `queue_hit` / `detonate` (the host's arrival queue and MetaImpact dispatch, swappable), `clear_notice` (the
    target's incoming-fire notification), `can_hit`, `held(house)` (its passengers, the garrison's order) and
    `cold_of(body)` (its freeze threshold first, None: never cold). The host's books a hit writes: `dots` (the DOT
    entries), `mark_cold(body, shooter)` (whose cold it is, for the frame's chill), `suppression_fields` and
    `emp_until()` (serial -> frame, the host makes it on first use). `victims` starts as [target] (an aim may change it); `victim` is the
    one a victim effect runs for. `claims`: the frame's leech claims (victim serial -> list; engine/combat/leech),
    the host's ledger, paid once the frame's damage is dealt. `host`: the host's narrow calls for the 'effect' phase
    (simdamage.EffectHost: lift_rule / lift_hit / LIFT_LANDING, attachments / attach, refresh_modifiers, upgrade_gate / self_power /
    disguise / modifier / wear, fits)."""
    __slots__ = ('world', 'by', 'target', 'weapon', 'n', 'hurt', 'scalar', 'armor', 'speed', 'frames', 'gap',
                 'queue_hit', 'detonate', 'clear_notice', 'can_hit', 'held', 'cold_of', 'dots', 'mark_cold',
                 'suppression_fields', 'emp_until', 'effects', 'victims', 'victim', 'claims', 'host', 'boost')

    def __init__(self, world, by, target, weapon, n, hurt, *, scalar, armor, speed, frames, gap, queue_hit,
                 detonate, clear_notice, can_hit, held, cold_of, dots, mark_cold, suppression_fields, emp_until,
                 claims=None, host=None, boost=1.0):
        self.world, self.by, self.target, self.weapon, self.n, self.hurt = world, by, target, weapon, n, hurt
        self.boost = boost      # the volley's damage factor (a charged shot's, weaponset.boost), the Damage nugget's
        self.claims = {} if claims is None else claims
        self.host = host
        self.scalar, self.armor, self.speed, self.frames, self.gap = scalar, armor, speed, frames, gap
        self.queue_hit, self.detonate, self.clear_notice, self.can_hit = queue_hit, detonate, clear_notice, can_hit
        self.held, self.cold_of = held, cold_of
        self.dots, self.mark_cold = dots, mark_cold
        self.suppression_fields, self.emp_until = suppression_fields, emp_until
        self.effects = effects(weapon)
        self.victims = [target]
        self.victim = None

    def add(self, victim, amount):
        """This frame's damage of `victim` grows by `amount` (accumulate, the shooter for a new entry)."""
        return accumulate(self.hurt, victim, amount, self.by)

    def hit(self, victim, damage_type):
        """What one point of `damage_type` from the shooter does to `victim` (the host's scalar)."""
        return self.scalar(victim, damage_type, self.by)
