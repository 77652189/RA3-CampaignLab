"""The AttachUpdate module (engine/modules/attach.py, step M7): the direct teleport / stick / status subset read, any
other shape False; the body's attachment_rules forwarded as {module id: rule}, {} without one; the statuses a rule's
links set made known to the script conditions. The bench replay: engine_attach (tests/test_simbench_c.py)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
from engine.modules import attach  # noqa: E402

HEAD = ' id="ModuleTag_Attach" Flags="STICK_TO_PARENT TELEPORT" Range="50" ParentStatus="X_P" AttachedObjectStatus="X_C"'


def test_the_supported_subset_is_read():
    d = attach.AttachData.parse(HEAD, '')
    assert d.id == 'ModuleTag_Attach'
    assert d.rule == dict(flags={'STICK_TO_PARENT', 'TELEPORT'}, range=50.0, child={'X_C', 'ATTACHED'},
                          parent={'X_P'})
    d = attach.AttachData.parse(HEAD.replace('TELEPORT"', 'TELEPORT ONE_ATTACH_PER_PARENT"'), '')
    assert 'ONE_ATTACH_PER_PARENT' in d.rule['flags']
    # engine_attach_nocoll n: NO_COLLISIONS in AttachedObjectStatus is never given
    assert attach.AttachData.parse(HEAD.replace('"X_C"', '"NO_COLLISIONS X_C"'), '').rule['child'] == {'X_C', 'ATTACHED'}


def test_any_other_shape_is_false():
    for head, inner in ((HEAD, '<Child />'),
                        (HEAD.replace(' TELEPORT', ''), ''),
                        (HEAD.replace('TELEPORT"', 'TELEPORT LEECH"'), ''),
                        (HEAD + ' IdleDetach="true"', ''),
                        (' id="M"', '')):        # no Flags: the default holds USE_GEOMETRY
        assert attach.AttachData.parse(head, inner).rule is False, head


def test_the_body_forwards_its_rules_and_the_known_statuses():
    import sim
    import engine.testing.small as simsmall
    e = simsmall.small_world()
    e.own['CNV_TestAttach'] = ('<GameObject id="CNV_TestAttach" Side="Neutral" KindOf="INFANTRY"><Behaviors>'
                               f'<AttachUpdate{HEAD} /></Behaviors></GameObject>')
    e.add('leech', 'CNV_TestAttach', 'Player_1', 100.0, 100.0)
    e.add('plain', 'AlliedMiner', 'Player_1', 200.0, 100.0)
    with_rules = [b for b in e.bodies.values() if b.attachment_rules]
    assert [b.name for b in with_rules] == ['leech']
    assert {'X_C', 'X_P'} <= e.attachment_known_status
    for b in with_rules:
        mods = b.find(sim.kernel_interfaces.Attach)
        assert b.attachment_rules == {x.module_id(): x.rule() for x in mods}
        for rule in b.attachment_rules.values():
            if rule:
                assert rule['child'] | rule['parent'] <= e.attachment_known_status
    assert all(b.attachment_rules == {} for b in e.bodies.values() if not b.find(sim.kernel_interfaces.Attach))


def test_the_repair_drones_take_one_hurt_vehicle_each_mend_it_and_let_go():
    """E181 / E235 (checks/engine_assignslaves.py): the war factory's drones, each to its own hurt vehicle within 200."""
    import engine.testing.small as simsmall
    e = simsmall.small_world()
    f = e.add('factory', 'AlliedWarFactory', 'Player_1', 1000.0, 1000.0)
    near, near2, far = (e.add(n, 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1000.0 + dx, 1100.0)
                        for n, dx in (('near', 0.0), ('near2', 60.0), ('far', 400.0)))
    for v in (near, near2, far):
        v.health = 50.0
    e.advance(30)
    held = sorted(m.repairing().name for d in f.spawned_children for m in d.find(attach.interfaces.Attach)
                  if m.repairing() is not None)
    assert held == ['near', 'near2'] and 'UNDERGOING_REPAIR' in near.status and not far.status
    e.advance(15 * 13)
    assert near.hp == near.max_hp and not near.status & {'TARGETED_FOR_REPAIR', 'UNDERGOING_REPAIR'}
    assert far.health == 50.0
