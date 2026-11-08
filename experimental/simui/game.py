r"""The playable simulator's back end (ADR 0024): a level's simulated run that a player drives from the browser.

It changes no rule. `PlaySim` is simshow.ShowSim (itself sim.Sim plus the presentation records) with two readers
added -- the dubbed lines' sound keys, and every script event as it happens (the replay record) -- and the player's
orders are *script events*: a click becomes the tuple sim.parse_script makes of a play script's line (走 / 派 / 攻击 /
放 / 占领 / 生产; a click on the ground is the place '@x,y', model.coord), put on Sim.events at the current tick, so
Sim.happen carries it out exactly as it carries out plays/<level>.txt. `Session.tick` is Sim.run's loop body (step, the
whole second's sample, t + DT) without the quiet stop: a level the player is still playing does not end because
nothing moved for two minutes.

  Session(level)          a fresh run; .command(dict) gives an order, .tick() one DT, .state() what the page draws
  Session.jump(stage)     the level's own play script (plays/<level>.txt) plays to that stage's flag, then the script
                          events still to come are dropped and the player has it
  Session.skip_scene()    as fast as the computer goes until the input is handed back

What a run met and does not model (Sim.unmodeled) and the level's coverage list (simcoverage.census) go to the page.
"""
import math
import os
import re
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CNV = os.path.join(os.path.dirname(HERE), 'cnv')
sys.path[:0] = [p for p in (CNV, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import sim  # noqa: E402
import simshow  # noqa: E402

PLAYS = os.path.join(CNV, 'plays')
REPO = os.path.dirname(os.path.dirname(HERE))
VOICE_DIRS = [os.path.join(HERE, 'voice'), os.path.join(REPO, 'work', 'voice')]   # <key>.wav / .mp3 / .ogg, if any
AUDIO_EXT = ('.wav', '.mp3', '.ogg')
SPEEDS = (0.0, 1.0, 2.0, 4.0, 8.0, -1.0)      # 0 paused, -1 as fast as it goes
TICK_BUDGET = 0.25                             # seconds of wall time one worker turn may spend ticking (as fast)


def at(x, y):
    """The name of a clicked ground point, as a script line can carry it (no spaces, no '#')."""
    return f'@{float(x):.0f},{float(y):.0f}'


class PlaySim(simshow.ShowSim):
    """ShowSim plus what the page needs: the sound key of each dubbed line, every script event as it happened (the
    replay). No rule changes: each action still goes to Sim.act."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.voices = []            # (t, kind, sound key, text): PLAY_SOUND_EFFECT / the announcer's
        self.happened = []          # every script event as Sim.happen carried it out, time as scheduled

    def act(self, name, a, script):
        if name in ('PLAY_SOUND_EFFECT', 'PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT') and a:
            key = a[0] if isinstance(a[0], str) else str(a[0])
            sub = self.text(self.mm.subtitles[key]) if key in getattr(self.mm, 'subtitles', {}) else ''
            self.voices.append((self.t, '配音' if name == 'PLAY_SOUND_EFFECT' else '播报', key, sub or self.text(key)))
        super().act(name, a, script)

    def happen(self, e):
        self.happened.append(tuple(e))
        super().happen(e)


def level_play(level):
    path = os.path.join(PLAYS, f'{level}.txt')
    return path if os.path.isfile(path) else ''


def phase_flags(s):
    """The level's stage flags, in order: CNV_<L>_Phase_<n> as its scripts set them."""
    got = set()
    for sc in s.mm.scripts:
        for a in sc.do or []:
            if a and a[0] == 'SET_FLAG' and re.fullmatch(r'CNV_\w+_Phase_\d+', str(a[1])):
                got.add(str(a[1]))
    return sorted(got, key=lambda f: int(f.rsplit('_', 1)[1]))


def coverage(level):
    """The level's coverage list (simcoverage.census): [{category, name, text, known}], and how many are not
    registered. Nothing is run (the levels are compiled and a probe Sim poked)."""
    import simcoverage
    items = simcoverage.census([level])
    out = [dict(category=i.category, name=i.name, text=i.text, known=simcoverage.match(i) is not None) for i in items]
    return out, sum(1 for i in out if not i['known'])


VOICE_LINE = os.path.join(os.path.dirname(REPO), 'RA3-ChineseVoice', 'work', 'campaign')   # the voice line's takes


def voice_dirs(key):
    """Where a line's recording may be: ours first, then the voice line's takes (zh before en, ADR 0013: the
    dialogue is dubbed once in its side's language; the level's folder, then the language's)."""
    m = re.match(r'CNV_([A-Za-z]+\d+)_', key)
    lv = m.group(1).upper() if m else ''
    out = list(VOICE_DIRS)
    for lang in ('zh', 'en'):
        if lv:
            out.append(os.path.join(VOICE_LINE, lang, lv))
        out.append(os.path.join(VOICE_LINE, lang))
    return out


def find_voice(key):
    if not key or '/' in key or '\\' in key or '..' in key:
        return None
    for d in voice_dirs(key):
        for ext in AUDIO_EXT:
            p = os.path.join(d, key + ext)
            if os.path.isfile(p):
                return p
    return None


class Session:
    """One level being played: the run, the orders, the clock. Thread-safe: every touch of the run holds .lock."""

    def __init__(self, level, difficulty='normal', play=None):
        """play: the script stage jumps play (default plays/<level>.txt; '' none). A run starts with no script."""
        import build
        self.level, self.difficulty = level, difficulty
        self.play = level_play(level) if play is None else play
        self.mission, self.test, _ = build.resolve(level, '')
        self.lock = threading.RLock()
        self.speed = 1.0
        self.busy = ''              # '' or what the worker is doing as fast as it goes (跳过场 / 跳阶段 n)
        self.target = None          # (kind, value) the busy run goes to
        self.orders = []            # (t, event tuple, from the page)
        self.refused = []           # (t, why)
        self.coverage, self.unregistered = None, 0
        self.stage_times = {}       # flag -> t its play script reached it (filled as runs reach them)
        self.new(script='')

    # ---- the run -----------------------------------------------------------------------------------------------
    def new(self, script=''):
        with self.lock:
            self.s = PlaySim(self.mission, self.test, self.difficulty, script)
            self.stages = phase_flags(self.s)
            self.orders, self.refused = [], []
            self.wall0 = time.time()

    def tick(self):
        """One DT, as Sim.run does it (no quiet stop)."""
        with self.lock:
            s = self.s
            if s.ending is not None:
                return False
            s.step()
            if abs(s.t - round(s.t)) < 1e-6:
                s.sample()
            for f in self.stages:
                if f not in self.stage_times and s.flags.get(f) == 1:
                    self.stage_times[f] = s.t
            s.t = round(s.t + sim.DT, 3)
            return True

    def run_to(self, until):
        while self.s.t <= until and self.s.ending is None:
            self.tick()
        return self.s

    # ---- the player's orders: script events --------------------------------------------------------------------
    def command(self, c):
        """An order from the page, as a script event at the current tick. c: {'verb': ..., ...}:
          走   units [names], to [x, y] or a point name             (a plain move)
          派   units, to                                             (attack-move)
          攻击 units, target name
          放   units, ability, to [x, y] or a name                    (a ground power: order_power)
          占领 units, target name
          生产 template, factory name
          line text                                                 (a play script's line, its time or 'now')
        Returns (ok, why)."""
        with self.lock:
            s = self.s
            if s.ending is not None:
                return False, '已经结束'
            verb = c.get('verb')
            if verb == 'line':
                return self._line(c.get('text', ''))
            if not s.input and not c.get('force'):
                return self._refuse('过场中，操作锁住')
            names = [n for n in c.get('units', []) if n in s.bodies and s.bodies[n].alive
                     and s.bodies[n].owner == s.human]
            where = c.get('to')
            if isinstance(where, (list, tuple)):
                where = at(*where)
            evs = []
            if verb in ('派', '走'):
                evs = [(verb, n, where) for n in names if s.bodies[n].speed > 0]
            elif verb == '攻击':
                evs = [('攻击', n, c['target']) for n in names] if c.get('target') in s.bodies else []
            elif verb == '放':
                evs = [('放', n, c['ability'], where) for n in names]
            elif verb == '占领':
                evs = [('占领', n, c['target']) for n in names] if c.get('target') in s.bodies else []
            elif verb == '生产':
                f = s.bodies.get(c.get('factory', ''))
                if f is None or f.owner != s.human:
                    return self._refuse('没有这个工厂')
                evs = [('生产', c['template'], f.name)]
            else:
                return self._refuse(f'不认识的命令 {verb}')
            if not evs:
                return self._refuse('没有能执行这个命令的单位')
            for e in evs:
                self._put((s.t,) + e)
            return True, ''

    def _refuse(self, why):
        self.refused.append((self.s.t, why))
        return False, why

    def _put(self, e):
        s = self.s
        s.events.append(e)
        s.events.sort(key=lambda x: x[0])
        self.orders.append((s.t, e))

    def _line(self, text):
        """A play script's line: 't verb ...' (t: seconds, m:ss, '<flag>+<delta>' or 'now')."""
        text = text.strip()
        if text.startswith('now '):
            text = f'{self.s.t} {text[4:]}'
        try:
            got = sim.parse_script(text)
        except ValueError as err:
            return self._refuse(str(err))
        for e in got:
            if isinstance(e[0], tuple):
                self.s.anchored.append(e)
            elif e[0] is None:
                return self._refuse('全局开关（自动打掉、不打、高地不挡）只能在开局给')
            else:
                self._put(e)
        return True, ''

    # ---- saving time ------------------------------------------------------------------------------------------
    def skip_scene(self):
        """As fast as it goes until the player has the input (and no letterbox)."""
        with self.lock:
            if self.s.input and not self.s.state_at(self.s.bars, self.s.t):
                return False, '现在不在过场里'
            self.busy, self.target = '跳过场', ('input', None)
            return True, ''

    def jump(self, stage):
        """The level's play script plays up to `stage` (index into self.stages) as fast as it goes; then the script's
        events still to come are dropped and the player plays on."""
        with self.lock:
            if not self.play:
                return False, f'{self.level} 没有全程脚本（plays/{self.level}.txt），不能按阶段跳'
            if not 0 <= stage < len(self.stages):
                return False, '没有这个阶段'
            self.new(self.play)
            self.busy, self.target = f'跳到第 {stage + 1} 阶段', ('flag', self.stages[stage])
            return True, ''

    def restart(self):
        with self.lock:
            self.new('')
            self.busy, self.target = '', None
            return True, ''

    def busy_done(self):
        s = self.s
        kind, v = self.target
        if s.ending is not None:
            return True
        if kind == 'input':
            return s.input and not s.state_at(s.bars, s.t)
        if kind == 'flag':
            if s.flags.get(v) == 1:
                s.events.clear()                    # the play script hands over: its orders still to come are dropped
                s.anchored.clear()
                return True
            if not s.events and not s.anchored and not s.pending() and s.t - s.last_change >= sim.QUIET:
                self.refused.append((s.t, f'全程脚本没打到 {v}，停在这里交给玩家'))
                return True
        return False

    def work(self, budget=TICK_BUDGET):
        """One turn of the worker: ticks as the speed asks (or as fast as it goes while busy). Returns the sim
        seconds it ran."""
        t0 = self.s.t
        if self.busy:
            end = time.time() + budget
            with self.lock:
                while time.time() < end:
                    if self.busy_done():
                        self.busy, self.target = '', None
                        break
                    self.tick()
            return self.s.t - t0
        if self.speed == 0 or self.s.ending is not None:
            return 0.0
        if self.speed < 0:
            end = time.time() + budget
            while time.time() < end and self.tick():
                pass
            return self.s.t - t0
        self.tick()
        return self.s.t - t0

    def loop(self, stop):
        """The worker thread: real time x speed (a tick is DT sim seconds)."""
        while not stop.is_set():
            w0 = time.time()
            ran = self.work()
            if ran and self.speed > 0 and not self.busy:
                rest = ran / self.speed - (time.time() - w0)
                if rest > 0:
                    stop.wait(rest)
            elif not ran:
                stop.wait(0.03)

    # ---- what the page draws -----------------------------------------------------------------------------------
    def static(self):
        """What does not change in a run: the ground, the areas, sites, borders, the objectives' texts."""
        import base64
        import numpy as np
        import platmap
        s = self.s
        g = s.ground
        walk, water = g.grids['ground'], g.grids['water']
        z = g.zgrid[:walk.shape[0], :walk.shape[1]]
        lo, hi = float(z.min()), float(z.max())
        shade = ((z - lo) / max(hi - lo, 1.0) * 255).astype(np.uint8)
        kind = np.where(walk, 1, np.where(water, 2, 0)).astype(np.uint8)
        x0, y0 = g.world((0, 0))
        sites = getattr(self.mission.map, 'SITES', {}) or {}
        return dict(
            level=self.level, difficulty=self.difficulty, play=bool(self.play), dt=sim.DT,
            grid=dict(w=int(walk.shape[1]), h=int(walk.shape[0]), x0=x0, y0=y0, step=g.d * platmap.CELL,
                      kind=base64.b64encode(kind.tobytes()).decode(), shade=base64.b64encode(shade.tobytes()).decode()),
            areas=[dict(name=k, pts=[[float(p[0]), float(p[1])] for p in v]) for k, v in s.areas.items()],
            sites=[dict(name=k, x=float(v.x), y=float(v.y), r=float(v.r or 0)) for k, v in sites.items()],
            borders=[[k] + [float(x) for x in v] for k, v in (getattr(self.mission.map, 'BORDERS', None) or {}).items()],
            objectives=[dict(name=o.name, title=s.text(o.title), bonus=bool(o.bonus)) for o in self.mission.objectives],
            stages=self.stages, human=s.human,
            players={k: v for k, v in s.players.items()},
            letterbox=dict(VIEW_HALF=list(simshow.model.VIEW_HALF)),
        )

    def unit(self, b, sees):
        s = self.s
        rel = 'me' if b.owner == s.human else ('foe' if s.enemy(s.human, b.owner) else 'other')
        shape = s.blocks(b)
        u = dict(id=b.name, x=round(b.x, 1), y=round(b.y, 1), o=b.owner, rel=rel, tp=b.template, lb=s.label(b),
                 hp=round(b.health, 1), r=round(b.radius or (30.0 if 'STRUCTURE' in b.kinds else 8.0), 1),
                 k=''.join(c for c, w in (('S', 'STRUCTURE'), ('A', 'AIRCRAFT'), ('I', 'INFANTRY')) if w in b.kinds),
                 mv=b.speed > 0, a=round(b.angle or 0.0, 3))
        if b.scenery:
            u['sc'] = 1
        if shape and len(shape) == 5:
            u['bar'] = [round(shape[3], 1), round(shape[4], 1), round(shape[2], 3)]
        if rel == 'foe' and not sees(b):
            u['fog'] = 1
        if b.status:
            u['st'] = sorted(b.status)
        if rel == 'me':
            own = next((x for x in s.mm.units if x.id == b.template), None)
            if own and own.abilities:
                f = s.frame_now()
                u['ab'] = {k: max(0.0, (b.ready_at.get(v, 0) - f) / s.fps) if s.eng else 0.0
                           for k, v in own.abilities.items()}
            if b.path:
                u['to'] = [round(b.path[-1][0]), round(b.path[-1][1])]
        return u

    def state(self, since=0):
        with self.lock:
            s = self.s
            t = s.t
            seen_cache = {}

            def sees(b):
                k = id(b)
                if k not in seen_cache:
                    seen_cache[k] = s.sees(b.x, b.y, b.surface == 'air')
                return seen_cache[k]
            units = [self.unit(b, sees) for b in s.living()]
            ui = []
            readings = s.eng.readings() if s.eng else {}
            for label in sorted(s._up):
                key = next((k for k in readings if s.text(str(k)) == label), None)
                counter = s.eng.displayed.get(key) if key and s.eng else None
                left = None
                if counter is not None and counter in s.timers:
                    left = max(0.0, s.timers[counter] - t)
                ui.append(dict(label=label, value=readings.get(key), left=left))
            panel = s.panel_at(t) if s.panel_log else []
            letter = bool(s.state_at(s.bars, t))
            unmod = [dict(kind=k[0], name=k[1], n=v['n'], t=v['t'], what=v['what']) for k, v in s.unmodeled.items()]
            import simunits
            offers = [dict(tp=o[0], cost=o[1], secs=o[2]) for o in s.offers(s.human)]
            factories, sold = [], set()
            for f in s.factories(s.human):
                q = s.queues.get(f.name, [])
                menu = set(simunits.menu(f.template, s.own, f.upgrades))
                can = [o for o in offers if o['tp'] in menu]
                sold |= {o['tp'] for o in can}
                factories.append(dict(id=f.name, lb=s.label(f), can=can,
                                      queue=[dict(tp=j['template'], p=round(j.get('progress', 0), 1)) for j in q]))
            if factories:                               # upgrades: bought at whichever structure sells them
                factories[0]['can'] += [o for o in offers if o['tp'] not in sold]
            return dict(
                t=t, clock=sim.mmss(t), speed=self.speed, busy=self.busy, input=bool(s.input), letterbox=letter,
                border=s.state_at(s.borders, t),
                camera=s.camera_at(t), ending=(dict(how=s.ending[0], t=s.ending[1], clock=sim.mmss(s.ending[1]),
                                                     by=s.ending[2]) if s.ending else None),
                units=units, caption=s.box_at(t), panel=panel,
                objectives=[dict(name=k, status=v) for k, v in s.objectives.items() if v],
                counters=ui, money=s.money.get(s.human, 0), unmodeled=unmod,
                voices=[dict(i=i, t=v[0], kind=v[1], key=v[2], text=v[3], file=bool(find_voice(v[2])))
                        for i, v in enumerate(s.voices) if i >= since],
                stages=[dict(flag=f, reached=s.flags.get(f) == 1) for f in self.stages],
                factories=factories, offers=offers,
                refused=[dict(t=a, why=b) for a, b in self.refused[-5:]],
                log=[dict(t=a, k=b, x=c) for a, b, c in
                     [x for x in s.log[-400:] if x[1] in ('目标', '剧本', '技能', '生产', '卡住', '够不着', '结局')][-12:]],
                wall=round(time.time() - self.wall0, 1),
            )

    # ---- the replay ---------------------------------------------------------------------------------------------
    def replay_events(self):
        """Every script event this run carried out, as scheduled (Sim.events tuples): fed to a fresh PlaySim's
        events they make the same run (tests/test_simui.py)."""
        with self.lock:
            return list(self.s.happened)


def replay(level, events, difficulty='normal', until=sim.UNTIL):
    """A fresh run fed `events` (Sim.events tuples), run the way Sim.run runs (the quiet stop included)."""
    import build
    m, t, _ = build.resolve(level, '')
    s = PlaySim(m, t, difficulty, '')
    s.events = sorted(events, key=lambda e: e[0])
    return s.run(until)


def key_times(s):
    """The run's ending and the moments that matter, to compare two runs: the ending, the stage flags, the objectives'
    changes."""
    out = {'ending': (s.ending[0], round(s.ending[1], 3)) if s.ending else None}
    for t, k, x in s.log:
        if k in ('目标', '结局'):
            out.setdefault(f'{k}:{x}', round(t, 3))
    return out
