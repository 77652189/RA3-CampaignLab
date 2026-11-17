"""E151: the direct capture-power probe, separated from engineer entry."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('capturespecial_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_capture_special_probe_controls():
    import build
    from parts import contract, merged
    m, t, _ = build.resolve('engine_capture', 'a')
    assert not contract(merged(m, t))
    assert {m.role(tag + ' flag').template for tag in ('neutral', 'enemy', 'own', 'off')} == {'CaptureFlag'}
    off = next(u.xml for u in m.units if u.id == 'CNVE151Off')
    assert 'CaptureSpecialAbilityUpdate' not in off
    assert 'SpecialPowerTemplate="SpecialPowerCaptureControlPoint"' in off
    casts = [a for s in t.scripts for a in s.do
             if a[0] == 'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED']
    assert len(casts) == 4
    assert all(a[2] == 'Command_CaptureBuilding' for a in casts)
    assert not any('TRANSFER' in a[0] for s in t.scripts for a in s.do)


def test_capture_special_named_negative_baseline():
    """Replay only the measured failed-input baseline, not capture capability."""
    import build
    import sim
    m, t, _ = build.resolve('engine_capture', 'a')
    # Keep the positive bench prediction in the check; this test separately
    # replays actual E151 observations. No BENCHED registration is warranted.
    assert t.expect[1] == ('归属', 28, '==', 111, 35)
    t.expect = [('前置', 2, '==', 1, 35), ('归属', 28, '==', 100, 35),
                ('存活', 28, '==', 1111, 35)]
    engine = sim.Sim(m, t).run(36)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts

