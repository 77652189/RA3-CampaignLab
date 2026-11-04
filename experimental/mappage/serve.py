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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-picture', action='store_true', help='page without the picture and terrain (faster)')
    a = ap.parse_args()
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
