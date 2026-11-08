r"""What the player sees, hears and may do, second by second, read off a simulated run (ADR 0022: the presentation logic).

The plan simulator (sim.py) runs a level's scripts and units; this answers what a player would have in front of them:

  1. the camera  -- where the scripted camera is (a pan takes its seconds), whether the picture shows the black beyond the
                    playable area (K5), which units stand in the picture;
  2. the lines   -- when each caption / subtitle / announcer event comes up, which one was pushed out early, which 功能
                    caption was late (K1), how many sentences were on screen together (strip.py);
  3. the flow    -- when the player's input is locked and when it is handed back, the scenes, the letterbox;
  4. the screen  -- objectives that came up / ticked, counters and countdowns shown (with their value), minimap blips.

It is a *reader*: `ShowSim` is sim.Sim with a few records added (it changes no rule: every action still goes to the
simulator's own `act`), so sim.py / simunits.py stay the engine line's. What the records need from the simulator is
listed in HOOKS below, to go to its owner when they should be native.

  python -I -X utf8 experimental/cnv/simshow.py a4 [--until 200] [--out work/player_timeline/a4.md]

What is NOT modelled (each is a guess or a gap, never a verdict): a pan's easing (taken linear); CAMERA_FOLLOW_NAMED's
300-behind offset (the camera sits on the unit); what the player scrolls to after the scene (the camera is the script's);
the recordings' own lengths and the engine's dialogue queue (a 配音 is logged at its event, its audio is not placed);
fog (what stands in the picture is listed whether or not the player's side sees it).
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import ctx  # noqa: E402
import model  # noqa: E402
import sim  # noqa: E402
import strip  # noqa: E402

BLACK_TOL = 1.0         # map units a picture may stick out of the playable area before it shows black (rounding)
SEEN_FOR_MIN = ctx.FUNC_HOLD    # a caption pushed out sooner than this after it came up was not read (ctx: a 功能 one stays)
BLACK_MIN = 2.0         # seconds a black picture stands before it counts: the mission's first ~1 s show the game's own start
                        # camera until the opening script has run (every level has them: the model's flag chain), and a pan
                        # may graze an edge on its way
CAPTION_ACTION = next(k for k, v in sim.SHOWN.items() if v == '通报')    # the one outlet is the simulator's: not spelt here (G3a)
CAST_LIMIT = 8         # units named in one camera row of the report

# What this reader had to add to the simulator (sim.Sim), for its owner to make native if it wants:
HOOKS = [
    "act(): CAMERA_LETTERBOX_BEGIN / END are in IGNORED and leave no trace; MOVE_CAMERA_TO keeps only the target point "
    "(self.camera), not the pan's seconds, the start point or the time; CAMERA_FOLLOW_NAMED jumps to the unit once and "
    "never follows; CAMERA_STOP_FOLLOW is ignored. The default camera at t=0 is not set.",
    "act(): HIDE_COUNTER is in IGNORED (a shown counter is never taken down in the records); DISPLAY_COUNTER is the "
    "engine model's own (eng.log 'show'), not the simulator's, so Sim.note does not see it.",
    "act(): ENABLE_INPUT / DISABLE_INPUT keep only the last state (Sim.input) plus a note; show_caption forgets the "
    "seconds the script asked for (box_log holds start / end after a replacement).",
]


def mmss(t):
    return sim.mmss(t)


class ShowSim(sim.Sim):
    """sim.Sim that also keeps the presentation records. Nothing here changes a rule: each action is recorded and then
    handed to the simulator's own act."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.moves = []             # (t, from (x, y), to (x, y), secs) -- a scripted pan
        self.follows = []           # (t, name or None): CAMERA_FOLLOW_NAMED / CAMERA_STOP_FOLLOW
        self.bars = [(0.0, False)]  # (t, letterbox on)
        self.locks = [(0.0, True)]  # (t, the player's input is on)
        self.borders = [(0.0, 0)]   # (t, the playable area's index)
        self.asked_caps = []        # (t, text, secs the script asked it up for)
        self.shown_ui = []          # (t, kind, text): counters / countdowns up and down, with their values
        self.shots = []             # (t, centre, half, outside {side: units}, [units in the picture])
        self._up = set()            # counters / countdowns shown now (by label)
        self._read = 0              # how much of the engine model's log is in shown_ui already
        self._value = {}            # a shown counter's last value seen
        start = (getattr(self.m.map, 'SITES', None) or {}).get('start')
        self.cam0 = (float(start.x), float(start.y)) if start is not None else None   # where the game starts looking

    # ---- the records ------------------------------------------------------------------------------------------
    def act(self, name, a, script):
        t = self.t
        if script is not None and script.name.startswith('Test') and 'CAMERA' in name:
            return super().act(name, a, script)        # a check's own harness camera is the bench's, not the level's
        if name == 'MOVE_CAMERA_TO' or name == 'MOVE_CAMERA_TO_NAMED':
            p = self.point(a[0])
            if p:
                secs = float(a[1]) if len(a) > 1 and isinstance(a[1], (int, float)) else 0.0
                self.moves.append((t, self.camera_at(t), (float(p[0]), float(p[1])), secs))
                self.follows.append((t, None))
        elif name == 'CAMERA_FOLLOW_NAMED':
            self.follows.append((t, a[0]))
        elif name == 'CAMERA_STOP_FOLLOW':
            self.follows.append((t, None))
        elif name == 'CAMERA_LETTERBOX_BEGIN':
            self.bars.append((t, True))
        elif name == 'CAMERA_LETTERBOX_END':
            self.bars.append((t, False))
        elif name in ('DISABLE_INPUT', 'ENABLE_INPUT'):
            self.locks.append((t, name == 'ENABLE_INPUT'))
        elif name == 'MAP_SWITCH_BORDER':
            self.borders.append((t, int(a[0])))
        elif name == CAPTION_ACTION:
            self.asked_caps.append((t, self.text(a[0]) if isinstance(a[0], str) else str(a[0]), float(a[1])))
        elif name in ('HIDE_COUNTER', 'HIDE_COUNTDOWN_TIMER'):
            label = self.text(a[0]) if isinstance(a[0], str) else str(a[0])
            if label in self._up:                       # scripts re-hide every frame: one row when it was up
                self._up.discard(label)
                self.shown_ui.append((t, '收起', label))
        super().act(name, a, script)
        if name in ('MOVE_CAMERA_TO', 'MOVE_CAMERA_TO_NAMED', 'CAMERA_LETTERBOX_BEGIN', 'CAMERA_LETTERBOX_END',
                    'MAP_SWITCH_BORDER', 'CAMERA_FOLLOW_NAMED'):
            self.snap(t)

    def step(self):
        super().step()
        eng = self.eng
        if eng is None:
            self.snap(self.t)
            return
        for frame, kind, where, name, a in eng.log[self._read:]:
            if kind == 'show' and name in ('DISPLAY_COUNTER', 'DISPLAY_COUNTDOWN_TIMER'):
                label = self.text(str(a[1]))
                if label not in self._up:
                    self._up.add(label)
                    self.shown_ui.append((frame / self.fps, '亮出' if name == 'DISPLAY_COUNTER' else '倒计时', label))
        self._read = len(eng.log)
        self.snap(self.t)                                 # the picture at each tick (DT) -- what a pan passes through

    def sample(self):
        super().sample()
        eng = self.eng
        if eng is not None:                               # a shown counter's value, when it changes
            for label, counter in eng.displayed.items():
                v = self.counters.get(counter)
                if v is not None and self._value.get(label) != v:
                    first = label not in self._value
                    self._value[label] = v
                    if not first:
                        self.shown_ui.append((self.t, '读数', f'{self.text(str(label))} = {v}'))

    # ---- the camera -------------------------------------------------------------------------------------------
    def camera_at(self, t):
        """Where the scripted camera is at t: the last pan, linear over its seconds, from where it was; a follow sits
        on its unit; before any script the game's own start camera."""
        who = next((n for tt, n in reversed(self.follows) if tt <= t + 1e-9), None)
        if who is not None:
            p = self.point(who)
            if p:
                return (float(p[0]), float(p[1]))
        past = [m for m in self.moves if m[0] <= t + 1e-9]
        if not past:
            return self.cam0
        t0, a, b, secs = past[-1]
        if a is None or secs <= 0 or t - t0 >= secs:
            return b
        f = (t - t0) / secs
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)

    def state_at(self, series, t):
        return next((v for tt, v in reversed(series) if tt <= t + 1e-9), series[0][1])

    def half_at(self, t):
        """The ground (half width, half height) the picture shows: the letterbox band in a scene, the screen in play."""
        return model.LETTERBOX_HALF if self.state_at(self.bars, t) else model.VIEW_HALF

    def playable(self, t):
        names = getattr(self.m.map, 'BORDERS', None)
        if not names:
            return None
        rects = list(names.values())
        i = self.state_at(self.borders, t)
        return rects[i] if i < len(rects) else rects[0]

    def snap(self, t):
        """The picture at t: its centre, what sticks out of the playable area, the units standing in it."""
        c = self.camera_at(t)
        if c is None:
            return
        hx, hy = self.half_at(t)
        rect = self.playable(t)
        out = {}
        if rect:
            for side, over in (('west', rect[0] - (c[0] - hx)), ('north', rect[1] - (c[1] - hy)),
                               ('east', (c[0] + hx) - rect[2]), ('south', (c[1] + hy) - rect[3])):
                if over > BLACK_TOL:
                    out[side] = round(over, 1)
        seen = [(self.label(b) if b.name else b.template, self.who(b.owner)) for b in self.living()
                if not b.scenery and b.owner != sim.CIV and abs(b.x - c[0]) <= hx and abs(b.y - c[1]) <= hy]
        if self.shots and self.shots[-1][0] == t:
            self.shots.pop()
        self.shots.append((t, c, (hx, hy), out, seen))


# ---- the run ----------------------------------------------------------------------------------------------------
def run(name, check='', until=sim.UNTIL, level='normal', script=''):
    """The level (or one of its checks) simulated with the presentation records. Returns the ShowSim."""
    import build
    m, t, _ = build.resolve(name, check)
    return ShowSim(m, t, level, script).run(until)


# ---- the readings -----------------------------------------------------------------------------------------------
def black_runs(s):
    """K5 on the run: [(from t, to t, centre, {side: units})] -- stretches where the picture shows black beyond the
    playable area (a run of consecutive shots, each with something sticking out)."""
    out, open_ = [], False
    for i, (t, c, _, o, _) in enumerate(s.shots):
        end = s.shots[i + 1][0] if i + 1 < len(s.shots) else s.t
        if not o:
            open_ = False
            continue
        if open_:
            r = out[-1]
            r[1] = end
            r[3] = {k: max(v, r[3].get(k, 0)) for k, v in {**r[3], **o}.items()}
        else:
            out.append([t, end, c, dict(o)])
            open_ = True
    return [tuple(r) for r in out if r[1] - r[0] >= BLACK_MIN]     # a cut's first frames are not a picture the player sees


def input_spans(s):
    """The stretches the player cannot act: [(from, to)] (to None: never handed back)."""
    out, lo = [], None
    for t, on in s.locks:
        if not on and lo is None:
            lo = t
        elif on and lo is not None:
            out.append((lo, t))
            lo = None
    if lo is not None:
        out.append((lo, None))
    return out


def first_control(s):
    """When the player first has the controls for good (the last hand-back before the end, or None)."""
    spans = input_spans(s)
    return spans[-1][1] if spans else 0.0


def pushed_out(s, floor=SEEN_FOR_MIN):
    """Captions another one pushed out of the box before `floor` seconds were up: [(t, text, shown, asked)]. A 闲话
    caption waits for the box (ctx), a 功能 one stays FUNC_HOLD at least, so none of the level's own should be here."""
    out = []
    for (t0, t1, text) in s.box_log:
        asked = next((secs for tt, tx, secs in s.asked_caps if abs(tt - t0) < 1e-6 and tx == text), None)
        ends = s.ending is not None and t1 >= s.ending[1] - 2.0       # the ending's own line takes the box
        if asked is not None and not ends and (t1 - t0) < min(asked, floor) - 1e-6:
            out.append((t0, text, round(t1 - t0, 2), asked))
    return out


def late_lines(s):
    """K1 on the run: the 功能 captions that came up later than ctx.FUNC_LATE after their event, or never:
    [(flag, asked at, shown at or None)]. A scene's seconds do not count (sim.late_captions)."""
    return s.late_captions()


def too_many(s):
    """I1 on the run: [(t, sentences on screen)] where more than ctx.STRIP_MAX were up together (strip.py)."""
    return strip.too_deep(s)


def locked_for_good(s):
    """Whether the mission ends (or the run stops) with the player's input still off while nothing is ending."""
    return s.ending is None and not s.input


def problems(s):
    """Everything the run found wrong in what the player sees, as readable lines (empty: nothing)."""
    out = []
    for lo, hi, c, o in black_runs(s):
        out.append(f'K5 {mmss(lo)}~{mmss(hi)}: the picture at ({c[0]:.0f}, {c[1]:.0f}) shows black beyond the playable '
                   f'area ({", ".join(f"{k} {v:g}" for k, v in o.items())} units)')
    for f, a, shown in late_lines(s):
        out.append(f'K1 {mmss(a)}: 功能 caption {f} ' + (f'came up {mmss(shown)}, too late' if shown is not None else
                                                       'never came up (or is still waiting at the end)'))
    for t, text, shown, asked in pushed_out(s):
        out.append(f'K1 {mmss(t)}: caption {text!r} was pushed out after {shown:g} s (asked {asked:g}): not read')
    for t, n in too_many(s):
        out.append(f'I1 {mmss(t)}: {n} sentences on screen at once (max {ctx.STRIP_MAX})')
    if locked_for_good(s):
        out.append(f'flow {mmss(s.t)}: the run ends with the player\'s input still off')
    return out


# ---- the player's timeline --------------------------------------------------------------------------------------
def timeline(s):
    """[(t, kind, text)] in time order: what the player has in front of them and may do."""
    rows = []
    for t, _, to, secs in s.moves:
        sh = next((x for x in s.shots if x[0] >= t - 1e-6), None)
        end = next((x for x in s.shots if x[0] >= t + secs - 1e-6), sh)
        seen = sorted(f'{w}（{o}）' + (f'×{n}' if n > 1 else '')
                      for (w, o), n in collections.Counter(end[4] if end else []).items())
        black = end[3] if end else {}
        rows.append((t, '镜头', f'到 ({to[0]:.0f}, {to[1]:.0f})，{secs:g} 秒' +
                     (f'；取景里：{"、".join(seen[:CAST_LIMIT])}' + ('……' if len(seen) > CAST_LIMIT else '') if seen
                      else '；取景里没有单位') + (f'；黑边 {black}' if black else '')))
    for t, on in s.bars[1:]:
        rows.append((t, '画面', '上下黑条（过场画面）' if on else '黑条收起'))
    for t, on in s.locks[1:]:
        rows.append((t, '操作', '交还给玩家' if on else '锁住，玩家不能动'))
    for t, t1, text in s.box_log:
        rows.append((t, '字幕框', f'{text}（占 {t1 - t:.1f} 秒）'))
    for g in s.panel_log:
        for t, text in g:
            rows.append((t, '对白面板', text))
    for t, k, x in s.log:
        if k in ('配音', '原版播报', '头像', '音乐'):
            rows.append((t, {'配音': '配音', '原版播报': '播报', '头像': '头像', '音乐': '音乐'}[k], x))
        elif k in ('目标', '小地图闪点', '信息框', '边界', '结局'):
            rows.append((t, '界面' if k not in ('边界', '结局') else k, f'{k}：{x}' if k in ('小地图闪点', '信息框') else x))
    for t, k, x in s.shown_ui:
        rows.append((t, '界面', f'计数 {k}：{x}'))
    return sorted(rows, key=lambda r: r[0])


def report(s):
    """The player's timeline as text lines, the problems first."""
    out = [s.ending_line(), '']
    p = problems(s)
    out += ['## 问题（' + str(len(p)) + '）'] + (['- ' + x for x in p] or ['- 没有']) + ['']
    spans = input_spans(s)
    out += ['## 操作', '- 锁住的时段：' + ('、'.join(f'{mmss(a)}~{mmss(b) if b is not None else "一直"}' for a, b in spans)
                                          or '没有'),
            f'- 玩家真正拿到操作：{mmss(first_control(s))}', '- 过场（InScene 旗）：' +
            ('、'.join(f'{mmss(a)}~{mmss(b) if b is not None else "…"}' for a, b in s.scenes) or '没有'), '']
    out += ['## 时间线'] + [f'{mmss(t)} [{k}] {x}' for t, k, x in timeline(s)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--check', default='')
    ap.add_argument('--until', type=float, default=sim.UNTIL)
    ap.add_argument('--level', default='normal', choices=list(sim.LEVELS))
    ap.add_argument('--out', default='', help='write the timeline here as a text file')
    a = ap.parse_args()
    s = run(a.name, a.check, a.until, a.level)
    text = '\n'.join(report(s))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
        print(f'{a.out}: {len(text.splitlines())} lines, {len(problems(s))} problems')
    else:
        print(text)


if __name__ == '__main__':
    main()
