r"""The playable simulator in the browser (ADR 0024): one command, standard library only.

  python -I -X utf8 experimental/simui/serve.py a4 [--port 8724] [--level normal] [--open]

Then open http://127.0.0.1:8724/ . The page (index.html, one file, canvas) polls /api/state and posts the player's
orders to /api/cmd; game.Session runs the level in a worker thread. Nothing here changes a rule (game.py says how).
"""
import argparse
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402
import sys  # noqa: E402

_spec = importlib.util.spec_from_file_location('simui_game', os.path.join(HERE, 'game.py'))
game = importlib.util.module_from_spec(_spec)       # by file: -I leaves the script's folder off the path, and the G4
sys.modules['simui_game'] = game                    # ratchet allows no new sys.path edit
_spec.loader.exec_module(game)

AUDIO_TYPES = {'.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg'}


class App:
    def __init__(self, level, difficulty):
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.coverage = None                # (items, unregistered) once read
        self.open(level, difficulty)

    def open(self, level, difficulty='normal'):
        with self.lock:
            old = getattr(self, 'thread', None)
            if old:
                self.stop.set()
                old.join(2)
                self.stop = threading.Event()
            self.session = game.Session(level, difficulty)
            self.session.speed = 0.0          # the page starts it (the voices wait for a click: browsers' autoplay)
            self.static = self.session.static()
            self.coverage = None
            self.thread = threading.Thread(target=self.session.loop, args=(self.stop,), daemon=True)
            self.thread.start()
            threading.Thread(target=self.read_coverage, args=(self.session,), daemon=True).start()

    def read_coverage(self, session):
        try:
            got = game.coverage(session.level)
        except Exception as err:            # the list is a help, not a rule: say it could not be read
            got = ([dict(category='覆盖检查', name='读不出', text=repr(err), known=False)], 1)
        if session is self.session:
            self.coverage = got


def levels():
    import build
    return [dict(name=lv, play=bool(game.level_play(lv))) for lv in build.LEVELS]


def make_handler(app):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, ctype='application/json; charset=utf-8'):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode('utf-8')
            elif isinstance(body, str):
                body = body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            s = app.session
            if u.path in ('/', '/index.html'):
                with open(os.path.join(HERE, 'index.html'), 'rb') as f:
                    return self.send(200, f.read(), 'text/html; charset=utf-8')
            if u.path == '/api/static':
                return self.send(200, dict(app.static, levels=levels()))
            if u.path == '/api/state':
                st = s.state(int(q.get('since', ['0'])[0]))
                cov = app.coverage
                st['coverage'] = None if cov is None else dict(items=cov[0], unregistered=cov[1])
                return self.send(200, st)
            if u.path == '/api/replay':
                lines = [' '.join(str(x) for x in e) for e in s.replay_events()]
                return self.send(200, '\n'.join(lines) + '\n', 'text/plain; charset=utf-8')
            if u.path.startswith('/voice/'):
                p = game.find_voice(os.path.basename(u.path[len('/voice/'):]))
                if not p:
                    return self.send(404, {'error': 'no recording'})
                with open(p, 'rb') as f:
                    return self.send(200, f.read(), AUDIO_TYPES.get(os.path.splitext(p)[1], 'application/octet-stream'))
            return self.send(404, {'error': 'not found'})

        def do_POST(self):
            u = urlparse(self.path)
            n = int(self.headers.get('Content-Length') or 0)
            try:
                c = json.loads(self.rfile.read(n) or b'{}')
            except ValueError:
                return self.send(400, {'ok': False, 'why': 'bad json'})
            s = app.session
            if u.path == '/api/cmd':
                ok, why = s.command(c)
            elif u.path == '/api/speed':
                s.speed = float(c.get('speed', 1.0))
                ok, why = True, ''
            elif u.path == '/api/skip':
                ok, why = s.skip_scene()
            elif u.path == '/api/jump':
                ok, why = s.jump(int(c.get('stage', 0)))
            elif u.path == '/api/restart':
                ok, why = s.restart()
            elif u.path == '/api/open':
                app.open(c.get('level', s.level), c.get('difficulty', s.difficulty))
                ok, why = True, ''
            else:
                return self.send(404, {'ok': False, 'why': 'not found'})
            return self.send(200, {'ok': ok, 'why': why})
    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('level', nargs='?', default='a4')
    ap.add_argument('--port', type=int, default=8724)
    ap.add_argument('--level', dest='difficulty', default='normal', choices=('easy', 'normal', 'hard'))
    ap.add_argument('--open', action='store_true', help='open the page in the default browser')
    a = ap.parse_args()
    app = App(a.level, a.difficulty)
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), make_handler(app))
    url = f'http://127.0.0.1:{a.port}/'
    print(f'模拟器 {a.level}：{url}  （Ctrl+C 退出）', flush=True)
    if a.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
