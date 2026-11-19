"""The SpawnBehavior / SlavedUpdate modules (engine/modules/spawn.py, step M7): the two configurations read exactly
(the war factory's drones, the refineries' collector), anything else neither; removed blocks absent from the template;
a child's death queuing its replacement the delay on, made in the spawn cell when due
and not before; the parent's death emptying the queue; a child template without SlavedUpdate given one; the body's
forwards with the old defaults. The bench replays: tests/test_simspawn.py."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import spawn  # noqa: E402


def data(template, own=None):
    return [spawn.SpawnData.parse(*b) for b in simunits.module_blocks(template, 'SpawnBehavior', own)]


def test_the_war_factory_s_drones_are_read_and_any_change_is_not_them():
    (d,) = data('AlliedWarFactory')
    assert (d.child, d.unpack, d.delay) == ('AlliedWarFactoryRepairDrone', None, 150)
    xml = simunits._xml('AlliedWarFactory')
    for changed in (xml.replace('InitialBurst="3"', 'InitialBurst="1"'),
                    xml.replace('SpawnedRequireSpawner="true"', 'SpawnedRequireSpawner="false"'),
                    xml.replace('<SpawnTemplate>AlliedWarFactoryRepairDrone</SpawnTemplate>',
                                '<SpawnTemplate>AlliedAirfieldRepairDrone</SpawnTemplate>'),
                    xml.replace('DeathTypes="ALL"', 'DeathTypes="NORMAL"')):
        assert changed != xml
        assert [(d.child, d.unpack) for d in data('AlliedWarFactory', {'AlliedWarFactory': changed})] == [(None, None)]


def test_each_refinery_gives_its_one_collector_and_a_changed_one_does_not():
    for refinery, miner in (('AlliedRefinery', 'AlliedMiner'), ('SovietRefinery', 'SovietMiner'),
                            ('JapanRefinery', 'JapanMiner')):
        assert [(d.id, d.unpack, d.child) for d in data(refinery)] == [('ModuleTag_Spawn', miner, None)]
    xml = simunits._xml('AlliedRefinery')
    changed = xml.replace('IsOneShotData="true"', 'IsOneShotData="false"')
    assert changed != xml and [d.unpack for d in data('AlliedRefinery', {'AlliedRefinery': changed})] == [None]


def test_a_remove_block_leaves_no_spawn_module():
    # Compiled AlliedRefinery_NoHarvester: zero SpawnBehavior modules after removal of ModuleTag_Spawn.
    assert data('alliedrefinery_noharvester') == []


def _world():
    from engine.kernel import world as kernel_world
    from engine.kernel.module import Thing as KThing
    made = []

    class T(KThing):
        def __init__(self, name, template):
            self.name, self.template, self.alive = name, template, True

    def make(thing, m, template):
        child = T(f'child{len(made)}', template)
        child.modules = w.build(child, w.frame)
        (child.find(interfaces.Slaved) or w.attach(child, 'SlavedUpdate')).enslave(thing, m)
        m.adopt(child)
        made.append(child)
        return child

    def remove(thing, why):
        thing.alive, thing.deleted = False, True
        w.removed.append((thing.name, why))
    w = kernel_world.World(lambda t, tag: simunits.module_blocks(t, tag), spawn=make, remove=remove)
    w.removed = []
    return w, T, made


def test_a_dead_child_is_replaced_the_delay_on_in_the_spawn_cell_and_not_before():
    w, T, made = _world()
    parent = T('factory', 'AlliedWarFactory')
    parent.modules = w.build(parent, 0)
    (m,) = parent.find(interfaces.Spawn)
    w.schedule.run('spawn', 0)                  # nothing queued: asleep
    assert w.schedule.awake('spawn') == {}
    m.child_died('AlliedWarFactoryRepairDrone', 40)
    assert m.refills() == [(190, 'ModuleTag_SpawnRepairDrones', 'AlliedWarFactoryRepairDrone')]
    assert w.schedule.awake('spawn') == {m: 190}
    w.schedule.run('spawn', 189)
    assert not made and len(m.refills()) == 1
    w.schedule.run('spawn', 190)
    assert len(made) == 1 and m.refills() == [] and m.children() == made
    assert made[0].find(interfaces.Slaved).slaver() is parent
    assert made[0].find(interfaces.Slaved).slaver_module() == 'ModuleTag_SpawnRepairDrones'
    assert w.schedule.awake('spawn') == {}      # asleep again
    m.child_died('AlliedWarFactoryRepairDrone', 200)
    parent.alive = False                        # a dead parent makes nothing, even with one queued
    w.schedule.run('spawn', 1000)
    assert len(made) == 1
    m.on_destroy()                              # its end: the queue emptied, the living child deleted with it
    assert m.refills() == [] and w.removed == [('child0', 'SpawnedRequireSpawner')]


def test_a_childs_death_tells_its_maker_and_a_deletion_only_notes_a_gap():
    from engine.kernel import module as kmodule
    w, T, made = _world()
    parent = T('factory', 'AlliedWarFactory')
    parent.modules = w.build(parent, 0)
    (m,) = parent.find(interfaces.Spawn)
    w.frame = 5
    m.on_create(0)
    child = w.spawn(parent, m, 'AlliedWarFactoryRepairDrone')
    sl = child.find(interfaces.Slaved)
    assert isinstance(sl, interfaces.Die) and isinstance(sl, interfaces.Destroy)
    child.alive, child.deleted = False, False
    sl.on_die(kmodule.Death(40, 'test'))
    sl.on_destroy()                             # a death's Destroy notes nothing
    assert m.refills() == [(190, 'ModuleTag_SpawnRepairDrones', 'AlliedWarFactoryRepairDrone')] and not w.gaps
    other = w.spawn(parent, m, 'AlliedWarFactoryRepairDrone')
    other.alive, other.deleted = False, True
    other.find(interfaces.Slaved).on_destroy()  # deleted: no refill, a gap
    assert len(m.refills()) == 1 and list(w.gaps) == [('SpawnBehavior', 'AlliedWarFactory')]
    parent.alive = False
    third = w.spawn(parent, m, 'AlliedWarFactoryRepairDrone')
    third.find(interfaces.Slaved).on_die(kmodule.Death(50))     # a dead maker hears nothing
    assert len(m.refills()) == 1


def test_two_queued_replacements_each_come_on_their_own_frame():
    w, T, made = _world()
    parent = T('factory', 'AlliedWarFactory')
    parent.modules = w.build(parent, 0)
    (m,) = parent.find(interfaces.Spawn)
    m.child_died('AlliedWarFactoryRepairDrone', 10)
    m.child_died('AlliedWarFactoryRepairDrone', 11)
    m.child_died('AlliedWarFactoryRepairDrone', 30)
    w.schedule.run('spawn', 160)
    assert len(made) == 1 and w.schedule.awake('spawn') == {m: 161}
    w.schedule.run('spawn', 161)
    assert len(made) == 2 and w.schedule.awake('spawn') == {m: 180}
    w.schedule.run('spawn', 180)
    assert len(made) == 3 and m.refills() == []


def test_a_child_without_slavedupdate_is_given_one_and_the_record_keeps_the_old_fields():
    import simsmall
    e = simsmall.small_world([('factory', 'AlliedWarFactory', 'Player_1', 100.0, 100.0)])
    parent = e.bodies['factory']
    (sp,) = parent.find(interfaces.Spawn)
    assert len(parent.spawned_children) == 3          # the initial burst of a placed factory
    assert all(c.spawn_parent is parent for c in parent.spawned_children)
    bare = e.add('bare', 'AlliedMiner', parent.owner, 0, 0)
    assert bare.find(interfaces.Slaved) is None
    assert (bare.spawn_parent, bare.spawn_module, bare.spawned_children, bare.spawn_refills,
            bare.attachment_rules) == (None, '', [], [], {})
    child = e.spawn_child(parent, sp, 'AlliedMiner', e.t)
    assert child.find(interfaces.Slaved).slaver() is parent and child.spawn_parent is parent
    assert child.spawn_module == 'ModuleTag_SpawnRepairDrones' and parent.spawned_children[-1] is child
    for b in (parent, child, bare):
        d = simrecord.body_state(b)
        assert {'spawned_children', 'spawn_refills', 'spawn_parent', 'spawn_module', 'attachment_rules'} <= set(d)
    assert simrecord.body_state(child)['spawn_parent'] is parent
    assert simrecord.body_state(parent)['spawned_children'] == parent.spawned_children
