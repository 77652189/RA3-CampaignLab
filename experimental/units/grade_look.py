r"""faction_grade on the bench -- CampGradeLook: the hook tank and the burrower (Tripo bakes, tripo_unit.py) each
twice, the bake as it is and graded to the Soviet retail vehicles, in a row beside the retail Hammer, Bullfrog and
Apocalypse, one camera on all of them (user 2026-11-15: "注意美术风格上要协调").

  "C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe" -b --factory-startup
      -P experimental/units/tripo_unit.py -- hooktank          (and burrower)
  python -I -X utf8 experimental/units/grade_look.py models    -> SDK Art: CNHookRaw / CNHook, CNBurrowRaw / CNBurrow
  python -I -X utf8 experimental/units/grade_look.py           -> Documents\Red Alert 3\Mods\CampGradeLook

Each look unit is a copy of the retail Hammer wearing the model (look only: it keeps the Hammer's weapons and
bones it does not have -- no tread scrolling, no muzzle flash where it should be).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'cnv'))
import parts                                    # noqa: E402  (puts experimental/campaign on the path)
import labpaths                                 # noqa: E402
from maps import island                         # noqa: E402
from model import Unit                          # noqa: E402

NAME = 'CampGradeLook'                          # <= 15 characters, no underscore
HAMMER = 'SovietAntiVehicleVehicleTech1'
RETAIL = [HAMMER, 'SovietAntiAirShip', 'SovietAntiVehicleVehicleTech3']
PARTS = {'HULL': 'BODY', 'TURRET': 'Bone_Turret', 'BARREL': 'Bone_Turret_Pitch'}
LOOKS = [('hooktank', 'CNHook'), ('burrower', 'CNBurrow')]   # (tripo_unit name, graded model; raw = model + Raw)


def models():
    import to_w3x
    for unit, model in LOOKS:
        src = os.path.join(labpaths.WORK, 'units', unit, 'game')
        with open(os.path.join(src, 'parts.json'), encoding='utf-8') as f:
            pivots = [(n, p, tuple(at)) for n, p, at in json.load(f)['_pivots']]
        for name, faction in ((model + 'Raw', None), (model, 'soviet')):
            print(name, to_w3x.convert(src, name, pivots, PARTS, src_name=model, level=None, grade=False,
                                       retail_maps=True, faction=faction), 'triangles')


def wearing(id, model):
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', HAMMER + '.xml'), encoding='utf-8').read()
    x = x.replace(f'id="{HAMMER}"', f'id="{id}"', 1)
    x = re.sub(r'(<Model\s+Name=")[^"]*(")', lambda m: m.group(1) + model.upper() + m.group(2), x)
    x = re.sub(r'AnimationName="[^"]*"', f'AnimationName="{model.upper()}_IDLE"', x)
    x = re.sub(r'\s*<TreadScrollingMap\b[^>]*/>', '', x)
    x = x.replace('<Includes>', f'<Includes>\n\t\t<Include type="all" source="ART:{model}.w3x" />'
                                f'\n\t\t<Include type="all" source="ART:{model}_IDLE.w3x" />', 1)
    return Unit(id, x)


def mission():
    looks = [wearing(f'CNV_Look{model}{tag}', model + tag) for _, model in LOOKS for tag in ('Raw', '')]
    m = parts.Mission(name=NAME, map=island, units=looks)
    row = RETAIL[:2] + [u.id for u in looks] + RETAIL[2:]
    for k, t in enumerate(row):
        m.put(t, 'west field', -60 + 75 * k, 60, name=f'UNIT - CNV Grade {k}', angle=0.0)   # x 1120..1570
    m.scripts += [parts.Script('Look - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    return m


if __name__ == '__main__':
    if sys.argv[1:] == ['models']:
        models()
    else:
        print(parts.assemble(mission()))
