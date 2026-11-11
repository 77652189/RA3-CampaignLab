"""JetAIUpdate ordinary move: one retail Vindicator, no combat or airfield."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('jet_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_jet_vindicator_ordinary_move_first_entry_and_survival():
    import build
    import sim
    from parts import contract, merged

    m, t, mod = build.resolve('engine_jet', 'a')
    assert len(mod) <= 15 and mod.isalnum()
    assert not contract(merged(m, t))
    assert len(m.objects) == 1 and len(t.counters) == 4
    e = sim.Sim(m, t).run(25)
    rows = [(sec, row) for sec, row in e.series if sec >= 2]
    assert rows and all(row[3] == 100 for _, row in rows)
    arrived = [row for _, row in rows if row[1] == 1]
    # Bench s6-s26: 97 / 1 / 1 / 100. Timing is checked separately below;
    # the coarse model's sample clock is not the bench's screenshot clock.
    assert arrived and all(row[1:] == [1, 1, 100] for row in arrived)
    assert build.report(t, [(sec, [97, 1, 1, 100]) for sec in range(6, 25)])[1] == 0
    assert e.body(m.role('jet').name).alive
    # Mutation: without the move order there must be no first-entry signal.
    m, t, _ = build.resolve('engine_jet', 'a')
    t.scripts = [s for s in t.scripts if s.name != 'Jet - move']
    blind = sim.Sim(m, t).run(25)
    assert not any(row[1] for _, row in blind.series)


@pytest.mark.xfail(strict=True, reason='E38 engine_jet:a first-entry counter 97 vs model 91; '
                   'takeoff/acceleration/turning unresolved; work/re/handoff-e.md E38')
def test_jet_vindicator_first_entry_frame_matches_bench():
    """engine_jet:a latched 97 on the bench, constant-speed model currently 91."""
    import build
    import sim

    m, t, _ = build.resolve('engine_jet', 'a')
    e = sim.Sim(m, t).run(15)
    arrived = [row for _, row in e.series if row[1] == 1]
    assert arrived
    assert {row[0] for row in arrived} == {97}
