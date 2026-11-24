"""Style.counter_defend (experimental/cnv/proxy/player.py): at home each unit answers only the enemies it is made for, the
rest keep to home. Pins the playtester's behaviour (INFERRED rule), not retail."""
from proxy import player as pp
from proxy import world as pw

F = frozenset


def _foe(i, x, y, kindof=('INFANTRY',)):
    return pw.Thing(i, 'Enemy', f'Foe{i}', kindof=F(kindof), x=x, y=y, value=200, hits=F({'ground'}))


def _mine(i, good, x=0, y=0, busy=''):
    return pw.Mine(i, f'Mine{i}', F({'VEHICLE'}), x, y, 300, 300, 700, 180, 300, F(good), busy=busy)


def _obs(mine, seen, frame=0):
    return pw.Observation(frame, 'Player', 0, (0, 0), list(mine), list(seen), [], F({'Enemy'}), [])


def _orders(out):
    return {o.units[0]: (o.kind, o.pos, o.target) for o in out if o.kind != 'build'}


def test_each_answers_its_own_kind_the_rest_keep_home():
    anti_inf = _mine(1, {'infantry'}, x=100)
    anti_veh = _mine(2, {'vehicle'}, x=100)
    far_veh = _mine(3, {'vehicle'}, x=500)                  # away from home, nothing it counters: walks back
    seen = [_foe(5, 400, 0), _foe(6, -300, 0, kindof=('VEHICLE',))]
    p = pp.ProxyPlayer(pp.Style(counter_defend=True))
    o = _orders(p.decide(_obs([anti_inf, anti_veh, far_veh], seen)))
    assert p.target[0] == 'defend'
    assert o[1] == ('attack_move', (400, 0), None)
    assert o[2] == ('attack_move', (-300, 0), None) and o[3] == ('attack_move', (-300, 0), None)
    p = pp.ProxyPlayer(pp.Style(counter_defend=True))
    o = _orders(p.decide(_obs([anti_inf, anti_veh, far_veh], seen[:1])))   # only infantry at home
    assert o[1] == ('attack_move', (400, 0), None)
    assert 2 not in o                                       # already home: stays, fights what reaches it
    assert o[3] == ('move', (0, 0), None)


def test_nobody_counters_then_everyone_answers():
    army = [_mine(i, {'air'}, x=100) for i in (1, 2)]
    p = pp.ProxyPlayer(pp.Style(counter_defend=True, defend_focus=False))
    o = _orders(p.decide(_obs(army, [_foe(5, 400, 0)])))
    assert o == {1: ('attack_move', (400, 0), None), 2: ('attack_move', (400, 0), None)}


def test_off_by_default():
    army = [_mine(1, {'infantry'}, x=100), _mine(2, {'vehicle'}, x=100)]
    o = _orders(pp.ProxyPlayer().decide(_obs(army, [_foe(5, 400, 0)])))
    assert set(o) == {1, 2}
