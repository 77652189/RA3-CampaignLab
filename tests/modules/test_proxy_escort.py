"""The proxy player's target rules (experimental/cnv/proxy/player.py): what cannot be aimed at, an escort level's leash, a
refused attack, defending by attack-move. Pins the playtester's behaviour (INFERRED rules), not retail."""
from proxy import player as pp
from proxy import world as pw

F = frozenset
AI = 'AlliedAntiInfantryVehicle'


def _foe(i, x, y, kindof=('INFANTRY',), status=(), hits=F({'ground'})):
    return pw.Thing(i, 'Enemy', f'Foe{i}', kindof=F(kindof), status=F(status), x=x, y=y, value=200, hits=hits)


def _mine(i, x=0, y=0, busy=''):
    return pw.Mine(i, AI, F({'VEHICLE'}), x, y, 300, 300, 700, 180, 300, pw.roles_from_name(AI), busy=busy)


def _obs(mine, seen, frame=0, home=(0, 0), escort=False):
    return pw.Observation(frame, 'Player', 0, home, list(mine), list(seen), [], F({'Enemy'}), [], escort=escort)


ARMY = [_mine(i) for i in (1, 2, 3)]


def test_never_aims_at_what_cannot_be_aimed_at():
    """UNATTACKABLE (a level's spawn sculpture) and INERT (smoke, props) are skipped, at home and away."""
    sculpture = _foe(5, 200, 0, kindof=('STRUCTURE',), status=('UNATTACKABLE',), hits=F())
    smoke = _foe(6, 100, 0, kindof=('IMMOBILE', 'INERT'), hits=F())
    p = pp.ProxyPlayer()
    p.decide(_obs(ARMY, [sculpture, smoke]))
    assert p.target is None
    p.decide(_obs(ARMY, [sculpture, smoke, _foe(7, 2000, 0)], frame=15))
    assert p.target == ('unit', 7)


def test_home_answers_only_what_can_hurt():
    unarmed = _foe(5, 200, 0, hits=F())
    p = pp.ProxyPlayer()
    p.decide(_obs(ARMY, [unarmed]))
    assert p.target == ('unit', 5)                          # still a target, but not a 'defend' at home
    p.decide(_obs(ARMY, [unarmed, _foe(6, 400, 0)], frame=15))
    assert p.target == ('defend', 6)


def test_escort_keeps_the_army_with_what_it_protects():
    """On an escort the far barracks is not the plan; the army walks with the convoy (home) instead."""
    barracks = _foe(5, 3000, 0, kindof=('STRUCTURE', 'FS_BARRACKS'), hits=F())
    p = pp.ProxyPlayer()
    p.decide(_obs(ARMY, [barracks]))
    assert p.target == ('source', 5)
    p = pp.ProxyPlayer()
    away = [_mine(i, x=-400) for i in (1, 2, 3)]
    out = p.decide(_obs(away, [barracks], escort=True))
    assert p.target is None and p.going is None
    assert sorted(o.units[0] for o in out if o.kind == 'move' and o.pos == (0, 0)) == [1, 2, 3]
    near = _foe(6, 800, 0)                                  # within escort_reach: worth a sortie
    p.decide(_obs(ARMY, [barracks, near], frame=15, escort=True))
    assert p.target == ('unit', 6)


def test_fighting_near_home_is_not_called_back():
    p = pp.ProxyPlayer()
    army = [_mine(1, x=300, busy='attack'), _mine(2, x=300), _mine(3, x=900, busy='attack')]
    out = p.decide(_obs(army, [], escort=True))
    assert sorted(o.units[0] for o in out if o.kind == 'move' and o.pos == (0, 0)) == [2, 3]   # 1 fights on


def test_a_refused_attack_forgets_the_target():
    p = pp.ProxyPlayer()
    p.decide(_obs(ARMY, [_foe(7, 2000, 0)]))
    o = pw.Order('attack', (1,), target=7)
    p.refused(_obs(ARMY, [], frame=15), o)
    assert 7 not in p.known and p.log[-1][1] == 'gone' and 1 not in p.orders
    p.refused(_obs(ARMY, [], frame=30), pw.Order('build', template=AI))   # nothing to forget


def test_defends_by_attack_move_when_not_focusing():
    raider = _foe(7, 300, 0)
    out = pp.ProxyPlayer(pp.Style(defend_focus=False)).decide(_obs(ARMY, [raider]))
    assert {(o.kind, o.pos) for o in out} == {('attack_move', (300, 0))}
    out = pp.ProxyPlayer(pp.Style(defend_move=False)).decide(_obs(ARMY, [raider]))
    assert {(o.kind, o.target) for o in out} == {('attack', 7)}
