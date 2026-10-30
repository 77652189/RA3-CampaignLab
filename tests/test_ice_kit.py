"""ice_kit.py on a clean machine: the Tripo props (gitignored downloads under work/) are reported missing and
skipped, not a FileNotFoundError that stops the kits rebuilt from retail (review 2026-10-26). A VARIANTS prop
(CNIceSculptHard) reads its base's bake."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'units'))
import ice_kit  # noqa: E402


def bake(model):
    return ice_kit.VARIANTS.get(model, (model,))[0]


def test_prop_without_its_tripo_bake_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(ice_kit.labpaths, 'WORK', str(tmp_path))
    for model in ice_kit.PROPS:
        names = [Path(p).name for p in ice_kit.missing(model)]
        assert names == [bake(model) + '.png', bake(model) + '_nrm.png', 'parts.json']


def test_prop_with_its_bake_is_not_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(ice_kit.labpaths, 'WORK', str(tmp_path))
    for model, unit in ice_kit.PROPS.items():
        game = tmp_path / 'units' / unit / 'game'
        game.mkdir(parents=True, exist_ok=True)
        for f in (bake(model) + '.png', bake(model) + '_nrm.png', 'parts.json'):
            (game / f).write_bytes(b'')
        assert ice_kit.missing(model) == []


def test_variant_reads_its_base_bake():
    assert ice_kit.VARIANTS['CNIceSculptHard'][0] == 'CNIceSculpt'
    assert ice_kit.PROPS['CNIceSculptHard'] == ice_kit.PROPS['CNIceSculpt']
