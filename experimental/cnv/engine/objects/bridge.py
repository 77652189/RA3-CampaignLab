"""A bridge's proxy and its gatehouses (L2, ADR 0029: the world only through simworld.WORLD_API).

The proxy: a template whose Body is a ManagerBody (HB_Bridge_02, HV_Bridge_01) takes its whole health from
simunits.manager_proxy_health (engine_managerbody a / b). The gatehouses (A315, engine_bridgefix, j07 2178): a named
bridge start (object flags 16) followed by its end (32) gets its BridgeBuilder's GateHouse at the start and GateHouse2
(else GateHouse) at the end, named '<start name>_GateHouse1' / '2', owned as the start; their health is the proxy's
(ManagedImmortalBody.manager: the start's name's proxy -- the end's when the end has the same name, as j07, the one a
script's NAMED_DAMAGE of that name hits). Bench run 2 (CampBridgeFixA_mcp_1122_202537): the gatehouse reads 100, 1
after the proxy took 20000, 100 again once an engineer went in (order.capture_due); it keeps its owner. Not modelled:
the bridge's pieces, a broken bridge closing its deck to the paths (sim.py 'bridge deck': walkable whatever its health)."""
import engine.data.units as simunits
from engine.kernel import interfaces
from engine.ports import templates
from engine.world.handle import CIV

GAP = '仅HB_Bridge_02整体代理脚本伤害、桥头堡血量随代理与工程师修桥已量；有效HP/内部下限映射INFERRED，其他配置、桥段生成、断桥通行未建模'


def proxy_health(world, template):
    """A ManagerBody template's whole-proxy health, else None (Sim.add makes the proxy immortal at 1 % of it)."""
    if not world.world.blocks_of(template, 'ManagerBody'):
        return None
    world.gap('ManagerBody', template, GAP)
    return simunits.manager_proxy_health(template, world.own)


def gatehouses(world, objects):
    """After the map's objects are placed (Sim.__init__): every named start / end pair's two gatehouses."""
    for start, end in zip(objects, objects[1:]):
        if not start.name or getattr(start, 'flags', None) != 16 or getattr(end, 'flags', None) != 32:
            continue
        head = next(iter(world.world.blocks_of(start.template, 'BridgeBuilder')), ('', ''))[0]
        first = templates.attr(head, 'GateHouse')
        proxy = world.bodies.get(start.name)
        if not first or proxy is None:
            continue
        for k, (template, at) in enumerate(((first, start), (templates.attr(head, 'GateHouse2') or first, end)), 1):
            g = world.add(f'{start.name}_GateHouse{k}', template, world.players.get(start.side, CIV), at.x, at.y)
            g.find(interfaces.Body).manager = proxy.find(interfaces.Body)
