"""E199 named discovery-clock replays; raw evidence in work/re/e199_vision_clock.md."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_infclock', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_clock_probe_contract():
    import build
    name = 'engine_inffoot'
    m, t, mod = build.resolve(name, 'c')
    assert len(mod) <= 15 and '_' not in mod
    assert build.show(name, 'c').endswith('contract: ok')
    samples = [s for s in t.scripts if s.name.startswith('Clock sample ')]
    assert len(samples) == 300
    assert [s.when[0][3] for s in samples] == list(range(1, 301))
    assert len(t.counters) == 4
    assert m.role('match').side == m.role('enemy').side


def test_clock_dual_probe_contract():
    import build
    m, t, mod = build.resolve('engine_infclock', 'a')
    assert len(mod) <= 15 and '_' not in mod
    assert build.show('engine_infclock', 'a').endswith('contract: ok')
    for lane in ('air', 'vehicle'):
        assert m.role(lane).side == m.role(lane + ' match').side
        assert len([s for s in t.scripts if s.name.startswith('Dual ' + lane + ' sample ')]) == 300
    assert len(t.counters) == 4


def test_clock_infantry_sequence_as_on_the_bench():
    """engine_inffoot:c: all twenty immutable pages read 31710 (300 samples)."""
    import build
    import sim
    m, t, _ = build.resolve('engine_inffoot', 'c')
    s = sim.Sim(m, t).run(80)
    host = s.infiltrators.module(s.body(m.role('enemy').name))
    assert s.infiltrators.unit_observers, host.rules() if host is not None else 'enemy host has no InfiltratorContain'
    assert [s.counters.get(f'Clock page {page}', 0) for page in range(20)] == [31710] * 20
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive


def test_clock_aircraft_vehicle_sequences_as_on_the_bench():
    """engine_infclock:a: both complete 300-pass streams are twenty 31710 pages."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infclock', 'a')
    s = sim.Sim(m, t).run(90)
    for lane in ('air', 'vehicle'):
        assert [s.counters.get(f'Dual {lane} page {page}', 0) for page in range(20)] == [31710] * 20
        assert not s.body(m.role(lane + ' spy').name).alive
        assert s.body(m.role(lane + ' match').name).alive
