"""DestroyObjectsUpdate's retail civilian filter (E307, engine_destroyobjects readings).

The script-spawned effect removes an initial nearby civilian and leaves a later
arrival alive. First update, center distance and deletion without death callbacks
are INFERRED. Other filters, ownership and spawn paths remain gaps.
"""
import math
import xml.etree.ElementTree as ET

from engine.kernel import factory, interfaces, module
from engine.ports import templates


class DestroyObjectsData(module.ModuleData):
    def __init__(self, radius):
        self.radius = radius

    @classmethod
    def parse(cls, head, inner):
        try:
            filt = ET.fromstring(inner.strip())
        except ET.ParseError:
            return cls(None)
        if filt.tag != 'ObjectFilter' or filt.attrib != {'Rule': 'NONE', 'Include': 'CIVILIAN_UNIT'} or len(filt):
            return cls(None)
        return cls(templates.num(templates.attr(head, 'Radius', '0'), None))


@factory.module('DestroyObjectsUpdate')
class DestroyObjects(module.Module, interfaces.Update):
    DATA = DestroyObjectsData
    PHASE = 'seq'
    STATE = ()

    def update(self, frame):
        host, radius = self.thing, self.data.radius
        if radius is None:
            self.world.gap('DestroyObjectsUpdate', host.template, '未模拟的对象筛选或半径')
            return interfaces.SLEEP
        if host.alive:
            for target in self.world.living():
                if target is not host and target.alive and 'CIVILIAN_UNIT' in target.kinds and (
                        math.hypot(target.x - host.x, target.y - host.y) <= radius):
                    self.world.remove(target, 'DestroyObjectsUpdate')
        return interfaces.SLEEP
