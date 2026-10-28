"""禁造: what the player may not build (retail Brighton Beach: ALLOW_DISALLOW_ONE_BUILDING on the player at the start,
1 again when the story lets it go; docs/design/a4-redesign.md P28: no airfield in the A4), and 准造 letting it go."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import parts  # noqa: E402
import plan  # noqa: E402
import sim  # noqa: E402


def small(**more):
    d = {'关卡': 'zz', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'},
         '开局': {'资金': 0, '部队': [{'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
         '段': [{'名字': '一'}]}
    d.update(more)
    return plan.Compiler(d).compile()


def test_banned_from_the_start_and_let_go_by_a_rule():
    m = small(禁造=['机场', '阿波罗战机'], 规则=[{'当': '开局 + 2:00', '做': [{'准造': ['阿波罗战机']}]}])
    p1 = m.player('p1')
    start = next(s for s in m.scripts if s.name == 'CNV ZZ - Bans')
    assert not start.when
    assert start.do == [('ALLOW_DISALLOW_ONE_BUILDING', p1, 'alliedairfield', 0),
                        ('ALLOW_DISALLOW_ONE_BUILDING', p1, 'alliedfighteraircraft', 0)]
    later = [a for s in m.scripts for a in s.do if a[0] == 'ALLOW_DISALLOW_ONE_BUILDING' and a[3] == 1]
    assert later == [('ALLOW_DISALLOW_ONE_BUILDING', p1, 'alliedfighteraircraft', 1)]
    assert not parts.contract(parts.merged(m))


def test_a_ban_as_an_action_and_bad_names():
    m = small(规则=[{'当': '开局 + 1:00', '做': [{'禁造': ['机场']}]}])
    assert ('ALLOW_DISALLOW_ONE_BUILDING', m.player('p1'), 'alliedairfield', 0) in \
        [a for s in m.scripts for a in s.do]
    with pytest.raises(plan.PlanError):
        small(禁造='机场')                         # a list
    with pytest.raises(plan.PlanError):
        small(禁造=['不存在的东西'])


def test_the_simulator_builds_nothing_banned():
    m = small(禁造=['机场'], 规则=[{'当': '开局 + 1:00', '做': [{'准造': ['机场']}]}])
    s = sim.Sim(m, script='10 造 AlliedAirfield 在 north base; 70 造 AlliedAirfield 在 north base')
    s.run(until=90)
    made = [b for b in s.bodies.values() if b.template == 'AlliedAirfield']
    assert len(made) == 1 and made[0].made_at >= 70
    assert any('不许造' in line for _, _, line in s.log)
