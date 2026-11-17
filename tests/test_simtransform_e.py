"""E206: the player's Tengu power replays engine_acts_btn:all's state/arrival HUD.

See work/re/e206_transform.md. Only the Tengu script press is replaced by a
player order; VX and the unpressed Tengu remain the measured controls.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('simproxy_e206', ROOT / 'experimental/cnv/simproxy.py')
proxy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(proxy)
pytestmark = pytest.mark.skipif(not proxy.available(), reason='no private engine model')


def test_player_transform_as_the_bench(monkeypatch):
    import build
    resolve = build.resolve

    def player_press(name, check):
        m, t, extra = resolve(name, check)
        for script in t.scripts:
            script.do = [a for a in script.do if a != (
                'NAMED_USE_COMMANDBUTTON_ABILITY', 'UNIT - CNV A10 TT', 'Command_JAIV_Transform')]
        return m, t, extra

    monkeypatch.setattr(build, 'resolve', player_press)
    w = proxy.SimWorld('engine_acts_btn', 'all')
    s = w.sim
    tengu = s.body('UNIT - CNV A10 TT')
    control = s.body('UNIT - CNV A10 TP')
    vx = s.body('UNIT - CNV A10 VT')
    while 'TRANSFORMATION_TOGGLE_STATE' not in vx.status and s.t < 8:
        w.step(1)
    assert 'TRANSFORMATION_TOGGLE_STATE' in vx.status
    assert 'TRANSFORMATION_TOGGLE_STATE' not in tengu.status
    assert w.issue(w.pw.Order('power', (w._id(tengu),), power='SpecialPower_JAIV_Transform'))
    # INFERRED player reload gate, taken from XML, not claimed as a bench fact.
    assert not w.issue(w.pw.Order('power', (w._id(tengu),), power='SpecialPower_JAIV_Transform'))
    w.step(int((26 - s.t) * proxy.FPS))
    at = dict(s.series)
    for k in range(3, 23):
        assert at[k + 2][3] % 10 == 1, (k, at[k + 2])  # TT's measured state bit, not SH's unrelated exit clock
    for k, arrival in ((10, 1), (13, 111), (17, 1111)):
        assert at[k + 2][2] == arrival, (k, at[k + 2])
    first = {bit: min(t for t, v in s.series if v[2] // bit % 10) for bit in (1, 10, 100, 1000)}
    assert first[1] < first[100] <= first[10] < first[1000]
    assert 'TRANSFORMATION_TOGGLE_STATE' not in control.status
    # Reverse state is measured separately by engine_transform:b (59059),
    # but this player's late press/cooldown acceptance remains INFERRED.
    assert w.issue(w.pw.Order('power', (w._id(tengu),), power='SpecialPower_JAIV_Transform'))
    assert 'TRANSFORMATION_TOGGLE_STATE' not in tengu.status
    assert tengu.speed == control.speed
    # Wrong host must fail through the same player seam, without changing it.
    assert not w.issue(w.pw.Order('power', (w._id(vx),), power='SpecialPower_JAIV_Transform'))
    assert not w.issue(w.pw.Order('power', (w._id(control),), power='SpecialPower_JAIV_Transform', pos=(0, 0)))
    assert not w.issue(w.pw.Order('power', (w._id(control),), power='SpecialPower_JAIV_Transform', target=w._id(vx)))
    assert 'TRANSFORMATION_TOGGLE_STATE' not in control.status


def test_transform_gap_has_measured_player_route():
    spec = importlib.util.spec_from_file_location('coverage_e206', ROOT / 'experimental/cnv/simcoverage.py')
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    assert ('命令', '技能 SpecialPower_JAIV_Transform') not in sc.KNOWN
    inf = sc.info('j7')
    assert sc.simunits.power_rules('JapanAntiInfantryVehicle', 'SpecialPower_JAIV_Transform', inf.own)
    own = {'JapanAntiInfantryVehicle': '<GameObject id="JapanAntiInfantryVehicle" '
           'inheritFrom="JapanAntiInfantryVehicle" />'}
    assert sc.simunits.power_rules('JapanAntiInfantryVehicle', 'SpecialPower_JAIV_Transform', own)['reload'] == 225
    assert sc.power_modelled('SpecialPower_JAIV_Transform', inf)
    assert not any(item.name == '技能 SpecialPower_JAIV_Transform' for item in sc.command_items(inf))
