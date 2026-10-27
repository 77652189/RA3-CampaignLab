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


def prompt(unit, note=''):
    faction, refs, brief = BRIEFS[unit]
    names = ', '.join(refs)
    kind = KIND.get(faction, 'unit')
    what = f'{faction} {kind}' if kind == 'unit' else f'{faction} {kind} (a map object, not a vehicle)'
    return f'''Generate ONE image with your image generation tool. Do not write code, do not run commands, do not edit files. Just generate the image and reply with one short sentence.

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


def generate(unit, note=''):
    _, refs, _ = BRIEFS[unit]
    out = os.path.join(UNITS, unit, 'gpt')
    os.makedirs(out, exist_ok=True)
    n = 1 + sum(1 for f in os.listdir(out) if f.startswith('v') and f.endswith('.png'))
    run = os.path.join(out, f'v{n}_run')
    os.makedirs(run, exist_ok=True)
    text = prompt(unit, note)
    open(os.path.join(run, 'prompt.txt'), 'w', encoding='utf-8').write(text)
    cmd = [codex(), 'exec', '--skip-git-repo-check', '-s', 'read-only', '-C', run, '--json',
           '-o', os.path.join(run, 'last.txt')]
    for r in refs:
        cmd += ['-i', os.path.join(REF, r + '_grid.png')]
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
    sheet = os.path.join(out, f'v{n}.png')
    shutil.copy(images[-1], sheet)
    print(sheet)
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
    if sys.argv[1] == '--views':
        views(sys.argv[2], sys.argv[3])
    else:
        generate(sys.argv[1], ' '.join(sys.argv[2:]))
