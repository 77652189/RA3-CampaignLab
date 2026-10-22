"""The decoupled build layer (experimental/cnv): unit variants keep apart, a check merges into its mission, the
verdict follows the counters, the counter reader reads back its calibration -- all without the game."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'cnv'))
sys.path.insert(1, os.path.join(ROOT, 'experimental', 'testbench'))
import build  # noqa: E402
import lint  # noqa: E402  (experimental/campaign, put on the path by parts)
import parts  # noqa: E402
from missions import a8, liberty_bench  # noqa: E402
from units import liberty as lib  # noqa: E402


def test_liberty_variants_keep_apart():
    a, b = lib.liberty('CNV_Liberty_A', tag='A'), lib.liberty('CNV_Liberty_B', tag='B')
    assert not set(a.names.values()) & set(b.names.values())
    assert 'SpecialPower_CNV_ChronoDeck_B' not in a.xml + a.files['CNV_Liberty_A_UI.xml']
    assert all(n.split(':')[1] in b.xml + b.files['CNV_Liberty_B_UI.xml'] for n in b.link)


def test_riders_left_out_of_the_deck(tmp_path):
    u = lib.liberty(riders='CNV_DeckGuardian')
    assert u.xml.count('<ExcludeThing>CNV_DeckGuardian</ExcludeThing>') == 3        # the filter and both templates
    assert '<ExcludeThing>' not in lib.liberty().xml
    p = tmp_path / 'CNV_Liberty.xml'
    p.write_text(u.xml, encoding='utf-8')
    assert [f for f in lint.check([str(p)]) if f[0] == 'ERROR'] == []


def test_check_merges_into_its_mission():
    m = liberty_bench.mission(riders=True)
    t = build.MISSIONS['liberty_riders'][1]['jump'](m)
    mm = parts.merged(m, t)
    assert len(mm.objects) == len(m.objects) and 'Test Jump Target' in mm.waypoints
    shown = [s for s in mm.scripts if s.name == 'Test - counters'][0]
    assert [a[1] for a in shown.do] == ['Test Crew', 'Test Landed', 'Test Deck']
    assert mm.strings['SCRIPT:CNVTEST_COUNTER2'] == '乘员在甲板'
    assert len(m.scripts) == 0                                   # the mission itself untouched


def test_areas_count_and_merge():
    m = liberty_bench.mission(riders=True)
    t = build.MISSIONS['liberty_riders'][1]['jump'](m)
    mm = parts.merged(m, t)
    assert list(mm.areas) == ['Test Landing'] and not m.areas
    assert parts.missing_areas(mm) == []
    landed = [s for s in mm.scripts if s.name.startswith('Test - count Test Landed')]
    assert len(landed) == 9 and landed[3].when[0][1:] == ('Player_1', 2, 3, m.role('crew').template, 'Test Landing')
    assert landed[8].when[0][1:3] == ('Player_1', 3) and landed[8].do == [('SET_COUNTER', 'Test Landed', 8)]
    del mm.areas['Test Landing']
    assert len(parts.missing_areas(mm)) == 9                     # assemble refuses to build that
    ab, _ = build.PAIRS['liberty_ride_ab']()
    b = parts.side_by_side(parts.Mission(areas={'X': parts.square(0, 0, 10)}), parts.Mission(areas={'Y': [(1, 2)]}), 5)
    assert b.areas == {'X': [(-10, -10), (10, -10), (10, 10), (-10, 10)], 'Y': [(6, 2)]}


def test_trigger_areas_round_trip():
    import mapscript
    m = object.__new__(mapscript.MapFile)
    m.nodes = [mapscript.Node('TriggerAreas', 1, b'\0\0\0\0', [])]
    areas = {'Test Landing': parts.square(1480, 2315, 150), 'B': [(1.5, 2.5), (3, 4), (5, 6)]}
    m.set_trigger_areas(areas)
    assert m.trigger_areas() == {k: [(float(x), float(y)) for x, y in v] for k, v in areas.items()}
    assert len(m.nodes[0].head) == 4 + sum(2 + len(k) + 2 + 8 + 8 * len(v) + 4 for k, v in areas.items())


def test_a8_assault_same_for_both():
    names = {}
    for build_name in ('a8', 'a8_control'):
        m, t, mod = build.resolve(build_name, 'assault')
        names[build_name] = mod
        mm = parts.merged(m, t)
        assert not [s for s in mm.scripts if s.name in ('CNV A8 - Win', 'CNV A8 - Lost')]
        assert parts.missing_areas(mm) == []
        labels = [label for _, label in t.counters]
        assert labels[:3] == ['平台剩余', '敌方铁锤', '守护者']
        jumps = [s for s in t.scripts if s.name.startswith('Test - jump ')]
        assert len(jumps) == (3 if build_name == 'a8' else 0) and labels[3:] == (['自由号'] if jumps else ['多功能车'])
        assert t.bench[0][0] == 'bench_camera'
        order = [s.name for s in t.scripts]
        assert order.index('Test - order again') > order.index('Test - attack 3')   # the tick resets after the orders
    assert names == {'a8': 'CampA8Assault', 'a8_control': 'CampA8CAssault'}
    assert parts.kindof('VEHICLE')[2] == 'VEHICLE'


def test_a8_lose_moves_the_carrier():
    m = a8.mission()
    build.MISSIONS['a8'][1]['lose'](m)
    c = m.find(m.role('carrier').name)
    assert (c.x, c.y) == m.site('west shore') and c.props == {'objectInitialHealth': 1}
    assert a8.mission().find(a8.CARRIER).props == {}


def test_every_build_keeps_the_contract():
    """Every object placed by a map site, every name a script uses published (offline: what assemble asserts)."""
    for n, (_, checks) in build.MISSIONS.items():
        for c in [''] + list(checks):
            m, t, _ = build.resolve(n, c)
            assert parts.contract(parts.merged(m, t)) == [], (n, c)
    for n in build.PAIRS:
        m, t, _ = build.resolve(n, '')
        assert parts.contract(parts.merged(m, t)) == [], n
    assert build.show('a8', 'assault').endswith('contract: ok')


def test_contract_catches_what_nobody_published():
    from maps import island
    m = a8.mission()
    m.objects.append(parts.Obj('AlliedWarFactory', 100, 100))                          # raw coordinates
    m.scripts.append(parts.Script('X', [('NAMED_DESTROYED', 'UNIT - Nobody')],          # no such object
                                  [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', a8.CARRIER, 'SpecialPower_X', 'WP X'),
                                   ('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', 'JapanNavalYard', 'Player_9', 'c'),
                                   ('SHOW_MILITARY_CAPTION', 'SCRIPT:NONE', 1.0)]))
    got = parts.contract(m)
    assert len(got) == 7, got
    assert any('raw coordinates' in p for p in got) and any("object 'UNIT - Nobody'" in p for p in got)
    assert any("power 'SpecialPower_X'" in p for p in got) and any("waypoint 'WP X'" in p for p in got)
    assert any("template 'JapanNavalYard'" in p for p in got) and any("player 'Player_9'" in p for p in got)
    assert any("string 'SCRIPT:NONE'" in p for p in got)
    other = lib.liberty('CNV_Other', tag='O')                                           # someone else's ability
    m2 = parts.Mission(name='X', map=island, units=[a8.mission().units[0], other])
    m2.put(m2.units[0].id, 'west shore', name='C', role='carrier')
    m2.scripts.append(parts.Script('Y', [], [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'C', other.abilities['jump'], 'W')]))
    m2.waypoints['W'] = m2.site('east 1')
    assert parts.contract(m2) == [f"Y: C (CNV_Liberty) fired {other.abilities['jump']}, an ability of CNV_Other"]
    import pytest
    with pytest.raises(AssertionError, match='no site'):
        m2.put('AlliedWarFactory', 'the moon')
    with pytest.raises(AssertionError, match='publishes no ability'):
        m2.ability('carrier', 'fly')


def test_ab_pair():
    m, t = build.PAIRS['liberty_ride_ab']()
    ids = [u.id for u in m.units]
    assert len(ids) == len(set(ids)) == 4
    carriers = [o for o in m.objects if o.template.startswith('CNV_Liberty')]
    assert [o.name for o in carriers] == ['UNIT - CNV Liberty', 'UNIT - CNV Liberty B']
    assert carriers[1].x - carriers[0].x == 500
    assert len(t.counters) == 4


def test_judge():
    t = parts.Test(counters=[('a', 'A'), ('b', 'B')], expect=[('A', 10, '>=', 3), ('B', 0, '==', 1)])
    v = build.judge(t, [(5, [1, 1]), (12, [4, 1]), (15, [3, None])])
    assert [ok for ok, _ in v] == [True, False]                  # B unread at s15 fails it
    assert build.judge(parts.Test(counters=[('a', 'A')], expect=[('A', 99, '==', 1)]), [(5, [1])])[0][0] is False
    ended = [(5, [1]), (8, [0]), (9, [None])]                    # the mission ended: its counters went with it
    assert build.judge(parts.Test(counters=[('a', 'A')], expect=[('A', 6, 'ever==', 0)]), ended)[0][0] is True


def test_judge_until_and_the_bench_round_trip():
    t = parts.Test(counters=[('a', 'A')], expect=[('A', 0, '==', 0, 15), ('A', 19, '>=', 3)])
    lines, status = build.report(t, build.parse_counters('s3: 0 | s12: 0 | s18: 2 | s21: 4'))
    assert status == 0 and lines[-1] == 'RESULT PASS'           # s18's 2 is in neither window
    assert lines[1] == 'PASS A == 0 from s0 until s15: s3-s12: 0'
    assert lines[0] == 'counters (A): s3-s12: 0 | s18: 2 | s21: 4'
    assert build.report(t, build.parse_counters('s3: 0 | s14: 1 | s21: 4'))[1] == 1
    plan = build.steps('CampX', build.resolve('liberty_riders', 'jump')[1])
    assert plan[0] == ['bench_start', {'mod': 'CampX', 'look': False}] and plan[-1] == ['bench_counters', {'lines': 3}]
    assert 'liberty_riders --check jump -> CampLibRJump' in build.listing()


def test_every_build_name_fits():
    """Mod names over 15 characters crash the game before the main menu (bench 2026-10-21)."""
    names = [build.resolve(n, c)[2] for n, (_, checks) in build.MISSIONS.items() for c in [''] + list(checks)]
    names += [build.resolve(n, '')[2] for n in build.PAIRS]
    assert all(len(n) <= parts.MAX_NAME for n in names), [n for n in names if len(n) > parts.MAX_NAME]


def test_judge_mission_ended():
    t = parts.Test(counters=[('a', 'A')], expect=[(build.ENDED, 5, '', None)])
    assert build.judge(t, [(1, [1]), (4, [1]), (6, [None])])[0][0] is True
    assert build.judge(t, [(1, [1]), (6, [1])])[0][0] is False
    assert build.judge(t, [(6, [None])])[0][0] is False                  # never up: no counters at all, not an end


def test_counter_reader_reads_its_calibration():
    import counters
    frames = os.path.join(ROOT, 'work', 'testbench', 'runs')
    shots = sorted(d for d in os.listdir(frames) if d.startswith('CampDigits_mcp_')) if os.path.isdir(frames) else []
    if not shots or len(counters.templates()) < 10:
        import pytest
        pytest.skip('no calibration frame or templates on this machine (work/ is local)')
    from PIL import Image
    im = Image.open(os.path.join(frames, shots[-1], '0001.png')).convert('RGB')
    assert counters.read(im, 3) == counters.CALIBRATION
    assert counters.read_line(im, counters.line_box(4)) is None   # under the bottom bar: nothing to read
    x1 = counters.glyphs(im, counters.line_box(2))[-1][1]         # a sparkle 6 px right of the 90's 0
    im.putpixel((x1 + 6, counters.line_box(2)[1] + 7), (255, 255, 120))
    assert counters.read_line(im, counters.line_box(2)) == 90
