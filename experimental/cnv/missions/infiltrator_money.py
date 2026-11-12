"""Retail economic infiltration, enemy and mutually allied refinery controls."""
from maps import probe_infmoney
from parts import Mission


def mission():
    m = Mission(name='CampInfMoney', map=probe_infmoney, units=[])
    m.spawns.add('AlliedMiner')
    for role, lane, side in (('enemy', 'base', 's1'), ('ally', 'high', 's2')):
        m.crew('Clean' + role, side)
        m.put('AlliedRefinery', role + ' refinery', side=side,
              role=role, name='Money refinery ' + role)
        m.put('AlliedInfiltrationInfantry', lane + ' gun', 0, -180,
              role=role + ' spy', name='Money spy ' + role)
    return m


MISSION = {'engine_infmon': mission}
