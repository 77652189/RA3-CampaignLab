"""E67 aggregate healing of one explicitly assigned ground vehicle.

No drone parent is selected here. Autonomous acquisition, occupancy, retargeting
and status cleanup remain gaps; see work/re/e_assign_e67.md.
L2 heal (ADR 0029): `Assignments` holds the world and reaches it only through simworld.WORLD_API.
"""
import math

import simunits


class Assignments:
    def __init__(self, world):
        self.world = world
        self.active = {}

    def press(self, source, command, target):
        world = self.world
        rate = simunits.assigned_repair_rate(source.template, command, world.own)
        if not rate:
            return False
        world.gap('AssignSlavesTargetObjectSpecialPower', source.template,
              '仅显式单目标治疗；自动获取、前三目标占用、换父/换目标/状态清理未测；启动相位INFERRED')
        if source.name in self.active:
            return True  # Retargeting is deliberately not inferred.
        if any(active[1] is target for active in self.active.values()):
            return True  # Multiple dispatchers on one target are unmeasured.
        if not (target and target.alive and target.owner == source.owner
                and target.template == 'AlliedAntiVehicleVehicleTech1'
                and target.template not in world.own
                and target.hp < target.max_hp
                and math.hypot(target.x - source.x, target.y - source.y) <= 200
                and any(c.alive for c in source.spawned_children)):
            return True
        self.active[source.name] = (source, target, rate, target.hp,
                                    (source.x, source.y, target.x, target.y))
        return True

    def due(self, frame):
        world = self.world
        for name, (source, target, rate, previous, positions) in list(self.active.items()):
            if (not source.alive or not target.alive or source.owner != target.owner
                    or not any(c.alive for c in source.spawned_children)
                    or positions != (source.x, source.y, target.x, target.y)
                    or abs(target.hp - previous) > 1e-6):
                world.gap('AssignSlavesTargetObjectSpecialPower', 'interrupted',
                      '移动、死亡、换主或外部血量变化后的派发边界未测；保守停止为INFERRED')
                del self.active[name]
                continue
            target.mend(rate / world.fps)
            self.active[name] = (source, target, rate, target.hp, positions)
            world.used.add('assigned repair')
            if target.hp >= target.max_hp:
                del self.active[name]
