"""时滞炮车's two models written into the SDK's Art (as ice_kit / liberty_kit do), for experimental/cnv/units/chronolag.py:

  CNChrono     packed: tripo_unit.py chronolag (Tripo chronolag_v2_hd.glb, hull / turret / barrel)
  CNChronoDep  deployed (user 2026-11-17): tripo_unit.py chronolag_dep (the Hunyuan model cut into hull + turret,
               the gun yaws, its barrel fixed at ~25 deg; team colour on the three reserved panels)

  python -I -X utf8 experimental/units/chrono_kit.py [CNChrono|CNChronoDep ...]   (default both; from a worktree set
  CNV_SDK; run the tripo_unit.py steps first; buttons and portraits are ui_kit.py CNChrono's)

The look is make_campchrono.py's (it reads LEVEL / LOOK from here): the bake as it is, cooled, its cyan lights caught
wider and lifted (user 2026-10-26: "太暗了，调亮一点，青色光要看得见"). make_campchrono.py also builds the old
CampChrono1 sample mod; that build needs gone experiments (work/units/shrinkvehicle), this file does not.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import to_w3x                                   # noqa: E402
import labpaths                                 # noqa: E402  (to_w3x put experimental/campaign on the path)

LEVEL = int(os.environ.get('CNV_CHRONO_LEVEL', 85))     # diffuse median (retail Allied vehicles 62..80); the bake's
# own is 84 and level only darkens: 62 read dark and brown beside the Guardian (user 2026-10-26)
LOOK = dict(glow_margin=30, glow_floor=120, glow_lift=True, cool=1.08)
# model -> (work/units/<unit>/game, part -> bone)
MODELS = {'CNChrono': ('chronolag', {'HULL': 'BODY', 'TURRET': 'Bone_Turret', 'BARREL': 'Bone_Turret_Pitch'}),
          'CNChronoDep': ('chronolag_dep', {'HULL': 'BODY', 'TURRET': 'Bone_Turret'})}


def src(model):
    return os.path.join(labpaths.WORK, 'units', MODELS[model][0], 'game')


def pivots(model):
    with open(os.path.join(src(model), 'parts.json'), encoding='utf-8') as f:
        return [(n, p, tuple(at)) for n, p, at in json.load(f)['_pivots']]


def write(model):
    return to_w3x.convert(src(model), model, pivots(model), MODELS[model][1], src_name=model, level=LEVEL,
                          retail_maps=True, **LOOK)


def main(models):
    for model in models or MODELS:
        if not os.path.exists(os.path.join(src(model), 'parts.json')):
            print(model, 'skipped: no', os.path.join(src(model), 'parts.json'), '-- run Blender tripo_unit.py',
                  MODELS[model][0], 'first')
            continue
        print(model, write(model), 'triangles')


if __name__ == '__main__':
    main(sys.argv[1:])
