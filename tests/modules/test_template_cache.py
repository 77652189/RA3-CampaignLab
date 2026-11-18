"""The template reads are kept per process (simunits._xml, T9): the SDK's by name, a mission's by its file's text. Two
worlds built one after the other in one process, each overriding the same template its own way, each read their own
override -- through the unit's own file and through a GameObject that only another of the mission's files defines."""
import dataclasses

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import model  # noqa: E402
import parts  # noqa: E402
import simsmall  # noqa: E402
import simunits  # noqa: E402

UNIT = 'AlliedAntiInfantryVehicle'          # a retail unit a mission may override
BASE = 'CNVCacheBase'                       # a template defined only inside a mission file (not under its own key)


def _world(cost, base_cost):
    unit = (f'<GameObject id="{UNIT}" inheritFrom="{BASE}"><BuildCost Amount="{cost}"/></GameObject>\n'
            f'<GameObject id="{BASE}"><BuildCost Amount="{base_cost}"/></GameObject>')
    holder = f'<GameObject id="CNVCacheHolder"></GameObject>\n<GameObject id="{BASE}x"></GameObject>\n{unit}'
    m = dataclasses.replace(parts.Mission(name='T', map=simsmall.island, scripts=[]),
                            units=[model.Unit(id=UNIT, xml=unit), model.Unit(id='CNVCacheHolder', xml=holder)])
    return simsmall.sim.Sim(m, model=False)


def test_two_worlds_overriding_one_template_each_read_their_own():
    retail = simunits.production(UNIT)
    first, second = _world(111, 1000), _world(222, 2000)
    assert simunits.production(UNIT, first.own) == (111, 0.0)
    assert simunits.production(UNIT, second.own) == (222, 0.0)
    assert simunits.production(BASE, first.own)[0] == 1000          # found inside another of the mission's files
    assert simunits.production(BASE, second.own)[0] == 2000
    assert simunits.production(UNIT) == retail != (111, 0.0)        # the SDK's own answer untouched by either
    assert simunits.production(BASE) == (0, 0.0)                     # nor taught the mission-only template
