"""A whole run's snapshot (experimental/cnv/simsnap.py; step S, docs/engine/sim-modules.md 9.2, guard 7): heal_a
taken at its half, through JSON and back equal, written onto a Sim made anew for the same mission, taken again
equal (4.2), and run on to its end as the one never stopped; every field of the Sim, its parts and its bodies
sorted (4.3); the fields called static the same on the new world; what it cannot keep an error. The kernel's and
the executor's own: tests/modules/test_snapshot_kernel.py. The 9 missions without the AI frame for frame: 11b-3c."""
import json

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import build  # noqa: E402
import sim  # noqa: E402
import simrecord  # noqa: E402
import simsnap  # noqa: E402
from engine.kernel import snap  # noqa: E402
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
        except TypeError:           # the mission merged with its test (a dataclass), the trigger areas: by fields
            same = type(a) is type(b) and (a == b or vars(a) == vars(b))
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
    taken['bodies'].append(['#late', 10 ** 6, '#late', 'X', {}])
    with pytest.raises(NotImplementedError, match='11b-3c'):
        simsnap.restore(sim.Sim(m, t, model=False), taken)
