"""Ground builds and routes a bridge deck independently of the water beneath."""
from types import SimpleNamespace

import numpy as np

import newmap
import platmap
from sim import Ground


def test_bridge_connects_ground_banks_and_ignores_an_obstacle_on_the_deck(monkeypatch):
    h = newmap.WATERLINE
    elevation = np.full((32, 48), h + 100, dtype=float)
    elevation[:, 16:32] = h - 100  # a north/south channel, cutting the map in two
    monkeypatch.setattr(platmap, 'heights', lambda *args: (elevation, None))
    start, goal = (100, 140), (380, 140)
    markers = [
        SimpleNamespace(x=x, y=y, flags=flags, template='BridgeMarker')
        for (x, y), flags in [(start, platmap.BRIDGE_START), (goal, platmap.BRIDGE_END)]
    ]
    terrain = SimpleNamespace(DIMS=(48, 32, 0), LAYOUT=[], OBJECTS=markers)
    g = Ground(terrain)
    deck, water = (240, 140), (240, 240)

    # The two markers lay a 120-wide ground deck across the channel. An
    # amphibian on shore can fall back to it; the water grid still runs below it.
    assert g.route('ground', start, goal) == [goal]
    assert g.route('both', start, goal) == [goal]
    assert g.route('water', deck, water) == [water]
    assert not g.open('ground', *water)
    g.set_blocks([(*deck, 20)])
    assert g.open('ground', *deck) and g.route('ground', start, goal) == [goal]
