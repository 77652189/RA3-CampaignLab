"""The proxy player on the plan simulator (experimental/cnv/simproxy.py): A4 played from the start to its ending, a
playtest report out of it, the world's seam (what the player sees, the orders it takes, the score screen) and the
ice criterion (report.power_at: 冰在哪) on a real run. Skipped where the engine line's ra3model.proxy is not on this
computer (labpaths.ENGINE_MODEL), as the simulator's engine model is."""
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simproxy.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simproxy', ROOT / 'experimental' / 'cnv' / 'simproxy.py')
simproxy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simproxy)

pytestmark = pytest.mark.skipif(not simproxy.available(), reason='no ra3model.proxy (labpaths.ENGINE_MODEL)')

FPS = simproxy.FPS


@pytest.fixture(scope='module')
def lib():
    return simproxy.proxy()['xmldata'].Library()


@pytest.fixture(scope='module')
def a4_run(lib):
    return simproxy.play('a4', lib=lib)


def _after_scene(w, extra=0.0, demo_holds_fire=False):
    """Run the world until the opening scene hands the controls back (plus `extra` seconds).
    demo_holds_fire: the opening demo's troops (' Demo Foe ' / ' Demo Out ') get NO_ATTACK the second they are made,
    so the player's engineer comes out of the scene alive as on the bench -- in the simulator Demo Foe 2 stops 157
    from him against the ice and shoots him (test_simbench.DEMO_KILL: where the demo troops stop is not modelled)."""
    s = w.sim
    while s.flags.get('CNV_A4_Scene_1') != 1 and s.t < 200:
        w.step(FPS)
        if demo_holds_fire:
            for n, b in s.bodies.items():
                if ' Demo Foe ' in n or ' Demo Out ' in n:
                    b.status.add('NO_ATTACK')
    w.step(int(extra * FPS))


def test_a4_played_to_its_ending_with_a_report(a4_run):
    rep, w = a4_run
    assert rep['result'] in ('win', 'lose')                         # the mission ended it, not the clock
    assert rep['result'] == simproxy.ENDINGS[w.sim.ending[0]]
    assert rep['frames'] == pytest.approx(w.sim.ending[1] * FPS, abs=FPS)
    assert json.loads(json.dumps(rep, ensure_ascii=False)) == rep   # plain JSON values
    assert set(rep['goals']) == {'会场冻街口', '最后一程冻口子', '拆北营指挥所'}
    assert rep['sorties'] >= 1 and rep['peak_army'] >= 10          # it fought: the ten it starts with, the engineers
                                                                    # the level sends after them
    assert rep['losses']['enemy'] is not None and rep['losses']['enemy']['count'] >= 1
    summary = w.p['report'].summary(rep)
    assert summary.startswith('试玩 a4') and '巧解' in summary


def test_the_score_screen_is_the_simulators_deaths(a4_run):
    _, w = a4_run
    got = w.losses()
    dead = [b for b in w.sim.bodies.values() if not b.alive and not b.deleted and not b.scenery
            and b.life_end is None]
    assert len(got) == len(dead)
    trucks = [l for l in got if l.template == 'CNV_ConvoyTruck']
    assert trucks and all(l.owner != w.me for l in trucks)          # the convoy is an ally's, not the player's
    assert all(l.kind in w.pw.KINDS for l in got)
    assert [l.frame for l in got] == sorted(l.frame for l in got)


def test_what_the_player_sees_at_the_start(lib):
    w = simproxy.SimWorld('a4', lib=lib)
    obs = w.observe()
    assert obs.me == w.sim.human and obs.frame == 0
    assert len(obs.mine) == 10                                      # 1 engineer, 3 Guardians, 4 Peacekeepers, 2 Javelins
    assert {u.template for u in obs.mine} >= {'CNV_IceEngineer', 'AlliedAntiVehicleVehicleTech1'}
    pk = next(u for u in obs.mine if u.template == 'AlliedAntiInfantryInfantry')
    assert pk.cost > 0 and pk.good_against and pk.weapon_range > 0  # the SDK's data (Matchup), not a guess
    trucks = [w.sim.bodies[n] for n in w.escort]
    assert len(trucks) == 3
    assert obs.home == pytest.approx((sum(b.x for b in trucks) / 3, sum(b.y for b in trucks) / 3))
    assert obs.enemies and w.me not in obs.enemies
    for t in obs.seen:                                              # only what the player's sight reaches
        b = w.sim.bodies[w.names[t.id]]
        assert not b.scenery and w.sim.sees(b.x, b.y, b.surface == 'air')
    far = w.sim.bodies[w.sim.m.cast['north command'].name]
    assert w.ids.get(far.name) not in {t.id for t in obs.seen}      # the north base is not in sight at the start
    assert len(obs.leads) == len(simproxy.LEADS['a4'])


def test_orders_move_attack_and_refusals(lib):
    w = simproxy.SimWorld('a4', lib=lib)
    _after_scene(w)
    obs = w.observe()
    pw = w.pw
    u = next(m for m in obs.mine if m.template == 'AlliedAntiVehicleVehicleTech1')
    goal = (u.x + 300, u.y)
    assert w.issue(pw.Order('move', (u.id,), pos=goal))
    w.step(3 * FPS)
    b = w.sim.bodies[w.names[u.id]]
    assert math.hypot(b.x - goal[0], b.y - goal[1]) < math.hypot(u.x - goal[0], u.y - goal[1]) - 50
    assert not w.issue(pw.Order('build', template='AlliedAntiInfantryInfantry'))    # A4: the player has no factory
    assert not w.issue(pw.Order('attack', (u.id,), target=999999))
    assert not w.issue(pw.Order('move', (999999,), pos=goal))
    assert [r[2] for r in w.refused][:1] == ['no factory of mine builds it now']
    sign = w.sim.bodies[w.sim.m.cast['标志 一号'].name]
    sid = w._id(sign)
    assert w.issue(pw.Order('attack', (u.id,), target=sid))
    assert b.goal is sign and b.mode == 'attack'


def test_build_through_the_simulators_sidebar(lib):
    """engine_production a (a barracks, 2000): the lit buttons come as Offers with the data's counters, a build order
    queues at the barracks, the money the player sees drops by the whole cost at once (the queue's debt), and the
    unit comes out as one of the player's."""
    w = simproxy.SimWorld('engine_production', check='a', lib=lib)
    w.step(30)
    obs = w.observe()
    pw = w.pw
    offers = {o.template: o for o in obs.offers}
    assert 'AlliedEngineer' in offers and 'AlliedInfiltrationInfantry' not in offers   # tier 2 needs the upgrade
    pk = offers['AlliedAntiInfantryInfantry']
    assert pk.cost > 0 and pk.seconds > 0 and 'infantry' in pk.good_against and pk.rates
    before = obs.money
    assert w.issue(pw.Order('build', template='AlliedEngineer'))
    assert w.observe().money == before - offers['AlliedEngineer'].cost
    had = {u.id for u in obs.mine}
    w.step(15 * 15)
    new = [u for u in w.observe().mine if u.id not in had]
    assert [u.template for u in new] == ['AlliedEngineer']
    assert w.observe().money == int(w.sim.money[w.me])                 # paid off: nothing owed
    assert not w.issue(pw.Order('build', template='AlliedInfiltrationInfantry'))


def test_the_ice_goes_where_the_player_put_it(lib):
    """A ground power: the engineer walks to the spot and the ice core stands there (the simulator's R5), and the
    report's 冰在哪 criterion (report.power_at) holds for that place and not for another."""
    w = simproxy.SimWorld('a4', lib=lib)
    _after_scene(w, 2, demo_holds_fire=True)
    s, pw, rp = w.sim, w.pw, w.p['report']
    eng = next(m for m in w.observe().mine if m.template == 'CNV_IceEngineer')
    spot = s.point('inside 1')
    power = s.m.ability('engineer', 'freeze')
    before = set(s.bodies)
    f = w.frame
    assert w.issue(pw.Order('power', (eng.id,), pos=spot, power=power))
    w.step(40 * FPS)
    made = [s.bodies[n] for n in set(s.bodies) - before if s.bodies[n].made_by == w.names[eng.id]]
    assert made and all(math.hypot(b.x - spot[0], b.y - spot[1]) < 1 for b in made)
    tr = rp.Trace('ice', None, [], [], [(f, pw.Order('power', (eng.id,), pos=spot, power=power))], None, 'timeout',
                  w.frame)
    venue = next(g for g in simproxy.goals(w) if g.name == '会场冻街口')
    last = next(g for g in simproxy.goals(w) if g.name == '最后一程冻口子')
    assert venue.test(tr) == f and last.test(tr) is None


def test_a4_every_way_has_a_junction_on_the_convoys_road(lib):
    """Where a guard waits for a wave: the way's x, the convoy road's y (CHOKES 'road'), one per way, each on the road."""
    w = simproxy.SimWorld('a4', lib=lib)
    j = w.junctions()
    ways = [c.name for c in w.observe().chokes]
    assert set(j) == set(ways) and len(ways) == 6
    road_y = w.sim.point('convoy start')[1]
    assert all(y == road_y for _x, y in j.values())
    assert j['一号'] == (w.sim.point('inside 1')[0], road_y) and j['二号'][0] == w.sim.point('inside 2')[0]


def test_a4_the_proxy_ices_the_streets_on_its_own_and_compares(a4_run, lib):
    """The level gives only what a human sees (simproxy.CHOKES: the horn's countdown, the ways, the ice power); the
    proxy decides when and which (player._blocks). The default play ices the venue's streets before a horn and the
    report's 冰在哪 criterion sees it; Style(block=0) (the plain play) never ices, and compare() puts the two side by
    side."""
    rep, w = a4_run
    blocks = [m for m in rep['moments'] if m['what'] == 'block']
    assert blocks and rep['goals']['会场冻街口']['met']
    assert all(m['detail'].split(' by ')[0] in {c[0] for c in simproxy.CHOKES['a4']['ways']} for m in blocks)
    plain, _ = simproxy.play('a4', style=w.p['player'].Style(block=0), label='不放冰', lib=lib)
    assert not [m for m in plain['moments'] if m['what'] == 'block']
    assert not plain['goals']['会场冻街口']['met'] and not plain['goals']['最后一程冻口子']['met']
    assert rep['result'] == plain['result'] == 'lose'             # 11-07 B r26: ice 3:02, plain 3:50 (no longer "ice
    # holds longer": with the army kept round the convoy, two streets iced send the third street's wave sooner)
    # the army never goes for what cannot be aimed at (the spawn sculptures, the signal smoke) nor at the dead
    goes = [m['detail'] for m in rep['moments'] + plain['moments'] if m['what'] in ('go', 'defend')]
    assert not [d for d in goes if 'Sculpture' in d or 'Smoke' in d]
    # B r28: the opening scene holds the player's input -- the proxy only watches (no order even tried), then the
    # only refusals are attacks on a unit that died out of sight (the proxy forgets it on the refusal)
    assert min(m['frame'] for m in rep['moments'] if m['what'] in ('go', 'defend', 'block', 'post')) >= 75 * 15
    assert not [r for r in w.refused if r[2] != 'target gone']
    table = w.p['report'].compare([rep, plain])
    assert '挡路 0 次' in table and '共 2 局' in table and '会场冻街口 1/2' in table
