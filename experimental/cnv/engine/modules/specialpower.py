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
RECALL = 'RecallUnitsSpecialPower'                  # its own class below (RecallUnits: whom a cast calls home)
RETURN = 'ReturnToProducerSpecialPower'             # its own class below (ReturnToProducer: a plane flies home)


class SpecialPowerData(module.ModuleData):
    def __init__(self, power=None):
        self.power = power          # SpecialPowerTemplate: the power it serves

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'))


@factory.module(*(t for t in TAGS if t not in (ASSIGN, RECALL, RETURN)))
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
        self.world.wake(self)

    def _stop(self):
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
