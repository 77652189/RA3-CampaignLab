"""Fit measured sockets and read the resulting retail road records."""
from collections import Counter
import json
import math

import numpy as np
import pytest

from experimental.mapgen import build, design, paint, roads, terrain

import mapterrain
import mapxml
import newmap
from mapscript import MapFile, Node
from platmap import walkable
from test_mapgen_terrain import _container


KIT = 'Heidelberg_HB'


def sketch(spine, branch=None, *, river=False, land_pass=('foot', 'vehicle', 'amphibian')):
    end = 1600 if river else 800
    ring = [[0, 0], [end, 0], [end, end], [0, end], [0, 0]]
    blocks = {'west': dict(at=[100, 200], height=4, use='suburb')}
    borders = {'frame': dict(line=ring, closed_reason='map edge')}
    lines = {'main': dict(line=spine, width='street', ends=['start', 'end'])}
    if branch:
        lines['branch'] = dict(line=branch, width='street', ends=['end'])
    if river:
        blocks.update(east=dict(at=[1400, 200], height=4, use='suburb'),
                      waterLow=dict(at=[800, 200], height=0, use='water', kind='water'),
                      waterHigh=dict(at=[800, 1400], height=0, use='water', kind='water'))
        for name, x in (('westBank', 350), ('eastBank', 1250)):
            borders[name] = {'line': [[x, 0], [x, end]], 'pass': list(land_pass)}
    return design.Design(dict(version=2, blocks=blocks, borders=borders, roads=lines))


def test_ports_and_t_piece():
    ground = terrain.expand(terrain.TerrainPlan(base_steps=4), {}, 81, 81, 0)
    result = roads.expand(sketch([[50, 400], [750, 400]], [[400, 400], [400, 750]]), ground, 0, KIT)
    pieces = [p for p in result.placements if p.ports]
    assert Counter(p.template for p in pieces) == {'HV_StreetSegment15': 1, 'HV_StreetSegment09': 9}
    ports = [port for p in pieces for port in p.ports]
    ends = ((50, 400), (750, 400), (400, 750))
    for i, port in enumerate(ports):
        hits = [p for j, p in enumerate(ports) if i != j and math.dist(port.xy, p.xy) <= 1]
        if any(math.dist(port.xy, end) <= 1 for end in ends):
            assert hits == []
        else:
            other, = hits
            assert math.cos(port.heading - other.heading) == pytest.approx(-1)


def test_unjoinable_names_road_and_location():
    ground = terrain.expand(terrain.TerrainPlan(base_steps=4), {}, 81, 81, 0)
    with pytest.raises(design.DesignError, match=r'branch .*\(400, 400\).*3 junction arms'):
        roads.expand(sketch([[50, 400], [750, 400]], [[400, 400], [500, 750]]), ground, 0, KIT)


def test_road_to_frame_uses_apron_grade_without_opening_the_backdrop(tmp_path, monkeypatch):
    monkeypatch.setattr(build, 'CONTAINER', (81, 81, 0))
    monkeypatch.setattr(paint, 'ART', tmp_path)
    (tmp_path / 'surface.tga').touch()

    def material(name):
        return [dict(id=name, Texture='surface.tga', BumpTexture='surface.tga')]

    library = tmp_path / 'library.json'
    library.write_text(json.dumps({
        'kits': {KIT: {'buildings': [], 'destructibles': [], 'props': []}},
        'blocking': {},
        'texture_kits': {
            'Heidelberg': {'Grass': material('Grass_Heidelberg01'), 'Road': material('Pavement_Heidelberg10')},
            'Gibraltar': {'Cliff': material('Cliff_Gibraltar1')},
        },
    }), encoding='utf8')
    frame = ((100, 200), (700, 200), (700, 600), (100, 600))
    design_file = tmp_path / 'slice.json'
    design_file.write_text(json.dumps({
        'version': 2,
        'blocks': {'south': {'at': [300, 300], 'height': 4, 'use': 'park'},
                   'north': {'at': [300, 500], 'height': 4, 'use': 'park'}},
        'borders': {'frame': {'line': (*frame, frame[0]), 'closed_reason': 'slice boundary'}},
        'roads': {'street': {'line': [(100, 400), (700, 400)], 'width': 'street'}},
    }), encoding='utf8')
    apron = terrain.Block(((50, 150), (750, 150), (750, 650), (50, 650)), 4,
                          surface=terrain.Surface('apron', 'park', KIT))
    result = build.build(design_file, library, terrain.TerrainPlan(blocks=(apron,)), kit=KIT, road_kit=KIT)
    assert result.frame.map_borders(0) == [(0, 0, 81, 81), (10, 20, 70, 60)]
    assert result.border_index == 1
    assert result.roadbed.paved[40, 10] and not result.ground.blocked[40, 10]
    assert result.ground.raw[40, 9] == result.ground.raw[40, 10] == 4 * terrain.CLIFF_STEP_RAW
    assert result.ground.blocked[40, 9] and result.ground.textures[40, 9] == 'Grass_Heidelberg01'


def test_same_design_same_map_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(paint, 'ART', tmp_path)
    (tmp_path / 'surface.tga').touch()

    def material(name):
        return [dict(id=name, Texture='surface.tga', BumpTexture='surface.tga')]

    library = {'texture_kits': {'Heidelberg': {'Grass': material('Grass_Heidelberg01'),
                                              'Road': material('Pavement_Heidelberg10')}}}
    plan = terrain.TerrainPlan()

    def build():
        d = sketch([[50, 400], [750, 400]], [[400, 400], [400, 750]])
        ground = terrain.expand(plan, library, 81, 81, 0)
        network = roads.expand(d, ground, 0, KIT)
        m = _container(81, 81, 0)
        terrain.apply(m, plan, paint.paint(plan, library, ground, network))
        m.name_id('Object')
        m.name_id('ObjectsList')
        m.nodes.append(Node('ObjectsList', 1, b'', [
            newmap.object_node(m, {}, p.flags, p.template, p.x, p.y, angle=p.angle)
            for p in network.placements]))
        return m.map_file()

    output = build()
    assert output == build()
    readback = MapFile(output)
    objects = mapxml.objects(readback)
    roads_only = [o for o in objects if o['flags']]
    assert roads_only
    assert all(a['template'] == b['template'] and (a['flags'] & 6, b['flags'] & 6) == (2, 4)
               for a, b in zip(roads_only[::2], roads_only[1::2], strict=True))
    tiles = mapterrain.Tiles(readback, 81)
    assert tiles.texture_at(40, 40) == 'Pavement_Heidelberg10'

    def bit(field, i, j):
        return tiles.extra[(field * tiles.height + j) * tiles.row_bytes + i // 8] & (1 << (i % 8))

    assert bit(0, 40, 40) == bit(4, 40, 40) == 0
    assert bit(4, 40, 30)


def test_bridge_deck_and_boat_channel():
    water = terrain.Water(((350, 0), (1250, 0), (1250, 1600), (350, 1600)))
    plan = terrain.TerrainPlan(base_steps=4, water=(water,))
    ground = terrain.expand(plan, {}, 161, 161, 0)
    line = [[100, 800], [1500, 800]]
    result = roads.expand(sketch(line, river=True), ground, 0, KIT)
    crossing, = result.bridges
    assert crossing.span == 2 * 75 + 6 * 150
    assert crossing.deck_width == 120
    assert crossing.deck_pass == {'foot', 'vehicle', 'amphibian'}
    assert crossing.water_pass == {'amphibian', 'ship'}
    assert crossing.landings == ((275, 800), (1325, 800))
    assert crossing.channel_width >= 36 and crossing.clearance == pytest.approx(280 - 200 - 27.46)
    pair = [p for p in result.placements if p.side == 'neutral']
    assert [(p.template, p.x, p.y, p.flags) for p in pair] == [
        ('HB_Bridge_02', 275, 800, 16), ('HB_Bridge_02', 1325, 800, 32)]
    # Discrete ground and water lanes cross at the same XY without a filled causeway.
    for x in (27, 28, 132, 133):
        assert not ground.blocked[80, x] and ground.raw[80, x] > ground.waterline[80, x]
    heights = ground.raw / terrain.rules.RAW_PER_OURS
    dry = walkable(None, dims=(161, 161, 0), e=heights)
    deck = walkable(None, pair, (161, 161, 0), e=heights)
    assert not dry[80, 80] and deck[80, 10:151].all()
    assert np.all(ground.raw[65:96, 80] < ground.waterline[65:96, 80])
    assert not result.hidden[80, 80]
    with pytest.raises(design.DesignError, match='main .*opening declares'):
        roads.expand(sketch(line, river=True, land_pass=('foot',)), ground, 0, KIT)
