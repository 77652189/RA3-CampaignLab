"""The proxy player's use of a level's blocking power (player._blocks, world.Choke): watch the countdown, block the
ways nearest home just in time, keep the blockers out of the army and the scouting. Hand-made observations; nothing
here is a level's own data (the A4 run is CampaignLab tests/test_simproxy.py)."""
from proxy import player as pp
from proxy import world as pw

F = frozenset
ENG, GUN = 'IceEngineer', 'AlliedAntiInfantryVehicle'
FREEZE = 'Freeze'


def _eng(i, x=0, y=0, speed=30.0):
    return pw.Mine(i, ENG, F({'INFANTRY'}), x, y, 100, 100, 500, 0, 300, F(), speed=speed)


def _gun(i, x=0, y=0):
    return pw.Mine(i, GUN, F({'VEHICLE'}), x, y, 300, 300, 700, 180, 300, F({'infantry'}))


def _choke(name, x, at, blocked=False):
    return pw.Choke(name, (x, 100), (x, 200), at, FREEZE, F({ENG}), blocked)


def _obs(mine, chokes, frame=0, home=(0, 0), leads=()):
    return pw.Observation(frame, 'Player', 0, home, list(mine), [], [], F({'Enemy'}), list(leads), list(chokes))


def _powers(orders):
    return [(o.units[0], o.pos) for o in orders if o.kind == 'power']


def test_waits_then_sends_just_in_time():
    """600 away at 30/s is 20 s walk + 8 s build + 4 s margin = 32 s: not at 40 s left, yes at 30 s left."""
    p = pp.ProxyPlayer()
    ch = [_choke('A', 600, at=40 * 15)]
    assert not _powers(p.decide(_obs([_eng(1, 0, 100)], ch, frame=0)))
    got = _powers(p.decide(_obs([_eng(1, 0, 100)], ch, frame=10 * 15)))
    assert got == [(1, (600, 100))]
    assert [d for _, w, d in p.log if w == 'block'] == [f'A by {ENG}#1, 30s before']
    assert not _powers(p.decide(_obs([_eng(1, 0, 100)], ch, frame=11 * 15)))     # once per threat


def test_clicks_a_bare_spot_and_tries_again_when_refused():
    """A unit of mine on the choke: the click goes to the nearest spot power_clearance from it (the world's
    ForbiddenObjectRange); the world refusing the click (Sim.order_power) frees the choke for the next think."""
    p = pp.ProxyPlayer()
    ch = [_choke('A', 600, at=30 * 15)]
    mine = [_eng(1, 0, 100), _gun(2, 600, 100)]
    (uid, spot), = _powers(p.decide(_obs(mine, ch)))
    assert uid == 1 and spot != (600, 100) and pp._d(spot, (600, 100)) == p.style.block_nudge
    assert not _powers(p.decide(_obs(mine, ch, frame=1)))            # under way: not again
    p.refused(_obs(mine, ch, frame=2), pw.Order('power', (1,), pos=spot, power=FREEZE))
    assert [u for u, _ in _powers(p.decide(_obs(mine, ch, frame=3)))] == [1]
    # its button greyed (Mine.reloading): it is not sent until the reload is over
    q = pp.ProxyPlayer()
    greyed = [_eng(1, 0, 100)]
    greyed[0].reloading = F({FREEZE})
    assert not _powers(q.decide(_obs(greyed, ch)))
    assert _powers(q.decide(_obs([_eng(1, 0, 100)], ch, frame=1)))


def test_blocks_the_ways_nearest_home_up_to_the_style():
    chokes = [_choke('far', 1200, 30), _choke('near', 300, 30), _choke('mid', 600, 30)]
    engs = [_eng(1, 300, 100), _eng(2, 600, 100), _eng(3, 1200, 100)]
    got = _powers(pp.ProxyPlayer().decide(_obs(engs, chokes)))
    assert sorted(got) == [(1, (300, 100)), (2, (600, 100))]          # two nearest home, each by the closest blocker
    got = _powers(pp.ProxyPlayer(pp.Style(block=1)).decide(_obs(engs, chokes)))
    assert got == [(1, (300, 100))]


def test_only_the_next_threat_and_not_what_is_blocked_or_far():
    chokes = [_choke('now', 300, 30), _choke('later', 200, 30 + 60 * 15), _choke('held', 400, 30, blocked=True),
              _choke('gone', 100, None)]
    got = _powers(pp.ProxyPlayer().decide(_obs([_eng(1, 0, 100), _eng(2, 0, 100)], chokes)))
    assert got == [(1, (300, 100))]
    far = [pw.Choke('x', (3000, 0), (3000, 0), 30, FREEZE, F({ENG}))]
    assert not _powers(pp.ProxyPlayer().decide(_obs([_eng(1, 2900, 0)], far)))   # its source is past block_reach


def test_never_with_block_zero():
    p = pp.ProxyPlayer(pp.Style(block=0))
    assert not _powers(p.decide(_obs([_eng(1, 0, 100)], [_choke('A', 300, 30)])))


def test_blockers_stay_home_out_of_the_army_and_the_scouting():
    """The engineer is the cheapest unit (it would scout) and walks off: it is kept for the power and keeps to home;
    without chokes it scouts as before."""
    leads = [(5000, 5000)]
    mine = [_eng(1, 900, 0), _gun(2)]
    p = pp.ProxyPlayer()
    out = p.decide(_obs(mine, [_choke('A', 300, None)], leads=leads))
    moves = {o.units[0]: o.pos for o in out if o.kind == 'move'}
    assert moves == {1: (0, 0), 2: (5000, 5000)} and p.scout == 2
    p = pp.ProxyPlayer()
    p.decide(_obs(mine, [], leads=leads))
    assert p.scout == 1
