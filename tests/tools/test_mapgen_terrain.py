"""Terrain expansion and the two map wrappers on a small generated container."""
from dataclasses import replace
import json
import struct

import numpy as np

from experimental.campaign.mapscript import MapFile
from experimental.mapgen.design import Design
from experimental.mapgen.terrain import Block, Cliff, Ramp, Surface, TerrainPlan, Water, apply, expand, from_design
from experimental.mapgen.build import build
from experimental.mapgen import paint
from experimental.mappage import sketch2map

import mapterrain
import mapxml
from mapscript import Node
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


def test_exposed_ramp_verge_is_grass_without_opening_the_steep_side(tmp_path, monkeypatch):
    monkeypatch.setattr(paint, 'ART', tmp_path)
    (tmp_path / 'surface').touch()

    def tiles(name):
        return [dict(id=name, Texture='surface', BumpTexture='surface')]

    kit = 'Heidelberg_HB'
    library = {'kits': {kit: {}}, 'texture_kits': {
        'Heidelberg': {'Grass': tiles('Grass_Heidelberg01'), 'Dirt': tiles('Dirt_Heidelberg01')},
        'Gibraltar': {'Cliff': tiles('Cliff_Gibraltar1')},
    }}
    plan = TerrainPlan(
        blocks=(Block(((0, 500), (1000, 500), (1000, 1000), (0, 1000)), 4,
                      surface=Surface('top', 'park', kit)),),
        ramps=(Ramp((500, 410), (0, 1), 1, 180),),
    )
    ground = expand(plan, library, 101, 101, 0)
    dressed = paint.paint(plan, library, ground)
    # The one-cell shoulder ends at x400. The drop still blocks at x390.
    assert ground.blocked[47, 39] and not ground.blocked[47, 50]
    assert dressed.blocked is ground.blocked and dressed.raw is ground.raw
    assert dressed.textures[47, 39] == 'Grass_Heidelberg01'
    assert dressed.textures[47, 50] == 'Dirt_Heidelberg01'
    assert dressed.textures[49, 20] == 'Cliff_Gibraltar1'


def test_straight_cliff_continues_across_a_face_split():
    sketch = Design({
        'version': 2,
        'blocks': {
            'low': {'at': [200, 200], 'height': 3, 'use': 'park'},
            'highWest': {'at': [200, 500], 'height': 4, 'use': 'park'},
            'highEast': {'at': [600, 500], 'height': 4, 'use': 'park'},
        },
        'borders': {
            'frame': {'line': [[0, 0], [800, 0], [800, 800], [0, 800], [0, 0]]},
            'cliff': {'line': [[0, 400], [800, 400]], 'closed_reason': 'scarp'},
            'edge': {'line': [[430, 400], [430, 800]]},
        },
    })
    # A boundary between two same-height high blocks cuts the sketch's line
    # at x430. The 100-unit wall modules still fit the full 800-unit run.
    assert from_design(sketch, TerrainPlan(), 'HB').cliffs == (Cliff((0, 400), (800, 400), 'HB'),)


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

def test_quay_connects_the_deck_to_deep_water_with_a_closed_lip():
    kit = 'StPetersburg_ST'
    template = 'ST_SeaWallPiece01'
    sketch = Design({
        'version': 2,
        'blocks': {
            'yard': {'height': 3, 'use': 'dock', 'at': [200, 430], 'kit': kit},
            'basin': {'height': 3, 'use': 'water', 'kind': 'water', 'at': [200, 200]},
        },
        'borders': {
            'frame': {'line': [[0, 0], [400, 0], [400, 500], [0, 500], [0, 0]]},
            'edge': {'line': [[400, 300], [0, 300]], 'shore': 'quay'},
        },
    })
    assert not sketch.reachable('basin', 'yard', 'amphibian')
    plan = from_design(sketch, TerrainPlan(), 'other_kit')
    ground = expand(plan, {'kits': {kit: {'props': [{'template': template}]}}}, 41, 51, 0)
    # The 100-unit retail model meets the next piece end to end, facing the water.
    assert [(p.template, p.x, p.y, p.angle) for p in ground.pieces] == [
        (template, x, 307, 0) for x in (50, 150, 250, 350)]
    # The sea bed reaches the wall. The first dry row holds any beaching unit.
    assert ground.raw[29, 20] == 130 * terrain_rules.RAW_PER_WORLD
    assert not ground.blocked[29, 20] and ground.blocked[31, 20]
    assert ground.blocked[32, 20] and not ground.blocked[33, 20]
    m = _container(41, 51, 0)
    apply(m, plan, ground)
    tiles = mapterrain.Tiles(m, 41)
    assert tiles.extra[31 * tiles.row_bytes + 20 // 8] & 1 << (20 % 8)

def test_named_atmosphere_reaches_both_mapgen_outputs_and_saves_review(tmp_path, monkeypatch):
    size = (61, 61, 0)
    monkeypatch.setattr('experimental.mapgen.build.CONTAINER', size)
    monkeypatch.setattr(paint, 'ART', tmp_path)
    (tmp_path / 'surface.tga').touch()
    kit = 'Heidelberg_HB'
    asset = {'id': 'Grass_Heidelberg01', 'Texture': 'surface.tga', 'BumpTexture': 'surface.tga'}
    donor = {'GlobalLighting': (11, b'\x03\0\0\0' + bytes(448)), 'FogSettings': (1, b'donor fog'),
             'EnvironmentData': (5, b'donor environment'), 'PostEffectsChunk': (2, b'donor effects')}
    chunks = {name: (ver, raw.hex()) for name, (ver, raw) in donor.items()}
    kit_assets = dict(buildings=[], destructibles=[], props=[])
    moods = {
        'other_town': {'name': '另一座城', 'time_of_day': 1, 'time_label': 'MORNING',
                       'atmosphere': {'chunks': chunks | {'GlobalLighting': (11, bytes(452).hex())},
                                      'weather': (1, 0)}},
        'retail_town': {'name': '旧城斜阳', 'time_of_day': 3, 'time_label': 'EVENING',
                        'atmosphere': {'chunks': chunks, 'weather': (1, 5)}},
    }
    library = {'kits': {kit: kit_assets}, 'blocking': {}, 'texture_kits': {'Heidelberg': {'Grass': [asset]}},
               'retail_moods': moods}
    sketch = {'version': 2, 'commitments': {'mood': '旧城斜阳'},
              'blocks': {'town': {'at': [200, 200], 'height': 3, 'use': 'park'}},
              'borders': {'rim': {'line': [[0, 0], [600, 0], [600, 600], [0, 600], [0, 0]]}},
              'points': {'start': {'at': [90, 90], 'block': 'town'}},
              'relations': {'space': {'type': '放得下', 'point': 'start', 'side': 50},
                            'oversize': {'type': '放得下', 'point': 'start', 'side': 300}}}
    design_file, library_file, container = (tmp_path / name for name in ('design.json', 'library.json', 'base.map'))
    design_file.write_text(json.dumps(sketch), encoding='utf-8')
    library_file.write_text(json.dumps(library), encoding='utf-8')

    base = _container(*size)
    world = mapxml.encode_props(base, {'cameraMaxHeight': (2, 450.), 'weather': (1, 0)})
    for name, ver, raw in [('ObjectsList', 3, b''), ('WorldInfo', 1, world),
                           *((name, ver, b'container') for name, (ver, _) in donor.items())]:
        base.name_id(name)
        base.nodes.append(Node(name, ver, raw, []))
    for name in ('PlayerScriptsList', 'ScriptList', 'Script', 'OrCondition', 'Condition', 'ScriptAction'):
        base.name_id(name)
    script = Node('Script', 4, bytes(1), [Node('OrCondition', 1, b'', [Node('Condition', 1, b'', [])]),
                                         Node('ScriptAction', 1, b'', [])])
    base.nodes.append(Node('PlayerScriptsList', 1, b'', [
        Node('ScriptList', 1, b'', kids) for kids in ([], [], [script])]))
    container.write_bytes(base.chunk_file())

    def export(stem):
        build(design_file, library_file, kit=kit).write(container, tmp_path / stem)
        return tuple((tmp_path / f'{stem}-{kind}').read_bytes()
                     for kind in ('game.map', 'editor.map', 'locked.json'))

    first = export('first')
    assert first == export('repeat')
    picture = (tmp_path / 'first-relations.svg').read_text(encoding='utf-8')
    results = (tmp_path / 'first-checks.md').read_text(encoding='utf-8')
    assert '地图草图' in picture and '>start</text>' in picture and 'oversize' in picture
    assert '🟢 通过 · `space`' in results and '🔴 未通过 · `oversize`' in results
    for raw in first[:2]:
        output = MapFile(raw)
        nodes = {node.name: node for node in output.nodes}
        assert {name: (nodes[name].ver, nodes[name].head) for name in donor} == donor
        assert mapxml._typed_props(output, nodes['WorldInfo'].head, 0) == {
            'cameraMaxHeight': (2, 450.), 'weather': (1, 5)}
