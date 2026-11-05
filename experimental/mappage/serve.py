"""The map page served from this computer (ADR 0017; user 2026-11-04: "我更希望运行在本地"): one level's page, its
proposals kept as files, and the rule preview computed here. Listens on 127.0.0.1 only; no accounts, nothing sent out.

  python -I -X utf8 experimental/mappage/serve.py a4            -> http://127.0.0.1:8765/
  python -I -X utf8 experimental/mappage/serve.py a4 --port 0   (any free port; the address is printed)

On start it writes the page (mappage.export, the same as `mappage.py a4`) and serves it at /. The page finds /api and
stores its proposals here:
  GET    /api/proposals          every proposal of the level: [{id, data}], oldest first
  POST   /api/proposals          body = one proposal; saved as work/mappage/<level>/proposals/<id>.json; returns {id}
  DELETE /api/proposals/<id>     removes that file
  POST   /api/preview            body = {draft: <terrain proposal or null>}: the saved terrain proposals, then the draft,
                                 applied to the built ground; the contract before and after (mappage.preview)
`mappage.py a4 --pull` and `--apply-preview` read the same folder by default.

New-map mode (user 2026-11-04: "地形编辑器升级成能画新地图"): draw a map from nothing, or start from a copy of one.
  python -I -X utf8 experimental/mappage/serve.py --new trial [--size W H] [--from sapporo]
The sketch is work/mappage/<name>/sketch.json (kept when it exists: --size / --from only start a new one); the page
draws it and saves every change:
  GET  /api/sketch               the sketch
  POST /api/sketch               body = the sketch: saved
  POST /api/generate             body = the sketch: saved, then sketch2map.report (the draft module, lint, contract,
                                 walkable regions, the .map and its study); returns the report
  GET  /files/ground.png | regions.png      the pictures the last generate wrote
"""
import argparse
import datetime
import http.server
import importlib.util
import json
import os
import re
import secrets
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('mappage', os.path.join(HERE, 'mappage.py'))
mappage = sys.modules.get('mappage') or importlib.util.module_from_spec(_spec)
if 'mappage' not in sys.modules:
    sys.modules['mappage'] = mappage
    _spec.loader.exec_module(mappage)

ID = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
MAX_BODY = 8 << 20                     # a terrain proposal with many dabs is tens of KB; the limit only stops mistakes


class Level:
    """One level's page, proposals folder and preview base (built once, on first use or in the background)."""

    def __init__(self, name, html, folder=None):
        self.name, self.html = name, html
        self.dir = folder or mappage.proposals_dir(name)
        os.makedirs(self.dir, exist_ok=True)
        self._base, self._ready, self.lock = None, threading.Event(), threading.Lock()
        self._error = None

    def warm(self):
        """Build the preview base (the map build, a few seconds) if nobody has yet."""
        with self.lock:
            if self._base is None and self._error is None:
                try:
                    self._base = mappage.preview_base(self.name)
                except Exception as e:                         # reported to the page, not swallowed
                    self._error = f'{type(e).__name__}: {e}'
            self._ready.set()

    def docs(self):
        out = []
        for f in sorted(os.listdir(self.dir)):
            if f.endswith('.json'):
                try:
                    out.append({'id': f[:-5], 'data': json.load(open(os.path.join(self.dir, f), encoding='utf-8'))})
                except (OSError, ValueError):
                    continue
        return sorted(out, key=lambda d: str(d['data'].get('at', '')) if isinstance(d['data'], dict) else '')

    def add(self, p):
        if not isinstance(p, dict) or not p.get('kind'):
            raise ValueError('a proposal is a JSON object with a kind')
        p = dict(p, level=p.get('level', self.name))
        pid = datetime.datetime.now().strftime('p%Y%m%d-%H%M%S-') + secrets.token_hex(2)
        path = os.path.join(self.dir, pid + '.json')
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(p, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return pid

    def delete(self, pid):
        if not ID.match(pid):
            raise ValueError('bad id')
        path = os.path.join(self.dir, pid + '.json')
        if not os.path.exists(path):
            return False
        os.remove(path)
        return True

    def preview(self, draft=None):
        self.warm()
        if self._error:
            raise RuntimeError(self._error)
        docs = mappage.read_proposals(self.name, self.dir) if os.listdir(self.dir) else []
        docs = [p for p in docs if p['kind'] == 'terrain']
        if isinstance(draft, dict) and draft.get('kind') == 'terrain':
            docs.append(dict(draft, id='正在画的'))
        with self.lock:                                        # lint_on swaps module globals: one at a time
            return mappage.preview(self._base, docs)


def handler(level):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):                    # quiet: one line per write, nothing per read
            if self.command != 'GET':
                sys.stderr.write(f'{self.command} {self.path} -> {args[1] if len(args) > 1 else ""}\n')

        def _send(self, code, body, ctype='application/json; charset=utf-8'):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False, default=str).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get('Content-Length') or 0)
            if n > MAX_BODY:
                raise ValueError('body too large')
            return json.loads(self.rfile.read(n).decode('utf-8') or 'null')

        def _local(self):
            """Only pages of this server may write (a page on another site cannot reach 127.0.0.1 and post here)."""
            origin = self.headers.get('Origin')
            host = self.headers.get('Host', '')
            return origin is None or origin == f'http://{host}'

        def do_GET(self):
            path = self.path.split('?')[0]
            if path in ('/', '/index.html', f'/{level.name}_mappage.html'):
                return self._send(200, open(level.html, 'rb').read(), 'text/html; charset=utf-8')
            if path == '/api/proposals':
                return self._send(200, {'level': level.name, 'docs': level.docs()})
            if path == '/api/ping':
                return self._send(200, {'level': level.name,
                                        'dir': os.path.relpath(level.dir, mappage.ROOT).replace(os.sep, '/')})
            self._send(404, {'error': 'not found'})

        def do_POST(self):
            if not self._local():
                return self._send(403, {'error': 'other origin'})
            path = self.path.split('?')[0]
            try:
                body = self._body()
                if path == '/api/proposals':
                    return self._send(200, {'id': level.add(body)})
                if path == '/api/preview':
                    return self._send(200, level.preview((body or {}).get('draft')))
            except ValueError as e:
                return self._send(400, {'error': str(e)})
            except Exception as e:
                return self._send(500, {'error': f'{type(e).__name__}: {e}'})
            self._send(404, {'error': 'not found'})

        def do_DELETE(self):
            if not self._local():
                return self._send(403, {'error': 'other origin'})
            m = re.match(r'^/api/proposals/([^/?]+)$', self.path)
            if not m:
                return self._send(404, {'error': 'not found'})
            try:
                return self._send(200 if level.delete(m.group(1)) else 404, {'id': m.group(1)})
            except ValueError as e:
                return self._send(400, {'error': str(e)})
    return H


def make_server(level, port=8765):
    """A threading HTTP server for level on 127.0.0.1 (port 0 = any free port)."""
    return http.server.ThreadingHTTPServer(('127.0.0.1', port), handler(level))


SKETCH_PAGE = os.path.join(HERE, 'sketch.html')
FILES = ('ground.png', 'regions.png')


def sketch2map():
    return mappage._load('sketch2map', os.path.join(HERE, 'sketch2map.py'))


class Sketch:
    """One new map's sketch (work/mappage/<name>/sketch.json) and its generate-and-check, one at a time."""

    def __init__(self, name, size=None, src=None, folder=None):
        sk = sketch2map()
        if not re.match(r'^[a-z][a-z0-9_]{0,30}$', name):
            raise ValueError(f'map name {name!r}: lower-case letters, digits and _ (it becomes a module name)')
        self.name, self.lock = name, threading.Lock()
        self.path = os.path.join(folder, 'sketch.json') if folder else sk.sketch_path(name)
        if not os.path.exists(self.path):
            if src:
                mod, names = sk.map_module(src)
                s = sk.from_module(mod, names)
                s['name'] = name
            else:
                s = sk.blank(name, size or (sk.WORLD, sk.WORLD))
            sk.write_sketch(s, self.path)
        self.dir = os.path.dirname(self.path)
        self.with_map = True                                   # tests turn the .map and its study off (seconds)

    def read(self):
        return sketch2map().read_sketch(self.path)

    def save(self, s):
        if not isinstance(s, dict) or s.get('version') != sketch2map().VERSION:
            raise ValueError('a sketch is a JSON object of version 1')
        s = dict(s, name=self.name)
        return sketch2map().write_sketch(s, self.path)

    def generate(self, s):
        self.save(s)
        with self.lock:                                        # contract.map_design, the build: one at a time
            # the engine line's pathfinding model too when it is on this computer (about a second): its "may stop
            # half way" warnings (docs/engine/pathing.md 1) are the page's to show
            return sketch2map().report(self.name, self.read(), with_map=self.with_map, with_pathing=True, out=self.dir)

    def report(self):
        p = os.path.join(self.dir, 'report.json')
        return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None

    def page(self):
        view = open(os.path.join(HERE, 'view.js'), encoding='utf-8').read()
        boot = {'sketch': self.read(), 'online': True, 'report': self.report(),
                'tiers': [sketch2map().platmap.TIER[k] for k in sorted(sketch2map().platmap.TIER)],
                'where': os.path.relpath(self.path, mappage.ROOT).replace(os.sep, '/')}
        html = open(SKETCH_PAGE, encoding='utf-8').read()
        # the boot data inside a <script>: no "</" may close it early
        data = json.dumps(boot, ensure_ascii=False).replace('</', '<\\/')
        return html.replace('/*VIEW_JS*/', view).replace('/*BOOT*/null', data).encode('utf-8')


def sketch_handler(sketch):
    class H(handler(None)):
        def do_GET(self):
            path = self.path.split('?')[0]
            if path in ('/', '/index.html'):
                return self._send(200, sketch.page(), 'text/html; charset=utf-8')
            if path == '/api/sketch':
                return self._send(200, sketch.read())
            if path == '/api/ping':
                return self._send(200, {'sketch': sketch.name})
            if path.startswith('/files/') and path[7:] in FILES:
                p = os.path.join(sketch.dir, path[7:])
                if os.path.exists(p):
                    return self._send(200, open(p, 'rb').read(), 'image/png')
            self._send(404, {'error': 'not found'})

        def do_POST(self):
            if not self._local():
                return self._send(403, {'error': 'other origin'})
            path = self.path.split('?')[0]
            try:
                body = self._body()
                if path == '/api/sketch':
                    sketch.save(body)
                    return self._send(200, {'saved': sketch.name})
                if path == '/api/generate':
                    return self._send(200, sketch.generate(body))
            except ValueError as e:
                return self._send(400, {'error': str(e)})
            except Exception as e:
                return self._send(500, {'error': f'{type(e).__name__}: {e}'})
            self._send(404, {'error': 'not found'})

        def do_DELETE(self):
            self._send(404, {'error': 'not found'})
    return H


def make_sketch_server(sketch, port=8765):
    return http.server.ThreadingHTTPServer(('127.0.0.1', port), sketch_handler(sketch))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name', nargs='?')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-picture', action='store_true', help='page without the picture and terrain (faster)')
    ap.add_argument('--new', metavar='MAP', help='draw a new map (work/mappage/<MAP>/sketch.json) instead of a level')
    ap.add_argument('--size', type=float, nargs=2, metavar=('W', 'H'), help='a new sketch\'s playable area (at most 5000)')
    ap.add_argument('--from', dest='src', metavar='MAP', help='a new sketch copied from maps/<MAP>.py')
    a = ap.parse_args()
    if a.new:
        sketch = Sketch(a.new, a.size, a.src)
        srv = make_sketch_server(sketch, a.port)
        print(f'草图 {os.path.relpath(sketch.path, mappage.ROOT)}', flush=True)
        print(f'打开 http://127.0.0.1:{srv.server_address[1]}/    （Ctrl+C 停止）', flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return
    if not a.name:
        ap.error('give a level (a4 ...) or --new MAP')
    print(f'正在生成 {a.name} 的地图页（构建地图，约十几秒）……', flush=True)
    html, d = mappage.export(a.name, not a.no_picture)
    level = Level(a.name, html)
    threading.Thread(target=level.warm, daemon=True).start()
    srv = make_server(level, a.port)
    print(f'contract: {d["rules"]["show"]}；提议存在 {os.path.relpath(level.dir, mappage.ROOT)}', flush=True)
    print(f'打开 http://127.0.0.1:{srv.server_address[1]}/    （Ctrl+C 停止）', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
