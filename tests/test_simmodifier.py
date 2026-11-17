"""The simulator's attribute modifiers, one interface for their two sources (simunits.modifier / upgrade_mods / auras /
effect; sim.Sim.modify / aura_tick). Bench: docs/engine/upgrades.md 1 (an upgrade taken away takes its modifier),
2 (RANGE the weapon only, VISION the sight), 4 (INVULNERABLE + UNDER_IRON_CURTAIN; a Duration hung through an upgrade
still runs out), 5 (the stasis zone: an aura, everyone within stops, free within 1 s of the zone's going)."""
from test_plans import named, small  # (puts experimental/cnv on the path)  # noqa: F401, I001
import sim  # noqa: E402
import simunits  # noqa: E402
from units import platform, stasis_zone, tower_ball  # noqa: E402


def test_stacking_adds_the_raises_and_multiplies_the_cuts():
    assert simunits.stack([1.5, 2.0]) == 2.5
    assert simunits.stack([0.5, 0.5]) == 0.25
    assert simunits.stack([2.0, 0.5]) == 1.0
    assert simunits.stack([]) == 1.0


def test_the_stasis_zone_modifier_and_aura_read():
    u = stasis_zone.zone()
    (a,) = simunits.auras(u.xml)
    assert a['range'] == stasis_zone.RADIUS and a['refresh'] == 4 and a['relation'] == {'ALLIES', 'ENEMIES', 'NEUTRAL'}
    assert a['include'] == set(stasis_zone.INCLUDE.split()) and a['active']
    m = simunits.modifier(u.xml, a['mod'])
    assert m['types'] == {'SPEED': [0.0]} and m['frames'] == 15
    assert {'IN_STASIS', 'UNATTACKABLE', 'NO_ATTACK'} <= m['status']


def test_the_tide_gun_high_upgrade_doubles_range_and_vision_only():
    u = platform.tide_gun()
    e = simunits.effect([simunits.modifier(u.xml, m) for _, m in simunits.upgrade_mods(u.xml, {u.names['on']})])
    assert e['RANGE'] == 2.0 and e['VISION'] == 2.0 and e['SPEED'] == 1.0 and not e['status']
    assert simunits.upgrade_mods(u.xml, set()) == []


def test_a_retail_modifier_is_found_and_shields_for_its_duration():
    m = simunits.modifier('', 'AttributeModifier_IronCurtain')
    assert m and m['frames'] == 300
    assert simunits.effect([m])['shielded']
    u = tower_ball.tower_ball()
    assert simunits.effect([simunits.modifier(u.xml, m) for _, m in
                            simunits.upgrade_mods(u.xml, {u.names['off']})])['shielded']


def _world(own):
    s = sim.Sim.__new__(sim.Sim)
    s.own, s.bodies, s.eng, s.t, s.used = own, {}, None, 0.0, set()
    s.relations, s.human, s.foe, s.ai, s.players = {}, 'PlyrHuman', 'PlyrEnemy', set(), {}
    return s


def _body(s, name, template, owner, x, kinds, speed=30.0):
    b = sim.Body(name, template, owner, float(x), 0.0, speed, kinds=frozenset(kinds))
    b.weapons = [{'range': 150.0, 'dps': 10.0, 'type': 'ARMOR_PIERCING', 'anti': set()}]
    b.vision = b.sight = 300.0
    s.bodies[name] = b
    return b


def test_the_zone_stops_friend_and_foe_within_and_lets_go_once_gone():
    u = stasis_zone.zone()
    s = _world({u.id: u.xml})
    zone = _body(s, 'zone', u.id, 'PlyrEnemy', 0, ['IMMOBILE'], speed=0.0)
    zone.weapons = []
    ours = _body(s, 'ours', 'Tank', 'PlyrHuman', 100, ['VEHICLE'])
    theirs = _body(s, 'theirs', 'Tank', 'PlyrEnemy', 150, ['VEHICLE'])
    out = _body(s, 'out', 'Tank', 'PlyrHuman', 400, ['VEHICLE'])
    s.aura_tick()
    for b in (ours, theirs):
        assert b.speed == 0.0 and {'IMMOBILE', 'NO_ATTACK', 'UNATTACKABLE', 'IN_STASIS'} <= b.status
    assert out.speed == 30.0 and not out.status and 'modifier' in s.used
    zone.alive = False                          # gone: held for the modifier's 1 s, then free
    s.t = 0.5
    s.aura_tick()
    assert ours.speed == 0.0
    s.t = 1.0
    s.aura_tick()
    assert ours.speed == 30.0 and not ours.status and theirs.weapons[0]['range'] == 150.0


def test_a_script_status_stays_under_the_modifiers():
    u = platform.tide_gun()
    s = _world({u.id: u.xml})
    gun = _body(s, 'gun', u.id, 'PlyrHuman', 0, ['STRUCTURE'], speed=0.0)
    gun.script_status.add('UNATTACKABLE')
    s.give_upgrade(gun, u.names['on'])
    assert gun.weapons[0]['range'] == 300.0 and gun.sight == 600.0 and gun.status == {'UNATTACKABLE'}
    s._upgrade(gun, u.names['on'], False)
    assert gun.weapons[0]['range'] == 150.0 and gun.sight == 300.0 and gun.status == {'UNATTACKABLE'}


def test_the_zone_holds_by_the_centre_and_a_short_hold_flickers_with_the_refresh():
    """Bench upgrades.md 5.1 (engine_stasis_edge / _leave): a Guardian at 190 from a 200 zone held, at 205 not (its
    box 20 x 12 does not count); refresh 1 s with hold 0.2 s flickers -- on at a refresh, off before the next."""
    u = stasis_zone.zone(radius=200, hold=0.2, refresh=1.0)
    s = _world({u.id: u.xml})
    zone = _body(s, 'zone', u.id, 'PlyrEnemy', 0, ['IMMOBILE'], speed=0.0)
    zone.weapons = []
    near = _body(s, 'near', 'Tank', 'PlyrHuman', 190, ['VEHICLE'])
    edge = _body(s, 'edge', 'Tank', 'PlyrHuman', 205, ['VEHICLE'])
    seen = []
    for k in range(4):
        s.t = 0.5 * k
        s.aura_tick()
        seen.append(near.speed == 0.0)
        assert edge.speed == 30.0
    assert seen == [True, False, True, False]
