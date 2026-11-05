"""The one dialogue queue (experimental/cnv/ctx.py Talk, ADR 0016 K1 / K2 / E6, 总控 2026-11-04). The screen has two channels:
the caption box holds ONE line (a new one replaces it, each leaves after its own seconds) and the dialogue panel stacks the
subtitles of dubbed lines. A 功能 line is a caption shown the frame its event comes (never dropped, never late: FUNC_LATE),
a 闲话 line nobody recorded is a caption that waits for the box, a 闲话 line that waited CHAT_LIFE seconds is dropped, the
ending's own line waits for the floor. Run on the simulator, which runs the product's scripts in order as the engine does."""
from test_plans import small  # (puts experimental/cnv on the path)  # noqa: I001
import contract  # noqa: E402
import ctx  # noqa: E402
import sim  # noqa: E402

BEAT = [{'镜头': 'west field'}]                 # an act before the first line: the rule hangs on something the player sees


def said(s):
    return [(t, x) for t, k, x in s.log if k == '通报']


def run(do, until=60, **kw):
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + do}], **kw)
    return sim.Sim(m, script='5 摧毁 camp').run(until)


def test_a_gong_line_is_up_the_frame_its_event_comes_and_the_chat_waits_for_the_box():
    s = run(['通报 闲话一', '通报 闲话二', '通报 闲话三', {'通报': '功能一', '功能': '是'}, {'通报': '功能二', '功能': '是'}])
    out = said(s)
    # the 功能 lines are up at the event (the second ctx.FUNC_HOLD after the first, so the first is read), ahead of the 闲话
    assert [x[-3:] for _, x in out[:2]] == ['功能一', '功能二'] and out[0][0] == 5.0 and out[1][0] == 5.0 + ctx.FUNC_HOLD, out
    assert not s.late_captions()
    # the 闲话 waited for the box (the 功能 caption's six seconds): the first came after them, the rest waited past CHAT_LIFE
    assert [x[-3:] for _, x in out[2:]] == ['闲话一'] and out[2][0] >= out[1][0] + 6.0 - 1e-6, out
    assert s.counters.get('CNV_ZZ_Dropped') == 2


def test_a_chat_caption_is_read_to_its_turn_and_the_next_waits_for_the_box():
    s = run(['通报 闲话一', '通报 闲话二', '通报 闲话三'])
    out = said(s)
    # each takes the box for its turn (a caption-only line holds the floor for its reading time, no more) and none is cut
    # off; a caption is not panel text, so all three are said, one after the other
    assert [x[-3:] for _, x in out] == ['闲话一', '闲话二', '闲话三'], out
    assert all(b - a >= 4.0 - 1e-6 for (a, _), (b, _) in zip(out, out[1:])), out
    assert not s.counters.get('CNV_ZZ_Dropped')


def test_a_chat_line_waits_up_to_chat_life_and_no_longer():
    s = run(['通报 闲话一', '通报 闲话二', '通报 闲话三', '通报 闲话四', '通报 闲话五'])
    out = said(s)
    # two lines fill the strip (5 and 9); the rest wait for it to clear, and what has waited CHAT_LIFE is dropped: no line is
    # said that waited longer than that (give or take a frame), the ones said are in the order they asked, none is lost
    names = [x[-3:] for _, x in out]
    asked = ['闲话一', '闲话二', '闲话三', '闲话四', '闲话五']
    assert names[:2] == asked[:2] and names == sorted(names, key=asked.index), out
    assert all(t - 5.0 <= ctx.CHAT_LIFE + 0.2 for t, _ in out), out
    assert len(out) + s.counters.get('CNV_ZZ_Dropped', 0) == 5 and len(out) < 5, (out, s.counters)


def test_first_come_first_played_inside_a_tier_and_none_is_cut_short():
    s = run([{'通报': '甲', '功能': '是'}, {'通报': '乙', '功能': '是'}, {'通报': '丙', '功能': '是'}])
    out = said(s)
    assert [x[-1] for _, x in out] == ['甲', '乙', '丙']
    # each read FUNC_HOLD at least, then the next caption replaces it (one sentence at a time; none is panel text)
    assert [round(t - 5.0, 3) for t, _ in out] == [0.0, ctx.FUNC_HOLD, 2 * ctx.FUNC_HOLD]
    assert not s.late_captions() and s.counters.get('CNV_ZZ_Dropped', 0) == 0


def test_a_chat_caption_does_not_cut_off_a_gong_caption_and_a_gong_one_replaces_the_chat():
    s = run([{'通报': '功能一', '功能': '是'}, '通报 闲话一'])
    assert s.box_log[0][1] - s.box_log[0][0] == 6.0 and s.box_log[1][0] >= s.box_log[0][1] - 1e-6, s.box_log   # chat after
    t = 5.0 + 1.0
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + ['通报 闲话一']}, {'当': '摧毁 camp + 0:02', '做': BEAT + [{'通报': '功能', '功能': '是'}]}])
    s = sim.Sim(m, script='5 摧毁 camp').run(30)
    assert s.box_at(t) is not None and s.box_at(t).endswith('闲话一')
    assert s.box_at(8.0).endswith('功能'), s.box_log               # the 功能 line replaced it at once (7 s)


def test_the_ending_line_waits_for_the_floor_and_is_said_as_the_mission_ends():
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + ['通报 正说着', '通报 排着队']}],
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
    assert contract.said_lines_kept(m) == [] and contract.said_once_and_on_time(m) == []
    drop = next(x for x in m.scripts if x.name.startswith('CNV ZZ - Drop'))
    drop.name = drop.name.replace('Drop 1', 'Drop 0')                       # it would drop line 0 (the 功能 one)
    assert any('not 闲话' in p for p in contract.said_lines_kept(m))
    drop.name = drop.name.replace('Drop 0', 'Drop 1')
    lose = next(x for x in m.scripts if x.name in m.endings)
    lose.when[:] = [c for c in lose.when if c[1] != 'CNV_ZZ_Talking']
    assert any('must wait for the floor' in p for p in contract.said_lines_kept(m))


def test_the_product_rule_refuses_a_gong_caption_that_waits_and_a_line_on_both_channels():
    m = small(规则=[{'当': '摧毁 camp', '做': BEAT + [{'通报': '功能一', '功能': '是'}]}])
    now = next(x for x in m.scripts if ' - Now ' in x.name)
    assert contract.said_once_and_on_time(m) == []
    now.when.append(('FLAG', 'CNV_ZZ_Talking', 0))                        # it would wait for the floor: late
    assert any('is late' in p for p in contract.said_once_and_on_time(m))
    now.when.pop()
    m.subtitles['CNV_X'] = next(a[1] for x in m.scripts for a in x.do if a[0] == 'SHOW_MILITARY_CAPTION')
    out = contract.said_once_and_on_time(m)                                # a recording whose subtitle is the caption's words
    assert any('one channel' in p for p in out) and any('the voice pack' in p or 'subtitle' in p for p in out), out


def test_no_more_than_strip_max_sentences_are_on_screen_at_once():
    # I1 (CampShell 2026-11-05, second round): a caption on top and a different line in the panel at the same time
    import plan
    import strip
    s = sim.simulate('a4', until=200.0)
    assert len(strip.lines(s)) >= 20 and not strip.too_deep(s), strip.too_deep(s)
    saved = ctx.STRIP_MAX
    ctx.STRIP_MAX = plan.STRIP_MAX = 99      # the queue without the gate: a caption and a subtitle meet, and the reading says so
    try:
        s = sim.simulate('a4', until=200.0)
    finally:
        ctx.STRIP_MAX = plan.STRIP_MAX = saved
    assert strip.too_deep(s), strip.lines(s)
