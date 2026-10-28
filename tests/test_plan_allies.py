"""A side of 阵营 其他 allied to the player (retail Odessa, Stalingrad: the transports a side of their own), the convoy
owned by it, and the convoy setting off in batches (分批)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import parts  # noqa: E402
import plan  # noqa: E402

ALLY = {'我': '盟军', '敌': '帝国', '其他': {'护送队': {'阵营': '盟军', '对我': '盟友', '对敌': '敌人'}, '哨所': '盟军'}}


def small(**more):
    d = {'关卡': 'zz', '地图': 'festival', '阵营': ALLY,
         '开局': {'资金': 0, '部队': [{'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
         '段': [{'名字': '一'}]}
    d.update(more)
    return plan.Compiler(d).compile()


def test_an_allied_side_and_a_neutral_one():
    m = small()
    sides = next(s for s in m.scripts if s.name == 'CNV ZZ - Sides').do
    ally, post, p1, s1 = m.player('s2'), m.player('s3'), m.player('p1'), m.player('s1')
    assert ('PLAYER_RELATES_PLAYER', ally, p1, 'Friend') in sides and ('PLAYER_RELATES_PLAYER', p1, ally, 'Friend') in sides
    assert ('PLAYER_RELATES_PLAYER', ally, s1, 'Enemy') in sides and ('PLAYER_RELATES_PLAYER', s1, ally, 'Enemy') in sides
    assert ('PLAYER_RELATES_PLAYER', post, p1, 'Neutral') in sides and ('PLAYER_RELATES_PLAYER', s1, post, 'Neutral') in sides
    assert m.team('s2') == f'{ally}/team{ally}'                   # no team in the map's table: the player's default
    with pytest.raises(plan.PlanError):
        plan.Compiler({'关卡': 'zz', '地图': 'festival', '段': [{'名字': '一'}],
                       '阵营': {'我': '盟军', '敌': '帝国', '其他': {'x': {'阵营': '盟军', '对我': '好朋友'}}}}).compile()


def test_the_convoy_is_the_allys_and_sets_off_in_batches():
    m = small(机关={'车队': {'类型': '车队', '出发': '开局 + 0:30', '车': '护送队', '分批': [0, 50, 110]}})
    assert {m.cast[f'truck {j}'].side for j in (1, 2, 3)} == {'s2'}
    rolls = [s for s in m.scripts if s.name.startswith('CNV ZZ - Roll ') and s.name[-1].isdigit()]
    assert [s.do for s in rolls] == [[('MOVE_NAMED_UNIT_TO', f'UNIT - CNV ZZ Truck {j}', 'CNV ZZ Exit')] for j in (1, 2, 3)]
    assert [next(c for c in s.when if c[0] == 'FLAG' and '_Go_' in c[1]) for s in rolls] == \
        [('FLAG', f'CNV_ZZ_Go_{j}', 1) for j in (1, 2, 3)]
    roll = next(s for s in m.scripts if s.name == 'CNV ZZ - Roll')
    assert not any(a[0] == 'MOVE_NAMED_UNIT_TO' for a in roll.do)               # only the tick again
    names = [s.name for s in m.scripts]
    assert names.index('CNV ZZ - Roll 3') < names.index('CNV ZZ - Roll')        # the moves before the timer is reset
    go = {s.name: s for s in m.scripts if s.name.startswith('CNV ZZ - Convoy go ')}
    assert set(go) == {'CNV ZZ - Convoy go 1', 'CNV ZZ - Convoy go 2', 'CNV ZZ - Convoy go 3'}
    assert not parts.contract(parts.merged(m))


def test_the_enemy_ai_lets_kinds_go_step_by_step():
    """敌方AI 分档 (retail Stalingrad: the Soviet AI's tanks, then aircraft, unlocked by time once it woke): the kinds
    of every step held back at the start, each step's let go when its condition holds; a kind capped too (上限) is
    let go by its cap only after its step."""
    d = {'关卡': 'zz', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'}, '段': [{'名字': '一'}],
         '开局': {'资金': 0, '部队': [{'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
         '敌方AI': {'基地': 'north base', '唤醒': '开局 + 1:00', '上限': {'海啸坦克': 3},
                  '分档': [{'当': '敌方AI 醒来 + 2:00', '放开': ['海啸坦克']}, {'当': '敌方AI 醒来 + 4:00', '放开': ['天狗']}]}}
    m = plan.Compiler(d).compile()
    ai = m.ai_player()
    held = next(s for s in m.scripts if s.name == 'CNV ZZ - AI held back')
    assert held.do == [('ALLOW_DISALLOW_ONE_BUILDING', ai, 'japanantivehiclevehicletech1', 0),
                       ('ALLOW_DISALLOW_ONE_BUILDING', ai, 'japanantiinfantryvehicle', 0)] and not held.when
    step1 = next(s for s in m.scripts if s.name == 'CNV ZZ - AI step 1')
    assert step1.do == [('ALLOW_DISALLOW_ONE_BUILDING', ai, 'japanantivehiclevehicletech1', 1),
                        ('SET_FLAG', 'CNV_ZZ_AI_Step_1', 1)]
    assert any(c[0] == 'TIMER_EXPIRED' for c in step1.when)
    off = next(s for s in m.scripts if s.name == 'CNV ZZ - AI cap JapanAntiVehicleVehicleTech1 off')
    assert ('FLAG', 'CNV_ZZ_AI_Step_1', 1) in off.when
    assert not parts.contract(parts.merged(m))
    for bad in ([{'当': '开局', '放开': ['天狗']}, {'当': '开局 + 1:00', '放开': ['天狗']}], [{'当': '开局'}]):
        with pytest.raises(plan.PlanError):
            plan.Compiler(dict(d, 敌方AI=dict(d['敌方AI'], 分档=bad))).compile()


def test_the_convoy_together_by_default_and_a_wrong_batch():
    m = small(机关={'车队': {'类型': '车队', '出发': '开局 + 0:30'}})
    roll = next(s for s in m.scripts if s.name == 'CNV ZZ - Roll')
    assert sum(a[0] == 'MOVE_NAMED_UNIT_TO' for a in roll.do) == 3
    assert m.cast['truck 1'].side == 'p1'
    with pytest.raises(plan.PlanError):
        small(机关={'车队': {'类型': '车队', '出发': '开局 + 0:30', '分批': [0, 50]}})
    with pytest.raises(plan.PlanError):
        small(机关={'车队': {'类型': '车队', '出发': '开局 + 0:30', '车': '路人'}})
