"""L6 script actions the player sees or hears and the scripts never ask about (ADR 0029, docs/engine/sim-layers.md):
the reshroud time, the camera, the player's input, the countdown timers, the logged-only names (SHOWN), the mission
hot spots and the names dropped on purpose (IGNORED).

Each action is `fn(sim, name, a, script)`, moved verbatim out of Sim.act's chain; simact.act looks them up in ACTIONS."""
import math

from simscript import IGNORED, SHOWN
from simworld import inside, mmss


def shown(sim, name, a, script):
    if name in SHOWN:
        text = sim.text(a[0]) if isinstance(a[0], str) else str(a[0])
        sim.note(SHOWN[name], text)
        if name == 'SHOW_MILITARY_CAPTION':
            sim.show_caption(text, a[1])
        elif name == 'PLAY_SOUND_EFFECT' and a[0] in sim.mm.subtitles:
            sim.show_subtitle(sim.text(sim.mm.subtitles[a[0]]))
    else:
        return False


def ignored(sim, name, a, script):
    if name in IGNORED or name == 'CAMERA_STOP_FOLLOW':
        pass
    else:
        return False


def map_shroud_set_reshroud_time(sim, name, a, script):
    sim.reshroud = float(a[0])


def move_camera_to(sim, name, a, script):
    p = sim.point(a[0])
    if p:
        # the way there counts (engine_eyes all: a 0.1 s move from the start across M latched M; INFERRED:
        # the straight line, sampled every 20)
        was = sim.camera or sim.start_camera()
        steps = max(1, int(math.hypot(p[0] - was[0], p[1] - was[1]) // 20))
        for k in range(steps + 1):
            x, y = was[0] + (p[0] - was[0]) * k / steps, was[1] + (p[1] - was[1]) * k / steps
            sim.camera_been |= {n for n, pts in sim.areas.items() if inside(pts, x, y)}
        sim.camera = p
        sim.note('镜头', f'到 {a[0]}')


def disable_input(sim, name, a, script):
    sim.input = name == 'ENABLE_INPUT'
    sim.note('过场', '交还控制' if sim.input else '锁住操作')


def display_countdown_timer(sim, name, a, script):
    if a[0] not in sim.countdowns:
        sim.countdowns.add(a[0])
        left = sim.timers.get(a[0], sim.t) - sim.t
        sim.note('倒计时', f'{sim.text(a[1])} {mmss(max(0.0, left))}')


def hide_countdown_timer(sim, name, a, script):
    sim.countdowns.discard(a[0])


def set_mission_hot_spot_activeness(sim, name, a, script):
    # (hot spot, on): one the map has, else nothing (D 116)
    if str(a[0]) in sim.hotspots:
        sim.hotspots[str(a[0])] = bool(a[1])


def set_mission_hot_spot_visibility(sim, name, a, script):
    pass                                            # the marker only: the on bit stays (D 116, 码)


ACTIONS = {
    'CAMPAIGN_CREATE_AUTO_SAVE': shown,
    'MOVIE_PLAY_RADAR': shown,
    'NAMED_FLASH': shown,
    'NAMED_SHOW_INFOBOX': shown,
    'OBJECT_CREATE_RADAR_EVENT': shown,
    'PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM': shown,
    'PATH_MUSIC_PLAY_EVENT': shown,
    'PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT': shown,
    'PLAY_SOUND_EFFECT': shown,
    'SHOW_MILITARY_CAPTION': shown,
    'CAMERA_LETTERBOX_BEGIN': ignored,
    'CAMERA_LETTERBOX_END': ignored,
    'CAMERA_STOP_FOLLOW': ignored,
    'DISPLAY_COUNTER': ignored,
    'HIDE_COUNTER': ignored,
    'SET_COOP_AI_COMMAND_UI_ENABLED': ignored,
    'MAP_SHROUD_SET_RESHROUD_TIME': map_shroud_set_reshroud_time,
    'MOVE_CAMERA_TO': move_camera_to,
    'MOVE_CAMERA_TO_NAMED': move_camera_to,
    'CAMERA_FOLLOW_NAMED': move_camera_to,
    'DISABLE_INPUT': disable_input,
    'ENABLE_INPUT': disable_input,
    'DISPLAY_COUNTDOWN_TIMER': display_countdown_timer,
    'HIDE_COUNTDOWN_TIMER': hide_countdown_timer,
    'SET_MISSION_HOT_SPOT_ACTIVENESS': set_mission_hot_spot_activeness,
    'SET_MISSION_HOT_SPOT_VISIBILITY': set_mission_hot_spot_visibility,
    'LINK_MISSION_HOT_SPOT_TO_OBJECT': set_mission_hot_spot_visibility,
    'LINK_MISSION_HOT_SPOT_TO_WAYPOINT': set_mission_hot_spot_visibility,
}
