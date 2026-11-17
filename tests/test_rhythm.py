"""The 节律 device (devices/rhythm.py) and the swell turret it was made for (units/platform.py), A8 海上发布会: the
guns of a platform change reach on a beat; a beat is two upgrades granted and taken away, group by group."""
import pytest
from test_plans import small  # (puts experimental/cnv on the path)  # noqa: F401, I001
import build  # noqa: E402
import parts  # noqa: E402
from devices import rhythm  # noqa: E402
from plantime import PlanError  # noqa: E402
from units import platform, roster  # noqa: E402


def test_the_turret_has_two_upgrades_each_with_its_own_range():
    u = platform.tide_gun(high=2.0, low=0.6)
    assert u.names == {'on': 'Upgrade_CNV_TideGun_High', 'off': 'Upgrade_CNV_TideGun_Low'}
    assert 'GameDependency' not in u.xml                                   # a placed turret needs no power plant
    for up, mod, pct in (('Upgrade_CNV_TideGun_High', 'AttributeModifier_CNV_TideGun_High', 200),
                         ('Upgrade_CNV_TideGun_Low', 'AttributeModifier_CNV_TideGun_Low', 60)):
        assert f'<TriggeredBy>{up}</TriggeredBy>' in u.xml and f'<UpgradeTemplate id="{up}" Type="OBJECT"/>' in u.xml
        assert f'AttributeModifier="{mod}"' in u.xml
        assert f'<Modifier Type="RANGE" Value="{pct}%"/>' in u.xml
    assert set(u.link) >= {f'UpgradeTemplate:{u.names["on"]}', f'UpgradeTemplate:{u.names["off"]}'}


def test_the_roster_publishes_both_of_a8s_new_units():
    assert '浪涌炮塔' in roster.NAMES and '自由号空天航母' in roster.NAMES
    assert roster.make('浪涌炮塔')[0].names['on'].startswith('Upgrade_')
    assert roster.make('自由号空天航母')[0].abilities['jump']


def test_the_plan_compiles_and_the_beat_is_wired_group_by_group():
    m, t, _ = build.resolve('a8', 'beat')
    mm = parts.merged(m, t)
    assert parts.contract(mm) == []
    key = rhythm.key_of('浪')
    mine = [s for s in mm.scripts if f' - {key} ' in s.name]
    assert len(mine) == 10                                  # the start, then begin / on / off for each of the three groups
    grants = {a[1] for s in mine for a in s.do if a[0] == 'NAMED_RECEIVE_UPGRADE'}
    assert grants == {'Upgrade_CNV_TideGun_High', 'Upgrade_CNV_TideGun_Low'}
    assert rhythm.on_flag('A8', '浪', 2).endswith('_On_2') and rhythm.on_flag('A8', '浪', 0) != rhythm.on_flag('A8', '浪', 1)


def test_a_bad_beat_is_refused():
    class Ctx:
        tag = 'A8'
    with pytest.raises(PlanError, match='开 .* must be between'):
        rhythm.Rhythm(Ctx(), 'x', {'单位': '浪涌炮塔', '周期': 30, '开': 30, '组': [{'角色': 'g'}]})
    with pytest.raises(PlanError, match='needs 组'):
        rhythm.Rhythm(Ctx(), 'x', {'单位': '浪涌炮塔'})
    with pytest.raises(PlanError, match='needs 单位'):
        rhythm.Rhythm(Ctx(), 'x', {'组': [{'角色': 'g'}]})
    with pytest.raises(PlanError, match='no on/off upgrades'):
        rhythm.Rhythm(Ctx(), 'x', {'单位': '纸鹤侦察机', '组': [{'角色': 'g'}]})
