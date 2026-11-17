"""Named CountModifier bench replay; original evidence: work/re/c_countmodifier_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


def measured():
    path = Path(simai.labpaths.WORK) / 're/c_countmodifier_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.mark.parametrize('build, expected', [('aicmhalf', [4, 5]), ('aicmfour', [7, 2])])
def test_count_modifier_original_readings(build, expected):
    rows = measured()[build]['rows']
    # Independent raw samples, without manufacturing an exact game frame.
    samples = [values for second, _, values in rows if 39 <= second <= 41]
    assert len(samples) >= 2
    assert all(values == expected for values in samples), samples


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build', ['aicmhalf', 'aicmfour'])
def test_count_modifier_named_bench_replay(build):
    rows = measured()[build]['rows']
    before = max((row for row in rows if row[0] <= 40), key=lambda row: row[0])
    after = min((row for row in rows if row[0] >= 40), key=lambda row: row[0])
    assert before[2] == after[2], (before, after)
    w = simai.run(build, 'a', until=41)
    samples = [values for second, values in w.sim.series if 40 <= second <= 41]
    assert samples and all(values == before[2] for values in samples), (samples, before, after)


# bench 2026-11-15 engine_countmodifier b (B round 206; CampCMHalfB_mcp_1115_143321 / CampCMFourB_mcp_1115_143201):
# (the copied unit, retail dogs, retail Javelins, retail Peacekeepers) at s66 -- with 1 Javelin placed at the start
BENCH_B = {'aicmhalf': ((2, 0, 1, 0), (5, 2, 3, 0)), 'aicmfour': ((4, 0, 1, 0), (7, 2, 4, 0))}
COST = {'aicmhalf': (300, 200, 300, 200), 'aicmfour': (200, 200, 300, 200)}
DEPOSIT = 2000                      # AlliedStandard's PRODUCTION Deposit, the only money PRODUCTION has in the opening


@pytest.mark.parametrize('build', sorted(BENCH_B))
def test_both_groups_stop_with_100_of_the_deposit_left(build):
    """The three-builds stop is the money: both spend 1900 of the Deposit and leave 100 with 200-cost units on offer
    (bench readings, no model)."""
    start, end = BENCH_B[build]
    spent = sum((e - s) * c for s, e, c in zip(start, end, COST[build]))
    assert spent == DEPOSIT - 100


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
def test_the_opening_deposit_never_pays_part_of_a_unit(monkeypatch):
    """aicmfour: the model's Deposit pays whole prices only (DEPOSIT_ONLY_PRICE_GATE) -- before, the fifth copied
    Peacekeeper took the last 100 (9/2 by s51). The rule, not the balance: what is left at the end depends on the
    retail barracks' mix (test_count_modifier_high_group_stops_after_three_builds, strict xfail); since the model's
    05d99e0 (a Husk target no longer falls back to a neutral object) that mix is 4 dogs + 2 Peacekeepers, all 200,
    and it spends the Deposit to 0 without a part payment (the bench's 2 dogs + 3 Javelins leave 100)."""
    player = simai.model()['player'].AIPlayer
    paid, spend = [], player.spend

    def record(self, account, cost):
        paid.append((account, cost))
        return spend(self, account, cost)
    monkeypatch.setattr(player, 'spend', record)
    w = simai.run('aicmfour', 'b', until=60)
    production = [c for a, c in paid if a == 'PRODUCTION']
    assert production and all(c in set(COST['aicmfour']) for c in production), production
    assert max(v[0] for _, v in w.sim.series) == 8


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.xfail(strict=True, reason='B206: bench aicmfour stays 7/2 s39-s66 -- the Deposit 2000 spent to 100 '
                   '(engine_countmodifier b: retail barracks 2 dogs + 3 Javelins = 1300, copied 3 Peacekeepers); the '
                   'model (price gate in) stops at 8/2 s45 with 100 left too, but its retail barracks buys 3 dogs + '
                   '1 Javelin + 1 Peacekeeper = 1100 -- the unit builder\'s mix, not CountModifier')
def test_count_modifier_high_group_stops_after_three_builds():
    rows = measured()['aicmfour']['rows']
    bench = {int(s): v for s, _, v in rows if 45 <= s <= 64}
    w = simai.run('aicmfour', 'a', until=65)
    model = {}
    for s, v in w.sim.series:
        model.setdefault(int(s), v)
    assert bench and all(model.get(s) == v for s, v in bench.items()), (bench, model)
