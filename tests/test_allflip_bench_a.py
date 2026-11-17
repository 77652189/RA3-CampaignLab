"""A274: the AI's building enemies follow the relation as it changes; the all-enemies action shows nothing on top.

Native readings of missions/aiallflip_bench.py (checks/engine_aiflip.py), saved in the private
work/re/a274_flip_measured.json (raw runs named there). s5 (twenty tanks) is s1's friend at the start; the pick
scores read the enemy set: 1666.836 while only p1 (ten conscripts) counts, 1666.833 once s5 does.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('allflip_simbench', ROOT / 'experimental/cnv/simbench.py')
_spec.loader.exec_module(importlib.util.module_from_spec(_spec))     # puts experimental/cnv on the path
NAMES = ['aiallflipon', 'aiallflipoff', 'aiallfliplate', 'aiallflipnever', 'aiallflipwoff', 'aiallflipwon']
SCOUT, JAV, PK = 'ddfc28de', '9c5d3bb8', '139cbc97'     # the ra3ext template tokens (C's run: 301 scout, 342 jav)
WITH_S5, WITHOUT_S5 = 1666.833, 1666.836


@pytest.mark.parametrize('name', NAMES)
def test_allflip_named_contract(name):
    import build
    import parts
    m, t, _ = build.resolve(name, 'a')
    assert parts.contract(parts.merged(m, t)) == [], name


def _evidence():
    import labpaths
    path = Path(labpaths.WORK) / 're/a274_flip_measured.json'
    if not path.exists():
        pytest.skip('private native construction archive unavailable')
    return json.loads(path.read_text(encoding='utf-8'))


def _scouts(run, lo, hi):
    return {score for frame, tmpl, score in run['picks'] if tmpl == SCOUT and lo <= frame <= hi}


def test_a_relation_change_reaches_the_building_enemies_without_the_action():
    """on / off / late (s5 turns enemy at 5 s, before the 10 s wake) build alike, never (s5 a friend) apart."""
    e = _evidence()
    common = min(e[n]['max_log_frame'] for n in ('aiallflipon', 'aiallflipoff', 'aiallfliplate'))
    alike = [[p for p in e[n]['picks'] if p[0] <= common] for n in ('aiallflipon', 'aiallflipoff', 'aiallfliplate')]
    assert alike[0] == alike[1] == alike[2]
    assert [o[2] for o in e['aiallflipoff']['success'][:6]] == [SCOUT, SCOUT, JAV, JAV, JAV, JAV]
    assert [o[2] for o in e['aiallflipnever']['success'][:4]] == [SCOUT, SCOUT, PK, PK]
    assert _scouts(e['aiallflipoff'], 152, 340) == {WITH_S5}
    assert _scouts(e['aiallflipnever'], 152, 340) == {WITHOUT_S5}


def test_a_change_after_the_wake_counts_from_the_next_pass():
    """woff: s5 turns enemy at 15 s (f225), no action -- the picks switch at the first pass after it (f229).
    won (the action at 20 s on top) picks the same."""
    e = _evidence()
    woff = e['aiallflipwoff']
    assert _scouts(woff, 152, 225) == {WITHOUT_S5}
    assert _scouts(woff, 226, 340) == {WITH_S5}
    assert [o[2] for o in woff['success'][:6]] == [SCOUT, SCOUT, JAV, JAV, JAV, JAV]
    end = e['aiallflipwon']['max_log_frame']
    assert e['aiallflipwon']['picks'] == [p for p in woff['picks'] if p[0] <= end]
