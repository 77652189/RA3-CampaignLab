"""Two plan words the A4 redo needs (docs/design/flow/mechanics.md 兵少补援, flow/a4.md): `兵少于 <n> <unit>、<unit>`
counts the player's own units of those kinds every frame and adds them up, and a caption written with `说` carries its
speaker and the flow script's words, so a dubbed line is found by who says what. The simulator runs the counter
actions the first one compiles to."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import glossary  # noqa: E402
import plan  # noqa: E402
import sim  # noqa: E402
import simstatic  # noqa: E402
from maps import festival  # noqa: E402
from parts import Mission, Script  # noqa: E402

TWO_KINDS = '兵少于 3 标枪兵、多功能步兵车'


def level(**more):
    """A plan on the festival map with the player's own units placed (two javelins, one IFV) plus `more`."""
    d = {'关卡': 'zz', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'},
         '开局': {'部队': [{'单位': '标枪兵', '在': 'start', '角色': 'jav a'}, {'单位': '标枪兵', '在': 'start', '角色': 'jav b'},
                          {'单位': '多功能步兵车', '在': 'start', '角色': 'ifv'},
                          {'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
         '段': [{'名字': '一'}]}
    d.update(more)
    return plan.Compiler(d).compile()


def test_fewer_than_n_counts_each_kind_every_frame_and_adds_them_up():
    m = level(规则=[{'当': TWO_KINDS, '做': ['通报 兵不够了']}])
    count = next(s for s in m.scripts if s.name == 'CNV ZZ - Count troops 1')
    assert count.when == [] and not count.once                        # every frame, from the start
    kinds = sorted(['alliedantivehicleinfantry', 'alliedantiairvehicletech1'])      # counted in this order
    p1, total = m.player('p1'), 'CNV_ZZ_Troops_1'
    assert count.do == [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', kinds[0], p1, total),
                        ('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', kinds[1], p1, total + '_1'),
                        ('COUNTER_MATH_COUNTER', total, 0, total + '_1')]
    rule = next(s for s in m.scripts if s.name == 'CNV ZZ - Rule 1')
    assert ('COUNTER', total, 0, 3) in rule.when                       # 0 is "<": fewer than 3
    assert set(kinds) <= m.spawns


def test_the_same_kinds_written_in_another_order_share_one_counter():
    m = level(规则=[{'当': TWO_KINDS, '做': ['通报 甲']}, {'当': '兵少于 2 多功能步兵车、标枪兵', '做': ['通报 乙']}])
    assert len([s for s in m.scripts if s.name.startswith('CNV ZZ - Count troops')]) == 1


def test_the_sum_is_what_the_simulator_reads_and_what_falls_drops_out():
    """Three of the two kinds alive: the rule waits; one javelin is shot: two left, fewer than 3, the level is won."""
    m = level(规则=[{'当': TWO_KINDS, '做': ['胜利']}])
    s = sim.Sim(m, script='不打').run(60)
    assert s.counters['CNV_ZZ_Troops_1'] == 3 and s.ending is None     # nothing shot: three stand, no win
    s = sim.Sim(m, script='20 摧毁 jav a').run(60)
    assert s.counters['CNV_ZZ_Troops_1'] == 2 and s.ending[0] == '赢' and s.ending[1] >= 20


def test_counter_math_and_counter_copy_in_the_simulator():
    """Retail's own uses: copy a counter, add another (code 0), take one away (code 1: transports left)."""
    m = Mission(name='T', map=festival, scripts=[
        Script('set', [], [('SET_COUNTER', 'A', 10), ('SET_COUNTER', 'B', 3), ('SET_COUNTER_TO_COUNTER', 'S', 'A'),
                           ('COUNTER_MATH_COUNTER', 'S', 0, 'B'), ('SET_COUNTER_TO_COUNTER', 'L', 'A'),
                           ('COUNTER_MATH_COUNTER', 'L', 1, 'B')])])
    s = sim.Sim(m).run(1)
    assert (s.counters['S'], s.counters['L']) == (13, 7)


def test_the_static_check_knows_who_sets_the_counter():
    """A rule waiting on the sum has its setter: the wiring finds no counter nobody sets."""
    m = level(规则=[{'当': TWO_KINDS, '做': ['通报 兵不够了']}])
    assert not [w for w in simstatic.wiring(m) if 'Troops' in w]


@pytest.mark.parametrize('bad', ['兵少于 标枪兵', '兵少于 3', '兵少于 三 标枪兵'])
def test_fewer_than_n_asks_for_a_number_and_the_kinds(bad):
    with pytest.raises(plan.PlanError):
        level(规则=[{'当': bad, '做': ['通报 x']}])


def test_an_unknown_kind_is_named_in_the_error():
    with pytest.raises(AssertionError, match='no unit called'):
        level(规则=[{'当': '兵少于 3 不存在的兵', '做': ['通报 x']}])


def test_a_spoken_caption_carries_its_speaker_and_the_flow_scripts_words():
    m = level(规则=[{'当': '开局', '做': [{'通报': '我再派两个。', '说': '沃斯', '原文': '工兵都没了？我再派两个。'},
                                         '通报 司令部：没有说话人的通报不进台词表']}])
    assert m.lines == [dict(说话人='沃斯', 原文='工兵都没了？我再派两个。', 通报='沃斯：我再派两个。',
                            字串=m.lines[0]['字串'])]
    assert m.strings[m.lines[0]['字串']] == '沃斯：我再派两个。'          # what the screen shows names the speaker
    rule = next(s for s in m.scripts if s.name == 'CNV ZZ - Rule 1')
    assert ('SHOW_MILITARY_CAPTION', m.lines[0]['字串'], plan.CAPTION) in rule.do


def test_a_spoken_caption_without_原文_looks_up_by_its_own_words_and_原文_needs_a_speaker():
    m = level(规则=[{'当': '开局', '做': [{'通报': '走吧。', '说': '科尔'}]}])
    assert m.lines[0]['原文'] == '走吧。'
    with pytest.raises(plan.PlanError, match='说'):
        level(规则=[{'当': '开局', '做': [{'通报': '走吧。', '原文': '走吧。'}]}])


def test_the_flow_scripts_unit_names_resolve_through_the_glossary():
    """The names the flow script and the voice line write (RA3-ChineseVoice GLOSSARY) are templates here."""
    assert glossary.template('激流气垫船', '盟军') == 'AlliedAntiInfantryVehicle'
    assert glossary.template('镰刀机甲', '苏联') == 'SovietAntiInfantryVehicle'
    assert glossary.template('天狗机甲', '帝国') == 'JapanAntiInfantryVehicle'
    assert glossary.template('鹰击者VX', '帝国') == 'JapanAntiAirVehicleTech1'
