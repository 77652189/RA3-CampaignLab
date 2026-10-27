"""ice_kit.py on a clean machine: the Tripo props (gitignored downloads under work/) are reported missing and
skipped, not a FileNotFoundError that stops the kits rebuilt from retail (review 2026-10-26)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'units'))
import ice_kit  # noqa: E402


def test_prop_without_its_tripo_bake_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(ice_kit.labpaths, 'WORK', str(tmp_path))
    for model in ice_kit.PROPS:
        names = [Path(p).name for p in ice_kit.missing(model)]
        assert names == [model + '.png', model + '_nrm.png', 'parts.json']


def test_prop_with_its_bake_is_not_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(ice_kit.labpaths, 'WORK', str(tmp_path))
    for model, unit in ice_kit.PROPS.items():
        game = tmp_path / 'units' / unit / 'game'
        game.mkdir(parents=True)
        for f in (model + '.png', model + '_nrm.png', 'parts.json'):
            (game / f).write_bytes(b'')
        assert ice_kit.missing(model) == []
