"""Engine unit test: 时空传送 (ADR 0019 layer 2; TeleportStoredObjectsUpdate) -- the timeline of the Chronosphere's
two steps (StoreObjectsSpecialPower picks up the people round a point, TeleportStoredObjectsSpecialPower sets the
landing, TeleportStoredObjectsUpdate carries them), read off the script cast (flag 8, no cooldown).

On the Niagara map the player's construction yard and, far off on the hawks' base, one copy of retail's Chronosphere
building per variant (CNV_TeleA..E: AlliedSuperWeapon with its TeleportStoredObjectsUpdate rewritten). At the west
field one Guardian tank and one Peacekeeper (60 aside), both NO_ATTACK, both inside the store radius 100 of waypoint
A; B is 450 east, C 400 south of B, all on the west field. In the 'Test Go' frame (one second in) the script fires the building's Select
power at A and, the same frame, its Spawn power at B (the second step = frame 0 of every reading). As soon as the
tank stands inside B's area it is sent on to C (every variant, as the control of c).

Update settings (Delay 2 s = 30 frames, insta-kill filter INFANTRY, GetObjectsCurrentlyAtStorePosition false):
  a  Initial 1.7 s, Delay 2 s, Fade 0 s, Telefrag NONE            model: infantry dies at 25, tank in B at 55
  b  Initial 0, Delay 0, Fade 0                                    same frame or the next?
  c  as a, Fade 2 s                                                (c - a) of the B-area count = the fade freeze (30)
  d  as a, Telefrag INSTANT_DEATH_TELEPORTER_ONLY, a parked p1 tank (NO_ATTACK) exactly at B
  e  as d, Telefrag HEALTH_SUBTRACTION

Counters (four lines), every one counted from 'Test Go' on:
  帧数   frames since Go
  第二行  1 x frames the Peacekeeper is not destroyed + 1000 x frames it is dying
  第三行  1 x frames the tank is inside A's area + 1000 x frames it is inside B's area (to the end, so it also
          holds the stay in B up to the move out)
  第四行  a-c: 1 x frames the tank is inside C's area; d: 1 x frames the parked tank is alive + 1000 x frames the
          Guardian is destroyed; e: 1 x frames the parked tank is below 100 % health + 1000 x the Guardian

Bench 11-06 (A round 53; the first row already ~27 frames in; runs CampTeleport{A..E}_mcp_1106_0650..0658):
  a  26: 26 26 0 | 41: 15026 41 0 | 56: 30026 56 0 | 71: 45026 15056 0 | 87: 61026 19056 0 | 147: 121026 19056 27
     -> infantry dead from 26, the tank in B from 56, drives off after 19 frames, in C from 120
  b  28: 27001 19002 0 | 41: 40001 19002 0 | 132: 127001 19002 66 | 147: 127001 19002 81
     -> 0 s + 0 s: dead from 1, in B from 2; the body gone after 127 dying frames (8.5 s chopped)
  c  as a to 71; then 86: 60026 30056 | 116: 90026 48056 -> lands at 56 as a, stays 48 frames (29 more than a)
  d  28: 2026 28 28 | 57: 31026 56 1057 | 148: 122026 56 92148 -> the teleported tank dies at 56, the parked lives
  e  27: 1026 27 0 | 54: 28026 54 0 | 70: 44026 56 0 | 146: 120026 56 0 -> leaves A at 56, never in B, neither
     ever hurt and alive: both die
Against the model (RA3-EngineModel teleport.py, tests/test_objects_bench.py "teleport"): every row before the tank
drives agrees; one strict xfail, not the teleport's own: the body lasts 128 in the model (ceil of 127.5).
"""
import os
import re

import labpaths
import resources
from maps import niagara
from parts import Mission, Script, Test, Unit, square

SAGE = os.path.join(labpaths.SDK3, 'SageXML')
RUN = 8.0
TANK, INF = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
SELECT, SPAWN = 'SpecialPowerChronosphereObjectSelect', 'SpecialPowerChronosphereObjectSpawn'
WEST, A_AT, B_AT, C_AT = 'west field', (-250.0, 100.0), (200.0, 100.0), (200.0, -300.0)
HOME = 'east base'
VARIANTS = {   # letter: (initial s, delay s, fade s, telefrag)
    'a': (1.7, 2.0, 0.0, 'NONE'),
    'b': (0.0, 0.0, 0.0, 'NONE'),
    'c': (1.7, 2.0, 2.0, 'NONE'),
    'd': (1.7, 2.0, 0.0, 'INSTANT_DEATH_TELEPORTER_ONLY'),
    'e': (1.7, 2.0, 0.0, 'HEALTH_SUBTRACTION'),
}


def _id(w):
    return f'CNV_Tele{w.upper()}'


def _n(part):
    return f'UNIT - CNV Teleport {part}'


def teleporter(w):
    """Retail's Chronosphere building under CNV_Tele<W>, its TeleportStoredObjectsUpdate rewritten to variant w."""
    ini, delay, fade, frag = VARIANTS[w]
    x = open(os.path.join(SAGE, 'Allied', 'Structures', 'AlliedSuperWeapon.xml'), encoding='utf-8').read()
    assert x.count('id="AlliedSuperWeapon"') == 1
    x = x.replace('id="AlliedSuperWeapon"', f'id="{_id(w)}"', 1)
    upd = f'''<TeleportStoredObjectsUpdate
				id="ModuleTag_CloneStoredObjectsSpecialPowerUpdate"
				SpecialPowerTemplate="{SPAWN}"
				GetObjectsCurrentlyAtStorePosition="false"
				Telefrag="{frag}"
				TargetFX="FX_None"
				InitialDelayTime="{ini:g}s"
				FadeInTime="{fade:g}s"
				DelayTime="{delay:g}s"
				DisabledTypesToProcess="USER_PARALYZED EMP HELD PARALYZED UNDERPOWERED TEMPORARILY_BUSY">
				<InstaKillObjectFilter Rule="ANY" Include="INFANTRY" />
				<CollidesWithOnTeleport Rule="ANY" Include="INFANTRY STRUCTURE VEHICLE"
					Exclude="BRIDGE BRIDGE_SEGMENT BRIDGE_ENDCAP" />
			</TeleportStoredObjectsUpdate>'''
    x, k = re.subn(r'<TeleportStoredObjectsUpdate\b.*?</TeleportStoredObjectsUpdate>', lambda _: upd, x, flags=re.S)
    assert k == 1, k
    return Unit(_id(w), x, names=dict(unit=_id(w)), abilities=dict(select=SELECT, spawn=SPAWN),
                what=f'Chronosphere building, store radius 100: initial {ini:g} s, delay {delay:g} s, fade {fade:g} s, '
                     f'Telefrag {frag}, insta-kill INFANTRY',
                params=dict(initial=ini, delay=delay, fade=fade, telefrag=frag))


def mission(w='a'):
    """One building per build (the contract lets a power belong to one template): build engine_teleport is a, the
    others engine_teleport_<w> (mod CampTeleport<W>)."""
    m = Mission(name='CampTeleport', map=resources.measured(niagara), units=[teleporter(w)], facts={})
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    m.put(_id(w), HOME, 0.0, 0.0, angle=0.0, role=f'tele {w}', name=_n(f'Tele {w}'))
    m.put(TANK, WEST, *A_AT, angle=0.0, role='tank', name=_n('Tank'))
    m.put(INF, WEST, A_AT[0] - 60.0, A_AT[1], angle=0.0, role='inf', name=_n('Inf'))
    m.put(TANK, WEST, *B_AT, angle=0.0, role='parked', name=_n('Parked'))
    return m


def teleport_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    x, y = m.site(WEST)[:2]

    def pt(d):
        return (x + d[0], y + d[1])
    t.waypoints['Test Tele A'], t.waypoints['Test Tele B'], t.waypoints['Test Tele C'] = pt(A_AT), pt(B_AT), pt(C_AT)
    t.areas['Test Tele A'] = square(*pt(A_AT), 150.0)
    t.areas['Test Tele B'] = square(*pt(B_AT), 80.0)
    t.areas['Test Tele C'] = square(*pt(C_AT), 80.0)
    tank, inf, parked, tele = _n('Tank'), _n('Inf'), _n('Parked'), _n(f'Tele {which}')
    start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 2000), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    if which not in 'de':
        start.append(('NAMED_DELETE', parked))
    start += [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1)
              for u in (tank, inf) + ((parked,) if which in 'de' else ())]
    t.scripts.append(Script('Test - start', [], start))
    go = [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', tele, m.ability(f'tele {which}', 'select'), 'Test Tele A'),
          ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', tele, m.ability(f'tele {which}', 'spawn'), 'Test Tele B')]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    t.counters.append(('CNV_Teleport_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Teleport_Frames')], once=False))
    t.scripts.append(Script('Test - move on', [going, ('NAMED_INSIDE_AREA', tank, 'Test Tele B')],
                            [('MOVE_NAMED_UNIT_TO', tank, 'Test Tele C')]))

    def inside(u, a):
        return ('NAMED_INSIDE_AREA', u, a)
    if which in 'de':
        def hurt(u):
            return ('UNIT_HEALTH', u, 0, 100)           # health below 100 %
        r4 = ([(('NAMED_NOT_DESTROYED', parked), 1), (('NAMED_DESTROYED', tank), 1000)] if which == 'd'
              else [(hurt(parked), 1), (hurt(tank), 1000)])
    else:
        r4 = [(inside(tank, 'Test Tele C'), 1)]
    rows = {2: [(('NAMED_NOT_DESTROYED', inf), 1), (('NAMED_DYING', inf), 1000)],
            3: [(inside(tank, 'Test Tele A'), 1), (inside(tank, 'Test Tele B'), 1000)],
            4: r4}
    for k, label in ((2, '第二行'), (3, '第三行'), (4, '第四行')):
        t.counters.append((f'CNV_Teleport_Row{k}', label))
        for j, (cond, step) in enumerate(rows[k]):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_Teleport_Row{k}')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


def _build(w):
    return 'engine_teleport' if w == 'a' else f'engine_teleport_{w}'


MISSION = {_build(w): (lambda w=w: mission(w)) for w in VARIANTS}
CHECKS = {_build(w): {w: (lambda m, w=w: teleport_test(m, w))} for w in VARIANTS}
