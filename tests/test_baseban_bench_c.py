"""C-line base construction controls; observed scope and gaps: work/re/c_baseban_report.md."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('baseban_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('variant,first,last', [('a', 74, 488), ('b', 75, 364)])
def test_baseban_native_core_final_readings(variant, first, last):
    """A: disabled human click and normal scripted press both finish at 1200/1200/11.

    The native click fell between measured frames 74 and 488. Inject its production order
    inside that interval; do not claim the exact click frame or production curve is known.
    This control establishes no base-construction gate and must not promote the action.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_baseban', variant)
    e = sim.Sim(m, t, script='不打')
    e.advance(first)
    assert e.order_build(m.player('p1'), 'JapanPowerPlantEgg')
    e.advance(last - first)
    assert [e.counters.get(k, 0) for k in (
        'CNV_BaseBan_p1', 'CNV_BaseBan_s5', 'CNV_BaseBan_Cores')] == [1200, 1200, 11]


@pytest.mark.xfail(strict=True, reason=(
    'engine_baseban:a/b at logic frame 74/75: scripted Japan core still paying, '
    'money 1426/1413 and cores 0; Sim consumes BuildTime 0 instantly. Native queue timing and '
    'the base-construction consumer remain gaps; see work/re/c_baseban_report.md.'))
@pytest.mark.parametrize('variant,frame,money', [('a', 74, 1426), ('b', 75, 1413)])
def test_baseban_scripted_core_measured_payment_frame(variant, frame, money):
    """Freeze actual frame/money/core tuple, without replacing it by the model's instant queue."""
    import build
    import sim
    m, t, _ = build.resolve('engine_baseban', variant)
    e = sim.Sim(m, t, script='不打')
    e.advance(frame)
    assert [e.counters.get(k, 0) for k in (
        'CNV_BaseBan_p1', 'CNV_BaseBan_s5', 'CNV_BaseBan_Cores', 'CNV_BaseBan_Clock')
    ] == [2000, money, 0, frame]
