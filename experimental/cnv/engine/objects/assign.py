"""E67 aggregate healing of one explicitly assigned ground vehicle.

No drone parent is selected here. Autonomous acquisition, occupancy, retargeting
and status cleanup remain gaps; see work/re/e_assign_e67.md.
L2 heal (ADR 0029): `Assignments` holds the world and reaches it only through simworld.WORLD_API.
Step M13: the dispatch and its healing are the source's AssignSlavesTargetObjectSpecialPower module's
(engine/modules/specialpower.py AssignSlaves, the assignments cell); this keeps the press: which press, which target.
"""
import math

import engine.data.units as simunits
from engine.kernel import interfaces


class Assignments:
    def __init__(self, world):
        self.world = world

    def press(self, source, command, target):
        world = self.world
        power = simunits.command_power(command, world.own)
        module = next((m for m in source.find(interfaces.Assign) if m.plain() and m.power() == power), None)
        rate = module and simunits.assigned_repair_rate(source.template, power, world.own)
        if not rate:
            return False
        world.gap('AssignSlavesTargetObjectSpecialPower', source.template,
              '仅显式单目标治疗；自动获取、前三目标占用、换父/换目标/状态清理未测；启动相位INFERRED')
        if module.target() is not None:
            return True  # Retargeting is deliberately not inferred.
        if any(m.target() is target for b in world.bodies.values() for m in b.find(interfaces.Assign)):
            return True  # Multiple dispatchers on one target are unmeasured.
        if not (target and target.alive and target.owner == source.owner
                and target.template == 'AlliedAntiVehicleVehicleTech1'
                and target.template not in world.own
                and target.hp < target.max_hp
                and math.hypot(target.x - source.x, target.y - source.y) <= 200
                and any(c.alive for c in source.spawned_children)):
            return True
        module.assign(target, rate)
        return True
