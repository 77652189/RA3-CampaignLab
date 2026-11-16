"""C SellButton probe: native observations and explicitly limited script replay.

UI input/state is not silently replaced by SELL_OBJECT. Scope and any remaining
gap: work/re/c_mousehud_report.md. No whole-action coverage claim.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('mousehud_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _evidence(variant):
    import labpaths
    path = Path(labpaths.WORK) / 're/c_mousehud_measured.json'
    if not path.exists():
        pytest.skip('private original native mouse HUD archive unavailable')
    return json.loads(path.read_text(encoding='utf-8'))[variant]


@pytest.mark.parametrize('variant', ['a', 'b'])
def test_mousehud_failed_activation_baseline_replay(variant):
    """Replay all three actual stable counters; neither native attempt sold a plant.

    This baseline does not establish the UI gate. The simulator has no bench
    mouse-event consumer; its matching negative result must not promote the action.
    """
    import build
    import sim
    evidence = _evidence(variant)
    expected = {row['values'][2]: row['values'] for row in evidence['rows']
                if row['values'][2] >= 84}
    assert expected
    m, t, _ = build.resolve('engine_mousehud', variant)
    assert [label for _, label in t.counters] == ['存活', '资金', '逻辑帧']
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.produce_due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.produce_due = observe
    e.advance(max(expected) + 1)
    assert got == expected
    assert all(v[:2] == [5, 2400] for v in expected.values())


@pytest.mark.parametrize('variant,frame', [('a', 356), ('b', 414)])
def test_mousehud_native_observation_archive(variant, frame):
    """Anchor the named original negative outcome, without claiming activation."""
    evidence = _evidence(variant)
    assert evidence['run'].startswith(f'CampMouseHUD{variant.upper()}_mcp_')
    assert evidence['rows'][-1]['values'] == [5, 2400, frame]
    assert 'bench_click: left click at screen (1126, 222)' in evidence['output']
    assert 'bench_click: left click at screen (723, 393)' in evidence['output']


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'engine_mousehud:b restores SellButton but the native attempt only selects the '
    'plant: f414 alive/money=5/2400, predicted 4/2800. Native sale-mode acceptance '
    'is unobserved; per-call Esc may cancel the mode (INFERRED). This is a native '
    'positive-control gap, not a fitted model rule; see work/re/c_mousehud_report.md.'))
def test_mousehud_restored_native_sale_positive_control():
    """Keep the original positive prediction red until a genuine sale is observed."""
    rows = _evidence('b')['rows']
    assert any(row['values'][:2] == [4, 2800] for row in rows)
