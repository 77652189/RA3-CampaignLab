"""Read the generated tile records to check paint choices and locality."""
from dataclasses import replace
import struct

import numpy as np
import pytest

from experimental.mapgen import paint, terrain
from experimental.mapgen.roads import Roadbed

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
    }, 'styles': {
        '*': {'places': {'texture_donors': {'Cliff': 'Cape_Cod'}}},
        'Heidelberg': {'places': {'texture_donors': {'Cliff': 'Gibraltar'}}},
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


def test_named_snow_skips_its_unused_palette(sample):
    plan, library = sample
    town, = plan.blocks[:1]
    library['texture_kits']['Iceland'] = {'Snow': [
        dict(id='Snow_Iceland03', Texture='surface.tga', BumpTexture='surface.tga')]}
    surface = replace(town.surface, use='snow', ground_texture='Snow_Iceland03')
    _, ground = _build(replace(plan, blocks=(replace(town, surface=surface),)), library)
    assert ground.textures[15, 15] == 'Snow_Iceland03'


def test_named_ramp_shoulder_skips_its_unused_palette(sample):
    plan, library = sample
    town, = plan.blocks[:1]
    tile = dict(Texture='surface.tga', BumpTexture='surface.tga')
    library['texture_kits']['Heidelberg'] = {
        kind: [dict(tile, id=name)] for kind, name in
        [('Snow', 'Snow_Iceland03'), ('Dirt', 'Dirt_Test'), ('Cliff', 'Cliff_Test')]}
    surface = replace(town.surface, use='park', ground_texture='Snow_Iceland03')
    plan = replace(plan, ground='Snow_Iceland03', blocks=(
        terrain.Block(_rect(0, 0, 600, 300), 3, surface=surface),
        terrain.Block(_rect(0, 310, 600, 600), 4, surface=replace(surface, id='high')),
    ), ramps=(terrain.Ramp((300, 210), (0, 1), 1, 180),))
    _, ground = _build(plan, library)
    assert ground.ramp_edges[30, 40] and ground.textures[30, 40] == 'Snow_Iceland03'


def test_writer_blends_final_dressed_material(sample, monkeypatch):
    plan, library = sample
    size = 61, 61, 0
    ground = terrain.expand(plan, library, *size)
    paved = np.zeros_like(ground.blocked)
    paved[40, 40] = True
    roadbed = Roadbed('StPetersburg_ST', (), (), paved, np.zeros_like(paved), np.zeros_like(paved), paved)
    ground = paint.paint(plan, library, ground, roadbed)
    updated = ground.textures.copy()
    updated[15, 30] = 'Asphalt'
    original = terrain.newmap.paint_grid

    def capture(tiles, materials, rank, edge):
        assert edge(30, 15, 31, 15, materials[31, 15]) == materials[31, 15]
        return original(tiles, materials, rank, edge)

    monkeypatch.setattr(terrain.newmap, 'paint_grid', capture)
    terrain.apply(_container(*size), plan, replace(ground, textures=updated))


def test_ramp_infill_recolors_only_the_visible_road_gap(sample):
    plan, library = sample
    kit = library['styles']['Heidelberg']
    kit['edges'] = {'road_surface': {'base': 'Stone', 'infill': 'Cobble', 'ramp_infill': 'Paver'}}
    library['texture_kits']['Heidelberg']['Dirt'] = [
        dict(id='Dirt_Test', Texture='surface.tga', BumpTexture='surface.tga')]
    ground = terrain.expand(plan, library, 61, 61, 0)
    ground.ramp[15, 11:14] = True
    paved = np.zeros_like(ground.ramp)
    paved[15, 10:14] = True
    infill = paved.copy()
    infill[15, 13] = False
    hidden = np.zeros_like(paved)
    hidden[15, 12] = True
    roadbed = Roadbed('Heidelberg_HB', (), (), paved, hidden, infill, paved)
    result = paint.paint(plan, library, ground, roadbed)
    assert list(result.textures[15, 10:14]) == ['Cobble', 'Paver', 'Cobble', 'Stone']
    assert np.array_equal(result.hidden, hidden)
