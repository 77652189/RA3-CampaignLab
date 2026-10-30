"""The plan's offline checks (experimental/cnv/offline.py) and the unit numbers they stand on (simunits)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'experimental', 'cnv'), os.path.join(ROOT, 'experimental', 'campaign')]
import offline  # noqa: E402
import simunits  # noqa: E402


def test_a_number_written_as_a_define_is_the_defines():
    """Most retail units see with ShroudClearingRange '=$STANDARD_SHROUD_CLEAR' (GlobalDefines: 500); read as a
    number it was missed, and every unit saw 200 (2026-10-29)."""
    assert simunits.number('<X ShroudClearingRange="=$STANDARD_SHROUD_CLEAR" />', 'ShroudClearingRange') == 500.0
    own = '<Defines><Define name="MY_HP" value="321" /></Defines><Body MaxHealth="=$MY_HP" />'
    assert simunits.number(own, 'MaxHealth') == 321.0
    assert simunits.number('<Body MaxHealth="=50000" />', 'MaxHealth') == 50000.0
    assert simunits.number('<Body VisionRange="200" />', 'VisionRange') == 200.0
    assert simunits.number('<Body />', 'VisionRange') is None
    assert simunits.stats('AlliedAntiVehicleVehicleTech1')['shroud'] == 500.0


def test_a4_offline():
    """A4's walkthrough wins and runs through the plan's four stages; the high-ground claims hold on sapporo; the
    fight model's numbers give the counters the plan leans on (the javelin beats the tsunami, the tank buster beats
    the guardian, the peacekeeper the tank buster)."""
    text, problems = offline.report('a4')
    assert '结局：赢' in text
    assert '段：会场 0:00，北营' in text and '布防' in text and '最后一程' in text
    assert not [p for p in problems if p.startswith('sight')], problems
    assert text.count('\n- 过 ') == 6 and '\n- 不对 ' not in text
    s, starts, enemy, have = offline.walk('a4')
    body = {}

    def b(t, owner):
        body[(t, owner)] = body.get((t, owner)) or s.add(f'#t {len(body)}', t, owner, 0.0, 0.0)
        return body[(t, owner)]
    javelin, tsunami = b('AlliedAntiVehicleInfantry', s.human), b('JapanAntiVehicleVehicleTech1', s.foe)
    guardian, buster = b('AlliedAntiVehicleVehicleTech1', s.human), b('JapanAntiVehicleInfantry', s.foe)
    peacekeeper = b('AlliedAntiInfantryInfantry', s.human)
    assert offline.ratio(s, javelin, tsunami) > 1
    assert offline.ratio(s, guardian, buster) < 1
    assert offline.ratio(s, peacekeeper, buster) > 1
