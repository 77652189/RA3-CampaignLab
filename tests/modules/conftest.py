from copy import deepcopy
from functools import cache

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
from engine.testing.small import island  # noqa: E402


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
