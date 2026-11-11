"""JetAIUpdate ordinary move: one retail Vindicator, no combat or airfield."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('jet_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('check', ['a', 'b'])
def test_jet_vindicator_ordinary_move_first_entry_and_survival(check):
    import build
    import sim
    from parts import contract, merged

    m, t, mod = build.resolve('engine_jet', check)
    assert len(mod) <= 15 and mod.isalnum()
    assert not contract(merged(m, t))
    assert len(m.objects) == 1 and len(t.counters) == 4
    e = sim.Sim(m, t).run(25)
    rows = [(sec, row) for sec, row in e.series if sec >= 2]
    assert rows and all(row[3] == 100 for _, row in rows)
    arrived = [row for _, row in rows if row[1] == 1]
    # Bench a s6-s26: 97/1/1/100; b s3-s26: 47/1/1/100.
    assert arrived and all(row[1:] == [1, 1, 100] for row in arrived)
    measured = 97 if check == 'a' else 47
    assert build.report(t, [(sec, [measured, 1, 1, 100]) for sec in range(6, 25)])[1] == 0
    assert build.report(t, [(sec, [measured + 1, 1, 1, 100]) for sec in range(6, 25)])[1] > 0
    assert e.body(m.role('jet').name).alive
    # Mutation: without the move order there must be no first-entry signal.
    m, t, _ = build.resolve('engine_jet', check)
    t.scripts = [s for s in t.scripts if s.name != 'Jet - move']
    blind = sim.Sim(m, t).run(25)
    assert not any(row[1] for _, row in blind.series)


@pytest.mark.parametrize('check, measured', [('a', 97), ('b', 47)])
@pytest.mark.parametrize('frame_clock', [False, True], ids=['default', 'frame-reference'])
def test_jet_vindicator_first_entry_frame_matches_bench(check, measured, frame_clock):
    """Both movement clocks must eventually match the independent bench counters.

    Jet startup uses its own frame cadence under either global movement clock.
    """
    import build
    import sim

    m, t, _ = build.resolve('engine_jet', check)
    e = sim.Sim(m, t)
    assert e.eng is not None, 'This replay requires the frame-based script model'
    e.shot_clock = frame_clock
    e.run(15)
    arrived = [row for _, row in e.series if row[1] == 1]
    assert arrived
    assert {row[0] for row in arrived} == {measured}


@pytest.mark.parametrize('check, entry', [('a', 112), ('b', 62)])
@pytest.mark.parametrize('frame_clock', [False, True])
def test_jet_startup_replays_d43_frame_positions(check, entry, frame_clock):
    """D43 a/b share the whole startup, not just a fitted endpoint counter."""
    import build
    import sim

    m, t, _ = build.resolve('engine_jet', check)
    e = sim.Sim(m, t)
    e.shot_clock = frame_clock
    jet = e.body(m.role('jet').name)
    positions = {}
    move = e.move

    def record(dt=sim.DT, precise=False):
        move(dt, precise)
        if precise:
            positions[e.eng.frame] = (jet.x, jet.y)

    e.move = record
    e.run(9)
    # Public measurements from D43's read-only position probe, rounded to 0.1.
    startup_x = [582.7, 586.2, 590.5, 595.6, 601.5, 608.2, 615.7,
                 624.0, 633.1, 643.0, 653.7, 665.2, 677.2]
    for frame, x in enumerate(startup_x, 16):
        assert positions[frame] == pytest.approx((x, 2375), abs=.051)
    assert positions[29][0] - positions[28][0] == pytest.approx(12)
    edge = t.waypoints['Jet Goal'][0] - 100
    assert positions[entry - 1][0] < edge <= positions[entry][0]
    assert ('JetAIUpdate', jet.template) in e.unmodeled  # unmeasured states remain visible


@pytest.mark.parametrize('variant', ['turn', 'configuration', 'repeated', 'speed-change'])
def test_jet_unmeasured_motion_does_not_reuse_startup(variant):
    import build
    import sim

    m, t, _ = build.resolve('engine_jet', 'a')
    e = sim.Sim(m, t)
    jet = e.body(m.role('jet').name)
    if variant == 'turn':
        jet.angle = 1
    elif variant == 'configuration':
        e.own[jet.template] = '<GameObject id="AlliedAntiGroundAircraft" inheritFrom="AlliedAntiGroundAircraft"/>'
    e.order_move(jet, 'Jet Goal', False)
    if variant == 'repeated':
        assert jet.jet_motion is not None
        e.order_move(jet, 'Jet Goal', False)
        jet.path = []
        e.order_move(jet, 'Jet Goal', False)
        assert jet.jet_motion is None
    elif variant == 'speed-change':
        assert jet.jet_motion is not None
        jet.speed = 90
        import simjet
        assert simjet.distance(e, jet) == 6
        jet.speed = 180
        assert simjet.distance(e, jet) == 12  # cannot restart the measured acceleration
    else:
        assert jet.jet_motion is None
    assert ('jet movement', jet.template) in e.unmodeled


def test_jet_routing_leaves_ground_movement_on_its_existing_clock():
    import build
    import sim

    m, t, _ = build.resolve('engine_jet', 'a')
    m.objects[0].template = 'AlliedAntiInfantryVehicle'
    e = sim.Sim(m, t)
    vehicle = e.body(m.role('jet').name)
    e.order_move(vehicle, 'Jet Goal', False)
    assert vehicle.path and not vehicle.frame_move and vehicle.jet_motion is None
    assert not vehicle.jet_started and not e.frame_movers
    assert not any(kind in ('jet movement', 'JetAIUpdate') for kind, _ in e.unmodeled)
