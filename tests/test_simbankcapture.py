"""E147: replay neutral bank capture by name against frame-latched wallets."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bankcapture_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_bankcapture_named_wallet_samples():
    import build
    import sim
    m, t, _ = build.resolve('engine_bankcapture', 'a')
    # Actual bench: 750/0 at observed f188; 770/0 and all ten evidence bits
    # at f257, stable afterwards. Evidence includes the four 15-frame samples,
    # so capture-index drift cannot turn a wrong income period into a pass.
    t.expect = [('收入', 22, '==', 770, 28), ('对照', 2, '==', 0, 28),
                ('证据', 22, '==', 1023, 28)]
    engine = sim.Sim(m, t).run(29)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
