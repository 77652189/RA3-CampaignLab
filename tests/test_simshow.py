"""What the player sees, hears and may do, read off the simulator (experimental/cnv/simshow.py, ADR 0022): the scripted
camera and its picture (K5), the lines and their timing (K1, I1), the hand-back of the controls, the objectives and
counters on the screen. Small missions on the sapporo map with a hand-set camera, then A4 itself."""
from test_plans import small  # (puts experimental/cnv on the path)  # noqa: I001
import build  # noqa: E402
import ctx  # noqa: E402
import model  # noqa: E402
import simshow  # noqa: E402
from maps import sapporo  # noqa: E402
from parts import Mission, Script  # noqa: E402

CORRIDOR = sapporo.BORDERS['corridor']          # (300, 1700, 3200, 3300): the playable area A4 opens in
WAYS = {'West': (450.0, 2500.0), 'Safe': (1250.0, 2500.0), 'East': (3000.0, 2500.0), 'Edge': (800.0, 2500.0), 'BandEdge': (900.0, 2500.0),
        'Near': (1000.0, 2500.0)}


def mission(*scripts):
    m = Mission(name='T', map=sapporo, scripts=list(scripts))
    m.waypoints = dict(WAYS)
    return m


def at(t, *acts, name=None):
    """A script that runs `t` seconds in (a timer), then does `acts`."""
    k = name or f'at{t:g}-{acts[0][0]}'
    return [Script(f'{k} set', [], [('SET_MILLISECOND_TIMER', f'T {k}', float(t))]),
            Script(k, [('TIMER_EXPIRED', f'T {k}')], list(acts))]


def play(scripts, until=30.0):
    return simshow.ShowSim(mission(*scripts)).run(until)


CORRIDOR_ON = [('MAP_SWITCH_BORDER', 1)]
PAN = lambda where, secs=0.1: ('MOVE_CAMERA_TO', where, secs, 0.0, 0.0, 0.0)      # noqa: E731
HOME = Script('home', [], [PAN('Safe')])        # the opening cut a level has when the start is too near the border (K5)


# ---- 1. the camera -----------------------------------------------------------------------------------------------
def test_a_camera_too_near_the_border_shows_black_and_a_view_point_does_not():
    s = play([Script('border', [], CORRIDOR_ON), HOME] + at(2, PAN('West')))
    runs = simshow.black_runs(s)
    assert runs and runs[0][3]['west'] == round(CORRIDOR[0] - (450 - model.VIEW_HALF[0]), 1) and set(runs[0][3]) == {'west'}, runs
    assert any(p.startswith('K5') for p in simshow.problems(s))
    ok = play([Script('border', [], CORRIDOR_ON), HOME] + at(2, PAN('Safe')))
    assert not simshow.black_runs(ok), simshow.black_runs(ok)       # 1250 - 950 = 300: the edge, not past it


def test_the_games_own_start_camera_is_looked_at_until_a_script_moves_it():
    """The game opens on the map's `start` site: before a script moves the camera that is the picture (I23)."""
    s = play([Script('border', [], CORRIDOR_ON)] + at(10, PAN('Safe')), until=20)
    start = sapporo.SITES['start']
    assert s.camera_at(5.0) == (start.x, start.y)
    assert s.camera_at(11.0) == WAYS['Safe']


def test_a_pan_takes_its_seconds_and_a_letterbox_picture_is_smaller():
    s = play([Script('border', [], CORRIDOR_ON), HOME] + at(5, PAN('East', 10.0), name='pan'))
    x = s.camera_at(10.0)[0]                                   # five seconds into a ten second pan from 1250 to 3000
    assert abs(x - (1250 + (3000 - 1250) * 0.5)) < 1.0, x
    assert s.camera_at(16.0) == WAYS['East']
    # at (800, 2500) the screen shows 150 units of black; the letterbox band (562 half wide at its far edge,
    # measured 2026-11-07) shows 62 of black there too, but none at (900, 2500) where the screen still shows 50 + 300 beyond
    edge = play([Script('border', [], CORRIDOR_ON), HOME] + at(1, PAN('Edge'), name='cut'))
    assert simshow.black_runs(edge) and edge.reach_at(5.0)[0] == model.VIEW_HALF[0]
    wide = play([Script('border', [], CORRIDOR_ON), HOME] + at(1, PAN('BandEdge'), name='cut'))
    assert simshow.black_runs(wide)
    band = play([Script('border', [], CORRIDOR_ON), HOME] + at(1, ('CAMERA_LETTERBOX_BEGIN',), PAN('BandEdge'), name='cut'))
    assert band.reach_at(5.0)[3] == model.LETTERBOX_BAND['north'] and not simshow.black_runs(band)
    assert [on for _, on in band.bars] == [False, True]


def test_a_border_that_closes_in_on_a_camera_that_stays_shows_black():
    """No camera move at all after the border changes: only the picture against the border tells."""
    s = play([Script('border0', [], [('MAP_SWITCH_BORDER', 0)]), Script('cam', [], [PAN('Near')])] + at(8, ('MAP_SWITCH_BORDER', 1), name='close'), until=20)
    runs = simshow.black_runs(s)           # (1000, 2500): fine on the whole map, 250 units past the corridor's west edge
    assert len(runs) == 1 and abs(runs[0][0] - 8.0) <= 1.0 and runs[0][3] == {'west': 250.0}, runs


def test_a_checks_own_camera_is_not_the_levels():
    s = play([Script('border', [], CORRIDOR_ON), HOME, Script('Test Camera', [], [PAN('West')])])
    assert not simshow.black_runs(s)


def test_the_picture_lists_the_units_in_it_not_the_crowd():
    m = small(开局={'资金': '5000/3000/2000', '部队': [{'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
              规则=[{'当': '摧毁 camp', '做': [{'镜头': 'north base'}]}])
    s = simshow.ShowSim(m, script='5 摧毁 camp').run(30)
    assert s.moves, 'the plan moved the camera'
    rows = [r for r in simshow.timeline(s) if r[1] == '镜头']
    assert rows and all('PlyrCivilian' not in r[2] for r in rows), rows


# ---- 2. the lines ------------------------------------------------------------------------------------------------
BEAT = [{'镜头': 'west field'}]


def lines(do, until=60):
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + do}])
    return simshow.ShowSim(m, script='5 摧毁 camp').run(until)


def test_gong_lines_at_once_are_in_time_until_the_queue_runs_past_func_late_k1():
    """Each 功能 caption holds the box FUNC_HOLD (2 s): the fifth, at 4 s after the first, is up in time; the sixth,
    at 10 s, is past FUNC_LATE (8.5 s)."""
    five = lines([{'通报': str(k), '功能': '是'} for k in range(5)])
    assert not simshow.late_lines(five) and not [p for p in simshow.problems(five) if p.startswith('K1')]
    six = lines([{'通报': str(k), '功能': '是'} for k in range(6)])
    late = simshow.late_lines(six)
    assert [(a, round(b - a)) for _, a, b in late] == [(5.0, 10)], late
    assert any(p.startswith('K1') and 'too late' in p for p in simshow.problems(six)), simshow.problems(six)


def test_a_caption_another_pushes_out_before_it_is_read_is_found():
    cap = lambda k, secs: ('SHOW_MILITARY_CAPTION', k, secs)                     # noqa: E731
    s = play([Script('first', [], [cap('A', 6.0)])] + at(1, cap('B', 6.0), name='second'), until=20)
    out = simshow.pushed_out(s)
    assert [(x[1], x[2]) for x in out] == [('A', 1.0)], out
    calm = play([Script('first', [], [cap('A', 6.0)])] + at(3, cap('B', 6.0), name='second'), until=20)
    assert not simshow.pushed_out(calm)


# ---- 3. the flow -------------------------------------------------------------------------------------------------
def test_the_locked_stretch_and_the_hand_back():
    off, on = ('DISABLE_INPUT',), ('ENABLE_INPUT',)
    s = play([Script('lock', [], [off])] + at(8, on), until=20)
    assert simshow.input_spans(s) == [(0.0, 8.0)] and simshow.first_control(s) == 8.0, simshow.input_spans(s)
    assert not simshow.locked_for_good(s)
    stuck = play([Script('lock', [], [off])], until=20)
    assert simshow.input_spans(stuck) == [(0.0, None)] and simshow.locked_for_good(stuck)
    assert any(p.startswith('flow') for p in simshow.problems(stuck))


# ---- 4. the screen -----------------------------------------------------------------------------------------------
def test_objectives_and_counters_are_in_the_timeline():
    s = play([Script('c', [], [('SET_COUNTER', 'N', 0), ('DISPLAY_COUNTER', 'N', 'Trucks')])] +
             at(4, ('SET_COUNTER', 'N', 2), name='two') + at(9, ('HIDE_COUNTER', 'Trucks'), name='hide'), until=20)
    ui = [(round(t), k, x) for t, k, x in s.shown_ui]
    assert (0, '亮出', 'Trucks') in ui and (9, '收起', 'Trucks') in ui, ui
    assert any(k == '读数' and x.endswith('= 2') for _, k, x in ui), ui
    assert [r for r in simshow.timeline(s) if r[1] == '界面' and 'Trucks' in r[2]]


# ---- 5. A4: the player's timeline -------------------------------------------------------------------------------
def test_a4_the_opening_scene_locks_the_controls_and_hands_them_back():
    s = simshow.run('a4', until=100.0)
    spans = simshow.input_spans(s)
    assert spans and spans[0][0] == 0.0 and spans[0][1] is not None and 60 < spans[0][1] < 100, spans
    rows = simshow.timeline(s)
    kinds = {r[1] for r in rows}
    assert {'镜头', '操作', '字幕框', '对白面板', '配音', '界面'} <= kinds, kinds
    assert any('目标亮出' in r[2] for r in rows), 'the objectives come up after the scene'
    assert all(r[0] > spans[0][1] - 1e-6 for r in rows if '目标亮出' in r[2]), 'none before the controls are back'
    assert not simshow.problems(s), simshow.problems(s)
    text = '\n'.join(simshow.report(s))
    assert '## 问题（0）' in text and '玩家真正拿到操作' in text


def test_a4_with_its_camera_scripts_taken_out_shows_black_the_whole_opening_k5():
    """The mutation of I23 (A2: the start camera never moved, black top left for a minute): the simulator's picture finds it."""
    m, t, _ = build.resolve('a4', '')
    m.scripts = [s for s in m.scripts if not any('MOVE_CAMERA_TO' in a[0] for a in s.do)]
    s = simshow.ShowSim(m, t).run(30.0)
    runs = simshow.black_runs(s)
    assert runs and runs[0][1] - runs[0][0] >= 20.0 and 'west' in runs[0][3], runs
    assert any(p.startswith('K5') for p in simshow.problems(s))


def test_every_levels_scripted_camera_stays_on_the_map_k5():
    """K5 on the simulator, every level, the opening and the first minutes after: no picture shows black."""
    bad = {}
    for lv in build.LEVELS:
        s = simshow.run(lv, until=150.0)
        runs = simshow.black_runs(s)
        if runs:
            bad[lv] = runs[:2]
    assert not bad, bad


def test_the_lines_of_every_level_come_in_time_k1():
    bad = {}
    for lv in build.LEVELS:
        s = simshow.run(lv, until=300.0)
        late = [x for x in simshow.problems(s) if x.startswith(('K1', 'I1'))]
        if late:
            bad[lv] = late[:2]
    assert not bad, bad
    assert ctx.FUNC_LATE > 0
