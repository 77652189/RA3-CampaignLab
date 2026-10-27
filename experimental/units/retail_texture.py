"""Pull a retail texture out of the game's static stream as PNG (reference only: the PNG goes to work/, not git).

  python -I experimental/units/retail_texture.py <texture id> [...]     -> work/reference/<id>.png

Ids as the asset names have them, e.g. AUAntiVehicleVehicleTech1_NRM; matched case-insensitively.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
sys.path.insert(0, HERE)
from PIL import Image                           # noqa: E402

import button_icon                              # noqa: E402  (its STATIC layer list)

OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'reference')


def main(names):
    import mapxml
    lib = mapxml.layered(button_icon.WORLDBUILDER + button_icon.STATIC)
    by = {i.name.lower(): i for i in lib.values()}
    os.makedirs(OUT, exist_ok=True)
    for n in names:
        inst = by.get(b'texture:' + n.lower().encode())
        if inst is None:
            print('not found:', n, [k.decode() for k in by if n.lower().encode()[:12] in k][:8])
            continue
        raw = bytes(inst.chunks[0])
        im = Image.open(io.BytesIO(raw[raw.find(b'DDS '):]))
        print(n, im.size, im.mode, 'DDS fourcc', raw[raw.find(b'DDS ') + 84:raw.find(b'DDS ') + 88])
        im.save(os.path.join(OUT, n + '.png'))


if __name__ == '__main__':
    main(sys.argv[1:])
