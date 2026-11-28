"""E200 independent ship configuration and named bench replays."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_infship', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_ship_configuration():
    import build
    import engine.objects.infiltrator as siminfiltrator
    import engine.data.units as simunits
    import re
    m, t, mod = build.resolve('engine_infship', 'a')
    assert len(mod) <= 15 and '_' not in mod
    assert 'contract: ok' in build.show('engine_infship', 'a').lower()
    rule = siminfiltrator.spec(m.role('enemy').template)
    assert {k: v for k, v in rule.items() if k not in ('xmlns', 'id')} == {
        'Effect': 'VISION_UNITS', 'Duration': '30s', 'UnitDuration': '30s',
        'ObjectRef': 'UnitVisionObserver', 'UnitFilter': 'InfiltrationShipObjectFilter',
        'StructureFilter': 'InfiltrationShipStructuresFilter'}
    points = [m.site(m.role(role).site) for role in ('match', 'wrong', 'third')]
    assert all((a[0]-b[0])**2+(a[1]-b[1])**2 >= 900**2
               for i, a in enumerate(points) for b in points[i+1:])
    for role in ('match', 'third'):
        xml = simunits.retail_xml(m.role(role).template)
        assert 'SHIP' in re.search(r'KindOf="([^"]+)"', xml).group(1).split()
    assert len(t.counters) == 4
    assert [item[3] for item in t.expect] == [11100, 1100, 11100, 0, 1, 511]


def test_ship_clock_probe_contract():
    import build
    m, t, mod = build.resolve('engine_infship', 'c')
    assert len(mod) <= 15 and '_' not in mod
    assert build.show('engine_infship', 'c').endswith('contract: ok')
    samples = [s for s in t.scripts if s.name.startswith('Clock sample ')]
    assert len(samples) == 300
    assert [s.when[0][3] for s in samples] == list(range(1, 301))
    assert len(t.counters) == 4
    assert m.role('match').side == m.role('enemy').side


def test_ship_entry_as_on_the_bench():
    """Only consume the enemy spy; leave friendly spy and both full-HP owners."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infship', 'a')
    s = sim.Sim(m, t).run(35)
    for start, end, expected in ((1, 7, [11100, 11100]), (20, 35, [1100, 11100])):
        rows = [values[:2] for second, values in s.series if start <= second <= end]
        assert rows and all(row == expected for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's3'), ('ally', 's5')):
        host = s.body(m.role(role).name)
        assert host.owner == m.player(side) and host.hp == host.max_hp
    assert not s.infiltrators.observers



def test_ship_marker_identity_as_on_the_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_infship', 'a')
    s = sim.Sim(m, t).run(41)
    assert s.series and all(values[3] == 511 for _, values in s.series)


def test_ship_wrong_kind_and_third_owner_as_on_the_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_infship', 'a')
    s = sim.Sim(m, t).run(41)
    assert s.series and all(values[2] in (0, 1) for _, values in s.series)


@pytest.mark.xfail(strict=True, reason='E200 a墙钟匹配舰船1/0间歇，逐帧调度另验；见 work/re/e200_ship.md')
def test_ship_discovery_wall_clock_as_on_the_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_infship', 'a')
    s = sim.Sim(m, t).run(41)
    for second, expected in ((11, 1), (18, 0), (19, 1), (20, 0), (21, 1),
                              (22, 0), (24, 1), (25, 0), (26, 1), (27, 0),
                              (28, 1), (29, 0), (30, 1), (41, 1)):
        rows = [values[2] for tick, values in s.series if tick == second]
        assert rows == [expected], (second, rows)


def test_ship_clock_sequence_as_on_the_bench():
    """engine_infship:c: entry 182, twenty pages each 31710, all 300 samples."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infship', 'c')
    s = sim.Sim(m, t).run(80)
    assert s.infiltrators.unit_observers
    assert [s.counters.get(f'Clock page {page}', 0) for page in range(20)] == [31710] * 20
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
