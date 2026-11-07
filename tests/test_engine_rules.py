"""What the engine line read in the game's own script code and checked on the bench (work/re/ra3-script-reference.md,
2026-11-04), held in the simulator and the product rules: E1 a kind counted in an area is everyone's, E2 "attacked by the
player" reads the last attacker and needs it standing, E3 an order to a team nobody joined does nothing, E4 a health
percentage is rounded down."""
from test_plans import small  # (puts experimental/cnv on the path)  # noqa: I001
import contract  # noqa: E402
import sim  # noqa: E402
from model import Script  # noqa: E402

LT, LE = 0, 1                                    # the comparison codes of a condition (sim.CMP)


def world():
    s = sim.Sim(small())
    foe = next(b for b in s.bodies.values() if b.owner == 'Soviet_1' and not b.scenery)
    hit = s.add('UNIT - hitter', foe.template, s.human, foe.x + 50, foe.y)
    return s, foe, hit


def test_e2_attacked_by_the_player_needs_the_last_attacker_standing_and_the_players():
    s, foe, hit = world()
    ask = lambda: s.cond('NAMED_ATTACKED_BY_PLAYER', [foe.name, s.human])  # noqa: E731
    assert not ask()                                                     # never hit
    foe.last_hit, foe.last_by = s.human, hit.name
    assert ask()
    hit.owner = 'Soviet_1'                                               # it changed hands: the new owner's
    assert not ask()
    hit.owner = s.human
    other = s.add('UNIT - other', foe.template, 'Soviet_1', foe.x, foe.y)
    foe.last_hit, foe.last_by = other.owner, other.name                  # hit by somebody else since: false
    assert not ask()
    foe.last_hit, foe.last_by = s.human, hit.name
    s.destroy(hit, 'self-destruct', delete=True)
    s.t += 5.0                                                           # gone from the name cache
    assert not ask()                                                     # its attacker died: the condition went false
    foe.last_hit, foe.last_by = s.human, None                            # a run script's made-up hit stands
    assert ask()


def test_e4_a_health_percentage_is_rounded_down():
    s, foe, _ = world()
    foe.health = 49.9
    assert s.cond('UNIT_HEALTH', [foe.name, LT, 50])                     # 49.9 reads 49: "< 50" holds
    foe.health = 50.0
    assert not s.cond('UNIT_HEALTH', [foe.name, LT, 50]) and s.cond('UNIT_HEALTH', [foe.name, LE, 50])
    foe.health = 99.9
    assert s.cond('UNIT_HEALTH', [foe.name, LE, 99]) and not s.cond('UNIT_HEALTH', [foe.name, 2, 100])


def test_e3_an_order_to_a_team_nobody_joined_is_lost_and_joining_makes_it_stand():
    s, foe, _ = world()
    team = 'Soviet_1/teamCNVTest'
    s.act('TEAM_STOP', [team], Script('X', [], []))
    assert s.lost_orders and s.lost_orders[0][2:] == ('TEAM_STOP', team)
    s.act('UNIT_SET_TEAM', ['UNIT - nobody', team], Script('X', [], []))      # even a unit that is not there makes it
    s.act('TEAM_STOP', [team], Script('X', [], []))
    assert len(s.lost_orders) == 1


def test_e3_the_product_rule_wants_the_team_joined_first():
    m = small()
    team = 'Soviet_1/teamCNVTest'
    assert contract.team_orders_land(m) == []
    m.scripts.append(Script('CNV ZZ - Lost', [], [('TEAM_ATTACK_NAMED', team, 'x')]))
    assert any('nobody joined' in p for p in contract.team_orders_land(m))
    m.scripts[-1].do[:0] = [('UNIT_SET_TEAM', 'a', team)]                    # ctx.order's shape
    assert contract.team_orders_land(m) == []
    m.scripts.append(Script('CNV ZZ - Stop', [], [('TEAM_STOP', 'Soviet_1/teamCNVOther')]))
    assert any('Other' in p for p in contract.team_orders_land(m))
    m.scripts.append(Script('CNV ZZ - Joins', [], [('UNIT_SET_TEAM', 'a', 'Soviet_1/teamCNVOther')]))
    assert contract.team_orders_land(m) == []                                # a stop follows an order some script gave
    m.scripts.append(Script('Test - ghost', [], [('TEAM_GUARD_AREA', 'Nobody/team', 'x')]))
    assert contract.team_orders_land(m) == []                                # a check's own scripts are not the level's


def test_e1_the_product_rule_refuses_a_kind_counted_in_an_area():
    m = small()
    assert contract.kind_counts_in_area(m) == []
    cond = ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', 'Player_1', 0, 3, ('KINDOF', 'x'), 'area')
    m.scripts.append(Script('CNV ZZ - Count', [cond], [('SET_FLAG', 'f', 1)]))
    assert len(contract.kind_counts_in_area(m)) == 1
    m.scripts.append(Script('Test - count', [cond], [('SET_FLAG', 'g', 1)]))
    assert len(contract.kind_counts_in_area(m)) == 1                         # a check may read it (it says "everyone")
