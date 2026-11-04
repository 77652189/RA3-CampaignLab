"""The one dialogue queue (experimental/cnv/ctx.py Talk, ADR 0016 K1 / K2, 总控 2026-11-04): first come, first played, in
three tiers -- the ending's own line ahead of everything, a 功能 line never dropped and ahead of the 闲话, a 闲话 line that
waited CHAT_LIFE seconds dropped. Run on the simulator, which runs the product's scripts in order as the engine does."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'tests'))
import contract  # noqa: E402
import ctx  # noqa: E402
import sim  # noqa: E402
from test_plans import small  # noqa: E402

BEAT = [{'镜头': 'west field'}]                 # an act before the first line: the rule hangs on something the player sees


def said(s):
    return [(t, x) for t, k, x in s.log if k == '通报']


def test_a_gong_line_goes_ahead_and_a_late_chat_line_is_dropped():
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + ['通报 闲话一', '通报 闲话二', '通报 闲话三',
                                                  {'通报': '功能一', '功能': '是'}, {'通报': '功能二', '功能': '是'}]}])
    s = sim.Sim(m, script='5 摧毁 camp').run(60)
    texts = [x for _, x in said(s)]
    # the 功能 lines go first, in the order they came; the 闲话 behind them waited past CHAT_LIFE (two lines, 13 s) and are dropped
    assert len(texts) == 2 and texts[0].endswith('功能一') and texts[1].endswith('功能二'), texts
    assert s.counters.get('CNV_ZZ_Dropped') == 3
    starts = [t for t, _ in said(s)]
    assert all(b - a >= ctx.STRIP_CLEAR - 1e-6 for a, b in zip(starts, starts[1:])), starts    # one at a time


def test_a_chat_line_waits_up_to_chat_life_and_no_longer():
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + ['通报 闲话一', '通报 闲话二', '通报 闲话三']}])
    s = sim.Sim(m, script='5 摧毁 camp').run(60)
    texts = [x for _, x in said(s)]
    # the first at once, the second after 6.5 s (inside 10 s), the third would start at 13 s: dropped at 10 s
    assert len(texts) == 2 and texts[0].endswith('闲话一') and texts[1].endswith('闲话二'), texts
    assert s.counters.get('CNV_ZZ_Dropped') == 1


def test_first_come_first_played_inside_a_tier():
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + [{'通报': '甲', '功能': '是'}]},
                  {'当': '摧毁 camp', '做': BEAT + [{'通报': '乙', '功能': '是'}]},
                  {'当': '摧毁 camp', '做': BEAT + [{'通报': '丙', '功能': '是'}]}])
    s = sim.Sim(m, script='5 摧毁 camp').run(60)
    assert [x[-1] for _, x in said(s)] == ['甲', '乙', '丙']
    assert s.counters.get('CNV_ZZ_Dropped', 0) == 0                         # a 功能 line waits as long as it takes


def test_the_ending_line_waits_for_the_floor_and_is_said_as_the_mission_ends():
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + [{'通报': '正说着', '功能': '是'}, {'通报': '排着队', '功能': '是'}]}],
              失败=[{'当': '摧毁 camp + 0:02', '原因': '最后一句'}])
    s = sim.Sim(m, script='5 摧毁 camp').run(60)
    assert s.ending and s.ending[0] == '输'
    out = said(s)
    assert out[-1][1].endswith('最后一句') and out[-1][0] == s.ending[1], (out, s.ending)
    assert out[0][1].endswith('正说着')                                      # the line being said is finished first
    assert out[0][0] < s.ending[1]
    assert not any('排着队' in x for _, x in out)                           # ... the one in the queue is lost with the mission


def test_the_product_rule_refuses_a_lost_function_line_and_an_ending_that_does_not_wait():
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + [{'通报': '功能一', '功能': '是'}, '通报 闲话']}],
              失败=[{'当': '摧毁 camp', '原因': '输了'}])
    assert contract.said_lines_kept(m) == []
    drop = next(x for x in m.scripts if x.name.startswith('CNV ZZ - Drop'))
    drop.name = drop.name.replace('Drop 1', 'Drop 0')                       # it would drop the 功能 line
    assert any('not 闲话' in p for p in contract.said_lines_kept(m))
    drop.name = drop.name.replace('Drop 0', 'Drop 1')
    lose = next(x for x in m.scripts if x.name in m.endings)
    lose.when[:] = [c for c in lose.when if c[1] != 'CNV_ZZ_Talking']
    assert any('must wait for the floor' in p for p in contract.said_lines_kept(m))
