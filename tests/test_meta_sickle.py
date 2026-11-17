"""Real retail Sickle landing evidence; see work/re/c_sickle_report.md."""
import importlib.util
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('sickle_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_meta_sickle_controls_preserve_real_leap_and_only_remove_meta():
    import build
    from checks import engine_knock_sickle as s

    a, ta, _ = build.resolve('engine_knock_sickle', 'a')
    b, tb, _ = build.resolve('engine_knock_sickle', 'b')
    ua, ub = (next(u for u in m.units if u.id == s.UID) for m in (a, b))
    assert re.sub(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', '', ua.xml, flags=re.S) == ub.xml
    assert 'GroundHitWeapon="' + s.WEAPON + '"' in ua.xml
    assert 'SpecialWeapon="SovietAntiInfantryVehicleLeapWeapon"' in ua.xml
    assert 'KindOf="SELECTABLE CAN_ATTACK CAN_CAST_REFLECTIONS SCORE VEHICLE CAN_BE_FAVORITE_UNIT"' in ua.xml
    assert len(ta.counters) == len(tb.counters) == 4
    for lane in s.LANES:
        assert a.point(lane) == b.point(lane)
        enemy = next(o for o in a.objects if o.name == s.name(lane, 'enemy'))
        friend = next(o for o in a.objects if o.name == s.name(lane, 'friend'))
        assert enemy.side == 's1' and friend.side == 'p1'
        assert (enemy.x - friend.x, enemy.y - friend.y) == (80, 0)
        assert enemy.template == friend.template == s.PROBE


def test_meta_sickle_cease_fire_controls_preserve_damage_and_repeat_after_leap():
    import build
    from checks import engine_knock_sickle as s

    for baseline, held in [('a', 'c'), ('b', 'd')]:
        old, _, _ = build.resolve('engine_knock_sickle', baseline)
        m, t, _ = build.resolve('engine_knock_sickle', held)
        assert [u.xml for u in old.units] == [u.xml for u in m.units]
        assert old.objects == m.objects
        hold = next(x for x in t.scripts if x.name == 'Test - hold fire')
        assert not hold.once
        assert hold.when == [('TIMER_EXPIRED', 'Sickle cease fire')]
        assert hold.do == [('UNIT_CHANGE_OBJECT_STATUS', s.name(lane, 'gun'), 'NO_ATTACK', 1)
                           for lane in s.LANES]
        start = next(x for x in t.scripts if x.name == 'Test - start')
        assert ('SET_MILLISECOND_TIMER', 'Sickle cease fire', 7.4) in start.do


@pytest.mark.parametrize('check', ['a', 'b', 'c', 'd'])
@pytest.mark.parametrize('lane,x', [('removed', 840), ('switch', 2340)])
def test_meta_sickle_replays_real_landing_dispatch_and_path(check, lane, x, monkeypatch):
    """Observed f114 landing is an input; f115 dispatch and f116..118 are assertions.

    Evidence: work/re/c_sickle_report.md. Leap timing/endpoint are separate gaps;
    this must exercise the landing consumer, without a V4 or direct shock call.
    """
    import build
    import sim
    import simunits
    from checks import engine_knock_sickle as s

    m, t, _ = build.resolve('engine_knock_sickle', check)
    e = sim.Sim(m, t)
    gun, enemy, friend = (e.bodies[s.name(lane, p)] for p in ('gun', 'enemy', 'friend'))
    e.eng.frame = 90
    e.leap_press(gun, 'Command_ActivateLeapSpecialPower', m.point(lane))
    # Replace only the arrival event with the observed event, as collision replays
    # do. The native flight clock and endpoint must not be claimed as reproduced.
    e.specials.leaps_due[:] = [(114, gun, (x - 39, 3561))]
    calls = []
    original = simunits.meta_impact_velocity

    def observe(effect, position, centre, height, **kw):
        velocity = original(effect, position, centre, height, **kw)
        calls.append((position, centre, velocity))
        return velocity

    monkeypatch.setattr(simunits, 'meta_impact_velocity', observe)
    e.eng.frame = 114
    e.self_power_due(114)
    assert not calls
    assert (gun.x, gun.y) == (x - 39, 3561)
    e.eng.frame = 115
    e.self_power_due(115)
    assert len(calls) == (1 if check in ('a', 'c') else 0)
    if calls:
        assert calls[0][0] == (x, 3550, 212.5)
        assert calls[0][1] == (x - 39, 3561, 212.5)
        assert calls[0][2] == pytest.approx((3.1677, -.8934, .5279), abs=.0001)
    assert id(friend) not in e.__dict__.get('impact_flights', {})
    assert (friend.x, friend.y) == (x - 80, 3550)
    samples = ([(x,3546.7,213.40), (x,3543.4,213.40), (x,3540,212.5)]
               if check in ('a', 'c') else [(x,3550,212.5)] * 3)
    for frame, xyz in enumerate(samples, 116):
        e.eng.frame = frame
        e.meta_impact_tick()
        z = e.impact_ground_z(enemy.x, enemy.y) if enemy.z is None else enemy.z
        assert (enemy.x, enemy.y, z) == pytest.approx(xyz, abs=.051)
    assert id(enemy) not in e.impact_flights
    e.self_power_due(118)
    assert len(calls) == (1 if check in ('a', 'c') else 0)
    assert any('落地伤害' in row['what'] for row in e.unmodeled.values())


@pytest.mark.xfail(strict=True, reason='真实跳跃到达帧/落点未闭环，见 work/re/c_sickle_report.md')
def test_meta_sickle_native_leap_arrival_remains_gap():
    import build
    import sim
    from checks import engine_knock_sickle as s

    m, t, _ = build.resolve('engine_knock_sickle', 'a')
    e = sim.Sim(m, t)
    gun = e.bodies[s.name('removed', 'gun')]
    e.eng.frame = 90
    e.leap_press(gun, 'Command_ActivateLeapSpecialPower', m.point('removed'))
    due, _, point = e.specials.leaps_due[0]
    assert (due, point) == (114, (801, 3561))


@pytest.mark.parametrize('check', ['a', 'b'])
def test_meta_sickle_named_landing_counters_match_bench(check):
    """Both native runs: the two named landing counters are 1 from s10..15.

    This broad area observation cannot establish exact leap frame/endpoint or
    damage; those remain gaps even when these two counters agree.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_knock_sickle', check)
    e = sim.Sim(m, t).run(16.)
    rows = [values for sec, values in e.series if 10 <= sec <= 15]
    assert rows
    assert all((v[1], v[3]) == (1, 1) for v in rows)


@pytest.mark.parametrize('check', ['c', 'd'])
def test_meta_sickle_cease_fire_named_health_and_landing_match_bench(check):
    """Frozen c/d readings: s10..15 HP=100%, land=1 in both lanes.

    See work/re/c_sickle_damage_report.md. This measures no health loss at
    these actual landing positions, not general DamageNugget correctness.
    The explicit landing-damage gap must remain even with matching counters.
    """
    import build
    import sim

    m, t, _ = build.resolve('engine_knock_sickle', check)
    e = sim.Sim(m, t).run(16.)
    rows = [values for sec, values in e.series if 10 <= sec <= 15]
    assert rows
    assert all(tuple(v) == (100, 1, 100, 1) for v in rows)
    assert any('落地伤害' in row['what'] for row in e.unmodeled.values())


@pytest.mark.parametrize('check,source', [
    pytest.param('c', True, marks=pytest.mark.xfail(
        strict=True, reason='零扣血的受伤来源通知未接到模型，见 work/re/c_sickle_damage_report.md')),
    ('d', False),
])
def test_meta_sickle_zero_health_notification_source_replay(check, source):
    """c: f115 ua source is each launcher, hp=150/150, hits=1; d: no ua.

    Replay the receiver's source attribution, not an UnderAttack predicate or
    a per-nugget damage amount. Its zero-health notification is still a gap.
    """
    import build
    import sim
    from checks import engine_knock_sickle as s

    m, t, _ = build.resolve('engine_knock_sickle', check)
    e = sim.Sim(m, t)
    for lane, x in [('removed', 801), ('switch', 2301)]:
        gun = e.bodies[s.name(lane, 'gun')]
        e.eng.frame = 90
        e.leap_press(gun, 'Command_ActivateLeapSpecialPower', m.point(lane))
        e.specials.leaps_due[-1] = (114, gun, (x, 3561))
    for frame in (114, 115):
        e.eng.frame = frame
        e.self_power_due(frame)
    for lane in s.LANES:
        enemy, friend = (e.bodies[s.name(lane, p)] for p in ('enemy', 'friend'))
        assert enemy.hp == friend.hp == 150
        assert friend.last_by is None
        assert enemy.last_by == (s.name(lane, 'gun') if source else None)
