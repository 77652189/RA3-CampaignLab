"""A unit's production button and selection portrait written into the SDK's Art folder, as its models are, for the
experimental/cnv units (no shared build step: the unit's dress() includes the ART: file and names the images).

  python -I -X utf8 experimental/units/ui_kit.py [<model> ...]       (default: all of UNITS)

The images are button_icon.py's (compose button|portrait <render> <out.tga>, kept under work/units/<unit>/game,
gitignored). Each goes in as Art/<XX>/<model><Kind>.tga padded to 128 square (the image at the top left, as
make_campnew26.image_assets did) and one asset file <model><Kind>.xml holding its Texture (<model><Kind>_tex) and the
PackedTextureImage the GameObject names: Button_<model> / Portrait_<model> (images()).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
import labpaths                                 # noqa: E402
import w3x                                      # noqa: E402
from PIL import Image                           # noqa: E402

# model -> (work/units/<unit>/game, button tga, portrait tga)
UNITS = {'CNChrono': ('chronolag', 'Button_CNV_PhaseProbe_on.tga', 'Portrait_CNV_PhaseProbe.tga'),
         'CNIceEngineer': ('iceengineer', 'Button_CNIceEngineer.tga', 'Portrait_CNIceEngineer.tga'),   # ice_kit
         # the Tripo platform's render (tripo_unit.py icon.png) on the Allied plates: button_icon.py compose
         'CNLiberty': ('libertyisle', 'Button_CNLiberty.tga', 'Portrait_CNLiberty.tga'),
         'CNIceSculpt': ('icesculpture', 'Button_CNIceSculpt.tga', 'Portrait_CNIceSculpt.tga'),    # ice_kit
         'CNIceSculptHard': ('icesculpture', 'Button_CNIceSculptHard.tga', 'Portrait_CNIceSculptHard.tga'),
         'CNSnowBank': ('ice', 'Button_CNSnowBank.tga', 'Portrait_CNSnowBank.tga'),                # ice_kit.kit_icons
         'CNLockGate': ('ice', 'Button_CNLockGate.tga', 'Portrait_CNLockGate.tga')}
# our units on retail models: the retail image with their ability icon badged on (ability_icons.py badges)
UNITS.update({m: (f'badged/{m}', f'Button_{m}.tga', f'Portrait_{m}.tga') for m in
              ('CNBeacon', 'CNBurrower', 'CNJammer', 'CNTesla', 'CNTrain', 'CNShikigami', 'CNComboParent',
               'CNComboChild', 'CNMaiden', 'CNCrane', 'CNIceWall')})
KINDS = ('Button', 'Portrait')


def images(model):
    """{kind: (asset file name without .xml, PackedTextureImage id, Texture id)} for a model's button and portrait."""
    return {k: (f'{model}{k}', f'{k}_{model}', f'{model}{k}_tex') for k in KINDS}


def write(model):
    unit, *files = UNITS[model]
    src = os.path.join(labpaths.WORK, 'units', unit, 'game')
    folder = os.path.join(w3x.ART, model[:2].upper())
    os.makedirs(folder, exist_ok=True)
    for kind, f in zip(KINDS, files):
        name, image, tex = images(model)[kind]
        icon = Image.open(os.path.join(src, f)).convert('RGBA')
        page = Image.new('RGBA', (128, 128))
        page.paste(icon, (0, 0))
        page.save(os.path.join(folder, name + '.tga'))
        w, h = icon.size
        with open(os.path.join(folder, name + '.xml'), 'w', encoding='utf-8', newline='\r\n') as out:
            out.write('<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset" '
                      'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
                      f'\t<Texture id="{tex}" File="{name}.tga" OutputFormat="A8R8G8B8" GenerateMipMaps="false"'
                      ' AllowAutomaticResize="false"/>\n'
                      f'\t<PackedTextureImage id="{image}" Texture="{tex}" Rotated="false">\n'
                      f'\t\t<Dimensions x="{w}" y="{h}"/>\n\t\t<Coords x="0" y="0"/>\n'
                      '\t\t<TextureDimensions x="128" y="128"/>\n\t</PackedTextureImage>\n</AssetDeclaration>\n')
        print(model, kind, f'{w}x{h}', '->', os.path.join(folder, name + '.xml'))


if __name__ == '__main__':
    for m in sys.argv[1:] or sorted(UNITS):
        write(m)
