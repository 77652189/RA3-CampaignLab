"""The 时停区 device (devices/stasis.py), its object (units/stasis_zone.py) and A3 格林尼治时差, the level it was made for:
the object is the engine line's probe unit (checks/engine_stasis.py, measured on the bench), the rings are made and
taken away by script, and the plan's rings are in the order the plan says."""
import pytest
from test_plans import small  # (puts experimental/cnv on the path)  # noqa: F401, I001
import build  # noqa: E402
import parts  # noqa: E402
from checks import a3, engine_stasis  # noqa: E402
from devices import stasis  # noqa: E402
from plantime import PlanError  # noqa: E402
from units import stasis_zone  # noqa: E402


def test_the_unit_is_the_probes_unit():
    """units/stasis_zone.py is a copy of the zone the engine probe measured: a change to one is a change to the other."""
    for kw in ({}, dict(radius=450.0), dict(id='CNV_X', radius=45.0, hold='2s', refresh='0.5s', include='VEHICLE')):
        a, b = engine_stasis.zone(**kw), stasis_zone.zone(**kw)
        assert a.xml == b.xml and a.link == b.link


def test_a_ring_is_made_by_script_and_taken_by_script():
    m, t, _ = build.resolve('a3', 'freeze')
    mm = parts.merged(m, t)
    assert parts.contract(mm) == []
    key = stasis.key_of('时停区')
    made = [s for s in mm.scripts if f' - {key} ring ' in s.name and s.name.endswith(' on')]
    assert len(made) == 5
    creates = [[a for a in s.do if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT'] for s in made]
    assert [len(c) for c in creates] == [4, 4, 4, 1, 4]                      # circles per ring, as the plan lists them
    assert {a[2] for c in creates for a in c} == {stasis_zone.zone(id='CNV_A3StasisZone', radius=450).id}
    names = [a[1] for c in creates for a in c]
    assert len(set(names)) == len(names)                                      # one object name per circle


def test_the_checks_spelling_of_a_ring_flag_is_the_devices():
    for k in range(5):
        assert a3.ring_flag(k) == stasis.ring_flag('A3', '时停区', k)


def test_bad_specs():
    class Ctx:
        tag = 'T'

        def side(self, who):
            return 's1'

        def spawns_add(self, *templates):
            pass
    for spec in ({}, {'圈': []}, {'圈': [{'名': 'a'}]}, {'圈': [{'名': 'a', '地点': ['x']}, {'名': 'a', '地点': ['y']}]}):
        with pytest.raises(PlanError):
            stasis.Stasis(Ctx(), 'z', spec)
