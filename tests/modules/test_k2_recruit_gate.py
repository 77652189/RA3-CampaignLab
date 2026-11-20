"""simai.Unit.in_combat: what TeamTemplate.AllowRecruitUnitsInCombat false keeps out of a team (R3 item 3, K2).

The rule (work/re/k2_recruit_gate_1119.md): the unit's own attack target -- the order's (goal) or the one it went after
(chase), else this tick's aim, else the AI's recorded target -- alive, that one of its weapons can hit and reaches.
Firing decides nothing: bench k2gate0 refuses a Guardian 60 s in pre-attack (no shot) at a live foe in range, and the
K2 cut's stale fire entries on dead foes kept the Hammers out past the swap (test_ai_reverse_k2). The whole-run
readings are checks/engine_k2gate.readings.toml."""
from types import SimpleNamespace

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.ai.core as simai  # noqa: E402

CANNON = {'range': 150.0, 'anti': ('ANTI_GROUND',)}


def body(x=0.0, y=0.0, alive=True, serial=1, goal=None, chase=None, weapons=(CANNON,)):
    return SimpleNamespace(x=x, y=y, radius=10.0, alive=alive, serial=serial, goal=goal, chase=chase,
                           weapons=list(weapons), template='T', kinds=(), name=f'b{serial}')


class Port:
    """The observation port's three reads in_combat uses."""

    def __init__(self, firing=(), volleys=(), hits=True):
        self._firing, self._volleys, self.hits = list(firing), list(volleys), hits

    def firing(self):
        return list(self._firing)

    def volleys(self):
        return list(self._volleys)

    def can_hit(self, w, t):
        return self.hits


def foe(d=100.0, alive=True, serial=9):
    return body(y=d, alive=alive, serial=serial)


def test_an_ordered_live_target_in_reach_is_combat_without_a_shot():
    """bench k2gate0: aiming in pre-attack (no fire entry) is in combat."""
    assert simai.Unit(body(goal=foe()), Port()).in_combat


def test_a_stale_fire_entry_on_a_dead_foe_is_not_combat():
    """The K2 cut: the continuous fire record still named a dead foe; that kept the Hammers out."""
    me = body()
    assert not simai.Unit(me, Port(firing=[(foe(alive=False), 1.0, me)])).in_combat


def test_this_ticks_aim_counts_when_it_holds_no_target():
    me = body()
    assert simai.Unit(me, Port(firing=[(foe(), 1.0, me)])).in_combat
    assert simai.Unit(me, Port(volleys=[(foe(), CANNON, me)])).in_combat
    assert not simai.Unit(me, Port(firing=[(foe(), 1.0, body(serial=2))])).in_combat     # someone else's aim


def test_a_dead_goal_is_no_target():
    assert not simai.Unit(body(goal=foe(alive=False)), Port()).in_combat
    assert not simai.Unit(body(goal=(50.0, 50.0)), Port()).in_combat                     # a point, not a thing


def test_the_chase_is_its_own_target():
    assert simai.Unit(body(chase=foe()), Port()).in_combat


@pytest.mark.parametrize('d, inside', [(160.0, True), (175.0, False)])
def test_out_of_reach_is_not_combat(d, inside):
    """Reach is edge to edge (simrange.in_range): 150 + both radii 10 less UNDERSIZE."""
    import engine.combat.range as simrange
    assert simrange.in_range(body(), foe(d), CANNON) is inside
    assert simai.Unit(body(goal=foe(d)), Port()).in_combat is inside


def test_a_weapon_that_cannot_hit_it_is_not_combat():
    assert not simai.Unit(body(goal=foe()), Port(hits=False)).in_combat
    assert not simai.Unit(body(goal=foe(), weapons=()), Port()).in_combat


def test_the_ais_recorded_target_is_the_last_resort():
    t = foe()
    assert simai.Unit(body(), Port(), hunted=lambda s: t).in_combat
    assert not simai.Unit(body(), Port(), hunted=lambda s: foe(alive=False)).in_combat
    assert not simai.Unit(body(), Port(), hunted=lambda s: None).in_combat
    # its own target first: a far own target is not overridden by a near recorded one
    assert not simai.Unit(body(goal=foe(400.0)), Port(), hunted=lambda s: t).in_combat


def test_no_port_or_a_dead_unit_is_not_combat():
    assert not simai.Unit(body(goal=foe())).in_combat
    assert not simai.Unit(body(goal=foe(), alive=False), Port()).in_combat


def test_brain_hunt_target_reads_the_hunt_state_by_serial():
    br = object.__new__(simai.Brain)
    assert br.hunt_target(1) is None
    t = foe()
    br._hunt_goals = {1: SimpleNamespace(target=t, state=26)}
    assert br.hunt_target(1) is t and br.hunt_target(2) is None
