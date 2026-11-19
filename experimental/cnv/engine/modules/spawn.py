"""SpawnBehavior and SlavedUpdate (bench engine_spawn / engine_spawn_refill / engine_spawn_power, the Allied war
factory's repair drones; checks/engine_mining.py, the refineries' collector; moved from simunits.spawn_modules /
unpack_spawn, Sim.spawn_due and the body's spawned_children / spawn_parent / spawn_module / spawn_refills in step M7,
ADR 0029, docs/engine/sim-modules.md 4): a thing that makes things of its own, and the thing it made.

Two SpawnBehavior configurations are read, each exactly (the whole subtree compared, so a new flag or child stays an
explicit gap):
  * the war factory's drones (DRONE, a Die DeathTypes="ALL" and one SpawnTemplate AlliedWarFactoryRepairDrone): the
    host makes the initial burst of three when a map places it (Sim.add); a drone's death queues one of the same
    template SpawnReplaceDelayData (10 s) on, made in the spawn cell when it is due (the module sleeps otherwise); a
    deletion queues none (the drone's SlavedUpdate notes a gap); the factory's death or deletion takes its drones
    with it (Destroy, step B4c). A supply
    shortage alone leaves the count at three (engine_spawn_power): it is not KillSpawnsOnDisabled. Real disabling,
    capture, death and refill during an outage, unpacking, the spot (INFERRED: the factory's centre) are not
    modelled; the subsecond phase of a refill is INFERRED.
  * the refineries' collector (UNPACK, one SpawnTemplate): one collector when a map places the refinery
    (Sim.unpack_child); built or scripted ones are a gap.
Any other block: neither (`child` and `unpack_child` None) -- the host notes the gap.

A made thing's SlavedUpdate keeps who made it (spawn_parent) and by which module id (spawn_module); one whose
template has none is given one when made (World.attach), as the body's fields were set on any child. The names are
the body's old fields, so the frame record is unchanged (the spawner's two lists, several modules a thing, record
through the body's forwards: its RECORDED is empty)."""
import math
import xml.etree.ElementTree as ET

from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15                # the game's logic frames a second (bench 2026-10-28, probe align)

DRONE = dict(SpawnNumberData='3', InitialBurst='3', SpawnReplaceDelayData='10s', SpawnedRequireSpawner='true',
             KillSpawnsOnCaptured='true', SpawnInsideBuilding='true', KillSpawnsOnDisabled='true')
DRONE_KIDS = [('Die', {'DeathTypes': 'ALL'}, '', 0), ('SpawnTemplate', {}, 'AlliedWarFactoryRepairDrone', 0)]
UNPACK = dict(SpawnNumberData='1', SpawnReplaceDelayData='9999s', IsOneShotData='true', FadeInTime='1.0s',
              SpawnOnUnpack='true', CanReclaimOrphans='false', SetPurchasePrice='true')


def _frames(seconds):
    """Whole frames, rounded up (engine_clip, bench 2026-11-09; the 1e-6 keeps 1.2 x 15 at 18)."""
    return int(math.ceil(seconds * FPS - 1e-6))


class SpawnData(module.ModuleData):
    def __init__(self, id='', child=None, unpack=None, delay=0):
        self.id = id                    # its module id (a made thing's spawn_module)
        self.child = child              # DRONE: the template it keeps alive; None: not that configuration
        self.unpack = unpack            # UNPACK: the collector it gives; None: not that configuration
        self.delay = delay              # SpawnReplaceDelayData in frames: a dead child's replacement after

    @classmethod
    def parse(cls, head, inner):
        try:
            node = ET.fromstring('<SpawnBehavior ' + head + '>' + inner + '</SpawnBehavior>')
        except ET.ParseError:
            return cls(templates.attr(head, 'id', ''))
        attrs = dict(node.attrib)
        mid = attrs.pop('id', '')
        kids = [(c.tag, dict(c.attrib), (c.text or '').strip(), len(c)) for c in node]
        child = 'AlliedWarFactoryRepairDrone' if attrs == DRONE and kids == DRONE_KIDS else None
        unpack = (kids[0][2] if attrs == UNPACK and len(kids) == 1 and kids[0][:2] == ('SpawnTemplate', {})
                  and kids[0][2] and not kids[0][3] else None)
        return cls(mid, child, unpack, _frames(templates.secs(attrs.get('SpawnReplaceDelayData'))))


@factory.module('SpawnBehavior')
class Spawn(module.Module, interfaces.Update, interfaces.Create, interfaces.Destroy, interfaces.Spawn):
    """In the spawn cell, when a queued replacement is due: asks the host to make it (World.spawn); asleep
    otherwise. Its thing's end (Destroy) takes the things it made (World.remove)."""
    DATA = SpawnData
    PHASE = 'spawn'
    STATE = ('spawned_children', 'spawn_refills')
    RECORDED = ()       # they record through the body's forwards

    def on_create(self, frame):
        self.spawned_children = []      # the things it made, in the order made (dead ones stay)
        self.spawn_refills = []         # (due frame, its module id, template): replacements queued

    def on_build_complete(self):
        pass

    def module_id(self):
        return self.data.id

    def child(self):
        return self.data.child

    def unpack_child(self):
        return self.data.unpack

    def children(self):
        return self.spawned_children

    def refills(self):
        return self.spawn_refills

    def adopt(self, child):
        self.spawned_children.append(child)

    def child_died(self, template, frame):
        due = frame + self.data.delay
        self.spawn_refills.append((due, self.data.id, template))
        self.world.wake(self, due)

    def on_destroy(self):
        """Its thing died or was deleted (step B4c): the queue emptied and every thing it made that lives deleted
        with it (engine_spawn: both script kill and delete remove all three in the same sample; deletion rather than
        a lethal hit INFERRED, the children's death effects unmeasured)."""
        self.spawn_refills.clear()
        for child in self.spawned_children:
            if child.alive:
                self.world.remove(child, 'SpawnedRequireSpawner')

    def update(self, frame):
        if not self.thing.alive:
            return interfaces.SLEEP
        for item in list(self.spawn_refills):
            if item[0] <= frame:
                self.spawn_refills.remove(item)
                self.world.spawn(self.thing, self, item[2])
        return min(due for due, _, _ in self.spawn_refills) - frame if self.spawn_refills else interfaces.SLEEP


@factory.module('SlavedUpdate')
class Slaved(module.Module, interfaces.Die, interfaces.Destroy, interfaces.Slaved):
    """Who made its thing (spawn_parent: the thing, None for one no spawner made) and by which of its modules
    (spawn_module: the module id; the module itself: spawner). Its thing's death (Die) tells that module while the
    maker lives (a replacement queued, the delay SpawnReplaceDelayData); a deletion (Destroy) tells it nothing --
    a gap noted (a child deleted outright refilling or not is unmeasured)."""
    DATA = module.ModuleData
    RECORDED = ('spawn_parent', 'spawn_module')
    STATE = RECORDED + ('_spawner',)
    spawn_parent, spawn_module, _spawner = None, '', None     # no spawner made it (yet)

    def enslave(self, parent, spawner):
        self.spawn_parent, self.spawn_module, self._spawner = parent, spawner.module_id(), spawner

    def slaver(self):
        return self.spawn_parent

    def slaver_module(self):
        return self.spawn_module

    def spawner(self):
        return self._spawner

    def on_die(self, info):
        parent = self.spawn_parent
        if parent is not None and parent.alive:
            self._spawner.child_died(self.thing.template, info.frame)

    def on_destroy(self):
        parent = self.spawn_parent
        if self.thing.deleted and parent is not None and parent.alive:
            self.world.gap('SpawnBehavior', parent.template, '子体直接删除是否补充未测；不作为死亡通知')
