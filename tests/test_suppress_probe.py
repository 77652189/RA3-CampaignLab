"""Suppression contribution lifetime in whole frames: ceil(DurationSeconds x 15), not round.

Bench (engine line D rounds 21, 22, 33; ra3ext CNVProbe reads the manager's entries, +0x14 = frames left): a 3 s
contribution is born with 45 frames, 1.1 s with 17 (16.5), and engine_suppress_probe fraction's 1.95 s with 30
(29.25 -- rounding would give 29): the entry born at frame 92 reads 0x1e and is gone at frame 122
(run CampSPFraction_mcp_1110_224839, counters 59/59 PASS). The simulator stamps each hit with simunits._frames.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experimental' / 'cnv'))

import simunits  # noqa: E402
from checks import engine_suppression  # noqa: E402


def test_suppression_entries_live_ceil_of_their_seconds_in_frames():
    for seconds, frames in ((3, 45), (1.1, 17), (1.95, 30), (2, 30), (1, 15)):
        assert simunits._frames(seconds) == frames


def test_the_fraction_lane_is_the_one_that_tells_ceil_from_round():
    lanes = engine_suppression.cases_for('fraction')
    assert lanes['order'][2] == lanes['removed'][2] == 1.95
    assert round(1.95 * 15) == 29 and simunits._frames(1.95) == 30
