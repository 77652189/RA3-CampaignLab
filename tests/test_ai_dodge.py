"""Native-beacon DodgeThreats contrast; bounded single-threat consumer; exact timing remains a gap."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)


def test_micro_dodge_fixture_changes_only_the_switch():
    import build
    from contract import contract
    from model import merged

    views = []
    for name, enabled in (('aidodgeon', 'true'), ('aidodgeoff', 'false')):
        m, t, _ = build.resolve(name, 'r')
        assert contract(merged(m, t)) == []
        xml = ET.fromstring(m.assets[0][1])
        micro = next(e for e in xml.iter() if e.tag.endswith('}AIMicroManagerData'))
        assert micro.attrib.pop('DodgeThreats') == enabled
        assert micro.get('DodgeThreatsReactionTimeMin') == '0.5s'
        assert micro.get('DodgeThreatsReactionTimeMax') == '0.5s'
        assert micro.get('UseSpecialPowers') == 'false'
        assert micro.get('PullbackInjured') == 'false'
        views.append((ET.tostring(xml), m.objects, m.scripts, m.waypoints))
    assert views[0] == views[1]


@pytest.fixture(scope='module')
def dodge_replay(request):
    if not simai.available():
        pytest.skip('no ra3model.ai (labpaths.ENGINE_MODEL)')
    return simai.run(request.param, 'r', until=36.0)


@pytest.mark.parametrize('dodge_replay', ['aidodgeon', 'aidodgeoff'], indirect=True)
def test_micro_dodge_replay_has_living_members_and_named_threat(dodge_replay):
    # Keep prerequisites separate from the movement observation.
    # Align by the displayed game-frame counter, not capture wall seconds.
    series = dodge_replay.sim.series
    before = [values for _, values in series if 27 * simai.FPS <= values[0] < 29 * simai.FPS]
    assert before and all(values[1:] == [2, 2, 0] for values in before), before
    rows = [values for _, values in series if 31 * simai.FPS <= values[0] < 34 * simai.FPS]
    assert rows and all(values[1] == 2 for values in rows), rows
    assert any(values[3] == 1 for values in rows), rows


@pytest.mark.parametrize('dodge_replay,limit', [
    ('aidodgeon', 1),
    ('aidodgeoff', 2),
], indirect=['dodge_replay'])
def test_micro_dodge_replays_named_beacon_observation(dodge_replay, limit):
    # Native on: f468 [2,1,1], f479..509 [2,0,1]; off: f456..501 [2,2,1].
    # work/re/c_dodge_logs/aidodge{on,off}__r.json. This proves movement in the
    # threat's presence, not an exact reaction clock, member filter or safety circle.
    rows = [values for _, values in dodge_replay.sim.series
            if 31 * simai.FPS <= values[0] < 34 * simai.FPS and values[3] == 1]
    assert rows, 'named threat must be present in the movement observation'
    assert all(values[1] == 2 for values in rows), rows
    near = [values[2] for values in rows]
    if limit == 1:
        assert min(near) <= limit, rows
    else:
        assert set(near) == {limit}, rows


@pytest.mark.parametrize('dodge_replay', ['aidodgeon', 'aidodgeoff'], indirect=True)
def test_micro_dodge_replay_expires_the_native_threat(dodge_replay):
    # Retail beacon lifetime is 4s. This checks eventual cleanup, not its exact frame.
    beacon = dodge_replay.sim.body('CNV Dodge Beacon')
    assert beacon is not None and not beacon.alive
    managers = [m for b in dodge_replay.brains.values() if hasattr(b, 'micro')
                for m in b.micro.managers.values()]
    assert managers and all(not m.dodging for m in managers)
