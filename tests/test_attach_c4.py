"""Native Tanya C4 replay; raw evidence: work/re/c_attachc4_report.md."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location('simbench_attachc4', Path(__file__).resolve().parents[1] /
                                             'experimental/cnv/simbench.py')
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)


def test_native_c4_controls_preserve_host_and_only_delete_nugget():
    """A missing AttachModuleId crashes the engine; keep all native providers."""
    import re
    import xml.etree.ElementTree as ET
    import build
    from benches.weapon.impact.checks import engine_attachc4
    LANES = engine_attachc4()["shared"].LANES
    from benches.weapon.firing.checks import engine_missile
    SAGE = engine_missile()["shared"].SAGE

    m, _, _ = build.resolve('engine_attachc4', 'a')
    original = ET.parse(Path(SAGE) / 'Allied/Units/AlliedCommandoTech1.xml').getroot()
    def nodes(root, tag):
        return [e for e in root.iter() if e.tag.rsplit('}', 1)[-1] == tag]
    original_module, = nodes(original, 'AttachUpdate')
    for lane in LANES:
        unit = next(u for u in m.units if u.id == 'CNV_AttC4' + lane.title())
        root = ET.fromstring(unit.xml)
        module, = nodes(root, 'AttachUpdate')
        assert ET.tostring(module) == ET.tostring(original_module)
        weapon, = [e for e in nodes(root, 'WeaponTemplate') if e.attrib['id'] == 'CNV_AttC4Gun' + lane.title()]
        nuggets = nodes(weapon, 'AttachNugget')
        assert len(nuggets) == (0 if lane in ('high', 'removed') else 1)
        if nuggets:
            assert nuggets[0].attrib['AttachModuleId'] == module.attrib['id']
        assert len(re.findall('Template="AlliedCommandoDetonationWeapon"', unit.xml)) == 1


@pytest.mark.parametrize('check', ['a', 'b'])
def test_native_c4_deleted_nugget_matches_bench(check):
    import build
    import sim
    m, t, _ = build.resolve('engine_attachc4', check)
    e = sim.Sim(m, t)
    e.shot_clock = True
    rows = e.run(24).series
    assert (rows[-1][1][1], rows[-1][1][3]) == (10024, 10028)


@pytest.mark.parametrize('check,observed', [('a', (11, 10030)), ('b', (11, 15))])
@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='Native C4 attachment/parent status/detonation consumer is not implemented; '
                          'see work/re/c_attachc4_report.md and handoff-c.md')
def test_native_c4_attachment_and_parent_gate_match_bench(check, observed):
    import build
    import sim
    m, t, _ = build.resolve('engine_attachc4', check)
    e = sim.Sim(m, t)
    e.shot_clock = True
    rows = e.run(24).series
    assert (rows[-1][1][0], rows[-1][1][2]) == observed
