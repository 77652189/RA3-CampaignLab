"""Terrain expansion and the two map wrappers on a small generated container."""
from dataclasses import replace
import struct

import numpy as np

from experimental.campaign.mapscript import MapFile
from experimental.mapgen.terrain import Block, Cliff, Ramp, TerrainPlan, Water, apply, expand
from experimental.mappage import sketch2map

import mapterrain
from ra3voice import refpack
import terrain_rules


def test_mapgen_terrain_geometry_and_both_files(tmp_path, monkeypatch):
    size = (101, 101, 0)
    library = {'kits': {'HB': {'cliffs': [
        {'template': 'HB_CliffWall01', 'height_steps': 1, 'length': 99, 'offset_y': -13, 'samples': 20}
    ]}}}
    plan = TerrainPlan(
        blocks=(Block(((0, 500), (1000, 500), (1000, 1000), (0, 1000)), 4),),
        cliffs=(Cliff((0, 500), (1000, 500), 'HB'),),
        ramps=(Ramp((500, 410), (0, 1), 1, 180),),
        water=(Water(((0, 0), (1000, 0), (1000, 400), (0, 400)), 200),),
    )
    ground = expand(plan, library, *size)
    assert ground.raw.dtype == np.uint16
    assert (ground.raw[40, 10], ground.raw[60, 10]) == (3 * 1792, 4 * 1792)
    assert (ground.raw[41, 50], ground.raw[59, 50]) == (3 * 1792, 4 * 1792)
    assert max(terrain_rules.slope(ground.raw / 16)[41:60, 50]) == 6.25
    assert ground.blocked[49, 10] and not ground.blocked[49, 50]
    assert len(ground.issues) == 1 and ground.issues[0].startswith('ramp sides:')
    assert [(p.template, p.x, p.y, p.angle) for p in ground.pieces] == [
        ('HB_CliffWall01', x, 515, 0) for x in (50, 150, 250, 350, 650, 750, 850, 950)]
    assert ground.raw[20, 20] == 130 * 25.6
    assert max(terrain_rules.slope(ground.raw / 16)[0:41, 20]) <= 6.5

    grid_kit = {'cliffs': [{'template': 'Sample_GRID', 'height_steps': 1, 'length': 119,
                            'offset_y': -28, 'samples': 19}],
                'props': [{'template': 'Sample_GRID', 'editor_name': 'SampleStraight'}]}
    grid_plan = replace(plan, blocks=(Block(((0, 510), (1000, 510), (1000, 1000), (0, 1000)), 4),),
                        cliffs=(Cliff((0, 510), (960, 510), 'Grid'),), ramps=(), water=())
    grid = expand(grid_plan, {'kits': {'Grid': grid_kit}}, 97, 101, 0)
    assert not grid.issues
    assert [(p.x, p.y) for p in grid.pieces] == [(x, 540) for x in range(60, 960, 120)]

    def build(_):
        m = _container(*size)
        apply(m, plan, expand(plan, library, *size))
        return m

    monkeypatch.setattr(sketch2map, 'build_map', build)
    game, editor = tmp_path / 'game.map', tmp_path / 'editor.map'
    mission = sketch2map.parts.Mission(name='Terrain', map=None)
    sketch2map.write_map_pair(mission, game, editor)
    first = game.read_bytes(), editor.read_bytes()
    sketch2map.write_map_pair(mission, game, editor)
    assert (game.read_bytes(), editor.read_bytes()) == first
    assert refpack.decompress(first[0])[:4] == b'EAR\0'
    assert first[1][:4] == b'EAR\0'
    game, editor = (MapFile(raw) for raw in first)
    assert [editor._write(n) for n in editor.nodes if n.name != 'GlobalVersion'] == [game._write(n) for n in game.nodes]
    gv = editor.nodes[0]
    assert (gv.name, gv.ver, gv.head) == ('GlobalVersion', 1, b'')
    np.testing.assert_array_equal(mapterrain.HeightMap(game).elev, ground.raw.ravel())
    tiles = mapterrain.Tiles(editor, size[0])
    assert tiles.extra[49 * tiles.row_bytes + 10 // 8] & 1 << (10 % 8)
    assert not tiles.extra[49 * tiles.row_bytes + 50 // 8] & 1 << (50 % 8)
    assert struct.unpack('<If', next(n.head for n in game.nodes if n.name == 'GlobalWaterSettings')) == (1, 200)
    standing = next(n.head for n in game.nodes if n.name == 'StandingWaterAreas')
    assert struct.unpack_from('<I8fI', standing, 21) == (4, 0., 0., 1000., 0., 1000., 400., 0., 400., 200)


def _container(w, h, border):
    # Minimal independent input for the existing v6 height and v27 tile readers.
    cells = w * h
    height = struct.pack('<5I', w, h, border, 0, cells) + bytes(2 * cells)
    name = b'Grass_Heidelberg01'
    tiles = (struct.pack('<I', cells) + bytes(9 * cells + 8 * h * ((w + 7) // 8))
             + struct.pack('<8IH', 16, 1, 1, 1, 0, 16, 4, 0, len(name)) + name + bytes(8))
    water = struct.pack('<II', 1, 1) + bytes(13) + struct.pack('<II', 0, 200)
    chunks = (('HeightMapData', 6, height), ('BlendTileData', 27, tiles),
              ('StandingWaterAreas', 2, water), ('GlobalWaterSettings', 1, bytes(8)),
              ('RiverAreas', 3, bytes(4)), ('StandingWaveAreas', 4, bytes(4)))
    names = b''.join(struct.pack('<B', len(n)) + n.encode() + struct.pack('<I', i)
                     for i, (n, _, _) in enumerate(chunks, 1))
    body = b''.join(struct.pack('<IHI', i, v, len(b)) + b for i, (_, v, b) in enumerate(chunks, 1))
    return MapFile(b'CkMp' + struct.pack('<I', len(chunks)) + names + body)
