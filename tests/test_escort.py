"""The escort devices (experimental/cnv/devices/convoy.py, ice_plazas.py) compile to what they say: trucks' health
by difficulty set the retail way, and with 遇伏: 停下 a plaza's troops out, alive and ungated stop the convoy --
counted only once made, from the moment a truck reaches that plaza -- until they are down or the gate is iced."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import parts  # noqa: E402
import plan  # noqa: E402

EASY, NORMAL, HARD = plan.ONE


def escort(convoy=None, plazas=None):
    d = {'关卡': 'zz', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'}, '段': [{'名字': '一'}],
         '机关': {'车队': {'类型': '车队', '出发': '开局 + 0:10', **(convoy or {})},
                 '广场': {'类型': '冰雕广场', '车队': '车队', '每座兵': ['坦克杀手', '帝国武士'], '每座几个': '1/2/2',
                        **(plazas or {})}}}
    return plan.Compiler(d).compile()


def named(m, start):
    return [s for s in m.scripts if s.name.startswith(start)]


def test_trucks_health_by_difficulty():
    m = escort({'血量': '700/500/350'})
    health = {tuple(s.levels): s.do for s in named(m, 'CNV ZZ - Truck health')}
    assert health[HARD] == [('NAMED_SET_MAX_HEALTH', f'UNIT - CNV ZZ Truck {j}', 350, 1) for j in (1, 2, 3)]
    assert health[EASY][0][2] == 700 and health[NORMAL][0][2] == 500
    assert not named(escort(), 'CNV ZZ - Truck health')                # left out: the truck's own 500


def test_an_ambush_stops_the_convoy_till_its_troops_are_down():
    m = escort(plazas={'遇伏': '停下'})
    roll = named(m, 'CNV ZZ - Roll')[0]
    assert roll.name == 'CNV ZZ - Roll' and ('FLAG', 'CNV_ZZ_Blocking_2', 0) in roll.when
    assert ('FLAG', 'CNV_ZZ_Halted', 0) in roll.when                      # 停下 / 继续 still hold it too
    held = [s for s in named(m, 'CNV ZZ - Roll held') if ('FLAG', 'CNV_ZZ_Blocking_2', 1) in s.when]
    assert len(held) == 1 and not held[0].once                            # the tick runs on while parked
    blocked, = named(m, 'CNV ZZ - Blocked 2')
    assert ('FLAG', 'CNV_ZZ_Near_2', 1) in blocked.when                   # only once a truck got there
    assert ('COUNTER', 'CNV_ZZ_Left_2', 3, 1) in blocked.when
    assert blocked.do[0] == ('SET_FLAG', 'CNV_ZZ_Blocking_2', 1) and blocked.do[1][0] == 'NAMED_STOP'
    assert named(m, 'CNV ZZ - Cleared 2')[0].when[1] == ('COUNTER', 'CNV_ZZ_Left_2', 1, 0)
    assert any(c[0] == 'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA' for c in named(m, 'CNV ZZ - Iced past 2')[0].when)
    # the troops made on easy: one a sculpture, counted up when it breaks and down as each falls, once made
    out = [s for s in named(m, 'CNV ZZ - Out 2-1') if tuple(s.levels) == EASY][0]
    assert ('INCREMENT_COUNTER', 1, 'CNV_ZZ_Left_2') in out.do
    down = [s for s in named(m, 'CNV ZZ - Down 2-1-') if tuple(s.levels) == EASY]
    assert [s.when for s in down] == [[('FLAG', 'CNV_ZZ_Out_2_1', 1), ('NAMED_DESTROYED', 'UNIT - CNV ZZ Troop 2-1-1')]]
    assert down[0].do == [('DECREMENT_COUNTER', 1, 'CNV_ZZ_Left_2')]
    assert not parts.contract(parts.merged(m))


def test_no_ambush_stop_unless_asked():
    m = escort()
    assert not named(m, 'CNV ZZ - Blocked') and not named(m, 'CNV ZZ - Down')
    assert named(m, 'CNV ZZ - Roll')[0].when[-1] == ('FLAG', 'CNV_ZZ_Halted', 0)
