"""Characterize AttachNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_attachment_teleports_the_child_and_tracks_the_parent(monkeypatch):
    """AttachNugget links a caster to a ground vehicle and applies the two sets of status bits."""
    s = small_world(model=False)
    s.own['SampleCaster'] = (
        '<GameObject id="SampleCaster" KindOf="INFANTRY"><Behaviors>'
        '<AttachUpdate id="Hook" Flags="STICK_TO_PARENT TELEPORT" Range="120"'
        ' ParentStatus="VEHICLE_ATTACHED" AttachedObjectStatus="ENCLOSED"/>'
        '</Behaviors></GameObject>'
    )
    caster = s.add('caster', 'SampleCaster', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1371, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<AttachNugget AttachModuleId="Hook"><SpecialObjectFilter Rule="ANY" '
           'Include="VEHICLE"/></AttachNugget>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    s.deal(FRAME)
    # A 121-unit centre distance is outside the AttachUpdate range of 120.
    assert caster.serial not in s.attachments
    assert (caster.x, caster.y) == (1250, 2500)

    target.x = 1350
    s.deal(FRAME)
    child, parent, _ = s.attachments[caster.serial]
    assert (child, parent) == (caster, target)
    assert {'ATTACHED', 'ENCLOSED'} <= child.status
    assert 'VEHICLE_ATTACHED' in parent.status
    assert (child.x, child.y) == (1350, 2500)
    parent.x += 40
    s.attachment_tick()
    assert (child.x, child.y) == (1390, 2500)
