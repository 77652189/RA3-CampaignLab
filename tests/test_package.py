"""package.build_mod (ADR 0016): the one outlet of packaging pours a ModSpec into the make_campnew pipeline and puts the
pipeline's globals back afterwards, so two builds in one process do not carry into each other."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import package  # noqa: E402


def test_with_more_appends_tuples_and_merges_dicts():
    spec = package.ModSpec(name='CampX', extra_own=(b'a',), strings={'A': '1', 'B': '2'}, slot=None)
    more = package.with_more(spec, extra_own=[b'b'], strings={'B': '3', 'C': '4'}, slot={'slot': 4})
    assert more.extra_own == (b'a', b'b') and list(more.strings.items()) == [('A', '1'), ('B', '3'), ('C', '4')]
    assert more.slot == {'slot': 4} and spec.extra_own == (b'a',) and spec.strings == {'A': '1', 'B': '2'}


def test_two_builds_in_one_process_do_not_carry_over(tmp_path, monkeypatch):
    import importlib
    chain = [importlib.import_module(n) for n in package.CHAIN]
    c2, c3, c4, c6, c7, c18 = chain
    if not os.path.isdir(c2.SDK):
        pytest.skip('no SDK')
    seen = []
    monkeypatch.setattr(package, 'sdk_build_lock', lambda name: (lambda: None))

    def main():                                 # what the pipeline would build from, instead of building it
        seen.append((c2.NAME, c2.OUT, list(c7.EXTRA_OWN), list(c7.EXTRA_ALL), dict(c3.STRINGS), c2.SHELL,
                     list(c4.EXTRA_FILES), list(c2.EXTRA_STATIC)))
        os.makedirs(c4.OUT)
    monkeypatch.setattr(c4, 'main', main)
    before = {m: dict(vars(m)) for m in chain}
    own_before, strings_before = list(c7.EXTRA_OWN), dict(c3.STRINGS)
    spec = package.ModSpec(name='CampX', extra_own=(b'GameObject:X',), extra_all=('DATA:x.xml',),
                           strings={'NAME:X': 'x'}, slot={'slot': 4}, big_files=(('data\\x', b'x'),))
    for k in range(2):
        package.build_mod(spec, str(tmp_path / f'out{k}'))
    assert seen[0][2:] == seen[1][2:], 'the second build saw what the first one added'
    assert seen[0][0] == 'CampX' and seen[0][2][-1] == b'GameObject:X' and seen[0][5] == {'slot': 4}
    assert seen[0][4]['NAME:X'] == 'x' and ('data\\x', b'x') in seen[0][6]
    for m in chain:                             # every global back to the object it was, with its contents
        now = vars(m)
        assert set(now) == set(before[m]), m.__name__
        assert all(now[k] is v for k, v in before[m].items() if k != 'main'), m.__name__
    assert c7.EXTRA_OWN == own_before and c3.STRINGS == strings_before
