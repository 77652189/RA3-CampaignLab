"""A whole run's snapshot (experimental/cnv/simsnap.py; step S, docs/engine/sim-modules.md 9.2, guard 7): heal_a
taken at its half, through JSON and back equal, written onto a Sim made anew for the same mission, taken again
equal (4.2), and run on to its end as the one never stopped; every field of the Sim, its parts and its bodies
sorted (4.3); the fields called static the same on the new world; what it cannot keep an error. The kernel's and
the executor's own: tests/modules/test_snapshot_kernel.py. The 9 missions without the AI frame for frame: 11b-3c.
On the island (simsmall): a sequential script queued and run, an order given, a moved waypoint, a module's field
set in the run (review 1119e #1-#4 #8 #9); a cut at the run's end refused (review 1119g #3)."""
import gc
import io
import json

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import build  # noqa: E402
import parts  # noqa: E402
import sim  # noqa: E402
import simrecord  # noqa: E402
import simbody  # noqa: E402
import simpower  # noqa: E402
import simsmall  # noqa: E402
import simsnap  # noqa: E402
from engine.kernel import interfaces, snap  # noqa: E402
from engine.ports.command import Command  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402

TASK = 'heal_a'                 # one of guard 7's fixed missions (simrecord.TASKS), half of its run and the end
_, _WHERE, END = simrecord.TASKS[TASK]
HALF = END / 2


@pytest.fixture(scope='module')
def heal():
    m, t, _ = build.resolve(*_WHERE)
    run = sim.Sim(m, t, model=False)
    run.run(HALF)
    taken = simsnap.snapshot(run)
    fresh = sim.Sim(m, t, model=False)
    restored = sim.Sim(m, t, model=False)
    simsnap.restore(restored, json.loads(json.dumps(taken)))
    return m, t, run, taken, fresh, restored


def test_taken_through_json_and_back_equal(heal):
    taken = heal[3]
    assert json.loads(json.dumps(taken)) == taken


def test_written_onto_a_new_run_and_taken_again_equal(heal):
    _, _, _, taken, _, restored = heal
    again = simsnap.snapshot(restored)
    assert [k for k in taken if again[k] != taken[k]] == []


def test_the_restored_run_goes_on_as_the_one_never_stopped(heal):
    m, t, run, taken, _, _ = heal
    a = sim.Sim(m, t, model=False)
    a.run(HALF)
    b = sim.Sim(m, t, model=False)
    simsnap.restore(b, json.loads(json.dumps(simsnap.snapshot(a))))
    a.run(END)
    b.run(END)
    oa, ob = Observe(a), Observe(b)
    assert [x.name for x in oa.things()] == [x.name for x in ob.things()]
    assert [x.name for x, y in zip(oa.things(), ob.things()) if oa.state(x) != ob.state(y)] == []
    assert (a.t, a.world.frame, a.log) == (b.t, b.world.frame, b.log)
    ends = [json.loads(json.dumps(simsnap.snapshot(s))) for s in (a, b)]     # what the things' state does not show
    assert simrecord.differences(*ends) == []
    assert a.report() == b.report()


def test_every_field_is_sorted(heal):
    run = heal[2]
    assert simsnap.unclassified(run) == []
    run.brand_new_field = 1
    next(iter(run.bodies.values())).brand_new_too = 2
    run.wallet.another = 3
    money = run.money
    run.money = dict(money)
    try:
        assert simsnap.unclassified(run) == ['Body.brand_new_too', 'sim.brand_new_field',
                                             'sim.money (not the object it names)', 'sim.wallet.another']
    finally:
        del run.brand_new_field, next(iter(run.bodies.values())).brand_new_too, run.wallet.another
        run.money = money


def _static(table, at=()):
    for f, kind in table.items():
        if isinstance(kind, dict):
            yield from _static(kind, at + (f,))
        elif kind == simsnap.STATIC:
            yield at + (f,)


def test_the_static_fields_are_the_new_worlds(heal):
    run, fresh = heal[2], heal[4]
    codec = simsnap._Codec(run)
    moved = []
    for p in _static(simsnap.SIM):
        a, b = simsnap._get(run, p), simsnap._get(fresh, p)
        if a is b:
            continue
        try:
            same = snap.encode(a, codec.extra) == snap.encode(b, codec.extra)
        except TypeError:           # the mission merged with its test (a dataclass): by fields
            same = type(a) is type(b) and (a == b or vars(a) == vars(b))
        if same and isinstance(a, dict) and hasattr(a, '__dict__'):    # a dict's own fields: dict == leaves them out
            same = vars(a) == vars(b)
        if not same:
            moved.append('.'.join(p))
    assert moved == []


def test_one_container_in_two_places_comes_back_one(heal):
    m, t = heal[0], heal[1]
    a = sim.Sim(m, t, model=False)
    a.run(1.0)
    b1, b2 = list(a.bodies.values())[:2]
    shared = [1, 2]
    b1.leaves, b2.leaves = shared, shared
    b = sim.Sim(m, t, model=False)
    simsnap.restore(b, json.loads(json.dumps(simsnap.snapshot(a))))
    n1, n2 = list(b.bodies.values())[:2]
    assert n1.leaves == [1, 2] and n1.leaves is n2.leaves


def _shadowed(m, t):
    """heal_a with its first body's name taken by a later one (two map objects of one name, as retail_a02's palms):
    the first is out of bodies and the schedule and still held (here in refs; on a retail map in topples)."""
    s = sim.Sim(m, t, model=False)
    old = next(iter(s.bodies.values()))
    s.refs['old'] = old
    s.add(old.name, old.template, old.owner, old.x + 30.0, old.y)
    return s, old


def test_a_thing_held_out_of_bodies_comes_back_by_its_serial(heal):
    m, t = heal[0], heal[1]
    a, old = _shadowed(m, t)
    a.run(HALF)
    old.leaves = [old.serial]               # a field of its own, set in the run
    taken = json.loads(json.dumps(simsnap.snapshot(a)))
    assert [o[:3] for o in taken['others']] == [[old.serial, old.name, old.template]]
    b, held = _shadowed(m, t)
    simsnap.restore(b, taken)
    assert b.refs['old'] is held and b.bodies[held.name] is not held and held.leaves == [held.serial]
    assert simsnap.snapshot(b) == taken
    a.run(END)
    b.run(END)
    oa, ob = Observe(a), Observe(b)
    assert [x.name for x, y in zip(oa.things(), ob.things()) if oa.state(x) != ob.state(y)] == []
    def own(x):         # its fields and its modules' STATE (the modules themselves are the new world's objects)
        return ({f: v for f, v in vars(x).items() if f != 'modules'},
                [{f: vars(m).get(f) for f in m.STATE} for m in x.modules])
    assert (a.t, a.world.frame, a.log, own(old)) == (b.t, b.world.frame, b.log, own(held))


def test_what_it_cannot_keep_is_an_error(heal):
    m, t = heal[0], heal[1]
    a = sim.Sim(m, t, model=False)
    a.asked['x'] = object()
    with pytest.raises(TypeError, match='sim.asked'):
        simsnap.snapshot(a)
    del a.asked['x']
    stray = sim.Sim(m, t, model=False).bodies
    a.refs['r'] = next(iter(stray.values()))
    other = next(iter(stray.values()))
    other.serial = 10 ** 6
    with pytest.raises(ValueError, match='not bodies of the run'):
        simsnap.snapshot(a)
    del a.refs['r']
    taken = simsnap.snapshot(a)
    gone = taken['bodies'].pop()
    with pytest.raises(ValueError, match='not in the snapshot'):
        simsnap.restore(sim.Sim(m, t, model=False), taken)
    taken['bodies'].append(gone)
    row = taken['kernel']['things'][-1]
    row[1].append('LifetimeUpdate')                 # a module more than its template makes, none attached
    with pytest.raises(ValueError, match='has modules'):
        simsnap.restore(sim.Sim(m, t, model=False), taken)
    row[1].append('LifetimeUpdate')                 # two more, one attached
    taken['kernel']['late'].append([row[0], [['LifetimeUpdate', '']]])
    with pytest.raises(ValueError, match='1 attached, the snapshot'):
        simsnap.restore(sim.Sim(m, t, model=False), taken)


# ---- on the island: what a script, an order or a module sets in the run
SEQ = parts.Mission(name='seq', map=simsmall.island, scripts=[
    parts.Script('seqtask', [], [('INCREMENT_COUNTER', 1, 'score')], once=False)])


def _seq_world():
    s = sim.Sim(SEQ, model=False)
    s.add('unit', 'AlliedAntiInfantryInfantry', 'Player_1', 300, 300)
    return s


def _go_on(a, b, frames):
    """Both runs `frames` frames on; their counters, logs, clocks, each thing's state."""
    for s in (a, b):
        s.advance(frames)
    oa, ob = Observe(a), Observe(b)
    assert [x.name for x, y in zip(oa.things(), ob.things()) if oa.state(x) != ob.state(y)] == []
    assert (a.t, a.world.frame, dict(a.counters), a.log) == (b.t, b.world.frame, dict(b.counters), b.log)


def _fork(a, b):
    taken = simsnap.snapshot(a)
    assert json.loads(json.dumps(taken)) == taken
    simsnap.restore(b, json.loads(json.dumps(taken)))
    assert simsnap.snapshot(b) == taken


def test_a_sequential_script_run_is_not_run_again():
    """1119e #1: the queued script turned subroutine; written back it stays one (not run every frame)."""
    a = _seq_world()
    a.act('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', ['unit', 'seqtask'], None)
    a.advance(15)
    assert (a.seq, a.counters.get('score'), a.executor.script_named('seqtask').subroutine) == ([], 1, True)
    b = _seq_world()
    _fork(a, b)
    assert b.executor.script_named('seqtask').subroutine
    _go_on(a, b, 40)
    assert b.counters.get('score') == 1


def test_a_sequential_script_waiting_is_kept_by_its_key():
    """1119e #3: Sim.seq holds the map's script: kept by the executor's key, the new executor's script again."""
    a = _seq_world()
    a.act('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', ['unit', 'seqtask'], None)
    assert len(a.seq) == 1
    b = _seq_world()
    _fork(a, b)
    assert b.seq[0]['script'] is b.executor.script_named('seqtask') and b.seq[0]['b'] is b.bodies['unit']
    _go_on(a, b, 30)
    assert (a.seq, b.counters.get('score')) == ([], 1)


def _island():
    s = simsmall.small_world([('unit', 'AlliedAntiInfantryInfantry', 'Player_1', 300, 300)], model=False)
    s.waypoints['dest'] = (400, 300)
    return s


def test_an_order_given_is_kept():
    """1119e #2: the command port's history holds the Command; a run that gave one is taken, and goes on the same."""
    a = _island()
    a.advance(15)
    assert a.commands.post(Command('move', units=('unit',), place='dest'), a.t + 1)[0]
    b = _island()
    _fork(a, b)
    assert b.commands.pending() == a.commands.pending() != ()
    _go_on(a, b, 60)
    assert [x[3] for x in b.commands.issued()] == [x[3] for x in a.commands.issued()] == ['posted', 'done']


def test_waypoints_are_each_runs_own():
    """1119e #4: two runs of one mission do not share its waypoints; writing one back leaves the source as it is."""
    a = _seq_world()
    a.waypoints['spot'] = (1, 2)
    taken = json.loads(json.dumps(simsnap.snapshot(a)))
    a.waypoints['spot'] = (3, 4)
    b = _seq_world()
    assert b.waypoints is not a.waypoints and 'spot' not in b.waypoints
    simsnap.restore(b, taken)
    b.waypoints['spot'] = (5, 6)
    assert (a.waypoints['spot'], sim.Sim(SEQ, model=False).waypoints.get('spot')) == ((3, 4), None)


def test_another_worlds_thing_of_the_same_serial_is_an_error():
    """1119e #8: a thing of another run with a serial this run gave too is not taken as this run's."""
    a, b = _island(), _island()
    assert a.bodies['unit'].serial == b.bodies['unit'].serial
    a.refs['r'] = b.bodies['unit']
    with pytest.raises(ValueError, match='not bodies of the run'):
        simsnap.snapshot(a)


def test_a_thing_made_in_the_run_and_a_module_attached_come_back():
    """11b-3c ① ②: a thing made after the start is built bare on the new run (its modules made, no on_create, the
    schedule the snapshot's), and a module attached in the run (World.attach: a late lifetime, a reload for a power
    no block serves) is made again -- on the thing made in the run and on one of the start."""
    a = _island()
    a.advance(15)
    late = a.add('late', 'AlliedAntiInfantryInfantry', 'Player_1', 350, 300, by='unit', at=a.t)
    simbody.last_until(a, late, a.world.frame + 30)
    simpower.start_reload(a, a.bodies['unit'], 'SpecialPowerTestReload', a.world.frame + 45)
    a.advance(5)
    assert sorted(a.world.late) == sorted([late.serial, a.bodies['unit'].serial])
    b = _island()
    assert 'late' not in b.bodies
    _fork(a, b)
    assert type(b.bodies['late']) is sim.Body and b.bodies['late'].serial == late.serial
    assert [type(m).__name__ for m in b.bodies['unit'].modules] == [type(m).__name__ for m in a.bodies['unit'].modules]
    _go_on(a, b, 60)
    assert (a.bodies['late'].alive, b.bodies['late'].alive) == (False, False)


def _replace_attached(s, n):
    """`n` times a new 'same' in the name's place, each with a late lifetime (World.attach); the last one's serial."""
    for _ in range(n):
        b = s.add('same', 'AlliedAntiInfantryInfantry', 'Player_1', 350, 300)
        simbody.last_until(s, b, s.world.frame + 300)
    serial = b.serial
    del b
    gc.collect()
    return serial


def test_a_replaced_things_attached_row_goes_with_it():
    """1119j #3: a thing replaced under its name and reclaimed leaves no row in World.late (it had kept one per
    thing ever attached to) -- on the run and on one written back (its rows bound to the restored table)."""
    a = _island()
    last = _replace_attached(a, 30)
    assert sorted(a.world.late) == [last]
    b = _island()
    _fork(a, b)
    last = _replace_attached(b, 3)
    assert sorted(b.world.late) == [last]


def _yard():
    return simsmall.small_world([('yard', 'AlliedConstructionYard', 'Player_1', 600, 600)], model=False)


def test_a_yard_packed_is_kept():
    """1119p #3: packing a yard holds its frames in Sim.pack_hold (by serial) until the MCV is made (the press frame,
    PACK_FRAMES 0), an empty dict left: a run that packed one is taken, and goes on the same (the MCV held still as
    long)."""
    a = _yard()
    a.act('NAMED_USE_COMMANDBUTTON_ABILITY', ['yard', 'Command_PackAlliedMCV'], None)
    a.advance(2)
    assert (a.pack_hold, a.bodies['yard'].template) == ({}, 'AlliedMCV') and a.emp_until
    b = _yard()
    _fork(a, b)
    _go_on(a, b, 60)
    assert (a.bodies['yard'].template, a.pack_hold, a.emp_until) == (b.bodies['yard'].template, b.pack_hold,
                                                                      b.emp_until)


def _spy_world():
    s = simsmall.small_world(model=False)
    target = s.add('t', 'AlliedWarFactory', 'Player_2', 1000.0, 1000.0)
    s.add('spy', 'AlliedInfiltrationInfantry', s.human, 1000.0, 1000.0)
    s.relations[target.owner, s.human] = 'Enemy'
    return s


def test_a_spy_on_its_way_is_kept_and_an_older_versions_snapshot_refused_whole():
    """1119m #1: a spy on its way (Infiltrators.going) is the spy's serial -> (spy, target) since edd381f1, version 6;
    written back it walks in as on the run never stopped. A snapshot of version 5 (the name -> target it had then
    broke the first tick restored) is refused before anything is written."""
    a = _spy_world()
    spy, target = a.bodies['spy'], a.bodies['t']
    a.infiltrators.send(spy, target)
    spy.path = []
    taken = json.loads(json.dumps(simsnap.snapshot(a)))
    b = _spy_world()
    simsnap.restore(b, taken)
    assert b.infiltrators.going == {spy.serial: (b.bodies['spy'], b.bodies['t'])}
    for s in (a, b):
        s.infiltrators.tick()
        assert not s.bodies['spy'].alive and s.infiltrators.entered(s.bodies['t'], 'vehicle')
        assert not s.infiltrators.going
    old = dict(taken, version=5)
    c = _spy_world()
    before = simsnap.snapshot(c)
    with pytest.raises(ValueError, match='version 5'):
        simsnap.restore(c, old)
    assert simsnap.snapshot(c) == before


class _Derived(sim.Sim):
    """A host's Sim subclass declared in a module with no Body (1119j #4: restore read Body from here)."""


def test_a_sim_subclass_declared_where_no_body_is_is_restored():
    """1119j #4: written onto a subclass of sim.Sim from another module: with no thing made in the run, and with one
    (built bare as sim's Body, found along the subclass's classes)."""
    def derived():
        s = _Derived(SEQ, model=False)
        s.add('unit', 'AlliedAntiInfantryInfantry', 'Player_1', 300, 300)
        return s
    a = _seq_world()
    a.advance(15)
    _fork(a, derived())
    a.add('late', 'AlliedAntiInfantryInfantry', 'Player_1', 350, 300, by='unit', at=a.t)
    b = derived()
    _fork(a, b)
    assert type(b.bodies['late']) is sim.Body
    _go_on(a, b, 15)


def test_another_worlds_thing_at_a_serial_left_free_is_an_error():
    """1119h P3: the first of two things of one name, held by nothing once the second took its name, leaves its
    serial free in what the snapshot reaches; another run's thing of that serial is still not this run's."""
    a = simsmall.small_world([('same', 'AlliedAntiInfantryInfantry', 'Player_1', 300, 300)], model=False)
    a.add('same', 'AlliedAntiInfantryInfantry', 'Player_1', 320, 300)
    other = simsmall.small_world([('same', 'AlliedAntiInfantryInfantry', 'Player_1', 1600, 300)], model=False)
    assert other.bodies['same'].serial == 0 and a.bodies['same'].serial == 1
    a.refs['check'] = other.bodies['same']
    with pytest.raises(ValueError, match='not bodies of the run'):
        simsnap.snapshot(a)
    del a.refs['check']
    a.bodies['x'] = other.bodies['same']
    with pytest.raises(ValueError, match='did not number it'):
        simsnap.snapshot(a)


def test_an_area_name_the_map_has_not_is_kept():
    """4.4 (11-19): a name looked up the map has not (Areas.missing, the report's line) was the setup's, left out:
    retail_s01's 'AREA - P2 Delete Aircraft', looked up in the first half, was gone from the restored run's report."""
    a = _island()
    assert a.areas['AREA - nowhere'] == ()
    b = _island()
    _fork(a, b)
    assert b.areas.missing == {'AREA - nowhere'} and b.areas == a.areas
    _go_on(a, b, 15)
    assert a.report() == b.report()


def test_a_modules_field_set_in_the_run_is_unclassified():
    """1119e #9: a field set on a module of a thing outside its STATE is named (the source guard reads only
    `self.x = ...`)."""
    a = _island()
    assert simsnap.unclassified(a) == []
    m = a.bodies['unit'].find(interfaces.Body)
    m.review_timer = 7
    assert simsnap.unclassified(a) == [f'{type(m).__name__}.review_timer']


def test_a_modules_slot_set_in_the_run_is_unclassified():
    """1119i #7: a slot (beside the __dict__ a module has) set in the run is named too."""
    from engine.kernel.module import Module

    class Slotted(Module):
        __slots__ = ('review_slot',)

    a = _island()
    b = a.bodies['unit']
    m = Slotted(b, None, a.world)
    b.modules = b.modules + (m,)
    assert simsnap.unclassified(a) == []
    m.review_slot = 7
    assert simsnap.unclassified(a) == ['Slotted.review_slot']


def test_a_snapshot_of_another_shape_is_refused_before_a_write():
    """1119i #6: a snapshot of an older shape (an executor row short of `subroutine`, a host field this one does not
    keep) is refused whole, the new run as made -- not written half and failed."""
    a = _seq_world()
    a.advance(15)
    taken = json.loads(json.dumps(simsnap.snapshot(a)))
    for spoil in (lambda s: s['executor']['active'][0].pop(), lambda s: s['host'].append(['gone_field', 1]),
                  lambda s: s['bodies'][0].pop()):
        s = json.loads(json.dumps(taken))
        spoil(s)
        b = _seq_world()
        before = simsnap.snapshot(b)
        with pytest.raises(ValueError, match='not of this shape'):
            simsnap.restore(b, s)
        assert simsnap.snapshot(b) == before


def test_a_cut_with_no_frame_after_it_is_refused():
    """1119g #3: cut at the end (Sim.run stops past it), the written-back run would run no frame: refused."""
    with pytest.raises(ValueError, match='no frame left'):
        simrecord.run_task(TASK, io.StringIO(), snap='1')
