"""The test launcher (launcher.pyw) groups the built mods from the code's registry: a level's edition (a4_intl, the
international edition CampA4En) is a campaign level right behind the level as played, its check builds are check builds
labelled with the edition -- recognized for any level, not written out for A4."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))


def launcher():
    spec = importlib.util.spec_from_file_location('launcher_under_test', ROOT / 'launcher.pyw')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_an_edition_key_is_its_level_with_a_label():
    lau = launcher()
    levels = ('a4', 'j3', 's2')
    assert lau.edition_of('a4', levels) == ('a4', '')
    assert lau.edition_of('a4_intl', levels) == ('a4', '（国际版）')
    assert lau.edition_of('s2_intl', levels) == ('s2', '（国际版）')          # any level, not only A4
    assert lau.edition_of('a4_before', levels) == ('a4_before', '')            # not an edition
    assert lau.edition_of('probe_intl', levels) == ('probe_intl', '')          # an edition of something that is no level


def test_the_international_a4_is_a_level_next_to_a4_and_its_checks_are_labelled(monkeypatch):
    import build
    lau = launcher()
    keep = {k: (build.MISSIONS[k][0], {'idle': build.MISSIONS[k][1]['idle']}) for k in ('a4', 'a4_intl')}
    monkeypatch.setattr(build, 'MISSIONS', keep)
    got = lau.catalog()
    assert got['CampA4En'][0] == lau.LEVEL and got['CampA4En'][1] == got['CampA4'][1] + '（国际版）'
    assert got['CampA4En'][2] > got['CampA4'][2] and got['CampA4En'][2] - got['CampA4'][2] < 1   # right behind it
    assert got['CampA4Idle'][0] == got['CampA4EnIdle'][0] == lau.LEVEL_CHECK
    assert '（国际版）' in got['CampA4EnIdle'][1] and '（国际版）' not in got['CampA4Idle'][1]
