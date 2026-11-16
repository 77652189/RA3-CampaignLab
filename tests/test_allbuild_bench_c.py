"""Native construction observations, not a model-equivalence claim.

The action remains TODO: work/re/c_allbuild_report.md and handoff-c.md.
Only the common logical-frame window is comparable; capture seconds differ.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('allbuild_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
import simai


@pytest.mark.parametrize('name,last,picks,orders,successes', [
    ('aiallbuildon', [0, 4, 20, 598], 31, 307, 7),
    ('aiallbuildoff', [0, 1, 20, 459], 16, 156, 6),
])
def test_allbuild_native_named_observations(name, last, picks, orders, successes):
    """Anchor the actual nonempty construction observations and their limit.

    No balance/empty-candidate proxy, assumed enemy input, fitted model or
    wall-clock equality. Neither capture reaches the friendship timer.
    """
    import build
    import labpaths
    path = Path(labpaths.WORK) / 're/c_allbuild_measured.json'
    if not path.exists():
        pytest.skip('private original native construction archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[name]
    m, t, _ = build.resolve(name, 'a')
    assert [label for _, label in t.counters] == ['维和', '标枪', '次敌坦克', '逻辑帧']
    assert evidence['rows'][-1]['values'] == last
    assert len(evidence['picks']) == picks
    assert len(evidence['orders']) == orders
    assert all(order['picks'] for order in evidence['orders'])
    assert len(evidence['success']) == successes
    assert evidence['success'][:6] == [
        dict(frame=f, site='U', template=template)
        for f, template in [(301, 'AlliedScoutInfantry'), (333, 'AlliedScoutInfantry'),
                            (342, 'AlliedAntiVehicleInfantry'), (374, 'AlliedAntiVehicleInfantry'),
                            (428, 'AlliedAntiVehicleInfantry'), (460, 'AlliedAntiVehicleInfantry')]]
    assert all(row['values'][2] == 20 for row in evidence['rows'])
    assert evidence['max_log_frame'] < 70 * 15
    # These are the published native fields, not an inferred enemy selection.
    assert evidence['fields']['bpick'] == ['a', 'fac', 'flt', 'frame', 'obj', 'score', 'tmpl']
    assert evidence['fields']['border'] == ['a', 'fac', 'frame', 'obj', 'ok', 'picks', 'site', 'tmpl']


@pytest.mark.skipif(not simai.available(), reason='private AI model unavailable')
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'Native aiallbuildon f598 PK/Javelin/tanks=0/4/20; whole-game production '
    'differs and the action is unsupported. Native scoring enemy inputs are '
    'not published, so this mismatch is not attributed to that action. '
    'See work/re/c_allbuild_report.md and handoff-c.md.'))
def test_allbuild_on_named_production_replay():
    """Keep the actual production mismatch visible without fitting B's clock."""
    import build
    import sim
    m, t, _ = build.resolve('aiallbuildon', 'a')
    e = sim.Sim(m, t)
    w = simai.SimAI(e, lib=simai.model()['xmldata'].Library())
    got = {}
    tick = e.produce_due

    def observe(frame):
        tick(frame)
        if frame == 598:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.produce_due = observe
    w.advance(599)
    assert got == {598: [0, 4, 20, 598]}
