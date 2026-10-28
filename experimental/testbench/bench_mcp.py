"""ra3bench: an MCP server that holds the test-bench game (harness.Session) so an agent plays a test map step by step
instead of writing a click timeline for run_bench.ps1 (registered in the repository's .mcp.json; Python from
envs/bench_mcp, which has mcp 2.x, Pillow, NumPy, pycaw).

Coordinates are world (map) units by default -- the same numbers the builders place units at -- converted with the
bench calibration (maps built on CampNew18's island). Every frame is archived full size in the run folder; tools
return a half-size view, and bench_inspect crops any archived frame at any zoom. Mission scripts report what a test
needs to know in the military caption (bench_caption reads it).

  ../envs/bench_mcp/Scripts/python.exe -I -X utf8 experimental/testbench/bench_mcp.py     (stdio; the client starts it)
"""
import functools
import io
import os
import sys
import time

from mcp.server.mcpserver import Image, MCPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

server = MCPServer('ra3bench', instructions=(
    'Red Alert 3 test bench: one game at a time. Design through interfaces: cnv_show(name, check) tells, without '
    'building, what the map publishes (named sites, players), what the units publish (abilities), the mission\'s cast '
    'and endings, and whether everything the scripts use was published (contract) -- missions place by site and '
    'checks ask the mission, never raw coordinates or another module\'s constants. '
    'First choice for a test: cnv_check(name, check) -- builds the '
    'mission with its check (experimental/cnv; cnv_list shows them), runs it and returns PASS / FAIL from the map\'s '
    'own counters, no clicks or pictures; cnv_map(mod) shows a built map from above without the game (placement, '
    'trigger areas). New checks are written in experimental/cnv/checks (counters, trigger areas, expectations). '
    'Maps: after any map or placement change run cnv_preview(name) first (~10 s, no compile, no game): the map\'s '
    'design lint, its measures against the retail campaign maps, a picture. The retail maps are the design '
    'reference (docs/story/map-language.md): map_study(target) measures one, retail_scripts(pattern) shows how their '
    'scripts use an action, retail_objects(pattern) where and how a template is placed, retail_goals() their '
    'objectives. bench_menu() shows the mission menu (objectives list) in a running game. '
    'By hand: bench_start(mod) walks the menus into the mod\'s test mission '
    '(~40 s). Then act in world coordinates (map units, as the builders place objects): bench_click / bench_box / '
    'bench_ability / bench_camera, advance with bench_wait, look with bench_look, zoom into any archived frame with '
    'bench_inspect, read script signals with bench_caption. With hold=true (default) the mission is paused between '
    'calls and runs only while a tool acts or waits; bench_status gives the mission seconds run so far. '
    'Hovering aircraft: pass air=true to click where they are drawn. bench_stop when done (it frees the bench lock). '
    'Fewest clicks and pictures: let the map\'s scripts act (experimental/cnv checks) and count (DISPLAY_COUNTER), '
    'then bench_watch(sheet=false) and bench_counters -- numbers as text; bench_strip / bench_inspect only to look.'))
S = harness.Session()


def view(img, scale=0.5, fmt='JPEG'):
    if scale != 1:
        img = img.resize((round(img.width * scale), round(img.height * scale)))
    buf = io.BytesIO()
    img.save(buf, fmt, quality=85) if fmt == 'JPEG' else img.save(buf, fmt)
    return Image(data=buf.getvalue(), format=fmt.lower())


def looked(note, scale=0.5, settle=0.5):
    """After an action: let it settle, archive a frame, pause again (hold mode), return the frame."""
    time.sleep(settle)
    fid, img = S.frame(note)
    S.pause()
    return [f'frame {fid} at mission second {S.second()} (camera {"start" if S.view is None else S.view})'
            f'{"; paused" if S.paused else ""}', view(img, scale)]


def go():
    """Before an action: the window, the menu closed (hold mode)."""
    h = S.window()
    S.resume()
    return h


def guard(fn):
    """Bench errors come back as text (the game state, what to do), not as a tool failure."""
    @functools.wraps(fn)                # the server reads the signature through __wrapped__
    def wrapped(*a, **k):
        try:
            return fn(*a, **k)
        except harness.BenchError as e:
            return f'BENCH: {e}'
    return wrapped


@server.tool(structured_output=False)
@guard
def bench_start(mod: str, visible: bool = False, hold: bool = True, look: bool = True) -> list:
    """Start the bench game with a built mod (a folder name under Documents/Red Alert 3/Mods, e.g. CampNew38) and
    walk the menus into its mission. Refuses while RA3 runs (the user may be playing) or the bench lock is held.
    visible=true leaves the window on the desktop (default: parked off screen, muted). hold=true (default): the
    mission is paused (its Esc menu) between tool calls and only runs while a tool acts or waits. look=false: no
    first frame (a scripted test that only needs bench_watch)."""
    r = S.start(mod, visible=visible, hold=hold)
    msg = f'started {r["mod"]} (pid {r["pid"]}); frames archived in {r["run_dir"]}; ' + '; '.join(r['log'])
    return [msg] + looked('start', settle=1.0) if look else after(msg, False)


@server.tool(structured_output=False)
@guard
def bench_look(note: str = '', scale: float = 0.5) -> list:
    """The current frame (scale 0.5 = 640x360; full size stays in the archive). Paused (hold mode): the last frame,
    the game has not moved since."""
    if S.paused and S.frames:
        fid = S.frames[-1]['id']
        return [f'frame {fid} at mission second {S.second()} (paused: nothing moved since)', view(S.archived(fid), scale)]
    S.window()
    return looked(note, scale, settle=0)


def after(msg, look):
    """The end of an acting tool: a frame (look) or just the pause."""
    if look:
        return [msg] + looked(msg)
    time.sleep(0.3)
    S.pause()
    return [msg]


@server.tool(structured_output=False)
@guard
def bench_inspect(frame: int, x0: float, y0: float, x1: float, y1: float, world: bool = False,
                  zoom: float = 2.0) -> list:
    """Crop an archived frame and enlarge it. Box in screen pixels (1280x720), or world units with world=true
    (converted with that frame's camera)."""
    img = S.archived(frame)
    if world:
        keep = S.view
        S.view = S.frames[frame - 1]['view']
        (u0, v0), (u1, v1) = S.to_screen(x0, y0), S.to_screen(x1, y1)
        S.view = keep
        x0, y0, x1, y1 = min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1)
    box = tuple(int(max(0, min(lim, c))) for c, lim in zip((x0, y0, x1, y1), (img.width, img.height) * 2))
    if box[2] <= box[0] or box[3] <= box[1]:
        return f'BENCH: empty box {box}'
    return [f'frame {frame} box {box} x{zoom}', view(img.crop(box), zoom, 'PNG')]


@server.tool(structured_output=False)
@guard
def bench_caption(frame: int = 0) -> list:
    """The military-caption strip (where mission scripts report test signals) of a frame, enlarged; frame 0 = a new
    frame now."""
    if not frame:
        if S.paused and S.frames:
            frame = S.frames[-1]['id']
        else:
            frame, _ = S.frame('caption')
            S.pause()
    return bench_inspect(frame, *harness.CAPTION_BOX, zoom=1.5)


@server.tool(structured_output=False)
@guard
def bench_click(x: float, y: float, world: bool = True, right: bool = False, air: bool = False,
                look: bool = True) -> list:
    """Left click (select) or right click (move / attack the thing under it) at a world point (or a screen pixel with
    world=false, e.g. a UI button). air=true: a hovering aircraft, clicked where it is drawn."""
    u, v = S.to_screen(x, y, air) if world else (x, y)
    harness.click(go(), u, v, right)
    return after(f'{"right" if right else "left"} click at screen ({u:.0f}, {v:.0f})', look)


@server.tool(structured_output=False)
@guard
def bench_box(x0: float, y0: float, x1: float, y1: float, world: bool = True, air: bool = False,
              look: bool = True) -> list:
    """Box-select between two corners (world units, or screen pixels with world=false)."""
    (u0, v0), (u1, v1) = ((S.to_screen(x0, y0, air), S.to_screen(x1, y1, air)) if world else ((x0, y0), (x1, y1)))
    harness.drag(go(), u0, v0, u1, v1)
    return after(f'box select screen ({u0:.0f}, {v0:.0f})-({u1:.0f}, {v1:.0f})', look)


@server.tool(structured_output=False)
@guard
def bench_ability(x: float, y: float, world: bool = True, look: bool = True) -> list:
    """Use the selected unit's first ability button, then click its target point (world units by default)."""
    h = go()
    harness.click(h, *harness.ABILITY_SLOT)
    time.sleep(0.3)
    u, v = S.to_screen(x, y) if world else (x, y)
    harness.click(h, u, v)
    return after(f'ability 1 at screen ({u:.0f}, {v:.0f})', look)


@server.tool(structured_output=False)
@guard
def bench_key(vk: int, look: bool = True) -> list:
    """Press a key (Windows virtual-key code, e.g. 32 space). Not Esc in hold mode: Esc is the pause itself."""
    if vk == 0x1B and S.hold:
        return 'BENCH: Esc is the hold-mode pause; start with hold=false to send it'
    harness.key(go(), vk)
    return after(f'key {vk}', look)


@server.tool(structured_output=False)
@guard
def bench_camera(x: float, y: float, look: bool = True) -> list:
    """Centre the camera on a world point (a minimap click); later world clicks follow the new camera."""
    go()
    S.camera(x, y)
    return after(f'camera on ({x}, {y})', look)


@server.tool(structured_output=False)
@guard
def bench_wait(seconds: float, look: bool = True) -> list:
    """Let the game run for some seconds (max 120), then look."""
    go()
    S.run_for(min(120.0, seconds))
    S.window()
    if look:
        return [f'ran {seconds} s'] + looked(f'after {seconds} s', settle=0)
    S.pause()
    return f'ran {seconds} s; mission second {S.second()}'


def box_of(frame_view, x0, y0, x1, y1, world, size):
    """A box in screen pixels, clamped; world corners converted with the given camera."""
    if world:
        keep = S.view
        S.view = frame_view
        (u0, v0), (u1, v1) = S.to_screen(x0, y0), S.to_screen(x1, y1)
        S.view = keep
        x0, y0, x1, y1 = min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1)
    return tuple(int(max(0, min(lim, c))) for c, lim in zip((x0, y0, x1, y1), size * 2))


CAPTION_DIFF = 20           # the caption strip changed this much: a caption came, went or changed (first run: a
                            # caption staying up drifts 8-10, one coming or going 29-40)


def change(a, b):
    """Mean absolute difference of two same-size images, 0..255 (a cheap 'did anything move' number)."""
    pa, pb = a.convert('L').tobytes(), b.convert('L').tobytes()
    return round(sum(abs(x - y) for x, y in zip(pa, pb)) / max(1, len(pa)), 1)


UNTIL_OPS = {'==': lambda a, b: a == b, '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b, '>': lambda a, b: a > b,
             '<': lambda a, b: a < b}


def until_met(until, vals):
    """'c1==0|c4==0' (counter lines from 1, any of them) against one frame's counter values."""
    import re
    for part in filter(None, until.replace(' ', '').split('|')):
        k, op, want = re.fullmatch(r'c(\d+)(==|>=|<=|>|<)(-?\d+)', part).groups()
        v = vals[int(k) - 1] if int(k) <= len(vals) else None
        if v is not None and UNTIL_OPS[op](v, int(want)):
            return part
    return None


@server.tool(structured_output=False)
@guard
def bench_watch(seconds: float, every: float = 3.0, x0: float = 0, y0: float = 0, x1: float = 1280, y1: float = 720,
                world: bool = False, air: bool = False, scale: float = 0.5, sheet: bool = True, lines: int = 0,
                until: str = '') -> list:
    """Let the game run for some seconds (max 120) and archive a frame every `every` seconds -- one call instead of a
    wait/look per step. Returns, per frame: mission second, how much the box changed since the previous frame (mean
    pixel difference; water and idle animation alone give ~8) and whether the military caption changed; plus ONE
    contact sheet of the box cut from each frame (sheet=false: numbers only, look later with bench_inspect). Box in
    screen pixels, or world units with world=true (the current camera); air=true also takes in the ~170 px above it
    where hovering aircraft over that ground are drawn. lines=n: also each frame's n counters as numbers; until
    (with lines): stop as soon as a frame meets it, e.g. 'c1==0' or 'c1==0|c4==0' (counter lines from 1) -- the
    row then says UNTIL met."""
    from PIL import Image as PImage, ImageDraw
    import counters
    go()
    end, rows, cuts, prev, prev_cap = S.second() + max(0.0, min(120.0, seconds)), [], [], None, None   # mission time
    while True:
        try:
            fid, img = S.frame(f'watch {every} s')
        except harness.BenchError as e:         # the game went (a crash): what was seen so far still counts
            rows.append(f'stopped: {e}')
            break
        box = box_of(S.view, x0, y0, x1, y1, world, img.size)
        if air:
            box = (box[0], max(0, box[1] - harness.AIR_LIFT), box[2], box[3])
        cut, cap = img.crop(box), img.crop(harness.CAPTION_BOX)
        moved = '-' if prev is None else change(prev, cut)
        d = 0 if prev_cap is None else change(prev_cap, cap)
        text = f' CAPTION CHANGED ({d})' if d >= CAPTION_DIFF else ''
        vals = counters.read(img, lines) if lines else []
        if vals:
            text += ' [' + ' '.join('?' if v is None else str(v) for v in vals) + ']'
        rows.append(f'#{fid} s{S.second()} change {moved}{text}')
        prev, prev_cap = cut, cap
        cuts.append((fid, S.second(), cut))
        met = until_met(until, vals) if until and vals else None
        if met:
            rows.append(f'UNTIL met: {met}')
            break
        if S.second() + every > end:
            break
        S.run_for(every)
    try:
        S.pause()
    except harness.BenchError:                  # no mission menu: the mission has ended (won / lost screen)
        rows.append('could not pause: the mission has ended?')
    out = [f'box {box}; ' + ' | '.join(rows)]
    if sheet and cuts:
        w, h = round(cuts[0][2].width * scale), round(cuts[0][2].height * scale)
        cols = min(len(cuts), max(1, 1280 // max(1, w)))
        page = PImage.new('RGB', (cols * w, -(-len(cuts) // cols) * h))
        d = ImageDraw.Draw(page)
        for k, (fid, s, cut) in enumerate(cuts):
            at = (k % cols * w, k // cols * h)
            page.paste(cut.resize((w, h)), at)
            d.text((at[0] + 4, at[1] + 4), f'#{fid} s{s}', fill=(255, 255, 0))
        out.append(view(page, 1, 'JPEG'))
    return out


@server.tool(structured_output=False)
@guard
def bench_counters(lines: int, frames: str = 'all') -> str:
    """The mission's on-screen counters (DISPLAY_COUNTER, bottom left) read as numbers from archived frames -- text,
    no image, the game untouched. lines: how many counters the map shows (top to bottom). frames as bench_strip.
    '?' = nothing read there (no digit templates yet: counters.py calibrate)."""
    import counters
    ids = [f['id'] for f in S.frames]
    if frames.startswith('last'):
        ids = ids[-int(frames[4:] or 5):]
    elif frames != 'all':
        ids = [int(v) for v in frames.split(',')]
    rows = []
    for fid in ids:
        vals = counters.read(S.archived(fid), lines)
        rows.append(f's{S.frames[fid - 1]["second"]:.0f}: ' + ' '.join('?' if v is None else str(v) for v in vals))
    return ' | '.join(rows) or 'BENCH: no frames'


@server.tool(structured_output=False)
@guard
def bench_strip(x0: float = harness.COUNTER_BOX[0], y0: float = harness.COUNTER_BOX[1],
                x1: float = harness.COUNTER_BOX[2], y1: float = harness.COUNTER_BOX[3], frames: str = 'all',
                zoom: float = 1.5) -> list:
    """The same screen box (pixels) cut from several archived frames, side by side with their mission seconds --
    a timeline in one small image, the game untouched. Default box: the script counters (DISPLAY_COUNTER, bottom
    left), so a test map that counts what it checks reads as numbers over time. frames: 'all', 'last5' or '3,7,10'."""
    from PIL import Image as PImage, ImageDraw
    ids = [f['id'] for f in S.frames]
    if frames.startswith('last'):
        ids = ids[-int(frames[4:] or 5):]
    elif frames != 'all':
        ids = [int(v) for v in frames.split(',')]
    if not ids:
        return 'BENCH: no frames'
    box = tuple(int(v) for v in (x0, y0, x1, y1))
    w, h, tag = box[2] - box[0], box[3] - box[1], 44
    cols = max(1, min(len(ids), 1280 // (w + tag)))
    page = PImage.new('RGB', (cols * (w + tag), -(-len(ids) // cols) * h))
    d = ImageDraw.Draw(page)
    for k, fid in enumerate(ids):
        x, y = k % cols * (w + tag), k // cols * h
        page.paste(S.archived(fid).crop(box), (x + tag, y))
        d.text((x + 2, y + h // 2 - 6), f's{S.frames[fid - 1]["second"]:.0f}', fill=(255, 255, 0))
    return [f'box {box}, frames {ids[0]}..{ids[-1]}', view(page, zoom, 'PNG')]


@server.tool(structured_output=False)
@guard
def bench_where(x: float, y: float, to_world: bool = False) -> str:
    """World point -> screen pixel under the current camera (or screen -> world with to_world=true)."""
    if to_world:
        return f'screen ({x}, {y}) -> world {S.to_world(x, y)}'
    return f'world ({x}, {y}) -> screen {S.to_screen(x, y)}; minimap {harness.calib.world_to_minimap(x, y)}'


@server.tool(structured_output=False)
@guard
def bench_status() -> str:
    """Is a game running, which mod, mission second, frames so far, the last log lines."""
    alive = S.p is not None and S.p.poll() is None
    return (f'alive={alive} mod={S.mod} second={S.second()} paused={S.paused} frames={len(S.frames)} camera={S.view} '
            f'run_dir={S.run_dir} log={S.log[-5:]}')


@server.tool(structured_output=False)
@guard
def bench_stop() -> str:
    """Close the bench game and free the bench lock (frames stay in the run folder)."""
    r = S.stop()
    return f'stopped {r["mod"]}: {r["frames"]} frames in {r["run_dir"]}'


# ------------------------------------------------------------- the decoupled builds (experimental/cnv), one call each
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, 'experimental', 'cnv', 'build.py')
PLANCHECK = os.path.join(ROOT, 'experimental', 'cnv', 'plancheck.py')
SIM = os.path.join(ROOT, 'experimental', 'cnv', 'sim.py')
SIMSTATIC = os.path.join(ROOT, 'experimental', 'cnv', 'simstatic.py')
MAPRENDER = os.path.join(ROOT, 'experimental', 'campaign', 'maprender.py')
MAPSTUDY = os.path.join(ROOT, 'experimental', 'campaign', 'mapstudy.py')
TERRAINREF = os.path.join(ROOT, 'experimental', 'campaign', 'terrainref.py')
RETAILREF = os.path.join(ROOT, 'experimental', 'campaign', 'retailref.py')
# the builds run in the base interpreter, in their own process: fresh code on every call (a check just edited), and
# the pipeline's module state (templates, strings) starts empty each time
BASE_PY = getattr(sys, '_base_executable', sys.executable)


def lab(*args, timeout=900):
    import subprocess
    r = subprocess.run([BASE_PY, '-I', '-X', 'utf8', *args], capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=ROOT, timeout=timeout)
    return r.returncode, r.stdout + (('\n' + r.stderr) if r.stderr.strip() else '')


def tail(text, n=12):
    return '\n'.join(text.strip().splitlines()[-n:])


def brief(tool, text):
    """A step's text inside cnv_check, without what the verdict repeats: the counters come once, folded, in the
    judge's report, so a watch keeps only its frame span and its events (captions, the stop) and bench_counters
    nothing; bench_start drops the menu-by-menu log. The full rows stay in bench_watch itself and the run folder."""
    import re
    if tool == 'bench_counters':
        return 'read' if not text.startswith('BENCH') else text
    if tool == 'bench_start':
        return re.sub(r'; menu \d+ [^;]*', '', text)
    if tool != 'bench_watch':
        return text[:600]
    rows = text.split(' | ')
    frames = [(m.group(0), r) for r in rows for m in [re.search(r'#\d+ s[\d.]+', r)] if m]
    seconds = [f.split()[1] for f, _ in frames]
    events = [f + ' caption changed' for f, r in frames if 'CAPTION CHANGED' in r]
    events += [r for r in rows if r.startswith(('UNTIL met', 'stopped:', 'could not pause'))]
    span = f'{len(seconds)} frames {seconds[0]}..{seconds[-1]}' if seconds else 'no frames'
    return span + ('; ' + '; '.join(events) if events else '')


@server.tool(structured_output=False)
def cnv_list() -> str:
    """Every decoupled build (experimental/cnv/build.py): mission, its checks, the mod each builds to, the counters a
    check shows and what it expects of them."""
    code, out = lab(BUILD, 'list', timeout=120)
    return out.strip() if code == 0 else 'BUILD: ' + tail(out)


@server.tool(structured_output=False)
def cnv_show(name: str, check: str = '') -> str:
    """What each layer of a build publishes to the next, as text, without building or the game: the map's sites
    (named places, what each is for) and players, each unit's abilities and options, the mission's cast (who plays
    which part, on which site) and endings, the check's counters and expectations -- then the contract check: every
    object placed by a site, every name a script uses published by someone. Read this before writing a mission or a
    check, and after: 'contract: ok' or the list of what is used but not published."""
    code, out = lab(BUILD, name, *(['--check', check] if check else []), '--show', timeout=120)
    return out.strip() if code in (0, 1) and 'contract:' in out else 'BUILD: ' + tail(out)


@server.tool(structured_output=False)
def plan_show(level: str) -> str:
    """A level's plan (docs/story/plans/<level>.md -- the level itself: edit it, build, the game plays the change)
    read back without the game, in seconds: the beat sheet it makes (phases with their objectives, border, opening
    actions and end; the attack waves, when they start at normal difficulty, their sources and caps), its design
    check against what the retail missions do (docs/story/map-language.md 7: phase count, a mid-mission twist,
    first threat and first real attack times, every repeating wave with a source or cap, objectives, autosaves,
    difficulty direction, hints), and the compile with its contract. Run it after every edit to a plan, before
    cnv_check."""
    code, out = lab(PLANCHECK, level, timeout=120)
    return out.strip() if code == 0 else 'PLAN: ' + tail(out)


@server.tool(structured_output=False)
def plan_sim(name: str, script: str = '', check: str = '', level: str = 'normal', until: float = 1800.0) -> str:
    """A level (or any build: 'a4', 'a4' with check 'stop') played out without the game, in seconds: the timeline
    (what happens when, what the player is told, what appears and whether the player sees it), the ending (won /
    lost / stuck and what each ending still waits for), the tension curve, the ground known, how the first enemy
    came; then every way it could go (simstatic: phases never reached, can it be won and lost, objectives never
    done, flags waited on that nobody sets). script: the player's part, one event a line or ';' between --
    '60 派 tank 去 north camp; 120 摧毁 north barracks; 90 血量 yuriko 1; 自动打掉 10' (empty: the player does
    nothing). Combat is not simulated: losses come from the script. With a check, its counters are judged by the
    simulator's own expectations where experimental/cnv/simchecks.py has them. Use it after every plan edit, before
    the bench (docs/story/plans/README.md, 模拟器)."""
    args = [name] + (['--check', check] if check else []) + (['--script', script] if script else []) + \
        ['--level', level, '--until', str(until)]
    code, out = lab(SIM, *args, timeout=300)
    _, static = lab(SIMSTATIC, name, *(['--check', check] if check else []), timeout=300)
    return out.strip() + '\n--- 所有可能的走向\n' + static.strip()


@server.tool(structured_output=False)
def plan_vocab(map: str = '') -> str:
    """The words a level plan may write: its sections, the conditions and actions, the devices (each level
    mechanic's parameters, events, actions), the unit names; with map (e.g. 'festival') that map's sites and
    borders too."""
    code, out = lab(PLANCHECK, '--vocab', *([map] if map else []), timeout=120)
    return out.strip() if code == 0 else 'PLAN: ' + tail(out)


@server.tool(structured_output=False)
@guard
def cnv_check(name: str, check: str = '', build: bool = True, keep: bool = False, retry: bool = True) -> str:
    """Build a mission with one of its checks (cnv_list), run it on the bench and judge it -- one call, no clicks, no
    pictures: the map's scripts act, its counters report, the counters are read as numbers and held against the
    check's expectations. Returns the build summary, the watch rows, the readings and PASS / FAIL per expectation.
    build=false: the mod already built. keep=true: the game stays up (inspect frames, bench_stop when done). Takes
    ~2-3 min (build ~70 s, menus ~40 s, the check's own run). retry=true: a run the capture dropped out of
    (BENCH DROPOUT) is run once more by itself, without building again."""
    out = _cnv_check(name, check, build, keep)
    if retry and 'BENCH DROPOUT' in out:
        # bench 2026-10-23: 3 of 14 runs dropped out, every rerun read through
        out = out + '\n\n--- run again (dropout) ---\n' + _cnv_check(name, check, False, keep)
    return out


def _cnv_check(name, check, build, keep):
    import json
    args = [BUILD, name] + (['--check', check] if check else [])
    code, out = lab(*args, '--plan', *([] if build else ['--no-build']))
    plan = next((json.loads(x[5:]) for x in out.splitlines() if x.startswith('PLAN ')), None)
    if code or plan is None:
        return 'BUILD FAILED:\n' + tail(out, 25)
    built = [x for x in out.splitlines() if x.startswith(('lint:', '-> ', plan['mod'] + ':'))]
    if plan.get('staged'):
        return '\n'.join(built + ['RA3 is running: built to work/staging, no bench run'])
    if not plan['steps']:
        return '\n'.join(built + ['built (no check: nothing to run)'])
    lines, counted, done = built, '', ''
    try:
        for tool, a in plan['steps']:
            # the condition came: the waits for it go; a watch without one (a look after it) still runs
            if done and tool == 'bench_watch' and (done != 'UNTIL met' or a.get('until')):
                lines.append(f'bench_watch: skipped ({done})')
                continue
            got = globals()[tool](**a)
            text = ' '.join(x for x in (got if isinstance(got, list) else [got]) if isinstance(x, str))
            lines.append(f'{tool}: {brief(tool, text)}')
            if text.startswith('BENCH:') and tool == 'bench_start':
                return '\n'.join(lines)
            if tool == 'bench_counters':
                counted = text
            if tool == 'bench_watch':           # nothing more to wait for: the condition came, or the game ended
                done = next((w for w in ('UNTIL met', 'mission has ended', 'stopped:') if w in text), '')
    finally:
        if not keep and S.p is not None:
            lines.append(bench_stop())
    code, out = lab(*args, '--judge', counted, timeout=120)
    if done == 'stopped:' and 'RESULT FAIL' in out:     # bench 2026-10-22: the shim went quiet at s11.6, the rerun passed
        out += ('\nBENCH DROPOUT: the capture stopped before the check was over -- "no reading" FAILs say nothing '
                'about the mission; run again with build=false')
    return '\n'.join(lines + [out.strip()])


@server.tool(structured_output=False)
def cnv_map(mod: str, x: float = 0, y: float = 0, r: float = 0, px: int = 2) -> list:
    """A built mod's map from above, without the game (maprender): terrain, objects coloured by owner, waypoints,
    trigger areas, a world grid -- to check where a mission placed things. x, y, r (world units): only that square
    around (x, y). px: pixels per map cell."""
    out_png = os.path.join(ROOT, 'work', 'maps', f'{mod}_mcp.png')
    code, out = lab(MAPRENDER, mod, '-o', out_png, '--px', str(px), *(['--around', str(x), str(y), str(r)] if r else []),
                    timeout=300)
    if code or not os.path.exists(out_png):
        return ['MAP: ' + tail(out)]
    from PIL import Image as PImage
    img = PImage.open(out_png).convert('RGB')
    scale = min(1.0, 1280 / max(img.size))
    return [f'{mod}: {img.width}x{img.height} (full size: {out_png})', view(img, scale)]


def picture(path, note):
    from PIL import Image as PImage
    img = PImage.open(path).convert('RGB')
    return [note, view(img, min(1.0, 1000 / max(img.size)))]


@server.tool(structured_output=False)
def cnv_preview(name: str, check: str = '') -> list:
    """A build's map in ~10 s, without compiling or the game: the map module's design lint (ramps, building sites,
    structures on flat ground, bridges bank to bank, blocks' use, gaps' width), the map written as the build would
    write it, measured against the retail campaign maps' ranges (flat ground, cliffs, height tiers, ore, tech,
    bridges, objectives; TERRAIN lines: chokes on the main way, high ground beside it, ramps, strongpoints, walls,
    how much of the walkable ground the mission uses -- docs/design/principles.md P24-P27), and a
    picture from above: height bands, cliffs dark, flat land light, ore gold, tech cyan, bridges white, the player's
    objects green, enemies red, objective markers yellow. Use it after every map or placement change, before
    cnv_check (docs/story/map-language.md)."""
    code, out = lab(BUILD, name, *(['--check', check] if check else []), '--preview', timeout=300)
    lint = next((x for x in out.splitlines() if x.startswith('LINT ')), 'LINT (map has no platform layout)')
    path = next((x[8:] for x in out.splitlines() if x.startswith('PREVIEW ')), None)
    if code or not path:
        return ['PREVIEW FAILED:\n' + tail(out, 20)]
    code, study = lab(MAPSTUDY, '--ours', path, timeout=300)
    pic = next((x[8:] for x in study.splitlines() if x.startswith('PICTURE ')), None)
    # the terrain rules (P24-P27): chokes on the main way, high ground beside it, how much of the ground is used
    tcode, terrain = lab(TERRAINREF, path, timeout=300)
    terrain = [x for x in terrain.splitlines() if x.startswith('TERRAIN ')] or ['TERRAIN FAILED: ' + tail(terrain, 5)]
    text = '\n'.join([lint] + [x for x in study.splitlines() if not x.startswith('PICTURE ')] + terrain)
    return picture(pic, text) if pic and os.path.exists(pic) else [text]


@server.tool(structured_output=False)
def map_study(target: str) -> list:
    """How a retail campaign map is built (target: part of its name, e.g. 's09_newyork', 'ep01_a02') or a built mod
    of ours (its name, or a .map path): the same measures and picture as cnv_preview, ours set against the retail
    ranges. The retail maps are RA3's 27 and Uprising's 13; their late missions are the design reference."""
    ours = os.path.exists(target) or os.path.isdir(os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3',
                                                                 'Mods', target))
    code, out = lab(MAPSTUDY, *(['--ours', target] if ours else [target]), timeout=600)
    if code:
        return ['STUDY: ' + tail(out)]
    rows = [x for x in out.splitlines() if x.startswith('|')]
    if not ours and len(rows) == 1:
        short = rows[0].split('|')[1].strip()
        path = os.path.join(ROOT, 'work', 'mapstudy', short + '.png')
        return picture(path, out.strip()) if os.path.exists(path) else [out.strip()]
    pic = next((x[8:] for x in out.splitlines() if x.startswith('PICTURE ')), None)
    text = '\n'.join(x for x in out.splitlines() if not x.startswith('PICTURE '))
    return picture(pic, text) if pic else [text]


@server.tool(structured_output=False)
def retail_scripts(pattern: str, maps: str = '', limit: int = 8) -> str:
    """Retail campaign scripts using a condition or action (pattern: a regex on the script lines, e.g.
    'LINK_MISSION_OBJECTIVE', "OBJECTIVE_STATUS\\('Bonus"), each whole with its map -- how the original missions do
    it. maps: comma-separated name parts (e.g. 's09,ep01') to search only those."""
    code, out = lab(RETAILREF, 'scripts', pattern, '--maps', maps, '--limit', str(limit), timeout=600)
    return out.strip() if code == 0 else 'RETAIL: ' + tail(out)


@server.tool(structured_output=False)
def retail_objects(pattern: str, maps: str = '', limit: int = 20) -> str:
    """Placements of retail map objects whose template matches pattern (regex, e.g. 'Bridge', 'OreNode',
    'OilDerrick'): map, position in the object list, position, angle, flags (a bridge's start 16 / end 32), owner,
    name, ground height under it (world units; water at 200)."""
    code, out = lab(RETAILREF, 'objects', pattern, '--maps', maps, '--limit', str(limit), timeout=600)
    return out.strip() if code == 0 else 'RETAIL: ' + tail(out)


@server.tool(structured_output=False)
def retail_goals(maps: str = '') -> str:
    """The retail campaign maps' objectives (English titles, main / bonus); maps: name parts to show only those."""
    code, out = lab(RETAILREF, 'goals', '--maps', maps, timeout=600)
    return out.strip() if code == 0 else 'RETAIL: ' + tail(out)


@server.tool(structured_output=False)
@guard
def bench_menu(scale: float = 0.5) -> list:
    """The mission menu (what Esc opens) as the player sees it: the objectives list (green main, yellow bonus, done
    / failed marks), the selected one's description, the battlefield map with the objective markers. Hold mode: the
    pause is that menu; otherwise Esc opens it for the picture and closes it again."""
    h = S.window()
    if S.hold:
        S.pause()
        fid, img = S.frame('mission menu')
    else:
        harness.key(h, 0x1B)
        time.sleep(0.8)
        fid, img = S.frame('mission menu')
        harness.key(h, 0x1B)
    return [f'frame {fid} at mission second {S.second()}: the mission menu', view(img, scale)]


if __name__ == '__main__':
    try:
        server.run()
    finally:
        S.stop()
