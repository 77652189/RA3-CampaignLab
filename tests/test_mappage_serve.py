"""The map page served locally (experimental/mappage/serve.py, user 2026-11-04): proposals posted to the server land as
files that --pull reads, delete removes them, other origins cannot write, and /api/preview is the contract on the
edited ground (nothing proposed = what build.py --show says)."""
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

from test_mappage import ROOT, _a4, mappage
from test_mappage_terrain import _terrain_doc

sys.modules.setdefault('mappage', mappage)
_spec = importlib.util.spec_from_file_location('mappage_serve', ROOT / 'experimental' / 'mappage' / 'serve.py')
serve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serve)


@pytest.fixture
def server(tmp_path):
    html = tmp_path / 'page.html'
    html.write_text('<!doctype html><title>t</title>', encoding='utf-8')
    level = serve.Level('a4', str(html), str(tmp_path / 'proposals'))
    srv = serve.make_server(level, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{srv.server_address[1]}', tmp_path
    srv.shutdown()
    srv.server_close()


def _call(url, method='GET', body=None, origin=None):
    req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json', **({'Origin': origin} if origin else {})})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b'null') if 'json' in r.headers['Content-Type'] else r.read()
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'null')


@pytest.mark.skipif(shutil.which('node') is None, reason='node not installed')
def test_page_script_parses(tmp_path):
    """The page's own script (template.html) is valid JavaScript: a stray quote stops the whole page, store included."""
    src = (ROOT / 'experimental' / 'mappage' / 'template.html').read_text(encoding='utf-8')
    js = re.findall(r'<script>(.*?)</script>', src, re.S)[-1].replace('__DATA__', '{}')
    f = tmp_path / 'page.js'
    f.write_text(js, encoding='utf-8')
    r = subprocess.run([shutil.which('node'), '--check', str(f)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    assert r.returncode == 0, r.stderr[-800:]


def test_server_listens_on_loopback_only(server):
    url, _ = server
    assert url.startswith('http://127.0.0.1:')
    code, page = _call(url + '/')
    assert code == 200 and b'<title>t</title>' in page


def test_post_saves_a_file_pull_reads_and_delete_removes(server):
    url, tmp = server
    s = _a4().map.SITES
    code, j = _call(url + '/api/proposals', 'POST', {'kind': 'note', 'at_xy': [s['start'].x, s['start'].y],
                                                     'why': '这里太空', 'level': 'a4', 'at': '2026-11-04T10:00'},
                    origin=url)
    assert code == 200
    pid = j['id']
    f = tmp / 'proposals' / f'{pid}.json'
    assert json.loads(f.read_text(encoding='utf-8'))['why'] == '这里太空'
    code, j = _call(url + '/api/proposals')
    assert [d['id'] for d in j['docs']] == [pid]
    out = mappage.pull('a4', str(tmp))
    assert '1 条' in out and f'[{pid}] 批注' in out and "地点 'start'" in out and '这里太空' in out
    assert _call(url + f'/api/proposals/{pid}', 'DELETE', origin=url)[0] == 200
    assert not f.exists()
    assert _call(url + '/api/proposals/../x', 'DELETE')[0] in (400, 404)


def test_another_site_cannot_write(server):
    url, tmp = server
    code, _ = _call(url + '/api/proposals', 'POST', {'kind': 'note', 'at_xy': [0, 0]}, origin='https://example.com')
    assert code == 403 and not list((tmp / 'proposals').iterdir())
    assert _call(url + '/api/proposals', 'POST', {'no': 'kind'})[0] == 400


def test_preview_is_the_show_contract_then_the_draft(server):
    """Nothing proposed: the preview's contract is build.py --show's. A hill raised on a cast site as the unsaved draft
    turns that site red, the same as --apply-preview on the saved proposal."""
    url, tmp = server
    code, j = _call(url + '/api/preview', 'POST', {'draft': None})
    assert code == 200, j
    assert j['steps'] == [] and j['after'] == list(mappage.parts.contract(_a4()))
    m = _a4()
    k = next(n for n, s in m.map.SITES.items() if s.cast)
    code, j = _call(url + '/api/preview', 'POST', {'draft': _terrain_doc(m.map.SITES[k])})
    assert code == 200, j
    assert {'site': k, 'what': 'cast', 'flat': False} in j['flips']
    assert any(k in p for p in j['red']), j['red']
