"""Lift timing from D50; historical engine_lift counters remain the oracle."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location('simbench_lift', Path(__file__).resolve().parents[1] /
                                             'experimental/cnv/simbench.py')
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)


@pytest.mark.parametrize('check,expected', [
    ('a', (1099, 11001099, 11001099, 1099)),
    pytest.param('landing', (1099, 10001099, 10001099, 1099),
                 marks=pytest.mark.xfail(strict=True, reason='D52 SoftLanding self-hit/expiry requires a Lift ground-contact event; no per-frame height/contact evidence or Lift trajectory exists. See work/re/c_lift_landing_gate_report.md and work/re/handoff-c.md')),
])
def test_lift_historical_bench_counters(check, expected):
    import build
    import sim
    m, t, _ = build.resolve('engine_lift', check)
    e = sim.Sim(m, t)
    e.shot_clock = True
    assert tuple(e.run(22).series[-1][1]) == expected
    assert not e.lift_timers.remaining
    assert (sim.GAP_WEAPON, 'ActivateLiftObjectNugget') in e.unmodeled  # falling still absent


def test_lift_timer_truncation_renewal_cap_and_caster_ownership():
    import simunits
    own = {'Caster': '<GameObject id="Caster"><LiftObjectUpdate TimeIncrement="0.5s" MaxTimeLifted="8s"/></GameObject>'}
    rule = simunits.lift_module('Caster', own)
    assert rule == dict(increment=7, maximum=120)
    timers = simunits.LiftTimers()
    timers.hit('one', 'victim', **rule)
    assert timers.remaining == {('one', 'victim'): 7}
    for _ in range(3):
        assert timers.tick() == []
    timers.hit('one', 'victim', **rule)
    assert timers.remaining[('one', 'victim')] == 11
    for _ in range(20):
        timers.hit('one', 'victim', **rule)
    assert timers.remaining[('one', 'victim')] == 120
    timers.hit('two', 'victim', **rule)
    for _ in range(7):
        assert timers.tick() == []
    assert timers.remaining[('two', 'victim')] == 0
    assert timers.tick() == [('two', 'victim')]
    assert timers.remaining[('one', 'victim')] == 112
    # New entries are not clamped; only renewal uses MaxTimeLifted.
    timers.hit('new', 'victim', 7, 3)
    assert timers.remaining[('new', 'victim')] == 7
    timers.hit('new', 'victim', 7, 3)
    assert timers.remaining[('new', 'victim')] == 3


def test_lift_hit_enters_caster_ledger_and_release_keeps_status():
    import build
    import sim
    m, t, _ = build.resolve('engine_lift', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    e.run(6.2)
    assert set(e.lift_timers.remaining) == {
        ('Lift high gun', 'Lift high victim'), ('Lift order gun', 'Lift order victim')}
    assert set(e.lift_timers.remaining.values()) <= set(range(1, 8))
    e.run(8)
    assert not e.lift_timers.remaining
    for lane in ('base', 'high', 'order', 'removed'):
        victim = e.body('Lift ' + lane + ' victim')
        e.modify(victim)  # unrelated modifier recomputation must not erase the lift-owned bit
        assert ('LIFTED_INTO_AIR' in victim.status) == (lane in ('high', 'order'))


@pytest.mark.parametrize('nugget', [
    '<ActivateLiftObjectNugget/>',
    '<ActivateLiftObjectNugget Lifetime="0.2s"><SpecialObjectFilter Rule="ANY" '
    'Include="VEHICLE"/></ActivateLiftObjectNugget>',
])
def test_lift_dispatch_survives_inheritance_and_warhead(nugget):
    import simunits
    xml = ('<WeaponTemplate id="LiftBase"><Nuggets>' + nugget + '</Nuggets></WeaponTemplate>'
           '<WeaponTemplate id="LiftChild" inheritFrom="LiftBase"/>'
           '<WeaponTemplate id="LiftShot"><Nuggets><ProjectileNugget '
           'WarheadTemplate="LiftChild"/></Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    for name in ('LiftBase', 'LiftChild', 'LiftShot'):
        resolved = simunits._resolve(weapons[name], weapons)
        assert len(resolved['lift']) == 1
        assert 'ActivateLiftObjectNugget' not in resolved['unmodeled_effects']


def test_lift_unsupported_filter_stays_a_gap():
    import simunits
    weapons = simunits._weapons(['<WeaponTemplate id="Lift"><Nuggets>'
        '<ActivateLiftObjectNugget><SpecialObjectFilter Rule="ALL" Include="VEHICLE"/>'
        '</ActivateLiftObjectNugget></Nuggets></WeaponTemplate>'])
    assert weapons['Lift']['unmodeled_effects'] == ['ActivateLiftObjectNugget']
    assert not weapons['Lift'].get('lift')


@pytest.mark.parametrize('excluded', [False, True])
def test_lift_zero_damage_dispatch_and_filter(excluded):
    import build
    import sim
    m, t, _ = build.resolve('engine_lift', 'a')
    for u in m.units:
        if 'ActivateLiftObjectNugget' in u.xml:
            u.xml = u.xml.replace('Damage="10"', 'Damage="0"')
            if excluded:
                u.xml = u.xml.replace('Include="VEHICLE"', 'Include="VEHICLE" Exclude="VEHICLE"')
    e = sim.Sim(m, t)
    e.shot_clock = True
    e.run(8)
    for lane in ('high', 'order'):
        victim = e.body('Lift ' + lane + ' victim')
        assert victim.hp == victim.max_hp
        assert ('LIFTED_INTO_AIR' in victim.status) == (not excluded)
