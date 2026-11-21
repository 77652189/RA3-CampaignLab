"""The terrain query used at a knockback's landing."""
from types import SimpleNamespace

import numpy as np

from sim import Ground


def test_amphibious_route_lands_by_the_shallows():
    # An 8-unit rise per fine cell joins deep water to dry ground, below
    # the 9-unit slope limit. The middle row of heights straddles the shore.
    elevation = np.tile([296] * 36 + [304, 312, 320, 328, 336, 344] + [352] * 12, (12, 1))
    g = Ground(SimpleNamespace(DIMS=(54, 12, 0), WATERLINE=320,
                               ground=lambda: SimpleNamespace(e=elevation)))
    sea, bank = (40, 60), (460, 60)
    assert g.open('water', *sea) and not g.open('ground', *sea)
    assert g.open('ground', *bank) and not g.open('water', *bank)
    assert g.route('ground', sea, bank) is None  # dry ground is outside the 300-unit snap range
    assert g.route('both', sea, bank) == [bank]


def test_knock_landing_moves_inland_and_uses_the_vehicle_half_cell_offset():
    elevation = np.full((24, 24), 400.0)
    elevation[:, :10] = 300.0
    g = Ground(SimpleNamespace(DIMS=(24, 24, 0), WATERLINE=320, ground=lambda: SimpleNamespace(e=elevation)))

    # x=80 is wet. x=100 is the first dry four-corner cell on the
    # man's 20-unit lattice. A vehicle first snaps to (90, 110), then
    # searches its offset lattice and finds (110, 110).
    # A dry point already has a valid offset cell and takes the direct return (not moved).
    assert g.landing(120, 100) == (130, 110, False)
    assert g.landing(80, 100, 'ground') == (100, 100, True)
    assert g.landing(80, 100) == (110, 110, True)
