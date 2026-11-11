"""SpecialPowerNugget gate replay; import the same simulator harness as line C."""
import importlib.util
from pathlib import Path
import pytest

_spec = importlib.util.spec_from_file_location('simbench_spng', Path(__file__).resolve().parents[1] /
                                             'experimental/cnv/simbench.py')
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)


@pytest.mark.parametrize('mission,expected', [
    ('engine_spng', (1011099075, 1011099080, 1011099080, 1011099075)),
    ('engine_spn', (1001099080, 1001099075, 1001099080, 1001099080)),
])
def test_special_power_nugget_upgrade_gates_use_caster_not_victim(mission, expected):
    """engine_spng a: required/forbidden x caster/victim, plus grant proof."""
    import build
    import sim
    m, t, _ = build.resolve(mission, 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    result = e.run(16)
    assert tuple(result.series[-1][1]) == expected
    assert all(tuple(row) == expected for sec, row in result.series if sec >= 14)
    assert (sim.GAP_WEAPON, 'SpecialPowerNugget') not in e.unmodeled


@pytest.mark.parametrize('inner', [
    '<RequiredUpgrade>A</RequiredUpgrade><RequiredUpgrade>B</RequiredUpgrade>',
    '<RequiredUpgrade>A</RequiredUpgrade><ForbiddenUpgrade>B</ForbiddenUpgrade>',
    '<RequiredUpgrade id="unexpected">A</RequiredUpgrade>',
])
def test_special_power_nugget_upgrade_gates_reject_unmeasured_forms(inner):
    import simunits
    xml = ('<WeaponTemplate id="GateTest"><Nuggets><SpecialPowerNugget '
           'SpecialPowerTemplate="Power">' + inner + '</SpecialPowerNugget></Nuggets></WeaponTemplate>')
    w = simunits._weapons([xml])['GateTest']
    assert not w.get('special_powers')
    assert 'SpecialPowerNugget' in w['unmodeled_effects']


def test_special_power_nugget_player_upgrade_gates_use_caster_owner():
    """engine_spngp a: PLAYER grants, distinct templates and status proof per lane."""
    import build
    import sim
    m, t, _ = build.resolve('engine_spngp', 'a')
    grants = next(s.do for s in t.scripts if s.name == 'Test - grant upgrades')
    assert len({a[2] for a in grants}) == 4
    assert all(a[0] == 'GIVE_PLAYER_UPGRADE' for a in grants)
    e = sim.Sim(m, t)
    e.shot_clock = True
    result = e.run(16)
    expected = (1011099075, 1011099080, 1011099080, 1011099075)
    assert all(tuple(row) == expected for sec, row in result.series if sec >= 14)
    assert tuple(result.series[-1][1]) == expected
    assert (sim.GAP_WEAPON, 'SpecialPowerNugget') not in e.unmodeled
    from checks.engine_spng import UPGRADE
    for lane in ('base', 'high', 'order', 'removed'):
        caster, victim = [e.body('SPN ' + lane + ' ' + role) for role in ('caster', 'victim')]
        owner = caster.owner if lane in ('base', 'order') else victim.owner
        assert UPGRADE + lane.title() in e.player_ups[owner]
        assert not caster.upgrades and not victim.upgrades
        receiver, other = (caster, victim) if lane in ('base', 'order') else (victim, caster)
        assert 'WEAPON_UPGRADED_01' in receiver.status
        assert 'WEAPON_UPGRADED_01' not in other.status


@pytest.mark.parametrize('mode,expected', [
    ('object_grant', (1011099080, 1011099080, 1011099075, 1011099075)),
    ('unknown_type', (1011099080,)*4),
])
def test_special_power_nugget_player_gate_does_not_accept_object_or_unknown(mode, expected):
    """Synthetic guards: object grants cannot substitute for PLAYER ownership."""
    import build
    import sim
    import re
    from checks.engine_spng import UPGRADE
    m, t, _ = build.resolve('engine_spngp', 'a')
    grant = next(s for s in t.scripts if s.name == 'Test - grant upgrades')
    grant.do = [('NAMED_RECEIVE_UPGRADE', UPGRADE + lane.title(),
                 'SPN ' + lane + (' caster' if lane in ('base', 'order') else ' victim'))
                for lane in ('base', 'high', 'order', 'removed')]
    if mode == 'unknown_type':
        for u in m.units:
            u.xml = re.sub(r'<(RequiredUpgrade|ForbiddenUpgrade)>[^<]+</',
                           r'<\1>Upgrade_CNVUnknown</', u.xml)
    e = sim.Sim(m, t)
    e.shot_clock = True
    result = e.run(16)
    assert tuple(result.series[-1][1]) == expected
    assert ((sim.GAP_WEAPON, 'SpecialPowerNugget') in e.unmodeled) == (mode == 'unknown_type')


def test_special_power_nugget_upgrade_gates_survive_retail_cache():
    import simunits
    weapon = simunits._fight_data()['weapons']['AlliedAntiVehicleVehicleTech1TargetPainter']
    assert [(p['required_upgrade'], p['forbidden_upgrade']) for p in weapon['special_powers']] == [
        ('', 'Upgrade_AlliedHighTechnology'), ('Upgrade_AlliedHighTechnology', '')]
