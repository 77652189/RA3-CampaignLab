"""The map page's new-map mode (user 2026-11-04: "地形编辑器升级成能画新地图"): a sketch becomes a map module in the
platmap format (experimental/mappage/sketch2map.py). The same sketch gives the same text; an existing map written out as
a sketch and generated again reads the same to every rule (sapporo, the A4 map); a drawn map is linted, its cut-off
sites found, its .map written; the server keeps the sketch and only takes writes from its own pages."""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest

from test_mappage import ROOT, mappage

sys.modules.setdefault('mappage', mappage)
sk = mappage._load('sketch2map', str(ROOT / 'experimental' / 'mappage' / 'sketch2map.py'))
_spec = importlib.util.spec_from_file_location('mappage_serve', ROOT / 'experimental' / 'mappage' / 'serve.py')
serve = sys.modules.get('mappage_serve') or importlib.util.module_from_spec(_spec)
if 'mappage_serve' not in sys.modules:
    sys.modules['mappage_serve'] = serve
    _spec.loader.exec_module(serve)


def _trial(ramp=True):
    """A small drawn map: a plateau with its ramp, a lake, a mesa (with or without its ramp), a cliff wall with a gap."""
    s = sk.blank('trialtest', (3000, 3000))
    s['shapes'] = [
        {'kind': 'poly', 'at': [[1800, 1900], [2800, 1850], [2900, 2800], [1900, 2850]], 'tier': 2, 'what': 'plateau'},
        {'kind': 'circle', 'at': [1300, 900, 350], 'tier': 0, 'what': 'lake'},
        {'kind': 'rect', 'at': [300, 2200, 900, 2800], 'tier': 3, 'what': 'mesa'},
    ]
    s['walls'] = [{'points': [[1100, 100], [1100, 1300]], 'width': 100, 'tier': 3, 'what': ''},
                  {'points': [[1100, 1600], [1100, 2000]], 'width': 100, 'tier': 3, 'what': ''}]
    s['ramps'] = [{'low': [1450, 2350], 'high': [2150, 2350], 'width': 180, 'what': 'plateau ramp'}]
    if ramp:
        s['ramps'].append({'low': [600, 1750], 'high': [600, 2420], 'width': 160, 'what': 'mesa ramp'})
    s['roads'] = [{'points': [[500, 1450], [1100, 1450], [1450, 2350]], 'width': 120, 'texture': 'Pavement_Heidel02'}]
    s['start'] = [500, 1450]
    s['sites'] = {'plateau': {'x': 2400, 'y': 2350, 'r': 300, 'zh': '东北高地', 'what': 'the enemy camp'},
                  'mesa': {'x': 600, 'y': 2500, 'r': 150, 'zh': '孤台', 'what': 'the mesa'},
                  'wall gap': {'x': 1100, 'y': 1450, 'r': 80, 'zh': '崖口', 'what': 'the gap in the wall'}}
    s['fields'] = [{'name': 'home', 'x': 600, 'y': 1000, 'facing': 45, 'twin': 1, 'base': '', 'owner': 'p1', 'build': 0}]
    return s


def test_same_sketch_same_text(tmp_path):
    s = _trial()
    assert sk.module_text(s) == sk.module_text(json.loads(json.dumps(s)))
    p = sk.generate(s, str(tmp_path))
    first = (tmp_path / 'trialtest.py').read_bytes()
    sk.generate(json.loads(json.dumps(s)), str(tmp_path))
    assert (tmp_path / 'trialtest.py').read_bytes() == first
    names = (tmp_path / 'trialtest_names.py').read_text(encoding='utf-8')
    assert "'mesa': '孤台'" in names and "'start': '玩家起点'" in names
    mod = sk.load(p)
    assert {'start', 'plateau', 'mesa', 'wall gap', 'home refinery'} <= set(mod.SITES)
    assert mod.BORDERS == {'whole': (0, 0, 3000, 3000)}


@pytest.mark.parametrize('name', ['sapporo', 'himeji'])
def test_existing_map_round_trip(tmp_path, name):
    """maps/<name>.py -> sketch -> module: every rule reading the same (heights, walkability, lint, sites, borders,
    objects, scenery, blocks); and the generated module written out again gives the same text."""
    mod, names = sk.map_module(name)
    s = sk.from_module(mod, names)
    s = json.loads(json.dumps(s))                       # what the page saves and the server reads back
    g = sk.load(sk.generate(s, str(tmp_path)))
    a, b = sk.readings(mod), sk.readings(g)
    for k in a:
        assert a[k] == b[k], k
    again = sk.from_module(g, names)
    again.update(name=s['name'], what=s['what'])
    assert sk.module_text(again) == sk.module_text(s)


def test_readings_see_a_moved_shape(tmp_path):
    """The round trip's comparison is not blind: one shape nudged 50 changes the heights it reads."""
    mod, names = sk.map_module('sapporo')
    s = sk.from_module(mod, names)
    s['shapes'][-1]['at'][0] += 50.0
    g = sk.load(sk.generate(s, str(tmp_path)))
    assert sk.readings(g)['heights'] != sk.readings(mod)['heights']


def test_cut_off_site_found_then_joined(tmp_path):
    no = sk.report('trialtest', _trial(ramp=False), with_map=False, out=str(tmp_path / 'no'))
    assert no['problems'] == [] and no['lint'] == [] and no['contract'] == []
    assert no['regions']['cut off'] == ['mesa'] and not no['ok']
    yes = sk.report('trialtest', _trial(ramp=True), with_map=False, out=str(tmp_path / 'yes'))
    assert yes['regions']['cut off'] == [] and yes['ok'], yes
    assert (tmp_path / 'yes' / 'regions.png').exists()


def test_cliff_wall_closes_the_way(tmp_path):
    """A wall straight across the map leaves the east out of reach (steep both sides, not an invisible wall)."""
    s = _trial()
    s['walls'] = [{'points': [[1500, -100], [1500, 3100]], 'width': 100, 'tier': 3, 'what': 'across'}]
    s['sites']['east'] = {'x': 2600, 'y': 800, 'r': 50, 'zh': '', 'what': ''}
    r = sk.report('trialtest', s, with_map=False, out=str(tmp_path))
    assert 'east' in r['regions']['cut off'] and 'plateau' in r['regions']['cut off']


def test_lint_reaches_the_page(tmp_path):
    """A ramp with both ends on one level is the design lint's (platmap), and the report carries it."""
    s = _trial()
    s['ramps'].append({'low': [200, 400], 'high': [700, 400], 'width': 160, 'what': 'flat'})
    r = sk.report('trialtest', s, out=str(tmp_path))
    assert any('both ends on one level' in p for p in r['lint']) and not r['ok']
    assert 'map' not in r and 'both ends on one level' in r['map_error']     # platmap.apply refuses to write it


def test_bad_sketch_is_refused():
    s = _trial()
    s['shapes'].append({'kind': 'poly', 'at': [[0, 0], [1, 1]], 'tier': 7, 'what': ''})
    probs = sk.check_sketch(s)
    assert any('3 points' in p for p in probs) and any('tier 7' in p for p in probs)
    with pytest.raises(ValueError):
        sk.module_text(s)
    with pytest.raises(ValueError):
        sk.blank('x', (6000, 1000))


def test_map_written(tmp_path):
    """The drawn map is written as the build writes it (parts.preview) and measured like cnv_preview."""
    r = sk.report('trialtest', _trial(), out=str(tmp_path))
    assert r['ok'], r
    assert (ROOT / r['map']).exists() and (tmp_path / 'ground.png').exists()
    assert any(x.startswith('TERRAIN ') for x in r['study']), r['study']


def test_pathing_skips_without_the_model(tmp_path):
    mod = sk.load(sk.generate(_trial(), str(tmp_path)))
    assert sk.pathing(mod, [('start', 'plateau')], model_dir=str(tmp_path / 'nowhere')) is None


# ---- the server's new-map mode

@pytest.fixture
def sketch_server(tmp_path):
    sketch = serve.Sketch('trialtest', (3000, 3000), folder=str(tmp_path / 'trialtest'))
    sketch.with_map = False
    srv = serve.make_sketch_server(sketch, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{srv.server_address[1]}', tmp_path / 'trialtest'
    srv.shutdown()
    srv.server_close()


def _call(url, method='GET', body=None, origin=None):
    req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json', **({'Origin': origin} if origin else {})})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, (json.loads(r.read() or b'null') if 'json' in r.headers['Content-Type'] else r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'null')


def test_server_keeps_the_sketch_and_generates(sketch_server):
    url, folder = sketch_server
    code, s = _call(url + '/api/sketch')
    assert code == 200 and s['size'] == [3000.0, 3000.0] and s['shapes'] == []
    drawn = dict(_trial(), name='ignored')
    assert _call(url + '/api/sketch', 'POST', drawn)[0] == 200
    saved = json.loads((folder / 'sketch.json').read_text(encoding='utf-8'))
    assert saved['name'] == 'trialtest' and len(saved['shapes']) == 3
    code, r = _call(url + '/api/generate', 'POST', drawn)
    assert code == 200 and r['ok'], r
    assert _call(url + '/files/regions.png')[0] == 200
    assert _call(url + '/files/../sketch.json')[0] == 404
    code, page = _call(url + '/')
    assert code == 200 and b'trialtest' in page and b'/*BOOT*/' not in page


def test_other_origin_cannot_write_the_sketch(sketch_server):
    url, folder = sketch_server
    before = (folder / 'sketch.json').read_bytes()
    assert _call(url + '/api/sketch', 'POST', _trial(), origin='https://example.com')[0] == 403
    assert _call(url + '/api/generate', 'POST', _trial(), origin='https://example.com')[0] == 403
    assert (folder / 'sketch.json').read_bytes() == before


def test_bad_names_refused(tmp_path):
    with pytest.raises(ValueError):
        serve.Sketch('../evil', folder=str(tmp_path))


@pytest.mark.skipif(shutil.which('node') is None, reason='node not installed')
def test_sketch_page_script_parses(tmp_path):
    src = (ROOT / 'experimental' / 'mappage' / 'sketch.html').read_text(encoding='utf-8')
    js = re.findall(r'<script>(.*?)</script>', src, re.S)[-1].replace('/*BOOT*/null', '{}')
    f = tmp_path / 'sketch.js'
    f.write_text(js, encoding='utf-8')
    r = subprocess.run([shutil.which('node'), '--check', str(f)], capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    assert r.returncode == 0, r.stderr[-800:]
