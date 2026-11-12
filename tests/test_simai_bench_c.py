"""C-line replays of named AI bench counters; evidence: work/re/c_release_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


@pytest.fixture(scope='module', params=['aialcloselo', 'aialclosehi'])
def alpha_close_rows(request):
    w = simai.run(request.param, 'a', until=66, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    return request.param, [(t, dict(zip(labels, values))) for t, values in w.sim.series]


def test_alpha_close_pair_has_only_one_changed_field():
    """Independent pair: the guard schedule, health hold and units are identical."""
    from missions.aialphaclose_bench import mission
    low, high = mission(False), mission(True)
    assert low.assets[0][1] == high.assets[0][1].replace(
        'AlphaStrikeTargetHealthPct="0.9"', 'AlphaStrikeTargetHealthPct="0.01"')
    assert low.objects == high.objects
    assert low.scripts == high.scripts


def test_alpha_close_arrives_with_target_at_seventy_percent(alpha_close_rows):
    """Named delayed-guard bench controls; this alone does not close AlphaStrike."""
    build, rows = alpha_close_rows
    assert any(row['到远厂'] == 4 and row['步兵数'] == 4 and row['目标血量'] == 70
               for t, row in rows if 17 <= t <= 29), build


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'Delayed-guard retail pair: low target HP59/home4/live4; high HP34/home0/live0. '
    'Model both HP64/home3/live3. Alpha target applicability needs B investigation; '
    'no model fit or inventory promotion. See work/re/handoff-c.md and '
    'work/re/c_alpha_close_report.md.'))
def test_alpha_close_replays_measured_outcome(alpha_close_rows):
    """Stable s39-55 bench plateaus; no exact dispatch-frame inference."""
    build, rows = alpha_close_rows
    expected = (59, 4, 4) if build == 'aialcloselo' else (34, 0, 0)
    plateau = [row for t, row in rows if 39 <= t <= 55]
    assert plateau
    assert {tuple(row[k] for k in ('目标血量', '步兵在家', '步兵数'))
            for row in plateau} == {expected}, (build, plateau)


@pytest.fixture(scope='module', params=['aimicupfast', 'aimicupslow'])
def micro_update_rows(request):
    build = request.param
    w = simai.run(build, 'a', until=56, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for _, values in w.sim.series]
    return build, rows


def test_micro_update_time_charge_and_survival(micro_update_rows):
    """Named micro-period pair; first skill and live units use the map clock."""
    build, rows = micro_update_rows
    charged = [r for r in rows if r['首冲帧'] > 0]
    print(build, 'first', charged[:1], 'final', rows[-1])
    assert charged, rows[-1]
    assert {r['首活'] for r in charged} == {2}
    assert max(r['造出'] for r in rows) >= 2


@pytest.mark.xfail(strict=True, reason='Micro UpdateTime-only pair: retail first-charge latch fast363/slow317, '
                  'model271/309; eligibility and update phase need B observations. '
                  'No fixed-delay inference or model fit. See work/re/handoff-c.md '
                  'and work/re/c_update_time_report.md.')
def test_micro_update_time_first_clock_replays_bench(micro_update_rows):
    """Assert the measured script latch, independent of capture wall time."""
    build, rows = micro_update_rows
    expected = 363 if build == 'aimicupfast' else 317
    seen = {r['首冲帧'] for r in rows if r['首冲帧']}
    assert seen == {expected}, (build, seen)


@pytest.mark.xfail(strict=True, reason='aiskirm:m replay has no populated Cleanup counter through 170s; '
                  'retail transfers defense 8 -> Cleanup 8. Named-team observation or release consumer '
                  'needs B investigation; no model change or inventory promotion. '
                  'See work/re/handoff-c.md and work/re/c_release_report.md.')
def test_release_to_priority_transfers_defense_without_a_pool_round_trip():
    """aiskirm:m: defense 8 -> 0, Cleanup 99 -> 8, pool peak 1 at transfer.

    This observes the stock DEFENSE -> STANDARD release path only. Other release
    modes and recruitment distance ordering remain gaps; no exact-second fit.
    """
    lib = simai.model()['xmldata'].Library()
    w = simai.run('aiskirm', 'm', until=170, lib=lib)
    labels = [label for _, label in w.sim.test.counters]
    rows = [(t, dict(zip(labels, values))) for t, values in w.sim.series]
    first = next((i for i, (_, row) in enumerate(rows) if row['清扫'] not in (0, 99)), None)
    observed = {label: sorted({row[label] for _, row in rows}) for label in labels}
    (brain,) = w.brains.values()
    assert first is not None, (observed, [e for e in brain.ai.teams.log if e[1] == 'go'])
    before, after = rows[first - 1][1], rows[first][1]
    assert (before['防御型'], before['清扫']) == (8, 99), rows[max(0, first - 2):first + 2]
    assert (after['防御型'], after['清扫']) == (0, 8), rows[max(0, first - 2):first + 2]
    assert after['池峰'] == 1
    assert any(row['池峰'] == 2 for _, row in rows[first:])


@pytest.mark.parametrize('build', ['aicr1', 'aicr3'])
@pytest.mark.xfail(strict=True, reason='CreateUnits slot recruitment/readiness is not consumed by B model; '
                  'retail aicr1:a has 3 owned Guardians, 2 home and 2 Peacekeepers home at s70, '
                  'while the model sends three Peacekeepers at wake and overproduces Guardians. '
                  'Named-team counters remain unknown. See work/re/handoff-c.md and work/re/c_create_report.md.')
def test_create_units_slot_replays_observed_counters(build):
    """Replay the dedicated CreateUnits check; exact counters, no timing fit.

    The two builds differ only in slot MinUnits. The opener supplies Guardians;
    this does not assert that CreateUnits manufactures them. Team identity and
    the exclusive-filter interpretation of UnitName remain unestablished.
    """
    w = simai.run(build, 'a', until=71, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [(t, dict(zip(labels, values))) for t, values in w.sim.series]
    at70 = next(row for t, row in rows if 70 <= t < 71)
    expected = (3, 2, 2) if build == 'aicr1' else (3, 0, 4)
    assert tuple(at70[k] for k in ('坦克总数', '坦克在家', '步兵在家')) == expected, at70
    if build == 'aicr1':
        assert any(row['坦克总数'] == 1 and row['坦克在家'] == 0 for _, row in rows)
    else:
        partial = [row for _, row in rows if row['坦克总数'] in (1, 2)]
        assert partial, 'the replay never exposed partial production'
        assert all(row['坦克总数'] == row['坦克在家'] for row in partial)


@pytest.mark.parametrize('build, expected', [('aisort0', (0, 1, 1)), ('aisort1', (1, 0, 2))])
def test_sort_by_distance_replays_named_departure(build, expected):
    """Fixed candidates, capacity one: compare identities, not departure totals.

    Named departure is indirect recruitment evidence. Dynamic team membership,
    the engine's distance metric and ties remain gaps (work/re/c_sort_report.md).
    Exact timing is intentionally not fitted to the engine's departure frame.
    """
    w = simai.run(build, 'a', until=36, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [(t, dict(zip(labels, values))) for t, values in w.sim.series]
    before = [row for t, row in rows if 1 <= t < 9]
    assert before
    assert all((row['远在原位'], row['近在原位'], row['首离身份']) == (1, 1, 0) for row in before)
    at35 = next(row for t, row in rows if 35 <= t < 36)
    assert tuple(at35[k] for k in ('远在原位', '近在原位', '首离身份')) == expected, at35
    assert at35['首离帧'] > 0


@pytest.mark.parametrize('build, home', [('aidist250', 1), ('aidist2000', 0)])
def test_tactic_distance_replays_displaced_guardian(build, home):
    """Observed s20/s65 endpoints only; aesthetics trajectory has a separate gap."""
    w = simai.run(build, 'a', until=67, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [(t, dict(zip(labels, values))) for t, values in w.sim.series]
    at20 = next(row for t, row in rows if 20 <= t < 21)
    at65 = next(row for t, row in rows if 65 <= t < 66)
    assert at20['圈900'] == 1, at20
    assert at65['曾出圈'] == 1, at65
    assert at65['坦克总数'] == 1, at65
    assert (at65['圈300'], at65['圈900']) == (home, home), at65


@pytest.mark.xfail(strict=True, reason='Distance 2000 retail leaves the 300 square before the push, '
                  're-enters the 900 square after displacement, then leaves it again. '
                  'B aesthetics stand-point selection is not replayed; endpoint agreement alone '
                  'does not close Distance. See work/re/handoff-c.md and work/re/c_distance_report.md.')
def test_tactic_distance_large_replays_observed_excursion():
    """Assert measured location transitions, independent of capture-clock seconds."""
    w = simai.run('aidist2000', 'a', until=76, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for _, values in w.sim.series]
    before = [row for row in rows if not row['曾出圈']]
    assert any((r['圈300'], r['圈900']) == (0, 1) for r in before), before[-3:]
    after = [row for row in rows if row['曾出圈']]
    transitions = []
    for row in after:
        pos = row['圈300'], row['圈900']
        if not transitions or pos != transitions[-1]:
            transitions.append(pos)
    assert transitions == [(0, 0), (0, 1), (0, 0)], transitions


@pytest.mark.parametrize('build', ['aiaeson', 'aiaesoff'])
def test_tactic_aesthetics_displacement_and_survival(build):
    """Both switch settings expose a successful displacement and one live tank."""
    w = simai.run(build, 'a', until=67, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    at65 = next(dict(zip(labels, values)) for t, values in w.sim.series if 65 <= t < 66)
    assert (at65['传送出圈'], at65['坦克总数']) == (1, 1), at65


@pytest.mark.parametrize('build', ['aiaeson', 'aiaesoff'])
@pytest.mark.xfail(strict=True, reason='Fixed Distance 2000 aesthetics pair: model stays outside after teleport; '
                  'retail enabled excursion / disabled return needs B stand-point and readiness investigation. '
                  'No timing or model fit. See work/re/handoff-c.md and work/re/c_aesthetics_report.md.')
def test_tactic_aesthetics_replays_named_location_transitions(build):
    """Compare ordered occupancy changes, without fitting capture seconds."""
    w = simai.run(build, 'a', until=76, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for _, values in w.sim.series]
    before = [row for row in rows if not row['传送出圈']]
    pre_positions = {(row['圈300'], row['圈900']) for row in before}
    expected_pre = {(1, 1), (0, 1)} if build == 'aiaeson' else {(1, 1)}
    assert pre_positions == expected_pre, pre_positions
    transitions = []
    for row in rows:
        if not row['传送出圈']:
            continue
        pos = row['圈300'], row['圈900']
        if not transitions or pos != transitions[-1]:
            transitions.append(pos)
    expected = [(0, 0), (0, 1), (0, 0)] if build == 'aiaeson' else [(0, 0), (0, 1), (1, 1)]
    assert transitions == expected, transitions
