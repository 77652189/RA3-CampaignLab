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


def test_every_wave_and_a_landed_ghost_king_blips_on_the_minimap():
    """Mechanics.md 小地图闪点: OBJECT_CREATE_RADAR_EVENT on the first troop of a wave, and on the Ghost King."""
    m = level()
    blips = [a for s in m.scripts for a in s.do if a[0] == 'OBJECT_CREATE_RADAR_EVENT']
    assert blips and all(a[2] == 0 for a in blips)
    waves = [s for s in m.scripts if s.name.startswith('CNV ZZ - Out V1')]
    assert waves and all(any(a[0] == 'OBJECT_CREATE_RADAR_EVENT' for a in s.do) for s in waves)
    lands = [s for s in m.scripts if s.name.startswith('CNV ZZ - King 3-1 lands')]
    assert lands and any(a[0] == 'OBJECT_CREATE_RADAR_EVENT' for a in lands[0].do)


def test_the_melt_event_goes_up_in_a_walls_last_seconds_and_down_when_it_is_gone():
    """冰快化: every wall's up script starts a second timer MELT_WARN short of the lifetime, which raises the flag if the
    wall still stands; its gone script puts the flag down; the plan's rule waits on that flag."""
    m = level(规则=[{'当': '雪祭.冰快化', '每隔': '0:20', '做': ['通报 冰快化了']}])
    life = 30.0
    ups = [s for s in m.scripts if s.name.startswith('CNV ZZ - Ice ') and s.name.endswith(' up')]
    assert ups and all(('SET_MILLISECOND_TIMER', f'CNV ZZ Melt {s.name.split()[4]}', life - horn.MELT_WARN) in s.do
                       for s in ups)
    melting = [s for s in m.scripts if s.name.endswith(' melting')]
    assert len(melting) == len(ups) and all(('SET_FLAG', 'CNV_ZZ_Melting', 1) in s.do for s in melting)
    gone = [s for s in m.scripts if s.name.startswith('CNV ZZ - Ice ') and s.name.endswith(' gone')]
    assert all(('SET_FLAG', 'CNV_ZZ_Melting', 0) in s.do for s in gone)
    rule = [s for s in m.scripts if ('FLAG', 'CNV_ZZ_Melting', 1) in s.when and 'Rule' in s.name]
    assert rule


def test_the_opening_demonstration_ices_a_street_and_the_foes_turn_back_to_the_lane():
    m = level(机关={'车队': {'类型': '车队', '出发': '开局 + 0:10'},
                  '雪祭': {'类型': '号角', '车队': '车队', '间隔': [45, 50, 45, 50, 45],
                         '每街一波': {'帝国武士': 2, '坦克杀手': 2}, '街': STREETS, '绕路': TABLE,
                         '演示': {'街': '一号', '绕去': '后巷', '等': 4, '兵': 2}}},
              规则=[{'当': '开局 + 0:01', '做': ['雪祭.演示']}, {'当': '开局 + 0:30', '做': ['雪祭.演示收']}])
    by = {s.name: s for s in m.scripts}
    assert ('SET_FLAG', 'CNV_ZZ_Demo_On', 1) in next(s for s in m.scripts if s.name.endswith('Rule 1')).do
    made = [a for a in by['CNV ZZ - Demo engineer'].do if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT']
    assert len(made) == 1 and made[0][4] == 'CNV ZZ Clear V2'               # plaza 1 is the second street
    assert any(a[0] == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT' for a in by['CNV ZZ - Demo ice'].do)
    assert ('FLAG', 'CNV_ZZ_Frozen_V2', 1) in by['CNV ZZ - Demo foes'].when     # the foes are made once the ice stands
    foes = [a[1] for a in by['CNV ZZ - Demo foes'].do if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT']
    turned = by['CNV ZZ - Demo turn'].do
    assert len(foes) == 2 and [a[1] for a in turned if a[0] == 'NAMED_DELETE'] == foes
    outs = [a for a in turned if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT']
    assert len(outs) == 2 and all(a[4] == m.mark('spawn V1') for a in outs)  # ... and a pair at the lane's foot
    with pytest.raises(plan.PlanError, match='演示'):
        level(规则=[{'当': '开局 + 0:01', '做': ['雪祭.演示']}])                # a device with no 演示
    with pytest.raises(plan.PlanError, match='same street'):
        level(机关={'车队': {'类型': '车队', '出发': '开局 + 0:10'},
                  '雪祭': {'类型': '号角', '车队': '车队', '间隔': [45], '每街一波': {'帝国武士': 2}, '街': STREETS,
                         '绕路': TABLE, '演示': {'街': '一号', '绕去': '一号'}}})


def test_the_convoy_truck_speed_is_the_plans_and_the_horns_last_as_long_as_the_festival():
    """A4 车队 速度 12: the festival (2730 along the avenue) takes ~4 minutes, and five horns sound before the convoy
    halts on every difficulty; the last leg (920, three trucks 0/50/110 s apart) is covered by the same table."""
    d = plan.load('a4')
    spec, horn_spec = d['机关']['车队'], d['机关']['雪祭']
    speed = float(spec['速度'])
    assert speed == 12.0
    drive = (2980.0 - 250.0) / speed                                   # convoy start to the halt
    gaps = [plan.times(g) for g in horn_spec['间隔']]
    assert len(gaps) == 5
    for lv in range(3):
        total = sum(g[lv] for g in gaps)
        assert 150 <= total <= drive, (lv, total, drive)               # five horns, all before the convoy gets there
        assert total >= 920.0 / speed + 100.0                          # ... and they run on over the last leg's trucks
    assert gaps[0][0] >= 45 and all(g[0] >= 45 for g in gaps)          # easy: every gap at least 45 s (the design line's)


def test_the_detour_event_goes_up_when_a_shut_streets_wave_is_made_at_another_street():
    m = level(规则=[{'当': '雪祭.绕路', '做': ['通报 绕路了']}])
    outs = [s for s in m.scripts if s.name.startswith('CNV ZZ - Out V')]
    detour = ('SET_FLAG', 'CNV_ZZ_Detoured', 1)
    own = [s for s in outs if s.name.split()[5] == s.name.split()[7]]            # 'Out V1 <origin> at <target>'
    assert own and not any(detour in s.do for s in own)
    assert any(detour in s.do for s in outs if s not in own)
    assert [s for s in m.scripts if ('FLAG', 'CNV_ZZ_Detoured', 1) in s.when and 'Rule' in s.name]


def test_the_tired_event_is_two_walls_not_yet_rested_and_each_wall_rests_for_the_reload():
    m = level(规则=[{'当': '雪祭.都在歇', '做': ['通报 都在歇']}])
    ups = [s for s in m.scripts if s.name.startswith('CNV ZZ - Ice ') and s.name.endswith(' up')]
    assert all(('SET_FLAG', f'CNV_ZZ_Rest_{s.name.split()[4]}', 1) in s.do and
               ('SET_MILLISECOND_TIMER', f'CNV ZZ Rest {s.name.split()[4]}', float(horn.RELOAD)) in s.do for s in ups)
    rested = [s for s in m.scripts if s.name.endswith(' rested')]
    assert len(rested) == len(ups) and all(('SET_FLAG', s.when[0][1], 0) in s.do for s in rested)
    rule = [s for s in m.scripts if 'Rule' in s.name and ('FLAG', 'CNV_ZZ_Rest_V1', 1) in s.when]
    assert rule and all(sum(c[0] == 'FLAG' and c[1].startswith('CNV_ZZ_Rest_') for c in s.when) == 2 for s in rule)


def test_the_ghost_king_events_go_up_when_it_is_sent_at_a_wall_and_when_that_wall_is_gone():
    m = level(规则=[{'当': '雪祭.鬼王砸墙', '做': ['通报 砸']}, {'当': '雪祭.鬼王砸开', '做': ['通报 开']}])
    smash = [s for s in m.scripts if s.name.endswith('smashes')]
    assert smash and all(('SET_FLAG', 'CNV_ZZ_Smashing', 1) in s.do for s in smash)
    broke = [s for s in m.scripts if s.name.endswith('Ghost broke')]
    assert broke and ('FLAG', 'CNV_ZZ_Smashing', 1) in broke[0].when and ('SET_FLAG', 'CNV_ZZ_Smashed', 1) in broke[0].do


def test_the_convoy_hit_event_is_a_truck_health_band_that_lasts_a_few_seconds():
    m = level(规则=[{'当': '车队.挨打', '每隔': '0:25', '做': ['通报 挨打']}])
    bands = [s for s in m.scripts if s.name.startswith('CNV ZZ - Hit ') and ' under ' in s.name]
    assert len(bands) == 3 * 9 and all(('SET_FLAG', 'CNV_ZZ_Hit', 1) in s.do for s in bands)
    over = [s for s in m.scripts if s.name.endswith('Hit over')]
    assert over and ('SET_FLAG', 'CNV_ZZ_Hit', 0) in over[0].do
    assert [s for s in m.scripts if ('FLAG', 'CNV_ZZ_Hit', 1) in s.when and 'Rule' in s.name]


def test_a_way_with_a_sign_smokes_ten_seconds_before_the_horn_that_sends_a_wave_there():
    arch = {'物件': 'OK_ARCH01', '偏移': [60, 20]}
    streets = {k: {**v, '标志': arch} for k, v in STREETS.items()}
    mouths = {k: {**v, '标志': arch} for k, v in MOUTHS.items()}
    m = level(机关={'车队': {'类型': '车队', '出发': '开局 + 0:10'},
                  '雪祭': {'类型': '号角', '车队': '车队', '间隔': ['0:45/0:30/0:20', 50, 45, 50, 45],
                         '每街一波': {'帝国武士': 2}, '街': streets, '绕路': TABLE, '口': mouths}})
    assert {r for r in m.cast if r.startswith('标志 ')} == {f'标志 {k}' for k in (*STREETS, *MOUTHS)}
    smoke = [s for s in m.scripts if s.name.startswith('CNV ZZ - Smoke ')]
    # the street plaza 2 opens from horn 2: no smoke for it at horn 1; every mouth smokes at every horn, ice or none
    assert not [s for s in smoke if s.name.endswith('V1 V3')] and [s for s in smoke if s.name.endswith('V2 V3')]
    assert all(('FLAG', 'CNV_ZZ_Frozen_' + s.name.split()[-1], 0) in s.when for s in smoke if ' V' in s.name[:20])
    assert not any(c[0] == 'FLAG' and c[1].startswith('CNV_ZZ_Frozen_') for s in smoke if ' L' in s.name[:20]
                   for c in s.when)
    # the warning timer runs out ten seconds short of the horn's, by difficulty
    starts = [s for s in m.scripts if s.name.startswith('CNV ZZ - Horn V start')]
    for s in starts:
        gap = next(a[2] for a in s.do if a[:2] == ('SET_MILLISECOND_TIMER', 'CNV ZZ Horn'))
        assert ('SET_MILLISECOND_TIMER', 'CNV ZZ Horn Warn', gap - 10.0) in s.do
    assert [u for u in m.units if u.id == 'CNV_ZZ_SignalSmoke']
