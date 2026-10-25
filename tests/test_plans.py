"""The plan language (experimental/cnv/plan.py, docs/story/plans/README.md) compiles to the scripts it says: values by
difficulty land in scripts with that difficulty's header bit only, a repeating wave stops at its cap and while none
of its sources stands, `X + t` waits on X, phases start in order, an unknown word is an error that names it, and
every plan passes its design check without a 问题 (against what the retail missions do)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import plan  # noqa: E402
import plancheck  # noqa: E402

EASY, NORMAL, HARD = plan.ONE


def small(**more):
    """A plan on the festival map: one phase, one enemy barracks, plus `more`."""
    d = {'关卡': 'zz', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'},
         '开局': {'资金': '5000/3000/2000', '部队': [{'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
         '段': [{'名字': '一'}]}
    d.update(more)
    return plan.Compiler(d).compile()


def named(m, start):
    return [s for s in m.scripts if s.name.startswith(start)]


def test_values_by_difficulty():
    assert plan.per('5000/3000/2000') == ('5000', '3000', '2000') and plan.per(7) == (7, 7, 7)
    assert plan.times('4:00/3:00/2:30') == (240.0, 180.0, 150.0) and plan.seconds('4分钟') == 240.0
    with pytest.raises(plan.PlanError):
        plan.per('1/2')
    money = named(small(), 'CNV ZZ - Money')
    assert {(tuple(s.levels), s.do[0][2]) for s in money} == {(EASY, 5000), (NORMAL, 3000), (HARD, 2000)}


def test_a_repeating_wave_has_its_cap_and_its_source():
    m = small(进攻=[{'名字': 'w', '开始': '开局 + 1:00', '兵': {'帝国武士': '1/2/3'}, '从': 'north base',
                    '打': 'west field', '每隔': 30, '最多': 3, '来源': ['camp']}])
    sends = [s for s in named(m, 'CNV ZZ - Wave 1 ') if not s.name.endswith(('start', 'more'))]
    assert len(sends) == 3 * 3                          # 3 waves x 3 difficulties
    for s in sends:
        i = int(s.name.split()[5])                      # CNV ZZ - Wave 1 <i> <difficulty>
        assert ('COUNTER', 'CNV_ZZ_Wave_1_Sent', 2, i - 1) in s.when
        assert ('NAMED_NOT_DESTROYED', 'UNIT - CNV ZZ camp') in s.when
        made = [a for a in s.do if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT']
        assert len(made) == {EASY: 1, NORMAL: 2, HARD: 3}[tuple(s.levels)]
    start = named(m, 'CNV ZZ - Wave 1 start')[0]
    assert any(c[0] == 'TIMER_EXPIRED' for c in start.when)          # waits for 开局 + 1:00


def test_any_of_makes_one_script_per_alternative_latched_once():
    m = small(规则=[{'当': {'任一': ['开局 + 2:00', '攻击 camp']}, '做': ['通报 来了']}])
    rule = named(m, 'CNV ZZ - Rule 1')
    assert len(rule) == 2
    latch = {c for s in rule for c in s.when if c[0] == 'FLAG' and c[2] == 0}
    assert len(latch) == 1                              # the same flag stops the second from running too


def test_phases_start_in_order_and_reveal_their_objectives():
    m = small(段=[{'名字': '一', '目标': ['甲'], '结束': '开局 + 1:00'}, {'名字': '二', '目标': ['乙']}],
              目标={'甲': {'标记': ['camp']}, '乙': {'奖励': True}})
    second = next(s for s in m.scripts if s.name == 'CNV ZZ - Phase 2')
    assert ('FLAG', 'CNV_ZZ_Phase_1', 1) in second.when
    reveal = [s for s in m.scripts if any(a == ('SET_MISSION_OBJECTIVE_STATUS', 'Bonus01 - CNV ZZ', 1) for a in s.do)]
    assert reveal and any(c == ('FLAG', 'CNV_ZZ_Wait_' + c[1].split('_')[-1], 1) for c in reveal[0].when
                          if c[0] == 'FLAG')


def test_chinese_names_stay_out_of_the_map():
    """Phases, waves, rules and roles named in Chinese: the scripts and objects get ASCII names (the map stores
    them as Latin-1), the cast keeps the plan's names."""
    import parts
    m = small(开局={'部队': [{'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': '北营兵营'}]},
              段=[{'名字': '布防', '目标': ['拆掉北营'], '结束': '开局 + 1:00'}, {'名字': '进攻'}],
              目标={'拆掉北营': {'标记': ['北营兵营'], '完成': '摧毁 北营兵营'}},
              进攻=[{'名字': '小队', '开始': '段 进攻', '兵': {'帝国武士': 2}, '从': 'north base', '打': '北营兵营'}],
              规则=[{'当': '攻击 北营兵营', '做': ['通报 打起来了']}])
    assert '北营兵营' in m.cast
    assert not parts.contract(parts.merged(m))


@pytest.mark.parametrize('bad', [{'规则': [{'当': '开局 后', '做': []}]},
                                 {'规则': [{'当': '开局', '做': ['跳舞']}]},
                                 {'规则': [{'当': '摧毁 nobody', '做': []}]},
                                 {'规则': [{'当': '段 三', '做': []}]},
                                 # 还没 (X + t) does not latch: an error, not (还没 X) + t (review 2026-10-24)
                                 {'规则': [{'当': '还没 段 一 + 4:00', '做': []}]},
                                 # a rule not done once ran every frame its condition held
                                 {'规则': [{'当': '开局', '做': [], '次数': '每次'}]},
                                 {'规则': [{'当': '开局', '做': [], '次数': 3}]},
                                 {'规则': [{'当': '开局', '做': [], '难度': '地狱'}]},
                                 {'规则': [{'当': '开局 + 0:30~0:10', '做': []}]},
                                 {'规则': [{'当': '开局', '做': [{'出动': 'camp'}]}]},
                                 {'进攻': [{'名字': 'w', '开始': '开局', '兵': {'帝国武士': 1}, '从': 'north base',
                                           '每隔': '0:30~1:00'}]}])
def test_an_unknown_word_is_an_error(bad):
    with pytest.raises((plan.PlanError, AssertionError)):
        small(**bad)


def test_two_waves_on_the_convoy_keep_the_contract():
    """Each wave on a device gets its own chase scripts (names cut from the troops' collided), and the convoy's tick
    runs before it sets off, so troops sent at it early have orders."""
    import parts
    wave = {'开始': '开局 + 0:30', '兵': {'帝国武士': 1}, '从': 'north base', '打': '车队'}
    m = small(机关={'车队': {'类型': '车队', '出发': '开局 + 3:00'}},
              进攻=[dict(wave, 名字='甲'), dict(wave, 名字='乙')])
    assert not parts.contract(parts.merged(m))
    before = next(s for s in m.scripts if s.name == 'CNV ZZ - Tick before')
    assert before.do[0][0] == 'SET_MILLISECOND_TIMER' and not before.when
    assert any(s.name == 'CNV ZZ - Roll parked' for s in m.scripts)
    import dataclasses
    m.scripts.append(dataclasses.replace(m.scripts[0]))
    assert any('scripts have it' in b for b in parts.contract(parts.merged(m)))


def test_the_carrier_defends_only_a_station_still_the_enemys():
    """A7's 回防 is a request: the jump waits on the station still the enemy's and the carrier not flying off."""
    m = plan.mission('a7')
    rule = next(s for s in m.scripts if any(a[0] == 'SET_FLAG' and a[1].endswith('Defend_Asked') for a in s.do))
    assert not any(a[0] == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT' for a in rule.do)
    jump = next(s for s in m.scripts if s.name.endswith('Carrier defends'))
    assert {c[0] for c in jump.when} >= {'NAMED_OWNED_BY_PLAYER', 'FLAG'}
    assert ('HIDE_COUNTDOWN_TIMER', 'CNV A7 Jump') in jump.do


def test_every_plan_passes_its_design_check():
    levels = plan.levels()
    assert levels, f'no plans in {plan.PLANS}'
    for level in levels:
        problems = [t for lv, t in plancheck.design_check(plan.load(level)) if lv == '问题']
        assert not problems, (level, problems)


def test_a_time_the_player_can_bring_forward_is_only_the_latest():
    """An any-of with the player's doing in it, or waiting on a phase the player starts sooner: the report says
    "最晚" (it is not when the attack comes, only when it comes at the latest)."""
    d = {'段': [{'名字': '一', '结束': {'任一': ['开局 + 6:00', '进入 harbour']}}, {'名字': '二'}],
         '进攻': [{'名字': 'w', '开始': '段 二 + 1:30', '兵': {}}, {'名字': 'v', '开始': '开局 + 2:00', '兵': {}}]}
    sheet = plancheck.beat_sheet(d)
    assert '第 2 段 二（最晚 6:00 起）' in sheet and 'w：最晚 7:30 起' in sheet and 'v：2:00 起' in sheet


def test_a_random_time_waits_between_its_two():
    m = small(规则=[{'当': '开局 + 0:15~0:30/0:10~0:20/5', '做': ['通报 来了']}])
    starts = {tuple(s.levels): s.do[0] for s in named(m, 'CNV ZZ - Wait')}
    timer = starts[HARD][1]
    assert starts == {EASY: ('SET_RANDOM_MSEC_TIMER', timer, 15.0, 30.0),
                      NORMAL: ('SET_RANDOM_MSEC_TIMER', timer, 10.0, 20.0),
                      HARD: ('SET_MILLISECOND_TIMER', timer, 5.0)}
    # the beat sheet takes its latest
    assert plancheck.times_of('开局 + 0:15~0:30', {}) == 30.0


def test_a_rule_again_every_so_often_while_it_holds():
    """每隔: not once, gated on its own timer, which it sets again; the timer starts run out, so the first is at once."""
    m = small(规则=[{'当': '进入 north base', '每隔': '0:30/0:20/0:20', '做': ['通报 快走']}])
    clock = named(m, 'CNV ZZ - Rule 1 clock')[0]
    assert clock.do == [('SET_MILLISECOND_TIMER', 'CNV ZZ Rule 1', 0.0)] and clock.once
    again = named(m, 'CNV ZZ - Rule 1 again')
    assert {tuple(s.levels) for s in again} == {EASY, NORMAL, HARD}
    for s in again:
        assert not s.once and ('TIMER_EXPIRED', 'CNV ZZ Rule 1') in s.when
        assert s.do[-1] == ('SET_MILLISECOND_TIMER', 'CNV ZZ Rule 1', 30.0 if tuple(s.levels) == EASY else 20.0)


def test_a_rule_or_a_force_for_some_difficulties_only():
    m = small(规则=[{'当': '开局', '难度': '困难', '做': ['通报 难']},
                   {'当': '开局', '难度': ['普通', '困难'], '每隔': 30, '做': ['通报 又来']}],
              开局={'部队': [{'单位': '帝国武士', '数量': 2, '在': 'north base', '阵营': '敌', '难度': '困难'}]})
    assert tuple(named(m, 'CNV ZZ - Rule 1')[0].levels) == HARD
    assert [tuple(s.levels) for s in named(m, 'CNV ZZ - Rule 2 again')] == [(False, True, True)]
    gone = {tuple(s.levels): len(s.do) for s in named(m, 'CNV ZZ - Fewer')}
    assert gone == {EASY: 2, NORMAL: 2}                 # placed for hard, both deleted on the others


def test_unattackable_and_sent_off():
    m = small(开局={'部队': [{'单位': '帝国武士', '数量': 2, '在': 'north base', '阵营': '敌', '角色': 'guard',
                          '无敌': '是'}]},
              规则=[{'当': '开局 + 1:00', '做': [{'出动': 'guard', '打': 'west field'}, {'取消无敌': 'guard 1'}]}])
    made = named(m, 'CNV ZZ - Unattackable')[0].do
    assert made == [('UNIT_CHANGE_OBJECT_STATUS', f'UNIT - CNV ZZ guard {j}', 'UNATTACKABLE', 1) for j in (1, 2)]
    rule = named(m, 'CNV ZZ - Rule 1')[0].do
    assert [a[0] for a in rule] == ['ATTACK_MOVE_NAMED_UNIT_TO'] * 2 + ['UNIT_CHANGE_OBJECT_STATUS']
    assert rule[-1] == ('UNIT_CHANGE_OBJECT_STATUS', 'UNIT - CNV ZZ guard 1', 'UNATTACKABLE', 0)
    import parts
    assert not parts.contract(parts.merged(m))


def test_an_enemy_ai_of_the_levels_own():
    """敌方AI: the enemy player made the enemy's faction with a generated personality (the co-op skirmish base, the
    style's moves and states, no taunts), asleep with no money until woken, its army sent only from 进攻, the
    plan's guards kept out of the AI's hands."""
    import enemy_ai
    m = small(开局={'部队': [{'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'},
                          {'单位': '帝国武士', '数量': 2, '在': 'north base', '阵营': '敌', '角色': 'guard',
                           '守': 'north base'}]},
              敌方AI={'性格': '机甲', '基地': 'north base', '资金': '2000/4000/6000', '唤醒': '开局 + 1:00',
                    '进攻': '开局 + 3:00', '偏好': {'海啸坦克': 2}, '上限': {'兵营': 1}})
    assert m.sides['s1'] == {'playerFaction': 'PlayerTemplate:Japan',
                             'aiPersonality': 'AIPersonalityDefinition:CNV_AIP_ZZ'}
    (fname, xml, link), = m.assets
    assert fname == 'CNV_AIP_ZZ.xml' and link == 'AIPersonalityDefinition:CNV_AIP_ZZ'
    assert 'inheritFrom="JapanCoopBaseSkirmishPersonality"' in xml and 'FeedbackEntry' not in xml
    assert xml.count('<StrategicState') == len([x for x in enemy_ai.taken('JapanMechaWarfare')
                                                 if x.startswith('<StrategicState')]) > 0
    assert '<UnitModifier Unit="JapanAntiVehicleVehicleTech1" OffensiveModifier="2"' in xml
    cap, off = named(m, 'CNV ZZ - AI cap JapanBarracks')
    assert cap.when == [('PLAYER_HAS_OBJECT_COMPARISON', 'Soviet_1', 3, 1, 'japanbarracks')] and not cap.once
    assert cap.do == [('ALLOW_DISALLOW_ONE_BUILDING', 'Soviet_1', 'japanbarracks', 0)]
    assert off.do == [('ALLOW_DISALLOW_ONE_BUILDING', 'Soviet_1', 'japanbarracks', 1)] and not off.once
    assert named(m, 'CNV ZZ - AI asleep')[0].do == [('PLAYER_SET_MONEY', 'Soviet_1', 0)]
    wake = named(m, 'CNV ZZ - AI wake')[0]
    assert any(c[0] == 'TIMER_EXPIRED' for c in wake.when)
    assert [a[0] for a in wake.do][:2] == ['UNIT_AI_TRANSFER_ALL', 'SKIRMISH_AI_MAKE_BASE']
    assert [a for a in wake.do if a[0] == 'UNIT_AI_TRANSFER'] == [
        ('UNIT_AI_TRANSFER', f'UNIT - CNV ZZ guard {j}', 0) for j in (1, 2)]
    assert {tuple(s.levels): s.do[0][2] for s in named(m, 'CNV ZZ - AI money')} == {EASY: 2000, NORMAL: 4000,
                                                                                    HARD: 6000}
    attack = named(m, 'CNV ZZ - AI attack')[0]
    assert attack.do == [('SKIRMISH_AI_TRANSFER_ALL', 'Soviet_1', 1)] and ('FLAG', 'CNV_ZZ_AI_Awake', 1) in attack.when
    import parts
    assert not parts.contract(parts.merged(m))
    with pytest.raises(plan.PlanError):
        small(敌方AI={'性格': '空军', '基地': 'north base', '唤醒': '开局'})          # 帝国 has no 空军 commander
