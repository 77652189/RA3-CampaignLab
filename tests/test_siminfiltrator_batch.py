"""E148 named multi-lane replay; unimplemented effects retain explicit gaps."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_infbatch', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_infiltrator_batch_retail_configuration():
    import build
    import siminfiltrator
    m, t, mod = build.resolve('engine_infbatch', 'a')
    assert len(mod) <= 15 and '_' not in mod
    assert len(t.counters) == 4
    for lane, kind in (('air', 'Aircraft'), ('infantry', 'Infantry'), ('ship', 'Ship')):
        rule = siminfiltrator.spec(m.role(lane).template)
        assert (rule['Effect'], rule['Duration'], rule['UnitDuration'], rule['ObjectRef']) == (
            'VISION_UNITS', '30s', '30s', 'UnitVisionObserver')
        assert rule['UnitFilter'] == 'Infiltration' + kind + 'ObjectFilter'
        assert rule['StructureFilter'] == 'Infiltration' + kind + 'StructuresFilter'
    port = siminfiltrator.spec(m.role('port').template)
    assert (port['Effect'], port['Duration'], port['BlockedDuration'], port['ObjectRef']) == (
        'VISION', '-1s', '9999999s', 'VisionObserver')


def test_infiltrator_batch_requires_real_retail_markers():
    import build
    import simunits
    m, _, _ = build.resolve('engine_infbatch', 'a')
    missing = [obj.template for obj in m.objects if not simunits.retail_xml(obj.template)]
    assert not missing, missing
    import re
    for lane, kind in (('air', 'AIRCRAFT'), ('infantry', 'INFANTRY'), ('ship', 'SHIP')):
        xml = simunits.retail_xml(m.role(lane + ' match').template)
        kinds = re.search(r'KindOf="([^"]+)"', xml).group(1).split()
        assert kind in kinds
    port, near, far = (m.point(role) for role in ('port', 'port match', 'port wrong'))
    assert (near[0] - port[0])**2 + (near[1] - port[1])**2 < 600**2
    assert (far[0] - port[0])**2 + (far[1] - port[1])**2 > 600**2
    _, t, _ = build.resolve('engine_infbatch', 'a')
    assert [item[3] for item in t.expect] == [200111, 200111, 200111, 1200111]


def test_infiltrator_batch_independent_prerequisite_bits():
    """Every single failed original predicate remains identifiable in variant b."""
    import build
    from parts import NOT, square
    m, original, _ = build.resolve('engine_infbatch', 'a')
    _, diagnostic, mod = build.resolve('engine_infbatch', 'b')
    assert len(mod) <= 15 and '_' not in mod
    assert 'contract: ok' in build.show('engine_infbatch', 'b').lower()
    assert diagnostic.scripts[:3] == original.scripts[:3]
    assert diagnostic.areas == original.areas
    assert [item[3] for item in original.expect] == [200111, 200111, 200111, 1200111]
    assert [item[3] for item in diagnostic.expect] == [33554431] * 4
    for lane in ('air', 'infantry', 'ship', 'port'):
        gate = next(s.when for s in original.scripts if s.name == 'Test - prerequisites ' + lane)
        bits = [s for s in diagnostic.scripts if s.name.startswith('Test - ' + lane + ' bit ')]
        assert len(bits) == len(gate) == 25
        assert [s.when for s in bits] == [[condition] for condition in gate]
        assert gate[0] == ('TIMER_EXPIRED', 'Entry', NOT)
        for index, suffix in enumerate(('', ' friend', ' spy', ' friend spy', ' match', ' wrong', ' third')):
            role = lane + suffix
            obj = m.role(role)
            area = 'Test identity ' + role
            assert gate[1 + 3*index:4 + 3*index] == [
                ('NAMED_NOT_DESTROYED', obj.name),
                ('NAMED_OWNED_BY_PLAYER', m.player(obj.side), obj.name),
                ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA',
                 m.player(obj.side), 3, 1, obj.template, area)]
            assert diagnostic.areas[area] == square(*m.point(role), 40)
        assert gate[-3:] == [('NAMED_DISCOVERED', m.player('p1'),
                             m.role(lane + ' ' + role).name, NOT)
                            for role in ('match', 'wrong', 'third')]
        weights = [s.do[0][1] for s in bits]
        assert weights == [2**i for i in range(25)]
        assert all(not s.once and s.do[0][2] == 'Prerequisites ' + lane for s in bits)
        # Exercise the compiled single-condition counter actions under each
        # possible one-predicate failure, independent of simulated unit rules.
        for failed in range(25):
            reading = sum(s.do[0][1] for i, s in enumerate(bits) if i != failed)
            assert 33554431 ^ reading == 2**failed


@pytest.mark.xfail(strict=True, reason='E149步兵/舰船身份位置门未过、港口首入前已发现标记；'
                   '前置不等价且效果未闭合，不登记覆盖；见work/re/handoff-e.md和work/re/e149_infiltrator.md')
def test_infiltrator_batch_diagnostic_as_on_the_bench():
    """Replay actual E149 diagnostic readings; failed gates forbid effect claims."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infbatch', 'a')
    s = sim.Sim(m, t).run(45)
    # Keep the failed real prerequisites, rather than changing their expectations.
    rows = [values for second, values in s.series if 1 <= second <= 7]
    assert rows and all(row == [200111, 111, 111, 1001111] for row in rows), rows
    rows = [values for second, values in s.series if 39 <= second <= 45]
    assert rows and all(row == [111110, 110, 1110, 1101110] for row in rows), rows
