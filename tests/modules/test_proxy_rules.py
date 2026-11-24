"""The proxy player's four general rules of 11-07 (experimental/cnv/proxy/player.py; the level line's A4 review): no orders in
a scene, a focused defence on the most dangerous enemy, standing ready where the coming threat's open way meets home,
no pulling back without healing. Pins the playtester's behaviour (INFERRED rules), not retail."""
from proxy import player as pp
from proxy import world as pw

F = frozenset
AI = 'AlliedAntiInfantryVehicle'
ENG = 'IceEngineer'


def _foe(i, x, y, template='Foe', value=200):
    return pw.Thing(i, 'Enemy', template, kindof=F({'INFANTRY'}), x=x, y=y, value=value, hits=F({'ground'}))


def _mine(i, x=0, y=0, health=300, template=AI, kindof=('VEHICLE',), good=None, rates=None):
    return pw.Mine(i, template, F(kindof), x, y, health, 300, 700, 180, 300,
                   pw.roles_from_name(template) if good is None else F(good), rates=rates or {})


def _obs(mine, seen=(), frame=0, home=(0, 0), chokes=(), **kw):
    return pw.Observation(frame, 'Player', 0, home, list(mine), list(seen), [], F({'Enemy'}), [], list(chokes), **kw)


ARMY = [_mine(i) for i in (1, 2, 3)]


def test_no_orders_in_a_scene():
    p = pp.ProxyPlayer()
    assert p.decide(_obs(ARMY, [_foe(7, 300, 0)], cinematic=True)) == []
    assert p.log[-1][1:] == ('wait', 'cinematic')
    assert p.decide(_obs(ARMY, [_foe(7, 300, 0)], frame=15))          # control back: it defends


def test_focus_the_most_dangerous_enemy_at_home():
    """Two enemies near home: a cheap one nearer and a tank killer (made for vehicles, the army is vehicles) a bit
    further. Every unit attacks the tank killer, one attack order each -- no attack-move."""
    near = _foe(5, 200, 0, template='JapanAntiInfantryInfantry')
    killer = _foe(6, 350, 0, template='JapanAntiVehicleInfantry')
    out = pp.ProxyPlayer().decide(_obs(ARMY, [near, killer]))
    assert {(o.kind, o.target) for o in out} == {('attack', 6)} and len(out) == 3
    # the world's own counters win over the name: say the near one is the vehicle killer
    out = pp.ProxyPlayer().decide(_obs(ARMY, [near, killer],
                                       counters={'JapanAntiInfantryInfantry': F({'vehicle'}),
                                                 'JapanAntiVehicleInfantry': F({'infantry'})}))
    assert {o.target for o in out} == {5}


def test_two_bands_at_once_split_the_defence():
    """A4's first horn: two streets send a band each at once, one inside defend_radius, the other just beyond it. The
    army splits by danger (equal here): each band gets half, the units nearer a band go to it; switched off, all go
    to the band at home. A band that grows on a later decision does not pull units already fighting the other."""
    west = [_foe(5, -400, 0, template='JapanAntiVehicleInfantry'), _foe(6, -420, 0, template='JapanAntiVehicleInfantry')]
    east = [_foe(7, 680, 0, template='JapanAntiVehicleInfantry'), _foe(8, 700, 0, template='JapanAntiVehicleInfantry')]
    army = [_mine(1, -50, 0), _mine(2, -60, 0), _mine(3, 50, 0), _mine(4, 60, 0)]
    p = pp.ProxyPlayer()
    out = p.decide(_obs(army, west + east))
    to = {o.units[0]: o.target for o in out}
    assert to[1] in (5, 6) and to[2] in (5, 6) and to[3] in (7, 8) and to[4] in (7, 8)
    out = pp.ProxyPlayer(pp.Style(split_defend=False)).decide(_obs(army, west + east))
    assert {o.target for o in out} <= {5, 6} and len(out) == 4
    # one band only: nothing changes from the plain focus
    out = pp.ProxyPlayer().decide(_obs(army, west))
    assert {o.target for o in out} <= {5, 6} and len(out) == 4


def test_focus_skips_what_a_unit_cannot_hurt():
    """A unit that does nothing to infantry (rates) is not sent at infantry; with nobody able, the old attack-move."""
    aa = _mine(1, good={'air'}, rates={'air': 50.0})
    out = pp.ProxyPlayer().decide(_obs([aa], [_foe(5, 200, 0)]))
    assert [(o.kind, o.pos) for o in out] == [('attack_move', (200, 0))]


def _chokes(at, blocked=()):
    # three ways out of the same countdown: sources 600, 900 and 1200 from home (all within block_reach)
    return [pw.Choke(n, (x, 300), (x, 600), at, 'freeze', F({ENG}), n in blocked)
            for n, x in (('a', 0), ('b', 800), ('c', 1100))]


def test_stand_ready_at_the_open_way():
    """Countdown 40 s off: two ways will be iced (Style.block 2, an engineer at hand), so the army attack-moves to
    the third one -- on the line from home to its mouth, post_reach out -- instead of waiting at home."""
    eng = [_mine(i, template=ENG, kindof=('INFANTRY',), good=()) for i in (9, 10)]   # two blockers: two ways shut
    p = pp.ProxyPlayer()
    out = p.decide(_obs(ARMY + eng, chokes=_chokes(40 * 15)))
    posts = {(o.kind, o.pos) for o in out if o.units[0] not in (9, 10)}
    assert len(posts) == 1
    kind, (x, y) = posts.pop()
    assert kind == 'attack_move' and abs((x * x + y * y) ** 0.5 - 500) < 1 and x > 900 * y / 300 * 0.9   # toward c
    assert p.log[-1][1] == 'post' and p.log[-1][2].startswith('c ')
    # no engineer -> nothing will be iced: the nearest way (a) is the open one
    p = pp.ProxyPlayer()
    out = p.decide(_obs(ARMY, chokes=_chokes(40 * 15)))
    assert {o.pos for o in out} == {(0, 300)}
    # too early (90 s off): nobody moves; Style.preposition off: nobody moves
    assert pp.ProxyPlayer().decide(_obs(ARMY, chokes=_chokes(90 * 15))) == []
    assert pp.ProxyPlayer(pp.Style(preposition=False)).decide(_obs(ARMY, chokes=_chokes(40 * 15))) == []


def test_the_post_is_held_after_the_horn_then_left():
    p = pp.ProxyPlayer(pp.Style(block=0))
    p.decide(_obs(ARMY, chokes=_chokes(30 * 15)))
    assert p.post is not None
    # the countdown ran out (no countdown on screen now): held post_hold (25 s) after the threat's frame
    assert p._post(_obs(ARMY, frame=40 * 15, chokes=_chokes(None))) == (0, 300)
    assert p._post(_obs(ARMY, frame=60 * 15, chokes=_chokes(None))) is None


def test_no_pulling_back_without_healing():
    hurt = _mine(1, health=50)
    p = pp.ProxyPlayer()
    p.decide(_obs([hurt], home=(500, 0)))
    assert 1 in p.wounded
    p = pp.ProxyPlayer()
    out = p.decide(_obs([hurt], home=(500, 0), healing=False))
    assert 1 not in p.wounded and not any(o.kind == 'move' and o.pos == (500, 0) and o.units == (1,) and
                                          p.log and p.log[0][1] == 'pull back' for o in out)
    assert not any(w == 'pull back' for _, w, _ in p.log)


def test_a_flash_in_the_fog_gets_a_share_of_the_army():
    """A4's second horn (B r36): a seen band out west, and a minimap flash east where nobody sees (an unseen street's
    wave). Half the army (the two nearer the flash) waits for it, attack-moving guard_reach out toward it, and is out
    of the army; the flash once old with nothing seen there frees its guards. Switched off: nobody guards."""
    west = [_foe(5, -1000, 0), _foe(6, -1020, 0)]
    army = [_mine(1, -250, 0), _mine(2, -260, 0), _mine(3, 250, 0), _mine(4, 260, 0)]
    flash = [(0, 1000.0, 0.0)]
    p = pp.ProxyPlayer()
    out = p.decide(_obs(army, west, frame=15, blips=flash))
    assert set(p.guards) == {3, 4}
    assert {o.units[0] for o in out if o.kind == 'attack_move' and o.pos == (100.0, 0.0)} == {3, 4}
    late = int(pp.Style().blip_hold * 15) + 15
    p.decide(_obs(army, west, frame=late, blips=flash))
    assert not p.guards
    p = pp.ProxyPlayer(pp.Style(ghost_guard=False))
    out = p.decide(_obs(army, west, frame=15, blips=flash))
    assert not p.guards and not any(o.pos == (100.0, 0.0) for o in out)


def test_flashes_the_player_can_read_are_no_guess():
    """No guard for a flash where the player's units see, at a way the player has shut (or is shutting), or behind a
    fight already at home (same direction from home)."""
    army = [_mine(1, -50, 0), _mine(2, 50, 0)]
    for flash, seen, chokes in (([(0, 250.0, 0.0)], [], ()),                       # in sight of unit 2
                                ([(0, 1000.0, 0.0)], [], [pw.Choke('e', (900, 0), (1000, 0), None, 'freeze',
                                                                   F({ENG}), True)]),
                                ([(0, 1000.0, 0.0)], [_foe(5, 400, 0)], ())):        # the fight at home is that way
        p = pp.ProxyPlayer()
        p.decide(_obs(army, seen, frame=15, blips=flash, chokes=chokes))
        assert not p.guards, (flash, seen, chokes)


def test_one_blocker_leaves_the_second_way_open():
    """Style.block 2 but one engineer: only the nearest way will be iced, so the army stands at the second (not the
    third, which nobody was going to shut)."""
    eng = _mine(9, template=ENG, kindof=('INFANTRY',), good=())
    out = pp.ProxyPlayer().decide(_obs(ARMY + [eng], chokes=_chokes(40 * 15)))
    (x, y), = {o.pos for o in out if o.units[0] != 9}
    assert abs(x - 800 * 500 / (800 ** 2 + 300 ** 2) ** 0.5) < 1      # toward b (800, 300)
