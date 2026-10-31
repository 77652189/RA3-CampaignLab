"""The horn device (experimental/cnv/devices/horn.py, A4's festival horn): the detour table sends a shut street's wave
to an open street, two shut streets bound for the same open one arrive at least 10 s apart; and a plan with the
device compiles into the scripts it should (a shut mouth keeps its wave, the Ghost King smashes the nearest wall)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import plan  # noqa: E402
from devices import horn  # noqa: E402

ORDER = ['L', '1', '2']                         # the back lane, plaza 1, plaza 2: west to east
DELAY = {'L': {'1': 10, '2': 20}, '1': {'L': 10, '2': 10}, '2': {'1': 20, 'L': 30}}
STREETS = {'后巷': {'点': 'lane foot', '出': 'lane foot', '偏移': [0, 160]},
           '一号': {'点': 'inside 1', '出': 'plaza 1'},
           '二号': {'点': 'inside 2', '出': 'plaza 2', '从': 2}}
MOUTHS = {'北坡口': {'点': 'north mouth', '出': 'north mouth', '偏移': [0, 120]},
          '三号广场': {'点': 'inside 3', '出': 'plaza 3'},
          '东街口': {'点': 'east mouth', '出': 'east mouth', '偏移': [0, 150]}}
TABLE = {'后巷': {'一号': 10, '二号': 20}, '一号': {'后巷': 10, '二号': 10}, '二号': {'一号': 20, '后巷': 30}}


def level(**more):
    d = {'关卡': 'zz', '地图': 'sapporo', '阵营': {'我': '盟军', '敌': '帝国'},
         '开局': {'部队': [{'单位': '冰幕工兵', '数量': 2, '在': 'start', '角色': 'engineer'}]}, '段': [{'名字': '一'}],
         '机关': {'车队': {'类型': '车队', '出发': '开局 + 0:10'},
                 '雪祭': {'类型': '号角', '车队': '车队', '间隔': ['0:45/0:30/0:20', 50, 45, 50, 45],
                        '每街一波': {'帝国武士': 2, '坦克杀手': 2}, '街': STREETS, '绕路': TABLE, '口': MOUTHS,
                        '鬼王': {'从': 3, '数量': '1/1/2'}}}}
    d.update(more)
    return plan.Compiler(d).compile()


def test_a_shut_street_goes_to_the_open_one_it_is_quickest_to():
    assert horn.route(DELAY, ORDER, ORDER, set(), '1') == ('1', 0)
    assert horn.route(DELAY, ORDER, ORDER, {'L'}, 'L') == ('1', 10)
    assert horn.route(DELAY, ORDER, ORDER, {'2'}, '2') == ('1', 20)
    assert horn.route(DELAY, ORDER, ORDER, {'L', '1'}, 'L') == ('2', 20)      # only plaza 2 is open
    assert horn.route(DELAY, ORDER, ORDER, {'L', '1'}, '1') == ('2', 10)
    assert horn.route(DELAY, ORDER, ORDER, {'1', '2'}, '2') == ('L', 30)


def test_a_street_not_open_yet_takes_no_wave():
    """The first horn has only the lane and plaza 1: with plaza 1 shut the lane's wave is not sent to plaza 2."""
    assert horn.route(DELAY, ORDER, ['L', '1'], {'1'}, '1') == ('L', 10)
    assert horn.route(DELAY, ORDER, ['L', '1'], {'L', '1'}, '1') is None


def test_two_shut_streets_bound_for_the_same_one_arrive_10_s_apart():
    horn.check_delays(DELAY, ORDER)
    bad = {**DELAY, '2': {'1': 15, 'L': 30}}                        # lane -> 1 is 10, plaza 2 -> 1 is 15: 5 apart
    with pytest.raises(AssertionError, match='apart'):
        horn.check_delays(bad, ORDER)
    with pytest.raises(AssertionError, match='missing'):
        horn.check_delays({'L': {'1': 10}, '1': {}, '2': {}}, ORDER)


def test_the_plans_table_passes():
    names = list(STREETS)
    horn.check_delays({s: {o: float(t) for o, t in row.items()} for s, row in TABLE.items()}, names)


def test_the_device_compiles_with_its_horns_streets_and_mouths():
    m = level()
    names = [s.name for s in m.scripts]
    assert len(names) == len(set(names))
    for want in ('CNV ZZ - Horn V start easy', 'CNV ZZ - Horn V1', 'CNV ZZ - Horn V5', 'CNV ZZ - Horn L start hard', 'CNV ZZ - Frozen V1 holds',
                 'CNV ZZ - Route V1 V1 open', 'CNV ZZ - Release L1 L1', 'CNV ZZ - Keep L3 L3',
                 'CNV ZZ - King 3-1 lands', 'CNV ZZ - King 5-2 smashes'):
        assert want in names, want
    assert not [n for n in names if n.startswith('CNV ZZ - Out V1 V3')]    # plaza 2 does not take part in horn 1
    assert [n for n in names if n.startswith('CNV ZZ - Out V2 V3 at')]


def test_a_shut_mouth_keeps_its_wave_and_makes_it_when_the_ice_is_gone():
    m = level()
    by = {s.name: s for s in m.scripts}
    frozen = 'CNV_ZZ_Frozen_L1'
    kept = by['CNV ZZ - Keep L2 L1']
    assert ('FLAG', frozen, 1) in kept.when and ('SET_FLAG', 'CNV_ZZ_Kept_L2_L1', 1) in kept.do
    release = by['CNV ZZ - Release L2 L1']
    assert ('FLAG', 'CNV_ZZ_Kept_L2_L1', 1) in release.when and ('FLAG', frozen, 0) in release.when
    assert sum(a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT' for a in release.do) == 4       # 2 + 2
    out = by['CNV ZZ - Out L2 L1']
    assert ('FLAG', frozen, 0) in out.when


def test_the_ghost_king_comes_from_the_third_horn_and_two_on_hard():
    m = level()
    by = {s.name: s for s in m.scripts}
    assert 'CNV ZZ - Boats 2 easy' not in by and 'CNV ZZ - Boats 3 easy' in by
    assert sum(a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT' for a in by['CNV ZZ - Boats 3 easy'].do) == 1
    assert sum(a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT' for a in by['CNV ZZ - Boats 3 hard'].do) == 2
    assert any(a[0] == 'SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER' for a in by['CNV ZZ - Ghost pick'].do)


def test_the_plan_can_start_stop_and_ask_the_horns():
    m = level(规则=[{'当': '开局 + 0:01', '做': ['雪祭.开 街']}, {'当': '雪祭.号角 2', '做': ['通报 第二声', '雪祭.停']},
                  {'当': '雪祭.冻住 一号', '做': ['通报 冻住了']}, {'当': '雪祭.口号角 1', '做': ['雪祭.开 口']}])
    by = {s.name: s for s in m.scripts}
    start = next(s for s in m.scripts if ('SET_FLAG', 'CNV_ZZ_Horn_V_Start', 1) in s.do)
    assert ('SET_COUNTER', 'CNV_ZZ_Horn_V_N', 0) in start.do
    assert ('COUNTER', 'CNV_ZZ_Horn_V_N', 3, 2) in next(s for s in m.scripts if ('HIDE_COUNTDOWN_TIMER', 'CNV ZZ Horn') in s.do
                                                         and s.when and s.when[0][0] == 'COUNTER').when
    with pytest.raises(plan.PlanError):
        level(规则=[{'当': '开局 + 0:01', '做': ['雪祭.开 天']}])
