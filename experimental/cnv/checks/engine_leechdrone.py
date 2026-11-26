"""E244: the Hammer's leeched carrier drone -- ObjectCreationUpgrade and SlaveWatcherBehavior (retail: both only on
SovietAntiVehicleVehicleTech1, the leech that kills an Aircraft Carrier gets Leech_AircraftCarrier_Upgrade).

The upgrade is given by script (NAMED_RECEIVE_UPGRADE) at 1 s and again at 7 s; the Hammer holds fire throughout; at
4 s an enemy Bullfrog (air only) is teleported in beside it to shoot the drone down, and deleted at 6 s. (A first try
teleported the Hammer away and killed p1's all in an area round the drone: the drone lived, so UNIT_KILL_ALL_IN_AREA
passes a slave by -- bench 11-25 CampLeechOnA: 机 1, 升 11 from s1 to s13; 型 0, a template count misses the drone.)
机 = p1's aircraft (KindOf AIRCRAFT, the drone the only one), 型 = the drone's template count, 升 = Hammer has the
upgrade 1 + Hammer alive 10.

Prediction from the data (before the bench): on 机 0 / 1 (s2-4) / 0 / 1 (s8-), 升 10 / 11 / 10 (the dead slave takes
the upgrade back) / 11; nowatch (SlaveWatcherBehavior taken out) 升 stays 11 after s4 and the second grant is a no-op,
机 0 from s5; nocreate (ObjectCreationUpgrade taken out) 机 0 throughout, 升 11 from s2.

Bench 11-25 (CampLeechOnA_mcp_1125_141339, NwA 141600, NcA 141814): on and nowatch 机 1, 升 11 s1-s13 -- the drone
made, the second grant made none, but the Bullfrog never shot it down, so SlaveWatcherBehavior is still unmeasured;
nocreate 机 0. Readings: engine_leechdrone.readings.toml.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Script, Test, counted, kindof, square
from checks import engine_scripts8 as s8

HAMMER, DRONE, UP = 'SovietAntiVehicleVehicleTech1', 'AlliedAttackDrone_Leeched', 'Leech_AircraftCarrier_Upgrade'
NAME, FROG = 'UNIT - E244 Hammer', 'UNIT - E244 Frog'
AA = [f'UNIT - E245 AA{i}' for i in range(4)]       # flak troopers (YES: 25 FLAK at the air, reach 300)
TAG = {'on': 'On', 'nowatch': 'Nw', 'nocreate': 'Nc'}      # mod names stay within 15 characters
CUT = {'nowatch': r'<SlaveWatcherBehavior\b[^>]*/>',
       'nocreate': r'<ObjectCreationUpgrade\b.*?</ObjectCreationUpgrade>'}


def mission(arm='on'):
    m = Mission(name='CampLeech' + TAG[arm], map=probe_range, facts={'arm': arm})
    source = (Path(labpaths.SDK3) / f'SageXML/Soviet/Units/{HAMMER}.xml').read_text(encoding='utf-8-sig')
    if arm in CUT:
        source, count = re.subn(CUT[arm], '', source, flags=re.S)
        assert count == 1
    m.assets.append(('E244Hammer.xml', source, f'GameObject:{HAMMER}'))
    m.replaces.append(f'GameObject:{HAMMER}')
    m.spawns |= {HAMMER, DRONE}
    m.put(HAMMER, 'high gun', role='hammer', name=NAME)
    m.put('SovietAntiAirShip', 'order gun', role='frog', side='s2', name=FROG)
    for i, name in enumerate(AA):                   # 1500 from the Hammer: idle in check a
        m.put('SovietAntiVehicleInfantry', 'order gun', 20.0 * i, role=f'aa{i}', side='s2', name=name)
    m.waypoint('near', 'E244 near', 'high gun', 150.0)
    return m


def _counters(t, m, p1, grant, shooters, gone, again):
    t.areas['E244 All'] = square(2500.0, 2500.0, 2700.0)
    t.scripts.append(Script('Test - E244 hold', [], [('UNIT_SET_STANCE', NAME, 3), ('MAP_REVEAL_ALL_PERM', p1)]))
    s8.at(t, 'grant', 1.0, grant)
    s8.at(t, 'frog', 4.0, [('UNIT_TELEPORT_TO_WAYPOINT', a, m.mark('near')) for a in shooters])
    s8.at(t, 'gone', gone, [('NAMED_DELETE', a) for a in shooters])
    s8.at(t, 'again', again, grant)
    counted('E244Air', '机', t, kind=kindof('AIRCRAFT'), area='E244 All', player=p1, most=4)
    counted('E244Type', '型', t, template=DRONE, player=p1)
    s8.total(t, 'E244Up', '升', [(1, ('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', p1, 1, UP)),
                                 (10, ('NAMED_NOT_DESTROYED', NAME))])


def check(m):
    t = Test()
    p1 = m.player('p1')
    _counters(t, m, p1, [('NAMED_RECEIVE_UPGRADE', UP, NAME)], [FROG], 6.0, 7.0)
    arm = m.facts['arm']
    made = 0 if arm == 'nocreate' else 1        # bench 11-25: the Bullfrog never downs the drone (see above)
    t.expect = [('机', 3, '==', made), ('机', 10, '==', made), ('升', 6, '==', 11)]
    s8.watch(t, 12.0)
    return t


def check_flak(m):
    """E245: four flak troopers (not the Bullfrog, which never acquires when idle) are teleported in at 4 s, deleted
    at 8 s, the upgrade given again at 9 s; the Hammer is UNATTACKABLE (without it the bench troopers shot the Hammer
    and the drone lived: CampLeechOnB_mcp_1125_183944 -- the simulator shot the drone; a target-choice gap, not here).
    Bench 11-25 (CampLeechOnB_mcp_1125_184445, NwB 184320): on 机 1 -> 0 at s4, 升 11 -> 10, then 1 / 11 from s8;
    nowatch 机 0 from s4, 升 11 throughout (the simulator downs the drone at s7)."""
    t = Test()
    p1 = m.player('p1')
    _counters(t, m, p1, [('NAMED_RECEIVE_UPGRADE', UP, NAME)], AA, 8.0, 9.0)
    # bench 11-25 CampLeechOnB_mcp_1125_183944 without this: the troopers shot at the Hammer, the drone lived
    t.scripts.append(Script('Test - E245 shield', [], [('UNIT_CHANGE_OBJECT_STATUS', NAME, 'UNATTACKABLE', 1)]))
    t.expect = [('机', 11, '==', int(m.facts['arm'] == 'on')), ('升', 11, '==', 11)]   # the dip: the readings
    s8.watch(t, 13.0)
    return t


MISSION = {f'engine_leechdrone_{arm}': (lambda arm=arm: mission(arm)) for arm in ('on', 'nowatch', 'nocreate')}
CHECKS = {name: {'a': check, 'b': check_flak} for name in MISSION}
CONTROLS = {'engine_leechdrone_nowatch': 'engine_leechdrone_on', 'engine_leechdrone_nocreate': 'engine_leechdrone_on'}
