from experimental.mapgen import terrain
from experimental.mapgen.build import MapBuild
from experimental.mapgen.buildings import Layout
from experimental.mapgen.campaign_writer import CONTAINER
from experimental.mapgen.design import Design
from experimental.mappage.viewer import write_preview, write_viewer


def test_failed_relation_has_a_place_in_a_repeatable_view(tmp_path):
    sketch = Design({
        'version': 2,
        'blocks': {'yard': {'height': 3, 'use': 'park', 'at': [200, 200]}},
        'borders': {'frame': {'line': [[100, 100], [300, 100], [300, 300], [100, 300], [100, 100]]}},
        'points': {'muster': {'at': [140, 175], 'block': 'yard'}},
        'relations': {'musterSpace': {'type': '放得下', 'point': 'muster', 'side': 100}},
    })
    border = CONTAINER[2]
    plan = terrain.from_design(sketch, terrain.TerrainPlan(), 'test')
    ground = terrain.expand(plan, {'kits': {}}, 95, 95, border)
    frame = terrain.design_frame(sketch, ground, 0, border)
    built = MapBuild(plan, frame.close(ground), None, Layout(()), sketch, frame, ())

    def emit(name):
        directory = tmp_path / name
        directory.mkdir()
        write_viewer(directory, title='Example', sketch=built.sketch, answers=built.check_relations(),
                     bounds=(100, 100, 300, 300), retail_label='Example reference')
        return directory

    first, second = emit('first'), emit('second')
    page = (first / 'index.html').read_bytes()
    assert page == (second / 'index.html').read_bytes()
    html = page.decode('utf-8')
    assert '未通过' in html and '位置　muster' in html
    assert 'data-highlight="0"><use href="#place-muster"/>' in html
    assert 'id="place-muster"><circle cx="40" cy="125"' in html
    summary = (first / 'summary.md').read_text(encoding='utf-8')
    assert 'FAIL `musterSpace`' in summary and '`muster` (140, 175)' in summary
    assert '留一块同高的空地' in html and '留一块同高的空地' in summary


def test_route_witness_is_drawn_at_its_own_location(tmp_path):
    from experimental.mapgen.checks import Answer, Witness

    sketch = Design({
        'version': 2, 'blocks': {'bay': {'height': 0, 'kind': 'water', 'use': 'water', 'at': [400, 350]}},
        'borders': {'frame': {'line': [[300, 200], [700, 200], [700, 600], [300, 600], [300, 200]]}},
    })
    answer = Answer('fail', '舰艇进港', ('bay',), '加深航道', Witness('bay', (500, 300), '航道水深 25'))
    write_viewer(tmp_path, title='Example', sketch=sketch, answers={'enter': answer},
                 bounds=(300, 200, 700, 600), retail_label='Example')
    assert '<circle class="witness" cx="200" cy="300"' in (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert '(500, 300) 航道水深 25' in (tmp_path / 'summary.md').read_text(encoding='utf-8')


def test_preview_displays_known_terrain_diagnostics(tmp_path):
    from dataclasses import replace

    sketch = Design({
        'version': 2, 'blocks': {'low': {'height': 3, 'use': 'park', 'at': [200, 150]},
                                 'high': {'height': 4, 'use': 'park', 'at': [200, 250]}},
        'borders': {'frame': {'line': [[100, 100], [300, 100], [300, 300], [100, 300], [100, 100]]},
                    'wall': {'line': [[100, 200], [300, 200]], 'closed_reason': 'cliff'}},
        'relations': {'closed': {'type': '通不通', 'from': 'low', 'to': 'high',
                                 'who': 'vehicle', 'reachable': False}},
    })
    border = CONTAINER[2]
    plan = terrain.from_design(sketch, terrain.TerrainPlan(), 'test')
    ground = terrain.expand(plan, {'kits': {}}, 95, 95, border)
    frame = terrain.design_frame(sketch, ground, 0, border)
    ground = replace(frame.close(ground), issues=('inspect the <shoulder>',))
    built = MapBuild(plan, ground, None, Layout(()), sketch, frame, (), level='sketch')
    assert built.check_relations()['closed'].status == 'pass'
    write_preview(tmp_path, built, title='Example')
    for file, shoulder in (('index.html', 'inspect the &lt;shoulder&gt;'), ('summary.md', ground.issues[0])):
        output = (tmp_path / file).read_text(encoding='utf-8')
        assert ground.errors[0] in output and shoulder in output
