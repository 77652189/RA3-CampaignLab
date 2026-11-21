from copy import deepcopy
from functools import cache

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.data.units as simunits  # noqa: E402
from engine.testing.small import island, small_world  # noqa: E402


@pytest.fixture(scope='session')
def cached_island_ground():
    """Generate the deterministic island terrain once per worker, on first use."""
    return cache(island.ground)


@pytest.fixture(scope='module', autouse=True)
def reuse_island_ground(cached_island_ground):
    """Reuse terrain generation in module tests while giving each world its own copy."""
    def ground():
        return deepcopy(cached_island_ground())

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(island, 'ground', ground)
        yield


@pytest.fixture
def weapon_world(monkeypatch):
    """Give the test a fresh world and fire its SampleHit XML at 15 Hz."""
    s = small_world(model=False)

    def fire(xml, target, caster, shots_due=lambda *_: 1):
        weapons = simunits._weapons([xml])
        weapon = simunits._resolve(weapons['SampleHit'], weapons)
        s.volleys = [(target, weapon, caster)]
        monkeypatch.setattr(s, 'shots_due', shots_due)
        s.deal(1 / 15)
        return weapon

    return s, fire
