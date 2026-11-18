"""E192 named civilian near/far/deletion control replay."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('animal_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.parametrize('mission', ['engine_animal_e', 'engine_animalfire_e'])
def test_animal_named_bench(mission):
    import build
    from parts import contract, merged

    m, t, _ = build.resolve(mission, 'a')
    assert not contract(merged(m, t))
    on, off, far = [unit.xml for unit in m.units]
    assert re.sub(r'<AnimalAIUpdate\b[^>]*/>', '',
                  on.replace('CNVE192Near', 'CNVE192Off')) == off
    assert on.replace('CNVE192Near', 'CNVE192Far') == far
