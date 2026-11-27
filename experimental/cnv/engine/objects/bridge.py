"""A bridge's proxy and its gatehouses (L2, ADR 0029: the world only through simworld.WORLD_API).

The proxy: a template whose Body is a ManagerBody (HB_Bridge_02, HV_Bridge_01) takes its whole health from
simunits.manager_proxy_health (engine_managerbody a / b). The gatehouses (A315, engine_bridgefix, j07 2178): a named
bridge start (object flags 16) followed by its end (32) gets its BridgeBuilder's GateHouse at the start and GateHouse2
(else GateHouse) at the end, named '<start name>_GateHouse1' / '2', owned as the start; their health is the proxy's
(ManagedImmortalBody.manager: the start's name's proxy -- the end's when the end has the same name, as j07, the one a
script's NAMED_DAMAGE of that name hits). Bench run 2 (CampBridgeFixA_mcp_1122_202537): the gatehouse reads 100, 1
after the proxy took 20000, 100 again once an engineer went in (order.capture_due); it keeps its owner. E301:
20000 script damage to the short center kills it and leaves proxy and gatehouse at 1%. Pieces outside the measured
centers and broken-deck pathing remain gaps."""
import engine.data.units as simunits
from engine.kernel import interfaces
from engine.ports import templates
from engine.world.handle import CIV, free_key

GAP = 'HB_Bridge_02整体代理伤害、桥头堡血量与修桥、向东270/700桥的中段落点和270桥中段脚本伤害已量；有效HP/内部下限映射和精确致死边界INFERRED，其他桥段及断桥通行仍gap'


def proxy_health(world, template):
    """A ManagerBody template's whole-proxy health, else None (Sim.add makes the proxy immortal at 1 % of it)."""
    if not world.world.blocks_of(template, 'ManagerBody'):
        return None
    world.gap('ManagerBody', template, GAP)
    return simunits.manager_proxy_health(template, world.own)


def place_parts(world, objects):
    """After the map load, place named pairs' gatehouses and the measured bridge centers."""
    add = world.add
    for start, end in zip(objects, objects[1:]):
        if not start.name or getattr(start, 'flags', None) != 16 or getattr(end, 'flags', None) != 32:
            continue
        head = next(iter(world.world.blocks_of(start.template, 'BridgeBuilder')), ('', ''))[0]
        first = templates.attr(head, 'GateHouse')
        proxy = world.bodies.get(start.name)
        if not first or proxy is None:
            continue
        owner = world.players.get(start.side, CIV)
        for k, (template, at) in enumerate(((first, start), (templates.attr(head, 'GateHouse2') or first, end)), 1):
            g = add(f'{start.name}_GateHouse{k}', template, owner, at.x, at.y)
            g.find(interfaces.Body).manager = proxy.find(interfaces.Body)
        length = end.x - start.x
        if (end.template != start.template or end.y != start.y
                or simunits.bridge_generation_counts(start.template, length, head=head) is None):
            continue
        # E297/E298: HB_Bridge_02 eastbound in Niagara, engine_bridgesegment:a/b.
        a, b = (templates.attr(head, field) for field in ('CenterPiece', 'CenterPieceB'))
        for i, template in enumerate((a,) if length == 270 else (a, b, a, b), 1):
            name = free_key(world, '#bridge center {}'.format, i)
            body = add(name, template, owner, start.x + 150 * i, start.y).find(interfaces.Body)
            if length == 270 and body.kind() == 'ManagedActiveBody':
                body.manager = proxy.find(interfaces.Body)
