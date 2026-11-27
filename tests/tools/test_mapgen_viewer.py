from experimental.mapgen import terrain
from experimental.mapgen.build import MapBuild
from experimental.mapgen.buildings import Layout
from experimental.mapgen.campaign_writer import CONTAINER
from experimental.mapgen.design import Design
from experimental.mappage.viewer import write_viewer


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
