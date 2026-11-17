"""E183 refinery exclusion: compare only the native module and replay HUD facts."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('structureplace_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_structureplace_only_reserved_shape_is_removed():
    import build
    on, ton, _ = build.resolve('structpon', 'a')
    off, toff, _ = build.resolve('structpoff', 'a')
    from checks.engine_structureplace_e import INCLUDE
    assert re.subn(INCLUDE, '', on.units[0].xml) == (off.units[0].xml, 1)
    assert on.units[1] == off.units[1]
    assert on.objects == off.objects
    assert ton.bench == toff.bench
    assert build.steps('CampSpOnA', ton)[0][1]['hold'] is False

@pytest.mark.parametrize('name', ['structpon', 'structpoff'])
def test_structureplace_named_no_accepted_plant(name):
    import build
    import sim
    m, t, _ = build.resolve(name, 'a')
    # Both actual runs contain zero plants throughout. This negative baseline
    # does not validate the original module-effect prediction in check().
    t.expect = [('电厂总数', 0, '==', 0), ('前方电厂', 0, '==', 0)]
    engine = sim.Sim(m, t).run(20)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
