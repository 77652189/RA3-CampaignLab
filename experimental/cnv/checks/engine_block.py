"""Block scene and helpers also used by the stasis bench."""
from maps import probe_block
from parts import Mission, Script, square

IFV = 'AlliedAntiAirVehicleTech1'
TANK = 'AlliedAntiVehicleVehicleTech1'
WALL = 'SovietBunker'              # the ice wall is a structure; a retail one stands in (G5: no units/ imports)
PLUG = 'AlliedMCV'
FOOT = 'AlliedAntiInfantryInfantry'
LABEL = {'bits': '位图墙', 'built': '建筑墙', 'late': '后建墙', 'enemy move': '敌堵移动', 'enemy attack': '敌堵攻移'}


def _key(s):
    return s.title().replace(' ', '')


def mission():
    m = Mission(name='CampBlock', map=probe_block, facts={})
    for lane in ('bits', 'built', 'late'):
        m.put(IFV, f'{lane} start', role=f'{lane} unit', name=f'UNIT - CNV Block {_key(lane)} Unit')
    m.put(FOOT, 'late start', 80.0, 0.0, role='late foot', name='UNIT - CNV Block Late Foot')    # foot's soldier
    x0, y0 = m.site('built wall')
    for k, (x, y) in enumerate(probe_block.ROW['built']):
        m.put(WALL, 'built wall', x - x0, y - y0, name=f'UNIT - CNV Block Built Wall {k}',
              role='built wall' if k == 0 else '')                  # a role publishes the template (counted)
    for lane in ('enemy move', 'enemy attack'):
        m.put(TANK, f'{lane} start', role=f'{lane} unit', name=f'UNIT - CNV Block {_key(lane)} Unit')
        for k, dy in enumerate((-30.0, 30.0)):
            m.put(PLUG, f'{lane} plug', 0, dy, side='s1', angle=90.0, role=f'{lane} plug {k + 1}',
                  name=f'UNIT - CNV Block {_key(lane)} Plug {k + 1}')
    return m


def _go(m, t, lane, kind='move'):
    wp = f'Test Block {_key(lane)} Goal'
    t.waypoints[wp] = m.site(f'{lane} goal')
    return m.order(kind, [m.role(f'{lane} unit').name], wp, crew=f'Block{_key(lane)}')


def _scored(m, t, lane):
    """Latched (sampling misses a pass): 1 once the lane's unit has been by the far gap, 10 once it has been at the
    goal -- 11 went round, 10 went straight through."""
    counter, unit = f'CNV_Block_{_key(lane)}', m.role(f'{lane} unit').name
    t.counters.append((counter, LABEL[lane]))
    for k, (site, half, n) in enumerate(((f'{lane} gap', 140.0, 1), (f'{lane} goal', 100.0, 10))):
        area = f'Test Block {_key(site)}'
        t.areas[area] = square(*m.site(site), half)
        t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', unit, area)],
                                [('INCREMENT_COUNTER', n, counter)], once=True))
