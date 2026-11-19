"""The fixed island shared by the map writer and simulator keeps its exact heights."""
from hashlib import sha256
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np

CAMPAIGN = Path(__file__).resolve().parents[2] / 'experimental' / 'campaign'


def _scalar_heights(newmap, dims, center, radius):
    # The original row-major height loop. Use the host's math library, as the generator did.
    seed = 7
    coast = newmap.value_noise(seed, 700.0)
    rough = newmap.value_noise(seed + 1, 260.0)
    hills = newmap.value_noise(seed + 2, 900.0)
    cx, cy = center
    cell = newmap.mapterrain.CELL
    for j in range(dims.height):
        for i in range(dims.width):
            x, y = (i - dims.border) * cell, (j - dims.border) * cell
            ang = math.atan2(y - cy, x - cx)
            r = radius * (0.75 + 0.5 * coast(1000 + 600 * math.cos(ang), 1000 + 600 * math.sin(ang)))
            d = math.hypot(x - cx, y - cy) / r
            land = max(0.0, min(1.0, (1.0 - d) / 0.12))
            hill = max(0.0, hills(x, y) - 0.55) / 0.45
            yield 230.0 + land * (95.0 + 25 * rough(x, y) + 140 * hill * hill * land)


def test_fixed_island_height_bytes():
    spec = importlib.util.spec_from_file_location('island_height_campnew18', CAMPAIGN / 'make_campnew18.py')
    c18 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c18)
    import platmap

    w, h, b = platmap.CONTAINER
    dims = SimpleNamespace(width=w, height=h, border=b)
    options = dict(center=c18.CENTER, radius=c18.RADIUS)
    want = sha256(np.fromiter(_scalar_heights(c18.newmap, dims, **options), dtype='<f8', count=w * h)).hexdigest()

    # Both callers get their own row-major dictionary, even after the field is cached.
    heights = c18.newmap.island_heights(dims, **options)
    again = c18.newmap.island_heights(dims, **options)
    assert again is not heights
    for field in (heights, again):
        assert len(field) == w * h
        assert all(key == (k % w, k // w) for k, key in enumerate(field))
        got = sha256(np.fromiter(field.values(), dtype='<f8', count=w * h)).hexdigest()
        assert got == want
