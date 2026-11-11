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


def test_special_power_nugget_retail_painter_consumer():
    """engine_spnret a: retail modifier gates, SPN kept/removed, early/late HP."""
    import build
    import sim
    from checks.engine_spnret import VALUES
    m, t, _ = build.resolve('engine_spnret', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    result = e.run(16)
    assert tuple(result.series[-1][1]) == VALUES
    assert all(tuple(row) == VALUES for sec, row in result.series if sec >= 14)
    assert (sim.GAP_WEAPON, 'SpecialPowerNugget') not in e.unmodeled
    assert (sim.GAP_WEAPON, 'AttributeModifierNugget') not in e.unmodeled
    import simunits
    weapon = simunits._fight_data()['weapons']['AlliedAntiVehicleVehicleTech1TargetPainter']
    assert [(p['required_upgrade'], p['forbidden_upgrade']) for p in weapon['hit_modifiers']] == [
        ('', 'Upgrade_AlliedHighTechnology'), ('Upgrade_AlliedHighTechnology', '')]


def test_special_power_nugget_retail_active_consumer_is_not_silently_ignored():
    """A real active companion must remain a gap, unlike the commented retail beam."""
    import build
    import simunits
    m, _, _ = build.resolve('engine_spnret', 'a')
    caster = m.units[0]
    power = 'SpecialPower_PaintTargetTrigger'
    own = {caster.id: caster.xml}
    assert simunits.nugget_self_power(caster.id, power, own)['noop']
    own[caster.id] = caster.xml.replace('<Behaviors>', '<Behaviors>' +
        f'<BeamSpecialAbilityUpdate id="ActiveConsumer" SpecialPowerTemplate="{power}"/>', 1)
    assert simunits.nugget_self_power(caster.id, power, own) is False
    own[caster.id] = caster.xml
    own['BaseVehicle'] = ('<GameObject id="BaseVehicle"><Behaviors>' +
        f'<BeamSpecialAbilityUpdate id="InheritedConsumer" SpecialPowerTemplate="{power}"/>' +
        '</Behaviors></GameObject>')
    assert simunits.nugget_self_power(caster.id, power, own) is False


@pytest.mark.parametrize('inner', [
    '<RequiredUpgrade>A</RequiredUpgrade><ForbiddenUpgrade>B</ForbiddenUpgrade>',
    '<RequiredUpgrade id="unexpected">A</RequiredUpgrade>',
    '<SpecialObjectFilter Rule="ANY" Include="VEHICLE"/>',
])
def test_retail_attribute_gates_reject_unmeasured_forms(inner):
    import simunits
    xml = ('<WeaponTemplate id="GateTest"><Nuggets><AttributeModifierNugget '
           'AttributeModifierName="Paint">' + inner + '</AttributeModifierNugget></Nuggets></WeaponTemplate>')
    weapon = simunits._weapons([xml])['GateTest']
    assert not weapon.get('hit_modifiers')
    assert 'AttributeModifierNugget' in weapon['unmodeled_effects']


def test_special_power_nugget_retail_scrambler_unresolved_consumers_remain_gaps():
    """engine_spnscr a: measured fire-delay differs, final HP alone hides it.

    Isolated expiry clearing is covered separately. Attack-order retention
    and the active SPN consumer remain unresolved. Retail filter dispatch
    has a separate isolated interface test below.
    This is a gap guard, not a bench replay claim.
    """
    import build
    import sim
    import simunits
    from checks.engine_spnscr import POWER
    m, t, _ = build.resolve('engine_spnscr', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    e.run(16)
    assert (sim.GAP_WEAPON, 'SpecialPowerNugget') in e.unmodeled
    assert (sim.GAP_WEAPON, 'AttributeModifierNugget') not in e.unmodeled
    # FX_None and CANNOT_LEAVE_ENCLOSURE are not yet a validated no-op boundary.
    assert simunits.nugget_self_power(m.units[0].id, POWER, e.own) is False


@pytest.mark.parametrize('status_source', ['status', 'script_status'])
@pytest.mark.parametrize('kinds,template,status,allowed', [
    ({'VEHICLE'}, 'Target', set(), True),
    ({'SHIP'}, 'Target', set(), True),
    ({'AIRCRAFT'}, 'Target', set(), True),
    ({'FS_BASE_DEFENSE'}, 'Target', set(), True),
    ({'STRUCTURE'}, 'Target', set(), False),
    ({'VEHICLE', 'INFANTRY'}, 'Target', set(), False),
    ({'VEHICLE'}, 'Target', {'UNDER_IRON_CURTAIN'}, False),
    ({'VEHICLE'}, 'Target', {'IMMOBILE'}, True),
    ({'AIRCRAFT'}, 'JapanRisingBalloon', set(), False),
    ({'AIRCRAFT'}, 'japanfallingballoonbomb', set(), False),
    ({'AIRCRAFT'}, 'JapanBalloonBomb', set(), False),
])
def test_retail_scrambler_filter_dispatch(kinds, template, status, allowed, status_source):
    """Retail filter -> selected target -> timed modifier, no attack-order replay.

    Categories/template exclusion reuse Garrisons.fits; the status mask uses
    current object bits. Frame90 is supplied input, not measured collision.
    """
    import build
    import sim
    import simunits
    m, t, _ = build.resolve('engine_spnscr', 'a')
    e = sim.Sim(m, t)
    caster, victim = [e.body('SCR base ' + role) for role in ('caster', 'victim')]
    weapon = next(w for w in caster.weapons if w.get('hit_modifiers'))
    mid = weapon['hit_modifiers'][0]['modifier']
    victim.kinds, victim.template = kinds, template
    victim.status, victim.script_status = set(), set()
    setattr(victim, status_source, set(status))
    now = [90]
    e.frame_now = lambda: now[0]
    e.shots_due = lambda *_: 1
    e.firing, e.volleys = [], [(victim, weapon, caster)]
    e.deal(1 / 15)
    assert (mid in victim.auras_on) == allowed
    assert mid not in caster.auras_on
    if allowed:
        assert victim.auras_on[mid][0] == 105
        assert {'NO_ATTACK', 'SCRAMBLED'} <= victim.status
        now[0] = 104
        e.modify(victim)
        assert mid in victim.auras_on
        now[0] = 105
        e.modify(victim)
        assert mid not in victim.auras_on
        assert not {'NO_ATTACK', 'SCRAMBLED'} & victim.status


def test_retail_scrambler_filter_survives_retail_cache():
    import simunits
    w = simunits._fight_data()['weapons']['AlliedAntiAirShipWeaponScrambler']
    assert w['hit_modifiers'][0]['target_filter']['status_exclude'] == ['UNDER_IRON_CURTAIN']


@pytest.mark.parametrize('change', ['rule', 'relationship', 'child', 'gate', 'duplicate'])
def test_retail_scrambler_filter_unknown_combinations_remain_gaps(change):
    import simunits
    import re
    from checks.engine_spnscr import retail_parts
    nugget = re.search(r'<AttributeModifierNugget\b.*?</AttributeModifierNugget>', retail_parts()[1], re.S).group()
    if change == 'rule':
        nugget = nugget.replace('Rule="ANY"', 'Rule="ALL"')
    elif change == 'relationship':
        nugget = nugget.replace('Rule="ANY"', 'Rule="ANY" Relationship="ENEMIES"')
    elif change == 'child':
        nugget = nugget.replace('</SpecialObjectFilter>', '<IncludeThing>Other</IncludeThing></SpecialObjectFilter>')
    elif change == 'gate':
        nugget = nugget.replace('</AttributeModifierNugget>', '<RequiredUpgrade>Other</RequiredUpgrade></AttributeModifierNugget>')
    else:
        f = re.search(r'<SpecialObjectFilter\b.*?</SpecialObjectFilter>', nugget, re.S).group()
        nugget = nugget.replace('</AttributeModifierNugget>', f + '</AttributeModifierNugget>')
    w = simunits._weapons(['<WeaponTemplate id="Unknown"><Nuggets>' + nugget + '</Nuggets></WeaponTemplate>'])['Unknown']
    assert not w.get('hit_modifiers')
    assert 'AttributeModifierNugget' in w['unmodeled_effects']


@pytest.mark.parametrize('script_frame', [None, 0, 6.5 * 15 + 4])
def test_retail_scrambler_modifier_expiry_clears_script_status(script_frame):
    """Isolated expiry input, not engine_spnscr attack-order replay.

    Retail Duration=1s; use frame90 as supplied application time and105 as
    expiry. The old bench exposes only coarse HP snapshots, not exact impact
    or expiry frames. D40 establishes clearing semantics independently.
    """
    import build
    import sim
    import simunits
    m, t, _ = build.resolve('engine_spnscr', 'a')
    e = sim.Sim(m, t)
    b = e.body('SCR base victim')
    # Read the actual retail nugget's modifier rather than copying its bits.
    import re
    from checks.engine_spnscr import retail_parts
    mid = re.search(r'AttributeModifierName="([^"]+)"', retail_parts()[1]).group(1)
    modifier = simunits.modifier('', mid)
    assert modifier['frames'] == 15
    assert modifier['status'] == {'NO_ATTACK', 'SCRAMBLED'}
    now = [90]
    e.frame_now = lambda: now[0]
    b.script_status.clear()
    e.act('UNIT_CHANGE_OBJECT_STATUS', [b.name, 'IMMOBILE', 1], 'expiry interface')
    if script_frame == 0:
        e.act('UNIT_CHANGE_OBJECT_STATUS', [b.name, 'NO_ATTACK', 1], 'expiry interface')
    b.auras_on[mid] = (105, '')
    e.modify(b)
    assert modifier['status'] <= b.status
    if script_frame and script_frame > 0:
        now[0] = script_frame
        e.act('UNIT_CHANGE_OBJECT_STATUS', [b.name, 'NO_ATTACK', 1], 'expiry interface')
    now[0] = 104
    e.modify(b)
    assert modifier['status'] <= b.status
    now[0] = 105
    e.aura_tick()
    assert not modifier['status'] & b.status
    assert not modifier['status'] & b.script_status
    assert 'IMMOBILE' in b.status
    assert mid not in b.auras_on
    # A later script write must work: expiry is a one-time clear, not a mask.
    now[0] = 106
    e.act('UNIT_CHANGE_OBJECT_STATUS', [b.name, 'NO_ATTACK', 1], 'expiry interface')
    e.aura_tick()
    assert {'NO_ATTACK', 'IMMOBILE'} <= b.status
