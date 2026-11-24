"""The proxy player (experimental/cnv/proxy): its decisions on hand-made observations, then whole loops on the toy world.
Nothing here is checked against the game -- these pin the playtester's behaviour (the user's style), not retail."""
from proxy import fake as fk
from proxy import player as pp
from proxy import world as pw

F = frozenset
AI, AV = 'AlliedAntiInfantryVehicle', 'AlliedAntiVehicleVehicle'
OFFERS = [pw.Offer(AI, F({'VEHICLE'}), 700, pw.roles_from_name(AI)),
          pw.Offer(AV, F({'VEHICLE'}), 900, pw.roles_from_name(AV))]


def _foe(i, template, kindof, x, y, value=200, hits=F({'ground'})):
    return pw.Thing(i, 'Enemy', template, kindof=F(kindof), x=x, y=y, value=value, hits=hits)


def _mine(i, template=AI, x=0, y=0, health=300, max_health=300, cost=700, **kw):
    return pw.Mine(i, template, F({'VEHICLE'}), x, y, health, max_health, cost, 180, 300,
                   pw.roles_from_name(template), **kw)


def _obs(mine=(), seen=(), money=5000, frame=0, leads=()):
    return pw.Observation(frame, 'Player', money, (0, 0), list(mine), list(seen), list(OFFERS), F({'Enemy'}),
                          list(leads))


def test_kinds_and_roles():
    assert pw.roles_from_name(AI) == {'infantry'} and pw.roles_from_name('SovietAntiAirShip') == {'air'}
    assert pw.roles_from_name('JapanAntiVehicleInfantry') == {'vehicle'} and not pw.roles_from_name('AlliedMCV')
    assert pw.kind_of(_foe(1, 'b', {'STRUCTURE', 'FS_BARRACKS'}, 0, 0)) == 'structure'
    assert pw.kind_of(_foe(1, 'c', {'INFANTRY'}, 0, 0)) == 'infantry'
    assert pw.kind_of(_foe(1, 'k', {'AIRCRAFT', 'VEHICLE'}, 0, 0)) == 'air'
    assert pw.kind_of(pw.Thing(1, 'Enemy', 's', water=True)) == 'ship'


def _builds(orders):
    return [o.template for o in orders if o.kind == 'build']


def test_builds_the_counter_to_what_it_saw():
    p = pp.ProxyPlayer()
    assert _builds(p.decide(_obs(seen=[_foe(9, 'Conscript', {'INFANTRY'}, 2000, 0)]))) == [AI]
    p = pp.ProxyPlayer()
    assert _builds(p.decide(_obs(seen=[_foe(9, 'Hammer', {'VEHICLE'}, 2000, 0)]))) == [AV]


def test_switches_when_the_mix_changes():
    """Own anti-infantry already answers the infantry; tanks show up -> the next build is anti-vehicle."""
    p = pp.ProxyPlayer()
    mine = [_mine(1), _mine(2)]
    seen = [_foe(9, 'Conscript', {'INFANTRY'}, 2000, 0)]
    assert _builds(p.decide(_obs(mine, seen))) == [AI]      # 1400 answered vs 200 -- still the only kind seen
    seen.append(_foe(10, 'Hammer', {'VEHICLE'}, 2000, 100, value=800))
    assert _builds(p.decide(_obs(mine, seen, frame=15))) == [AV]


def test_saves_up_for_the_counter():
    p = pp.ProxyPlayer()
    assert _builds(p.decide(_obs(seen=[_foe(9, 'Hammer', {'VEHICLE'}, 2000, 0)], money=800))) == []
    assert p.log[-1][1] != 'build'


def test_pull_back_and_rejoin():
    p = pp.ProxyPlayer(pp.Style(pullback=0.35, rejoin=0.9))
    hurt = _mine(1, x=1000, health=90)                      # 0.30
    out = p.decide(_obs([hurt]))
    assert [(o.kind, o.pos) for o in out] == [('move', (0, 0))] and 1 in p.wounded
    half = _mine(1, x=10, health=200)                       # healing at home: not back yet
    p.decide(_obs([half], frame=15))
    assert 1 in p.wounded
    p.decide(_obs([_mine(1, x=10, health=280)], frame=30))
    assert 1 not in p.wounded and [w for _, w, _ in p.log] == ['pull back', 'rejoin']


def test_wounded_stay_out_of_the_attack():
    p = pp.ProxyPlayer(pp.Style(min_army=1))
    out = p.decide(_obs([_mine(1, health=50), _mine(2), _mine(3)], [_foe(9, 'Conscript', {'INFANTRY'}, 2000, 0)]))
    attackers = {o.units[0] for o in out if o.kind == 'attack'}
    assert attackers == {2, 3}


def test_sources_first_and_home_defence_overrides():
    barracks = _foe(5, 'SovietBarracks', {'STRUCTURE', 'FS_BARRACKS'}, 3000, 0, hits=F())
    near_unit = _foe(6, 'Conscript', {'INFANTRY'}, 1500, 0)
    p = pp.ProxyPlayer()
    p.decide(_obs([_mine(i) for i in (1, 2, 3)], [barracks, near_unit]))
    assert p.target == ('source', 5)                        # the closer conscript is not the plan
    raider = _foe(7, 'Conscript', {'INFANTRY'}, 300, 0)
    p.decide(_obs([_mine(i) for i in (1, 2, 3)], [barracks, near_unit, raider], frame=15))
    assert p.target == ('defend', 7)


def test_groups_up_before_going_and_regroups_when_beaten():
    barracks = _foe(5, 'SovietBarracks', {'STRUCTURE', 'FS_BARRACKS'}, 3000, 0, hits=F())
    guards = [_foe(10 + i, 'Conscript', {'INFANTRY'}, 3000, 50, value=200) for i in range(4)]   # threat 800
    p = pp.ProxyPlayer(pp.Style(min_army=3, attack_ratio=1.2, regroup_ratio=0.6))
    out = p.decide(_obs([_mine(1), _mine(2)], [barracks] + guards))
    assert not [o for o in out if o.kind == 'attack'] and p.log[-1][1] == 'wait'
    out = p.decide(_obs([_mine(1), _mine(2), _mine(3)], [barracks] + guards, frame=15))   # 2100 >= 960
    assert len([o for o in out if o.kind == 'attack']) == 3 and p.going == 5
    worn = [_mine(i, x=2500, health=120) for i in (1, 2, 3)]                               # 840 >= 480: keep going
    p.decide(_obs(worn, [barracks] + guards, frame=30))
    assert p.going == 5
    guards += [_foe(20 + i, 'Conscript', {'INFANTRY'}, 3000, 60) for i in range(4)]       # threat 1600: 840 < 960
    out = p.decide(_obs(worn, [barracks] + guards, frame=45))
    assert p.going is None and 'regroup' in [w for _, w, _ in p.log]
    assert {o.kind for o in out} <= {'move', 'build'}


def test_scouts_leads_with_the_cheapest_unit():
    p = pp.ProxyPlayer()
    leads = [(1500, 0), (0, 1500)]
    cheap = pw.Mine(4, 'AlliedScoutVehicle', F({'VEHICLE'}), 0, 0, 100, 100, 300)
    out = p.decide(_obs([_mine(1), cheap], leads=leads))
    assert [(o.kind, o.units, o.pos) for o in out] == [('move', (4,), (1500, 0))]
    out = p.decide(_obs([_mine(1), pw.Mine(4, 'AlliedScoutVehicle', F({'VEHICLE'}), 1450, 0, 100, 100, 300)],
                        leads=leads, frame=15))
    assert [(o.units, o.pos) for o in out] == [((4,), (0, 1500))]


def test_forgets_what_it_should_see_and_does_not():
    p = pp.ProxyPlayer()
    p.decide(_obs(seen=[_foe(9, 'Conscript', {'INFANTRY'}, 2000, 0)]))
    p.decide(_obs([_mine(1, x=0)], frame=15))               # nobody near: still remembered
    assert 9 in p.known
    p.decide(_obs([_mine(1, x=1900)], frame=30))            # looked, not there
    assert 9 not in p.known and p.log[-1][1] in ('gone', 'scout')




# --- whole loops on the toy world --------------------------------------------------------------------------------
SPECS = {
    'AlliedScoutVehicle': fk.Spec(F({'VEHICLE'}), 100, cost=300, speed=6, sight=400, range=100, dps=2),
    AI: fk.Spec(F({'VEHICLE'}), 300, cost=700, speed=4, range=180, dps=30, good_against=pw.roles_from_name(AI),
                seconds=8),
    AV: fk.Spec(F({'VEHICLE'}), 400, cost=900, speed=3.5, range=200, dps=30, good_against=pw.roles_from_name(AV),
                seconds=10),
    'SovietBarracks': fk.Spec(F({'STRUCTURE', 'FS_BARRACKS', 'SPAWNER'}), 1500, cost=500,
                              spawn=('SovietAntiVehicleInfantry', 300, 4)),
    'SovietWarFactory': fk.Spec(F({'STRUCTURE', 'FS_WARFACTORY', 'SPAWNER'}), 2000, cost=1000,
                                spawn=('SovietAntiVehicleVehicle', 450, 3)),
    'SovietAntiVehicleInfantry': fk.Spec(F({'INFANTRY'}), 100, cost=200, speed=2, sight=250, range=150, dps=20),
    'SovietAntiVehicleVehicle': fk.Spec(F({'VEHICLE'}), 400, cost=800, speed=3, sight=300, range=180, dps=25),
}


def _world(*spawners, money=2000):
    w = fk.FakeWorld(SPECS, money=money, income=1.0, offers=[AI, AV], leads=[(1500, 0), (1500, 1500), (0, 1500)])
    w.add('AlliedScoutVehicle', 'Player', 0, 0)
    for t, x, y in spawners:
        w.add(t, 'Enemy', x, y)
    return w


def _first(log, what):
    return next(f for f, w, _ in log if w == what)


def test_loop_scout_counter_attack_pull_back():
    """The one loop this round promised: scout -> build what counters the enemy -> go at its source -> pull the
    wounded back; the barracks falls inside four minutes."""
    w = _world(('SovietBarracks', 1500, 1500))
    p = pp.ProxyPlayer()
    pp.play(w, p, 15 * 240)
    log = p.log
    first_army_pullback = next(f for f, w_, d in log if w_ == 'pull back' and d.startswith(AI))
    assert _first(log, 'scout') < _first(log, 'build') < _first(log, 'attack') < first_army_pullback
    assert {d for f, w_, d in log if w_ == 'build'} == {f'{AI} vs infantry'}
    assert any(w_ == 'attack' and d.startswith('source SovietBarracks') for _, w_, d in log)
    assert any(t == 'SovietBarracks' for _, t, _ in w.dead)
    assert any(w_ == 'rejoin' for _, w_, _ in log)


def test_loop_against_tanks_builds_anti_vehicle():
    w = _world(('SovietWarFactory', 1500, 1500), money=3000)
    p = pp.ProxyPlayer()
    pp.play(w, p, 15 * 120)
    builds = {d for _, w_, d in p.log if w_ == 'build'}
    assert builds and all(d.startswith(AV) for d in builds)


def test_loop_is_deterministic():
    runs = []
    for _ in range(2):
        w = _world(('SovietBarracks', 1500, 1500))
        p = pp.ProxyPlayer()
        pp.play(w, p, 15 * 60)
        runs.append(p.log)
    assert runs[0] == runs[1]
