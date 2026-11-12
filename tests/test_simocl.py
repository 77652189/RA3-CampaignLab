"""E62 named engine replays: valid stays 100/100 through cast frame 352,
then 86/86 at 361; none/wrong are already 86/86 at frames 30/28 and
47/47 at s12. PLAYER_TRIGGERED_SPECIAL_POWER counts 1/0/0.
Raw results and the bounded-window rejudge: work/re/e_ocl_e62.md.
E63 empty-reference replay: first enemy hit at frame 30 gives 86/86,
frame 119 gives 47/47, with cast count 1. See work/re/e_ocl_e63.md.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench', ROOT / 'experimental/cnv/simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


@pytest.mark.parametrize('mission,protected', [('engine_oclcurtain', True),
                                              ('engine_oclnone', False),
                                              ('engine_oclwrong', False)])
def test_iron_curtain_ocl_host_boundary(mission, protected):
    import build
    import sim
    m, t, _ = build.resolve(mission, 'a')
    s = sim.Sim(m, t).run(34.0)
    rows = [row for _, row in s.series if 90 <= row[0] <= 180]
    assert rows
    assert all(row[3] == int(protected) for row in rows), rows
    if protected:
        assert all(row[1:3] == [100, 100] for row in rows), rows
        assert s.series[-1][1][1] < 100 and s.series[-1][1][2] < 100
    else:
        assert all(row[1] < 100 and row[2] < 100 for row in rows), rows
    verdicts = build.judge(t, s.series)
    assert all(ok for ok, _ in verdicts), verdicts


def test_iron_curtain_empty_ocl_reference():
    """E63: empty OCL dispatches once without protecting against enemy fire."""
    import build
    import sim
    m, t, _ = build.resolve('engine_oclempty', 'a')
    s = sim.Sim(m, t).run(34.0)
    rows = [row for _, row in s.series if 90 <= row[0] <= 180]
    assert rows
    assert all(row[1] < 100 and row[2] < 100 and row[3] == 1 for row in rows), rows
    assert all(ok for ok, _ in build.judge(t, s.series))
    assert not any('OCLSpecialPower' in gap['what'] for gap in s.unmodeled.values()), s.unmodeled
