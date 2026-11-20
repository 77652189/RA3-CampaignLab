"""WeaponSetUpdate's data (step W1, ADR 0029, docs/engine/sim-modules.md): the
<Weapon> lines of each WeaponSlot* of a block, read from the template data port. Step W1 moves the readers of
simunits (read_fight's weapon per slot, weapon_sets, declared_weapons, template_weapons) and simcoverage.declared_picks
onto it, their answers unchanged; step W2 adds the module that holds a thing's weapons and slots. A WeaponTemplate is a
named resource of its own, not a module: simunits.weapon_table resolves the names these lines give.

The choices the readers make, here on the data (no weapon resolved -- that is the reader's, it knows the table):
- pick: per slot the PRIMARY_WEAPON line, else the slot's first (read_fight's and declared_weapons' choice);
- conditioned: some line names a status or an upgrade (weapon_sets reads nothing for a block set without one);
- counted: per slot, slots by kind (Hardpoint, Turret, HierarchicalTurret, Contained), the first line by Ordering
  (XML order among equals) with no Upgrade and no ObjectStatus, or with ConquerMetricsAlwaysCount (template_weapons:
  the skirmish AI's template rate)."""
import re

from engine.kernel import factory, interfaces, module
from engine.ports import templates

UPGRADE_BIT = 'UPGRADE:'            # a <Weapon Upgrade="X"> line's need is the bit UPGRADE_BIT + x (lower case)
ORDERING = ('PRIMARY_WEAPON', 'SECONDARY_WEAPON', 'TERTIARY_WEAPON', 'QUATERNARY_WEAPON', 'QUINARY_WEAPON',
            'NO_WEAPON')            # the SDK's WeaponSlotType enumeration, the order the asset sorts a slot's lines by
COUNTED_KINDS = ('WeaponSlotHardpoint', 'WeaponSlotTurret', 'WeaponSlotHierarchicalTurret', 'WeaponSlotContained')
_SLOT = re.compile(r'<(WeaponSlot\w*)\b.*?</WeaponSlot\w*>', re.S)


class WeaponLine(module.ModuleData):
    """One <Weapon> line of a slot."""

    def __init__(self, ordering=None, template=None, status=frozenset(), forbidden=frozenset(), upgrades=(),
                 always=False, raw_status='', raw_upgrade=''):
        self.ordering = ordering        # Ordering (PRIMARY_WEAPON ...), None when not written
        self.template = template        # Template: the WeaponTemplate's name, None when not written
        self.status = status            # ObjectStatus: every bit
        self.forbidden = forbidden      # ForbiddenObjectStatus: none of them
        self.upgrades = upgrades        # Upgrade: the names written, in order
        self.always = always            # ConquerMetricsAlwaysCount="true"
        self.raw_status = raw_status    # ObjectStatus as written ('' when not), template_weapons' test
        self.raw_upgrade = raw_upgrade  # Upgrade as written

    @classmethod
    def parse(cls, head, inner=''):
        status, upgrade = templates.attr(head, 'ObjectStatus') or '', templates.attr(head, 'Upgrade') or ''
        return cls(templates.attr(head, 'Ordering'), templates.attr(head, 'Template'), frozenset(status.split()),
                   templates.words(head, 'ForbiddenObjectStatus'), tuple(upgrade.split()),
                   templates.attr(head, 'ConquerMetricsAlwaysCount') == 'true', status, upgrade).seal()

    @property
    def primary(self):
        return self.ordering == 'PRIMARY_WEAPON'

    @property
    def need(self):
        """The bits the line is held under: its ObjectStatus and an upgrade bit a name of its Upgrade."""
        return self.status | {UPGRADE_BIT + u.lower() for u in self.upgrades}

    @property
    def counts(self):
        """The skirmish AI's template rate may count it: ConquerMetricsAlwaysCount, or no Upgrade and no
        ObjectStatus."""
        return self.always or not self.raw_upgrade.strip() and not self.raw_status.strip()


class WeaponSlot(module.ModuleData):
    """One WeaponSlot* element: its kind (the tag) and its lines in XML order."""

    def __init__(self, kind='', lines=()):
        self.kind = kind
        self.lines = lines

    @classmethod
    def parse(cls, head, inner=''):
        """head: the slot's tag; inner: the slot element's text."""
        return cls(head, tuple(WeaponLine.parse(h, i) for h, i in templates.blocks(inner, 'Weapon'))).seal()

    def pick(self):
        """The PRIMARY_WEAPON line's template, else the first line's (None for a slot with no line)."""
        line = next((x for x in self.lines if x.primary), self.lines[0] if self.lines else None)
        return line.template if line else None

    def counted(self):
        """The first line by Ordering (XML order among equals) the AI's template rate counts, None if none."""
        rank = {o: i for i, o in enumerate(ORDERING)}
        return next((x for x in sorted(self.lines, key=lambda x: rank.get(x.ordering, 0)) if x.counts), None)


class WeaponSetUpdateData(module.ModuleData):
    def __init__(self, slots=()):
        self.slots = slots              # WeaponSlot per WeaponSlot* element, in XML order

    @classmethod
    def parse(cls, head, inner):
        return cls(tuple(WeaponSlot.parse(m.group(1), m.group(0)) for m in _SLOT.finditer(inner or ''))).seal()

    def picks(self):
        """The template each slot holds by read_fight's rule (WeaponSlot.pick), the slots with none left out."""
        return [p for p in (s.pick() for s in self.slots) if p]

    def conditioned(self):
        """Some line names a status (needed or forbidden) or an upgrade."""
        return any(x.need or x.forbidden for s in self.slots for x in s.lines)

    def counted(self):
        """The line each slot gives the AI's template rate, slots by kind (COUNTED_KINDS), XML order within one."""
        return [x for k in COUNTED_KINDS for s in self.slots if s.kind == k for x in (s.counted(),) if x]


@factory.module('WeaponSetUpdate')
class WeaponSet(module.Module, interfaces.WeaponSet):
    """The weapons a thing holds and its slots (step W2; the fields `weapons` / `slots` the thing had, by the same
    names in the frame record). The host arms it when it makes the thing (Sim.add, simbody.fill: the template's
    weapons, simunits.fight, and slots, simunits.weapon_sets) and its modifier pass holds what the status picks
    (simmodifier). A thing whose template has no block and that is armed gets one attached (equip). No update of its
    own.
    Step W3: each weapon's firing state, before the host's dicts by (serial, weapon key) (Sim.clocks / pre_locks /
    fire_gate) -- the private model's Weapon keeps its reload and pre-attack clocks per weapon too. The host's fight
    still decides when (Sim.shots_due, Sim.first_shot, simdamage.deal); this keeps what it decided. Not in the frame
    record (the host's dicts never were: RECORDED leaves them out)."""
    DATA = WeaponSetUpdateData
    STATE = ('weapons', 'slots', 'clocks', 'pre_locks', 'fire_gate')
    RECORDED = ('weapons', 'slots')
    weapons = []        # the held weapons (never changed in place: a new list each write)
    slots = None        # simunits.weapon_sets' slots, None: the weapons are fixed
    clocks = None       # weapon key (a keyless one: its slot) -> [this cycle's start, the last window with a target]
    #                     (Sim.shots_due; made on the first)
    pre_locks = None    # weapon key -> (target, second): a PER_TARGET weapon's last target and when its first shot at
    #                     it is due (Sim.first_shot)
    fire_gate = None    # target serial -> no fire dealt at it before this second (simdamage.deal). INFERRED: one gate
    #                     per shooter and target, its other weapons on that target wait with it (first_shot)

    def held(self):
        return self.weapons

    def choices(self):
        return self.slots

    def arm(self, weapons, slots):
        self.weapons, self.slots = weapons, slots

    def hold(self, weapons):
        self.weapons = weapons

    def clip_clock(self, key):
        return (self.clocks or {}).get(key)

    def set_clip_clock(self, key, clock):
        if self.clocks is None:
            self.clocks = {}
        self.clocks[key] = clock

    def pre_lock(self, key):
        return (self.pre_locks or {}).get(key)

    def lock_on(self, key, target, ready):
        if self.pre_locks is None:
            self.pre_locks, self.fire_gate = {}, {}
        self.pre_locks[key] = (target, ready)
        self.fire_gate[target.serial] = ready

    def gate_until(self, target):
        return (self.fire_gate or {}).get(target.serial, 0.0)


def equip(world, thing, weapons, slots, frame=None):
    """Arm `thing` (WeaponSet.arm): its module, one attached (World.attach) when its template has no block and it
    has weapons or slots to hold. -> the module, None for a thing with neither and no block."""
    m = thing.find(interfaces.WeaponSet)
    if m is None:
        if not weapons and slots is None:
            return None
        m = world.attach(thing, 'WeaponSetUpdate', frame)
    m.arm(weapons, slots)
    return m


def of(world, thing, frame=None):
    """`thing`'s WeaponSet, one attached (World.attach) to a thing that has none -- a weapon made by hand in a test
    fires too (its held weapons stay the default [], as the thing's were)."""
    return thing.find(interfaces.WeaponSet) or world.attach(thing, 'WeaponSetUpdate', frame)


def gate(shooter, target):
    """The second before which `shooter` deals no fire at `target` (first_shot's PER_TARGET wait), 0.0: none."""
    m = shooter.find(interfaces.WeaponSet)
    return m.gate_until(target) if m is not None else 0.0


def read(blocks):
    """The data of each WeaponSetUpdate block the template data port gives ([(attributes text, inner XML)])."""
    return [WeaponSetUpdateData.parse(*b) for b in blocks]


def armed(weapon):
    """A resolved weapon (simunits._resolve's dict) that can hurt (damage, a second damage, a DOT or a lift) and
    reach (range > 0): a gun; the target painter is not one."""
    return bool(weapon and (weapon['dps'] > 0 or weapon.get('sdps', 0) > 0 or weapon.get('dot') or weapon.get('lift'))
                and weapon['range'] > 0)
