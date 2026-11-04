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
HEAD_ID = 'CNVHEAD01'               # the overview's talking head (OverviewTalkingHead), shared by every slot
HEAD_SIZE = (512, 288)              # retail's AMB01..09.vp6 (MVhd), the frame on the overview is drawn at this ratio
WORK = os.path.join(ROOT, 'work', 'shell')
TO_VP6 = os.path.join(ROOT, 'experimental', 'video', 'to_vp6.py')
VOSS = os.path.join(os.path.dirname(ROOT), 'RA3-ChineseVoice', 'third_party', 'comfyui', 'input', 'voss_p1.png')
MAP_PICTURE = os.path.join(ROOT, 'work', 'maps', 'CampA4_mcp.png')       # cnv_preview's picture of the map from above
FONT = r'C:\Windows\Fonts\msyhbd.ttc'
B = chr(92)
APT = 'data' + B + 'aptui' + B
OWN_STEM = 'camp_cnv01_probe'               # the built mission's map folder and file stem (make_campnew2.NEW_STEM)
PANEL = 'tacticalhudcoopaiorderpanel'       # the HUD's co-op commander panel (portrait, four buttons, the defence-state bar)

# The words of the shell, by edition (langs.py: zh, intl). The built mission's own names are the plan's; the other slots' come
# from shell_missions[.en].json (docs/design/flow/a<k>.md, the English a translation of them). `make(.., lang)` picks the
# edition, the picture functions below read it from T.
TEXTS = {
    'zh': dict(title='札幌雪祭 · 号角与冰墙', short='札幌雪祭', file='shell_missions.json',
               intro='战前全屏视频（占位）', colon='：', semi='；', note='（任务说明）', narr='（占位旁白）',
               card='盟军战役（占位）：札幌雪祭的雪祭会场里，号角一响，三条街的地道同时出兵。',
               mission='盟军第 {k} 关', pic='占位图', pic_of='（占位图）', intel='情报', goals='目标',
               card_lines=('CNV', '占位卡片'), faction=dict(allies='战役实验室', soviet='苏军战役', empire='帝国战役'),
               notes_title='任务说明', other_card='（占位）：这一战役还没做。', other_name='{side} 第 {k} 关（占位）', other_short='{side} {k}'),
    'intl': dict(title='Sapporo Snow Festival · Horns and Ice Walls', short='Ice Soldiers', file='shell_missions.en.json',
                 intro='Pre-mission movie (placeholder)', colon=': ', semi='; ', note=' (mission notes)', narr='(placeholder narration) ',
                 card='Allied campaign (placeholder): at the Sapporo snow festival, one blast of the horn and the tunnels of three streets send out their troops.',
                 mission='Allied Mission {k}', pic='Placeholder', pic_of=' (placeholder)', intel='Intel', goals='Goals',
                 card_lines=('CNV', 'Placeholder card'), faction=dict(allies='Campaign Lab', soviet='Soviet campaign', empire='Empire campaign'),
                 notes_title='Mission notes', other_card=' (placeholder): this campaign is not made yet.', other_name='{side} mission {k} (placeholder)', other_short='{side} {k}'),
}
T = TEXTS['zh']
TITLE, SHORT = T['title'], T['short']
SLOT_OF = {'CampA4': 4, 'CampA4En': 4}


def use_lang(lang):
    global T, TITLE, SHORT
    T = TEXTS[lang]
    TITLE, SHORT = T['title'], T['short']


def missions():
    with open(os.path.join(HERE, T['file']), encoding='utf-8') as f:
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
    prefix_overrides: dict = field(default_factory=dict)    # label prefix -> text, every retail label that starts so


def font(size):
    from PIL import ImageFont
    return ImageFont.truetype(FONT, size, index=0)


def centered(draw, xy_center, text, size, fill, stroke=0, stroke_fill=(0, 0, 0)):
    x, y = xy_center
    f = font(size)
    l, t, r, b = draw.textbbox((0, 0), text, font=f, stroke_width=stroke)
    draw.text((x - (l + r) / 2, y - (t + b) / 2), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


# ---- pictures ----------------------------------------------------------------------------------------------------

def map_picture(size, short=None, real=True, label=True):
    """The briefing's map picture, `size` (w, h) or a square side: the built mission's map from above in the briefing's amber, or
    (a slot with no map of ours) an amber grid with the name and 'placeholder'."""
    from PIL import Image, ImageDraw, ImageOps
    w, h = (size, size) if isinstance(size, int) else size
    short = short or SHORT
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
        centered(d, (int(w * 0.32), h // 2 - 30), short, max(20, w // 16), (255, 190, 100), stroke=3)    # (the screen shows the left part)
    d.rectangle((0, 0, w - 1, h - 1), outline=(200, 110, 30), width=3)
    if label:
        centered(d, (int(w * 0.32), h - 40), short + T['pic_of'] if real else T['pic'], 40, (255, 220, 160), stroke=3)
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
            pics = [m, v, name_card(inner, [(short, 56, 110), (T['pic'], 34, 190)])]
        else:
            pics = [name_card(inner, [(short, 52, 110), (T['pic'], 34, 190)]),
                    name_card(inner, [(T['intel'], 56, 110), (T['pic'], 34, 190)]),
                    name_card(inner, [(T['goals'], 56, 110), (T['pic'], 34, 190)])]
        for x0, pic in zip((5, 301, 597), pics):
            out.paste(pic, (x0 + 8, 13))
        return out
    return paint


# ---- the overview's world map ----------------------------------------------------------------------------------------
# Retail's world map (global_map2 of fe_missionBriefingAssets, only panned and zoomed by each overview) is a plain latitude /
# longitude grid. Fitted on the 23 retail overviews of a known place (2026-11-03: the marker's first stop minus the map's
# offset, in the map's own pixels): x = 1182.7 + 3.792 (lon - 139.84), repeating every 360 degrees, y = 431.7 - 3.821 lat;
# the retail markers sit within 10 px (x) and 5 px (y) rms of it (they were placed by hand).
GRID = dict(x0=1182.7, lon0=139.84, px_lon=3.792, y0=431.7, px_lat=-3.821)
MARKER = ('brackets square', 'flashing square', 'line')     # the marker: its brackets, its flashing square, the crosshair


def grid(lat, lon):
    return GRID['x0'] + GRID['px_lon'] * (lon - GRID['lon0']), GRID['y0'] + GRID['px_lat'] * lat


def marked(m, apt):
    """Where on the map a retail overview points: its marker's first stop (the flashing square, both at scale 1) minus the
    map's offset at that frame."""
    import apt_movie
    world, square = m['imports']['global_map2'], m['imports']['flashing square']
    at = None
    for it in apt_movie.placements(m, apt):
        if it.char == world and it.flags & apt_movie.HAS_MATRIX:
            at = it
        elif it.char == square and it.flags & apt_movie.HAS_CHARACTER and at and abs(it.matrix[0] - 1) < .01 and abs(at.matrix[0] - 1) < .01:
            return it.translate[0] - at.translate[0], it.translate[1] - at.translate[1]
    raise ValueError('no marker on the world map')


def retarget(where):
    """The overview's timeline pointing at `where` (lat, lon) instead of its retail place, the difference (dx, dy) in map
    pixels: the marker (brackets, flashing square, crosshair) moves down by dy, the map pans further by zoom * dx and up by
    (zoom - 1) * dy at every frame. So the place lies under the marker at every zoom, and at zoom 1 (the whole world) the
    map's vertical framing is retail's: no edge of the map comes into view."""
    def edit(apt, const):
        import apt_movie
        m = apt_movie.movie(apt, const)
        (ox, oy), (nx, ny) = marked(m, apt), grid(*where)
        period = 360 * GRID['px_lon']
        dx, dy = (nx - ox + period / 2) % period - period / 2, ny - oy
        world, marks = m['imports']['global_map2'], {m['imports'][n] for n in MARKER}
        buf = bytearray(apt)
        for it in apt_movie.placements(m, apt):
            if not it.flags & apt_movie.HAS_MATRIX:
                continue
            a, b, c, d = it.matrix
            x, y = it.translate
            if it.char == world:
                assert abs(b) < 1e-6 and abs(c) < 1e-6, f'frame {it.frame}: the map is turned'
                apt_movie.move(buf, it, (x - a * dx, y - (d - 1) * dy))
            elif it.char in marks:
                apt_movie.move(buf, it, (x, y + dy))
        return bytes(buf)
    return edit


# The cards of the faction menu, by texture: {faction: [boxes]} (normal first, then highlighted) -- found from the orange outline
# of the retail cards (2026-11-03): Allies and (a second copy of) the Empire in texture 1, the Empire and the Soviets in texture 3.
CARD_BOXES = {
    'apt_fes_m_factionMenu_1': {'allies': [(1652, 0, 1908, 441), (1652, 455, 1908, 894)], 'empire': [(1369, 563, 1625, 1002)]},
    'apt_fes_m_factionMenu_3': {'empire': [(2, 1, 258, 440)], 'soviet': [(272, 1, 528, 440), (542, 1, 798, 440)]},
}
# card colours: the gradient's top and bottom RGB, the lettering's outline
CARD_COLOURS = {'allies': ((135, 210, 250), (15, 50, 120), (10, 30, 80)), 'soviet': ((230, 60, 40), (70, 8, 8), (70, 10, 10)),
                'empire': ((200, 200, 215), (60, 60, 85), (30, 30, 55))}


def faction_cards(orig, boxes):
    """The texture with each faction's cards repainted as a placeholder card (gradient, 'CNV', the faction's line, 'placeholder')."""
    from PIL import Image, ImageDraw
    out = orig.convert('RGBA').copy()
    for faction, where in boxes.items():
        top, bottom, edge = CARD_COLOURS[faction]
        for k, (x0, y0, x1, y1) in enumerate(where):
            w, h = x1 - x0, y1 - y0
            card = Image.new('RGBA', (w, h), (0, 0, 0, 255))
            d = ImageDraw.Draw(card)
            for y in range(h):
                t = y / h
                d.line((0, y, w, y), fill=tuple(min(255, int(bottom[c] + (top[c] - bottom[c]) * (1 - t)) + 40 * k) for c in range(3)) + (255,))
            big, small = T['card_lines']
            centered(d, (w // 2, h // 2 - 70), big, 110, (255, 255, 255), stroke=4, stroke_fill=edge)
            centered(d, (w // 2, h // 2 + 40), T['faction'][faction], 50, (245, 245, 245), stroke=3, stroke_fill=edge)
            centered(d, (w // 2, h // 2 + 120), small, 36, (225, 225, 225), stroke=2, stroke_fill=edge)
            d.rectangle((0, 0, w - 1, h - 1), outline=(240, 170, 100, 255), width=2)
            out.paste(card, (x0, y0))
    return out


# The chapter list's three faction icons (Soviet, Allied, Japanese flags), by stream: the mouse UI's and the gamepad UI's
# copy -- found from the opaque boxes of the components' only texture (2026-11-03).
ICON_BOXES = {'mouse_chapterselectcomponent': {'soviet': [(1, 1, 127, 88)], 'allies': [(129, 1, 255, 88)], 'empire': [(1, 90, 127, 177)]},
              'chapterselectcomponent': {'soviet': [(1, 1, 82, 48)], 'allies': [(84, 1, 165, 48)], 'empire': [(1, 50, 82, 97)]}}


def faction_icons(orig, boxes):
    """The texture with each faction's icon repainted as a placeholder: the card's gradient and 'CNV'."""
    from PIL import Image, ImageDraw
    out = orig.convert('RGBA').copy()
    for faction, where in boxes.items():
        top, bottom, edge = CARD_COLOURS[faction]
        for (x0, y0, x1, y1) in where:
            w, h = x1 - x0, y1 - y0
            icon = Image.new('RGBA', (w, h))
            d = ImageDraw.Draw(icon)
            for y in range(h):
                t = y / h
                d.line((0, y, w, y), fill=tuple(int(bottom[c] + (top[c] - bottom[c]) * (1 - t)) for c in range(3)) + (255,))
            centered(d, (w // 2, h // 2), T['card_lines'][0], max(12, h // 3), (255, 255, 255), stroke=2, stroke_fill=edge)
            d.rectangle((0, 0, w - 1, h - 1), outline=(240, 170, 100, 255), width=1)
            out.paste(icon, (x0, y0))
    return out


PORTRAIT_CALL = re.compile(rb'RenderImage')     # the panel's script asks the engine to draw the commander's picture; nobody answers 'RenderImagx'
MONITOR = ['ASSAULT', 'ATTACKING', 'BUILDINGAIRCRAFT', 'BUILDINGFORCES', 'BUILDINGNAVY', 'BUILDINGVEHICLES', 'DEFENDING',
           'EXPANDING', 'HOLDOBJECT', 'HOLDPOSITION', 'INCOMBAT', 'INDANGER', 'LOWONCREDITS', 'LOWONPOWER', 'NORMAL', 'ONGUARD',
           'PREPARINGSTRIKE', 'RUSHING', 'SENDINGFORCES', 'TECHINGUP', 'TRAININGINFANTRY']      # the panel's state texts ("防御状态" ...)

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
            out[f'DIALOGEVENT:{new}'] = {1: T['narr'] + m['briefing'], 2: T['narr'] + T['semi'].join(m['objectives'])}.get(
                line, f'{T["narr"]}{m["title"]}')
    return out


def apt_files(slots):
    """The APT streams with our pictures and the emptied co-op panel: [(big path, bytes)]. `slots`: {slot: (short name, built
    mission?, (lat, lon))}. Only the .bin carries pictures / shapes / timelines; the other three files of a stream are the
    retail ones byte for byte (checked by tests/test_shell.py), so they are not shipped."""
    files = []

    def add(stem, make):
        prefix = APT + stem + '.'
        files.extend((p, v) for p, v in make(prefix) if p.endswith('.bin'))

    for k, (short, built, where) in slots.items():
        def painted(prefix, k=k, short=short, built=built, renames=None, movie=None):
            orig = apt_textures.originals('Apt.big', prefix)
            kinds = {'Objective_Briefing_1': objective_map(short, built), 'Objective_Briefing_2': objective_arrow,
                     'Global_Briefing_1': global_pictures(short, built)}
            images = {t: kinds[t[len(f'apt_A{k:02d}_'):]](orig[t]) for t in orig if t[len(f'apt_A{k:02d}_'):] in kinds}
            return apt_textures.patch('Apt.big', prefix, images, renames, movie)
        add(f'a{k:02d}_objective_briefing', lambda prefix, painted=painted: painted(prefix, renames=(EVENT, new_event)))
        add(f'a{k:02d}_global_briefing', lambda prefix, painted=painted, where=where: painted(prefix, movie=retarget(where)))
    add('fes_m_factionmenu', lambda prefix: apt_textures.patch(
        'Apt.big', prefix, {t: faction_cards(apt_textures.originals('Apt.big', prefix)[t], boxes) for t, boxes in CARD_BOXES.items()}))
    for stem, boxes in ICON_BOXES.items():
        add(stem, lambda prefix, boxes=boxes: apt_textures.patch('Apt.big', prefix, {
            t: faction_icons(img, boxes) for t, img in apt_textures.originals('Apt.big', prefix).items()}))
    add(PANEL, lambda prefix: apt_textures.hollow('Apt.big', prefix, (PORTRAIT_CALL, lambda old: old[:-1] + b'x')))
    return files


# ---- the chapter list's thumbnails ----------------------------------------------------------------------------------------

def retail_map_stems():
    """{slot: 'camp_a01_...' (the map's folder, which is also the map's file stem)}: retail's Allied missions' maps."""
    import labpaths
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'CampaignTemplates.xml'), encoding='ascii') as f:
        xml = f.read()
    return {k: re.search(rf'<MissionTemplate\s+id="Allies_{k}".*?MapName="[^"]*?([^\\\\]+)\.map"', xml, re.S).group(1).lower()
            for k in range(1, 10)}


def thumbnail(short, real, size=128):
    """A picture of a map as retail's files are: 128 x 128 uncompressed 32-bit TGA (<map>.tga), or 512 x 512 24-bit (<map>_art.tga)."""
    import io
    from PIL import Image
    img = map_picture(size, short, True, False).convert('RGBA') if real else name_card((size, size), [(short, size // 6, size * 0.4), (T['pic'], size // 9, size * 0.7)])
    buf = io.BytesIO()
    img.convert('RGBA' if size == 128 else 'RGB').save(buf, 'TGA')
    return buf.getvalue()


def thumbnails(slots):
    """[(big path, bytes)]: a mission's map picture is the file <its map folder>\\\\<stem>.tga; the built mission's is in the new
    folder (the build puts it there: make_campnew2.map_files), the others replace the retail folders' files (this mod's big
    only: retail's are not touched)."""
    out = []
    for k, stem in retail_map_stems().items():
        short, built, _ = slots[k]
        if built:
            stem = OWN_STEM
        out.append((f'data{B}maps{B}official{B}{stem}{B}{stem}.tga', thumbnail(short, built)))
        out.append((f'data{B}maps{B}official{B}{stem}{B}{stem}_art.tga', thumbnail(short, built, 512)))
    return out


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
    path = os.path.join(WORK, f'intro{k}.mp4' if T is TEXTS['zh'] else f'intro_en{k}.mp4')
    seconds = 4

    def frame(t, i):
        img = Image.new('RGB', (1280, 720), (6, 14, 30))
        d = ImageDraw.Draw(img)
        for y in range(720):
            c = int(10 + 40 * y / 720)
            d.line((0, y, 1280, y), fill=(c // 3, c // 2, c))
        a = min(1.0, t / 0.8)
        centered(d, (640, 280), T['mission'].format(k=k), int(96 * (0.9 + 0.1 * a)), (int(255 * a),) * 3, stroke=4)
        centered(d, (640, 400), title, 56, (200, 225, 255))
        centered(d, (640, 480), T['intro'], 40, (160, 190, 230))
        d.rectangle((240, 600, 1040, 624), outline=(200, 225, 255), width=3)
        d.rectangle((244, 604, 244 + int(792 * t / seconds), 620), fill=(120, 190, 255))
        centered(d, (640, 660), f'{t:4.1f} s', 28, (160, 190, 230))
        return img

    if not os.path.exists(path):
        _write_mp4(path, (1280, 720), seconds, frame)
    return _to_vp6(path, 'full')


def head_clip():
    """8 seconds, 512 x 288 like retail's AMB*.vp6 (the overview's frame is 16:9; a square clip was stretched into it):
    Voss's portrait with a slow zoom and a sway (no lips: a still stands in for the talking video)."""
    import math
    from PIL import Image
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, 'voss_head169.mp4')
    src = Image.open(VOSS).convert('RGB')
    w, h = HEAD_SIZE

    def frame(t, i):
        z = 1.0 + 0.012 * t
        bw = min(src.width, src.height * w / h) * 0.95 / z
        bh = bw * h / w
        cx = src.width / 2 + 10 * math.sin(t * 1.3)
        box = (cx - bw / 2, src.height * 0.02, cx + bw / 2, src.height * 0.02 + bh)
        return src.resize((w, h), Image.LANCZOS, box=box)

    if not os.path.exists(path):
        _write_mp4(path, (w, h), 8, frame)
    return _to_vp6(path, 'head')


# ---- the shell -----------------------------------------------------------------------------------------------------

def slot_of(mission_name):
    got = SLOT_OF.get(mission_name) or (int(m.group(1)) if (m := re.search(r'A(\d)', mission_name)) else None)
    if not got:
        raise SystemExit(f'shell: {mission_name!r} is no Allied mission (slot unknown: add it to shell.SLOT_OF)')
    return got


def commander_text(k, title, info):
    objectives = '\n'.join(f'{n}. {o}' for n, o in enumerate(info['objectives'], 1))
    return f'{title}{T["note"]}\n{info["briefing"]}\n{objectives}'


def make(mission_title, mission_name='CampA4', lang='zh'):
    """Everything the shell adds to the build of `mission_name` (the plan's `名字` / title, in the briefing's mission list) in the
    edition `lang` (langs.py: zh, intl; the words of the shell are TEXTS)."""
    use_lang(lang)
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
                           f'MissionDesc:{label(k)}': T['intro'] + T['colon'] + m['title'],
                           f'BriefingSummary:{label(k)}': m['briefing'],
                           f'CommanderDescription:{label(k)}': commander_text(k, m['title'], m),
                           f'MISSIONOBJ:{label(k)}_1': m['objectives'][0], f'MISSIONOBJ:{label(k)}_2': m['objectives'][1]})
    sp.strings.update(narration_strings(info))
    sp.clips[HEAD_ID] = head_clip()
    slots = {k: (m['short'], k == slot, tuple(m['where'])) for k, m in info.items()}
    sp.files = apt_files(slots) + thumbnails(slots)
    sp.overrides = {'APT:ALLIES_FACTION_DESCRIPTION': T['card'], **{f'MONITOR:{k}': ' ' for k in MONITOR},
                    **{f'APT:{k}': T['notes_title'] for k in ('COCOMMANDER_NAME_TITLE', 'COCOMMANDER', 'YOUR_CO_COMMANDER',
                                                              'SELECT_YOUR_AI_CO_COMMANDER')}}   # the overview tab's head ("副指挥官")
    sp.prefix_overrides = {'PERSONALITY:': '—'}         # the co-op commanders' names (the briefing's team column)
    for key, side, desc in (('SOVIETS', 'soviet', 'APT:SOVIET_FACTION_DESCRIPTION'), ('JAPAN', 'empire', 'APT:JAPANESE_FACTION_DESCRIPTION')):
        sp.overrides[desc] = T['faction'][side] + T['other_card']        # the other two campaigns: placeholders (names, cards, texts)
        for k in range(1, 10):
            sp.overrides[f'MISSIONNAME:{key}_{k}'] = T['other_name'].format(side=T['faction'][side], k=k)
            sp.overrides[f'MISSIONNAME:{key}_{k}_SHORT'] = T['other_short'].format(side=T['faction'][side], k=k)
    return sp
