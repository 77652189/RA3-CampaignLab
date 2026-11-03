"""The campaign shell probe (ADR 0014, 2026-11-02): our level in the place of retail's first Allied mission, wearing our own
front end -- mission name and briefing text, a test full-screen movie before the mission, the co-op overview's talking head,
placeholder pictures in the briefing screens and on the faction card. One mod, `CampShell`, started by its own launcher
(Play_CampShell.bat: RA3.exe -modConfig); retail started directly is not touched (nothing is written outside Mods\\CampShell).

  python -I -X utf8 experimental/cnv/build.py a4 --shell     -> Documents\\Red Alert 3\\Mods\\CampShell

What the probe asks of the game (the answers are in docs/story/handoff.md):
  - the campaign list / briefing show our strings (a new template, Allies_New, in Allies_1's place; strings from the mod's csf);
  - IntroMovie and OverviewTalkingHead name videos of ours (experimental/video/pack.py declares them, the clips ride in the big);
  - a retail APT screen's pictures can be replaced by a mod: the stream's Texture instances rewritten (campaign/apt_textures.py)
    for the objective briefing (the map and its arrow), the global briefing (three framed pictures) and the faction menu
    (the Allies card, normal and highlighted);
  - a retail label (the card's text) can be overwritten from the mod's csf (make_campnew3.OVERRIDES).
The mission's own briefing name and summary come from the plan (`名字`, `简报`).
"""
import os
import subprocess
import sys
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'campaign'))
import apt_textures                                     # noqa: E402

NAME = os.environ.get('CNV_SHELL_NAME', 'CampShell')    # at most 15 characters, letters and digits (parts.assemble asserts it)
INTRO_ID = 'CNVINTRO01'             # the full-screen movie before the mission (IntroMovie)
HEAD_ID = 'CNVHEAD01'               # the overview's talking head (OverviewTalkingHead): radar-sized
WORK = os.path.join(ROOT, 'work', 'shell')
TO_VP6 = os.path.join(ROOT, 'experimental', 'video', 'to_vp6.py')
VOSS = os.path.join(os.path.dirname(ROOT), 'RA3-ChineseVoice', 'third_party', 'comfyui', 'input', 'voss_p1.png')
MAP_PICTURE = os.path.join(ROOT, 'work', 'maps', 'CampA4_mcp.png')       # cnv_preview's picture of the map from above
FONT = r'C:\Windows\Fonts\msyhbd.ttc'
B = chr(92)
APT = 'data' + B + 'aptui' + B

TITLE = '札幌雪祭 · 号角与冰墙'
SHORT = '札幌雪祭'
INTRO_TEXT = '战前全屏视频（测试用）'
OBJECTIVES = ['把车队护送到港口，至少两辆到达', '拆掉北营的指挥所，打开最后一程']
CARD_TEXT = '盟军战役（占位）：札幌雪祭的雪祭会场里，号角一响，三条街的地道同时出兵。'
ARTWORK = {                         # APT stream -> {texture id: (what it is on the screen)}
    'a01_objective_briefing': ('apt_A01_Objective_Briefing_1', 'apt_A01_Objective_Briefing_2'),
    'a01_global_briefing': ('apt_A01_Global_Briefing_1',),
    'fes_m_factionmenu': ('apt_fes_m_factionMenu_1',),
}


@dataclass
class Shell:
    attrs: dict = field(default_factory=dict)       # MissionTemplate attributes (make_campnew2.SHELL)
    template: dict = field(default_factory=dict)    # the rest of make_campnew2.SHELL: 'base' (the retail template copied), 'replace'
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

def map_picture(size):
    """The A4 map from above in the briefing's amber, `size` square."""
    from PIL import Image, ImageDraw, ImageOps
    img = ImageOps.colorize(Image.open(MAP_PICTURE).convert('L'), black=(14, 6, 0), white=(255, 160, 60))
    img = img.resize((size, size), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, size - 1, size - 1), outline=(200, 110, 30), width=3)
    centered(d, (size // 2, size - 40), SHORT + '（占位图）', 40, (255, 220, 160), stroke=3)
    return img


def objective_map(orig):
    from PIL import Image
    out = Image.new('RGBA', orig.size, (0, 0, 0, 255))
    out.paste(map_picture(1002), (0, 0))
    return out


def objective_arrow(orig):
    """The red arrow of the map screen, recoloured to ice blue (red and blue channels swapped)."""
    from PIL import Image
    r, g, b, a = orig.convert('RGBA').split()
    return Image.merge('RGBA', (b, g, r, a))


def global_pictures(orig):
    """The overview's three framed pictures (276 x 326 at x 5, 301, 597): inside the frames, the map from above, Voss, and a card."""
    from PIL import Image, ImageDraw
    out = orig.convert('RGBA').copy()
    inner = (260, 310)
    pics = []
    m = map_picture(1000).crop((120, 0, 880, 1000)).resize(inner, Image.LANCZOS)
    pics.append(m)
    v = Image.open(VOSS).convert('RGBA')
    pics.append(v.crop((120, 0, 1134, 1254)).resize(inner, Image.LANCZOS))
    card = Image.new('RGBA', inner, (20, 50, 100, 255))
    d = ImageDraw.Draw(card)
    for y in range(inner[1]):
        t = y / inner[1]
        d.line((0, y, inner[0], y), fill=(int(30 + 90 * t), int(70 + 130 * t), int(130 + 110 * t), 255))
    centered(d, (inner[0] // 2, 110), SHORT, 56, (255, 255, 255), stroke=3, stroke_fill=(10, 30, 70))
    centered(d, (inner[0] // 2, 190), '占位图', 34, (230, 240, 255), stroke=2, stroke_fill=(10, 30, 70))
    pics.append(card)
    for x0, pic in zip((5, 301, 597), pics):
        out.paste(pic, (x0 + 8, 13))
    return out


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
        centered(d, (w // 2, h // 2 + 40), SHORT, 62, (235, 245, 255), stroke=3, stroke_fill=(10, 30, 80))
        centered(d, (w // 2, h // 2 + 120), '占位卡片', 36, (210, 230, 255), stroke=2, stroke_fill=(10, 30, 80))
        d.rectangle((0, 0, w - 1, h - 1), outline=(240, 170, 100, 255), width=2)
        out.paste(card, (x0, y0))
    return out


PICTURES = {'apt_A01_Objective_Briefing_1': objective_map, 'apt_A01_Objective_Briefing_2': objective_arrow,
            'apt_A01_Global_Briefing_1': global_pictures, 'apt_fes_m_factionMenu_1': faction_card}


def apt_files():
    """The three APT streams with our pictures: [(big path, bytes)]. Only the .bin carries pictures; the other three files
    of a stream are the retail ones byte for byte (checked by tests/test_shell.py), so they are not shipped."""
    files = []
    for stem, texs in ARTWORK.items():
        prefix = APT + stem + '.'
        orig = apt_textures.originals('Apt.big', prefix)
        images = {t: PICTURES[t](orig[t]) for t in texs}
        files += [(p, v) for p, v in apt_textures.patch('Apt.big', prefix, images) if p.endswith('.bin')]
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


def intro_clip():
    """4 seconds, 1280 x 720: dark blue, the title, a bar filling up (so a frozen picture is told from a playing one)."""
    from PIL import Image, ImageDraw
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, 'intro.mp4')
    seconds = 4

    def frame(t, k):
        img = Image.new('RGB', (1280, 720), (6, 14, 30))
        d = ImageDraw.Draw(img)
        for y in range(720):
            c = int(10 + 40 * y / 720)
            d.line((0, y, 1280, y), fill=(c // 3, c // 2, c))
        a = min(1.0, t / 0.8)
        centered(d, (640, 280), 'CNV 战役外壳探针', int(96 * (0.9 + 0.1 * a)), (int(255 * a),) * 3, stroke=4)
        centered(d, (640, 400), TITLE, 56, (200, 225, 255))
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

    def frame(t, k):
        z = 1.0 + 0.012 * t
        side = src.width * 0.9 / z
        cx = src.width / 2 + 10 * math.sin(t * 1.3)
        box = (cx - side / 2, src.height * 0.02, cx + side / 2, src.height * 0.02 + side)
        return src.resize((288, 288), Image.LANCZOS, box=box)

    if not os.path.exists(path):
        _write_mp4(path, (288, 288), 8, frame)
    return _to_vp6(path, 'radar')


# ---- the probe -----------------------------------------------------------------------------------------------------

def make(mission_name):
    """Everything the probe adds to the build of `mission_name` (the plan's `名字`, in the briefing's mission list)."""
    sp = Shell()
    sp.attrs = {'OverviewTalkingHead': HEAD_ID,
                'IntroMovie:FileName': INTRO_ID,
                'IntroMovie:ScreenName': 'MissionName:CNV01',
                'IntroMovie:Description': 'MissionDesc:CNV01'}
    keep = [p.strip() for p in os.environ.get('CNV_SHELL_KEEP', '').split(',')]    # bisecting a crash: retail's field / pictures
    for part in keep:
        sp.attrs.pop(part, None)
    if os.environ.get('CNV_SHELL_BASE'):                # bisecting: a template copied from another mission / put in front
        sp.template['base'] = os.environ['CNV_SHELL_BASE']
    if os.environ.get('CNV_SHELL_FRONT'):
        sp.template['replace'] = False
    sp.clips = {INTRO_ID: intro_clip(), HEAD_ID: head_clip()}
    sp.files = [] if 'apt' in keep else apt_files()
    sp.strings = {'MissionName:CNV01': TITLE, 'MissionName:CNV01_Short': SHORT,
                  'MissionDesc:CNV01': '战前全屏视频（测试用）：' + mission_name,
                  'MISSIONOBJ:CNV01_1': OBJECTIVES[0], 'MISSIONOBJ:CNV01_2': OBJECTIVES[1]}
    sp.overrides = {'APT:ALLIES_FACTION_DESCRIPTION': CARD_TEXT}
    return sp
