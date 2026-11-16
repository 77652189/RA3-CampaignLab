"""Engine probe, MARK_MISSION_OBJECTIVE_COMPLETED (14 retail uses) and MARK_MISSION_OBJECTIVE_NOT_COMPLETED (1): what
each does to an objective in the mission menu, from each status. No condition reads an objective, so -- as
engine_scripts5 -- the counter 阶段 (1 at STEP1, 2 at STEP2) only says the steps ran and the reading is the menu
(the check's last bench step, bench_menu: a frame in the run folder). Retail: a04 'Objective1a' is shown (status 1)
and later only MARKed completed, no status 2; j07 'failed bonus 2' MARKs a bonus NOT_COMPLETED -- used as its failure. Mission here (build
engine_markobj) on maps/probe_border.py: one tank of the player's at 'line', all six objectives hidden at the start.

  goals   STEP1 sets the starting status, STEP2 the MARK:
            M1 一：1, then COMPLETED                  -- a04's use: done?
            M2 二：never shown, then COMPLETED        -- listed done (as status 2 without 1, engine_scripts5 O4)?
            M3 三：1, then NOT_COMPLETED              -- no mark (shown) or failed?
            M4 四：2, then NOT_COMPLETED              -- done taken back: no mark, or failed?
            M5 五：3, then COMPLETED                  -- failed turned done?
            M6 六 (bonus)：1, then NOT_COMPLETED      -- j07's use
          [The simulator (sim.py, before this probe): the engine model's core keeps COMPLETED = 2 and NOT_COMPLETED =
          1 in its own table, the simulator's objectives never see them -- so M1 stays 1, M2 hidden, M3 1, M4 2,
          M5 3, M6 1. The model's own guess: M1 2, M2 2, M3 1, M4 1, M5 2, M6 1.]

读数 (bench 11-16, two runs, the same menu: CampMarkGoals_mcp_1116_124443 (its verdict FAIL only for the menu's
pause hiding the s16 reading: the expectation now ends at s15) and _124638 PASS; 阶段 2 from s6; menu frame 14)
  menu list (main, green):  1. 一 [check]   2. 三 [empty box]   3. 四 [empty box]   4. 五 [check]   5. 二 [check]
            (bonus, yellow):  1. 六 [empty box]
  - COMPLETED = status 2 from any status: M1 shown -> done (a04's use), M5 failed -> done, M2 hidden -> listed done,
    last (first shown at STEP2, the list in order of first appearance as engine_scripts5).
  - NOT_COMPLETED = status 1: M3 stays shown unticked, M4 done -> unticked, M6 bonus unticked -- no failed mark
    anywhere, so j07's 'failed bonus 2' only takes the tick back. The model's guess holds; the simulator now passes
    both to its own objectives (Sim.act), tests/test_simbench.py test_mark_objective_as_the_bench.
"""
from maps import probe_border
from parts import Goal, Mission, Script, Test

TANK = 'AlliedAntiVehicleVehicleTech1'
STEP1, STEP2, RUN = 2.0, 6.0, 12.0
DONE, NOT_DONE = 'MARK_MISSION_OBJECTIVE_COMPLETED', 'MARK_MISSION_OBJECTIVE_NOT_COMPLETED'
GOALS = [('M1', '一 亮出后标完成'), ('M2', '二 不亮直接标完成'), ('M3', '三 亮出后标未完成'),
         ('M4', '四 完成后标未完成'), ('M5', '五 失败后标完成'), ('M6', '六 奖励 亮出后标未完成')]
STEPS = {'M1': (1, DONE), 'M2': (None, DONE), 'M3': (1, NOT_DONE), 'M4': (2, NOT_DONE), 'M5': (3, DONE),
         'M6': (1, NOT_DONE)}


def goal(name):
    return f'CNV MK {name}'


def mission():
    goals, strings = [], {}
    for name, title in GOALS:
        key = f'MISSIONOBJ:CNVMK_{name}'
        strings[key], strings[key + '_DESC'] = title, f'探针目标 {name}：{title}'
        goals.append(Goal(goal(name), key, key + '_DESC', bonus=name == 'M6', at=None))
    m = Mission(name='CampMark', map=probe_border, objectives=goals, facts={})
    m.strings.update(strings)
    m.put(TANK, 'line', 0.0, 0.0, angle=0.0, name='UNIT - CNV MK Tank', role='tank')
    return m


def _at(t, key, secs, actions):
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def goals(m):
    t = Test()
    first = [('SET_MISSION_OBJECTIVE_STATUS', goal(n), s) for n, (s, _) in STEPS.items() if s is not None]
    second = [(mark, goal(n)) for n, (_, mark) in STEPS.items()]
    t.counters.append(('CNV_MK_Step', '阶段'))
    t.scripts.append(Script('Test - step 0', [], [('SET_COUNTER', 'CNV_MK_Step', 0)]))
    _at(t, 'one', STEP1, first + [('SET_COUNTER', 'CNV_MK_Step', 1)])
    _at(t, 'two', STEP2, second + [('SET_COUNTER', 'CNV_MK_Step', 2)])
    t.expect += [('阶段', STEP2 + 2, '==', 2, RUN + 3)]         # the menu step's pause: no reading after it
    t.bench = [('bench_watch', dict(seconds=RUN, every=1.0, sheet=False, lines=1)), ('bench_menu', dict(scale=0.5))]
    return t


MISSION = {'engine_markobj': mission}
CHECKS = {'engine_markobj': {'goals': goals}}
