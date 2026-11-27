"""Read the generated tile records to check paint choices and locality."""
from dataclasses import replace
import struct

import numpy as np
import pytest

from experimental.mapgen import paint, terrain

import mapterrain
from test_mapgen_terrain import _container


def _rect(x0, y0, x1, y1):
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


@pytest.fixture
def sample(tmp_path, monkeypatch):
    monkeypatch.setattr(paint, 'ART', tmp_path)

    def entries(*names):
        (tmp_path / 'surface.tga').touch()
        return [dict(id=name, Texture='surface.tga', BumpTexture='surface.tga') for name in names]

    library = {'kits': {'Heidelberg_HB': {}, 'StPetersburg_ST': {}}, 'texture_kits': {
        'Heidelberg': {'Grass': entries('Grass_Heidelberg01'), 'Road': entries('Stone', 'Cobble', 'Paver')},
        'Saint_Petersburg': {'Road': entries('Asphalt')},
        'Gibraltar': {'Cliff': entries('GibraltarRock')},
        'Cape_Cod': {'Cliff': entries('CapeRock')},
    }}
    plan = terrain.TerrainPlan(blocks=(
        terrain.Block(_rect(0, 0, 300, 300), 3, surface=terrain.Surface('town', 'oldtown', 'Heidelberg_HB', 7)),
        terrain.Block(_rect(310, 0, 600, 300), 3,
                      surface=terrain.Surface('plaza', 'square', 'Heidelberg_HB', 19)),
    ))
    return plan, library


def _build(plan, library):
    size = 61, 61, 0
    ground = paint.paint(plan, library, terrain.expand(plan, library, *size))
    m = _container(*size)
    terrain.apply(m, plan, ground)
    return m, ground


def test_kit_lookup_and_cliff_class(sample):
    plan, library = sample
    town, plaza = plan.blocks
    library['kits']['Heidelberg_HB']['cliffs'] = [
        dict(template='HB_CliffWall01', height_steps=1, length=100, offset_y=-15, samples=1)]
    plan = replace(plan, blocks=(replace(town, height=4),
                                 replace(plaza, surface=replace(plaza.surface, kit='StPetersburg_ST'))),
                   cliffs=(terrain.Cliff((300, 0), (300, 300), 'Heidelberg_HB'),))
    # Directed north, high side west. The terrain writer hides the covered low-side cell.
    m, ground = _build(plan, library)
    tiles = mapterrain.Tiles(m, 61)
    assert tiles.texture_at(50, 15) == 'Asphalt'
    assert ground.blocked[15, 30] and ground.hidden[15, 31]
    assert tiles.texture_at(30, 15) == 'GibraltarRock'
    assert tiles.texture_at(31, 15) == 'CapeRock'
    vis = 4 * tiles.row_bytes * tiles.height + 15 * tiles.row_bytes
    assert tiles.extra[vis + 30 // 8] & (1 << (30 % 8))
    assert not tiles.extra[vis + 31 // 8] & (1 << (31 % 8))


@pytest.mark.parametrize('missing', ['texture', 'kit'])
def test_missing_material_names_the_block(sample, missing):
    plan, library = sample
    if missing == 'texture':
        for asset in library['texture_kits']['Heidelberg']['Road']:
            asset['Texture'] = 'missing.tga'
    else:
        del library['kits']['Heidelberg_HB']
    with pytest.raises(ValueError, match=rf'block town: missing {missing}'):
        _build(plan, library)


def test_same_plan_same_map_bytes_and_local_kit_swap(sample):
    plan, library = sample
    first, ground = _build(plan, library)
    again, _ = _build(plan, library)
    assert first.map_file() == again.map_file()
    assert first.editor_file() == again.editor_file()
    town, plaza = plan.blocks
    swap = replace(town, surface=replace(town.surface, kit='StPetersburg_ST'))
    changed, _ = _build(replace(plan, blocks=(swap, plaza)), library)
    a, b = (mapterrain.Tiles(m, 61) for m in (first, changed))
    assert any(a.arrays[1]) and not any(a.arrays[2]) and not any(b.arrays[2])

    def material(tiles, i, j):
        index = tiles.arrays[1][j * tiles.width + i]
        desc = tiles.descs[index - 1] if index else b''
        overlay = None
        if desc:
            cell = struct.unpack_from('<I', desc)[0] // 4
            overlay = next(n for n, (start, count, _) in tiles.textures.items() if start <= cell < start + count)
        return tiles.texture_at(i, j), overlay, desc[4:10]

    assert material(a, 31, 15)[1] == 'Grass_Heidelberg01'
    assert b.texture_at(20, 15) == 'Asphalt'
    for j, i in zip(*np.nonzero(ground.owners != 0)):
        assert material(a, i, j) == material(b, i, j)
