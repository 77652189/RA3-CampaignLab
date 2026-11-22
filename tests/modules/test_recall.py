"""RecallUnitsSpecialPower / ReturnToProducerSpecialPower (engine/modules/specialpower.py): what the bench's counters
cannot see. Read on the bench: checks/engine_recall_e.readings.toml (the airport's one Apollo called home, the cast
seen; none without), checks/engine_returnproducer_e.readings.toml (the Apollo's own return: home, USER_1, one cast)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402

APOLLO = 'AlliedFighterAircraft'


def test_a_cast_calls_home_only_its_own_living_planes_up_to_four():
    s = simsmall.small_world([('field', 'AlliedAirfield', 'Player_1', 0.0, 0.0),
                              ('other', 'AlliedAirfield', 'Player_1', 600.0, 0.0)])
    for k in range(5):
        s.add(f'made {k}', APOLLO, 'Player_1', 0.0, 800.0, by='field')
    s.add('elsewhere', APOLLO, 'Player_1', 600.0, 800.0, by='other')
    s.bodies['made 0'].alive = False
    s.bodies['made 1'].owner = 'Soviet_1'                    # given away: no longer its owner's
    (m,) = s.bodies['field'].find(interfaces.Recall)
    assert [(b.name, h.name) for b, h in m.flights(s.bodies.values())] == [
        ('made 2', 'field'), ('made 3', 'field'), ('made 4', 'field')]
    for k in range(5, 8):
        s.add(f'made {k}', APOLLO, 'Player_1', 0.0, 800.0, by='field')
    assert len(m.flights(s.bodies.values())) == 4             # MaxAircraftToRecall


def test_an_apollo_returns_to_the_living_airport_that_made_it_marked_for_30_s():
    s = simsmall.small_world([('field', 'AlliedAirfield', 'Player_1', 0.0, 0.0),
                              ('other', 'AlliedAirfield', 'Player_1', 600.0, 0.0)])
    s.add('plane', APOLLO, 'Player_1', 0.0, 800.0, by='other')
    (m,) = s.bodies['plane'].find(interfaces.Recall)
    assert [(b.name, h.name) for b, h in m.flights(s.bodies.values())] == [('plane', 'other')]
    assert m.mark() == ('USER_1', 30.0)
    s.bodies['other'].alive = False
    assert m.flights(s.bodies.values()) == []                 # its airport gone: nowhere to fly
