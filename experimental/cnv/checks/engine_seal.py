"""Engine unit tests: what a unit does when it has NO way (docs/engine/pathing.md; engine line, 2026-11-08). The
player's own structures made in the run (SovietBunker stands in for the ice wall) close a ring round it, the goal /
target is outside. Map: maps/probe_block.py (the 'seal *' sites on open ground, goal 600 east of the start).
Ring: RING bunkers on a circle of radius R round the start, made at MAKE s (nothing between them).

move: an IFV and a peacekeeper sealed in, ordered by move at ORDER s to the goal 600 east. Counters per unit: sum of
  1 = left the start's 60, 2 = been at the east wall's inside, 10 = at the goal (0: never left the start).
idle: a peacekeeper alone in the ring, no order, an unarmed enemy MCV 210 east (in sight, out of range; 60 beyond the
  ring). Counters: the peacekeeper as above (1, 2), the MCV's health. idle_open: the same, no ring (the control).
spawn: a power plant of the player's stands; MAKE s: an IFV and a peacekeeper made at its centre; ORDER s: move to
  the goal 600 east. Counters per unit: 1 = out of the centre's 40, 2 = out of 110, 10 = at the goal.

(Move's counters also add 4 = in the strip 60..80 east of the start, 8 / 16 / 32 = in the north / south / west part of
the ring, 100 = at the goal. The idle_open check is named 'open': a mod name with an underscore crashes.)

Read (测, 2026-11-08):
move -- the ring is made s1, the order s4. The peacekeeper: 7 at s4 (out of the start, mid strip, east wall's inside)
  and it stays there to s61; never 100 (no way through, no way round: it stands at the east wall). The IFV: 17 (left
  the start, sits in the south part of the ring), never at the east wall, never at the goal to s61.
idle -- the peacekeeper 0 and the enemy MCV 100 for 61 s: it neither moves nor fires (the ring is up from s1).
open (no ring) -- the peacekeeper 0 too (never leaves the start's 60), the MCV 99 at s1 .. 88 at s61, 1 % per ~5 s:
  it fires from where it stands at 210 (an MCV is big; its edge is nearer), no walk.
spawn -- a peacekeeper and an IFV made at the power plant's centre (s1): not out of the centre's 40 at s1 (0 0); the IFV
  out of 110 at s4 (3), the soldier out of 40 at s4 (1), out of 110 at s7 (3); goal: IFV s10, soldier s13. Units made
  inside a building come out of it by themselves and walk the 600 east.
cut -- open's set-up, a closed box of field-0 ground (40 thick, 100 inside, no structure) round the MCV: the peacekeeper
  0 (stands), the MCV 99 at s1 .. 88 at s61, the same 1 % per ~5 s as open: terrain between does NOT stop the fire.
row -- open's set-up, 11 player bunkers in a row 105 east of the soldier (330 long, ends open), made s1: the peacekeeper 0
  (never leaves, never goes round), the MCV 99 from s1 to s61 (one hit at most before the row stood): a structure in
  the line stops the fire. So 'sealed in, no fire' is the structures blocking the shot, not 'no way, no target'.
erow -- row's set-up, the 11 bunkers the ENEMY's (s1): the peacekeeper 0 (stands), the MCV 99 and the middle bunker (Row
  Wall 5) 100, both flat from s1 to s61: it fires at neither the MCV nor the bunkers.
tank -- a Guardian (AttackRange 150, LINE_OF_SIGHT flag) at the lane's start, the MCV 130 east, 11 player bunkers 65 east:
  the tank 0 (stands), the MCV 100 for s1..s61.  topen (control, no row): the tank 0, the MCV 98 s1, 96 s4-s10, 98 s13,
  99 s16-s19, 100 from s22 (hit by 4 % at most, then back up: NOT a clean control -- the cannon should hit harder;
  unexplained, the MCV may repair itself).
arty (V4 launcher range 500, min 200, no LINE_OF_SIGHT flag; the Athena unit's only own weapon is a 500 / min 200
  targeter, so V4 stands in; MCV 350 east, the player's row 200 east) -- the V4 0, the MCV 100 s1..s61.  artyhp (the
  same, the middle bunker counted): the bunker 100 too.  artyo (no row, the control): the MCV 100 s1..s62 as well --
  the idle V4 does not fire at all, the row is not why (not split: unseen, or takes nothing by itself).
attack -- the soldier 1 at s4 (left the start), 5 from s7 (north of the row's end, never east of it); the MCV 99 s1-s7,
  97 s10, 96 s13 ... 86 s37, 85 s40-s61: told to attack, it walks round the row's end and fires from there.
aa (IFV, a hovering Twinblade with NO_ATTACK 200 east, the row 100 east) and aaopen (no row): the same readings, 79 s1,
  50 s4, 16 s7, 4 from s10: the row does not stop a shot at a target in the air.
(All four measured 2026-11-08 06:41-06:59; arty / attack / aa / aaopen had failed on a lost Direct3D device before.)
(A first spawn run read 3 3 at s1: a named unit that does not exist yet counts as 'outside' an area; the scripts now
also ask it to be inside a big area.)
"""
import math

from maps import probe_block
from parts import Mission, Script, Test, counted, square

IFV = 'AlliedAntiAirVehicleTech1'
FOOT = 'AlliedAntiInfantryInfantry'
WALL = 'SovietBunker'
ENEMY = 'AlliedMCV'
TANK, V4, HELI = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiStructureVehicle', 'SovietAntiGroundAircraft'
BUILDING = 'AlliedPowerPlant'
RING, R = 36, 150.0
MAKE, ORDER = 1.0, 4.0


def _ring(m, t, site):
    """The script that makes the ring round `site` when MAKE has run out."""
    x0, y0 = m.site(site)
    make = []
    for k in range(RING):
        a = 2 * math.pi * k / RING
        wp = f'Test Seal {site.title()} Ring {k}'
        t.waypoints[wp] = (x0 + R * math.cos(a), y0 + R * math.sin(a))
        make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Seal {site.title()} Ring {k}', WALL,
                     m.team('p1'), wp))
    t.scripts.append(Script(f'Test - seal ring {site}', [('TIMER_EXPIRED', 'Test Seal Make')], make))


def _timers(t):
    t.scripts.append(Script('Test - seal timers', [], [('SET_MILLISECOND_TIMER', 'Test Seal Make', MAKE),
                                                       ('SET_MILLISECOND_TIMER', 'Test Seal Order', ORDER)]))


def _order(m, t, site, names, crew):
    wp = f'Test Seal {site.title()} Goal'
    t.waypoints[wp] = m.site(f'{site} goal')
    t.scripts.append(Script(f'Test - seal go {site}', [('TIMER_EXPIRED', 'Test Seal Order')],
                            m.order('move', names, wp, crew=crew)))


def _score(m, t, counter, label, unit, parts):
    """parts: [(site-relative area, n, 'out' | 'in')]: once a unit is out of / in the area, the counter gets n."""
    t.counters.append((counter, label))
    for k, (area, n, how) in enumerate(parts):
        t.scripts.append(Script(f'Test - {counter} {k}',
                                [('NAMED_OUTSIDE_AREA' if how == 'out' else 'NAMED_INSIDE_AREA', unit, area)],
                                [('INCREMENT_COUNTER', n, counter)], once=True))


def _areas(m, t, site, tag, root=True, goal=True):
    x, y = m.site(site)
    out = []
    t.areas[f'Test Seal {tag} Start'] = square(x, y, 60.0)
    out.append((f'Test Seal {tag} Start', 1, 'out'))
    if root:
        for nm, n, (ax0, ay0, ax1, ay1) in (('North', 8, (-140, 60, 140, 140)), ('South', 16, (-140, -140, 140, -60)),
                                            ('West', 32, (-140, -60, -60, 60))):
            t.areas[f'Test Seal {tag} {nm}'] = [(x + ax0, y + ay0), (x + ax1, y + ay0), (x + ax1, y + ay1),
                                                (x + ax0, y + ay1)]
            out.append((f'Test Seal {tag} {nm}', n, 'in'))
        t.areas[f'Test Seal {tag} Mid'] = [(x + 60, y - 70), (x + 80, y - 70), (x + 80, y + 70), (x + 60, y + 70)]
        out.append((f'Test Seal {tag} Mid', 4, 'in'))
        t.areas[f'Test Seal {tag} Root'] = [(x + 80, y - 70), (x + 140, y - 70), (x + 140, y + 70), (x + 80, y + 70)]
        out.append((f'Test Seal {tag} Root', 2, 'in'))
    if goal:
        gx, gy = m.site(f'{site} goal')
        t.areas[f'Test Seal {tag} Goal'] = square(gx, gy, 100.0)
        out.append((f'Test Seal {tag} Goal', 100, 'in'))
    return out


def mission():
    m = Mission(name='CampSeal', map=probe_block, facts={})
    m.put(IFV, 'seal move', -20.0, 0.0, role='move ifv', name='UNIT - CNV Seal Move Ifv')
    m.put(FOOT, 'seal move', 20.0, 0.0, role='move foot', name='UNIT - CNV Seal Move Foot')
    for lane in ('idle', 'idle open', 'cut', 'row'):
        k = lane.title()
        m.put(FOOT, f'seal {lane}', role=f'{lane} foot', name=f'UNIT - CNV Seal {k} Foot')
        m.put(ENEMY, f'seal {lane}', 210.0, 0.0, side='s1', angle=90.0, role=f'{lane} enemy',
              name=f'UNIT - CNV Seal {k} Enemy')
    for lane, kind, dx in (('erow', FOOT, 210.0), ('attack', FOOT, 210.0), ('tank', TANK, 130.0),
                           ('tankopen', TANK, 130.0), ('arty', V4, 350.0)):
        k = lane.title()
        m.put(kind, f'seal {lane}', role=f'{lane} foot', name=f'UNIT - CNV Seal {k} Foot')
        m.put(ENEMY, f'seal {lane}', dx, 0.0, side='s1', angle=90.0, role=f'{lane} enemy', name=f'UNIT - CNV Seal {k} Enemy')
    for lane in ('aa', 'aaopen'):
        k = lane.title()
        m.put(IFV, f'seal {lane}', role=f'{lane} foot', name=f'UNIT - CNV Seal {k} Foot')
        m.put(HELI, f'seal {lane}', 200.0, 0.0, side='s1', role=f'{lane} enemy', name=f'UNIT - CNV Seal {k} Enemy')
    m.put(BUILDING, 'seal spawn', role='spawn building', name='UNIT - CNV Seal Spawn Building')
    for lane, (bx, by), (px, py), (us, them) in (('ebld', (120.0, 0.0), (-150.0, 0.0), ('s1', 'p1')),
                                                 ('ebldam', (500.0, 100.0), (500.0, -120.0), ('s1', 'p1')),
                                                 ('pam', (500.0, 100.0), (500.0, -120.0), ('p1', 's1'))):
        k = lane.title()
        m.put(FOOT, f'seal {lane}', side=us, role=f'{lane} foot', name=f'UNIT - CNV Seal {k} Foot')
        m.put(WALL, f'seal {lane}', bx, by, side=them, role=f'{lane} bunker', name=f'UNIT - CNV Seal {k} Bunker')
        m.put(BUILDING, f'seal {lane}', px, py, side=them, role=f'{lane} plant', name=f'UNIT - CNV Seal {k} Plant')
    return m


def move(m):
    t = Test()
    _timers(t)
    _ring(m, t, 'seal move')
    for role, tag, counter, label in (('move ifv', 'Ifv', 'CNV_Seal_Ifv', '车'), ('move foot', 'Foot', 'CNV_Seal_Foot', '兵')):
        unit = m.role(role).name
        _score(m, t, counter, label, unit, _areas(m, t, 'seal move', f'Move {tag}'))
    _order(m, t, 'seal move', [m.role('move ifv').name, m.role('move foot').name], 'SealMove')
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=2))]
    t.expect = []
    return t


def _idle(m, lane, ring):
    t = Test()
    site = f'seal {lane}'
    if ring:
        _timers(t)
        _ring(m, t, site)
    _score(m, t, 'CNV_Seal_Foot', '兵', m.role(f'{lane} foot').name, _areas(m, t, site, lane.title(), goal=False,
                                                                       root=lane in ('idle', 'idle open')))
    counted('CNV_Seal_Hp', '敌车血量', t, health=m.role(f'{lane} enemy').name)
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=2))]
    t.expect = []
    return t


def idle(m):
    return _idle(m, 'idle', True)


def idle_open(m):
    return _idle(m, 'idle open', False)


def cut(m):
    """open's set-up with a closed ring of field-0 ground (no structure) round the MCV, between it and the soldier."""
    return _idle(m, 'cut', False)


def row(m):
    """open's set-up with a row of the player's bunkers (ROW_N, spacing 30, 105 east of the start, centred on its y)
    made at MAKE s: the ends are open (the row is 330 long), a soldier can walk round. Counters: 1 = left the start's
    60, 2 = east of the row, 4 / 8 = north / south of the row's end."""
    t = _idle(m, 'row', False)
    _timers(t)
    x0, y0 = m.site('seal row')
    make = []
    for k in range(11):
        wp = f'Test Seal Row {k}'
        t.waypoints[wp] = (x0 + 105.0, y0 - 150.0 + 30.0 * k)
        make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Seal Row Wall {k}', WALL, m.team('p1'), wp))
    t.scripts.append(Script('Test - seal row make', [('TIMER_EXPIRED', 'Test Seal Make')], make))
    unit = m.role('row foot').name
    t.areas['Test Seal Row East'] = [(x0 + 130, y0 - 400), (x0 + 600, y0 - 400), (x0 + 600, y0 + 400), (x0 + 130, y0 + 400)]
    t.areas['Test Seal Row North'] = [(x0 - 200, y0 + 170), (x0 + 130, y0 + 170), (x0 + 130, y0 + 400), (x0 - 200, y0 + 400)]
    t.areas['Test Seal Row South'] = [(x0 - 200, y0 - 400), (x0 + 130, y0 - 400), (x0 + 130, y0 - 170), (x0 - 200, y0 - 170)]
    for k, (area, n) in enumerate((('Test Seal Row East', 2), ('Test Seal Row North', 4), ('Test Seal Row South', 8))):
        t.scripts.append(Script(f'Test - CNV_Seal_Foot r{k}', [('NAMED_INSIDE_AREA', unit, area)],
                                [('INCREMENT_COUNTER', n, 'CNV_Seal_Foot')], once=True))
    return t


def _wall(m, lane, side, dx, step=30.0, n=11, wall_hp=False):
    """A row of n bunkers of `side`, dx east of the lane's start, centred on its y, made at MAKE s. Counters:
    CNV_Seal_Foot (1 = left the start's 60, 2 = east of the row, 4 / 8 = north / south of the row's end),
    CNV_Seal_Hp the target's health, CNV_Seal_Wall the middle bunker's health when wall_hp."""
    t = _idle(m, lane, False)
    _timers(t)
    x0, y0 = m.site(f'seal {lane}')
    half = step * (n - 1) / 2
    names = [f'UNIT - CNV Seal {lane.title()} Wall {k}' for k in range(n)]
    make = []
    for k in range(n):
        wp = f'Test Seal {lane.title()} Row {k}'
        t.waypoints[wp] = (x0 + dx, y0 - half + step * k)
        make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', names[k], WALL, m.team(side), wp))
    t.scripts.append(Script(f'Test - seal {lane} make', [('TIMER_EXPIRED', 'Test Seal Make')], make))
    unit = m.role(f'{lane} foot').name
    e, hy, tag = x0 + dx + 25.0, half + 20.0, lane.title()
    t.areas[f'Test Seal {tag} East'] = [(e, y0 - 400), (x0 + 900, y0 - 400), (x0 + 900, y0 + 400), (e, y0 + 400)]
    t.areas[f'Test Seal {tag} North'] = [(x0 - 200, y0 + hy), (e, y0 + hy), (e, y0 + 400), (x0 - 200, y0 + 400)]
    t.areas[f'Test Seal {tag} South'] = [(x0 - 200, y0 - 400), (e, y0 - 400), (e, y0 - hy), (x0 - 200, y0 - hy)]
    for k, (area, nn) in enumerate(((f'Test Seal {tag} East', 2), (f'Test Seal {tag} North', 4),
                                    (f'Test Seal {tag} South', 8))):
        t.scripts.append(Script(f'Test - CNV_Seal_Foot {lane} r{k}', [('NAMED_INSIDE_AREA', unit, area)],
                                [('INCREMENT_COUNTER', nn, 'CNV_Seal_Foot')], once=True))
    if wall_hp:
        counted('CNV_Seal_Wall', '中墙血', t, health=names[n // 2])
    return t


def erow(m):
    """row with the 11 bunkers the ENEMY's (s1): does the soldier shoot the MCV, the bunkers, or nothing."""
    return _wall(m, 'erow', 's1', 105.0, wall_hp=True)


def tank(m):
    """a Guardian tank (range 150), the MCV 130 east, the player's row 65 east."""
    return _wall(m, 'tank', 'p1', 65.0)


def tankopen(m):
    return _idle(m, 'tankopen', False)


def arty(m):
    """a Soviet V4 launcher (range 500, min 200; no LINE_OF_SIGHT flag), the MCV 350 east, the player's row 200 east."""
    return _wall(m, 'arty', 'p1', 200.0)


def artyhp(m):
    """arty's set-up, the middle bunker's health counted too: does the V4's rocket hit the row in between."""
    t = _wall(m, 'arty', 'p1', 200.0, wall_hp=True)
    t.bench[0][1]['lines'] = 3
    return t


def artyopen(m):
    """arty's lane with no row (the control): does the idle V4 fire at the MCV 350 off at all."""
    return _idle(m, 'arty', False)


def attack(m):
    """row's set-up (lane 'attack'), plus an explicit attack order on the MCV at 4 s."""
    t = _wall(m, 'attack', 'p1', 105.0)
    t.scripts.append(Script('Test - seal attack', [('TIMER_EXPIRED', 'Test Seal Order')],
                            m.order('attack', [m.role('attack foot').name], m.role('attack enemy').name, 'p1',
                                    crew='SealAttack')))
    return t


def aa(m):
    """an IFV (range 300), an s1 Twinblade (NO_ATTACK, on the ground) 200 east, the player's row 100 east."""
    t = _wall(m, 'aa', 'p1', 100.0)
    t.scripts.append(Script('Test - seal aa start', [], [('UNIT_CHANGE_OBJECT_STATUS', m.role('aa enemy').name,
                                                          'NO_ATTACK', 1)]))
    return t


def aaopen(m):
    t = _idle(m, 'aaopen', False)
    t.scripts.append(Script('Test - seal aa start', [], [('UNIT_CHANGE_OBJECT_STATUS', m.role('aaopen enemy').name,
                                                          'NO_ATTACK', 1)]))
    return t


def _ebld(m, lane):
    """The computer side's soldier by the player's buildings (Generals PartitionFilterRejectBuildings: a computer
    player's units take enemy buildings by themselves, a human's only base defences): a bunker and a power plant of
    the player's in range, the line clear. Counters: the bunker's and the plant's health, the soldier (1 = left the
    start's 60, 10 = at the goal)."""
    t = Test()
    counted('CNV_Seal_Wall', '地堡血', t, health=m.role(f'{lane} bunker').name)
    counted('CNV_Seal_Hp', '电厂血', t, health=m.role(f'{lane} plant').name)
    x, y = m.site(f'seal {lane}')
    t.areas[f'Test Seal {lane.title()} Start'] = square(x, y, 60.0)
    parts = [(f'Test Seal {lane.title()} Start', 1, 'out')]
    if lane in ('ebldam', 'pam'):
        k = lane.title()
        gx, gy = m.site(f'seal {lane} goal')
        t.areas[f'Test Seal {k} Goal'] = square(gx, gy, 100.0)
        parts.append((f'Test Seal {k} Goal', 10, 'in'))
        # 100 = back by the plant (a strip south of the attack-move's line, round the plant: not on the way)
        t.areas[f'Test Seal {k} By Plant'] = [(x + 300, y - 300), (x + 700, y - 300), (x + 700, y - 70), (x + 300, y - 70)]
        parts.append((f'Test Seal {k} By Plant', 100, 'in'))
        wp = f'Test Seal {k} Goal Point'
        t.waypoints[wp] = (gx, gy)
        _timers(t)
        side = 's1' if lane == 'ebldam' else 'p1'
        t.scripts.append(Script(f'Test - seal {lane} go', [('TIMER_EXPIRED', 'Test Seal Order')],
                                m.order('attack_move', [m.role(f'{lane} foot').name], wp, side, crew=f'Seal{k}')))
    _score(m, t, 'CNV_Seal_Foot', '兵', m.role(f'{lane} foot').name, parts)
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=3))]
    t.expect = []
    return t


def ebld(m):
    """the enemy's soldier idle, the player's bunker 120 east and power plant 150 west."""
    return _ebld(m, 'ebld')


def ebldam(m):
    """the enemy's soldier attack-moves 1000 east at 4 s past the player's bunker (100 north of its line) and power
    plant (120 south), both 500 along."""
    return _ebld(m, 'ebldam')


def pam(m):
    """ebldam with the sides swapped: the player's soldier attack-moves past the enemy's bunker and plant."""
    return _ebld(m, 'pam')


def spawn(m):
    t = Test()
    _timers(t)
    x, y = m.site('seal spawn')
    t.waypoints['Test Seal Spawn Centre'] = (x, y)
    names = ['UNIT - CNV Seal Spawn Ifv', 'UNIT - CNV Seal Spawn Foot']
    t.scripts.append(Script('Test - seal make', [('TIMER_EXPIRED', 'Test Seal Make')],
                            [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', names[0], IFV, m.team('p1'), 'Test Seal Spawn Centre'),
                             ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', names[1], FOOT, m.team('p1'),
                              'Test Seal Spawn Centre')]))
    gx, gy = m.site('seal spawn goal')
    for tag, counter, label, unit in (('Ifv', 'CNV_Seal_Ifv', '车', names[0]), ('Foot', 'CNV_Seal_Foot', '兵', names[1])):
        t.areas[f'Test Seal Spawn {tag} Near'] = square(x, y, 40.0)
        t.areas[f'Test Seal Spawn {tag} Far'] = square(x, y, 110.0)
        t.areas[f'Test Seal Spawn {tag} Goal'] = square(gx, gy, 100.0)
        t.areas[f'Test Seal Spawn {tag} Big'] = square(x + 300, y, 800.0)    # alive: a missing unit is 'outside'
        t.counters.append((counter, label))
        for k, (area, n, how) in enumerate(((f'Test Seal Spawn {tag} Near', 1, 'out'),
                                            (f'Test Seal Spawn {tag} Far', 2, 'out'),
                                            (f'Test Seal Spawn {tag} Goal', 10, 'in'))):
            cond = [('NAMED_OUTSIDE_AREA' if how == 'out' else 'NAMED_INSIDE_AREA', unit, area),
                    ('NAMED_INSIDE_AREA', unit, f'Test Seal Spawn {tag} Big')]
            t.scripts.append(Script(f'Test - {counter} {k}', cond, [('INCREMENT_COUNTER', n, counter)], once=True))
    _order(m, t, 'seal spawn', names, 'SealSpawn')
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=2))]
    t.expect = []
    return t


MISSION = {'engine_seal': mission}
CHECKS = {'engine_seal': {'move': move, 'idle': idle, 'open': idle_open, 'cut': cut, 'row': row, 'spawn': spawn,
                           'erow': erow, 'tank': tank, 'topen': tankopen, 'arty': arty, 'artyhp': artyhp, 'artyo': artyopen, 'attack': attack,
                           'aa': aa, 'aaopen': aaopen, 'ebld': ebld, 'ebldam': ebldam, 'pam': pam}}
