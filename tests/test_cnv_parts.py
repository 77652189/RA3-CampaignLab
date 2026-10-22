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
    assert [a[1] for a in shown.do] == ['Test Crew', 'Test Deck']
    assert mm.strings['SCRIPT:CNVTEST_COUNTER1'] == '乘员在甲板'
    assert len(m.scripts) == 0                                   # the mission itself untouched


def test_a8_lose_moves_the_carrier():
    m = a8.mission()
    build.MISSIONS['a8'][1]['lose'](m)
    c = m.find(a8.CARRIER)
    assert (c.x, c.y) == a8.CARRIER_AT and c.props == {'objectInitialHealth': 1}
    assert a8.mission().find(a8.CARRIER).props == {}


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
