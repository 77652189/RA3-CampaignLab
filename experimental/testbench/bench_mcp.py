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
    'Red Alert 3 test bench: one game at a time. bench_start(mod) walks the menus into the mod\'s test mission '
    '(~40 s). Then act in world coordinates (map units, as the builders place objects): bench_click / bench_box / '
    'bench_ability / bench_camera, advance with bench_wait, look with bench_look, zoom into any archived frame with '
    'bench_inspect, read script signals with bench_caption. With hold=true (default) the mission is paused between '
    'calls and runs only while a tool acts or waits; bench_status gives the mission seconds run so far. '
    'Hovering aircraft: pass air=true to click where they are drawn. bench_stop when done (it frees the bench lock).'))
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
    time.sleep(max(0.0, min(120.0, seconds)))
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


@server.tool(structured_output=False)
@guard
def bench_watch(seconds: float, every: float = 3.0, x0: float = 0, y0: float = 0, x1: float = 1280, y1: float = 720,
                world: bool = False, air: bool = False, scale: float = 0.5, sheet: bool = True) -> list:
    """Let the game run for some seconds (max 120) and archive a frame every `every` seconds -- one call instead of a
    wait/look per step. Returns, per frame: mission second, how much the box changed since the previous frame (mean
    pixel difference; water and idle animation alone give ~8) and whether the military caption changed; plus ONE
    contact sheet of the box cut from each frame (sheet=false: numbers only, look later with bench_inspect). Box in
    screen pixels, or world units with world=true (the current camera); air=true also takes in the ~170 px above it
    where hovering aircraft over that ground are drawn."""
    from PIL import Image as PImage, ImageDraw
    go()
    end, rows, cuts, prev, prev_cap = time.monotonic() + max(0.0, min(120.0, seconds)), [], [], None, None
    while True:
        fid, img = S.frame(f'watch {every} s')
        box = box_of(S.view, x0, y0, x1, y1, world, img.size)
        if air:
            box = (box[0], max(0, box[1] - harness.AIR_LIFT), box[2], box[3])
        cut, cap = img.crop(box), img.crop(harness.CAPTION_BOX)
        moved = '-' if prev is None else change(prev, cut)
        d = 0 if prev_cap is None else change(prev_cap, cap)
        text = f' CAPTION CHANGED ({d})' if d >= CAPTION_DIFF else ''
        rows.append(f'#{fid} s{S.second()} change {moved}{text}')
        prev, prev_cap = cut, cap
        cuts.append((fid, S.second(), cut))
        if time.monotonic() + every > end:
            break
        time.sleep(every)
    S.pause()
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


if __name__ == '__main__':
    try:
        server.run()
    finally:
        S.stop()
