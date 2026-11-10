r"""One test-bench game session driven step by step (the core of bench_mcp.py, the ra3bench MCP server).

run_bench.ps1 runs open loop: a fixed timeline of clicks, then a sheet of shots to read afterwards. Here one
process holds the bench game (work/testbench/RA3, the capture shim's copy), and the agent acts, looks and acts again
(VISTA, arXiv 2610.02200: a mechanical harness that alone advances the game, a lossless frame archive the agent
inspects on demand, notes outside the context). The pieces are run_bench.ps1's, in Python:
  - launch: Data\RA3_1.13.game with the bench SkuDef, windowed 1280x720, -modConfig <mod skudef>
  - menus: nav.py's screens and popups (Tacitus off, the "connection lost" box sends the walk back to step 0)
  - input: posted window messages only (no focus, no real cursor); keys also through the shim's key.req
  - frames: the shim saves shots\<name>.bmp when shots\shot.req names it; each frame is archived as a PNG
  - world <-> screen: calib.py (maps built on CampNew18's island, start camera; after a minimap jump the mapping
    shifts with the view); the minimap draws only the playable area, read off the frame among the borders the cnv
    build lists in cnv_map.json beside the mod
  - the window is parked off the desktop and the game's own audio sessions are muted; a bench slot is held while
    the game runs (slots.py: several games at once, each with its own lock in shared\locks and its own shot folder)

  python -I -X utf8 experimental/testbench/harness.py smoke <mod>     start, one frame, stop (a check without MCP)
"""
import ctypes
import ctypes.wintypes as wt
import datetime
import json
import os
import re
import subprocess
import sys
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import calib  # noqa: E402
import nav  # noqa: E402
import slots  # noqa: E402

BENCH = slots.BENCH
SHOTS = os.path.join(BENCH, 'shots')
# RA3_BENCH_SPEED=<x>: the mission runs x times as fast (the capture shim scales the game's clocks once the menus are
# walked); mission seconds, waits and watches are all in mission time. 1 (default): the shim hooks no clock.
SPEED = float(os.environ.get('RA3_BENCH_SPEED') or 1)
STOP_WAIT = 20      # seconds stop() waits for the killed game to exit before it warns and frees the slot anyway
FRAME_COST = 0.35           # real seconds a watched frame takes: capture, archive, counters (bench 2026-10-27, x8)
RUNS = os.path.join(ROOT, 'work', 'testbench', 'runs')
LOCK = slots.lock_path(1)
MODS = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods')
# engine line D (ADR 0027/0028): a mod whose folder holds ra3ext.allow (a mission with ext=True writes it) starts
# through this launcher, which injects ra3ext.dll; every other start is the plain Popen, as before
EXT_LAUNCH = os.environ.get('RA3EXT_LAUNCH') or os.path.join(ROOT, 'work', 're', 'ext', 'ra3ext', 'bin',
                                                             'ra3ext_launch.exe')
W, H = 1280, 720
AIR_LIFT = 170              # a hovering aircraft is drawn ~170 px above its ground point (select it there)
CAPTION_BOX = (340, 125, 840, 185)     # the military caption (SHOW_MILITARY_CAPTION): where scripts report signals
COUNTER_BOX = (0, 560, 150, 615)       # DISPLAY_COUNTER lines, bottom left (two counters; more grow upwards?)
# hold mode: Esc opens the mission menu (任务菜单) and the mission stands still (bench 2026-10-21: two frames 4 s apart
# identical), Esc again goes on -- so the game only moves while a tool acts or waits, not while the agent thinks.
# The menu is recognised by its title (template cut from that run, work/testbench/nav/pause_menu.png).
MENU_BOX, MENU_TPL, MENU_THR = (175, 20, 335, 62), os.path.join(nav.OUT, 'pause_menu.png'), 18
ABILITY_SLOT = (1135, 628)  # the first ability button of a selected unit

user32 = ctypes.WinDLL('user32', use_last_error=True)
EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]


def windows(pid):
    """[(hwnd, title, visible)] of the process's top-level windows."""
    out = []

    def each(h, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid:
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, buf, 256)
            out.append((h, buf.value, bool(user32.IsWindowVisible(h))))
        return True
    user32.EnumWindows(EnumProc(each), 0)
    return out


def main_window(pid):
    return next((h for h, _, vis in windows(pid) if vis), None)


CRASH_TITLES = ('Game crash', 'DirectX错误', 'DirectX Error')
DEVICE_HINT = ('the game could not make its Direct3D device (D3DERR_DEVICELOST in shots/cnv_testbench.log): '
               'another program holds the screen in exclusive fullscreen -- bench 2026-10-24: the user playing '
               'another game -- or the display is off / locked; try again once it is free')


def crash_box(pid):
    """The game's own fatal-error box ("Game crash", or the DirectX one it shows when it gets no Direct3D device):
    its texts, or None."""
    for h, title, _ in windows(pid):
        if title in CRASH_TITLES:
            texts = []

            def each(c, _):
                buf = ctypes.create_unicode_buffer(2048)
                user32.GetWindowTextW(c, buf, 2048)
                texts.append(buf.value)
                return True
            user32.EnumChildWindows(h, EnumProc(each), 0)
            text = ' | '.join(t for t in texts if t)
            return f'{title}: {text}' + (f' -- {DEVICE_HINT}' if title != 'Game crash' else '')
    return None


def boxes(pid):
    """[(title, [its texts])] of the process's visible standard dialog boxes (top-level, class #32770): a message
    box the game put up -- "Steam: Failed to initialize Steam", a crash box -- which no captured frame shows (with no
    Direct3D device yet there are no frames at all, and the parked window is off screen)."""
    out = []

    def each(h, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value != pid or not user32.IsWindowVisible(h):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls, 256)
        if cls.value != '#32770':
            return True
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, title, 256)
        texts = []

        def child(c, _):
            buf = ctypes.create_unicode_buffer(2048)
            user32.GetWindowTextW(c, buf, 2048)
            if buf.value.strip():
                texts.append(buf.value.strip())
            return True
        user32.EnumChildWindows(h, EnumProc(child), 0)
        out.append((title.value, texts))
        return True
    user32.EnumWindows(EnumProc(each), 0)
    return out


STEAM_HINT = ('Steam is not ready (bench 2026-11-08: right after boot its library never got ready -- '
              'steamui_login.txt "Timed out waiting for library ready"): restart Steam, '
              'python -I -X utf8 experimental/testbench/doctor.py checks it')
BOX_WAIT = 10       # seconds a box stays up in the menu walk before it is the error (a passing one may close itself)
BUTTONS = {'OK', 'Cancel', 'Yes', 'No', 'Retry', 'Abort', 'Ignore', '确定', '取消', '是', '否', '重试'}


def box_error(found):
    """The bench error for dialog boxes `found` (boxes(pid)), or None when there are none: each box's title and its
    texts without the buttons, plus what to do when it is Steam's."""
    if not found:
        return None
    said = '; '.join(f'{title or "(untitled)"}: ' + ' | '.join(t for t in texts if t not in BUTTONS)
                     for title, texts in found)
    hint = f' -- {STEAM_HINT}' if 'steam' in said.lower() else ''
    return f'the game put up a box: {said}{hint}'


def lp(x, y):
    return (int(y) << 16) | (int(x) & 0xFFFF)


def post(h, msg, w, l):
    user32.PostMessageW(h, msg, w, l)


def click(h, x, y, right=False):
    down, up, mk = (0x0204, 0x0205, 2) if right else (0x0201, 0x0202, 1)
    post(h, 0x0200, 0, lp(x, y)); time.sleep(0.06)
    post(h, down, mk, lp(x, y)); time.sleep(0.06)
    post(h, up, 0, lp(x, y))


def drag(h, x1, y1, x2, y2):
    """Box selection: button down at (x1, y1), moves with the button held, up at (x2, y2)."""
    post(h, 0x0200, 0, lp(x1, y1)); time.sleep(0.06)
    post(h, 0x0201, 1, lp(x1, y1)); time.sleep(0.06)
    for k in range(1, 9):
        post(h, 0x0200, 1, lp(x1 + (x2 - x1) * k / 8, y1 + (y2 - y1) * k / 8)); time.sleep(0.04)
    post(h, 0x0202, 0, lp(x2, y2))


def key(h, vk):
    """WM_KEYDOWN / WM_KEYUP after telling the game it is active (it drops keys otherwise); the shim also makes the
    key read as held for 300 ms (the game polls GetAsyncKeyState)."""
    sc = user32.MapVirtualKeyW(vk, 0) << 16
    post(h, 0x001C, 1, 0); post(h, 0x0006, 1, 0); post(h, 0x0007, 0, 0)
    time.sleep(0.1)
    post(h, 0x0100, vk, sc | 1); time.sleep(0.08)
    post(h, 0x0101, vk, 0xC0000001 | sc)
    with open(os.path.join(SHOTS, 'key.req'), 'w', encoding='ascii') as f:
        f.write(str(vk))


def park(h):
    """Out of sight, not minimized (a minimized D3D9 window stops presenting)."""
    user32.SetWindowPos(h, 0, -4000, -4000, 0, 0, 0x0001 | 0x0004 | 0x0010)


def mute(pid):
    """Mute only this process's audio sessions; how many are muted."""
    try:
        from pycaw.pycaw import AudioUtilities
        n = 0
        for s in AudioUtilities.GetAllSessions():
            if s.Process and s.Process.pid == pid:
                s.SimpleAudioVolume.SetMute(1, None)
                n += 1
        return n
    except Exception:           # no pycaw, or COM trouble: sound stays on, nothing else breaks
        return 0


def game_running():
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    return bool(re.search(r'\bra3(_1\.\d+\.game|\.exe|ep1)', out))


def lock_holder():
    """Who holds the shared bench lock now (reslock's rule), or None."""
    if not os.path.exists(LOCK):
        return None
    with open(LOCK, encoding='utf-8-sig') as f:
        held = json.load(f)
    if held.get('until'):
        live = datetime.datetime.fromisoformat(held['until']) > datetime.datetime.now()
    else:
        live = bool(re.search(rf'\b{held.get("pid")}\b', subprocess.run(
            ['tasklist', '/FI', f'PID eq {held.get("pid")}'], capture_output=True, text=True, errors='replace').stdout))
    return held if live else None


def skudef(mod):
    if mod.lower().endswith('.skudef'):
        return mod
    return os.path.join(MODS, mod, f'{mod}_1.0.skudef')


def map_borders(sku, chapter=None):
    """The built map's borders [(name, (x0, y0, x1, y1))] from the sidecar the cnv build leaves next to the mod
    (cnv/parts.write_sidecar); a shell with several levels: chapter `chapter`'s map (the sidecar's 'levels'); [] for a
    mod without one (older builds, the campaign makers: the whole map)."""
    try:
        with open(os.path.join(os.path.dirname(sku), 'cnv_map.json'), encoding='utf-8') as f:
            side = json.load(f)
        side = side.get('levels', {}).get(str(chapter), side)
        # empty ones left out: the island's container keeps retail leftovers like (5010, 5010, 5010, 5010), and
        # a zero-size area divided the minimap fit by zero (bench 2026-10-27, the units line's bench_camera)
        return [(n, tuple(r)) for n, r in side['borders'] if r[2] > r[0] and r[3] > r[1]]
    except (OSError, ValueError, KeyError):
        return []


# The plain game (no -modConfig) walks nav.json into the first Allied mission; its map, read for borders and terrain.
RETAIL_DEFAULT = 'camp_a01_brightonbeach_smith'


def retail_borders(name):
    """A retail campaign map's borders [(name, (x0, y0, x1, y1))] in world units (the same as map_borders gives for a
    built map): read from the map in the game's MapsCampaign.big by name; [] where it cannot be read."""
    try:
        maprender = calib._load_file('maprender', os.path.join(calib.ROOT, 'experimental', 'campaign', 'maprender.py'))
        hm = sys.modules['mapterrain'].HeightMap(maprender.load(name))
        cell = sys.modules['mapterrain'].CELL
        return [(str(k), tuple(v * cell for v in r)) for k, r in enumerate(hm.borders()) if r[2] > r[0] and r[3] > r[1]]
    except (Exception, SystemExit):
        return []


def shell_slot(sku):
    """The campaign shell's slot a check build rides on (cnv build.py --shell --check: the sidecar's 'slot'), else None."""
    try:
        with open(os.path.join(os.path.dirname(sku), 'cnv_map.json'), encoding='utf-8') as f:
            return json.load(f).get('slot')
    except (OSError, ValueError):
        return None


def chapter_step(slot):
    """The chapter list (title bar template cut from a frame of it: work/testbench/nav/step_chapters.png): its `slot`-th row,
    then Proceed. The rows are 20.7 px apart from y 263 (1280 x 720 frame)."""
    return {'name': f'chapter list: slot {slot}', 'how': 'tpl', 'box': [190, 28, 360, 68], 'threshold': 18,
            'template': 'step_chapters.png',
            'actions': [['click', 640, round(262.7 + 20.7 * (slot - 1))], ['wait', 0.6], ['click', 875, 676]]}


def shell_steps(slot):
    """nav.json's way into a mission, through the campaign shell's chapter list to `slot` instead of the faction menu:
    main menu, the campaign submenu's chapter button, the chapter list, then nav.json's briefing video, world map and
    mission briefing into the game (testbench/shell_shots.py --tour overview --slot walks the same)."""
    with open(os.path.join(nav.OUT, 'nav.json'), encoding='utf-8') as f:
        steps = json.load(f)
    return [steps[0], dict(steps[1], actions=[['click', 375, 426]]), chapter_step(slot)] + steps[3:]


# The faction select screen's three cards (1280 x 720 frame, 2026-11-08): Soviet left, Allied middle, Empire right.
FACTION_X = {'s': 360, 'a': 637, 'j': 907}


def faction_steps(letter):
    """nav.json's way into the FIRST mission of a faction (the plain game's campaign is linear: only mission 1 of each
    faction can be walked into; later ones need a campaign shell): the faction card clicked is `letter` (s Soviet,
    a Allied, j Empire; the retail map names camp_<letter>01_...). The steps after it are the same screens."""
    with open(os.path.join(nav.OUT, 'nav.json'), encoding='utf-8') as f:
        steps = json.load(f)
    acts = [['click', FACTION_X[letter], 315]] + steps[2]['actions'][1:]
    last = dict(steps[-1], template=f'step8_{letter}.png') if letter != 'a' else steps[-1]   # the HUD's faction emblem
    return steps[:2] + [dict(steps[2], actions=acts)] + steps[3:-1] + [last]


def seen_step(steps, frame, at, back=False):
    """A menu step other than `at` that the frame shows, the furthest first; earlier ones only with back=True (after a
    "connection lost" box). Template steps only: the video's brightness steps match any bright screen, the mission's
    too. None if none (bench 2026-10-27: the walk sent back to the main menu waited there with the mission running)."""
    for j in range(len(steps) - 1, -1, -1):
        if j != at and (j > at or back) and steps[j]['how'] == 'tpl' and \
                nav.matches(steps[j], nav.metric(frame, steps[j])):
            return j
    return None


class BenchError(RuntimeError):
    pass


def ext_wanted(args):
    """True when the game args carry -modConfig <skudef> and that skudef's folder holds ra3ext.allow (engine line D,
    ADR 0028: the same rule ra3ext_launch injects by). Off for every mod that does not write the file."""
    if '-modConfig' not in args or args.index('-modConfig') + 1 >= len(args):
        return False
    return os.path.isfile(os.path.join(os.path.dirname(args[args.index('-modConfig') + 1]), 'ra3ext.allow'))


def ext_command(args, log):
    """The launcher's command line for the game command `args`: ra3ext_launch [opts] -- <game> <args...>."""
    return [EXT_LAUNCH, '--log', log, '--cwd', BENCH, '--verify-ms', '15000', '--'] + list(args)


def parse_launch(text):
    """{pid, inject, reason, dll_loaded} from the launcher's one line 'pid=<n> inject=<yes|no> reason=<...> ...'."""
    line = next((x for x in text.splitlines() if x.startswith('pid=')), '')
    return dict(m.groups() for m in re.finditer(r'(\w+)=(.*?)(?= \w+=|$)', line))


def ext_summary(path):
    """One line on ra3ext's log: 'ra3ext: <status>; N create, M update (log)', or None without a log."""
    if not path or not os.path.isfile(path):
        return None
    lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    status = next((x.split(': ', 1)[-1] for x in lines if x.startswith('ra3ext loaded')), 'no load line')
    creates = sum(x.startswith('create ') for x in lines)
    updates = sum(x.startswith('update ') for x in lines)
    return f'ra3ext: {status}; {creates} create, {updates} update ({path})'


class GameProcess:
    """The bits of Popen the Session uses (pid, poll, returncode, kill, wait) for a game another program started (the
    ra3ext launcher). A game already gone when opened polls as exited, code -1."""
    _k32 = ctypes.WinDLL('kernel32', use_last_error=True) if os.name == 'nt' else None

    def __init__(self, pid):
        self.pid, self.returncode = pid, None
        k = self._k32
        k.OpenProcess.restype = wt.HANDLE
        self._h = k.OpenProcess(0x00100000 | 0x0001 | 0x1000, False, pid)  # SYNCHRONIZE | TERMINATE | QUERY_LIMITED
        if not self._h:
            self.returncode = -1

    def poll(self):
        if self.returncode is None and self._k32.WaitForSingleObject(wt.HANDLE(self._h), 0) == 0:
            code = wt.DWORD()
            self._k32.GetExitCodeProcess(wt.HANDLE(self._h), ctypes.byref(code))
            self.returncode = code.value
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            ms = 0xFFFFFFFF if timeout is None else int(timeout * 1000)
            if self._k32.WaitForSingleObject(wt.HANDLE(self._h), ms) != 0:
                raise subprocess.TimeoutExpired('game', timeout)
        return self.poll()

    def kill(self):
        if self.poll() is None:
            self._k32.TerminateProcess(wt.HANDLE(self._h), 1)


class Session:
    """The one bench game. start() -> act / frame -> ... -> stop(). Frames go to work/testbench/runs/<mod>_mcp_<time>/
    as 0001.png ... with index.json (id, mission second, note)."""

    def __init__(self):
        self.p = None
        self.slot = None            # the bench slot held (slots.py) while a game runs
        self.mod = None
        self.run_dir = None
        self.ext_log = None         # ra3ext's log in the run folder, while a game started through ra3ext_launch
        self.frames = []
        self.t0 = None              # mission start (time.monotonic)
        self.view = None            # None: the start camera; else the world point the last minimap jump centred
        self.shift = (0.0, 0.0)     # screen pixels the view's point stands off the minimap-jump calibration (scripted_view)
        self._ground = None         # the mod's terrain (calib.Ground), read at the first world click; False: unreadable
        self.map_name = None        # the retail map a plain game plays (RETAIL_DEFAULT), None with a mod
        self.borders = []         # the built map's playable areas (cnv_map.json beside the mod), [] the whole map
        self.last_border = None
        self.log = []
        self.muted = 0
        self.hold = False           # pause (Esc menu) between steps
        self.paused = False
        self.game_s = 0.0           # mission seconds run before the current running stretch
        self.run_from = None        # when the current running stretch began (time.monotonic), None while paused
        self.rate = 1.0             # the speed the mission runs at now: x1 till speed_up
        self.boxes = boxes          # pid -> the game's dialog boxes (a stand-in in tests)

    # -- life cycle -------------------------------------------------------------------------------------------
    def start(self, mod, visible=False, timeout=150, hold=True, steps=None, chapter=None, menu_frames=0.0,
              retail_map=None):
        """mod None: the plain game (no -modConfig); its map is `retail_map` (default: RETAIL_DEFAULT, the first
        Allied mission nav.json walks into): the borders and terrain are read from it and the camera fitted for it
        (calib.set_profile) is used. steps: nav steps to walk instead of nav.json's way into the CNV
        mission, e.g. nav.json's first step without its click to stop on the main menu (skirmish by hand). A build on
        the campaign shell (its sidecar names a slot) walks the chapter list into that slot (shell_steps), or into
        `chapter` (1..9) when given (I18: the release shell carries every level, cnv build.py campaign --shell).
        menu_frames > 0 (I22): also archive the walk itself -- a half-size frame every `menu_frames` seconds and one
        of each menu step before its click (chapter list, briefing cards, mission briefing, the opening cutscene till
        the HUD is up), as ordinary frames with second None and note "menu: <step>", so bench_inspect reads them."""
        if self.p and self.p.poll() is None:
            raise BenchError(f'a session is running ({self.mod}): stop it first')
        sku = skudef(mod) if mod else 'RA3'
        if mod and not os.path.exists(sku):
            raise BenchError(f'no such mod: {sku}')
        if chapter and not (mod and shell_slot(sku)):
            raise BenchError(f'{mod} is no campaign shell build (its cnv_map.json names no slot): no chapter to pick')
        chapter = chapter or (shell_slot(sku) if mod else None)
        if steps is None and chapter:
            steps = shell_steps(chapter)
        if steps is None and not mod and (retail_map or '')[:6] in ('camp_s', 'camp_j') and retail_map[6:8] == '01':
            steps = faction_steps(retail_map[5])        # the Soviet / Empire campaign's first mission
        slot = slots.take_waiting('RA3-CampaignLab ra3bench', sku)     # queues while other bench games hold all
        foreign = slots.foreign_games()
        if foreign:
            if slot is not None:
                slots.release(slot)
            raise BenchError(f'an RA3 process the bench did not start is running (pid {", ".join(map(str, foreign))}: '
                             'the user playing, or an older tool): not starting')
        if slot is None:
            held = slots.holders()
            raise BenchError('bench locked by ' + '; '.join(f'{h.get("owner")} (pid {h.get("pid")}) {h.get("note", "")}'
                                                            for h in held.values())
                             + f' -- all {slots.SLOTS} slots, still after {slots.WAIT:.0f} s in the queue')
        global LOCK, SHOTS          # one session per process: the slot's lock and shot folder for this game
        self.slot, LOCK, SHOTS = slot, slots.lock_path(slot), slots.shots_dir(slot)
        os.makedirs(SHOTS, exist_ok=True)
        for n in os.listdir(SHOTS):
            if os.path.isfile(os.path.join(SHOTS, n)):
                os.remove(os.path.join(SHOTS, n))
        self.mod = os.path.splitext(os.path.basename(sku))[0].replace('_1.0', '')
        self.run_dir = os.path.join(RUNS, f'{self.mod}_mcp_{datetime.datetime.now():%m%d_%H%M%S}')
        os.makedirs(self.run_dir)
        self.frames, self.view, self.log, self.muted, self.t0 = [], None, [], 0, None
        self.shift = (0.0, 0.0)
        self._ground = None
        self.map_name = None if mod else (retail_map or RETAIL_DEFAULT)
        if not mod and not calib.set_profile(self.map_name):
            self._say(f'no camera fitted for {self.map_name} (calib.py fit_retail): world clicks are not to be trusted')
        elif mod:
            calib.set_profile(None)
        self.borders = map_borders(sku, chapter) if mod else retail_borders(self.map_name)
        self.last_border = self.borders[0] if self.borders else None
        self.hold, self.paused, self.game_s, self.run_from, self.rate = hold, False, 0.0, None, 1.0
        args = [os.path.join(BENCH, 'Data', 'RA3_1.13.game'), '-config', os.path.join(BENCH, 'RA3_chinese_t_1.13.SkuDef'),
                '-runver', '1.13', '-win', '-xres', str(W), '-yres', str(H)] + (['-modConfig', sku] if mod else [])
        try:
            self._launch(args)
            self._walk_menus(visible, timeout, steps, menu_frames)
        except BaseException:
            self.stop()
            raise
        return dict(mod=self.mod, pid=self.p.pid, run_dir=self.run_dir, log=self.log[-12:])

    def _launch(self, args, tries=5):
        """Start the game in this slot and close its one-copy mutex, so the next copy can start. A copy that exits
        at once found another one's mutex (a game still starting): wait a little and start again."""
        env = dict(os.environ, CNV_SHOT_DIR=SHOTS)
        env.pop('CNV_SPEED', None)
        if SPEED != 1:
            env['CNV_SPEED'] = '1'          # clocks hooked, the menus and videos at x1; the mission sped up in game
        for _ in range(tries):
            self.p = self._start(args, env)
            slots.note_game(self.slot, self.p.pid)
            for _ in range(60):
                time.sleep(0.5)
                if self.p.poll() is not None:
                    break
                if slots.free_instance(self.p.pid):
                    self._say(f'slot {self.slot}: game {self.p.pid} up, its one-copy mutex closed')
                    return
            else:
                self._say(f'slot {self.slot}: game {self.p.pid} up, no one-copy mutex found in 30 s')
                return
            self._say(f'slot {self.slot}: game exited at once (code {self.p.returncode}): another copy starting')
            time.sleep(3)
        raise BenchError(f'the game would not start next to the other bench games ({tries} tries)')

    def _start(self, args, env):
        """The game's process: Popen, or -- for a mod that asks for ra3ext (ext_wanted) -- the launcher's child, held
        as a GameProcess (the launcher prints the game's pid and exits). ra3ext's log goes to the run folder."""
        self.ext_log = None
        if not ext_wanted(args):
            return subprocess.Popen(args, cwd=BENCH, env=env)
        if not os.path.isfile(EXT_LAUNCH):
            raise BenchError(f'the mod asks for ra3ext (ra3ext.allow) but {EXT_LAUNCH} is missing: build.bat in '
                             'work/re/ext/ra3ext')
        self.ext_log = os.path.join(self.run_dir, 'ra3ext.log')
        r = subprocess.run(ext_command(args, self.ext_log), capture_output=True, text=True, errors='replace', env=env,
                           timeout=60)
        got = parse_launch(r.stdout)
        self._say(f'ra3ext_launch: {r.stdout.strip()} {r.stderr.strip()}'.strip())
        if 'pid' not in got:
            raise BenchError(f'ra3ext_launch gave no game (rc {r.returncode}): {r.stdout.strip()} {r.stderr.strip()}')
        if got.get('inject') != 'yes' or got.get('dll_loaded') != 'yes':
            GameProcess(int(got['pid'])).kill()
            raise BenchError(f'ra3ext not in the game: {r.stdout.strip()}')
        return GameProcess(int(got['pid']))

    def _say(self, s):
        self.log.append(s)

    def _walk_menus(self, visible, timeout, steps=None, every=0.0):
        if steps is None:
            with open(os.path.join(nav.OUT, 'nav.json'), encoding='utf-8') as f:
                steps = json.load(f)
        at, done_at, parked, t = 0, 0, False, time.monotonic()
        lost = False                    # a "connection lost" box was answered: the screen may be any step now
        kept = None                     # when the last walk frame was archived (every > 0)
        boxed = None                    # since when a dialog box of the game's has been up
        while True:
            time.sleep(1)
            s = round(time.monotonic() - t)
            self._alive()
            # A Windows box (Steam failed, ...) blocks the game before any menu: no frame ever shows it, so ask the
            # windows. Up BOX_WAIT s in a row: report it instead of waiting the whole timeout out as "menus stuck".
            box = box_error(self.boxes(self.p.pid))
            boxed = (boxed if boxed is not None else s) if box else None
            if box and s - boxed >= BOX_WAIT:
                raise BenchError(f'{box} (up {s - boxed} s, menus at "{steps[at]["name"]}")')
            if s > timeout:             # here, not only after a frame: with no frames at all it never got there
                raise BenchError(box or f'menus stuck at "{steps[at]["name"]}" after {s} s '
                                        f'(see {self.run_dir}\\nav_last.bmp)')
            h = main_window(self.p.pid)
            if h is None:
                continue
            if not visible and not parked:
                park(h); parked = True
            if self.muted == 0 or s % 5 == 0:
                self.muted = max(self.muted, mute(self.p.pid))
            frame = self._capture('nav', bmp=True)
            if frame is None:
                continue
            pop = nav.popup(frame)
            matched = not pop and nav.matches(steps[at], nav.metric(frame, steps[at]))
            if every and (matched or kept is None or time.monotonic() - kept >= every):
                name = 'opening cutscene (waiting for the HUD)' if at == len(steps) - 1 and not matched \
                    else steps[at]['name']
                self.keep_walk(frame, name + (' (before its keys)' if matched else ''), s)
                kept = time.monotonic()
            if pop:
                name, (x, y) = pop
                self._say(f'popup {name} at {s} s: click {x},{y}')
                click(h, x, y)
                if name == 'connection lost':        # often back to the main menu, but it also came up in the
                    lost, done_at = True, s          # mission (bench 2026-10-27): walk on from what the screen shows
            elif matched:
                self._say(f'menu {at} {steps[at]["name"]} at {s} s')
                self._do(h, steps[at]['actions'])
                at, done_at = at + 1, s
                if at == len(steps):
                    self.t0 = self.run_from = time.monotonic()      # at x1 till a tool first runs it (speed_up)
                    self._say(f'in game at {s} s')
                    os.replace(frame, os.path.join(self.run_dir, 'nav_last.bmp'))
                    return              # running: the caller archives a first frame, then pauses (hold mode)
            elif at and s - done_at >= 3 and steps[at - 1]['how'] == 'tpl' and \
                    nav.matches(steps[at - 1], nav.metric(frame, steps[at - 1])):
                self._say(f'menu retry {at - 1} at {s} s')        # its click was swallowed: again
                self._do(h, steps[at - 1]['actions'])
                done_at = s
            else:
                j = seen_step(steps, frame, at, lost)
                if j is not None:
                    self._say(f'menu {j} {steps[j]["name"]} on screen at {s} s (was at {at}): walking on from it')
                    at, lost = j, False
            os.replace(frame, os.path.join(self.run_dir, 'nav_last.bmp'))

    def _do(self, h, actions):
        for a in actions:
            if a[0] == 'click':
                click(h, a[1], a[2])
            elif a[0] == 'key':
                key(h, a[1])
            elif a[0] == 'wait':
                time.sleep(a[1])
            time.sleep(0.25)

    def stop(self, wait=STOP_WAIT):
        """Kill this session's own game (its pid only, never another line's) and free the slot. A game that has not
        exited after `wait` seconds is a warning in the reply (dict 'warning'), not an exception: bench 2026-11-10 a
        TimeoutExpired here lost a check's readings and verdict (engine_sweepoff, B's run the same night)."""
        warning = None
        if self.p and self.p.poll() is None:
            self.p.kill()
            try:
                self.p.wait(wait)
            except subprocess.TimeoutExpired:
                warning = f'game pid {self.p.pid} still up {wait} s after kill (left to exit by itself)'
                self._say(warning)
        if self.slot:
            slots.release(self.slot)
            self.slot = None
        r = dict(mod=self.mod, frames=len(self.frames), run_dir=self.run_dir)
        if warning:
            r['warning'] = warning
        return r

    def _alive(self):
        if self.p is None:
            raise BenchError('no session: start one')
        box = crash_box(self.p.pid)
        if box:
            self.stop()
            raise BenchError(f'game crash box: {box}')
        if self.p.poll() is not None:
            code = self.p.returncode
            self.stop()
            raise BenchError(f'game exited (code {code})')

    def window(self):
        self._alive()
        if self.t0 is None:
            raise BenchError('not in the mission yet')
        h = main_window(self.p.pid)
        if h is None:
            raise BenchError('no game window')
        return h

    def second(self):
        """Mission seconds the game has run (the paused stretches left out)."""
        if self.t0 is None:
            return None
        return round(self.game_s + ((time.monotonic() - self.run_from) * self.rate if self.run_from else 0), 1)

    def run_for(self, seconds):
        """Let the mission run `seconds` of mission time (real time / the rate it runs at)."""
        time.sleep(max(0.0, seconds) / self.rate)

    def speed_up(self, every=None):
        """Run the mission at SPEED from now on -- slower when frames are wanted every `every` mission seconds and a
        frame and its counters (~FRAME_COST real seconds) would take longer than that at SPEED. Not at once in the
        mission: the first frame and the hold pause after it take ~1 s of real time, at x8 the first 8 s of the
        mission went by unseen (bench 2026-10-27: a8 jump and liberty open expect readings from s0)."""
        rate = SPEED if every is None else max(1.0, min(SPEED, every / FRAME_COST))
        if self.rate == rate or self.run_from is None:
            return
        now = time.monotonic()
        with open(os.path.join(SHOTS, 'speed.req'), 'w', encoding='ascii') as f:
            f.write(f'{rate:g}')        # the shim reads it within 0.1 s
        self.game_s += (now - self.run_from) * self.rate
        self.run_from, self.rate = now, rate
        self._say(f'mission at x{rate:g} from second {self.second()}')

    def menu_open(self, img):
        a = img.convert('L').crop(MENU_BOX).tobytes()
        b = Image.open(MENU_TPL).tobytes()
        return sum(abs(x - y) for x, y in zip(a, b)) / len(a) < MENU_THR

    def pause(self):
        """Hold mode: open the mission menu (the mission stands still); checked on a frame, retried once."""
        if not self.hold or self.paused:
            return
        # the clock stops / starts at the Esc that worked, not after the check: resume started it after its 0.4 s
        # and a frame, while the mission was already running -- ~0.4 mission s lost per pause, a run paused every
        # 1.4 s counted 15 s for 19.5 (bench 11-09, movie_pause_probe.py: 19.5 counter frames a 'second', 15 unpaused)
        h = self.window()
        for _ in range(2):
            pressed = time.monotonic()
            key(h, 0x1B)
            time.sleep(0.5)
            img = self._capture('hold')
            if img is not None and self.menu_open(img):
                self.game_s += (pressed - self.run_from) * self.rate
                self.paused, self.run_from = True, None
                return
        raise BenchError('Esc did not open the mission menu (a targeting cursor or a dialog in the way?)')

    def resume(self):
        """Before acting: close the mission menu (hold mode); the mission runs at SPEED from here."""
        if not self.paused:
            self.speed_up()
            return
        h = self.window()
        for _ in range(2):
            pressed = time.monotonic()
            key(h, 0x1B)
            time.sleep(0.4)
            img = self._capture('hold')
            if img is not None and not self.menu_open(img):
                self.paused, self.run_from = False, pressed
                self.speed_up()
                return
        raise BenchError('Esc did not close the mission menu')

    # -- frames -----------------------------------------------------------------------------------------------
    def _capture(self, name, bmp=False, timeout=3.0):
        """Ask the shim for a frame; the .bmp path (bmp=True) or the PIL image, None if none came."""
        path = os.path.join(SHOTS, name + '.bmp')
        if os.path.exists(path):
            os.remove(path)
        # written aside, then renamed in whole: the shim reads the request any frame, and a file it caught created but
        # not yet written was an empty name -- saved as shot_<ms>.bmp, this wait ran out (bench 2026-10-25: the
        # "dropouts" of A4 win at s118 and s125)
        tmp = os.path.join(SHOTS, 'shot.req.tmp')
        with open(tmp, 'w', encoding='ascii') as f:
            f.write(name)
        for _ in range(20):
            try:
                os.replace(tmp, os.path.join(SHOTS, 'shot.req'))
                break
            except PermissionError:             # the shim has the last request open
                time.sleep(0.02)
        end = time.monotonic() + timeout
        while not os.path.exists(path):
            if time.monotonic() > end:
                return None
            time.sleep(0.05)
        time.sleep(0.15)            # let the shim finish writing
        if bmp:
            return path
        img = Image.open(path).convert('RGB')
        img.load()
        os.remove(path)
        return img

    def frame(self, note=''):
        """Archive a frame; (id, PIL image)."""
        self.window()
        if self.muted == 0:
            self.muted = mute(self.p.pid)
        # the mission second when the shot was asked for: the shim saves the next frame drawn (ms later), while
        # waiting for the file and reading it back take ~0.3 s -- 2-3 mission seconds at x8 (bench 2026-10-27)
        second = self.second()
        img = self._capture('mcp')
        if img is None:
            raise BenchError('no frame from the capture shim within 3 s')
        fid = len(self.frames) + 1
        img.save(os.path.join(self.run_dir, f'{fid:04d}.png'))
        self.frames.append(dict(id=fid, second=second, note=note, view=self.view))
        with open(os.path.join(self.run_dir, 'index.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(mod=self.mod, frames=self.frames), f, ensure_ascii=False, indent=1)
        return fid, img

    def keep_walk(self, bmp, step, s, scale=0.5):
        """Archive a frame of the menu walk (I22): `scale` size, second None, the step and walk second in the note."""
        img = Image.open(bmp).convert('RGB')
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.BILINEAR)
        fid = len(self.frames) + 1
        img.save(os.path.join(self.run_dir, f'{fid:04d}.png'))
        self.frames.append(dict(id=fid, second=None, note=f'menu: {step} at walk {s} s', view=None, scale=scale))
        with open(os.path.join(self.run_dir, 'index.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(mod=self.mod, frames=self.frames), f, ensure_ascii=False, indent=1)
        return fid

    def archived(self, fid):
        p = os.path.join(self.run_dir, f'{int(fid):04d}.png')
        if not os.path.exists(p):
            raise BenchError(f'no frame {fid} (frames 1..{len(self.frames)})')
        return Image.open(p).convert('RGB')

    # -- world <-> screen -------------------------------------------------------------------------------------
    def ground(self):
        """The running mod's terrain (calib.Ground), or None where its map cannot be read (then the ground is flat)."""
        if self._ground is None:
            try:
                self._ground = calib.Ground(self.map_name or self.mod)
            except (Exception, SystemExit) as e:          # maprender.load exits on a missing map
                self._say(f'terrain of {self.mod} not read ({e}): clicks as on flat ground')
                self._ground = False
        return self._ground or None

    def _lift(self, x, y):
        g = self.ground() if self.view is not None and (self.mod or self.map_name) else None
        return g.lift(x, y, self.view) if g else 0.0

    def to_screen(self, x, y, air=False):
        if self.view is None:
            u, v = calib.world_to_screen(x, y)
        else:   # the ground's height against what the camera looks at (calib.Ground; A4 back lane V1, round 8)
            u, v = calib.world_to_screen_at(x, y + self._lift(x, y), self.view)
        return u + self.shift[0], v + self.shift[1] - (AIR_LIFT if air else 0)

    def to_world(self, u, v):
        x, y = calib.screen_to_world(u - self.shift[0], v - self.shift[1])
        if self.view is not None:
            x, y = x + self.view[0] - calib.START_VIEW[0], y + self.view[1] - calib.START_VIEW[1]
            fy = y                                         # the flat point drawn there; solve y + lift(x, y) = fy
            for _ in range(4):
                y = fy - self._lift(x, y)
        return round(x, 1), round(y, 1)

    def border(self):
        """(name, rect) of the playable area now, or None (no sidecar: the whole map). With several, the one whose
        drawn size matches the minimap on a fresh frame (the mission switches them as it goes)."""
        if len(self.borders) < 2:
            return self.borders[0] if self.borders else None
        img = self._capture('minimap')
        size = img and calib.minimap_drawn(img)
        if size:
            self.last_border = min(self.borders, key=lambda b: sum(abs(p - q) for p, q in
                                                                   zip(calib.drawn_size(b[1]), size)))
        return self.last_border

    def camera(self, x, y):
        """Centre the camera on world (x, y): a left click on the minimap (which draws only the playable area)."""
        h = self.window()
        b = self.border()
        if b and not (b[1][0] <= x <= b[1][2] and b[1][1] <= y <= b[1][3]):
            raise BenchError(f'({x}, {y}) is outside the playable area now ({b[0]} {b[1]}): the camera cannot go there')
        click(h, *calib.world_to_minimap(x, y, b and b[1]))
        self.view = (float(x), float(y))
        self.shift = (0.0, 0.0)
        time.sleep(0.3)

    def scripted_view(self, x, y):
        """The mission's own MOVE_CAMERA_TO put the camera on world (x, y): that point, at the height the camera looks
        at, then stands at screen (640, 350) (bench 2026-11-03, a4 place: an engineer teleported to the waypoint stood
        there), not where a minimap jump's calibration puts the view's centre; later world clicks follow. The ground
        there is drawn lower where the camera looks higher (to_screen, calib.Ground: at A4's V1, 26 px)."""
        self.view = (float(x), float(y))
        u, v = calib.world_to_screen_at(x, y, self.view)      # the flat mapping: the look height at (640, 350)
        self.shift = (640.0 - u, 350.0 - v)


def main():
    if sys.argv[1] == 'smoke':
        s = Session()
        try:
            print(s.start(sys.argv[2]))
            fid, img = s.frame('smoke')
            print('frame', fid, img.size, 'at mission second', s.second())
        finally:
            print(s.stop())


if __name__ == '__main__':
    main()
