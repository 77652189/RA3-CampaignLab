"""E192 named civilian near/far/deletion control replay."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('animal_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.parametrize('mission,counter,expected', [
    ('engine_animal_e', 'E192Frame', 240),
    ('engine_animal_e', 'E192Left', 0),
    ('engine_animal_e', 'E192Live', 7),
    ('engine_animal_e', 'E192Start', 7),
    ('engine_animalfire_e', 'E192Frame', 240),
    ('engine_animalfire_e', 'E192Left', 0),
    pytest.param('engine_animalfire_e', 'E192Live', 7, marks=pytest.mark.xfail(
        strict=True, reason='E192: Sim accepts firing (gate63), bench gate7 has no legal hits; see work/re/e192_animal.md')),
    ('engine_animalfire_e', 'E192Start', 7),
])
def test_animal_named_bench(mission, counter, expected):
    import build
    import sim
    from parts import contract, merged

    m, t, _ = build.resolve(mission, 'a')
    assert not contract(merged(m, t))
    on, off, far = [unit.xml for unit in m.units]
    assert re.sub(r'<AnimalAIUpdate\b[^>]*/>', '',
                  on.replace('CNVE192Near', 'CNVE192Off')) == off
    assert on.replace('CNVE192Near', 'CNVE192Far') == far
    engine = sim.Sim(m, t).run(20)
    assert engine.eng.value(counter) == expected
