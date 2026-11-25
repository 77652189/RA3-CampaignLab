"""E67 aggregate healing of one explicitly assigned ground vehicle.

No drone parent is selected here. Autonomous acquisition, occupancy, retargeting
and status cleanup remain gaps; see work/re/e_assign_e67.md.
L2 heal (ADR 0029): `Assignments` holds the world and reaches it only through simworld.WORLD_API.
Step M13 / E235: the press sends the source's nearest idle repair drone (engine/modules/attach.py send: it flies);
with none idle the AssignSlavesTargetObjectSpecialPower module heals it (engine/modules/specialpower.py AssignSlaves,
the assignments cell); this keeps the press: which press, which target.
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
              '派最近的空闲无人机、全忙时从按下起治疗（第四架）；换父/换目标/状态清理未测')
        if module.target() is not None:
            return True  # Retargeting is deliberately not inferred.
        if any(h is target for b in world.bodies.values() for h in
               [m.target() for m in b.find(interfaces.Assign)] + [m.repairing() for m in b.find(interfaces.Attach)]):
            return True  # Multiple dispatchers, or a drone already on it (one a parent: INFERRED), are unmeasured.
        if not (target and target.alive and target.owner == source.owner
                and target.template == 'AlliedAntiVehicleVehicleTech1'
                and target.template not in world.own
                and target.hp < target.max_hp
                and math.hypot(target.x - source.x, target.y - source.y) <= 200
                and any(c.alive for c in source.spawned_children)):
            return True
        if not any(m.send(target) for c in sorted(source.spawned_children, key=lambda c: math.hypot(
                c.x - target.x, c.y - target.y)) if c.alive for m in c.find(interfaces.Attach)):
            module.assign(target, rate)     # E181: all drones busy (nearest idle one first: INFERRED)
        return True
