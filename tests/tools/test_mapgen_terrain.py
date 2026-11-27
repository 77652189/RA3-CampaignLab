"""Terrain expansion and the two map wrappers on a small generated container."""
from dataclasses import replace
import json
import struct

import numpy as np
import pytest

from experimental.campaign.mapscript import MapFile
from experimental.mapgen.design import Design
from experimental.mapgen.terrain import Block, Cliff, Ramp, Surface, TerrainPlan, Water, apply, expand, from_design
from experimental.mapgen.build import build
from experimental.mapgen import paint, terrain
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


def test_vladivostok_wall_fits_the_run_up_to_the_ramp_shoulders():
    kit = 'Iceland_IL'
    wall = dict(template='VL_CliffWall02', length=74, offset_y=-26, height_steps=1, samples=56)
    library = {'kits': {kit: {'cliffs': [wall]}}}
    plan = TerrainPlan(
        blocks=(Block(((0, 200), (450, 200), (450, 350), (0, 350)), 4),),
        cliffs=(Cliff((0, 200), (450, 200), kit),),
        ramps=(Ramp((250, 110), (0, 1), 1, 200),),
    )
    ground = expand(plan, library, 46, 36, 0)
    # The cut is [140, 360]. Two 74-unit pieces fit the first run at pitch 66.
    # The second 90-unit run is too short for that overlap; it keeps one centred piece.
    assert [(p.x, p.y) for p in ground.pieces] == [(37, 226), (103, 226), (405, 226)]
    assert ground.hidden[19, :14].all() and not ground.hidden[19, 14:36].any()


def test_measured_short_cliff_fills_a_straight_run_on_the_same_axis():
    long, short, curve = ('MJ_CliffWall' + suffix for suffix in ('01', '08', '10'))
    library = {'kits': {'Fuji': {
        'props': [{'template': name, 'editor_name': role} for name, role in
                  ((long, 'CliffStraight'), (short, 'CliffStraightShorter2'), (curve, 'CliffSCurveLeft2'))],
        'cliffs': [
            {'template': name, 'height_steps': 1, 'length': length, 'offset_y': offset, 'samples': samples}
            for name, length, offset, samples in ((long, 120, -28, 91), (short, 60, -10, 79), (curve, 157, -13, 100))
        ],
    }}}
    plan = TerrainPlan(blocks=(Block(((0, 100), (190, 100), (190, 200), (0, 200)), 4),),
                       cliffs=(Cliff((0, 100), (190, 100), 'Fuji'),))
    ground = expand(plan, library, 20, 21, 0)
    # 120 + 60 centred in 190. The paired originals are 90 apart with no cross-axis offset.
    assert [(p.template, p.x, p.y) for p in ground.pieces] == [(long, 65, 128), (short, 155, 128)]
    assert any('10 units uncovered' in issue for issue in ground.issues)


def test_authored_dirt_track_keeps_its_material_across_the_ramp_join(tmp_path, monkeypatch):
    monkeypatch.setattr(paint, 'ART', tmp_path)
    (tmp_path / 'tile').touch()

    def tiles(name):
        return [dict(id=name, Texture='tile', BumpTexture='tile')]

    kit = 'Heidelberg_HB'
    library = {'kits': {kit: {}}, 'texture_kits': {
        'Heidelberg': {'Grass': tiles('BaseGrass'), 'Dirt': tiles('BaseDirt')},
        'Cape_Cod': {'Dirt': tiles('TrackDirt')},
        'Gibraltar': {'Cliff': tiles('RockFace')},
    }}
    plan = TerrainPlan(ground='BaseGrass', blocks=(
        Block(((0, 0), (200, 0), (200, 150), (0, 150)), 3, surface=Surface('low', 'wildland', kit, 0, 'TrackDirt')),
        Block(((0, 150), (200, 150), (200, 300), (0, 300)), 4, surface=Surface('high', 'wildland', kit, 0, 'TrackDirt')),
    ), ramps=(Ramp((100, 60), (0, 1), 1, 100),))
    ground = paint.paint(plan, library, expand(plan, library, 21, 31, 0))
    assert ground.owners[14, 10] != ground.owners[16, 10]
    assert list(ground.textures[14:17, 10]) == ['TrackDirt'] * 3
    assert ground.edge_texture(10, 14, 10, 15, 'TrackDirt') == 'TrackDirt'


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
    # Two terrain cells of setback put the model's origin over the 130
    # floor. The two dry routing rows behind the model still block beaching.
    assert all(p.z == pytest.approx(80) for p in ground.pieces)
    assert ground.raw[32, 20] == 130 * terrain_rules.RAW_PER_WORLD
    assert not ground.blocked[32, 20] and ground.blocked[33, 20]
    assert ground.blocked[34, 20] and not ground.blocked[35, 20]
    m = _container(41, 51, 0)
    apply(m, plan, ground)
    tiles = mapterrain.Tiles(m, 41)
    assert tiles.extra[33 * tiles.row_bytes + 20 // 8] & 1 << (20 % 8)
    assert not ground.hidden[33, 20]  # the blocked lip continues past the mesh

def test_quay_corner_fits_both_straights_and_a_diagonal_join():
    kit = 'StPetersburg_ST'
    straight, corner = 'ST_SeaWallPiece01', 'ST_SeaWallPiece02'
    library = {'kits': {kit: {'props': [{'template': name} for name in (straight, corner)]}}}
    plan = TerrainPlan(quays=tuple(terrain.Quay(a, b, kit, 3) for a, b in (
        ((0, 200), (400, 200)), ((400, 200), (400, 450)), ((400, 450), (550, 600)),
    )))
    pieces = expand(plan, library, 71, 71, 0).pieces
    fitting, = [p for p in pieces if p.template == corner]
    # Two 50-unit legs, on axes offset 7 inland. The diagonal
    # straight shares a tip with the preceding one at the miter.
    assert (fitting.x, fitting.y, fitting.angle) == (393, 207, 0)
    east = [p for p in pieces if p.angle == 0 and p.template == straight]
    north = [p for p in pieces if p.angle == np.pi / 2]
    diagonal = [p for p in pieces if p.angle == np.pi / 4]
    assert (east[-1].x + 50, east[-1].y) == (343, 207)
    assert (north[0].x, north[0].y - 50) == (393, 257)
    diagonal_tip = np.array([diagonal[0].x, diagonal[0].y]) - 50 / np.sqrt(2)
    np.testing.assert_allclose(diagonal_tip, [north[-1].x, north[-1].y + 50])


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


def test_winter_apron_keeps_the_adjacent_surface():
    from experimental.mapgen.design import Design

    sketch = Design({
        'version': 2, 'blocks': {'woods': {'height': 3, 'at': [500, 400], 'use': 'snow_woodland',
                                            'kit': 'Iceland_IL', 'ground_texture': 'Snow_Iceland03'}},
        'borders': {'frame': {'line': [[200, 200], [800, 200], [800, 600], [200, 600], [200, 200]]}},
    })
    plan = terrain.from_design(sketch, terrain.TerrainPlan(), 'Heidelberg_HB')
    extended = terrain.frame_apron(sketch, plan, (161, 141, 30))
    assert len(extended.blocks) == 5
    assert all(block.surface == plan.blocks[0].surface for block in extended.blocks)


def test_mixed_frame_continues_both_sides_of_the_coast():
    sketch = Design({
        'version': 2,
        'blocks': {'land': {'height': 3, 'at': [600, 720], 'use': 'farm'},
                   'sea': {'height': 3, 'at': [600, 400], 'use': 'water', 'kind': 'water'}},
        'borders': {'frame': {'line': [[200, 200], [1200, 200], [1200, 900], [200, 900], [200, 200]]},
                    'coast': {'line': [[200, 550], [1200, 550]]}},
    })
    size = (191, 161, 30)
    plan = terrain.frame_apron(sketch, from_design(sketch, TerrainPlan(), 'Cape_Cod_CC'), size)
    ground = expand(plan, {}, *size)
    outside_sea = (30, 90)  # world (600, 0), at the camera boundary
    outside_land = (132, 90)  # world (600, 1020)
    assert ground.raw[outside_sea] == 130 * terrain_rules.RAW_PER_WORLD
    assert ground.waterline[outside_sea] == 200 * terrain_rules.RAW_PER_WORLD
    assert plan.blocks[ground.owners[outside_land]].surface.id == 'land'
    frame = terrain.design_frame(sketch, ground, len(plan.blocks) - plan.design_land_count, size[2])
    assert not frame.mask[outside_sea] and not frame.mask[outside_land]


def test_beach_bank_descends_from_the_adjacent_grade():
    sketch = Design({
        'version': 2,
        'blocks': {'beach': {'height': 3, 'at': [500, 750], 'use': 'farm'},
                   'sea': {'height': 3, 'at': [500, 250], 'use': 'water', 'kind': 'water'}},
        'borders': {'frame': {'line': [[0, 0], [1000, 0], [1000, 1000], [0, 1000], [0, 0]]},
                    'shore': {'line': [[0, 600], [1000, 600]], 'pass': ['amphibian']}},
    })
    plan = from_design(sketch, TerrainPlan(base_steps=4), 'Cape_Cod_CC')
    ground = expand(plan, {}, 101, 101, 0)
    assert ground.raw[60, 50] == 210 * terrain_rules.RAW_PER_WORLD
    assert ground.raw[59, 50] == round(206 * terrain_rules.RAW_PER_WORLD)
    assert ground.raw[57, 50] < ground.waterline[57, 50]
    assert not ground.blocked[57:61, 50].any()


def test_delivery_rejects_missing_cliff_wall(tmp_path):
    from experimental.mapgen.build import MapBuild
    from experimental.mapgen.buildings import Layout

    plan = terrain.TerrainPlan(
        blocks=(terrain.Block(((0, 100), (300, 100), (300, 300), (0, 300)), 4),),
        cliffs=(terrain.Cliff((0, 100), (300, 100), 'test'),),
    )
    size = 91, 91, 30
    ground = terrain.expand(plan, {'kits': {}}, *size)
    assert any('no measured 1-step straight piece' in issue for issue in ground.issues)
    built = MapBuild(plan, ground, None, Layout(()), None, None, ())
    source = tmp_path / 'container.map'
    m = _container(*size)
    m.name_id('ObjectsList')
    m.nodes.append(Node('ObjectsList', 3, b'', []))
    source.write_bytes(m.map_file())
    with pytest.raises(ValueError, match='no measured 1-step straight piece'):
        built.write(source, tmp_path / 'map')
    assert not list(tmp_path.glob('map-*'))
