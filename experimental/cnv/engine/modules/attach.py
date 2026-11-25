"""AttachUpdate (bench engine_attach a; moved from simunits.attach_modules in step M7, ADR 0029,
docs/engine/sim-modules.md 4): what an AttachNugget of its thing's weapon may stick it to -- the direct teleport /
stick / status subset only.

A block is supported when it has no inner XML, its Flags hold STICK_TO_PARENT and TELEPORT and nothing beyond those
and ONE_ATTACH_PER_PARENT, and its attributes are no more than id, Flags, Range, CloseEnoughRange, ParentStatus and
AttachedObjectStatus; anything else is False (unsupported), so recognising a module id cannot silently implement
leech, death, repair, idle-detach or autonomous scanning. Several inherited groups and the distance boundary are
unbenched. Who attaches by a nugget stays outside (the combat family's AttachNugget: simdamage, reading the rules
through the body's attachment_rules forward; the attachments themselves: Sim.attachments).

One more shape, the retail repair drone's (BaseRepairDrone, REPAIR: the whole block compared), is an update of its own
(E66 / E181, checks/engine_assignslaves.py): a drone holding none takes the nearest hurt vehicle / aircraft of its
owner within Range of its slaver that no other drone or AssignSlaves dispatch mends (BOOBY_TRAPPED ones first), marks
it TARGETED_FOR_REPAIR, after InitialAttachDelay plus the straight flight at SPEED attaches (the
parent UNDERGOING_REPAIR, the drone ATTACHED, riding it), mends it its PassiveAreaEffectBehavior's
HealingPointsPerSecond once a SurveyDelayFrames (20: 26.7 HP a pulse, E235 d) and lets go -- both statuses cleared -- once it is whole, dead, another owner's or out of Range
of the slaver. An AssignSlaves press sends an idle one the same way (send). The flight (no acceleration), a scan every frame, nearest as the best parent and the owner alone for
ALLIES are INFERRED."""
import math
import re
import xml.etree.ElementTree as ET

from engine.kernel import factory, interfaces, module
from engine.ports import templates

FLAGS = frozenset({'STICK_TO_PARENT', 'TELEPORT'})
MORE_FLAGS = frozenset({'ONE_ATTACH_PER_PARENT'})
ATTRS = frozenset({'id', 'Flags', 'Range', 'CloseEnoughRange', 'ParentStatus', 'AttachedObjectStatus'})
REPAIR = dict(CloseEnoughRange='20.0', InitialAttachDelay='0.25s', ParentStatusToPrefer='BOOBY_TRAPPED',
              ParentStatus='TARGETED_FOR_REPAIR', ParentStatusAttached='UNDERGOING_REPAIR',
              ForbiddenParentStatus='NOT_IN_WORLD', Flags=frozenset(
                  'STICK_TO_PARENT DETACH_WHEN_PARENT_OUT_OF_SLAVE_RANGE PARENT_MUST_BE_FULL_HEALTH_TO_DETACH '
                  'SCAN_FOR_NEW_PARENT_WHEN_DETACHED FIND_BEST_PARENT UNCONTAINED_ONLY ONE_ATTACH_PER_PARENT '
                  'USE_GEOMETRY DETACH_WHEN_PARENT_HEALED'.split()))
REPAIR_KIDS = [('ObjectFilter', dict(Rule='ANY', Include='VEHICLE AIRCRAFT HUGE_VEHICLE',
                                     StatusBitFlagsExclude='NOT_IN_WORLD', Relationship='ALLIES'), 0)]
# the retail Terror Drone's block (SovietScoutVehicle; engine_attachterror a): attaches like the simple shape and its
# child dies with a parent killed by another (a script's NAMED_KILL). Bounce, unmanned detach, the forbidden-status death
# and the parent's own INTERNAL_DESTRUCTION are not modelled (the rule's flags keep them; INFERRED / gap)
TERROR = dict(ParentStatus='VEHICLE_ATTACHED BOOBY_TRAPPED', CloseEnoughRange='5', Range='10',
              AttachedObjectStatus='IGNORE_AI_COMMAND ENCLOSED NON_AUTOACQUIRABLE UNATTACKABLE',
              AttachedModelConditions='HIDDEN', Flags=frozenset(
                  'ONE_ATTACH_PER_PARENT STICK_TO_PARENT ADD_BOUNCE_TO_PARENT DIE_WHEN_PARENT_HAS_FORBIDDEN_STATUS '
                  'DIE_WHEN_PARENT_DIES_FROM_NOT_ME TELEPORT DETACH_WHEN_PARENT_UNMANNED'.split()),
              ParentDeathTypeToListenFor='INTERNAL_DESTRUCTION', ParentOwnerAttachmentEvaEvent='UnitInfected',
              ForbiddenParentStatus='UNDERGOING_REPAIR', IgnoreForbiddenParentStatusStatus='UNDER_IRON_CURTAIN',
              BounceTimeout='0.5s')
TERROR_KIDS = [('ObjectFilter', dict(Rule='ANY', Include='VEHICLE', Relationship='ENEMIES ALLIES NEUTRAL'), 0)]
PARENT_KINDS = frozenset({'VEHICLE', 'AIRCRAFT', 'HUGE_VEHICLE'})
FPS = 15
SPEED = 150.0       # BaseRepairDrone's LocomotorSet Speed: REPAIR's only retail user (another drone's: INFERRED)
SURVEY = 20         # PassiveAreaEffectBehavior's SurveyDelayFrames default (the schema): it heals once a survey
PHASE = 2           # E235 d: both arms' first pulse at script frame 142 (attached f136 / f138): INFERRED world clock


def _native(head, inner, want, kids, keep=()):
    """The block's attributes (Flags a set, `keep` popped first) if it is `want` with the children `kids`; else None."""
    try:
        node = ET.fromstring('<AttachUpdate ' + head + '>' + inner + '</AttachUpdate>')
    except ET.ParseError:
        return None
    attrs = dict(node.attrib)
    attrs.pop('id', None)
    kept = {k: attrs.pop(k, None) for k in keep}
    attrs['Flags'] = frozenset(attrs.get('Flags', '').split())
    if attrs != want or [(c.tag, dict(c.attrib), len(c)) for c in node] != kids:
        return None
    return {**attrs, **kept}


def _repair(head, inner):
    """The retail repair drone's block: {range, delay (frames)}; None for any other."""
    attrs = _native(head, inner, REPAIR, REPAIR_KIDS, keep=('Range',))
    if attrs is None:
        return None
    return dict(range=templates.num(attrs['Range']),
                delay=math.ceil(templates.secs(REPAIR['InitialAttachDelay']) * FPS - 1e-6))


class AttachData(module.ModuleData):
    def __init__(self, id=None, rule=False, repair=None):
        self.id = id                    # its module id (what an AttachNugget names)
        self.rule = rule                # {flags, range, child, parent}, or False: a shape not modelled
        self.repair = repair            # REPAIR's {range, delay}; None: not the drone's block

    @classmethod
    def parse(cls, head, inner):
        repair = _repair(head, inner)
        if repair:
            return cls(templates.attr(head, 'id'), False, repair)
        if _native(head, inner, TERROR, TERROR_KIDS):
            return cls(templates.attr(head, 'id'), dict(
                # range None: no gate at the hit -- the bench's drone dispatches at its weapon's 25 past the parent's
                # edge (49 centre to centre) and attaches; whether Range 10 gates a closer hit is unread (INFERRED)
                flags=set(TERROR['Flags']), range=None, die_with_parent=True,
                child=set(TERROR['AttachedObjectStatus'].split()) | {'ATTACHED'},
                parent=set(TERROR['ParentStatus'].split())))
        flags = set(templates.attr(head, 'Flags', 'STICK_TO_PARENT TELEPORT USE_GEOMETRY').split())
        if (inner.strip() or not FLAGS <= flags or flags - FLAGS - MORE_FLAGS
                or set(re.findall(r'(\w+)\s*=', head)) - ATTRS):
            return cls(templates.attr(head, 'id'), False)
        return cls(templates.attr(head, 'id'), dict(
            flags=flags, range=templates.num(templates.attr(head, 'Range')),
            # engine_attach_nocoll n: NO_COLLISIONS listed there is never given (alone or in either order)
            child=set(templates.attr(head, 'AttachedObjectStatus', '').split()) - {'NO_COLLISIONS'} | {'ATTACHED'},
            parent=set(templates.attr(head, 'ParentStatus', '').split())))


@factory.module('AttachUpdate')
class Attach(module.Module, interfaces.Attach, interfaces.Update):
    """Its module id and rule (the shape simunits.attach_modules gave: {flags, range, child, parent} or False). The
    repair drone's block runs in the assignments cell (held: the parent it flies to or mends; due: the frame it
    attaches; on: attached); any other sleeps."""
    DATA = AttachData
    PHASE = 'assignments'
    STATE = ('held', 'due', 'on')
    RECORDED = ()
    ALIGN = {'drone repair': '部分对齐：原版修理无人机自己找最近的受损己方车辆贴上去修（E66 / E181）；'
                             '飞行时间、每帧扫描、最近即最佳、ALLIES 只认同一玩家为 INFERRED'}
    held, due, on = None, 0, False

    def module_id(self):
        return self.data.id

    def rule(self):
        return self.data.rule

    def repairing(self):
        return self.held

    def _fits(self, p, home):
        return (p.alive and not p.deleted and p.owner == self.thing.owner and p.kinds & PARENT_KINDS
                and 'NOT_IN_WORLD' not in p.status
                and math.hypot(p.x - home.x, p.y - home.y) - p.radius <= self.data.repair['range'])

    def send(self, p):
        """Fly to and mend `p` (an AssignSlaves press: E235 c / d) as if its scan had found it; False: not an idle
        repair drone."""
        if not self.data.repair or self.held is not None or not self.thing.alive:
            return False
        self.held, self.on, self.due = p, False, None
        p.status.add('TARGETED_FOR_REPAIR')
        return True

    def _let_go(self):
        self.held.status.difference_update({'TARGETED_FOR_REPAIR', 'UNDERGOING_REPAIR'})
        self.thing.status.discard('ATTACHED')
        self.held, self.on = None, False

    def _choose(self, home):
        living = self.world.living()
        held = [m.repairing() for t in living for m in t.find(interfaces.Attach)]
        held += [m.target() for t in living for m in t.find(interfaces.Assign)]
        taken = {p.serial for p in held if p is not None}
        d = self.thing
        return min((p for p in living if p.hp < p.max_hp and p.serial not in taken and self._fits(p, home)),
                   key=lambda p: ('BOOBY_TRAPPED' not in p.status, math.hypot(p.x - d.x, p.y - d.y)), default=None)

    def _heal(self):
        """(HealingPointsPerSecond, SurveyDelayFrames) of its PassiveAreaEffectBehavior that AffectAttached."""
        return next(((templates.num(templates.attr(h, 'HealingPointsPerSecond'), 0.0),
                      int(templates.num(templates.attr(h, 'SurveyDelayFrames'), SURVEY)))
                     for h, _ in self.world.blocks_of(self.thing.template, 'PassiveAreaEffectBehavior')
                     if templates.attr(h, 'AffectAttached') == 'true'), (0.0, SURVEY))

    def update(self, frame):
        d, rule = self.thing, self.data.repair
        slaved = d.find(interfaces.Slaved)
        home = slaved.slaver() if slaved else None
        if not rule or not d.alive or home is None or not home.alive:
            if self.held is not None:
                self._let_go()
            return interfaces.SLEEP
        if self.held is not None and (not self._fits(self.held, home) or self.held.hp >= self.held.max_hp):
            self._let_go()
        p = self.held
        if p is None:
            p = self._choose(home)
            if p is None:
                return 1
            self.send(p)
        if self.due is None:
            self.due = frame + rule['delay'] + math.ceil(math.hypot(p.x - d.x, p.y - d.y) / SPEED * FPS)
        if not self.on:
            if frame < self.due:
                return 1
            self.on = True
            p.status.add('UNDERGOING_REPAIR')
            d.status.add('ATTACHED')
        d.x, d.y = p.x, p.y
        rate, survey = self._heal()
        if frame % survey == PHASE:
            p.mend(rate * survey / FPS)
            self.world.used.add('drone repair')
        if p.hp >= p.max_hp:
            self._let_go()
        return 1
