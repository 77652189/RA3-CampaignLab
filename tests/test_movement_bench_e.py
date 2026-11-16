"""E171 named retail rush control; observations are documented in work/re/e171_movement.md."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('movement_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_movement_rush_control_contract():
    import build
    from parts import contract, merged
    m, t, _ = build.resolve('engine_movement_e', 'a')
    on, off = [u.xml for u in m.units]
    assert re.sub(r'<MovementSpecialPower\b[^>]*/>', '', on.replace('CNVE171On', 'CNVE171Off')) == off
    assert not contract(merged(m, t))


def test_movement_rush_named_bench_readings():
    import build
    import sim
    from parts import Script
    m, t, _ = build.resolve('engine_movement_e', 'a')
    # Real HUD: f59 0/0/0, f73 1/0/0 for the three observation counters.
    for frame, active in [(59, 0), (73, 1)]:
        t.scripts.append(Script('Test - E171 snapshot ' + str(frame), [
            ('COUNTER', 'E171Frame', 2, frame), ('COUNTER', 'E171Active', 2, active),
            ('COUNTER', 'E171Moved', 2, 0), ('COUNTER', 'E171Clear', 2, 0)],
            [('SET_COUNTER', 'E171Match' + str(frame), 1)]))
    engine = sim.Sim(m, t).run(18)
    # CampMovementEA_mcp_1116_002328: frozen same-frame HUD values.
    assert [engine.eng.value(c) for c in ('E171Frame', 'E171Active', 'E171Moved', 'E171Clear')] == [210, 1, 1, 11]
    assert engine.eng.value('E171Match59') == engine.eng.value('E171Match73') == 1
