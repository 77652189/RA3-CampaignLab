"""Native landing-grid classifier controls and measured replay."""
import importlib.util
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('grid_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_meta_grid_controls():
    import build
    from checks import engine_knock_kindgate as kg
    from checks import engine_knock_grid as grid

    m, _, _ = build.resolve('engine_knock_kindgate', 'b')
    baseline = next(u.xml for u in m.units if u.id == kg.NONINF)
    for check in ('a', 'b'):
        m, t, _ = build.resolve('engine_knock_grid', check)
        xml = next(u.xml for u in m.units if u.id == kg.NONINF)
        if check == 'a':
            assert xml == re.sub(r'(\bKindOf=")([^"]*)(")', lambda x: x[1] + x[2] + ' VEHICLE' + x[3], baseline)
        else:
            assert xml == baseline.replace('Locomotor="' + grid.HUMAN + '"', 'Locomotor="' + grid.TREADS + '"')
        assert len(t.counters) == 4


@pytest.mark.parametrize('check', ['a', 'b'])
def test_meta_grid_named_counters(check):
    """Native runs and evidence: work/re/c_grid_report.md."""
    import build
    import sim

    m, t, _ = build.resolve('engine_knock_grid', check)
    e = sim.Sim(m, t).run(24.)
    readings = [tuple(values) for sec, values in e.series if 22 <= sec <= 23]
    assert readings and all(row == (99, 99, 11, 0) for row in readings)


@pytest.mark.parametrize('check,lane', [('a', 'yuri'), ('a', 'rocket'), ('b', 'yuri'), ('b', 'rocket')])
def test_meta_grid_native_dispatch_and_controls(check, lane, monkeypatch):
    _replay(check, lane, monkeypatch)


@pytest.mark.parametrize('check', ['a', 'b'])
@pytest.mark.xfail(strict=True, reason='Native synthetic noninf retains the infantry grid after either VEHICLE '
                   'addition or Hammer NORMAL locomotor swap; Sim uses vehicle grid. '
                   'Classifier unresolved after two native runs: work/re/c_grid_report.md.')
def test_meta_grid_noninf_native_trajectory(check, monkeypatch):
    _replay(check, 'rocket', monkeypatch, verify_noninf=True)


def _replay(check, lane, monkeypatch, verify_noninf=False):
    """Replay observed collision input; same-frame dispatch remains INFERRED."""
    import build
    import sim
    import simunits
    from checks.engine_knock_objectgate import BIT
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_grid', check)
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = frame = 174
    gun, victim, near, other = (e.bodies[name(lane, p)] for p in ('gun', 'man', 'near', 'noninf'))
    for body in (near, other):
        (body.status.add if lane == 'yuri' else body.status.discard)(BIT)
    positions = {(b.x, b.y): part for b, part in ((victim, 'man'), (near, 'near'), (other, 'noninf'))}
    called = set()
    original = simunits.meta_impact_velocity

    def observe(effect, position, centre, height, **kwargs):
        part = positions[position[:2]]
        called.add(part)
        velocity = original(effect, position, centre, height, **kwargs)
        if part in ('near', 'noninf'):
            assert velocity == pytest.approx((5.9333, -.0001, -.0001), abs=.0001)
        return velocity

    monkeypatch.setattr(simunits, 'meta_impact_velocity', observe)
    delta = (-.00006, -.00024, .00003) if lane == 'yuri' else (0, -.00024, -.00049)
    centre = (victim.x - delta[0], victim.y - delta[1], 219 - delta[2])
    weapon, = gun.weapons
    e.queue_projectile_hit(frame, victim, weapon['dmg'], gun, weapon, centre)
    e.deal(1/15)
    assert called == ({'man'} if lane == 'yuri' else {'man', 'near', 'noninf'})
    assert int(100 * victim.hp / 150) == 99
    assert near.hp == other.hp == 150
    x = 820 if lane == 'yuri' else 2320
    samples = ([(x, 3750, 212.5)] * 7 if lane == 'yuri' else
               [(x+5.7,3748.6,214.27), (x+11.3,3747.2,215.45),
                (x+17,3745.7,216.04), (x+22.7,3744.3,216.04),
                (x+28.4,3742.9,215.45), (x+34.2,3741.5,214.27),
                (x+40,3740,212.5)])
    for tick, xyz in enumerate(samples, frame + 1):
        e.eng.frame = tick
        e.meta_impact_tick()
        z = lambda b: e.impact_ground_z(b.x, b.y) if b.z is None else b.z
        assert (near.x, near.y, z(near)) == pytest.approx(xyz, abs=.051)
        if lane == 'yuri' or verify_noninf:
            other_xyz = (x+20,3750,212.5) if lane == 'yuri' else (xyz[0]+20,xyz[1],xyz[2])
            assert (other.x, other.y, z(other)) == pytest.approx(other_xyz, abs=.051)
    assert id(near) not in e.impact_flights
    if lane == 'yuri' or verify_noninf:
        assert id(other) not in e.impact_flights


