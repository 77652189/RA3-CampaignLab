"""E157 ParkingPlaceBehavior: retail airport versus only removing Parking.

Prediction before bench: five scripted Apollo build presses, 12 seconds apart,
produce four aircraft at the retail 2x2 airport and none without Parking
(INFERRED). Counts are living produced aircraft, not internal parking slots.
No aircraft is placed or spawned. Both sides have power, money and a yard.
Near-airport counts independently measure location; they do not prove docking.
Return/slot reservation/release remain gaps. See work/re/e157_parking.md.

MEASURED 2026-11-15: a PASS, f194=1/0, f982=4/0 after five
presses. Swapped players: f196=1/0; production control agrees. The
team sortie prediction FAILED: near count stays 1 at f438..513, so the
later near=1 does not establish a return. Expectations remain unchanged.
E188 named object-world replays pass the three production samples. Admission
at order time and queue reservations are INFERRED; parking/return remain gaps.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted, square


def mission(swap=False):
    m = Mission(name='CampParkSwapE' if swap else 'CampParkE', map=probe_range, units=[],
                facts={'swap': swap})
    source = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedAirfield.xml').read_text(encoding='utf-8-sig')
    m.spawns.add('AlliedFighterAircraft')
    for tag, side, site in [('on', 'p1', 'base gun'), ('off', 's1', 'high gun')]:
        if swap:
            side = 's1' if side == 'p1' else 'p1'
        ident = 'CNVE157Airfield' + tag
        xml = source.replace('id="AlliedAirfield"', f'id="{ident}"', 1)
        if tag == 'off':
            xml, n = re.subn(r'<ParkingPlaceBehavior\b.*?</ParkingPlaceBehavior>', '', xml, flags=re.S)
            assert n == 1
        m.units.append(Unit(ident, xml))
        m.put(ident, site, side=side, role=tag + ' airport', name='E157 ' + tag + ' airport')
        m.put('AlliedConstructionYard', site, 0, 650, side=side, role=tag + ' yard')
        m.put('AlliedPowerPlant', site, 400, 0, side=side, role=tag + ' power')
        m.waypoint(tag + ' sortie', 'E157 ' + tag + ' sortie', site, 0, 850)
    return m


def check(m):
    t = Test()
    swap = m.facts['swap']
    presses = (2.,) if swap else (2., 14., 26., 38., 50.)
    t.counters = [('E157Frame', '帧数')]
    t.scripts = [Script('Test - E157 start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1'))] + [
        ('PLAYER_SET_MONEY', m.player(side), 20000) for side in ('p1', 's1')] + [
        ('SET_MILLISECOND_TIMER', 'E157 press ' + str(k), at)
        for k, at in enumerate(presses)] + ([
        ('SET_MILLISECOND_TIMER', 'E157 depart', 20.),
        ('SET_MILLISECOND_TIMER', 'E157 return', 35.)] if swap else [])),
        Script('Test - E157 frame', [], [('INCREMENT_COUNTER', 1, 'E157Frame')], once=False)]
    for tag, side in [('on', 'p1'), ('off', 's1')]:
        side = m.role(tag + ' airport').side
        counted('E157' + tag, '原机产出' if tag == 'on' else '删后产出', t,
                template='AlliedFighterAircraft', player=m.player(side))
        for k in range(len(presses)):
            t.scripts.append(Script(f'Test - E157 {tag} press {k}',
                [('TIMER_EXPIRED', 'E157 press ' + str(k))],
                [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(tag + ' airport').name,
                  'Command_ConstructAlliedFighterAircraft')]))
        airport = m.role(tag + ' airport')
        t.areas['E157 ' + tag + ' near'] = square(*m.site(airport.sites[0]), 250.)
    t.counters.append(('E157Near', '场区飞机'))
    t.scripts.append(Script('Test - E157 near clear', [], [('SET_COUNTER', 'E157Near', 0)], once=False))
    for tag, side, bit in [('on', 'p1', 1), ('off', 's1', 10)]:
        side = m.role(tag + ' airport').side
        for n in range(1, 7):
            t.scripts.append(Script(f'Test - E157 near {tag} {n}',
                [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player(side), 2, n,
                  'AlliedFighterAircraft', 'E157 ' + tag + ' near')],
                [('INCREMENT_COUNTER', bit * n, 'E157Near')], once=False))
    if swap:
        for tag in ('on', 'off'):
            team = m.team(m.role(tag + ' airport').side)
            t.scripts += [Script('Test - E157 depart ' + tag, [('TIMER_EXPIRED', 'E157 depart')],
                                [('MOVE_TEAM_TO', team, m.mark(tag + ' sortie'))]),
                          Script('Test - E157 return ' + tag, [('TIMER_EXPIRED', 'E157 return')],
                                [('TEAM_USE_COMMANDBUTTON_ABILITY', team, 'Command_ReturnToAirfield')])]
        t.expect = [('原机产出', 45, '==', 1, 50), ('删后产出', 45, '==', 0, 50),
                    ('场区飞机', 27, 'ever==', 0, 33), ('场区飞机', 45, 'ever==', 1, 50)]
    else:
        t.expect = [('原机产出', 60, '==', 4, 65), ('删后产出', 60, '==', 0, 65)]
    t.bench = [('bench_watch', dict(seconds=55 if swap else 70, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_parking': mission, 'engine_parkingswap': lambda: mission(swap=True)}
CHECKS = {name: {'a': check} for name in MISSION}
