"""C condition probe: replay observed buildings and physical controls.

Evidence and unresolved boundaries: work/re/c_pathbanks_report.md.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.fixture(scope='module', params=['aipcland', 'aipcamph', 'aipclandy'])
def path_rows(request):
    w = simai.run(request.param, 'a', 45, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    return {t: dict(zip(labels, values)) for t, values in w.sim.series}


def test_path_condition_disconnected_banks(path_rows):
    """Bank probes choose barracks=1/power=0 at s22-24: D108 and the early-registration follow-up observe a
    pre-wake nobase return. B round 217: the simulator's opening draw now answers "cannot judge" too
    (simai.Brain.path_to_target); amphibious reachability remains unproven (work/re/c_pathready_report.md)."""
    rows = path_rows
    assert all((rows[t]['兵营'], rows[t]['电厂']) == (1, 0)
               for t in (22, 23, 24)), {t: rows[t] for t in (22, 23, 24)}


def test_path_condition_controls_observed(path_rows):
    """Both survived without reaching the goal; this is not a reachability proof."""
    rows = path_rows
    assert all((rows[t]['陆路'], rows[t]['两栖']) == (1, 1)
               for t in (40, 41, 42, 43, 44)), {t: rows[t] for t in (40, 41, 42, 43, 44)}
