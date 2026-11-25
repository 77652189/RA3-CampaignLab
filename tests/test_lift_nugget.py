"""Lift timing from D50; the engine_lift / engine_liftground / engine_liftair readings: checks/engine_lift.readings.toml."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location('simbench_lift', Path(__file__).resolve().parents[1] /
                                             'experimental/cnv/simbench.py')
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)


def test_lift_timer_truncation_renewal_cap_and_caster_ownership():
    import engine.data.units as simunits
    own = {'Caster': '<GameObject id="Caster"><LiftObjectUpdate TimeIncrement="0.5s" MaxTimeLifted="8s"/></GameObject>'}
    rule = simunits.lift_module('Caster', own)
    assert rule == dict(increment=7, maximum=120, rise=0.0, top=0.0, soft=False)
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


def test_a_soft_landing_from_28_clears_the_bit_28_frames_after_the_hit_and_one_from_40_never():
    """engine_lift_probe: 7 frames up at 4 a frame (28), released, 20 frames falling: cleared at hit + 28; 10 frames
    (40 up) keeps it."""
    import engine.data.units as simunits
    timers = simunits.LiftTimers()
    timers.hit('c', 'low', 7, 120, rise=4.0, top=60.0, soft=True, serial=1)
    timers.hit('c', 'high', 10, 120, rise=4.0, top=60.0, soft=True, serial=2)
    landed = {}
    for frame in range(1, 60):
        timers.tick(lambda serial, z: 20)               # the probe's spot: 20 frames from 28
        landed.update({s: frame for s in timers.landed})
    assert landed == {1: 28}


@pytest.mark.parametrize('nugget', [
    '<ActivateLiftObjectNugget/>',
    '<ActivateLiftObjectNugget Lifetime="0.2s"><SpecialObjectFilter Rule="ANY" '
    'Include="VEHICLE"/></ActivateLiftObjectNugget>',
])
def test_lift_dispatch_survives_inheritance_and_warhead(nugget):
    import engine.data.units as simunits
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
    import engine.data.units as simunits
    weapons = simunits._weapons(['<WeaponTemplate id="Lift"><Nuggets>'
        '<ActivateLiftObjectNugget><SpecialObjectFilter Rule="ALL" Include="VEHICLE"/>'
        '</ActivateLiftObjectNugget></Nuggets></WeaponTemplate>'])
    assert weapons['Lift']['unmodeled_effects'] == ['ActivateLiftObjectNugget']
    assert not weapons['Lift'].get('lift')


def test_lift_retail_closure_keeps_all_six_consumers_unmeasured():
    """Synthetic VEHICLE snapshots cover no complete native Lift consumer."""
    import inventory
    import retailmodules as rm

    if not Path(rm.SAGEXML).is_dir():
        pytest.skip('requires retail XML')
    ground = {'JapanCommandoTech1PsyonicCrush',
              'AAAVT1_JapanCommandoTech1PsyonicCrush',
              'ABD_JapanCommandoTech1PsyonicCrush'}
    air = {'JapanCommandoTech1AirborneKiller',
           'AAAVT1_JapanCommandoTech1PsyonicAntiAirCrush',
           'ABD_JapanCommandoTech1PsyonicAntiAirCrush'}
    observed_consumers = set()  # engine_lift uses synthetic guns, not these hosts.
    residual = ground | air
    st = rm._load()
    actual = set()
    for key, (name, _, _) in st['weapons'].items():
        forms = [n for n in rm.effective_weapon_forms(key, st)
                 if rm._tag(n) == 'ActivateLiftObjectNugget']
        if not forms:
            continue
        actual.add(name)
        assert len(forms) == 1
        nugget = forms[0]
        assert nugget.get('Lifetime') == ('0.2s' if name in ground else '5.0s')
        filt, = list(nugget)
        assert rm._tag(filt) == 'SpecialObjectFilter'
        assert filt.get('Rule') == 'ANY'
        assert set(filt.get('StatusBitFlagsExclude').split()) == {
            'UNCONTROLLABLY_SCARED', 'UNDER_IRON_CURTAIN'}
        assert {n.text.strip() for n in filt if rm._tag(n) == 'ExcludeThing'} == {
            'AlliedWallPiece', 'SovietWallPiece', 'JapanWallPiece'}
        assert set(filt.get('Include').split()) == {
            'INFANTRY', 'VEHICLE', 'STRUCTURE', 'VALID_TARGET_FOR_C4',
            'TIME_BOMB' if name in ground else 'TRANSFORMER'}
    assert not ground & air
    assert not observed_consumers & residual
    assert observed_consumers | residual == actual
    assert len(observed_consumers) + len(residual) == rm.weapon_census()[
        'ActivateLiftObjectNugget']['weapons'] == 6
    rows = [i for i in inventory.apply_registers(inventory.nugget_items())
            if i['name'].split(':')[0] == 'ActivateLiftObjectNugget']
    assert sum(i['uses'] for i in rows) == 6
    assert all(i['state'] in (inventory.GUESSED, inventory.TODO) for i in rows)
