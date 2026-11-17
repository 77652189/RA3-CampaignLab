"""Engine probe, the mission objective items (docs/engine/inventory-levels-a.md, the three heaviest inferred script
actions): SET_MISSION_OBJECTIVE_STATUS (732), LINK_MISSION_OBJECTIVE_TO_OBJECT (950), LINK_MISSION_OBJECTIVE_TO_WAYPOINT
(194). No condition reads an objective, so the check only steps the statuses (counter 阶段: 1 at STEP1, 2 at STEP2)
and the reading is the mission menu (cnv_check keep=true, then bench_menu by hand). Mission here (build
engine_scripts5) on maps/probe_border.py (the simulator's level ground): one tank of the player's at 'line' for the object markers.

  goals   six objectives, all hidden at the start (the mission's own goal_scripts), then:
            O1 一：1 at STEP1, 2 at STEP2                        -- shown, then done
            O2 二：1 at STEP1, 3 at STEP2                        -- shown, then failed
            O3 三：1 at STEP1, 0 at STEP2                        -- shown, then hidden again?
            O4 四：2 at STEP2, never 1                           -- done without being shown: listed?
            O5 五：1 at STEP1, 7 at STEP2                        -- a status out of 0..3 [源码: ignored, stays shown]
            O6 六 (bonus)：1 at STEP1                            -- a yellow one, shown
          markers: O1 on the tank (TO_OBJECT 1 at STEP1, left on after done), O2 on the tank too, taken off at STEP2
          (TO_OBJECT 0), O6 on a waypoint 600 east of it (TO_WAYPOINT 1 at STEP1).
          [The simulator (sim.py): objectives[name] = status as written, 7 too; markers a set per objective, apart
          from the status.]

读数 (bench 11-09, CampScr5Goals_mcp_1109_095326: PASS 阶段 1 s1-s4, 2 from s5; bench_menu at s14, minimap frames 4 / 13)
  menu list at s14 (main, green):  1. 一 [check]   2. 二 [red X]   3. 五 [empty box]   4. 四 [check]
               (bonus, yellow, numbered apart):  1. 六 [empty box]
  - O1 1 -> 2: done mark; O2 1 -> 3: failed mark.
  - O3 1 -> 0: gone from the list, the numbers close up (五 is 3) -- 0 hides an objective already shown.
  - O4 2 without ever 1: listed, done -- a done / failed status shows it too.
  - the list is in order of first appearance, not of the mission's goal list: 四 (first shown at STEP2) after 五
    (STEP1).
  - O5 1 -> 7: still listed, no mark -- 7 ignored, as the source (and the simulator since round 119).
  - O6 bonus: a separate yellow list, its own numbers from 1.
  - markers (minimap, s4): a green '!' on the tank (main; O1 and O2 both on it, one icon drawn), a yellow '!' at the
    east waypoint (bonus). s13: the tank's marker gone (O1 done with its link left on, O2 unlinked and failed), the
    waypoint's stays. The menu map at s14 shows only the bonus pin ('1', yellow). So a done objective's marker is not
    drawn [not told apart: done hides the marker vs one icon per object that O2's unlink took away].
"""
from maps import probe_border
from parts import Goal, Mission, Script, Test

TANK = 'AlliedAntiVehicleVehicleTech1'
STEP1, STEP2, RUN = 2.0, 6.0, 12.0
GOALS = [('O1', '一 亮出后完成'), ('O2', '二 亮出后失败'), ('O3', '三 亮出后藏回'), ('O4', '四 不亮直接完成'),
         ('O5', '五 亮出后写 7'), ('O6', '六 奖励 只亮出')]
STEPS = {'O1': (1, 2), 'O2': (1, 3), 'O3': (1, 0), 'O4': (None, 2), 'O5': (1, 7), 'O6': (1, None)}


def _goal(name):
    return f'CNV S5 {name}'


def mission():
    goals, strings = [], {}
    for name, title in GOALS:
        key = f'MISSIONOBJ:CNVS5_{name}'
        strings[key], strings[key + '_DESC'] = title, f'探针目标 {name}：{title}'
        goals.append(Goal(_goal(name), key, key + '_DESC', bonus=name == 'O6', at=None))
    m = Mission(name='CampScr5', map=probe_border, objectives=goals, facts={})
    m.strings.update(strings)
    m.put(TANK, 'line', 0.0, 0.0, angle=0.0, name='UNIT - CNV S5 Tank', role='tank')
    m.waypoint('east', 'CNV S5 East', 'line', 600.0, 0.0)
    return m


def _at(t, key, secs, actions):
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def goals(m):
    t = Test()
    tank, east = m.role('tank').name, m.mark('east')
    first = [('SET_MISSION_OBJECTIVE_STATUS', _goal(n), s) for n, (s, _) in STEPS.items() if s is not None]
    second = [('SET_MISSION_OBJECTIVE_STATUS', _goal(n), s) for n, (_, s) in STEPS.items() if s is not None]
    first += [('LINK_MISSION_OBJECTIVE_TO_OBJECT', _goal('O1'), tank, 1),
              ('LINK_MISSION_OBJECTIVE_TO_OBJECT', _goal('O2'), tank, 1),
              ('LINK_MISSION_OBJECTIVE_TO_WAYPOINT', _goal('O6'), east, 1)]
    second.append(('LINK_MISSION_OBJECTIVE_TO_OBJECT', _goal('O2'), tank, 0))
    t.counters.append(('CNV_S5_Step', '阶段'))
    t.scripts.append(Script('Test - step 0', [], [('SET_COUNTER', 'CNV_S5_Step', 0)]))
    _at(t, 'one', STEP1, first + [('SET_COUNTER', 'CNV_S5_Step', 1)])
    _at(t, 'two', STEP2, second + [('SET_COUNTER', 'CNV_S5_Step', 2)])
    t.expect += [('阶段', STEP2 + 2, '==', 2)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1.0, sheet=False, lines=1))]
    return t


MISSION = {'engine_scripts5': mission}
CHECKS = {'engine_scripts5': {'goals': goals}}
