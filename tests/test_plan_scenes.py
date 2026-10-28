"""The plan words for what the player sees (docs/design/teardowns/layout.md 3): a phase's 过场 (input off, the camera
led, steps one after another, the input back), 揭开 / 收回 / 揭全图, a goal's 亮出 <condition>, a wave that waits for the
player to push on -- and the design check's notes on them."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import plan  # noqa: E402
import plancheck  # noqa: E402

SCENE = [{'镜头': 'west field', '秒': 3}, {'揭全图': '看一眼'}, {'跟随': 'camp', '秒': 4}, {'停': 2}, '通报 看好了']


def plan_of(**more):
    d = {'关卡': 'zz', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'},
         '开局': {'资金': 0, '部队': [{'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
         '段': [{'名字': '一'}]}
    d.update(more)
    return d


def small(**more):
    return plan.Compiler(plan_of(**more)).compile()


def named(m, start):
    return [s for s in m.scripts if s.name.startswith(start)]


def waits_for(m, s):
    """The seconds a script waits after its phase began: the wait script that starts its timer says."""
    started = next(c[1] for c in s.when if c[0] == 'FLAG' and '_Wait_' in c[1])
    start = next(w for w in m.scripts if ('SET_FLAG', started, 1) in w.do)
    return next(a[2] for a in start.do if a[0] == 'SET_MILLISECOND_TIMER')


def test_a_scene_holds_the_input_and_leads_the_camera():
    m = small(段=[{'名字': '一', '过场': SCENE, '目标': ['甲']}], 目标={'甲': {'标记': ['camp']}})
    first = next(s for s in m.scripts if s.name == 'CNV ZZ - Phase 1').do
    assert first[:3] == [('SET_FLAG', 'CNV_ZZ_Phase_1', 1), ('DISABLE_INPUT',), ('CAMERA_LETTERBOX_BEGIN',)]
    assert ('MOVE_CAMERA_TO', 'CNV ZZ At west field', 3.0, 0.0, 1.0, 1.0) in first
    steps = {waits_for(m, s): s.do for s in named(m, 'CNV ZZ - Phase 1 scene')}
    camp = m.cast['camp'].name
    assert set(steps) == {3.0, 7.0, 9.0}
    assert steps[3.0] == [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('CAMERA_FOLLOW_NAMED', camp, 0, plan.FOLLOW_AT)]
    assert steps[7.0] == [('CAMERA_STOP_FOLLOW',)]
    assert steps[9.0][0][0] == 'SHOW_MILITARY_CAPTION'
    assert steps[9.0][1:] == [('ENABLE_INPUT',), ('CAMERA_LETTERBOX_END',), ('CAMERA_STOP_FOLLOW',),
                              ('MAP_REVEAL_ALL_UNDO_PERM', m.player('p1')), ('SET_FLAG', 'CNV_ZZ_Scene_1', 1)]
    assert m.facts['过场 一'] == 9.0
    goal = named(m, 'CNV ZZ - Phase 1 goal 1')[0]
    assert waits_for(m, goal) == 9.0 + plan.REVEAL_FIRST         # the goals once the player has the input back


def test_after_the_scene():
    m = small(段=[{'名字': '一', '过场': SCENE}], 规则=[{'当': '过场 一 结束', '做': ['通报 到你了']}])
    assert ('FLAG', 'CNV_ZZ_Scene_1', 1) in named(m, 'CNV ZZ - Rule 1')[0].when
    with pytest.raises(plan.PlanError):
        small(规则=[{'当': '过场 一 结束', '做': ['通报 没有过场']}])


def test_the_camera_on_one_of_the_plans_own_and_a_flash():
    m = small(规则=[{'当': '开局', '做': [{'镜头': 'camp', '秒': 2}, {'闪烁': 'camp'}]}])
    camp = m.cast['camp'].name
    assert named(m, 'CNV ZZ - Rule 1')[0].do == [('MOVE_CAMERA_TO_NAMED', camp, 2.0, 0.0, 1.0, 1.0),
                                                 ('NAMED_FLASH', camp, plan.FLASHES)]


def test_reveal_for_good_and_undo_it():
    m = small(规则=[{'当': '开局', '做': [{'揭开': 'north base', '永久': True}, {'揭开': 'west field', '半径': 500}]},
                  {'当': '开局 + 0:10', '做': [{'收回': 'north base'}, {'揭全图': '永久'}]},
                  {'当': '开局 + 0:20', '做': [{'收回': '全图'}]}])
    p1 = m.player('p1')
    r = m.map.SITES['north base'].r or plan.SIGHT
    assert named(m, 'CNV ZZ - Rule 1')[0].do == [
        ('MAP_REVEAL_PERMANENTLY_AT_WAYPOINT', 'CNV ZZ At north base', r, p1, 'CNV ZZ Sight north base'),
        ('MAP_REVEAL_AT_WAYPOINT', 'CNV ZZ At west field', 500.0, p1)]
    assert named(m, 'CNV ZZ - Rule 2')[0].do == [('MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT', 'CNV ZZ Sight north base'),
                                                 ('MAP_REVEAL_ALL_PERM', p1)]
    assert named(m, 'CNV ZZ - Rule 3')[0].do == [('MAP_REVEAL_ALL_UNDO_PERM', p1)]


@pytest.mark.parametrize('bad', [{'规则': [{'当': '开局', '做': [{'揭全图': '看一眼'}]}]},
                                 {'规则': [{'当': '开局', '做': [{'跟随': 'camp'}]}]},
                                 {'段': [{'名字': '一', '过场': ['通报 没有时间']}]},
                                 {'段': [{'名字': '一', '过场': [{'跟随': 'west field'}]}]},
                                 {'规则': [{'当': '开局', '做': [{'揭开': 'nowhere'}]}]}])
def test_scene_words_misused_are_errors(bad):
    with pytest.raises((plan.PlanError, AssertionError)):
        small(**bad)


def test_a_goal_shown_once_the_player_gets_near():
    m = small(段=[{'名字': '一', '目标': ['甲', '乙']}],
              目标={'甲': {'标记': ['camp']}, '乙': {'奖励': True, '标记': ['camp'], '亮出': '进入 west field'}})
    assert len(named(m, 'CNV ZZ - Phase 1 goal')) == 1                  # only 甲 on the clock
    shown = named(m, 'CNV ZZ - Goal Bonus01 shown')
    assert len(shown) == 1
    assert ('FLAG', 'CNV_ZZ_Phase_1', 1) in shown[0].when
    assert any(c[0] == 'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA' for c in shown[0].when)
    assert ('SET_MISSION_OBJECTIVE_STATUS', 'Bonus01 - CNV ZZ', 1) in shown[0].do
    # in no phase, only 亮出: still shown, and the design check knows it
    d = plan_of(目标={'甲': {'标记': ['camp'], '亮出': '攻击 camp'}})
    assert named(plan.Compiler(d).compile(), 'CNV ZZ - Goal Objective01 shown')
    assert not [t for lvl, t in plancheck.design_check(d) if lvl == '问题' and '亮出' in t]


def test_the_first_enemy_waits_for_the_player():
    """Already a wave's 开始 can be what the player does (layout.md 3: retail, 22 of 40)."""
    m = small(进攻=[{'名字': 'w', '开始': '进入 west field', '兵': {'帝国武士': 2}, '从': 'north base', '打': 'west field'}])
    start = [s for s in m.scripts if s.name.startswith('CNV ZZ - Wave 1') and
             any(c[0] == 'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA' for c in s.when)]
    assert start


def test_the_design_check_on_scenes_shown_goals_and_the_first_enemy():
    timed = [{'名字': 'w', '开始': '开局 + 0:30', '兵': {'帝国武士': 2}, '从': 'north base', '打': 'west field'}]
    notes = lambda d: {t.split('：')[0]: lvl for lvl, t in plancheck.design_check(d)}   # noqa: E731
    bare = notes(plan_of(进攻=timed, 目标={'乙': {'奖励': True}}, 段=[{'名字': '一', '目标': ['乙']}]))
    assert bare['开场过场'] == '注意' and bare['奖励目标随推进冒出来'] == '注意'
    assert any(k.startswith('开局没有基地，第一股敌人') for k in bare)
    led = notes(plan_of(段=[{'名字': '一', '过场': SCENE, '目标': ['乙']}],
                        目标={'乙': {'奖励': True, '亮出': '进入 west field'}},
                        进攻=[dict(timed[0], 开始='进入 west field')]))
    assert led['开场过场'] == '符合' and led['奖励目标随推进冒出来'] == '符合'
    assert not any(k.startswith('开局没有基地') for k in led)
    with_base = plan_of(进攻=timed)
    with_base['开局']['部队'].append({'单位': '建造厂', '在': 'west field'})
    assert not any(t.startswith('开局没有基地') for _, t in plancheck.design_check(with_base))
    sheet = plancheck.beat_sheet(plan_of(段=[{'名字': '一', '过场': SCENE}]))
    assert '9 秒后交还控制' in sheet
