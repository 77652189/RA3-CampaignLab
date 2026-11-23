"""C line: PLAYER_DISABLE_BASE_CONSTRUCTION(player), native production control.

JapanConstructionYard's UNIT_BUILD Command_ConstructJapanPowerPlantEgg builds an 800-cost
JapanPowerPlantEgg (retail BuildTime 0). No placement or artificial spawning is used.
A disables p1; B disables s5. The human p1 clicks the first structure button; s5 receives
the same native command by NAMED_USE_COMMANDBUTTON_ABILITY at 2 seconds.
Prediction: p1's disabled native click spends nothing and makes no core; the normal click
spends 800 and makes one core. Whether the scripted press bypasses this gate is unmeasured.
Counters: human money, s5 money, human cores + 10*s5 cores, script logic frame.
Evidence and scope: work/re/c_baseban_report.md. Other factions/AI queues remain unmeasured.
BENCH 11-16: A at f74 2000/1426/0, final f488 1200/1200/11;
B at f75 2000/1413/0, final f364 1200/1200/11. Disabling either player
does not block these UNIT_BUILD core orders. The base-construction consumer remains a gap;
do not infer a no-op action or promote it from this control. Payment timing is strict xfail.
C: PLAYER_DISABLE_FACTORIES(each, 'japanconstructionyard') as j09 writes it (lower case): the program sets every
matching object of the player's script-disabled (type 9, for ever). Prediction: no core either side, money 2000.
BENCH 11-22 (A311): C, D (the own case, two walkers too), F (D at 0.5 s): every core made, both walkers walk -- as
with no gate; E (NAMED_SET_DISABLED SCRIPT_DISABLED on the yards and walker 0, EMP walker 1) 2000/2000/0 to s53: the
type holds both. So the action reaches no object here (why: not found). Readings: engine_baseban.readings.toml.
"""
from maps import probe_border
from parts import Mission, Script, Test, square
from checks import engine_scripts8 as s8

CORE = 'JapanPowerPlantEgg'
BUTTON = 'Command_ConstructJapanPowerPlantEgg'
WALKERS = (('AlliedAntiVehicleVehicleTech1', 200.), ('AlliedEngineer', 350.))


def mission():
    m = Mission(name='CampBaseBan', map=probe_border, units=[], facts={})
    m.spawns.add(CORE)
    for side, dx in (('p1', 0.), ('s5', 1800.)):
        m.put('JapanConstructionYard', 'stop row', dx, -500., side=side,
              name=f'CNV BaseBan {side}', role=f'yard {side}')
    for k, (unit, dy) in enumerate(WALKERS):      # D's probe of the disabled bit: does each still walk?
        m.put(unit, 'stop row', 600., dy, name=f'CNV BaseBan W{k}', role=f'walker {k}')
        m.waypoint(f'end {k}', f'CNV BaseBan End{k}', 'stop row', 1200., dy)
    return m


def check(m, gate, walk=False, more=()):
    t = Test()
    t.scripts.append(Script('Test - baseban setup', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('PLAYER_SET_MONEY', m.player('p1'), 2000),
        ('PLAYER_SET_MONEY', m.player('s5'), 2000),
        *gate]))
    for side, label in (('p1', '甲资金'), ('s5', '乙资金')):
        counter = f'CNV_BaseBan_{side}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - baseban money {side}', [], [
            ('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), counter)], once=False))
    s8.total(t, 'CNV_BaseBan_Cores', '核心', [
        (w, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(side), 3, 1, CORE))
        for side, w in (('p1', 1), ('s5', 10))] + [
        (100 * 10 ** k, ('NAMED_INSIDE_AREA', m.role(f'walker {k}').name, f'Test BaseBan End{k}'))
        for k in range(len(WALKERS) if walk else 0)] + list(more))
    s8.frames(t, 'CNV_BaseBan_Clock', '逻辑帧', [])
    s8.at(t, 'baseban press', 2., [
        ('NAMED_USE_COMMANDBUTTON_ABILITY', 'CNV BaseBan s5', BUTTON)])
    watch = dict(every=1., sheet=False, lines=4)
    t.bench = [('bench_watch', dict(watch, seconds=2.)),
               ('bench_click', dict(x=1120, y=252, world=False, look=False)),
               ('bench_click', dict(x=1120, y=252, world=False, look=False)),
               ('bench_click', dict(x=1137, y=323, world=False, look=False)),
               ('bench_watch', dict(watch, seconds=18.))]
    return t


def a(m):
    return check(m, [('PLAYER_DISABLE_BASE_CONSTRUCTION', m.player('p1'))])


def b(m):
    return check(m, [('PLAYER_DISABLE_BASE_CONSTRUCTION', m.player('s5'))])


def c(m):
    return check(m, [('PLAYER_DISABLE_FACTORIES', m.player(s), 'japanconstructionyard') for s in ('p1', 's5')])


def d(m, late=False):
    """C's yards in the template's own case; walker 0 disabled by a lower-case name, walker 1 by its own, both sent
    600 east at 1 s: 核心 adds 100 walker 0 at its end + 1000 walker 1 (within 100). F: the same at 0.5 s."""
    return walked(m, late=late, gate=[('PLAYER_DISABLE_FACTORIES', m.player(s), 'JapanConstructionYard') for s in ('p1', 's5')] + [
        ('PLAYER_DISABLE_FACTORIES', m.player('p1'), WALKERS[0][0].lower()),
        ('PLAYER_DISABLE_FACTORIES', m.player('p1'), WALKERS[1][0])])


def e(m):
    """The same, each by NAMED_SET_DISABLED: the yards and walker 0 SCRIPT_DISABLED (the type C / D set), walker 1
    EMP (the control: frozen, engine_emp)."""
    return walked(m, [('NAMED_SET_DISABLED', n, 'SCRIPT_DISABLED', 1) for n in (
        'CNV BaseBan p1', 'CNV BaseBan s5', m.role('walker 0').name)] + [
        ('NAMED_SET_DISABLED', m.role('walker 1').name, 'EMP', 1)])


def f(m):
    return d(m, late=True)


def walked(m, gate, late=False):
    t = check(m, [] if late else gate, walk=True)
    if late:
        s8.at(t, 'baseban off', .5, gate)
    s8.at(t, 'baseban walk', 1., [('MOVE_NAMED_UNIT_TO', m.role(f'walker {k}').name, m.mark(f'end {k}'))
                                  for k in range(len(WALKERS))])
    for k in range(len(WALKERS)):
        t.areas[f'Test BaseBan End{k}'] = square(*m.point(f'end {k}'), 100.)
    return t


def late_mission():
    """G (review 1122yy #11, the positive control C-F lack): a yard made mid-game. Each side also has a JapanMCV,
    unpacked where it stands at 0.2 s (the name passes on, engine_unpack); at 3 s PLAYER_DISABLE_FACTORIES(s5,
    'JapanConstructionYard') -- s5's only, p1 the control; at 5 s each unpacked yard is pressed for a core.
    核心 adds p1 >= 2 cores 100 + s5 >= 2 cores 1000 + p1 >= 2 yards 10000 + s5 >= 2 yards 100000.
    [the gate reaches a yard made in play: 110111; it reaches none: 111111] BENCH 11-23 (CampBanLateG_mcp_1123_012105):
    111111 s36-s54, money 400 / 400 -- none; no positive control found, the dispatch itself stays unshown."""
    m = mission()
    m.name = 'CampBanLate'
    for side, dx in (('p1', 0.), ('s5', 1800.)):
        m.put('JapanMCV', 'stop row', dx, 400., side=side, name=f'CNV BaseBan M{side}', role=f'mcv {side}')
        m.waypoint(f'here {side}', f'CNV BaseBan Here{side}', 'stop row', dx, 400.)
    return m


def g(m):
    t = check(m, [], more=[(w, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(s), 3, 2, what)) for s, w, what in (
        ('p1', 100, CORE), ('s5', 1000, CORE), ('p1', 10000, 'JapanConstructionYard'),
        ('s5', 100000, 'JapanConstructionYard'))])
    s8.at(t, 'baseban unpack', .2, [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', m.role(f'mcv {s}').name,
                                     'Command_UnPackJapanMCV', m.mark(f'here {s}')) for s in ('p1', 's5')])
    s8.at(t, 'baseban off', 3., [('PLAYER_DISABLE_FACTORIES', m.player('s5'), 'JapanConstructionYard')])
    s8.at(t, 'baseban late press', 5., [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(f'mcv {s}').name, BUTTON)
                                        for s in ('p1', 's5')])
    return t


MISSION = {'engine_baseban': mission, 'engine_banlate': late_mission}
CHECKS = {'engine_baseban': {'a': a, 'b': b, 'c': c, 'd': d, 'e': e, 'f': f}, 'engine_banlate': {'g': g}}
