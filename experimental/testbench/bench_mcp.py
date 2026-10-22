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
def bench_start(mod: str, visible: bool = False, hold: bool = True) -> list:
    """Start the bench game with a built mod (a folder name under Documents/Red Alert 3/Mods, e.g. CampNew38) and
    walk the menus into its mission. Refuses while RA3 runs (the user may be playing) or the bench lock is held.
    visible=true leaves the window on the desktop (default: parked off screen, muted). hold=true (default): the
    mission is paused (its Esc menu) between tool calls and only runs while a tool acts or waits."""
    r = S.start(mod, visible=visible, hold=hold)
    return [f'started {r["mod"]} (pid {r["pid"]}); frames archived in {r["run_dir"]}; ' + '; '.join(r['log'])] + \
        looked('start', settle=1.0)


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
