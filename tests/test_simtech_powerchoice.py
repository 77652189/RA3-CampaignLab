"""A computer player's protocol lottery (experimental/cnv/simtech.py Book.ai_buy): its personality's PowerChoice
lines, by weight, among the ones it may buy now; nothing without lines. Read from the program (engine line B round
60); where the draw falls (simtech.DRAW) from the bench (round 74, checks/engine_aipower.py)."""
import importlib.util
from pathlib import Path

import pytest

# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location(
    'simbench', Path(__file__).resolve().parent.parent / 'experimental' / 'cnv' / 'simbench.py')
_spec.loader.exec_module(importlib.util.module_from_spec(_spec))
import simtech  # noqa: E402

try:
    simtech._personalities()
except OSError:
    pytest.skip('the SDK SageXML is not on this computer', allow_module_level=True)


def test_lines_add_up_through_inheritance_parents_first():
    lines = simtech.power_choices('AIPersonalityDefinition:3AlliedSpecialForces', 'Allies')
    assert len(lines) == 15 + 4
    assert lines[0] == ('PlayerTech_Allied_AirPower', 1.0)
    assert lines[-1] == ('PlayerTech_Allied_HighTechnology', 3.0)


def test_an_unknown_personality_takes_its_factions_solo_base_lines():
    assert simtech.power_choices('AIP_A03_Soviet02BaseMarshall', 'Soviet') == \
        simtech.power_choices('SovietSoloBasePersonality', 'Soviet')
    assert simtech.power_choices(None, 'Japan')


def test_a_personality_without_lines_never_buys():
    b = simtech.Book('Soviet', 15, 'AIPersonalityDefinition:HuntPersonality')
    for f in range(0, 60):
        b.ai_buy(f)
    assert b.points == 1 and not b.log


def test_the_draw_takes_only_lines_it_may_buy_and_one_a_frame():
    b = simtech.Book('Allies', 15, '3AlliedSpecialForces')
    b.points = 3
    assert not b.ai_buy(9)                      # not before frame 10
    for f in range(10, 13):
        assert b.ai_buy(f)
    assert b.points == 0 and len(b.log) == 3
    keys = {p.lower() for p, _ in b.choices}
    bought = [w.split()[1].split('（')[0].lower() for _, w in b.log]
    assert all(k in keys for k in bought)


def test_the_draw_is_the_same_every_time_and_skips_a_zero_weight():
    b = simtech.Book('Allies', 15, 'Allies-test')
    b.choices = [('PlayerTech_Allied_SatelliteSweep', 0.0), ('PlayerTech_Allied_AirPower', 1.0),
                 ('PlayerTech_Allied_HighTechnology', 3.0)]
    b.can_buy = lambda name: True               # dependencies / ownership aside: the weights alone
    got = set()
    for i in range(20):
        b.points = 1
        b.log.clear()
        b.ai_buy(10)
        got.add(b.log[0][1])
    assert len(got) == 1 and 'AirPower' in got.pop()        # 0.2 x 4 = 0.8 falls in AirPower's 1


# ---- bench 2026-11-09 `cnv_check aipwr<k> a / e`, readings in experimental/cnv/checks/engine_aipower.py
@pytest.mark.parametrize('variant,bought', [
    ('aipwra', 'X'), ('aipwrb', 'X'), ('aipwrd', None),     # one line / Y 0% then X 100% / no PowerChoice
    ('aipwre', 'X'), ('aipwrf', 'Y'),                       # 50/50: the first listed, 7 runs of 7
    ('aipwrg', 'X'), ('aipwrh', 'Y')])                      # X 30% / Y 70% -> X; X 10% / Y 90% -> Y
def test_the_draw_buys_what_the_bench_bought(variant, bought):
    from missions import aipower_bench as ab
    m = ab.MISSION[variant]()
    b = simtech.Book('Soviet', 15, 'AIPersonalityDefinition:HuntPersonality')   # no lines of its own
    b.choices = [(p, simtech._weight(w)) for p, w in m.cnv_power]               # the probe personality's
    for f in range(0, 30):
        b.ai_buy(f)
    names = {'X': ab.X, 'Y': ab.Y}
    assert b.points == (1 if bought is None else 0)
    assert [w for _, w in b.log] == ([] if bought is None else [f'买 {names[bought]}（-1）'])
