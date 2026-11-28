from collections import Counter

import numpy as np

from experimental.mapgen import lot_miner, retail


def test_mine_fenced_and_textured_lots_without_roads(monkeypatch):
    # Two street faces. A fence cuts the all-grass west face; texture cuts the east face.
    base = np.zeros((10, 26), dtype=int)
    base[:, 20:] = 1
    roads = np.zeros_like(base, dtype=bool)
    roads[0, :] = roads[:, 13] = True
    land = np.ones_like(roads)
    fence = dict(template='TestFence', cell=(5, 6), x=65, y=55, angle=0, flags=0, props={}, footprint=())
    house = dict(template='T_House01', cell=(4, 2), x=25, y=45, angle=0, flags=0, props={},
                 footprint=({'Type': 'BOX', 'MajorRadius': 10, 'MinorRadius': 10},))
    monkeypatch.setattr(retail, 'model_vertices', lambda _: np.array([[0, -45], [0, 45]]))
    m = retail.RetailMap({}, base, land, ('TestGrass', 'TestPaving'), base,
                         np.array(['grass', 'paving'])[base], ~land, land, [fence, house], roads, ~land, [], [])
    spec = dict(exclude=[], uses={'park': [2]}, default_use='residential')
    measured = list(lot_miner.measure(m, spec, 36, 30, {}, {'t'}, {}))

    # The west/east faces have 13/12 columns of nine land cells. The road has its own column and row.
    assert [b['cells'] for b, _ in measured] == [117, 108]
    assert [sum(lot.cells for lot in lots) for _, lots in measured] == [117, 108]
    assert [Counter(lot.kind for lot in lots) for _, lots in measured] == [
        {'house': 1, 'lawn': 1}, {'lawn': 1, 'yard': 1},
    ]
    types, mixes = lot_miner._recipes((b['use'], lots) for b, lots in measured)
    assert mixes == {'residential': {'house': 1, 'lawn': 1}, 'park': {'lawn': 1, 'yard': 1}}
    assert types['house']['edges']['lot_to_lot'] == [{'treatment': 'fence', 'template': 'TestFence', 'count': 1}]
    assert types['house']['contents']['buildings'] == {'T_House01': 1}
