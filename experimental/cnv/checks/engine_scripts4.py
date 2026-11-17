"""Engine probe, the inferred script items (docs/engine/inventory-levels-a.md): MAP_SWITCH_BORDER, the countdown shown
and hidden (DISPLAY_COUNTDOWN_TIMER / HIDE_COUNTDOWN_TIMER), TEAM_STOP, TEAM_GUARD_AREA. Mission here (build
engine_scripts4) on maps/probe_border.py, flat ground with a second border (the west half, x <= 2500). What the
Generals source / the simulator predicts is in brackets; the readings go below.

  border   MAP_SWITCH_BORDER 1 (the west half) in the first frame, 0 (the whole map) at OPEN_AT. Three Guardian
           pairs 120 apart, the player's facing the enemy's: X across the line (the player's west of it, the
           enemy's 60 east: on the map / off it), Y both east (both off), Z both west (both on). X血 / Y血 / Z血 the
           enemy Guardian's health; Y在 1 while the player's Y Guardian is in an area round where it stands (RA3's
           ObjectStatus has no OFF_MAP to count). [源码 4.4: the object is not killed or deleted, only marked
           OFF_MAP -- Y在 1 throughout; Generals' auto-targeting filters
           on the same map status (PartitionFilterSameMapStatus, INFERRED for RA3): X holds its fire till OPEN_AT,
           Y and Z fight. The simulator: the border changes no fight -- X falls from the start.]
  team     two Guardians on team Stop sent east along the stop row (MOVE_TEAM_TO, at 1 s, 1400 away), TEAM_STOP at
           STOP_AT; two on team Guard told TEAM_GUARD_AREA of a zone 700 east of them at 1 s. 停起点 / 停中段 /
           停终点 the stop team's Guardians in the start / middle / far area; 守区内 the guard team's in the zone.
           [Sim.order_stop drops the way: 0 / 2 / 0 to the end; Sim.order_guard sends each to the zone's middle
           (UNIT_GUARD_AREA, engine_acquire): 守区内 2 and stays.]
  clock    timer 20 s set and DISPLAY_COUNTDOWN_TIMER in the first frame, HIDE_COUNTDOWN_TIMER at 8 s, shown
           again at 14 s; 到点 1 once the timer expires. [源码 4.3: showing is UI only -- the hidden timer runs on,
           到点 1 at 20; shown again it reads what is left (~0:06).] The countdown line itself is skipped by the
           counter reader (a colon): read off the frames by hand.

读数
Bench 2026-11-09 (one run each; bench seconds run ~2 ahead of mission time; sim pairs tests/test_simbench.py
test_scripts4_*; docs/engine/script-semantics.md 4.3, 4.4):
  border  CampScr4Border_mcp_1109_072744: X血 and Y血 100 till s18, then 87 at s19 and down ~6 a second (12 at
          s31); Z血 87 at s1 down to 12 at s12, held there (one of the pair dead); Y在 1 all along (0 at s33: the
          player's Y Guardian died in its fight). So an object off the border neither fires nor is fired on -- X
          (ours inside, theirs outside) as Y (both outside): stricter than Generals' same-status filter; it lives
          on and the area conditions see it. Sim.on_map since.
  team    CampScr4Team_mcp_1109_073024: PASS -- 停中段 2 from s1, 停起点 / 停终点 0 to the end (TEAM_STOP: they stop
          where they are and stay); 守区内 1 at s6, 2 from s8 to s32 (TEAM_GUARD_AREA: both go in and stay).
  clock   CampScr4Clock_mcp_1109_073246: PASS -- 到点 1 from s19 (the hidden timer ran on). The countdown line read
          off the frames by hand: "测试倒计时 0:15" above 到点 at s3, gone s6-s11, back from s12 reading 0:04 (what
          was left, not reset) and **below** 到点 (shown again, it goes to the end of the list), "0:00" still shown
          after it expired (s20-s27: an expired countdown stays till hidden).
"""
import math

from maps import probe_border
from parts import Mission, Script, Test, counted, square

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
OPEN_AT, STOP_AT, HIDE_AT, SHOW_AT, CD = 20.0, 4.0, 8.0, 14.0, 20.0
RUN = {'border': 32.0, 'team': 30.0, 'clock': 26.0}
# the border scene: (pair, dx, dy) of the player's Guardian from the line; the enemy's 120 east of it
PAIRS = {'x': (-60.0, 0.0), 'y': (440.0, 200.0), 'z': (-560.0, 200.0)}
ROW = 700.0                                     # the team rows: start dx -ROW, the far end / the zone further east


def _n(part):
    return f'UNIT - CNV S4 {part}'


def mission():
    m = Mission(name='CampScr4', map=probe_border, facts={})
    m.spawns |= {GUARDIAN}
    for pair, (dx, dy) in PAIRS.items():
        m.put(GUARDIAN, 'line', dx, dy, angle=0.0, name=_n(f'Mine {pair}'), role=f'mine {pair}')
        m.put(GUARDIAN, 'line', dx + 120.0, dy, side='s1', angle=math.pi, name=_n(f'Foe {pair}'), role=f'foe {pair}')
    for row, key in (('stop row', 'Stop'), ('guard row', 'Guard')):
        for k, dy in enumerate((-30.0, 30.0), 1):
            m.put(GUARDIAN, row, -ROW, dy, angle=0.0, name=_n(f'{key} {k}'), role=f'{key.lower()} {k}')
        m.crew(key)
    m.waypoint('stop far', 'CNV S4 Stop Far', 'stop row', ROW, 0.0)
    return m


def _at(t, key, secs, actions):
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def _watch(t, run):
    t.bench = [('bench_watch', dict(seconds=run, every=1.0, sheet=False, lines=len(t.counters)))]


def border(m):
    t = Test()
    t.scripts.append(Script('Test - border', [], [('MAP_SWITCH_BORDER', list(probe_border.BORDERS).index('west half'))]))
    _at(t, 'open', OPEN_AT, [('MAP_SWITCH_BORDER', 0)])
    for pair in PAIRS:
        counted(f'CNV_S4_{pair.upper()}', f'{pair.upper()}血', t, health=m.role(f'foe {pair}').name)
    t.areas['Test S4 Y'] = square(*m.site('line', *PAIRS['y']), 80.0)
    counted('CNV_S4_YIn', 'Y在', t, named=m.role('mine y').name, area='Test S4 Y')
    t.expect += [('Z血', 8, '<', 100), ('Y血', 1, '==', 100, OPEN_AT - 2), ('X血', 1, '==', 100, OPEN_AT - 2),
                 ('X血', OPEN_AT + 8, '<', 100), ('Y血', OPEN_AT + 8, '<', 100), ('Y在', 1, '==', 1, 10)]
    _watch(t, RUN['border'])
    return t


def team(m):
    t = Test()
    x, y = m.site('stop row', 0.0, 0.0)
    t.areas['Test S4 Stop Start'] = square(x - ROW, y, 100.0)
    t.areas['Test S4 Stop Mid'] = [(x - ROW + 101, y - 150), (x + ROW - 101, y - 150), (x + ROW - 101, y + 150),
                                   (x - ROW + 101, y + 150)]
    t.areas['Test S4 Stop Far'] = square(x + ROW, y, 100.0)
    gx, gy = m.site('guard row', 0.0, 0.0)
    zone = 'Test S4 Guard Zone'
    t.areas[zone] = square(gx, gy, 150.0)
    for area, label in (('Start', '停起点'), ('Mid', '停中段'), ('Far', '停终点')):
        counted(f'CNV_S4_Stop{area}', label, t, template=GUARDIAN, area=f'Test S4 Stop {area}')
    counted('CNV_S4_Guard', '守区内', t, template=GUARDIAN, area=zone)
    stop, guard = m.teams['Stop'], m.teams['Guard']
    joins = [('UNIT_SET_TEAM', m.role(f'{key} {k}').name, m.teams[key.capitalize()])
             for key in ('stop', 'guard') for k in (1, 2)]
    _at(t, 'go', 1.0, joins + [('MOVE_TEAM_TO', stop, m.mark('stop far')), ('TEAM_GUARD_AREA', guard, zone)])
    _at(t, 'halt', STOP_AT, [('TEAM_STOP', stop)])
    t.expect += [('停起点', STOP_AT + 2, '==', 0), ('停中段', STOP_AT + 2, '==', 2), ('停终点', 0, '==', 0),
                 ('守区内', RUN['team'] - 4, '==', 2)]
    _watch(t, RUN['team'])
    return t


def countdown(m):
    t = Test()
    timer, text = 'Test S4 Countdown', 'CNV:S4Countdown'
    t.strings[text] = '测试倒计时'
    t.counters.append(('CNV_S4_Due', '到点'))
    t.scripts += [Script('Test - countdown', [], [('SET_COUNTER', 'CNV_S4_Due', 0), ('SET_MILLISECOND_TIMER', timer, CD),
                                                  ('DISPLAY_COUNTDOWN_TIMER', timer, text)]),
                  Script('Test - countdown due', [('TIMER_EXPIRED', timer)], [('SET_COUNTER', 'CNV_S4_Due', 1)])]
    _at(t, 'hide', HIDE_AT, [('HIDE_COUNTDOWN_TIMER', timer)])
    _at(t, 'show', SHOW_AT, [('DISPLAY_COUNTDOWN_TIMER', timer, text)])
    t.expect += [('到点', 1, '==', 0, CD - 1), ('到点', CD + 2, '==', 1)]
    _watch(t, RUN['clock'])
    return t


MISSION = {'engine_scripts4': mission}
CHECKS = {'engine_scripts4': {'border': border, 'team': team, 'clock': countdown}}
