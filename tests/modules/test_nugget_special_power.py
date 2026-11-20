"""Characterize SpecialPowerNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_an_eligible_hit_installs_the_modifier_on_the_caster(monkeypatch):
    """SpecialPowerNugget dispatches the caster's zero-reload self armor modifier."""
    s = small_world(model=False)
    s.own['SampleCaster'] = (
        '<GameObject id="SampleCaster" KindOf="INFANTRY"><Behaviors>'
        '<SpecialPower id="SelfArmor" SpecialPowerTemplate="SamplePower"'
        ' AttributeModifier="SampleArmor" AttributeModifierAffectsSelf="true"/>'
        '</Behaviors></GameObject>'
        '<SpecialPowerTemplate id="SamplePower" ReloadTime="0s"/>'
        '<AttributeModifier id="SampleArmor" Duration="1s">'
        '<Modifier Type="ARMOR" Value="50%"/></AttributeModifier>'
    )
    caster = s.add('caster', 'SampleCaster', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<SpecialPowerNugget SpecialPowerTemplate="SamplePower"><SpecialObjectFilter '
           'Rule="ANY" Include="VEHICLE"/></SpecialPowerNugget>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    now = s.frame_now()
    s.deal(FRAME)
    until, xml = caster.auras_on['SampleArmor']
    assert until == now + 15  # one-second modifier at 15 frames/s
    assert xml == s.own['SampleCaster']
    assert 'SampleArmor' not in target.auras_on
