"""The campaign shell (ADR 0014, 2026-11-02 probe, 2026-11-03 all nine Allied slots): our levels in the place of retail's Allied
campaign, wearing our own front end -- mission names and briefings from docs/design/flow (shell_missions.json), a test
full-screen movie before each mission, the co-op overview's talking head, placeholder pictures in the briefing screens and on
the faction card, the co-op commander panel gone from the HUD. One mod, `CampShell`, started by its own launcher (launcher.py:
a desktop shortcut for RA3.exe -modConfig); retail started directly is not touched (nothing is written outside Mods\\CampShell).

  python -I -X utf8 experimental/cnv/build.py a4 --shell     -> Documents\\Red Alert 3\\Mods\\CampShell

The built mission (a4) is slot 4; the other eight slots are retail's missions of those slots (their maps, a placeholder) under
our names. What the shell asks of the game (the answers are in docs/story/handoff.md):
  - the campaign list / briefing show our strings (a template per slot, Allies_New and Allies_S<k>, in retail's place);
  - IntroMovie and OverviewTalkingHead name videos of ours (experimental/video/pack.py declares them, the clips ride in the big);
  - a retail APT screen's pictures can be replaced by a mod: the stream's Texture instances rewritten (campaign/apt_textures.py)
    for each slot's objective briefing (the map) and global briefing (three framed pictures) and for the faction menu (the Allies
    card, normal and highlighted);
  - a retail APT screen can be emptied (apt_textures.hollow): the co-op commander panel of the HUD;
  - a retail label (the card's text) can be overwritten from the mod's csf (make_campnew3.OVERRIDES).
"""
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'campaign'))
import apt_textures                                     # noqa: E402

NAME = os.environ.get('CNV_SHELL_NAME', 'CampShell')    # at most 15 characters, letters and digits (parts.assemble asserts it)
HEAD_ID = 'CNVHEAD01'               # the overview's talking head (OverviewTalkingHead): radar-sized, shared by every slot
WORK = os.path.join(ROOT, 'work', 'shell')
TO_VP6 = os.path.join(ROOT, 'experimental', 'video', 'to_vp6.py')
VOSS = os.path.join(os.path.dirname(ROOT), 'RA3-ChineseVoice', 'third_party', 'comfyui', 'input', 'voss_p1.png')
MAP_PICTURE = os.path.join(ROOT, 'work', 'maps', 'CampA4_mcp.png')       # cnv_preview's picture of the map from above
FONT = r'C:\Windows\Fonts\msyhbd.ttc'
B = chr(92)
APT = 'data' + B + 'aptui' + B
PANEL = 'tacticalhudcoopaiorderpanel'       # the HUD's co-op commander panel (portrait, four buttons, the defence-state bar)

# the built mission's own names (the plan's); the other slots' come from shell_missions.json (docs/design/flow/a<k>.md)
TITLE = '札幌雪祭 · 号角与冰墙'
SHORT = '札幌雪祭'
INTRO_TEXT = '战前全屏视频（占位）'
CARD_TEXT = '盟军战役（占位）：札幌雪祭的雪祭会场里，号角一响，三条街的地道同时出兵。'
SLOT_OF = {'CampA4': 4}


def missions():
    with open(os.path.join(HERE, 'shell_missions.json'), encoding='utf-8') as f:
        data = json.load(f)
    return {int(k[1:]): v for k, v in data.items()}


def label(k):
    return f'CNV{k:02d}'


def intro_id(k):
    return f'CNVINTRO{k:02d}'                           # the full-screen movie before the mission (IntroMovie)


@dataclass
class Shell:
    slot: int = 4
    attrs: dict = field(default_factory=dict)       # the built mission's MissionTemplate attributes (make_campnew2.SHELL)
    others: dict = field(default_factory=dict)      # the other slots': {slot: attrs}
    template: dict = field(default_factory=dict)    # the rest of make_campnew2.SHELL ('no_portrait')
    clips: dict = field(default_factory=dict)       # video id -> .vp6
    files: list = field(default_factory=list)       # (big path, bytes): the APT streams with our pictures
    strings: dict = field(default_factory=dict)     # new labels
    overrides: dict = field(default_factory=dict)   # retail labels rewritten


def font(size):
    from PIL import ImageFont
    return ImageFont.truetype(FONT, size, index=0)


def centered(draw, xy_center, text, size, fill, stroke=0, stroke_fill=(0, 0, 0)):
    x, y = xy_center
    f = font(size)
    l, t, r, b = draw.textbbox((0, 0), text, font=f, stroke_width=stroke)
    draw.text((x - (l + r) / 2, y - (t + b) / 2), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


# ---- pictures ----------------------------------------------------------------------------------------------------

def map_picture(size, short=SHORT, real=True):
    """The briefing's map picture, `size` (w, h) or a square side: the built mission's map from above in the briefing's amber, or
    (a slot with no map of ours) an amber grid with the name and 'placeholder'."""
    from PIL import Image, ImageDraw, ImageOps
    w, h = (size, size) if isinstance(size, int) else size
    if real and os.path.exists(MAP_PICTURE):
        img = ImageOps.colorize(Image.open(MAP_PICTURE).convert('L'), black=(14, 6, 0), white=(255, 160, 60))
        img = img.resize((w, h), Image.LANCZOS)
        d = ImageDraw.Draw(img)
    else:
        img = Image.new('RGB', (w, h), (22, 10, 2))
        d = ImageDraw.Draw(img)
        for x in range(0, w, 64):
            d.line((x, 0, x, h), fill=(60, 30, 8))
        for y in range(0, h, 64):
            d.line((0, y, w, y), fill=(60, 30, 8))
        centered(d, (w // 2, h // 2 - 30), short, max(24, w // 12), (255, 190, 100), stroke=3)
    d.rectangle((0, 0, w - 1, h - 1), outline=(200, 110, 30), width=3)
    centered(d, (w // 2, h - 40), short + '（占位图）' if real else '占位图', 40, (255, 220, 160), stroke=3)
    return img


def objective_map(short, real):
    """The objective briefing's map texture: our picture over the retail picture's opaque rectangle."""
    def paint(orig):
        from PIL import Image
        out = orig.convert('RGBA').copy()
        x0, y0, x1, y1 = orig.getchannel('A').getbbox()
        out.paste(map_picture((x1 - x0, y1 - y0), short, real).convert('RGBA'), (x0, y0))
        return out
    return paint


def objective_arrow(orig):
    """The red arrow of the map screen, recoloured to ice blue (red and blue channels swapped)."""
    from PIL import Image
    r, g, b, a = orig.convert('RGBA').split()
    return Image.merge('RGBA', (b, g, r, a))


def name_card(inner, lines):
    from PIL import Image, ImageDraw
    card = Image.new('RGBA', inner, (20, 50, 100, 255))
    d = ImageDraw.Draw(card)
    for y in range(inner[1]):
        t = y / inner[1]
        d.line((0, y, inner[0], y), fill=(int(30 + 90 * t), int(70 + 130 * t), int(130 + 110 * t), 255))
    for (text, size, dy) in lines:
        centered(d, (inner[0] // 2, dy), text, size, (255, 255, 255), stroke=3, stroke_fill=(10, 30, 70))
    return card


def global_pictures(short, real):
    """The overview's three framed pictures (276 x 326 at x 5, 301, 597): inside the frames, for the built mission the map from
    above, Voss and a card; for the other slots three cards."""
    def paint(orig):
        from PIL import Image
        out = orig.convert('RGBA').copy()
        inner = (260, 310)
        if real:
            m = map_picture(1000).crop((120, 0, 880, 1000)).resize(inner, Image.LANCZOS)
            v = Image.open(VOSS).convert('RGBA').crop((120, 0, 1134, 1254)).resize(inner, Image.LANCZOS)
            pics = [m, v, name_card(inner, [(short, 56, 110), ('占位图', 34, 190)])]
        else:
            pics = [name_card(inner, [(short, 52, 110), ('占位图', 34, 190)]),
                    name_card(inner, [('情报', 56, 110), ('占位图', 34, 190)]),
                    name_card(inner, [('目标', 56, 110), ('占位图', 34, 190)])]
        for x0, pic in zip((5, 301, 597), pics):
            out.paste(pic, (x0 + 8, 13))
        return out
    return paint


CARD_BOXES = [(1652, 0, 1908, 441), (1652, 455, 1908, 894)]     # the Allies card in the faction menu: normal, highlighted


def faction_card(orig):
    from PIL import Image, ImageDraw
    out = orig.convert('RGBA').copy()
    for k, (x0, y0, x1, y1) in enumerate(CARD_BOXES):
        w, h = x1 - x0, y1 - y0
        card = Image.new('RGBA', (w, h), (0, 0, 0, 255))
        d = ImageDraw.Draw(card)
        lift = 40 * k
        for y in range(h):
            t = y / h
            d.line((0, y, w, y), fill=(min(255, int(15 + 40 * (1 - t)) + lift), min(255, int(50 + 110 * (1 - t)) + lift),
                                       min(255, int(120 + 120 * (1 - t)) + lift), 255))
        centered(d, (w // 2, h // 2 - 70), 'CNV', 110, (255, 255, 255), stroke=4, stroke_fill=(10, 30, 80))
        centered(d, (w // 2, h // 2 + 40), '战役实验室', 50, (235, 245, 255), stroke=3, stroke_fill=(10, 30, 80))
        centered(d, (w // 2, h // 2 + 120), '占位卡片', 36, (210, 230, 255), stroke=2, stroke_fill=(10, 30, 80))
        d.rectangle((0, 0, w - 1, h - 1), outline=(240, 170, 100, 255), width=2)
        out.paste(card, (x0, y0))
    return out


EVENT = re.compile(rb'MA(\d\d)_AlliedIntel(\d\d)', re.I)       # the retail briefing narration the objective screens play


def new_event(old):
    """Retail's narration event of a briefing line -> ours (same length: it is a name inside the screen's script constants).
    Ours is no audio event at all, so nothing is spoken; its subtitle label (DIALOGEVENT:<name>) holds our placeholder text."""
    m = EVENT.fullmatch(old)
    return f'CNV_SHELL_I_{int(m.group(1)):02d}{int(m.group(2)):02d}00'.encode()


def narration_strings(info):
    """{DIALOGEVENT:<our name>: text}: line 1 of a mission's briefing says its briefing, line 2 its objectives, the others only
    say they are placeholders."""
    out = {}
    for mission in range(1, 10):
        for line in range(1, 25):
            old = f'MA{mission:02d}_AlliedIntel{line:02d}'.encode()
            new = new_event(old).decode().upper()
            m = info[mission]
            out[f'DIALOGEVENT:{new}'] = {1: '（占位旁白）' + m['briefing'], 2: '（占位旁白）' + '；'.join(m['objectives'])}.get(
                line, f'（占位旁白）{m["title"]}')
    return out


def apt_files(slots):
    """The APT streams with our pictures and the emptied co-op panel: [(big path, bytes)]. `slots`: {slot: (short name, built
    mission?)}. Only the .bin carries pictures / shapes; the other three files of a stream are the retail ones byte for byte
    (checked by tests/test_shell.py), so they are not shipped."""
    files = []

    def add(stem, make):
        prefix = APT + stem + '.'
        files.extend((p, v) for p, v in make(prefix) if p.endswith('.bin'))

    for k, (short, built) in slots.items():
        def painted(prefix, k=k, short=short, built=built, renames=None):
            orig = apt_textures.originals('Apt.big', prefix)
            kinds = {'Objective_Briefing_1': objective_map(short, built), 'Objective_Briefing_2': objective_arrow,
                     'Global_Briefing_1': global_pictures(short, built)}
            images = {t: kinds[t[len(f'apt_A{k:02d}_'):]](orig[t]) for t in orig if t[len(f'apt_A{k:02d}_'):] in kinds}
            return apt_textures.patch('Apt.big', prefix, images, renames)
        add(f'a{k:02d}_objective_briefing', lambda prefix, painted=painted: painted(prefix, renames=(EVENT, new_event)))
        add(f'a{k:02d}_global_briefing', painted)
    add('fes_m_factionmenu', lambda prefix: apt_textures.patch(
        'Apt.big', prefix, {'apt_fes_m_factionMenu_1': faction_card(apt_textures.originals('Apt.big', prefix)['apt_fes_m_factionMenu_1'])}))
    add(PANEL, lambda prefix: apt_textures.hollow('Apt.big', prefix))
    return files


# ---- videos ------------------------------------------------------------------------------------------------------

def _to_vp6(mp4, size):
    vp6 = mp4[:-4] + '.vp6'
    if not os.path.exists(vp6) or os.path.getmtime(vp6) < os.path.getmtime(mp4):
        r = subprocess.run([sys.executable, '-I', '-X', 'utf8', TO_VP6, mp4, vp6, '--size', size],
                           capture_output=True, text=True)
        if r.returncode or not os.path.exists(vp6):
            raise SystemExit(f'shell: {mp4} not converted: {(r.stderr or r.stdout).strip()[-300:]}')
    return vp6


def _write_mp4(path, size, seconds, frame, fps=24):
    import cv2
    import numpy as np
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, size)
    for k in range(int(seconds * fps)):
        out.write(cv2.cvtColor(np.array(frame(k / fps, k)), cv2.COLOR_RGB2BGR))
    out.release()


def intro_clip(k, title):
    """4 seconds, 1280 x 720: dark blue, the title, a bar filling up (so a frozen picture is told from a playing one)."""
    from PIL import Image, ImageDraw
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, 'intro.mp4' if k == 4 else f'intro{k}.mp4')
    seconds = 4

    def frame(t, i):
        img = Image.new('RGB', (1280, 720), (6, 14, 30))
        d = ImageDraw.Draw(img)
        for y in range(720):
            c = int(10 + 40 * y / 720)
            d.line((0, y, 1280, y), fill=(c // 3, c // 2, c))
        a = min(1.0, t / 0.8)
        centered(d, (640, 280), f'盟军第 {k} 关', int(96 * (0.9 + 0.1 * a)), (int(255 * a),) * 3, stroke=4)
        centered(d, (640, 400), title, 56, (200, 225, 255))
        centered(d, (640, 480), INTRO_TEXT, 40, (160, 190, 230))
        d.rectangle((240, 600, 1040, 624), outline=(200, 225, 255), width=3)
        d.rectangle((244, 604, 244 + int(792 * t / seconds), 620), fill=(120, 190, 255))
        centered(d, (640, 660), f'{t:4.1f} s', 28, (160, 190, 230))
        return img

    if not os.path.exists(path):
        _write_mp4(path, (1280, 720), seconds, frame)
    return _to_vp6(path, 'full')


def head_clip():
    """8 seconds, 288 x 288: Voss's portrait with a slow zoom and a sway (no lips: a still stands in for the talking video)."""
    import math
    from PIL import Image
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, 'voss_head.mp4')
    src = Image.open(VOSS).convert('RGB')

    def frame(t, i):
        z = 1.0 + 0.012 * t
        side = src.width * 0.9 / z
        cx = src.width / 2 + 10 * math.sin(t * 1.3)
        box = (cx - side / 2, src.height * 0.02, cx + side / 2, src.height * 0.02 + side)
        return src.resize((288, 288), Image.LANCZOS, box=box)

    if not os.path.exists(path):
        _write_mp4(path, (288, 288), 8, frame)
    return _to_vp6(path, 'radar')


# ---- the shell -----------------------------------------------------------------------------------------------------

def slot_of(mission_name):
    got = SLOT_OF.get(mission_name) or (int(m.group(1)) if (m := re.search(r'A(\d)', mission_name)) else None)
    if not got:
        raise SystemExit(f'shell: {mission_name!r} is no Allied mission (slot unknown: add it to shell.SLOT_OF)')
    return got


def commander_text(k, title, info):
    objectives = '\n'.join(f'{n}. {o}' for n, o in enumerate(info['objectives'], 1))
    return f'{title}（任务说明）\n{info["briefing"]}\n{objectives}'


def make(mission_title, mission_name='CampA4'):
    """Everything the shell adds to the build of `mission_name` (the plan's `名字` / title, in the briefing's mission list)."""
    slot = slot_of(mission_name)
    info = missions()
    info[slot] = dict(info[slot], title=TITLE, short=SHORT)             # the built mission's names are the plan's
    sp = Shell(slot=slot)
    sp.template = {'no_portrait': True}
    for k, m in info.items():
        attrs = {'OverviewTalkingHead': HEAD_ID, 'IntroMovie:FileName': intro_id(k),
                 'IntroMovie:ScreenName': f'MissionName:{label(k)}', 'IntroMovie:Description': f'MissionDesc:{label(k)}',
                 'AICommander:Description': f'CommanderDescription:{label(k)}'}
        if k == slot:
            sp.attrs = attrs
        else:
            sp.others[k] = attrs
        sp.clips[intro_id(k)] = intro_clip(k, m['title'])
        sp.strings.update({f'MissionName:{label(k)}': m['title'], f'MissionName:{label(k)}_Short': m['short'],
                           f'MissionDesc:{label(k)}': INTRO_TEXT + '：' + m['title'],
                           f'BriefingSummary:{label(k)}': m['briefing'],
                           f'CommanderDescription:{label(k)}': commander_text(k, m['title'], m),
                           f'MISSIONOBJ:{label(k)}_1': m['objectives'][0], f'MISSIONOBJ:{label(k)}_2': m['objectives'][1]})
    sp.strings.update(narration_strings(info))
    sp.clips[HEAD_ID] = head_clip()
    sp.files = apt_files({k: (m['short'], k == slot) for k, m in info.items()})
    sp.overrides = {'APT:ALLIES_FACTION_DESCRIPTION': CARD_TEXT}
    return sp
