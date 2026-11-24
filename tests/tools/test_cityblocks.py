"""experimental/mappage/cityblocks.py: a block ringed by streets gets buildings on its kerb, none on the street."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'cityblocks', Path(__file__).resolve().parents[2] / 'experimental' / 'mappage' / 'cityblocks.py')
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)


def test_buildings_stand_on_the_kerb_off_the_street():
    foot = {'HouseA': [60, 40], 'HouseB': [50, 30]}
    setback = 8
    city = cb.City(600, foot, 1, lambda x, y, hill: 'd', {'d': 'test'}, {'d': 'T'},
                   kinds={'test': (['HouseA', 'HouseB'], setback, 6, 0.25, 1, cb.GRASS, 'x')})
    city.water([[-50, -50], [-10, -50], [-10, -10]], 'none')            # off the map: all land
    city.road([(40, 40), (560, 40), (560, 560), (40, 560), (40, 40)], 80)   # street 0-80 and 520-600 on every side
    city.build()
    houses = [o for o in city.objs if o['template'] in foot]
    assert len(houses) >= 4 and city.table[0]['buildings'] == len(houses)
    for o in houses:
        w, h = foot[o['template']]
        jj, ii = cb.rect_cells(o['x'], o['y'], w, h, o['angle'], city.n)
        assert not city.street[jj, ii].any(), o
        kerb = min(o['x'] - 80, 520 - o['x'], o['y'] - 80, 520 - o['y']) - min(w, h) / 2   # front wall to the kerb
        assert setback - 12 <= kerb <= setback + 2, (o, kerb)
