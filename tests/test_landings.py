"""Amphibious units must be able to go ashore (simstatic.landings). The banks of the platform maps are steep (22..35 a
cell, ground over 9 is impassable), so a Riptide leaves the water only where a slip (a Ramp) is cut; A5's draft (2026-11-04)
sent a Riptide with the beacon across a canal it could not land from -- found by the bench, not by any check. One finding
class (ADR 0015): every level's amphibians reach every dry site of the land that touches the water, or it is listed."""
import dataclasses
import types

import pytest
from test_plans import small  # (puts experimental/cnv on the path)  # noqa: F401, I001
import build  # noqa: E402
import parts  # noqa: E402
import sim  # noqa: E402
import simstatic  # noqa: E402

# what the levels do today (a name prefix of the finding's line): delete a line when it is fixed, never add one.
LEFT = ()


def found(level, ground=None):
    m, t, _ = build.resolve(level, '')
    return simstatic.landings(parts.merged(m, t), ground)


@pytest.mark.parametrize('level', build.LEVELS)
def test_every_levels_amphibians_can_go_ashore_or_the_level_is_listed(level):
    bad = [x for x in found(level) if not x.startswith(LEFT)]
    assert not bad, bad[:3]


@pytest.mark.parametrize('level', ['a5', 's5'])
def test_the_panama_slips_are_what_lets_the_riptide_land(level):
    """Mutation: the canal's two slips taken out, the Riptide (A5) / the Bullfrog's side (S5) cannot reach the east
    bank -- the rule names it."""
    from maps import panama
    assert found(level) == []
    no_slips = dataclasses.replace(panama.LAYOUT, ramps=[r for r in panama.LAYOUT.ramps if 'slip' not in r.what and
                                                        'beach' not in r.what])
    fake = types.SimpleNamespace(LAYOUT=no_slips, OBJECTS=panama.OBJECTS, SITES=panama.SITES)
    bad = found(level, sim.Ground(fake))
    assert any('east beach' in x or 'north bank' in x for x in bad), bad
