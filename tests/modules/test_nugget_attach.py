"""Characterize AttachNugget in a small world."""

FRAME = 1 / 15


def test_attachment_teleports_the_child_and_tracks_the_parent(weapon_world):
    """AttachNugget links a caster to a ground vehicle and applies the two sets of status bits."""
    s, fire = weapon_world
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
    fire(xml, target, caster)
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
