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
SURVEY, PHASE = 20, 2       # the repair drone's pulse, attach.py's SURVEY / PHASE (module files import none other)
RECALL = 'RecallUnitsSpecialPower'                  # its own class below (RecallUnits: whom a cast calls home)
RETURN = 'ReturnToProducerSpecialPower'             # its own class below (ReturnToProducer: a plane flies home)
DOMINATE = 'DominateEnemySpecialPower'              # its own class below (DominateEnemy: whom a cast takes)
STORE = 'StoreObjectsSpecialPower'                  # its own class below (StoreObjects: who the teleport takes)
OCL = 'OCLSpecialPower'                             # its own class below (OCLRun: a bombing run's delay and drop)
PULL = 'TeleportToCasterSpecialPower'               # its own class below (PullToCaster: the beacon pull)
FALL = 6    # frames from the bomber over its target to the bomb's hit (A375 INFERRED: engine_oclmon_n 93 / 94 from GO)


class SpecialPowerData(module.ModuleData):
    def __init__(self, power=None, at_start=True, link=None):
        self.power = power          # SpecialPowerTemplate: the power it serves
        self.at_start = at_start    # AvailableAtStart (XSD default true): ready before any reload was started
        self.link = link            # TeleportLinkID / StoreObjectsLinkID: the teleport's two steps paired

    @classmethod
    def parse(cls, head, inner):
        """read's data, AvailableAtStart read here for every family (the Chronosphere's StoreObjects read true)."""
        return cls.read(head, inner).starts((templates.attr(head, 'AvailableAtStart') or 'true').lower() != 'false')

    def starts(self, at_start):
        self.at_start = at_start
        return self

    @classmethod
    def read(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'),
                   link=templates.attr(head, 'TeleportLinkID') or templates.attr(head, 'StoreObjectsLinkID'))


@factory.module(*(t for t in TAGS if t not in (ASSIGN, RECALL, RETURN, DOMINATE, STORE, OCL, PULL)))
class SpecialPower(module.Module, interfaces.SpecialPower, interfaces.Create):
    """Data and a reload frame; no update of its own (a reload is over once the frame passes it)."""
    DATA = SpecialPowerData
    STATE = ('ready', 'first', 'made')
    RECORDED = ()
    ready = None        # the frame its reload ends; None: no cast started one
    first = None        # AvailableAtStart false: the frame its first charge is over (simpower.charge_due keeps it)
    made = 0            # the frame its thing was made (World.build; review 141 A388: not the tick's seconds label)

    def on_create(self, frame):
        self.made = frame

    def on_build_complete(self):
        pass

    def made_frame(self):
        return self.made

    def power(self):
        return self.data.power

    def ready_at(self):
        return self.ready

    def set_ready_at(self, frame):
        self.ready = frame

    def first_charge(self):
        return self.first

    def set_first_charge(self, frame):
        self.first = frame

    def ready_by(self, frame):
        at = self.ready if self.ready is not None else 0 if self.data.at_start else self.first
        return at is not None and at <= frame


class MonitorData(SpecialPowerData):
    def __init__(self, power=None, condition=None):
        super().__init__(power)
        self.condition = condition      # ReadyCondition: the model condition it sets while its power is ready

    @classmethod
    def read(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'), templates.attr(head, 'ReadyCondition'))


@factory.module('MonitorSpecialPowerTimerUpdate')
class Monitor(module.Module, interfaces.ReadyMonitor):
    """MonitorSpecialPowerTimerUpdate (E145, checks/engine_modulebatch.readings.toml): its thing has ReadyCondition
    while the reload of every SpecialPower module of its thing serving its power is over, and not otherwise (the
    proton collider's SPECIALPOWER1_READY after a countdown of 0, gone after 10000; none on the one without it). A
    module with AvailableAtStart="false" no reload has started is ready once its first charge is over (the bench's
    collider: 0 at s1-s6; A388 the Chronosphere's, simpower.charge_due), nor is a power its thing has no module for
    (review yy #6). Asked when the condition is read (Sim.has_model_condition). Not modelled: disabled / unpacking
    hosts (INFERRED: the reload alone); the cast itself still ignores AvailableAtStart."""
    DATA = MonitorData

    def shows(self, condition, frame):
        d = self.data
        mods = [m for m in self.thing.find(interfaces.SpecialPower) if m.power() == d.power]
        return bool(d.condition) and condition == d.condition and bool(mods) and all(m.ready_by(frame) for m in mods)


class RecallData(SpecialPowerData):
    def __init__(self, power=None, most=4):
        super().__init__(power)
        self.most = most            # MaxAircraftToRecall (the XSD's default 4)

    @classmethod
    def read(cls, head, inner):
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
    def read(cls, head, inner):
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
    def read(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'), templates.attr(head, 'TeleportLinkID'),
                   templates.num(templates.attr(head, 'Radius')), templates.attr(head, 'CanAffectObjectFilter'))


# AlliedChronosphereSpecialPowerObjectFilter (Includes/SpecialPowerObjectFilters.xml), the one retail store filter:
# Include, Exclude kinds, StatusBitFlagsExclude (its IncludeThing time bombs not taken)
CHRONO = ('AlliedChronosphereSpecialPowerObjectFilter', frozenset({'INFANTRY', 'VEHICLE'}), frozenset({'AIRCRAFT'}),
          frozenset({'SUBMERGED', 'AIRBORNE_TARGET', 'NOT_IN_WORLD'}))


def asset_filter(name, texts):
    """The ObjectFilterAsset `name` of the mission's own XML texts as store() takes it: (Include, Exclude kinds,
    StatusBitFlagsExclude, (IncludeThing, ExcludeThing templates lower case), Relationship); None: not there or not
    Rule ANY. Relationship read as its owner's own only (INFERRED: SAME_PLAYER ALLIES, another allied player not taken)."""
    return _filter_in(texts, 'ObjectFilterAsset', name, 'Filter')


def _filter_in(texts, tag, name, inner_tag):
    """The filter `inner_tag` of the block <tag id=name> as asset_filter gives it (also a SpecialPowerTemplate's own
    ObjectFilter: the beacon pull)."""
    for text in texts:
        for head, inner in templates.blocks(text, tag):
            if templates.attr(head, 'id') != name:
                continue
            fh, fi = next(iter(templates.blocks(inner, inner_tag)), ('', ''))
            if (templates.attr(fh, 'Rule') or 'ANY') != 'ANY':
                return None
            return (frozenset(templates.words(fh, 'Include')), frozenset(templates.words(fh, 'Exclude')),
                    frozenset(templates.words(fh, 'StatusBitFlagsExclude')),
                    tuple(frozenset(x.strip().lower() for x in re.findall(rf'<{k}>([^<]+)</{k}>', fi))
                          for k in ('IncludeThing', 'ExcludeThing')), templates.attr(fh, 'Relationship'))
    return None


def _takes(spec, me, t):
    """t passes spec (asset_filter's), me the caster: not me, its kinds or templates, its status, its owner."""
    inc, exc, bits, things, rel = spec
    return (t is not me and t.alive and (t.kinds & inc or t.template.lower() in things[0]) and not t.kinds & exc
            and t.template.lower() not in things[1] and not module.status_now(t) & bits
            and (rel is None or t.owner == me.owner))


@factory.module(STORE)
class StoreObjects(SpecialPower, interfaces.Store):
    """StoreObjectsSpecialPower (E227, checks/engine_teleport.readings.toml): the Chronosphere's first step takes the
    things of its filter within Radius of the cast's point (the second step, TeleportStoredObjectsUpdate, carries them:
    engine/modules/teleport.py). A filter other than CHRONO takes no one (a gap; INFERRED as the private model's
    unfiltered store). Not modelled: the OCL's markers."""
    DATA = StoreData
    STATE = ('ready', 'first', 'made', 'stored_at', 'carried', 'spec')
    stored_at = None    # the stored point; None: never stored, or cleared
    carried = ()        # the stored things
    spec = None         # the last cast's own filter (a send's second take keeps it)

    def link(self):
        return self.data.link

    def store(self, point, texts=()):
        """texts: the mission's own XML, its CanAffectObjectFilter read there (asset_filter: the Liberty's deck, A427);
        none: the last cast's (a send's second take), else CHRONO."""
        me, d = self.thing, self.data
        spec = self.spec = asset_filter(d.filter, texts) if texts else self.spec
        self.stored_at, self.carried = point, ()
        if spec is None and d.filter != CHRONO[0]:
            self.world.gap('StoreObjectsSpecialPower', d.filter or '', '只认原版时空传送的对象过滤器：没带走谁')
            return
        spec = spec or (CHRONO[1], CHRONO[2], CHRONO[3], (frozenset(), frozenset()), None)
        self.carried = tuple(t for t in self.world.living() if _takes(spec, me, t)
                             and math.hypot(t.x - point[0], t.y - point[1]) <= d.radius)

    def stored(self):
        return [t for t in self.carried if t.alive]

    def clear(self):
        self.stored_at, self.carried = None, ()


class PullData(SpecialPowerData):
    def __init__(self, power=None, unpack=0, radius=0.0, near=0.0):
        super().__init__(power)
        self.unpack, self.radius, self.near = unpack, radius, near     # UnpackTime (frames), Radius, MinDestinationRadius

    @classmethod
    def read(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'),
                   int(FPS * templates.secs(templates.attr(head, 'UnpackTime') or '0s') + 0.5),
                   templates.num(templates.attr(head, 'Radius')), templates.num(templates.attr(head, 'MinDestinationRadius')))


@factory.module(PULL)
class PullToCaster(SpecialPower, interfaces.Teleport, interfaces.Update):
    """TeleportToCasterSpecialPower (A428, checks/engine_bcnpull.readings.toml; read in the program): the beacon pull. UnpackTime frames after the cast (rounded, the base unpack) the things
    of its power's own ObjectFilter within Radius of the point are put round the caster: the i-th of n at angle
    2 pi i / n, MinDestinationRadius out, facing out. Not modelled: the search for a free spot out to
    MaxDestinationRadius (INFERRED: the first one is free), the scan order, KillObjectsIfPlacedInBadSpot, the FX."""
    DATA = PullData
    PHASE = 'seq'
    STATE = ('ready', 'first', 'made', 'end', 'due', 'spec')
    end = None          # the point; None: idle
    due = 0             # the frame they land
    spec = None         # its power's filter (asset_filter's), read at the cast

    def begin(self, point, lag=0, texts=()):
        """lag 0 (engine_bcnpull a / b: in at his side from the 9th frame of the script's cast -- the Liberty's own
        jump, the same base unpack, a frame later: INFERRED the script's frame not counted here)."""
        self.spec = _filter_in(texts, 'SpecialPowerTemplate', self.data.power, 'ObjectFilter') or self.spec
        self.end, self.due = point, self.world.frame + self.data.unpack + lag
        self.world.wake(self, self.due)

    def update(self, frame):
        if self.end is None:
            return interfaces.SLEEP
        if frame < self.due:
            return self.due - frame
        me, d, (px, py) = self.thing, self.data, self.end
        self.end = None
        if self.spec is None:
            self.world.gap(PULL, d.power or '', '技能模板里没有对象过滤器：没拉人')
            return interfaces.SLEEP
        pulled = [t for t in self.world.living() if _takes(self.spec, me, t) and math.hypot(t.x - px, t.y - py) <= d.radius]
        for i, t in enumerate(pulled):
            a = 2 * math.pi * i / len(pulled)
            t.x, t.y, t.angle = me.x + d.near * math.cos(a), me.y + d.near * math.sin(a), a
        return interfaces.SLEEP


class ReturnData(SpecialPowerData):
    def __init__(self, power=None, condition=None, seconds=0.0):
        super().__init__(power)
        self.condition, self.seconds = condition, seconds      # SetModelCondition, SetModelConditionTime

    @classmethod
    def read(cls, head, inner):
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
    def read(cls, head, inner):
        names = set(re.findall(r'(\w+)\s*=', head))
        return cls(templates.attr(head, 'SpecialPowerTemplate'),
                   not inner.strip() and names == {'id', 'SpecialPowerTemplate'})


@factory.module(ASSIGN)
class AssignSlaves(SpecialPower, interfaces.Assign, interfaces.Update):
    """AssignSlavesTargetObjectSpecialPower (step M13; E67, moved from simassign.Assignments' store and due): a
    SpecialPower with a dispatch. The host's press (simassign.Assignments.press) sends an idle drone of its (E235 c /
    d: it flies, attach.Attach.send); with all of them busy it assigns here (E181: the fourth from the press on, the
    three kept busy -- a fourth drone of no flight, INFERRED). Then in the assignments cell it mends the target on the
    drones' pulse (SURVEY / PHASE: rate x 20 / 15 a pulse) until whole, and stops -- a gap noted -- once anything
    moves: either dies, the owners differ, no drone of its SpawnBehaviors lives, either moves, or the target's health
    is changed by anything else (a conservative stop, INFERRED). Asleep without a target. Its state was a store's, never in the frame record: RECORDED names none."""
    DATA = AssignData
    PHASE = 'assignments'
    STATE = ('ready', 'first', 'made', 'tgt', 'rate', 'last', 'spots')
    RECORDED = ()
    ALIGN = {'assigned repair': '部分对齐：无人机全忙时显式派发从按下起按无人机脉冲治疗（E181 第四台）；'
                                '"第四架、不飞"与中断即停为 INFERRED'}
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
        if frame % SURVEY == PHASE:
            t.mend(self.rate * SURVEY / FPS)
            self.last = t.hp
            self.world.used.add('assigned repair')
        if t.hp >= t.max_hp:
            return self._stop()
        return 1


class OCLMonitorData(module.ModuleData):
    def __init__(self, options=frozenset()):
        self.options = options      # Options: MASTER, RELEASE_WHEN_MASTER_CHANGES_TARGET (the measured ones)

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.words(head, 'Options'))


@factory.module('OCLMonitorUpdate')
class OCLMonitor(module.Module):
    """OCLMonitorUpdate: its Options, read by its thing's OCLRun (the bomber's own, no options, does nothing)."""
    DATA = OCLMonitorData


@factory.module(OCL)
class OCLRun(SpecialPower, interfaces.OCLRun, interfaces.Update):
    """OCLSpecialPower of one ParabolicCurve (A375; checks/engine_oclmonitor_e, engine_spnbomb): a SpecialPowerNugget
    hit calls a run (curve: simunits.nugget_self_power) -- InitialDelay + ApproachTime frames on the bomber is over the
    target (TRACK_TARGET_OBJECT: where it stands then, else where it stood), the bomb's warhead hits FALL frames later
    (World.fire, as the caster's: its DamageNuggets alone); the bomber is gone ApproachTime x End / StartDistance
    after it was over. With an OCLMonitorUpdate MASTER the master holds one run: a call while it is held does nothing;
    the run is let go (drops nothing) once the master stops attacking -- no call within the calling weapon's
    FiringDuration + PreAttackDelay of its last (INFERRED: E222 s, and engine_spnbombc's instant one-shot gun that
    never gets a bomber) -- or, with RELEASE_WHEN_MASTER_CHANGES_TARGET, calls at another target. The bomber
    (CreateObject, its owner's) is a thing from InitialDelay on till gone (engine_spnbombc counts AIRCRAFT: from 53
    frames after the call), made StartDistance short of the target on the caster's side and left there (INFERRED: the
    side; its flight not modelled); it holds its own gun (the run's bomb is its drop); a run let go takes it away at
    once (INFERRED); one shot down before it is over drops nothing (review 133; the retail cut-off not measured,
    INFERRED). Not modelled: the bomb's other nuggets."""
    PHASE = 'seq'
    STATE = ('ready', 'first', 'made', 'runs', 'firing', 'aim')
    runs = ()           # (target, its spot at the call, made, hit, gone frame, the curve, the bomber made or None)
    firing = 0          # the last frame the master counts as attacking
    aim = None          # the target of its last call

    def options(self):
        return frozenset().union(*(m.data.options for m in self.thing.find(OCLMonitor)))

    def let_go(self, run, frame, opts):
        return 'MASTER' in opts and (frame > self.firing or not self.thing.alive or (
            'RELEASE_WHEN_MASTER_CHANGES_TARGET' in opts and self.aim is not run[0]))

    def call(self, target, curve, window):
        now, opts = self.world.frame, self.options()
        self.firing, self.aim = now + window, target
        self.runs = tuple(run for run in self.runs if not self.drop(run, now, opts))
        if 'MASTER' in opts and self.runs:
            return
        over = now + curve['delay'] + curve['approach']
        self.runs += ((target, (target.x, target.y), now + curve['delay'], over + FALL,
                       over + round(curve['approach'] * curve['out']), curve, None),)
        self.world.wake(self, now + 1)

    def drop(self, run, frame, opts):
        """Whether `run` ends: let go or gone (its bomber, if made, taken away)."""
        if not (self.let_go(run, frame, opts) or frame >= run[4]):
            return False
        if run[6] is not None and run[6].alive:
            self.world.remove(run[6], '轰炸机飞走')
        return True

    def update(self, frame):
        me, opts, kept = self.thing, self.options(), []
        for run in self.runs:
            t, spot, made, hit, gone, curve, plane = run
            if self.drop(run, frame, opts):
                continue
            at = (t.x, t.y) if curve['track'] and t.alive else spot
            if frame == made and curve['plane']:
                d = math.hypot(me.x - at[0], me.y - at[1]) or 1.0
                plane = self.world.make(me, curve['plane'], at[0] + (me.x - at[0]) * curve['start'] / d,
                                        at[1] + (me.y - at[1]) * curve['start'] / d)
                plane.engine_status.add('NO_ATTACK')
                plane.status.add('NO_ATTACK')
            if plane is not None and not plane.alive and frame <= hit - FALL:
                continue                # shot down before it was over: the bomb never left it (INFERRED)
            if frame == hit:
                self.world.fire(me, curve['bomb'], at=at)
            kept.append((t, spot, made, hit, gone, curve, plane))
        self.runs = tuple(kept)
        return 1 if self.runs else interfaces.SLEEP
