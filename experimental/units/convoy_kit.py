"""The convoy truck's cargo (A4 / J4, experimental/cnv/units/convoy.py: retail's Allied ore collector): retail's
snowy cargo container prop (AP_SNOWYCARGOCONTAINER01, World Builder's stream) scaled into the collector's bin,
written as CNConvoyCargo -- a model the truck draws in place of its ore (convoy_look.dress), at the truck's origin:

  python -I -X utf8 experimental/units/convoy_kit.py        -> SDK Art (CNConvoyCargo + CNCargo textures)
                                                              and work/units/convoy/convoy_grid.png (with the truck)

The collector (AUHARVESTER_SKN, +X forward): 51 long (-20 .. 31), 30 wide, its bin's lining (ORE_BUCKET) 19 x 18
with the floor at 6.9 and the rim at 15. The container is 39 x 19 x 18: at SCALE it is 28 long, sits in the bin
and stands ~5 above the rim, a little forward of the bin's open back (AT). Textures: the prop's own (AP_AlliedSnowyProps01),
its normal map flat (no tangent frames written), its SPM's specular kept, no glow, no house colour.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
sys.path.insert(0, HERE)
import labpaths                                 # noqa: E402
import retail_mesh                              # noqa: E402
import retail_sheet                             # noqa: E402
import retail_texture                           # noqa: E402
import w3x                                      # noqa: E402
from PIL import Image                           # noqa: E402

MODEL, TEXTURE = 'CNConvoyCargo', 'CNCargo'
PROP, PROP_TEX = 'AP_SNOWYCARGOCONTAINER01', 'AP_AlliedSnowyProps01'
SCALE = 0.72
AT = (0.5, 0.0, 7.5)                            # where the container's bottom middle goes, in the truck's space (at
                                                # 0.77 and x -4 its rear end showed through the bin's open back; at
                                                # x -2.5 the bench showed a strip of empty bin before the cab)
OUT = os.path.join(labpaths.WORK, 'units', 'convoy')


def cargo(by):
    m = retail_mesh.load(by, PROP)
    verts = [(x * SCALE + AT[0], y * SCALE + AT[1], z * SCALE + AT[2]) for x, y, z in m['vertices']]
    uvs = [(u, 1 - v) for u, v in m['uvs']]             # compiled meshes are v-down; ours as Blender's
    w3x.write_model(MODEL, w3x.rig_model(MODEL, [], [('CARGO', 0, (verts, m['normals'], uvs, m['triangles']))],
                                         (TEXTURE, TEXTURE + '_NRM', TEXTURE + '_SPM')))
    os.makedirs(OUT, exist_ok=True)
    obj = os.path.join(OUT, MODEL + '.obj')
    retail_mesh.write_obj(dict(vertices=verts, uvs=m['uvs'], triangles=m['triangles'], layout='convoy_kit'), obj)
    return obj, len(m['triangles'])


def textures():
    retail_texture.main([PROP_TEX, PROP_TEX + '_SPM'])
    d = Image.open(os.path.join(retail_texture.OUT, PROP_TEX + '.png')).convert('RGB')
    s = Image.open(os.path.join(retail_texture.OUT, PROP_TEX + '_SPM.png')).convert('RGB').resize(d.size)
    dp, sp = d.load(), s.load()
    w, h = d.size
    w3x.write_texture(TEXTURE, w, h, lambda x, y: (*dp[x, y], 255))
    w3x.write_texture(TEXTURE + '_NRM', 16, 16, lambda x, y: (128, 128, 255, 255))
    w3x.write_texture(TEXTURE + '_SPM', w, h, lambda x, y: (sp[x, y][0], 0, 0, 255))
    return os.path.join(retail_texture.OUT, PROP_TEX + '.png')


def main():
    by = retail_mesh.library()
    tex = textures()
    obj, n = cargo(by)
    retail_texture.main(['AUHarvester', 'AUHarvester_SPM'])
    truck = os.path.join(retail_mesh.OUT, 'AUHARVESTER_SKN.NEWSKIN.obj')
    retail_mesh.write_obj(retail_mesh.load(by, 'AUHARVESTER_SKN.NEWSKIN'), truck)
    prefix = os.path.join(OUT, 'convoy')
    specs = [f'{truck}={os.path.join(retail_texture.OUT, "AUHarvester.png")}='
             f'{os.path.join(retail_texture.OUT, "AUHarvester_SPM.png")}', f'{obj}={tex}']
    subprocess.run([retail_sheet.BLENDER, '-b', '--factory-startup', '-P', retail_sheet.__file__, '--', prefix] + specs,
                   check=True, stdout=subprocess.DEVNULL)
    grid = Image.new('RGB', (1536, 1536), (208, 208, 208))
    for k, v in enumerate(retail_sheet.VIEWS):
        grid.paste(Image.open(f'{prefix}_{v}.png').convert('RGB').resize((768, 768)), ((k % 2) * 768, (k // 2) * 768))
    grid.resize((1024, 1024), Image.LANCZOS).save(prefix + '_grid.png')
    print(MODEL, n, 'triangles ->', prefix + '_grid.png')


if __name__ == '__main__':
    main()
