"""C FriendlyUnit Distance probe: three same-player MCVs, swapped near role.

Prediction before measurement: StaticDefense's tactical target is the MCV
nearest the AI base, independently of whether its Guardians move there.
Other sort modes and unique-slot arbitration remain INFERRED.
"""
from missions.aifriendly_bench import mission as original
from missions.aiteams_bench import host_unit


def mission(swapped=False):
    m = original(True)
    m.name = 'CampFrSwap' if swapped else 'CampFrNear'
    # All candidates stay outside the original Guardian recruitment mask.
    for role, offset in [('friendly', (1400, 0) if swapped else (-650, 0)),
                         ('second', (-650, 0) if swapped else (1400, 0)),
                         ('third', (0, 1500))]:
        if role == 'friendly':
            o = m.find(m.role(role).name)
            x, y = m.site('east base')
            o.x, o.y = x + offset[0], y + offset[1]
        else:
            m.put('AlliedMCV', 'east base', *offset, side='s1',
                  name='UNIT - Friendly ' + role, role=role)
    m.units.append(host_unit())
    m.put('CNVTeamsHost', 'east base', 250, 400, side='s1', role='teams host')
    m.ext = True
    m.facts['friendly nearest'] = 'second' if swapped else 'friendly'
    return m


MISSION = {'aifrnear': mission, 'aifrswap': lambda: mission(True)}
