"""Concept sheets from GPT's image model, driven through the Codex CLI on the user's ChatGPT subscription (the
"ChatGPT" desktop app here is OpenAI Codex; its codex.exe has image generation on and takes reference images).

  python -I experimental/units/concept_gpt.py <unit> [<note for this round>]   -> work/units/<unit>/gpt/v<N>.png + v<N>_views/
  python -I experimental/units/concept_gpt.py --views <sheet.png> <out dir>     cut a sheet into views only

The sheet standard (user 2026-10-26: good reference images are what the image-to-3D step lacked; three views):
- one square 2 x 2 sheet in ONE generation (front / side / back must come from the same generation, or they drift
  apart -- game-asset-aesthetic-test's spine-multiview lesson), plain #D0D0D0, no text; three orthographic panels at
  one scale plus a 3/4 view from the RTS camera's height.
- the references are retail units of the same faction and class rendered from the game (retail_sheet.py) in that
  very layout: they fix the style, the size class and the layout at once.
- team colour is painted saturated blue, only where the retail units have it (raised upper panels), so the mask can
  be taken from the hue later.
Views: rows split at the widest empty band, then columns; the three orthographic views share one scale (each
fitted to its own box they came out at different sizes); right = left mirrored. One generation took ~70 s.
"""
import glob
import json
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageChops, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
import labpaths                                 # noqa: E402

UNITS = os.path.join(labpaths.WORK, 'units')
REF = os.path.join(labpaths.WORK, 'reference', 'sheets')
CODEX_IMAGES = os.path.join(os.path.expanduser('~'), '.codex', 'generated_images')

STYLE = {
    'allied': '''- stylised-realistic RTS game asset, "toy-like" chunky proportions, hand-painted game texture look, like Red
  Alert 3 retail units; not photoreal, not anime, not low-poly.
- armour: cool silver-grey gunmetal with dark panel seams, bevelled edges with light edge wear, a few black vents
  and grilles.
- team colour: saturated BLUE paint (same blue as the references) ONLY on raised upper armour panels and the turret
  top, so it is visible from above; about 20 to 30 percent of the top surface.
- lights: small cyan / white glowing lights and lenses, as on the Guardian.
- no weathering mud, no camouflage, no text, no numbers, no emblems.''',
    # map props of ice (the 冰幕工兵's festival, A4): retail's Iceland glaciers are the look
    'ice': '''- stylised-realistic RTS game prop like the Red Alert 3 retail glacier and snowman props in the references:
  clean FACETED ice -- large flat planes with crisp edges, not smooth glass, not noisy.
- colour: pale white-cyan ice, brightest on the upper faces, slightly deeper cyan-grey in the recesses and toward
  the base; a few faint inner cracks; opaque-looking (no see-through refraction, no rainbow caustics).
- no team colour, no lights, no snow-covered ground, no people, no text.''',
}
KIND = {'ice': 'prop'}                          # what the sheet shows: a unit (default) or a map prop

LAYOUT = '''- one square image, a 2 x 2 grid of four equal panels, plain flat light-grey background (#D0D0D0) everywhere,
  no panel borders, no labels, no text.
- top-left: FRONT view, orthographic (no perspective), the unit facing the viewer.
- top-right: SIDE view, orthographic, the unit in profile, front pointing the same way as in the reference sheet's
  side view.
- bottom-left: BACK view, orthographic.
- bottom-right: three-quarter view from the front-left and above (about 35 degrees down), like the reference's
  bottom-right panel.
- the SAME unit with the SAME design in all four panels, same scale in the three orthographic panels, whole unit
  visible with margin, centred, even soft studio lighting, no cast shadow on the background.'''

# A hero shot finds a big unit's design before its sheet (user 2026-10-26: the Liberty sheets lacked grandeur --
# orthographic panels, a high camera and vehicle-sized references make anything read small). The sheet is then
# drawn with the chosen hero shot as a reference (--from).
HERO = '''- one wide cinematic concept painting (16:9), NOT a sheet, no panels, no text, no labels, no logos.
- low camera near the ground, looking up at the ship as it passes overhead above a snowy battlefield; the ship
  fills most of the frame and runs out past one edge, so it feels too big for the picture.
- scale: a few tiny Allied tanks and a small base building on the ground below, and soldiers, so the ship reads
  as hundreds of metres long; atmospheric haze between the camera and the far end of the hull.
- its anti-gravity emitters cast cyan light onto the ground and the haze below; a squadron of its small drone
  fighters dropping out of the flank bays.
- dramatic but clear light: overcast sky with a break of sun; the design must still read clearly.'''
HERO_STYLE = '''- Red Alert 3 world and design language (Allied: cool silver-grey gunmetal armour, saturated blue team-colour
  panels, cyan-white lights), painted as a high-end cinematic concept art frame, more realistic than the game
  asset but the same design; not anime, not photoreal CGI render.'''
GRAND = {'liberty': '''GRANDEUR (the earlier designs read like a squat toy; fix that):
- long and massive: length about 2 to 2.5 times its width, a heavy overhanging prow, a deep armoured keel below
  the hull, many stacked tiers rising toward the citadel; strong long horizontal lines plus a few tall verticals
  (the citadel, antenna masts).
- extreme detail density against huge clean armour masses: hundreds of tiny lit windows in bands, small hatches,
  gun ports, ribbing, deck lights; nothing on it looks bigger than a building's window.
- the anti-gravity emitters are huge glowing rings and discs along the keel, the size of buildings.''',
         'libertyisle': '''GRANDEUR: it must feel like a national monument turned into a flying fortress -- a heavy armoured
mechanical mass below, dense fortress detail (hundreds of tiny lit windows, hatches, deck lights) against huge masses above,
the statue towering over everything; nothing on it looks bigger than a building's window except the statue.'''}

# unit: faction, retail reference sheets (REF/<name>_grid.png), what it is
BRIEFS = {
    'chronolag': ('allied', ['guardian', 'athena'], '''UNIT: "Chrono-Lag Artillery" (Allied faction, tier 2 support artillery). It does no damage: it fires a
slow glowing chrono shell that pushes a target briefly out of time. It must deploy before firing (folding
stabiliser legs at the four corners, currently stowed). Read it as Allied chronosphere technology made into a
field gun.
- Body: a medium tracked vehicle, same size class as the Guardian tank (length about 1.6x its width), two armoured
  track pods holding a narrower raised centre hull, layered sloped armour plates.
- Weapon: a long, slightly oversized chrono cannon on a low turret: a thick barrel wrapped by three spaced ring
  coils (chrono emitter rings), a muzzle with a glowing cyan-white lens, heat-sink fins near the breech. Barrel
  points straight forward in every panel.
- Rear: a squat cylindrical chrono reactor / capacitor drum on the back deck with a cyan glowing window strip.
- Silhouette must read clearly from a high top-down RTS camera: big simple shapes first (track pods, hull, turret,
  barrel with rings, rear drum), small details second.'''),
    # v1 (a flying aircraft-carrier deck with corner fans) was turned down 2026-10-26: not a carrier, a grand
    # sci-fi sky battleship (the user's touchstones: Mental Omega's Paradox Engine, Ultraman Gaia's anti-gravity
    # warships launching modular fighters, retail's Giga Fortress as the idea -- none of them copied)
    'liberty': ('allied', ['guardian', 'athena'], '''UNIT: "Liberty" (Allied signature super-unit, docs/story/units.md 5.2.1): a colossal ANTI-GRAVITY SKY
BATTLESHIP -- a flying fortress, the Allies' answer to a floating island. NOT an aircraft carrier, NOT a sea ship
with fans, NOT a troop transport. It should feel as grand as a cinematic CG capital ship, yet stay a chunky,
readable Red Alert 3 game asset. Original design: do not copy any existing game or film ship.
- Hull: one massive armoured hull, broad and heavy, layered in stepped tiers like a fortress (thick lower keel,
  middle gun decks, upper citadel); big clean armour masses with fine detail on top. Wide enough to hide what is
  under it: from above, its outline is a broad shape (about 0.4 to 0.5 as wide as it is long), not a thin needle.
- Command citadel: a tall stepped bridge tower rising from the middle-rear, the highest point, with a band of
  lit bridge windows and a radar / chrono antenna crown.
- Anti-gravity: no fans, no propellers, no rocket jets. It floats on glowing anti-gravity emitters: several big
  round cyan-white emitter discs or rings set into the underside and the flanks, with a faint cyan glow; plus one
  larger chronosphere ring in the centre of the belly. The glow must be visible in the side, back and
  three-quarter views.
- Modular fighters: launch bays along both flanks -- rows of open hangar slots with small arrow-shaped drone
  fighters docked in them, ready to drop out (they read as plug-in modules of the ship).
- Deck factory: a large armoured drop-bay door in the belly or the rear, where ground vehicles are lowered.
- Turrets: three EMPTY round armoured turret sockets (ring mounts, no guns in them) on the upper decks, two
  forward and one aft -- the turrets are separate models.
- Scale cues so it reads as huge: rows of tiny lit windows, small hatches and deck lights, hangar doors with tiny
  fighters in them -- tiny details against very large masses.
- Proportions: a super-unit about 10 times a Guardian tank in length; hull with keel about 1/2 of its width
  high, the citadel the tallest thing. Silhouette from the high RTS camera: the broad armoured hull, the citadel, the flank
  fighter bays, three ring sockets; team-colour blue on the big upper armour plates.'''),
    # the user 2026-10-26: what felt oppressive in RA3 were its story set pieces -- Mount Rushmore's laser heads, the
    # Emperor's floating island fortress, Uprising's Giga Fortress in its sky form: a landmark or a piece of land
    # turned into a weapon, far bigger than a vehicle. Liberty Island lifted into the sky is the Allies' own.
    'libertyisle': ('allied', ['guardian', 'athena'], '''UNIT: "Liberty" (Allied signature super-unit, docs/story/units.md 5.2.1), in Red Alert 3's
tongue-in-cheek alternate history: a hawkish US commander's flagship that is LIBERTY ISLAND ITSELF torn out of New
York harbour and lifted into the sky by Allied anti-gravity -- a flying monument-fortress, the Allies' answer to
the Empire's floating island fortress and to Mount Rushmore's laser heads. Grand, oppressive, a little absurd.
Original design (no copy of any game or film ship); not a vehicle, a piece of land and monument turned into a
weapon.
DESIGN RULES (from the big air fortresses of RTS games, 2026-10-26: the boxy v1/v2 base read as a pile of equal
blocks -- Soviet-looking, no focus, no threat):
- ONE focal point and a radial hierarchy: everything is smaller than and leads the eye to the statue and the
  chrono core under her; no field of equal-sized boxes.
- The threat points DOWN at the ground (like a mothership's belly beam): the underside ends in one huge chrono
  aperture, an armoured iris ringed with cyan light, aimed at whatever is beneath.
- Technology shown by FLOATING, rotating parts (the Allied chronosphere's gyroscope): rings that hover around
  the core without visible supports.
- Allied design language, not Soviet: sleek sloped and rounded armour, smooth curved bastions, glass domes and
  strips, white-silver and gunmetal with blue team colour; clean large surfaces, detail concentrated in bands.
- Weak points readable as separate modules: three turret bastions, the drop bay, the conduits feeding the torch.

THE DESIGN:
- Platform: the island's STAR FORT redrawn as a sleek Allied platform -- eleven smooth, rounded, sloped
  bastion points around a raised round centre. Three of the points carry EMPTY round armoured turret sockets
  (ring mounts, no guns); one carries a large drop-bay door that lowers ground vehicles; the others carry low
  launch rails with small arrow-shaped drone fighters. Under it NO rock, NO soil (the user 2026-10-26: once it
  has flown nothing of the ground is left).
- Core: at the centre a tall tapered chronosphere core column as her pedestal, sleek armour with vertical glowing
  cyan slots, thick power conduits climbing it; around the core TWO OR THREE huge gyroscope rings hover at
  different tilts (thin, bright-edged, glowing inner track), not touching anything. From above they frame the
  statue like a target reticle.
- On the core: the Statue of Liberty (kept recognisable), her torch a blazing cyan chrono beacon, conduits from
  the core up her back to the torch.
- Underside: a smooth stepped inverted cone of armour plates under the platform, gravity-repulsor discs (flush,
  concentric cyan rings) under the bastion points, and at the cone's tip the big downward chrono aperture.
- Proportions: a super-unit about 10 times a Guardian tank across, round from above, the statue the tallest
  thing; the cone below about half as deep as the platform is wide. From the high RTS camera: the
  star outline, the statue, three ring sockets, blue team-colour on the fortress roofs.'''),
    'icesculpture': ('ice', ['glacier06', 'snowman'], '''PROP: "Festival Ice Sculpture" for a snow festival plaza (the Sapporo snow festival). Enemy soldiers hide
inside it; it shatters when the convoy comes close. Read it as a carved festival showpiece, not a natural glacier.
- Subject: an Eastern (Japanese) dragon coiled around itself, head raised and turned forward, mouth open, long
  whiskers and a spiky back ridge, two front claws gripping the plinth.
- Plinth: a thick, roughly square faceted ice block as the base, about one third of the total height, its top
  edge slightly chipped, so the whole sculpture stands square on the ground.
- Proportions: footprint square, total height about 1.3 times the footprint width (a bit taller than a tank);
  big simple masses first (plinth, coiled body, raised head), carved detail second.
- The FRONT view looks at the dragon's face.'''),
}


def prompt(unit, note='', hero=False, source=False):
    faction, refs, brief = BRIEFS[unit]
    names = ', '.join(refs)
    kind = KIND.get(faction, 'unit')
    what = f'{faction} {kind}' if kind == 'unit' else f'{faction} {kind} (a map object, not a vehicle)'
    head = 'Generate ONE image with your image generation tool. Do not write code, do not run commands, do not edit files. Just generate the image and reply with one short sentence.'
    if hero:
        return f'''{head}

The attached images are reference sheets rendered from the retail game Command & Conquer: Red Alert 3 ({faction} {kind}s: {names}). They show the faction's design language and how small its ordinary units are. Design a NEW {what} in that design language and show it in a cinematic hero shot.

{brief}
{GRAND.get(unit, '')}
{note}
STYLE:
{HERO_STYLE}

SHOT (strict):
{HERO}
'''
    if source:
        # the user 2026-10-26: for modelling keep only the main elements, the rest confuses Tripo
        note = ('The LAST attached image(s) are the chosen design (cinematic hero shots): draw that design -- same '
                'silhouette and main parts -- as the game asset on the sheet. This sheet feeds an image-to-3D '
                'model generator, so SIMPLIFY: keep only the main forms as big clean shapes; drop small clutter '
                '(little buildings, pipes, masts, tiny windows beyond a few bands, flying fighters, snow, smoke, '
                'ground, sky).\n' + note)
    return f'''{head}

The attached images are reference sheets rendered from the retail game Command & Conquer: Red Alert 3 ({faction} {kind}s: {names}). They define the ART STYLE, the SCALE and the SHEET LAYOUT. Design a NEW {what} in exactly that style and lay it out exactly like the reference sheet.

{brief}
{note}
ART STYLE (match the references, do not invent a new style):
{STYLE[faction]}

SHEET LAYOUT (strict):
{LAYOUT}
'''


def codex():
    if os.environ.get('CNV_CODEX'):
        return os.environ['CNV_CODEX']
    # WindowsApps cannot be listed (a glob finds nothing), the package can be asked where it lives
    loc = subprocess.run(['pwsh', '-NoProfile', '-Command', '(Get-AppxPackage OpenAI.Codex).InstallLocation'],
                         capture_output=True, text=True).stdout.strip()
    exe = os.path.join(loc, 'app', 'resources', 'codex.exe')
    if not loc or not os.path.exists(exe):
        raise SystemExit('codex.exe not found (set CNV_CODEX)')
    return exe


def generate(unit, note='', hero=False, source=None):
    """hero: a cinematic shot (h<N>.png) instead of a sheet; source: images the sheet must follow"""
    _, refs, _ = BRIEFS[unit]
    out = os.path.join(UNITS, unit, 'gpt')
    os.makedirs(out, exist_ok=True)
    p = 'h' if hero else 'v'
    n = 1 + sum(1 for f in os.listdir(out) if f.startswith(p) and f.endswith('.png'))
    run = os.path.join(out, f'{p}{n}_run')
    os.makedirs(run, exist_ok=True)
    text = prompt(unit, note, hero, bool(source))
    open(os.path.join(run, 'prompt.txt'), 'w', encoding='utf-8').write(text)
    cmd = [codex(), 'exec', '--skip-git-repo-check', '-s', 'read-only', '-C', run, '--json',
           '-o', os.path.join(run, 'last.txt')]
    for r in refs:
        cmd += ['-i', os.path.join(REF, r + '_grid.png')]
    for s in source or []:
        cmd += ['-i', os.path.abspath(s)]
    cmd.append('-')
    with open(os.path.join(run, 'events.jsonl'), 'w', encoding='utf-8') as ev, \
            open(os.path.join(run, 'stderr.txt'), 'w', encoding='utf-8') as err:
        subprocess.run(cmd, input=text, text=True, encoding='utf-8', stdout=ev, stderr=err, check=True, cwd=run)
    thread = None
    for line in open(os.path.join(run, 'events.jsonl'), encoding='utf-8'):
        e = json.loads(line)
        if e.get('type') == 'thread.started':
            thread = e['thread_id']
    images = sorted(glob.glob(os.path.join(CODEX_IMAGES, thread or '-', '*.png')), key=os.path.getmtime)
    if not images:
        raise SystemExit(f'no image from thread {thread}; see {run}')
    sheet = os.path.join(out, f'{p}{n}.png')
    shutil.copy(images[-1], sheet)
    print(sheet)
    if not hero:
        views(sheet, os.path.join(out, f'v{n}_views'))
    return sheet


def _split(lo, hi, filled):
    """middle of the longest run of empty lines in the central 60 % of [lo, hi)"""
    a, b = lo + (hi - lo) // 5, hi - (hi - lo) // 5
    best, run, start = (0, (lo + hi) // 2), 0, a
    for i in range(a, b):
        if filled(i):
            run = 0
            continue
        if run == 0:
            start = i
        run += 1
        if run > best[0]:
            best = (run, start + run // 2)
    return best[1]


def views(sheet, out, size=1024):
    im = Image.open(sheet).convert('RGB')
    w, h = im.size
    bg = im.getpixel((5, 5))
    fg = ImageChops.difference(im, Image.new('RGB', im.size, bg)).convert('L').point(lambda v: 255 if v > 18 else 0)
    px = fg.load()
    ymid = _split(0, h, lambda y: any(px[x, y] for x in range(0, w, 2)))
    names = iter(['front', 'left', 'back', 'threequarter'])
    boxes = {}
    for y0, y1 in ((0, ymid), (ymid, h)):
        xmid = _split(0, w, lambda x: any(px[x, y] for y in range(y0, y1, 2)))
        for x0, x1 in ((0, xmid), (xmid, w)):
            b = fg.crop((x0, y0, x1, y1)).getbbox()
            boxes[next(names)] = (x0 + b[0], y0 + b[1], x0 + b[2], y0 + b[3])
    ortho = int(max(max(b[2] - b[0], b[3] - b[1]) for k, b in boxes.items() if k != 'threequarter') * 1.12)
    os.makedirs(out, exist_ok=True)
    for name, b in boxes.items():
        q = im.crop(b)
        s = ortho if name != 'threequarter' else int(max(q.size) * 1.12)
        c = Image.new('RGB', (s, s), bg)
        c.paste(q, ((s - q.width) // 2, (s - q.height) // 2))
        c = c.resize((size, size), Image.LANCZOS)
        c.save(os.path.join(out, name + '.png'))
        if name == 'left':
            ImageOps.mirror(c).save(os.path.join(out, 'right.png'))
        print(name, b)


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[0] == '--views':
        views(args[1], args[2])
    else:
        hero = '--hero' in args
        src = [args[i + 1] for i, a in enumerate(args) if a == '--from']
        rest = [a for i, a in enumerate(args) if a != '--hero' and a != '--from' and (i == 0 or args[i - 1] != '--from')]
        generate(rest[0], ' '.join(rest[1:]), hero=hero, source=src)
