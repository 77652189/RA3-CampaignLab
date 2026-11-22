"""RecallUnitsSpecialPower (engine/modules/specialpower.py RecallUnits): what the bench's counters cannot see. Read on
the bench: checks/engine_recall_e.readings.toml (the airport's one Apollo called home, the cast seen; none without)."""
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
    assert [b.name for b in m.members(s.living())] == ['made 2', 'made 3', 'made 4']
    for k in range(5, 8):
        s.add(f'made {k}', APOLLO, 'Player_1', 0.0, 800.0, by='field')
    assert len(m.members(s.living())) == 4                   # MaxAircraftToRecall
