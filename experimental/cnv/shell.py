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
# The built mission's map from above for players (ground only, no debug labels): maprender.py <built mod> --plain -o this
MAP_PICTURE = os.path.join(ROOT, 'work', 'shell', 'map_plain.png')
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
               notes_title='任务说明', goal='目标{n}：{text}', closing='指挥官，两个目标都已标在地图上。',
               other_card='（占位）：这一战役还没做。', other_name='{side} 第 {k} 关（占位）', other_short='{side} {k}',
               officer='莉娜·沃斯', officer_title='情报官'),
    'intl': dict(title='Sapporo Snow Festival · Horns and Ice Walls', short='Sapporo Snow Festival', file='shell_missions.en.json',
                 intro='Pre-mission movie (placeholder)', colon=': ', semi='; ', note=' (mission notes)', narr='(placeholder narration) ',
                 card='Allied campaign (placeholder): at the Sapporo snow festival, one blast of the horn and the tunnels of three streets send out their troops.',
                 mission='Allied Mission {k}', pic='Placeholder', pic_of=' (placeholder)', intel='Intel', goals='Goals',
                 card_lines=('CNV', 'Placeholder card'), faction=dict(allies='Campaign Lab', soviet='Soviet campaign', empire='Empire campaign'),
                 notes_title='Mission notes', goal='Objective {n}: {text}', closing='Commander, both objectives are marked on the map.',
                 other_card=' (placeholder): this campaign is not made yet.', other_name='{side} mission {k} (placeholder)', other_short='{side} {k}',
                 officer='Lena Voss', officer_title='Intel officer'),
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
    map_files: tuple = ()                           # f(MapFile) -> files drawn from the built map (make(.., later=True))
    drawn: dict = field(default_factory=dict)       # the same per built slot: {slot: f(MapFile) -> files} (make_slots)


def font(size):
    from PIL import ImageFont
    return ImageFont.truetype(FONT, size, index=0)


def centered(draw, xy_center, text, size, fill, stroke=0, stroke_fill=(0, 0, 0), width=None):
    """`text` centred on xy_center; width: at most this wide (the font shrinks till it fits: I17, a long English name
    ran off both sides of its card)."""
    x, y = xy_center
    f = font(size)
    l, t, r, b = draw.textbbox((0, 0), text, font=f, stroke_width=stroke)
    while width and r - l > width and size > 8:
        size -= 2
        f = font(size)
        l, t, r, b = draw.textbbox((0, 0), text, font=f, stroke_width=stroke)
    draw.text((x - (l + r) / 2, y - (t + b) / 2), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


# ---- pictures ----------------------------------------------------------------------------------------------------

def map_picture(size, short=None, real=True, label=True, picture=None):
    """The briefing's map picture, `size` (w, h) or a square side: the built mission's map from above (`picture`, a PIL
    image or a file; MAP_PICTURE by default) in the briefing's amber, or (a slot with no map of ours) an amber grid with
    the name and 'placeholder'."""
    from PIL import Image, ImageDraw, ImageOps
    w, h = (size, size) if isinstance(size, int) else size
    short = short or SHORT
    picture = picture if picture is not None else MAP_PICTURE
    if real and (not isinstance(picture, str) or os.path.exists(picture)):
        src = picture if not isinstance(picture, str) else Image.open(picture)
        img = ImageOps.colorize(src.convert('L'), black=(14, 6, 0), white=(255, 160, 60))
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


def objective_map(short, real, picture=None):
    """The objective briefing's map texture: our picture over the retail picture's opaque rectangle (no label: the screen
    names the mission above the map, and a label would sit under the zoom)."""
    def paint(orig):
        out = orig.convert('RGBA').copy()
        x0, y0, x1, y1 = orig.getchannel('A').getbbox()
        out.paste(map_picture((x1 - x0, y1 - y0), short, real, label=False, picture=picture).convert('RGBA'), (x0, y0))
        return out
    return paint


def name_card(inner, lines):
    from PIL import Image, ImageDraw
    card = Image.new('RGBA', inner, (20, 50, 100, 255))
    d = ImageDraw.Draw(card)
    for y in range(inner[1]):
        t = y / inner[1]
        d.line((0, y, inner[0], y), fill=(int(30 + 90 * t), int(70 + 130 * t), int(130 + 110 * t), 255))
    for (text, size, dy) in lines:
        centered(d, (inner[0] // 2, dy), text, size, (255, 255, 255), stroke=3, stroke_fill=(10, 30, 70),
                 width=inner[0] * 0.9)
    return card


def global_pictures(short, real, picture=None):
    """The overview's three framed pictures (276 x 326 at x 5, 301, 597): inside the frames, for the built mission the map from
    above, Voss and a card; for the other slots three cards."""
    def paint(orig):
        from PIL import Image
        out = orig.convert('RGBA').copy()
        inner = (260, 310)
        if real:
            m = map_picture(1000, picture=picture).crop((120, 0, 880, 1000)).resize(inner, Image.LANCZOS)
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


# The commander overview (fes_m_objectivesbriefing) is our intel officer's notes: no co-op commander comes with our missions.
# Its name bar carries a row of rating stars baked into the screen's texture, over a bar whose colour changes only along x.
STAR_BARS = {'apt_fes_m_objectivesBriefing_1': [(1620, 799, 1896, 822)]}


def destar(orig, boxes):
    """The texture with the stars gone from each box: every column of a box takes its unstarred pixel (the stars darken the
    bar, so the column's reddest pixel is the bar's own)."""
    out = orig.convert('RGBA').copy()
    px = out.load()
    for (x0, y0, x1, y1) in boxes:
        for x in range(x0, x1):
            bar = max((px[x, y] for y in range(y0, y1)), key=lambda p: p[0])
            for y in range(y0, y1):
                px[x, y] = bar
    return out


# The end-of-mission card (tacticalendgamedialog, I21): its textures hold every faction's victory and defeat poster; the
# Allied two (our campaign takes the Allied slot) carry retail's pin-up in a circle between two rules, her hands and flags
# reaching past it. The band between the rules is repainted: the paper's own colour row by row, Voss in the circle (grey
# and dark on the defeat card). Boxes and circles measured on the retail textures (2026-11-05, the teal circle's widest row).
END_CARDS = {'apt_TacticalEndGameDialog_2': [((20, 112, 336, 414), (173, 264, 141), 'victory')],
             'apt_TacticalEndGameDialog_3': [((375, 112, 691, 416), (529.5, 264.5, 140.5), 'defeat')]}


def end_cards(orig, cards):
    """The texture with each Allied end card's band repainted (END_CARDS)."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageOps
    out = orig.convert('RGBA').copy()
    px = out.load()
    for (x0, y0, x1, y1), (cx, cy, r), kind in cards:
        def paper(x, y):                        # the paper near (x, y): the median of the light pixels around (not burns)
            near = sorted((p[:3] for p in (px[u, v] for u in range(max(x0, x - 20), min(x1, x + 21))
                                           for v in (y - 2, y, y + 2)) if sum(p[:3]) > 330), key=sum)
            return near[len(near) // 2] if near else (225, 200, 150)
        rows = {x: (paper(x, y0 + 2), paper(x, y1 - 3)) for x in range(x0, x1)}
        for x in range(x0, x1):                 # each column blended from the band's top to its bottom
            top, bottom = rows[x]
            for y in range(y0, y1):
                t = (y - y0) / (y1 - 1 - y0)
                px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(top[:3], bottom[:3])) + (255,)
        side = int(2 * r)
        v = Image.open(VOSS).convert('RGBA').crop((120, 0, 1134, 1014)).resize((side, side), Image.LANCZOS)
        if kind == 'defeat':
            v = ImageEnhance.Brightness(ImageOps.grayscale(v).convert('RGBA')).enhance(0.6)
        mask = Image.new('L', (side, side))
        ImageDraw.Draw(mask).ellipse((0, 0, side - 1, side - 1), fill=255)
        out.paste(v, (int(cx - r), int(cy - r)), mask)
        ImageDraw.Draw(out).ellipse((cx - r, cy - r, cx + r, cy + r), outline=(150, 30, 30, 255), width=2)
    return out


PORTRAIT_CALL = re.compile(rb'RenderImage')     # the panel's script asks the engine to draw the commander's picture; nobody answers 'RenderImagx'
MONITOR = ['ASSAULT', 'ATTACKING', 'BUILDINGAIRCRAFT', 'BUILDINGFORCES', 'BUILDINGNAVY', 'BUILDINGVEHICLES', 'DEFENDING',
           'EXPANDING', 'HOLDOBJECT', 'HOLDPOSITION', 'INCOMBAT', 'INDANGER', 'LOWONCREDITS', 'LOWONPOWER', 'NORMAL', 'ONGUARD',
           'PREPARINGSTRIKE', 'RUSHING', 'SENDINGFORCES', 'TECHINGUP', 'TRAININGINFANTRY']      # the panel's state texts ("防御状态" ...)

# the retail briefing narration: the objective screens' scripts carry the table of all three campaigns' lines
EVENT = re.compile(rb'M([ASI])(\d\d)_(?:Allied|Soviet|Imperial)Intel(\d\d)', re.I)


# ---- the objective briefing (I11, K9) ------------------------------------------------------------------------------
# Retail's nine objective briefings are nine different timelines (A04 zooms three times and never back out, A01 never zooms
# out, A04 draws no arrow ...). Every slot of ours plays one of them, A07's (2026-11-04 survey of the nine): the whole map
# and the briefing; a zoom onto objective 1 where two arrows close in; back out to the whole map, objective 1 marked, a
# route of arrows to objective 2, objective 2 marked -- over each slot's own map shape and picture (apt_textures.patch,
# donor). Its five narration lines (frames 2, 179, 419, 509, 659) say, in order, LINES.
TEMPLATE = 7
TEMPLATE_LINES = (1, 2, 3, 4, 10)               # MA07_AlliedIntel<nn> in the order the timeline plays them
LINES = ('opening', 'objective 1', 'briefing rest', 'objective 2', 'closing')
SCREEN = (455, 474)                             # the briefing's map window (shape 1 of every objective briefing)
# Where A07 has its two objectives, in its map's own units (its markers' boxes on the whole map, frames 479 and 529, through
# the map's placement there): A is the first one marked, B the one its first zoom closes in on.
RETAIL_A, RETAIL_B = (148.8, 810.2), (789.3, 763.5)
# What each of A07's markers and arrows points at, by the frame its character is placed: (first, last, role). 'zoom' items
# keep their place on the screen relative to the zoom's focus (retail B -> our objective 1), 'mark k' items to our objective
# k on the whole map, 'route' arrows are carried from retail A -> B onto our objective 1 -> 2.
ROLES = ((200, 470, ('zoom', RETAIL_B, 0)), (471, 508, ('mark', RETAIL_A, 0)), (509, 528, ('route',)),
         (529, 719, ('mark', RETAIL_B, 1)))
# A placeholder map's two objectives (fractions of the picture): a slot without a map of ours still shows the structure.
PLACEHOLDER_TARGETS = ((0.30, 0.62), (0.72, 0.36))


def new_event(old, slot=None):
    """Retail's narration event of a briefing line -> ours (same length: it is a name inside the screen's script constants).
    Ours is no audio event at all, so nothing is spoken; its subtitle label (DIALOGEVENT:<name>) holds our text. In slot
    `slot`'s screen the template's lines become that slot's lines in the order they play (CNV_SHELL_I_<slot><n>00).
    The script's table of the other missions' lines, all three campaigns' (never played here), goes to CNV_SHELL_X<side>...,
    no label: no retail subtitle is left reachable from the screen."""
    m = EVENT.fullmatch(old)
    side, mission, line = m.group(1).upper().decode(), int(m.group(2)), int(m.group(3))
    if side == 'A' and not slot:
        return f'CNV_SHELL_I_{mission:02d}{line:02d}00'.encode()
    if side == 'A' and mission == TEMPLATE and line in TEMPLATE_LINES:
        return f'CNV_SHELL_I_{slot:02d}{TEMPLATE_LINES.index(line) + 1:02d}00'.encode()
    return f'CNV_SHELL_X{side}{mission:02d}{line:02d}'.ljust(len(old), '0').encode()


def narration_lines(m):
    """The objective briefing's five lines for mission info `m`, in LINES' order: the briefing's first sentence over the whole
    map, objective 1 as the map zooms onto it, the rest of the briefing, objective 2 as the route reaches it, a closing line."""
    parts = [s + '。' for s in m['briefing'].split('。') if s] if '。' in m['briefing'] else \
        [s.strip() + '.' for s in m['briefing'].split('. ') if s.strip()]
    parts = [p.replace('..', '.') for p in parts]
    first, rest = (parts[0], ''.join(parts[1:]) if T is TEXTS['zh'] else ' '.join(parts[1:])) if len(parts) > 1 else (m['briefing'], m['title'])
    one, two = m['objectives']
    return (first, T['goal'].format(n=1, text=one), rest, T['goal'].format(n=2, text=two), T['closing'])


def narration_strings(info):
    """{DIALOGEVENT:<our name>: text}: each slot's five lines (narration_lines) under the names its screen plays."""
    return {f'DIALOGEVENT:CNV_SHELL_I_{k:02d}{n:02d}00': text for k, m in info.items()
            for n, text in enumerate(narration_lines(m), 1)}


def _geometry_rect(prefix, number=3):
    """The (width, height) of a briefing's shape `number` (3: the map, in its own units = texture pixels)."""
    import struct
    import mapxml
    (h, E, chunks, bufs), _ = mapxml.read_stream(prefix, mapxml._archive_get('Apt.big'))
    for e, c in zip(E, chunks):
        if mapxml.sa.cstr(bufs[2], e[6]).decode().endswith(f'Objective_Briefing_{number}') and \
                mapxml.sa.cstr(bufs[2], e[6]).startswith(b'AptGeometryData'):
            _, at, length, _ = struct.unpack_from('<4I', c[0], 0)
            xs, ys = [], []
            for line in c[0][at:at + length].decode('latin1').split('\r\n'):
                if line.startswith('t '):
                    v = [float(x) for x in line[2:].split(':')]
                    xs += v[0::2]
                    ys += v[1::2]
            return max(xs), max(ys)
    raise KeyError(f'{prefix}: no shape {number}')


def views(size, targets):
    """Our map's placements: {'whole': (scale, tx, ty), 'zoom': ...} for a map `size` (w, h) in its own units with the
    objectives `targets` [(x, y)] in those units. The whole map covers the window (as retail's, cropped a little rather than
    showing an edge); the zoom is retail's (A07's 0.78 over its whole 0.456) and puts objective 1 where A07's zoom puts B,
    then is held inside the map (no edge in view)."""
    w, h = size
    whole = max(SCREEN[0] / w, SCREEN[1] / h)
    z = whole * 0.78 / 0.456

    def held(s, tx, ty):
        return s, min(0.0, max(SCREEN[0] - s * w, tx)), min(0.0, max(SCREEN[1] - s * h, ty))
    focus = 0.78 * RETAIL_B[0] - 330.4, 0.78 * RETAIL_B[1] - 348.6         # A07's zoom (frame 209 on) at its B
    return {'whole': held(whole, (SCREEN[0] - whole * w) / 2, (SCREEN[1] - whole * h) / 2),
            'zoom': held(z, focus[0] - z * targets[0][0], focus[1] - z * targets[0][1])}


RETAIL_VIEWS = {'whole': (0.449, 3.7, -1.8), 'zoom': (0.78, -330.4, -348.6)}       # A07's after its moves (frames 479, 209)


def retime(size, targets):
    """The template's timeline (A07's) over a map of `size` with `targets` (views): every placement of the map is the
    blend of our views that retail's is of its own (its scale between the whole map and the zoom); every marker and arrow
    is carried to our objective by its ROLES."""
    def edit(apt, const):
        import apt_movie
        m = apt_movie.movie(apt, const)
        ours = views(size, targets)
        mark = {k for n, k in m['imports'].items() if n != 'Map frame'}
        buf = bytearray(apt)
        role_at = {}

        def screen(view, p):
            s, tx, ty = view
            return s * p[0] + tx, s * p[1] + ty

        a0, b0 = screen(RETAIL_VIEWS['whole'], RETAIL_A), screen(RETAIL_VIEWS['whole'], RETAIL_B)
        a1, b1 = screen(ours['whole'], targets[0]), screen(ours['whole'], targets[1])
        r0, r1 = complex(*b0) - complex(*a0), complex(*b1) - complex(*a1)
        turn = r1 / r0                                  # the route: retail A -> B onto ours, turned and scaled
        for it in apt_movie.placements(m, apt):
            if not it.flags & apt_movie.HAS_MATRIX:
                continue
            a, b, c, d = it.matrix
            x, y = it.translate
            if it.char == 4 and it.depth == 2:          # the map (sprite 4, depth 2 in every objective briefing)
                lo, hi = RETAIL_VIEWS['whole'][0], RETAIL_VIEWS['zoom'][0]
                u = min(1.0, max(0.0, (a - lo) / (hi - lo)))
                v = [p + u * (q - p) for p, q in zip(ours['whole'], ours['zoom'])]
                apt_movie.place(buf, it, (v[0], 0.0, 0.0, v[0]), (v[1], v[2]))
                continue
            if it.char not in mark:
                continue
            if it.flags & apt_movie.HAS_CHARACTER:
                role_at[it.depth] = next(r for f0, f1, r in ROLES if f0 <= it.frame <= f1)
            role = role_at[it.depth]
            if role[0] == 'route':
                p = complex(*a1) + turn * (complex(x, y) - complex(*a0))
                col1, col2 = turn * complex(a, b), turn * complex(c, d)
                apt_movie.place(buf, it, (col1.real, col1.imag, col2.real, col2.imag), (p.real, p.imag))
            else:
                kind, retail, k = role
                view = ours['zoom'] if kind == 'zoom' else ours['whole']
                was = screen(RETAIL_VIEWS[kind if kind == 'zoom' else 'whole'], retail)
                now = screen(view, targets[k])
                apt_movie.move(buf, it, (x + now[0] - was[0], y + now[1] - was[1]))
        return bytes(buf)
    return edit


def objective_briefing(k, short, real, picture=None, targets=None):
    """Slot k's objective briefing: [(big path, bytes)] for its four files -- A07's timeline (TEMPLATE) over slot k's own map
    shape, our map picture in its texture, the narration renamed to slot k's lines. `targets`: our two objectives as
    fractions (u, v) of the picture (PLACEHOLDER_TARGETS for a slot with no map of ours); `picture`: the map from above."""
    prefix = APT + f'a{k:02d}_objective_briefing.'
    tex = f'apt_A{k:02d}_Objective_Briefing_1'
    orig = apt_textures.originals('Apt.big', prefix)[tex]
    x0, y0, x1, y1 = orig.getchannel('A').getbbox()
    targets = targets or PLACEHOLDER_TARGETS
    local = [(x0 + u * (x1 - x0), y0 + v * (y1 - y0)) for u, v in targets]
    return apt_textures.patch('Apt.big', prefix, {tex: objective_map(short, real, picture)(orig)},
                              (EVENT, lambda old: new_event(old, k)), retime(_geometry_rect(prefix), local),
                              donor=APT + f'a{TEMPLATE:02d}_objective_briefing.')


def apt_files(slots, picture=None, screens=True):
    """The APT streams with our pictures and the emptied co-op panel: [(big path, bytes)]. `slots`: {slot: (short name, built
    mission?, (lat, lon), targets)}; `picture`: the built mission's map from above (map_picture); `screens`: the screens
    shared by every slot too. Only the .bin carries pictures / shapes / timelines; the other three files of a stream are the
    retail ones byte for byte (checked by tests/test_shell.py), so they are not shipped."""
    files = []

    def add(stem, make):
        prefix = APT + stem + '.'
        files.extend((p, v) for p, v in make(prefix) if p.endswith('.bin'))

    for k, (short, built, where, targets) in slots.items():
        files.extend(objective_briefing(k, short, built, picture, targets))     # all four files: the donor's sizes
        add(f'a{k:02d}_global_briefing', lambda prefix, k=k, short=short, built=built, where=where: apt_textures.patch(
            'Apt.big', prefix, {f'apt_A{k:02d}_Global_Briefing_1': global_pictures(short, built, picture)(
                apt_textures.originals('Apt.big', prefix)[f'apt_A{k:02d}_Global_Briefing_1'])}, movie=retarget(where)))
    if not screens:
        return files
    add('fes_m_factionmenu', lambda prefix: apt_textures.patch(
        'Apt.big', prefix, {t: faction_cards(apt_textures.originals('Apt.big', prefix)[t], boxes) for t, boxes in CARD_BOXES.items()}))
    for stem, boxes in ICON_BOXES.items():
        add(stem, lambda prefix, boxes=boxes: apt_textures.patch('Apt.big', prefix, {
            t: faction_icons(img, boxes) for t, img in apt_textures.originals('Apt.big', prefix).items()}))
    add('fes_m_objectivesbriefing', lambda prefix: apt_textures.patch('Apt.big', prefix, {
        t: destar(apt_textures.originals('Apt.big', prefix)[t], boxes) for t, boxes in STAR_BARS.items()}))
    add('tacticalendgamedialog', lambda prefix: apt_textures.patch('Apt.big', prefix, {
        t: end_cards(apt_textures.originals('Apt.big', prefix)[t], cards) for t, cards in END_CARDS.items()}))
    add(PANEL, lambda prefix: apt_textures.hollow('Apt.big', prefix, (PORTRAIT_CALL, lambda old: old[:-1] + b'x')))
    return files


# ---- what the player still sees of retail (K9, ADR 0015) -------------------------------------------------------------------
# Every screen of the campaign flow, and every component library it imports (recursively: I12 hid in an imported component),
# is read as the shell ships it; a picture whose pixels are retail's, a label whose text is the retail table's and that the
# shell neither rewrites nor adds, and a template's video field that is not one of our clips, are retail content the player
# sees. Each one is either replaced or listed in KEEP with its reason; anything else is an error (tests/test_shell.py).

SCREENS = ('fes_m_factionmenu', 'fes_m_chapterselect', 'fes_m_missionbriefing', 'fes_m_objectivesbriefing',
           'loadscreencampaign', PANEL, 'fes_m_postgameroundup', 'tacticalendgamedialog',
           *(f'a{k:02d}_{kind}_briefing' for k in range(1, 10) for kind in ('global', 'objective')))
LABEL = re.compile(rb'(?<=\x00)\$([A-Za-z][\x21-\x7e]{2,})(?=\x00)')     # '$KEY' or '$KEY&Outline' (no ':' -> APT:KEY)
VIDEO_FIELDS = ('OverviewTalkingHead', 'IntroMovie:FileName')
_FRAME = 'the interface frame: panels, borders, bars (no picture of retail\'s story)'
_ALLIED = 'the Allied screens\' backdrop (world map silhouette, the statue): our campaign takes the Allied slot'
_WORD = 'a word of the interface itself, true in our campaign as it is'
_MODE = 'single player / co-op choice of every campaign mission'
KEEP = {
    ('screen', 'shellcontent'): 'imported by the load screen but in no archive of the game: nothing of it is ever drawn',
    ('screen', 'shellbuttons'): 'imported by the load screen but in no archive of the game: nothing of it is ever drawn',
    ('screen', 'fe_m_assetsgamesetup'): 'the chapter list borrows only its MapPreviewComponent (the thumbnail frame; the '
                                        'thumbnails are ours); the rest is the multiplayer setup screen',
    ('screen', 'chatcomponent'): 'the co-op chat box (only with a human co-commander)',
    ('screen', 'helpbox'): 'the tooltip of the co-op panel, which is hollowed (nothing of the panel is drawn)',
    **{('texture', t): _FRAME for t in (
        'apt_fes_m_factionMenu_2', 'apt_fes_m_objectivesBriefing_2', 'apt_fes_m_postgameRoundup_2',
        'apt_fe_m_generalScreenComponents_1', 'apt_std_MouseButton_1', 'apt_std_mouseRadioButton_1',
        'apt_std_mouseScrollbar_1', 'apt_std_mouseDropDownMenu_1', 'apt_LoadScreenCampaign_1',
        'apt_fe_missionBriefingAssets_2', 'apt_fe_missionBriefingAssets_3', 'apt_fe_missionBriefingAssets_4',
        'apt_fe_missionBriefingAssets_5', *(f'apt_A{k:02d}_Global_Briefing_2' for k in range(1, 10)))},
    **{('texture', t): _ALLIED for t in (
        'apt_fes_m_chapterSelect_1', 'apt_fes_m_missionBriefing_1', 'apt_fes_m_missionBriefing_2',
        'apt_fes_m_postgameRoundup_1')},
    ('texture', 'apt_TacticalEndGameDialog_1'): 'the Soviet and Japanese defeat posters of the end card: the dialog draws '
                                                'the player\'s faction\'s, ours is the Allied slot (END_CARDS, I21)',
    ('texture', 'apt_fe_missionBriefingAssets_1'): 'the world map of the overview: geography; every slot\'s marker points at '
                                                   'its own place on it (I10, retarget)',
    ('texture', 'apt_fe_objectiveBriefingsAssets_1'): 'the objective briefing\'s window frame, markers and arrows, which '
                                                      'point at our objectives (retime)',
    ('texture', 'apt_A01_Objective_Briefing_2'): 'A01\'s own arrow picture, never drawn: A07\'s image table (the donor\'s '
                                                 'AptDatData, "2->1") points only at texture 1',
    **{('label', 'APT:' + w): _WORD for w in (
        'BACK', 'CONTINUE', 'PLAY', 'NEXT', 'LOAD', 'MAINMENU', 'MAIN_MENU_BUTTON', 'ABORT_BUTTON', 'REPLAY_BUTTON',
        'REPLAY_VIDEO_BUTTON', 'REPLAY_BRIEFING', 'READY', 'DIFFICULTY', 'EASYDIFFICULTY', 'MEDIUMDIFFICULTY',
        'HARDDIFFICULTY', 'FACTION_SELECT_SCREEN_TITLE', 'HEADERCHAPTERSELECT', 'MISSION_CHOOSER', 'MISSION_NAME',
        'MISSION_BRIEFING', 'MISSION_OBJECTIVES', 'MISSION_OBJECTIVE_PANEL_TITLE', 'GAME_COMMANDERS', 'MAIN_COMMANDER',
        'COMMANDERS', 'POSTGAME_ROUNDUP', 'POSTGAME_STATS_TAB', 'RESOURCES', 'STRUCTURES', 'UNITS', 'LOADINGDOTDOTDOT',
        'CHAT', 'CHATPANELTITLEBAR', 'ALLIESSHORTNAME', 'SOVIETSSHORTNAME', 'JAPANSHORTNAME')},
    **{('label', 'APT:' + w): _MODE for w in (
        'AI_BUTTON', 'RECRUIT_BUTTON', 'PLEASE_SELECT_YOUR_CO_COMMANDER_TYPE', 'CAMPAIGNMODESELECTIONHELPTEXT',
        'WAITINGFORCOCOMMANDER')},
}


def _stream(prefix, get):
    (h, E, chunks, bufs), _ = apt_textures.mapxml.read_stream(prefix, get)
    return {apt_textures.mapxml.sa.cstr(bufs[2], e[6]).decode(): c[0] for e, c in zip(E, chunks)}


def retail_labels():
    """{LABEL: text} of the string table the mod's csf starts from (make_campnew3.strings)."""
    import make_campnew3 as c3
    from ra3voice import big, csf
    name = 'data' + B + 'gamestrings.csf'
    data = big.read_files(os.path.join(c3.GAME, 'Data', 'CNVoice_text.big'), [name])[name]
    return {e[0].upper(): e[1] for e in csf.parse_full(data)[1]}


def still_retail(sp, table=None):
    """[(kind, where, what)] of the retail content the shell `sp` (make()) leaves on the campaign's screens and in its
    templates and does not KEEP: ('texture', screen, texture id), ('label', screen, LABEL), ('video', template, field),
    ('screen', name, 'not in Apt.big'), and ('keep', kind, what) for a KEEP entry that matches nothing any more."""
    import apt_movie
    table = retail_labels() if table is None else table
    retail = apt_textures.mapxml._archive_get('Apt.big')
    ours = dict(sp.files)
    mine = {k.upper() for k in (*sp.strings, *sp.overrides)}
    prefixes = tuple(p.upper() for p in sp.prefix_overrides)
    left, seen, todo, used = [], set(), list(SCREENS), set()

    def kept(item):
        used.add(item)
        return item in KEEP

    while todo:
        stem = todo.pop(0).lower()
        if stem in seen or kept(('screen', stem)):
            continue
        seen.add(stem)
        prefix = APT + stem + '.'
        try:
            got = _stream(prefix, lambda n: ours[n] if n in ours else retail(n))
        except KeyError:
            left.append(('screen', stem, 'not in Apt.big'))
            continue
        orig = _stream(prefix, retail) if any(n.startswith(prefix) for n in ours) else got
        for name, data in got.items():
            if name.startswith('Texture:') and data == orig.get(name) and not kept(('texture', name[8:])):
                left.append(('texture', stem, name[8:]))
        kinds = {n.split(':')[0]: d for n, d in got.items()}
        a, c = kinds['AptAptData'], kinds['AptConstData']
        for m in sorted({m.group(1).decode('latin1').split('&')[0] for m in LABEL.finditer(a + c)}):
            key = (m if ':' in m else 'APT:' + m).upper()
            if key in table and key not in mine and not key.startswith(prefixes) and not kept(('label', key)):
                left.append(('label', stem, key))
        (ao, al), (co, cl) = apt_movie.apt_of(a), apt_movie.apt_of(c)
        todo += [re.split(r'[\\/]', lib)[-1] for lib in apt_movie.movie(a[ao:ao + al], c[co:co + cl])['libraries'].values()]
    for k in range(1, 10):
        attrs = sp.attrs if k == sp.slot else sp.others.get(k, {})
        left += [('video', f'Allies_{k}', f) for f in VIDEO_FIELDS if attrs.get(f) not in sp.clips]
    left += [('keep', kind, what) for kind, what in KEEP if (kind, what) not in used]      # kept, but no longer there
    return left


# ---- the chapter list's thumbnails ----------------------------------------------------------------------------------------

def retail_map_stems():
    """{slot: 'camp_a01_...' (the map's folder, which is also the map's file stem)}: retail's Allied missions' maps."""
    import labpaths
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'CampaignTemplates.xml'), encoding='ascii') as f:
        xml = f.read()
    return {k: re.search(rf'<MissionTemplate\s+id="Allies_{k}".*?MapName="[^"]*?([^\\\\]+)\.map"', xml, re.S).group(1).lower()
            for k in range(1, 10)}


def thumbnail(short, real, size=128, picture=None):
    """A picture of a map as retail's files are: 128 x 128 uncompressed 32-bit TGA (<map>.tga), or 512 x 512 24-bit (<map>_art.tga)."""
    import io
    from PIL import Image
    img = map_picture(size, short, True, False, picture).convert('RGBA') if real else name_card((size, size), [(short, size // 6, size * 0.4), (T['pic'], size // 9, size * 0.7)])
    buf = io.BytesIO()
    img.convert('RGBA' if size == 128 else 'RGB').save(buf, 'TGA')
    return buf.getvalue()


def thumbnails(slots, picture=None, own=None):
    """[(big path, bytes)]: a mission's map picture is the file <its map folder>\\\\<stem>.tga; a built mission's is in its
    new folder (`own`: {slot: stem}, OWN_STEM by default; the build puts it there: make_campnew2.map_files), the others
    replace the retail folders' files (this mod's big only: retail's are not touched). `slots`: the slots to make
    (make()'s {slot: (short, built?, ..)})."""
    out = []
    stems = retail_map_stems()
    for k in slots:
        short, built = slots[k][:2]
        stem = (own or {}).get(k, OWN_STEM) if built else stems[k]
        out.append((f'data{B}maps{B}official{B}{stem}{B}{stem}.tga', thumbnail(short, built, picture=picture)))
        out.append((f'data{B}maps{B}official{B}{stem}{B}{stem}_art.tga', thumbnail(short, built, 512, picture)))
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


def site_targets(map_name, names=None, goals=(), slot=None):
    """The built mission's two objectives on its map picture as fractions (u, v) of the picture, which shows the map's
    first border (the whole map), north up: the map's published sites `names` (shell_missions.json `targets`), or
    without them the first two of `goals` (ModSpec.goals: where the mission's own objectives send the player; one is
    used twice). Neither: the build stops and says so (I16: a missing field must not fall back to anything silently)."""
    import importlib
    mod = importlib.import_module(f'maps.{map_name}')
    # a map with no BORDERS is the whole container: Heidelberg's, 5000 x 5000 world units playable (maps/island.py)
    x0, y0, x1, y1 = next(iter((getattr(mod, 'BORDERS', None) or {'whole': (0.0, 0.0, 5000.0, 5000.0)}).values()))
    if names:
        gone = [n for n in names if n not in mod.SITES]
        if gone:
            raise SystemExit(f'shell: slot {slot}: {T["file"]} targets {gone} are no sites of map {map_name} '
                             f'(its sites: {sorted(mod.SITES)})')
        points = [mod.SITES[n].at() for n in names]
    else:
        points = list(goals)[:2]
        if not points:
            raise SystemExit(f'shell: slot {slot}: no "targets" in {T["file"]} and the mission publishes no objective '
                             f'with a place (Goal.show) on map {map_name}: name two of its sites there')
    points = (points * 2)[:2]
    return tuple(((x - x0) / (x1 - x0), 1 - (y - y0) / (y1 - y0)) for x, y in points)


def short_of(m):
    """A slot's short name: its title's first part (before ' · '), so the briefing's heading and the map card say what
    the chapter list says (I17: 'Ice Soldiers' under 'Sapporo Snow Festival · ...')."""
    return m['title'].split(' · ')[0].strip()




def picture_of(m):
    """The map MapFile `m` from above, the ground only (maprender, plain), as MAP_PICTURE (kept there for a look)."""
    import maprender
    return maprender.render(m, MAP_PICTURE, px=2, plain=True)


def make(mission_title, mission_name='CampA4', lang='zh', map_name='sapporo', later=False, goals=()):
    """Everything the shell adds to the build of the one mission `mission_name` (in the slot slot_of names) in the
    edition `lang` (langs.py: zh, intl; the words of the shell are TEXTS) on the map module `map_name`; `goals`: where
    its objectives are (ModSpec.goals), for a slot whose shell_missions entry names no targets. make_slots says more."""
    return make_slots({slot_of(mission_name): (map_name, goals, OWN_STEM)}, lang, later)


def make_slots(built, lang='zh', later=False):
    """Everything the shell adds to a build carrying the missions `built`, {slot: (map module name, goals (ModSpec.goals),
    map stem)}, in the edition `lang`. Every slot's names are shell_missions[.en].json's (the short name short_of the
    title). later: each built slot's screens and thumbnails are drawn from the map the build writes (sp.drawn[slot],
    f(MapFile) -> files; one built slot: also sp.map_files), not from MAP_PICTURE as the last build left it."""
    use_lang(lang)
    info = missions()
    for m in info.values():
        m['short'] = short_of(m)
    first = min(built)
    sp = Shell(slot=first)
    sp.template = {'no_portrait': True}
    for k, m in info.items():
        attrs = {'OverviewTalkingHead': HEAD_ID, 'IntroMovie:FileName': intro_id(k),
                 'IntroMovie:ScreenName': f'MissionName:{label(k)}', 'IntroMovie:Description': f'MissionDesc:{label(k)}',
                 'AICommander:Description': f'CommanderDescription:{label(k)}'}
        if k == first:
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
    slots = {k: (m['short'], k in built, tuple(m['where']),
                 site_targets(built[k][0], m.get('targets'), built[k][1], k) if k in built else None)
             for k, m in info.items()}
    own = {k: b[2] for k, b in built.items()}
    if later:
        mine = {k: slots.pop(k) for k in built}

        def drawn(m, k):                                # a built slot's screens, from the map this build writes
            use_lang(lang)
            picture = picture_of(m)
            return apt_files({k: mine[k]}, picture, screens=False) + thumbnails({k: mine[k]}, picture, own)
        sp.drawn = {k: (lambda m, k=k: drawn(m, k)) for k in built}
        sp.map_files = (sp.drawn[first],) if len(built) == 1 else ()
    sp.files = apt_files(slots) + thumbnails(slots, own=own)
    sp.overrides = {'APT:ALLIES_FACTION_DESCRIPTION': T['card'], **{f'MONITOR:{k}': ' ' for k in MONITOR},
                    **{f'APT:{k}': T['notes_title'] for k in ('COCOMMANDER_NAME_TITLE', 'COCOMMANDER', 'YOUR_CO_COMMANDER',
                                                              'SELECT_YOUR_AI_CO_COMMANDER')}}   # the overview tab's head ("副指挥官")
    # the commander overview is our intel officer's (docs/design/flow/cast.md): its tab, the team column's second row and the
    # co-op commanders' names (its name bar, the team column) are hers
    sp.overrides.update({'APT:MISSION_COMMANDERS': T['officer_title'], 'APT:CO_COMMANDER': T['officer_title']})
    sp.prefix_overrides = {'PERSONALITY:': T['officer']}
    for key, side, desc in (('SOVIETS', 'soviet', 'APT:SOVIET_FACTION_DESCRIPTION'), ('JAPAN', 'empire', 'APT:JAPANESE_FACTION_DESCRIPTION')):
        sp.overrides[desc] = T['faction'][side] + T['other_card']        # the other two campaigns: placeholders (names, cards, texts)
        for k in range(1, 10):
            sp.overrides[f'MISSIONNAME:{key}_{k}'] = T['other_name'].format(side=T['faction'][side], k=k)
            sp.overrides[f'MISSIONNAME:{key}_{k}_SHORT'] = T['other_short'].format(side=T['faction'][side], k=k)
    return sp


def contribute(spec, lang='zh'):
    """The campaign shell as a layer on a mod's ModSpec (ADR 0016; package.spec_of adds it for build.py --shell): the
    built mission in its slot of the Allied campaign and the other eight slots ours (make_campnew2.SHELL), the shell's
    labels, the retail labels it rewrites, its APT screens and its movies (the mission's own clips kept, in the same
    video pack). It only adds to the spec (package.with_more) and touches no other module; the shell has its own
    launcher (launcher.py), so no Play_<name>.bat."""
    from dataclasses import replace
    from package import with_more
    from experimental.video import pack as video_pack
    sp = make(spec.title or spec.mission, spec.mission, lang, spec.map_name or 'sapporo', later=True, goals=spec.goals)
    video = dict(spec.packs).get('video')
    video = video_pack.Later({**(video.clips if video else {}), **sp.clips})     # written in build_mod's lock
    packs = tuple((k, video if k == 'video' else p) for k, p in spec.packs)
    if 'video' not in dict(spec.packs):
        packs += (('video', video),)
    spec = with_more(spec, strings=sp.strings, overrides=sp.overrides, prefix_overrides=sp.prefix_overrides,
                     big_files=sp.files, map_files=sp.map_files)
    import langs
    return replace(spec, packs=packs, slot={'slot': sp.slot, 'attrs': sp.attrs, 'others': sp.others, **sp.template},
                   launcher=False, strings_base=langs.edition(lang)['strings_base'])


def campaign(levels, name=None, lang='zh', fallback=()):
    """The campaign shell with a level of ours in each of `levels`' slots (I16: the release shell carries every Allied
    level, not one): {slot: the level's ModSpec (package.spec_of, no shell)} -> the mod's ModSpec, its levels in
    ModSpec.levels (package.build_mod builds each map into its own folder, package.level_stem) and every slot's
    template on its map (make_campnew2.SHELL 'maps'). The levels' labels and packs go into the one mod: a label two
    levels give different texts, or a second music / voice pack, stops the build (one mod has one of each); their
    movies join the shell's in one video pack. `fallback`: the slots whose level has no edition `lang` (another
    edition stands in, build.campaign_levels says so): a label they share with a level of the edition keeps that
    level's text (AUTOSAVE:CNVCAMPAIGN in English, not Chinese)."""
    from dataclasses import replace
    from package import ModSpec, level_stem, with_more
    from experimental.video import pack as video_pack
    import langs
    name = name or NAME + langs.edition(lang)['suffix']
    built = {k: (lv.map_name, lv.goals, level_stem(k)) for k, lv in levels.items()}
    sp = make_slots(built, lang, later=True)
    strings, clips, packs = {}, {}, {}
    for k, lv in sorted(levels.items(), key=lambda kv: (kv[0] in fallback, kv[0])):    # the edition's own levels first
        clash = sorted(x for x in lv.strings if x in strings and strings[x] != lv.strings[x])
        if clash and k not in fallback:
            raise SystemExit(f'shell: slot {k} ({lv.mission}) gives labels another level has a different text: {clash[:8]}')
        strings.update({x: v for x, v in lv.strings.items() if x not in strings})
        for kind, p in lv.packs:
            if kind == 'video':
                clips.update(p.clips)
            elif kind in packs:
                raise SystemExit(f'shell: slot {packs[kind][0]} and slot {k} both bring a {kind} pack: one mod has one')
            else:
                packs[kind] = (k, p)
    video = video_pack.Later({**clips, **sp.clips})                     # written in build_mod's lock
    maps = {k: f'data{B}maps{B}official{B}{s}{B}{s}.map' for k, (_, _, s) in built.items()}
    spec = ModSpec(name=name, mission='+'.join(lv.mission for _, lv in sorted(levels.items())),
                   packs=tuple((kind, p) for kind, (_, p) in packs.items()) + (('video', video),),
                   levels=tuple((k, replace(lv, map_files=lv.map_files + (sp.drawn[k],))) for k, lv in sorted(levels.items())),
                   slot={'slot': sp.slot, 'attrs': sp.attrs, 'others': sp.others, 'maps': maps, **sp.template},
                   launcher=False, strings_base=langs.edition(lang)['strings_base'])
    return with_more(spec, strings={**strings, **sp.strings}, overrides=sp.overrides,
                     prefix_overrides=sp.prefix_overrides, big_files=sp.files)
