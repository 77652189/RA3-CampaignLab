"""Retail-campaign conditions, batch 6 (round 241, written; NOT YET ON THE BENCH): PLAYER_TRIGGERED_SPECIAL_POWER_FROM_
NAMED (5 uses: a02 (Player_1, specialpower_timebelt, the commando), j03 (Player_1, specialpower_mechakingshockwave,
o_executioner), s03 (Player_1, specialpower_ejectpassengers, three transports)), PLAYER_TRIGGERED_SPECIAL_POWER_IN_AREA
(4, j07: (Player_1 / Player_2, specialpowernanoswarmhive, area_relay_01 / _02)) and TEAM_CAN_PATH_TO_WAYPOINT (4, j07:
NOT (Allies02/Bridge_*, wp_jinzatsu_goto_p1) once a bridge is down -> the team walks off). Mission on maps/probe_air.py
(its trench: water x ~2160..2440, y 3050..3550, ground units go round it), every place absolute; the start (1250, 2500)
and the lanes' S ends (x 1700) clear. No enemies.

  all  casts: the player's two JapanMechaKing A (3500, 2200) / B (4500, 2200), Tanya (3500, 3000), a nanoswarm hive
       (JapanSuperWeapon) H at (4500, 3300) inside area 'zone H' (300 round it); area 'zone Q' (250 round Q1 (3500,
       3550)), Q2 (4000, 2700) outside both. NAMED_USE_COMMANDBUTTON_ABILITY A's shockwave at 2 s, B's at 6 s, Tanya's
       time belt at 10 s; NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT H at Q1 14 s, at Q2 18 s.
       名 (adds its weight every frame its reader holds; the readers in this order) = 1 FROM_NAMED(p1, shockwave, A)
         2 (.., B) 16 (.., A) again 4 PLAYER_TRIGGERED(p1, shockwave) 8 FROM_NAMED(p1, timebelt, Tanya): this last
         script off until 13 s (ENABLE_SCRIPT), 3 s after the belt
       区 = 1 IN_AREA(p1, nanoswarm, zone Q) 2 (.., zone H) 4 PLAYER_TRIGGERED(p1, nanoswarm) 8 FROM_NAMED(p1,
         nanoswarm, H)
       paths: crews G (two Guardians at (800, 3300 / 3450)), A (a Bullfrog at (900, 3800)), M (a Guardian and a
       Bullfrog at (700 / 900, 4600)), K (a Guardian at (1100, 4600), NAMED_KILL at 8 s -> empty); M's Bullfrog
       NAMED_KILL at 16 s. Waypoints L (1300, 4000) land, W (2300, 3300) in the trench's water.
       路 (every frame) = 1 TEAM_CAN_PATH_TO_WAYPOINT(G, L) 2 (G, W) 4 (A, W) 8 (M, W) 16 (K, L)
  [prediction from the data. Generals' ScriptEngine keeps a per-player LIST of triggered powers (power, source id):
   isSpecialPowerTriggered(removeFromList TRUE) -- the FIRST condition that matches TAKES the entry, and an entry no
   one reads stays until one does; FROM_NAMED with the named unit dead is false. The simulator today (sim.py
   'PLAYER_TRIGGERED_SPECIAL_POWER', bench 11-09 pfire 施放数 1) lets every reader see a cast in the next frame only.
   The two read apart: 名 H1 (all see one frame) 21 after A, 27 after B, 27 to the end (the late reader never);
   H2 (taken) 1, 3, then 11 at ~13 s (the late reader takes the belt still listed). 区 by where IN_AREA looks, T the
   cast's point / C the caster's place: H1T 13 then 25, H1C 14 then 28, H2T 1 then 5, H2C 2 then 4. Shockwave casts
   are recorded when the weapon fires (after the unpack), not at the press: the steps come a few frames after the
   timers. 路: from the routing grid with the goal snapped to its nearest open cell (simai.Brain.reach, D152) 1 + 2 +
   4 + 8 = 15 to 8 s, 15 after K dies (16 never: an empty team has no one to path), 7 once M's Bullfrog dies if any
   member counts (W snaps to the bank for a Guardian, so 2 / 8 hold); without the snap (the water cell is no Guardian's)
   1 + 4 + 8 = 13, 5 after 16 s.]
"""
from maps import probe_air
from parts import Mission, Script, Test
import checks.engine_scripts8 as s8

KING, TANYA, HIVE, TANK, FROG = ('JapanMechaKing', 'AlliedCommandoTech1', 'JapanSuperWeapon',
                                 'AlliedAntiVehicleVehicleTech1', 'SovietAntiAirShip')
SHOCK, BELT, NANO = 'SpecialPower_MechaKingShockwave', 'SpecialPower_TimeBelt', 'SpecialPowerNanoSwarmHive'
O = (4000.0, 1500.0)                            # probe_air's 'air B'
UNITS = {'king a': (KING, (3500.0, 2200.0)), 'king b': (KING, (4500.0, 2200.0)), 'tanya': (TANYA, (3500.0, 3000.0)),
         'hive': (HIVE, (4500.0, 3300.0)),
         'g1': (TANK, (800.0, 3300.0)), 'g2': (TANK, (800.0, 3450.0)), 'a1': (FROG, (900.0, 3800.0)),
         'm1': (TANK, (700.0, 4600.0)), 'm2': (FROG, (900.0, 4600.0)), 'k1': (TANK, (1100.0, 4600.0))}
CREWS = {'G': ('g1', 'g2'), 'A': ('a1',), 'M': ('m1', 'm2'), 'K': ('k1',)}
POINTS = {'q1': (3500.0, 3550.0), 'q2': (4000.0, 2700.0), 'l': (1300.0, 4000.0), 'w': (2300.0, 3300.0)}
RUN = 30.0


def _n(part):
    return f'UNIT - CNV Cast {part.title()}'


def _square(x, y, half):
    return [(x - half, y - half), (x + half, y - half), (x + half, y + half), (x - half, y + half)]


def mission():
    m = Mission(name='CampCast', map=probe_air, units=[], facts={})
    m.spawns |= {KING, TANYA, TANK, FROG}
    for role, (template, (x, y)) in UNITS.items():
        m.put(template, 'air B', x - O[0], y - O[1], side='p1', angle=0.0, name=_n(role), role=role)
    for k, (x, y) in POINTS.items():
        m.waypoint(k, f'Test Cast {k.title()}', 'air B', x - O[0], y - O[1])
    m.facts.update(zones={'Test Cast Zone Q': _square(*POINTS['q1'], 250.0),
                          'Test Cast Zone H': _square(*UNITS['hive'][1], 300.0)})
    return m


def _seen(t, counter, label, parts):
    """counter += weight every frame a reader holds (never reset), one script per reader, in this order."""
    t.counters.append((counter, label))
    t.scripts += [Script(f'Test - {counter} {k}', when, [('INCREMENT_COUNTER', w, counter)], once=False,
                         active=active) for k, (w, when, active) in enumerate(parts)]


def all_(m):
    t = Test()
    p1 = m.player()
    n = {r: m.role(r).name for r in UNITS}
    wp = {k: m.mark(k) for k in POINTS}
    t.areas.update(m.facts['zones'])
    zq, zh = 'Test Cast Zone Q', 'Test Cast Zone H'
    crew = {k: m.crew(f'Cast{k}') for k in CREWS}
    t.scripts.append(Script('Test - Cast start', [], [('MAP_REVEAL_ALL_PERM', p1)] + [
        ('UNIT_SET_TEAM', n[r], crew[k]) for k, rs in CREWS.items() for r in rs]))
    s8.at(t, 'a', 2.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', n['king a'], 'Command_ActivateMechaKingShockwave')])
    s8.at(t, 'b', 6.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', n['king b'], 'Command_ActivateMechaKingShockwave')])
    s8.at(t, 'k', 8.0, [('NAMED_KILL', n['k1'])])
    s8.at(t, 'belt', 10.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', n['tanya'], 'Command_TimeBeltSpecialPower')])
    late = 'Test - CNV_Cast_Named 4'
    s8.at(t, 'late', 13.0, [('ENABLE_SCRIPT', late)])
    s8.at(t, 'q1', 14.0, [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', n['hive'], NANO, wp['q1'])])
    s8.at(t, 'm', 16.0, [('NAMED_KILL', n['m2'])])
    s8.at(t, 'q2', 18.0, [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', n['hive'], NANO, wp['q2'])])
    f, a = 'PLAYER_TRIGGERED_SPECIAL_POWER_FROM_NAMED', 'PLAYER_TRIGGERED_SPECIAL_POWER_IN_AREA'
    _seen(t, 'CNV_Cast_Named', '名', [
        (1, [(f, p1, SHOCK, n['king a'])], True), (2, [(f, p1, SHOCK, n['king b'])], True),
        (16, [(f, p1, SHOCK, n['king a'])], True), (4, [('PLAYER_TRIGGERED_SPECIAL_POWER', p1, SHOCK)], True),
        (8, [(f, p1, BELT, n['tanya'])], False)])
    _seen(t, 'CNV_Cast_Area', '区', [
        (1, [(a, p1, NANO, zq)], True), (2, [(a, p1, NANO, zh)], True),
        (4, [('PLAYER_TRIGGERED_SPECIAL_POWER', p1, NANO)], True), (8, [(f, p1, NANO, n['hive'])], True)])
    c = 'TEAM_CAN_PATH_TO_WAYPOINT'
    s8.total(t, 'CNV_Cast_Path', '路', [(1, (c, crew['G'], wp['l'])), (2, (c, crew['G'], wp['w'])),
                                       (4, (c, crew['A'], wp['w'])), (8, (c, crew['M'], wp['w'])),
                                       (16, (c, crew['K'], wp['l']))])
    t.expect = [('名', RUN - 1, '>=', 1), ('区', RUN - 1, '>=', 1)]
    s8.watch(t, RUN, 0.5)
    return t


MISSION = {'engine_cast': mission}
CHECKS = {'engine_cast': {'all': all_}}
