"""The SpecialPowerModule family's reload (step M8, ADR 0029, docs/engine/sim-modules.md 4; moved from the body's
`ready_at` dict): one module a block of any SpecialPowerModule tag, serving the SpecialPowerTemplate its block names.
It keeps the frame its power's reload ends; every cast -- the script's too -- starts it anew (RA3 1.13, read in the
program). How long a reload is (simunits.power_rules: the SpecialPowerTemplate's ReloadTime) and what
a cast does stay with the callers (simact_ability, simorder, simmicro) until the cast is a module's.

Its state is shown in the frame record by the body's forward `ready_at` ({power: frame} of the modules a cast
started; simpower.ready_at): several of these on one thing record as one field, so RECORDED names none of them.
A thing whose template has no block for a power cast on it (35 retail template / power pairs: ReplaceSelf's packs,
the player spell book's nearest-template blocks, the structures' PlayerPowerManager powers; and simmicro's Bonzai,
keyed by its command) is given one then (simpower.start_reload, World.attach), as the body's dict took any key."""
import math
import re

from engine.kernel import factory, interfaces, module
from engine.ports import templates

# The SpecialPowerModule tags of the retail XML (the Generals SpecialPowerModule family and RA3's own: the index's
# tags ending in SpecialPower)
TAGS = ('SpecialPower', 'OCLSpecialPower', 'MovementSpecialPower', 'DominateEnemySpecialPower',
        'RecallUnitsSpecialPower', 'StoreObjectsSpecialPower', 'TeleportStoredObjectsSpecialPower',
        'TeleportToCasterSpecialPower', 'PlayerUpgradeSpecialPower', 'ReturnToProducerSpecialPower',
        'ActivateModuleSpecialPower', 'AssignSlavesTargetObjectSpecialPower', 'GiveProductionBonusSpecialPower',
        'PrematureDischargeSpecialPower', 'ReturnToDockSpecialPower')
FPS = 15                        # the game's logic frames a second (bench 2026-10-28, probe align)
ASSIGN = 'AssignSlavesTargetObjectSpecialPower'     # its own class below (AssignSlaves: a SpecialPower with a dispatch)
REPAIR_BITS = frozenset({'TARGETED_FOR_REPAIR', 'UNDERGOING_REPAIR'})   # the repair drone's ParentStatus(Attached)
RECALL = 'RecallUnitsSpecialPower'                  # its own class below (RecallUnits: whom a cast calls home)
RETURN = 'ReturnToProducerSpecialPower'             # its own class below (ReturnToProducer: a plane flies home)
DOMINATE = 'DominateEnemySpecialPower'              # its own class below (DominateEnemy: whom a cast takes)
STORE = 'StoreObjectsSpecialPower'                  # its own class below (StoreObjects: who the teleport takes)


class SpecialPowerData(module.ModuleData):
    def __init__(self, power=None, at_start=True, link=None):
        self.power = power          # SpecialPowerTemplate: the power it serves
        self.at_start = at_start    # AvailableAtStart (XSD default true): ready before any reload was started
        self.link = link            # TeleportLinkID / StoreObjectsLinkID: the teleport's two steps paired

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'),
                   (templates.attr(head, 'AvailableAtStart') or 'true').lower() != 'false',
                   templates.attr(head, 'TeleportLinkID') or templates.attr(head, 'StoreObjectsLinkID'))


@factory.module(*(t for t in TAGS if t not in (ASSIGN, RECALL, RETURN, DOMINATE, STORE)))
class SpecialPower(module.Module, interfaces.SpecialPower):
    """Data and a reload frame; no update of its own (a reload is over once the frame passes it)."""
    DATA = SpecialPowerData
    STATE = ('ready',)
    RECORDED = ()
    ready = None        # the frame its reload ends; None: no cast started one

    def power(self):
        return self.data.power

    def ready_at(self):
        return self.ready

    def set_ready_at(self, frame):
        self.ready = frame


class MonitorData(SpecialPowerData):
    def __init__(self, power=None, condition=None):
        super().__init__(power)
        self.condition = condition      # ReadyCondition: the model condition it sets while its power is ready

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'), templates.attr(head, 'ReadyCondition'))


@factory.module('MonitorSpecialPowerTimerUpdate')
class Monitor(module.Module, interfaces.ReadyMonitor):
    """MonitorSpecialPowerTimerUpdate (E145, checks/engine_modulebatch.readings.toml): its thing has ReadyCondition
    while the reload of every SpecialPower module of its thing serving its power is over, and not otherwise (the
    proton collider's SPECIALPOWER1_READY after a countdown of 0, gone after 10000; none on the one without it). A
    module with AvailableAtStart="false" no reload has started is not ready (the bench's collider: 0 at s1-s6), nor
    is a power its thing has no module for (review yy #6). Asked when the condition is read (Sim.has_model_condition).
    Not modelled: disabled / unpacking hosts (INFERRED: the reload alone); the cast itself still ignores
    AvailableAtStart."""
    DATA = MonitorData

    def shows(self, condition, frame):
        d = self.data
        mods = [m for m in self.thing.find(interfaces.SpecialPower) if m.power() == d.power]
        return bool(d.condition) and condition == d.condition and bool(mods) and all(
            (m.ready_at() if m.ready_at() is not None else 0 if m.data.at_start else frame + 1) <= frame
            for m in mods)


class RecallData(SpecialPowerData):
    def __init__(self, power=None, most=4):
        super().__init__(power)
        self.most = most            # MaxAircraftToRecall (the XSD's default 4)

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'),
                   int(templates.num(templates.attr(head, 'MaxAircraftToRecall'), 4.0)))


@factory.module(RECALL)
class RecallUnits(SpecialPower, interfaces.Recall):
    """RecallUnitsSpecialPower (E184, checks/engine_recall_e.readings.toml): a cast calls home the living AIRCRAFT its
    holder made for its owner, MaxAircraftToRecall of them in the order made (the host sends them: act_ability). One
    produced Apollo benched: which ones past the cap, the way home, landing and parking slots INFERRED / not modelled."""
    DATA = RecallData

    def flights(self, things):
        me = self.thing
        return [(b, me) for b in things if b.alive and b.made_by == me.name and b.owner == me.owner
                and 'AIRCRAFT' in b.kinds][:self.data.most]


class DominateData(SpecialPowerData):
    def __init__(self, power=None, radius=0.0, keep=False, rels=(), kinds=()):
        super().__init__(power)
        self.radius = radius        # DominateRadius
        self.keep = keep            # PermanentlyConvert (false takes nothing: units/clone.py, bench 2026-10-22)
        self.rels = rels            # AttributeModifierAffects Relationship / Include
        self.kinds = kinds

    @classmethod
    def parse(cls, head, inner):
        a = re.search(r'<AttributeModifierAffects\b[^>]*', inner or '')
        f = lambda name: (templates.attr(a.group(0), name) or '').split() if a else []    # noqa: E731
        keep = (templates.attr(head, 'PermanentlyConvert') or '').lower() == 'true' and not f('StatusBitFlags')
        return cls(templates.attr(head, 'SpecialPowerTemplate'), templates.num(templates.attr(head, 'DominateRadius')),
                   keep, f('Relationship'), f('Include'))


@factory.module(DOMINATE)
class DominateEnemy(SpecialPower, interfaces.Dominate):
    """DominateEnemySpecialPower (E216, checks/engine_dominate_e.readings.toml): a cast takes for its holder's owner the
    living things of the Relationship and an Include kind within DominateRadius of it, the press's frame (the host
    hands them over: act_ability). The spy's bribe benched (40 / 50 taken, 90 and a structure not). INFERRED: the
    centre distance, Rule ANY; not modelled: the pack / BUSY / stealth options, the FX, a StatusBitFlags filter (our
    mind maiden's, units/clone.py: such a block takes nothing, as before)."""
    DATA = DominateData

    def taken(self, things, stands):
        me, d = self.thing, self.data
        return [t for t in things if t.alive and t is not me and stands(me.owner, t.owner, d.rels)
                and set(d.kinds) & t.kinds and math.hypot(t.x - me.x, t.y - me.y) <= d.radius] if d.keep else []


class StoreData(SpecialPowerData):
    def __init__(self, power=None, link=None, radius=0.0, filter_=None):
        super().__init__(power, link=link)
        self.radius, self.filter = radius, filter_      # Radius; CanAffectObjectFilter (its name)

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'), templates.attr(head, 'TeleportLinkID'),
                   templates.num(templates.attr(head, 'Radius')), templates.attr(head, 'CanAffectObjectFilter'))


# AlliedChronosphereSpecialPowerObjectFilter (Includes/SpecialPowerObjectFilters.xml), the one retail store filter:
# Include, Exclude kinds, StatusBitFlagsExclude (its IncludeThing time bombs not taken)
CHRONO = ('AlliedChronosphereSpecialPowerObjectFilter', frozenset({'INFANTRY', 'VEHICLE'}), frozenset({'AIRCRAFT'}),
          frozenset({'SUBMERGED', 'AIRBORNE_TARGET', 'NOT_IN_WORLD'}))


@factory.module(STORE)
class StoreObjects(SpecialPower, interfaces.Store):
    """StoreObjectsSpecialPower (E227, checks/engine_teleport.readings.toml): the Chronosphere's first step takes the
    things of its filter within Radius of the cast's point (the second step, TeleportStoredObjectsUpdate, carries them:
    engine/modules/teleport.py). A filter other than CHRONO takes no one (a gap; INFERRED as the private model's
    unfiltered store). Not modelled: the OCL's markers."""
    DATA = StoreData
    STATE = ('ready', 'stored_at', 'carried')
    stored_at = None    # the stored point; None: never stored, or cleared
    carried = ()        # the stored things

    def link(self):
        return self.data.link

    def store(self, point):
        me, d = self.thing, self.data
        self.stored_at, self.carried = point, ()
        if d.filter != CHRONO[0]:
            self.world.gap('StoreObjectsSpecialPower', d.filter or '', '只认原版时空传送的对象过滤器：没带走谁')
            return
        self.carried = tuple(t for t in self.world.living() if t is not me and t.alive and t.kinds & CHRONO[1]
                          and not t.kinds & CHRONO[2] and not module.status_now(t) & CHRONO[3]
                          and math.hypot(t.x - point[0], t.y - point[1]) <= d.radius)

    def stored(self):
        return [t for t in self.carried if t.alive]

    def clear(self):
        self.stored_at, self.carried = None, ()


class ReturnData(SpecialPowerData):
    def __init__(self, power=None, condition=None, seconds=0.0):
        super().__init__(power)
        self.condition, self.seconds = condition, seconds      # SetModelCondition, SetModelConditionTime

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'), templates.attr(head, 'SetModelCondition'),
                   templates.secs(templates.attr(head, 'SetModelConditionTime')))


@factory.module(RETURN)
class ReturnToProducer(SpecialPower, interfaces.Recall):
    """ReturnToProducerSpecialPower (E173, checks/engine_returnproducer_e.readings.toml): a cast flies its holder back to
    the living thing that made it and sets SetModelCondition for SetModelConditionTime (the Apollo: USER_1 30 s, seen at
    the cast). Its AttributeModifier (the speed home), landing and the parking slot are not modelled."""
    DATA = ReturnData

    def flights(self, things):
        me = self.thing
        return [(me, b) for b in things if b.alive and b.name == me.made_by][:1]

    def mark(self):
        return (self.data.condition, self.data.seconds) if self.data.condition else None


class AssignData(SpecialPowerData):
    def __init__(self, power=None, plain=False):
        super().__init__(power)
        self.plain = plain          # no attribute but SpecialPowerTemplate (and id), no inner text: the measured shape

    @classmethod
    def parse(cls, head, inner):
        names = set(re.findall(r'(\w+)\s*=', head))
        return cls(templates.attr(head, 'SpecialPowerTemplate'),
                   not inner.strip() and names == {'id', 'SpecialPowerTemplate'})


@factory.module(ASSIGN)
class AssignSlaves(SpecialPower, interfaces.Assign, interfaces.Update):
    """AssignSlavesTargetObjectSpecialPower (step M13; E67, moved from simassign.Assignments' store and due): a
    SpecialPower with a dispatch. The host (simassign.Assignments.press: which press, which target, the rate from the
    retail repair drone's PassiveAreaEffectBehavior) assigns; then in the assignments cell it mends the target rate / 15
    a frame until whole, and stops -- a gap noted -- once anything moves: either dies, the owners differ, no drone of
    its SpawnBehaviors lives, either moves, or the target's health is changed by anything else (a conservative stop,
    INFERRED). Asleep without a target. Its state was a store's, never in the frame record: RECORDED names none."""
    DATA = AssignData
    PHASE = 'assignments'
    STATE = ('ready', 'tgt', 'rate', 'last', 'spots')
    RECORDED = ()
    ALIGN = {'assigned repair': '部分对齐：显式单目标派无人机治疗（E67 原版 AlliedWarFactoryRepairDrone 的 '
                                'PassiveAreaEffectBehavior 每秒治疗量）；自动获取、前三目标占用、换父/换目标/状态清理未模拟，'
                                '启动相位与中断即停为 INFERRED'}
    tgt = None          # the thing it heals; None: none
    rate = 0.0          # its heal a second
    last = 0.0          # the target's health after its last mend (or at the dispatch)
    spots = None        # (its x, y, the target's x, y) at the dispatch

    def plain(self):
        return self.data.plain

    def target(self):
        return self.tgt

    def assign(self, target, rate):
        s = self.thing
        self.tgt, self.rate, self.last = target, rate, target.hp
        self.spots = (s.x, s.y, target.x, target.y)
        target.status.update(REPAIR_BITS)       # E66: the dispatched target reads 110 like a drone's (from the press: INFERRED)
        self.world.wake(self)

    def _stop(self):
        if self.tgt is not None:
            self.tgt.status.difference_update(REPAIR_BITS)
        self.tgt = self.spots = None
        return interfaces.SLEEP

    def update(self, frame):
        s, t = self.thing, self.tgt
        if t is None:
            return interfaces.SLEEP
        if (not s.alive or not t.alive or s.owner != t.owner
                or not any(c.alive for m in s.find(interfaces.Spawn) for c in m.children())
                or self.spots != (s.x, s.y, t.x, t.y)
                or abs(t.hp - self.last) > 1e-6):
            self.world.gap(ASSIGN, 'interrupted', '移动、死亡、换主或外部血量变化后的派发边界未测；保守停止为INFERRED')
            return self._stop()
        t.mend(self.rate / FPS)
        self.last = t.hp
        self.world.used.add('assigned repair')
        if t.hp >= t.max_hp:
            return self._stop()
        return 1
