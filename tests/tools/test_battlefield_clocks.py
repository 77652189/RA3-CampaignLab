"""Battlefield's modules' timers (experimental/cnv/engine/state/battlefield.py step 10, S 11d): a run cut while an Apocalypse
waits to mend (and one hurt the moment before the cut), a power plant unpacks, another is being sold, a core's
lifetime runs and a tank's late lifetime (simbody.last_until) runs, its file placed onto an empty run of the same map:
each timed module's clocks read back on the file's clock, and run on, the host mends, gives power, deletes and kills
at the source's frames (sampled each tick). A clock row of a tag the host's thing has no module of is named; the
check refuses a row of no known tag, a missing field, a frame not a whole number and a hurt not a bool."""
import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.state.battlefield as simbattlefield  # noqa: E402
import engine.objects.body as simbody  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from maps import probe_range  # noqa: E402

P1 = 'Player_1'
APOC = 'SovietAntiVehicleVehicleTech3'      # AutoHealBehavior: 2 points every 7 frames, 15 frames after a hurt
PLANT = 'SovietPowerPlant'                  # unpacks 150 frames made in the run; sold in 30
TANK = 'AlliedAntiVehicleVehicleTech1'
CORE = '''<GameObject id="CNV_TestCore" Side="Neutral" KindOf="IMMOBILE">
  <Behaviors>
    <LifetimeUpdate id="ModuleTag_Life" MinLifetime="4s" MaxLifetime="4s" DeathType="FADED" />
  </Behaviors>
</GameObject>'''
OWN = {'CNV_TestCore': CORE}


def _small(objects=()):
    w = simsmall.small_world(list(objects), model=False, map=probe_range)
    w.own.update(OWN)
    return w


def _source():
    w = _small([('apoc', APOC, P1, 2000.0, 2000.0), ('hurt', APOC, P1, 2300.0, 2000.0),
                ('sold', PLANT, P1, 2600.0, 2600.0), ('tank', TANK, P1, 2000.0, 2600.0)])
    w.money[P1] = 0
    w.run(1.0)
    w.bodies['apoc'].damage(300)            # its mend waits 15 frames from its next run
    w.add('core', 'CNV_TestCore', CIV_OWNER, 1500.0, 1500.0, at=w.t)
    w.add('built', PLANT, P1, 2900.0, 2900.0, by='script', at=w.t)     # made in the run: it unpacks
    w.sell(w.bodies['sold'])
    simbody.last_until(w, w.bodies['tank'], w.frame_now() + 40)        # a late lifetime: no block of the tank's
    w.run(1.5)
    w.bodies['hurt'].damage(300)            # the moment before the cut: told, not run yet
    return w


CIV_OWNER = simbattlefield.CIV


def _trace(w, seconds=12.0):
    """Each tick: each named thing's (alive, health) and the player's power, for `seconds`."""
    out = []
    end = w.t + seconds
    while w.t < end - 1e-9:
        w.run(w.t + 0.5)
        out.append(([(n, b.alive, round(float(b.hp), 3)) for n, b in sorted(w.bodies.items()) if not n.startswith('#')],
                     tuple(w.power(P1))))
    return out


def _clocks(doc, thing):
    return next(t for t in doc['things'] if t['id'] == thing)['clocks']


def _placed():
    src = _source()
    doc = simbattlefield.export(Observe(src))
    host = _small()
    return src, doc, host, simbattlefield.place(host, doc)


def test_the_cut_holds_each_timer_and_the_host_reads_them_back_on_the_files_clock():
    src, doc, host, gaps = _placed()
    assert simbattlefield.check(doc) == [] and gaps == []
    f = doc['frame']
    [heal] = [c for c in _clocks(doc, 'apoc') if c['module'] == 'AutoHealBehavior' and c['mend'] is not None]
    assert f < heal['mend'] <= f + 15 and not heal['hurt']
    assert any(c['module'] == 'AutoHealBehavior' and c['hurt'] for c in _clocks(doc, 'hurt'))
    assert [c['dies'] for c in _clocks(doc, 'core')] == [src.bodies['core'].life_end] and src.bodies['core'].life_end > f
    assert [c['dies'] for c in _clocks(doc, 'tank') if c['module'] == 'LifetimeUpdate'] == [src.bodies['tank'].life_end]
    assert {c['module']: c for c in _clocks(doc, 'sold')}['StructureSellUpdate']['gone'] > f
    assert {c['module']: c for c in _clocks(doc, 'built')}['StructureUnpackUpdate']['unpacked'] > f
    back = simbattlefield.rebase(simbattlefield.export(Observe(host)), doc['t'], doc['frame'])
    assert {t['id']: t['clocks'] for t in back['things']} == {t['id']: t['clocks'] for t in doc['things']}
    old = dict(doc, things=[{k: v for k, v in t.items() if k != 'clocks'} for t in doc['things']])   # before step 10
    assert all('clocks' not in t for t in simbattlefield.rebase(old, doc['t'] + 1, doc['frame'] + 15)['things'])


def test_run_on_the_host_mends_gives_power_deletes_and_kills_at_the_sources_ticks():
    src, doc, host, gaps = _placed()
    assert gaps == []
    host.money[P1] = src.money[P1]
    a, b = _trace(src), _trace(host)
    assert a == b
    first, last = ({n: alive for n, alive, _ in a[k][0]} for k in (0, -1))
    assert all(first[n] and not last[n] for n in ('core', 'sold', 'tank'))     # each timer ran out in the trace
    hp = [{n: h for n, _, h in tick}['apoc'] for tick, _ in a]
    assert hp[0] < hp[-1]                   # the apocalypse mended
    made = [power[0] for _, power in a]
    assert made[0] > min(made) < made[-1]   # the sold plant's power went with it, the built one's came unpacked


def test_the_round_trip_has_no_difference():
    src = _source()
    doc = simbattlefield.export(Observe(src))
    assert simbattlefield.round_trip(_small(), doc) == []


def test_a_clock_of_a_module_the_hosts_thing_lacks_is_named():
    src = _source()
    doc = simbattlefield.export(Observe(src))
    i = next(k for k, t in enumerate(doc['things']) if t['id'] == 'apoc')
    doc['things'][i]['clocks'].append({'module': 'StructureSellUpdate', 'gone': doc['frame'] + 10})
    gaps = simbattlefield.place(_small(), doc)
    assert [g for g in gaps if g.startswith(f'things[{i}].clocks:')] and len(gaps) == 1
    assert simbattlefield.WHY['clocks'] in gaps[0]


@pytest.mark.parametrize('row, why', [
    ({'module': 'Nope', 'dies': 1}, 'module: not one of'),
    ({'module': 'LifetimeUpdate'}, 'missing dies'),
    ({'module': 'LifetimeUpdate', 'dies': 1.5}, 'dies: not null or a whole number'),
    ({'module': 'LifetimeUpdate', 'dies': True}, 'dies: not null or a whole number'),
    ({'module': 'AutoHealBehavior', 'mend': None, 'ok': 0, 'hurt': 1}, 'hurt: not a bool'),
    ({'module': 'StructureSellUpdate', 'gone': None, 'extra': 1}, 'extra'),
    ({'module': ['LifetimeUpdate'], 'dies': 1}, 'module: not one of'),
])
def test_the_check_refuses_a_broken_clock_row(row, why):
    doc = simbattlefield.export(Observe(_small([('tank', TANK, P1, 2000.0, 2000.0)])))
    doc['things'][-1]['clocks'] = [row]
    bad = simbattlefield.check(doc)
    assert any(b.startswith(f'things[{len(doc["things"]) - 1}].clocks[0]') and why in b for b in bad), bad
