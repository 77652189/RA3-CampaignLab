"""experimental/cnv/playtest.py (ADR 0025): the playtest edition starts the release mod from its own copy of the game with
the dev keys on; the Steam folder and the mod are not touched. The keys themselves are checked in the game by
experimental/testbench/devkeys_check.py."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location('playtest', os.path.join(ROOT, 'experimental', 'cnv', 'playtest.py'))
playtest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(playtest)


def test_the_game_starts_from_the_copy_with_the_dev_keys_on():
    args, env = playtest.command(r'C:\copy', r'C:\mods\CampShell\CampShell_1.0.skudef', ['-win'])
    assert args[0] == os.path.join(r'C:\copy', 'Data', 'RA3_1.13.game')
    assert args[args.index('-modConfig') + 1].endswith('CampShell_1.0.skudef') and args[-1] == '-win'
    assert env['CNV_DEV_KEYS'] == '1' and env['CNV_SPEED'] == '1'          # the clocks hooked at x1: the keys can speed up
    assert env['CNV_SHOT_DIR'].startswith(r'C:\copy')


def test_the_copy_is_never_the_steam_folder():
    assert 'steamapps' not in playtest.COPY.lower()
    assert playtest.skudef('intl').endswith(os.path.join('CampShellEn', 'CampShellEn_1.0.skudef'))


def test_a_running_game_stops_it_before_anything(monkeypatch):
    monkeypatch.setattr(playtest, 'running', lambda: ['RA3_1.13.game'])
    monkeypatch.setattr(playtest, 'prepare', lambda: (_ for _ in ()).throw(AssertionError('prepared while running')))
    try:
        playtest.main([])
    except SystemExit as e:
        assert 'running' in str(e)
    else:
        raise AssertionError('no stop')
