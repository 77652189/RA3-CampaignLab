"""The plan words for what the player sees (docs/design/teardowns/layout.md 3): a phase's 过场 (input off, the camera
led, steps one after another, the input back), 揭开 / 收回 / 揭全图, a goal's 亮出 <condition>, a wave that waits for the
player to push on -- and the design check's notes on them."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import contract  # noqa: E402
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
    assert first[:4] == [('SET_FLAG', 'CNV_ZZ_Phase_1', 1), ('SET_FLAG', 'CNV_ZZ_InScene', 1), ('DISABLE_INPUT',),
                         ('CAMERA_LETTERBOX_BEGIN',)]
    move = next(a for a in first if a[0] == 'MOVE_CAMERA_TO')
    assert move[2:] == (3.0, 0.0, 1.0, 1.0) and move[1].startswith('CNV ZZ Cam west field ')     # a view point (K5)
    assert move[1] in m.views and contract.camera_outside_the_view(m) == []
    steps = {waits_for(m, s): s.do for s in named(m, 'CNV ZZ - Phase 1 scene')}
    camp = m.cast['camp'].name
    assert set(steps) == {3.0, 7.0, 13.0}           # the closing line (at 9 s, a script of its own) is said before the hand-back
    line = named(m, 'CNV ZZ - Phase 1 line')[0]
    assert waits_for(m, line) == 9.0 and ('FLAG', 'CNV_ZZ_Talking', 0) in line.when
    assert steps[3.0] == [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('CAMERA_FOLLOW_NAMED', camp, 0, plan.FOLLOW_AT)]
    assert steps[7.0] == [('CAMERA_STOP_FOLLOW',)]
    assert any(a[0] == 'SHOW_MILITARY_CAPTION' for a in line.do)
    # a 镜头's own reveal at its site while the scene runs (the camera sees what is not explored), shrouded at the hand-back
    reveal = next(a for a in first if a[0] == 'MAP_REVEAL_PERMANENTLY_AT_WAYPOINT')
    assert reveal[1] == 'CNV ZZ At west field' and reveal[3:] == (m.player('p1'), 'CNV ZZ Look west field')
    assert plan.LOOK_MIN <= reveal[2] <= plan.LOOK_MAX
    assert steps[13.0][1:] == [('ENABLE_INPUT',), ('CAMERA_LETTERBOX_END',), ('CAMERA_STOP_FOLLOW',),
                              ('MAP_REVEAL_ALL_UNDO_PERM', m.player('p1')),
                              ('MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT', 'CNV ZZ Look west field'),
                              ('SET_FLAG', 'CNV_ZZ_Scene_1', 1)]
    assert m.facts['过场 一'] == 13.0
    goal = named(m, 'CNV ZZ - Phase 1 goal 1')[0]
    assert waits_for(m, goal) == 13.0 + plan.REVEAL_FIRST         # the goals once the player has the input back


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
                                 {'段': [{'名字': '一', '过场': [{'揭全图': '看一眼'}]}]},
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


def test_lines_in_a_scene_are_said_one_at_a_time():
    """User 2026-11-03 ("一句说完了之后再继续说", scenes too): each line takes the floor for its own turn (a
    caption its reading time, a dubbed line its recording and a gap: no longer, E6), so any two lines of a scene start a
    turn apart at least, whatever the plan wrote between them, and the hand-back leaves the floor busy until the last
    line is said."""
    m = small(段=[{'名字': '一', '过场': [{'镜头': 'west field', '秒': 3}, '通报 一', '通报 二', {'停': 1}, '通报 三']}])
    lines = named(m, 'CNV ZZ - Phase 1 line')           # each line is a script of its own: it waits for the floor and takes it
    starts = sorted(waits_for(m, s) for s in lines)
    assert len(starts) == 3 and all(b - a >= plan.CAPTION_TURN for a, b in zip(starts, starts[1:]))
    assert all(('FLAG', 'CNV_ZZ_Talking', 0) in s.when and ('SET_FLAG', 'CNV_ZZ_Talking', 1) in s.do for s in lines)
    # the hand-back is not held for the last line: the floor stays taken (Say done frees it), so a queued line waits
    hand = next(s for s in named(m, 'CNV ZZ - Phase 1 scene') if ('ENABLE_INPUT',) in s.do)
    assert not any(a[0] == 'SET_MILLISECOND_TIMER' for a in hand.do)
    assert any(s.name.endswith('Say done') for s in m.scripts)


def test_a_camera_is_held_inside_the_playable_area_a_screen_from_its_edge():
    """K5: a camera move aims at a view point: the site, clamped a half screen (plan.VIEW_HALF) inside the border in force
    (a scene's phase border, else the level's; a rule's camera: every border the level uses)."""
    from maps import festival
    c = plan.Compiler({'关卡': 'zz', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'}, '开局': {'资金': 1},
                       '边界': 'west of the canal', '段': [{'名字': '一'}, {'名字': '二', '边界': 'whole'}]})
    c.setup_phases()
    hx, hy = plan.VIEW_HALF
    x0, y0, x1, y1 = c.view_rect(['whole'])
    assert (x0, y0, x1, y1) == (hx, hy, 5000.0 - hx, 5000.0 - hy)
    assert c.view_rect(['west of the canal'])[2] == festival.BORDERS['west of the canal'][2] - hx
    assert c.view_rect(['whole', 'west of the canal'])[2] == c.view_rect(['west of the canal'])[2]     # the intersection
    assert [c.border_at(p) for p in c.phases] == ['west of the canal', 'whole']
    c.view = 'whole'
    name = c.view_point('west field')
    assert c.m.waypoints[name][0] >= x0 and c.m.views[name] == (x0, y0, x1, y1)
