"""Tracer audio (experimental/music/tracer.py): a sequence of streams (one replayed), resampled to 44.1 kHz and quietened like the
game would, decodes back to the same indices in order, with a blip at every stream start."""
import sys
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from experimental.music import tracer  # noqa: E402


def test_sequence_decodes():
    seq = [(0, 1500), (731, 2000), (412, 900), (412, 900), (88, 2472)]
    x = np.concatenate([tracer.stream(k, ms) for k, ms in seq]).astype(np.float64)
    y = resample_poly(x, 2, 1) * 0.2 + np.random.default_rng(0).normal(0, 30, len(x) * 2)
    runs, blips = tracer.decode(y, 44100)
    assert [k for _, _, k in runs] == [0, 731, 412, 412, 88]     # a replayed stream is a new run
    starts = np.cumsum([0] + [ms / 1000 for _, ms in seq[:-1]])
    assert len(blips) == len(seq)
    assert np.abs(np.array(blips) - starts).max() < 0.2
