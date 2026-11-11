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
    # Bench a s6-s26: 97/1/1/100; b s3-s26: 47/1/1/100. Timing is checked separately;
    # the coarse model's sample clock is not the bench's screenshot clock.
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
@pytest.mark.xfail(strict=True, reason='E40 engine_jet:a/b bench 97/47; default 91/39, '
                   'frame reference 92/42 leaves common 5-frame timing gap; '
                   'work/re/handoff-e.md 待答问题 E40')
def test_jet_vindicator_first_entry_frame_matches_bench(check, measured, frame_clock):
    """Both movement clocks must eventually match the independent bench counters.

    shot_clock changes the movement cadence here; it does not model Jet startup.
    Keep the measured target unchanged in both cases, so fixing coarse phase
    alone cannot silently close the engine timing gap.
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
