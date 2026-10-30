"""Our units' ability buttons in the retail style, from GPT's image model (concept_gpt.py's Codex CLI): one image per
faction, a grid of icons drawn after three of that faction's retail ability icons (button_icon.retail), cut into
82 x 82 buttons and written into the SDK's Art as one asset file each (CNA_<key>.xml: Texture CNA_<key>_tex and the
PackedTextureImage CNA_<key> a ButtonSingleStateData names; experimental/cnv/units/look.py wires them).

  python -I -X utf8 experimental/units/ability_icons.py gen [<faction> ...]   one generation per faction (~70 s)
  python -I -X utf8 experimental/units/ability_icons.py write                cut the sheets, write the Art

Sheets and cells under work/units/abilities/ (gitignored; a lost sheet is generated again, the icons may differ).
"""
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
sys.path.insert(0, HERE)
import labpaths                                 # noqa: E402
from PIL import Image, ImageEnhance             # noqa: E402

OUT = os.path.join(labpaths.WORK, 'units', 'abilities')
SIZE = 82                                       # retail ability buttons (SUA_Sickle_Leap, AUA_Bribe ...) are 82 square
# faction: (grid columns, rows, retail references, the background the references share)
FACTIONS = {
    'allied': (3, 2, ['AUA_Bribe', 'AUA_Tank_TargetPainter', 'AUA_Timebelt'], 'deep blue'),
    'soviet': (3, 3, ['SUA_Sickle_Leap', 'SUA_Evacuate', 'SUA_Engineer_Bunker'], 'deep red'),
    'japan': (3, 3, ['JUA_KingOni_BullRush', 'JUA_Kagami_Armor', 'JUA_Shinobi_SmokeBomb'], 'orange-gold'),
}
# key: (faction, what the icon shows), in grid order (left to right, top to bottom)
ICONS = {
    'freeze': ('allied', 'a thick wall of faceted pale-cyan ice blocks rising out of the ground across a road'),
    'pull': ('allied', 'a glowing cyan chrono beacon on a pole, three small soldier silhouettes being pulled toward '
                       'it along swirling cyan time-streaks'),
    'deploy': ('allied', 'a stopwatch face cracked by a cyan time-distortion ripple, an artillery shell frozen in it'),
    'pack': ('allied', 'two heavy tank tracks with motion arrows, ready to drive'),
    'deck': ('allied', 'a floating island fortress platform seen from the side vanishing in a bright cyan chrono '
                       'flash, a ring of light under it'),
    'burrow': ('soviet', 'a heavy drill nose boring down into brown earth, dirt flying'),
    'surface': ('soviet', 'an armoured vehicle bursting up out of cracked earth'),
    'jam': ('soviet', 'a radio dish sending out jagged red static waves over a slowed gear'),
    'jam_off': ('soviet', 'a radio dish folded down, a crossed-out static wave'),
    'surge': ('soviet', 'a tesla coil on a tank turret throwing blue-white lightning all round'),
    'surge_off': ('soviet', 'a tesla coil with its lightning dying, small sparks only'),
    'brake': ('soviet', 'a locomotive wheel on a rail clamped by a brake shoe, sparks'),
    'brake_off': ('soviet', 'a locomotive wheel on a rail with forward motion lines'),
    'guard': ('japan', 'a white folded-paper warrior figure holding up a glowing paper talisman shield, bullets '
                       'bending toward it'),
    'guard_off': ('japan', 'a white folded-paper warrior figure standing at rest, the talisman lowered'),
    'rush': ('japan', 'a huge mech fist charging forward through a building wall, speed lines'),
    'armor': ('japan', 'a hexagonal energy shield glowing over a small tank'),
    'part': ('japan', 'two mech halves separating apart with a bright split line between them'),
    # the mind maiden (J8) is the Empire's; first drawn on the Allied sheet, its sixth cell is left unused
    'control': ('japan', 'a white glowing hand breaking a puppet string that runs down to a small tank'),
    # no ability: the paper-crane scout's badge on the Twinblade's pictures (BADGED)
    'crane': ('japan', 'a white folded-paper crane gliding, a faint eye shape in the glow behind it'),
}
STYLE = '''- the style of the reference icons exactly: Red Alert 3 ability buttons -- a square button with a thin bevelled
  frame and slightly rounded corners, a {bg} glossy background with a soft radial glow, one bold simple symbol in
  the middle, painted, high contrast, readable at 40 pixels.
- no text, no letters, no numbers, no logos.'''
LAYOUT = '''- one square image: a {cols} x {rows} grid of equal square icons on a plain flat light-grey (#D0D0D0) background,
  a clear gap of grey between icons, no labels.
- the icons, left to right, top to bottom:
{items}'''


def keys(faction):
    return [k for k, (f, _) in ICONS.items() if f == faction]


def refs(faction):
    import button_icon
    folder = os.path.join(labpaths.WORK, 'reference', 'abilities')
    os.makedirs(folder, exist_ok=True)
    out = []
    for name in FACTIONS[faction][2]:
        p = os.path.join(folder, name + '.png')
        if not os.path.exists(p):
            button_icon.retail(name).resize((256, 256), Image.LANCZOS).save(p)
        out.append(p)
    return out


def generate(faction):
    import concept_gpt
    cols, rows, _, bg = FACTIONS[faction]
    ks = keys(faction)
    assert len(ks) <= cols * rows, (faction, len(ks))
    items = '\n'.join(f'  {i + 1}. {ICONS[k][1]}' for i, k in enumerate(ks))
    if len(ks) < cols * rows:
        items += f'\n  (the last {cols * rows - len(ks)} cells: empty grey)'
    text = ('Make a game UI icon sheet. The attached images are three ability buttons from Red Alert 3.\n'
            + STYLE.format(bg=bg) + '\n' + LAYOUT.format(cols=cols, rows=rows, items=items))
    run = os.path.join(OUT, f'{faction}_run')
    os.makedirs(run, exist_ok=True)
    open(os.path.join(run, 'prompt.txt'), 'w', encoding='utf-8').write(text)
    cmd = [concept_gpt.codex(), 'exec', '--skip-git-repo-check', '-s', 'read-only', '-C', run, '--json',
           '-o', os.path.join(run, 'last.txt')]
    for r in refs(faction):
        cmd += ['-i', r]
    cmd.append('-')
    with open(os.path.join(run, 'events.jsonl'), 'w', encoding='utf-8') as ev, \
            open(os.path.join(run, 'stderr.txt'), 'w', encoding='utf-8') as err:
        subprocess.run(cmd, input=text, text=True, encoding='utf-8', stdout=ev, stderr=err, check=True, cwd=run)
    thread = None
    for line in open(os.path.join(run, 'events.jsonl'), encoding='utf-8'):
        e = json.loads(line)
        if e.get('type') == 'thread.started':
            thread = e['thread_id']
    images = sorted(glob.glob(os.path.join(concept_gpt.CODEX_IMAGES, thread or '-', '*.png')), key=os.path.getmtime)
    if not images:
        raise SystemExit(f'no image from thread {thread}; see {run}')
    sheet = os.path.join(OUT, faction + '.png')
    shutil.copy(images[-1], sheet)
    print(sheet)
    return sheet


def cells(faction):
    """The sheet's icons: each grid cell trimmed of the grey round it (pixels far from #D0D0D0), squared."""
    import numpy as np
    cols, rows, _, _ = FACTIONS[faction]
    im = Image.open(os.path.join(OUT, faction + '.png')).convert('RGB')
    a = np.asarray(im, float)
    ink = np.abs(a - 208).max(axis=2) > 24
    W, H = im.size
    out = {}
    for i, k in enumerate(keys(faction)):
        c, r = i % cols, i // cols
        x0, x1, y0, y1 = W * c // cols, W * (c + 1) // cols, H * r // rows, H * (r + 1) // rows
        ys, xs = np.nonzero(ink[y0:y1, x0:x1])
        bx0, bx1, by0, by1 = x0 + xs.min(), x0 + xs.max() + 1, y0 + ys.min(), y0 + ys.max() + 1
        side = max(bx1 - bx0, by1 - by0)
        cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2
        box = (cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)
        icon = ImageEnhance.Contrast(im.crop(box).resize((SIZE, SIZE), Image.LANCZOS)).enhance(1.05)
        out[k] = icon
    return out


def write():
    import w3x
    folder = os.path.join(w3x.ART, 'CN')
    os.makedirs(folder, exist_ok=True)
    os.makedirs(os.path.join(OUT, 'icons'), exist_ok=True)
    for faction in FACTIONS:
        if not os.path.exists(os.path.join(OUT, faction + '.png')):
            print('SKIPPED', faction, '(no sheet: gen', faction + ')')
            continue
        for k, icon in cells(faction).items():
            name = f'CNA_{k}'
            icon.save(os.path.join(OUT, 'icons', name + '.png'))
            page = Image.new('RGBA', (128, 128))
            page.paste(icon.convert('RGBA'), (0, 0))
            page.save(os.path.join(folder, name + '.tga'))
            with open(os.path.join(folder, name + '.xml'), 'w', encoding='utf-8', newline='\r\n') as out:
                out.write('<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset" '
                          'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
                          f'\t<Texture id="{name}_tex" File="{name}.tga" OutputFormat="A8R8G8B8" GenerateMipMaps="false"'
                          ' AllowAutomaticResize="false"/>\n'
                          f'\t<PackedTextureImage id="{name}" Texture="{name}_tex" Rotated="false">\n'
                          f'\t\t<Dimensions x="{SIZE}" y="{SIZE}"/>\n\t\t<Coords x="0" y="0"/>\n'
                          '\t\t<TextureDimensions x="128" y="128"/>\n\t</PackedTextureImage>\n</AssetDeclaration>\n')
            print(name, '->', os.path.join(folder, name + '.xml'))


# our units on retail models: model -> (retail button, retail portrait, the ability icon badged on them). Their
# build buttons beside the retail unit's (the jammer and the Sickle in one factory) read apart by the badge
BADGED = {
    'CNBeacon': ('Button_AlliedAntiInfantryInfantry_on', 'Portrait_AlliedAntiInfantryInfantry', 'pull'),
    'CNBurrower': ('Button_SovietAntiAirShip_small', 'Portrait_SovietAntiAirShip_big', 'burrow'),
    'CNJammer': ('Button_SovietAntiInfantryVehicle_small', 'Portrait_SovietAntiInfantryVehicle_big', 'jam'),
    'CNTesla': ('Button_SovietTeslaTank_small', 'Portrait_SovietTeslaTank_big', 'surge'),
    'CNTrain': (None, None, 'brake'),          # retail's campaign train has no pictures: its icon, enlarged
    'CNShikigami': ('Button_JapanAntiInfantryInfantry', 'Portrait_JapanAntiInfantryInfantry', 'guard'),
    'CNComboParent': ('Button_JapanAntiVehicleVehicleTech3', 'Portrait_JapanAntiVehicleVehicleTech3', 'part'),
    'CNComboChild': ('Button_JapanAntiVehicleVehicleTech1', 'Portrait_JapanAntiVehicleVehicleTech1', 'part'),
    'CNMaiden': ('Button_AlliedInfiltrationInfantry_on', 'Portrait_AlliedInfiltrationInfantry', 'control'),
    'CNCrane': ('Button_SovietAntiGroundAircraft_small', 'Portrait_SovietAntiGroundAircraft_big', 'crane'),
}


def badge_folder(model):
    return os.path.join(labpaths.WORK, 'units', 'badged', model, 'game')      # ui_kit's work/units/<unit>/game


def badges():
    """BADGED's buttons and portraits -> work/units/badged/<model>/Button_<model>.tga, Portrait_<model>.tga: the
    retail image, the ability icon at its bottom right (two fifths of the height, a dark rim); no retail image (None):
    the ability icon itself, filling the button (the portrait its middle band)."""
    import button_icon
    from PIL import ImageDraw
    for model, (button, portrait, key) in BADGED.items():
        icon = Image.open(os.path.join(OUT, 'icons', f'CNA_{key}.png')).convert('RGBA')
        out = badge_folder(model)
        os.makedirs(out, exist_ok=True)
        for kind, name, size in (('Button', button, (106, 106)), ('Portrait', portrait, (101, 76))):
            if name is None:
                big = icon.resize((size[0], size[0]), Image.LANCZOS)
                im = big.crop((0, (size[0] - size[1]) // 2, size[0], (size[0] + size[1]) // 2))
            else:
                im = button_icon.retail(name)
                w, h = im.size
                s = round(h * 0.42)
                x, y = w - s - 5, h - s - 5
                ImageDraw.Draw(im).rectangle((x - 2, y - 2, x + s + 1, y + s + 1), fill=(8, 12, 18, 255))
                im.alpha_composite(icon.resize((s, s), Image.LANCZOS), (x, y))
            path = os.path.join(out, f'{kind}_{model}.tga')
            im.save(path)
            im.save(os.path.splitext(path)[0] + '_preview.png')
        print(model, '->', out)


if __name__ == '__main__':
    if sys.argv[1] == 'gen':
        for f in sys.argv[2:] or list(FACTIONS):
            generate(f)
    elif sys.argv[1] == 'badges':
        badges()
    else:
        write()
