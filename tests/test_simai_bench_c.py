"""C-line replays of named AI bench counters; evidence: work/re/c_release_report.md."""
import importlib.util
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


def test_engineer_pair_isolates_tactic_with_named_capture_candidate():
    """The experiment fixes candidates, geometry, micro and the wake clock."""
    from missions.aiengineer_bench import mission
    engineer, control = mission(True), mission(False)
    assert engineer.assets[0][1].replace('Tactic="Engineer"', 'Tactic="SimpleAttack"') == control.assets[0][1]
    assert engineer.objects == control.objects
    assert engineer.scripts == control.scripts
    assert engineer.waypoints == control.waypoints
    candidates = [o for o in engineer.objects if o.template == 'AlliedEngineer']
    assert len(candidates) == 1
    assert candidates[0].name == engineer.cnv_named['engineer']


@pytest.mark.parametrize('build', ['aieng', 'aiengctl'])
def test_engineer_replays_observed_no_capture_without_claiming_recruitment(build):
    """Retail s1-63 / s1-74 plateau; shared absence does not prove a tactic."""
    w = simai.run(build, 'a', until=63, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [(t, dict(zip(labels, values))) for t, values in w.sim.series]
    observed = [row for t, row in rows if 1 <= t <= 62]
    assert observed
    assert {tuple(row[k] for k in ('目标归属', '到目标量', '工程师量', '目标血量'))
            for row in observed} == {(0, 0, 1, 100)}, build


def test_never_release_pair_changes_only_release_type():
    """Fixed candidates, states, target and clock; only release policy changes."""
    from missions.airelease_bench import mission
    never, priority = mission(True), mission(False)
    assert never.assets[0][1].replace('NEVER_RELEASE', 'RELEASE_TO_PRIORITY') == priority.assets[0][1]
    assert never.objects == priority.objects
    assert never.scripts == priority.scripts


@pytest.mark.parametrize('build', ['airelnever', 'airelprio'])
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'Legacy script-team counters remain unresolved: retail '
    'defense/attack counters 99/99, model 0/0. This does not establish release '
    'behavior. CNVTeams follow-up resolves actual membership; legacy script counters remain a naming gap. '
    'See work/re/handoff-c.md and work/re/c_never_release_report.md.'))
def test_never_release_named_team_observation_replays_bench(build):
    """Replay raw diagnostic readings; absent instances cannot prove retention."""
    w = simai.run(build, 'a', until=66, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [(t, dict(zip(labels, values))) for t, values in w.sim.series]
    for second in (25, 55, 65):
        row = next(row for t, row in rows if second <= t < second + 1)
        assert tuple(row[k] for k in ('防御人数', '进攻人数', '坦克总数', '曾防御量')) == (99, 99, 2, 0), (build, second, row)


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
    'E90 shares actual firing geometry with Alpha eligibility: high HP37/home0/live0; '
    'low remains HP64/home3/live3. Exact firing/retreat chronology still needs '
    'same-frame engine target/member/eligibility evidence. No threshold fitting or '
    'inventory promotion. See work/re/handoff-e.md and work/re/e_alpha_e90.md.'))
def test_alpha_close_replays_measured_outcome(alpha_close_rows):
    """Stable s39-55 bench plateaus; no exact dispatch-frame inference."""
    build, rows = alpha_close_rows
    expected = (59, 4, 4) if build == 'aialcloselo' else (34, 0, 0)
    plateau = [row for t, row in rows if 39 <= t <= 55]
    assert plateau
    assert {tuple(row[k] for k in ('目标血量', '步兵在家', '步兵数'))
            for row in plateau} == {expected}, (build, plateau)


@pytest.mark.parametrize('alpha_close_rows', ['aialclosehi'], indirect=True)
def test_alpha_close_high_replays_measured_no_survivors(alpha_close_rows):
    """Measured high-threshold counts only; exact target HP remains a separate gap."""
    build, rows = alpha_close_rows
    assert build == 'aialclosehi'
    plateau = [row for t, row in rows if 39 <= t <= 55]
    assert plateau
    assert {(row['步兵在家'], row['步兵数']) for row in plateau} == {(0, 0)}


@pytest.fixture(scope='module', params=['aimicupfast', 'aimicupslow'])
def micro_update_rows(request):
    build = request.param
    w = simai.run(build, 'a', until=56, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for _, values in w.sim.series]
    return build, rows


def test_micro_update_time_pair_changes_only_micro_period():
    """Keep the measured pair independent of tactical clocks and scripted powers."""
    from missions.aimicro_bench import update_time
    fast, slow = update_time('CampMicUpFast', 0.5), update_time('CampMicUpSlow', 4)
    assert len(fast.assets) == len(slow.assets)
    changed = 0
    for (path, text, key), (other_path, other_text, other_key) in zip(fast.assets, slow.assets):
        assert (path, key) == (other_path, other_key)
        if text != other_text:
            changed += 1
            assert text.count('UpdateTime="0.5s"') == 1
            assert other_text.count('UpdateTime="4s"') == 1
            assert text == other_text.replace('UpdateTime="4s"', 'UpdateTime="0.5s"')
    assert changed == 1
    assert fast.objects == slow.objects
    assert fast.scripts == slow.scripts
    assert fast.waypoints == slow.waypoints


def test_micro_update_time_charge_and_survival(micro_update_rows):
    """Named micro-period pair; first skill and live units use the map clock."""
    build, rows = micro_update_rows
    charged = [r for r in rows if r['首冲帧'] > 0]
    print(build, 'first', charged[:1], 'final', rows[-1])
    assert charged, rows[-1]
    assert {r['首活'] for r in charged} == {2}
    assert max(r['造出'] for r in rows) >= 2


@pytest.mark.xfail(strict=True, reason='Micro UpdateTime-only pair: retail first-charge latch fast363/slow317, '
                  'model271/309; both model fires use the low-health branch outside charge distance. '
                  'Health eligibility and micro state/order updates need B observations. '
                  'See work/re/handoff-c.md and work/re/c_update_model_report.md.')
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


def test_release_eight_carrier_only_adds_passive_logging_to_existing_yard():
    import labpaths
    from missions.aiskirm_bench import mission
    m = mission(observe=True)
    carrier, = m.units
    original = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedConstructionYard.xml').read_text(encoding='utf-8')
    behavior = '\n  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>'
    assert carrier.xml.count(behavior) == 1
    assert carrier.xml.replace(behavior, '').replace('id="CNVSkirmTeamsYard"', 'id="AlliedConstructionYard"') == original
    assert carrier.id == 'CNVSkirmTeamsYard' and m.ext
    assert len(m.objects) == 4
    stock = mission()
    assert stock.units == [] and not stock.ext


def _release_eight_transition():
    import teamlog
    source = ROOT / 'tests/fixtures/c_release_teams/aiskirm_m.txt'
    defense = teamlog._wants('LandDefense_MEDIUM_StaticDefense_0_0')
    cleanup = teamlog._wants('BalancedCleanup_SimpleAttack_0_0')
    previous = None
    for frame, teams in teamlog.samples(source):
        defenders = [t for t in teams if teamlog._named(t, defense) and t['active'] and t['n']]
        attackers = [t for t in teams if teamlog._named(t, cleanup) and t['n'] > 0]
        if attackers:
            assert previous is not None and len(attackers) == 1
            return previous, (frame, defenders, attackers[0])
        previous = frame, defenders
    pytest.fail('No populated retail Cleanup team in recorded samples')


def test_release_eight_carrier_diagnostic_records_partial_transfer():
    before, after = _release_eight_transition()
    frame, defenders = before
    next_frame, remaining, cleanup = after
    assert (frame, next_frame) == (1951, 1966)
    assert next_frame - frame == 15
    assert len(defenders) == 1
    defense, = defenders
    assert defense['active'] == 1 and defense['n'] == 9
    assert cleanup['active'] == 1 and cleanup['n'] == 7
    original = {m[0] for m in defense['ids']}
    assert original == set(range(3171, 3180))
    assert {m[0] for m in cleanup['ids']} == set(range(3173, 3180))
    assert len(remaining) == 1 and remaining[0]['active'] == 1 and remaining[0]['n'] == 2
    assert {m[0] for m in remaining[0]['ids']} == {3171, 3172}


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'The unique-yard carrier diagnostic measures defense 9 -> 2, Cleanup 0 -> 7; '
    'stock model predicts an entire eight-member transfer. The original eight-member '
    'scenario is not validated by this carrier. See work/re/handoff-c.md and '
    'work/re/c_release_eight_report.md.'))
def test_release_eight_named_model_replays_carrier_partial_transfer():
    """Assert the measured carrier result; do not change the stock model or clock."""
    before, after = _release_eight_transition()
    w = simai.run('aiskirmc', 'm', until=170, record=True, lib=simai.model()['xmldata'].Library())
    brain, = w.brains.values()
    rows = brain.rec['frames']
    first = next((r for r in rows if r['state_key'] == 'BalancedCleanup' and r['members']), None)
    assert first is not None
    defenders = [r for r in rows if r['state_key'] == 'LandDefense_MEDIUM'
                 and r['frame'] < first['frame'] and r['members']]
    assert defenders, 'No populated model defense before Cleanup'
    defense = defenders[-1]
    original = {m['name'] for m in defense['members']}
    assert len(original) == before[1][0]['n'] == 9, (first['frame'], sorted(original))
    transferred = {m['name'] for m in first['members']}
    assert len(transferred) == after[2]['n'] == 7
    assert transferred < original
    retained = [r for r in rows if r['state_key'] == 'LandDefense_MEDIUM'
                and r['frame'] == first['frame'] and r['phase'] != 'done']
    assert {m['name'] for r in retained for m in r['members']} == original - transferred
    activated = next(r for r in rows if r['run'] == first['run'] and r['phase'] == 'go')
    assert {m['name'] for m in activated['members']} == transferred


@pytest.mark.parametrize('build', ['aicr1', 'aicr3'])
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'CreateUnits membership/activation now replay, but s70 production remains four Guardians '
    'instead of retail three (one extra at home in both builds). Production consumer remains '
    'a separate B gap; see work/re/handoff-e.md and work/re/e_create_e88.md.'))
def test_create_units_slot_replays_observed_counters(build):
    """Replay the dedicated CreateUnits check; exact counters, no timing fit.

    The two builds differ only in slot MinUnits. The opener supplies Guardians;
    this does not assert that CreateUnits manufactures them. Team identity and
    the exclusive-filter interpretation of UnitName were unestablished by this
    original counter probe; the c variants below add direct member observations.
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


def _create_units_observation(build):
    """Selected complete engine samples; pointer fields removed, values unchanged."""
    import teamlog
    rows = teamlog.samples(ROOT / 'tests/fixtures/c_create_teams' / (build + '.txt'))
    return [(frame, next(t for t in teams if t['names'][1] == '7203be5f_SimpleAttack_0_0'))
            for frame, teams in rows]


@pytest.mark.parametrize('build, expected', [
    ('aicr1c', [(31, 0, 0), (316, 3, 1)]),
    ('aicr3c', [(31, 0, 0), (316, 1, 0), (481, 2, 0), (646, 3, 1)]),
])
def test_create_units_engine_team_samples(build, expected):
    """Assert logged counts/active bits; exact conversion lies between samples."""
    rows = _create_units_observation(build)
    changes = []
    for frame, team in rows:
        assert len(team['ids']) == team['n']
        state = (team['n'], team['active'])
        if not changes or state != changes[-1][1:]:
            changes.append((frame, *state))
    assert changes == expected
    assert {i for i, _, _ in rows[-1][1]['ids']} == (
        {3176, 3166, 3167} if build == 'aicr1c' else {3176, 3177, 3178})


@lru_cache(maxsize=2)
def _create_units_team_go(build):
    w = simai.run(build, 'a', until=45, lib=simai.model()['xmldata'].Library())
    brain, = w.brains.values()
    return next(e for e in brain.ai.teams.log if e[1] == 'go' and e[2][0] == 'CNVStateTF')


@pytest.mark.parametrize('build', ['aicr1c', 'aicr3c'])
def test_create_units_replays_observed_activation_interval(build):
    rows = _create_units_observation(build)
    first = next(i for i, (_, team) in enumerate(rows) if team['active'])
    assert rows[first - 1][0] < _create_units_team_go(build)[0] <= rows[first][0]


@pytest.mark.parametrize('build', ['aicr1c', 'aicr3c'])
def test_create_units_replays_observed_first_members(build):
    # Initial Peacekeeper IDs are fixed by their placed positions; new Guardian
    # attribution uses the isolated opener and total counters (INFERRED).
    expected = ['AlliedAntiVehicleVehicleTech1'] * (1 if build == 'aicr1c' else 3)
    if build == 'aicr1c':
        expected += ['AlliedAntiInfantryInfantry'] * 2
    assert Counter(_create_units_team_go(build)[3]) == Counter(expected)


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


@pytest.mark.parametrize('build, expected_before, expected_after', [
    ('aidist250', [(1, 1)], [(0, 0), (0, 1), (1, 1)]),
    pytest.param('aidist2000', [(1, 1), (0, 1)], [(0, 0), (0, 1), (0, 0)],
                 marks=pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
                     'Distance 2000 stand-point selection is unresolved: retail leaves the 300 square '
                     'before displacement, returns to the 900 square, then leaves again. '
                     'Same-frame stand-point, order source and readiness observations are missing; '
                     'endpoint agreement does not close Distance. See work/re/e_distance_e91.md.'))),
])
def test_tactic_distance_replays_observed_excursion(build, expected_before, expected_after):
    """Assert measured location transitions, independent of capture-clock seconds."""
    w = simai.run(build, 'a', until=76, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for _, values in w.sim.series]
    # Original retail sequences: work/re/c_distance_report.md and the two
    # aidist*__a.json recordings. Keep displacement and survival in every row.
    assert rows
    assert all(row['坦克总数'] == 1 for row in rows)
    for displaced, expected in ((False, expected_before), (True, expected_after)):
        transitions = []
        for row in rows:
            if bool(row['曾出圈']) != displaced:
                continue
            pos = row['圈300'], row['圈900']
            if not transitions or pos != transitions[-1]:
                transitions.append(pos)
        assert transitions == expected, (build, displaced, transitions)


@pytest.mark.parametrize('build', ['aiaeson', 'aiaesoff'])
def test_tactic_aesthetics_displacement_and_survival(build):
    """Both switch settings expose a successful displacement and one live tank."""
    w = simai.run(build, 'a', until=67, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    at65 = next(dict(zip(labels, values)) for t, values in w.sim.series if 65 <= t < 66)
    assert (at65['传送出圈'], at65['坦克总数']) == (1, 1), at65


@pytest.mark.parametrize('build', [
    pytest.param('aiaeson', marks=pytest.mark.xfail(strict=True, reason=(
        'Enabled aesthetics stand-point selection remains unresolved; disabled return now replays. '
        'Exact random stream and stand-point observations are missing. See work/re/e_aesthetics_e89.md.'))),
    'aiaesoff',
])
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


@pytest.mark.parametrize('build', ['airelnever', 'airelprio'])
def test_never_release_engine_members_and_model_replay(build):
    """Same retail member IDs first defend, then stay/transfer; no HUD-name inference."""
    import teamlog
    source = ROOT / 'tests/fixtures/c_release_teams' / (build + '.txt')
    defense = 'CNVStateTF_StaticDefense'
    attack = 'CNVReleaseAttack_SimpleAttack'
    initial = teamlog.members(source, defense, 301)
    assert len(initial) == 1 and {m[0] for m in initial[0]} == {3166, 3167}
    never = build == 'airelnever'
    for frame in (601, 976):
        assert teamlog.team_sizes(source, defense if never else attack, frame) == [2]
        # Empty instances are periodically removed; absence is not the primary evidence.
        assert teamlog.team_sizes(source, attack if never else defense, frame) in ([], [0])
        held = teamlog.members(source, defense if never else attack, frame)
        assert {m[0] for m in held[0]} == {3166, 3167}
        teams = teamlog.at(source, frame)
        actual = [t for t in teams if t['names'][1].lower().startswith(teamlog._hashed(defense if never else attack))]
        assert len(actual) == 1 and actual[0]['active'] == 1
    w = simai.run(build, 'a', until=66, record=True, lib=simai.model()['xmldata'].Library())
    brain, = w.brains.values()
    original = {'UNIT - CNV AI Tank 1', 'UNIT - CNV AI Tank 2'}
    for frame in (301, 601, 976):
        observed = {state: set() for state in ('CNVStateTF', 'CNVReleaseAttack')}
        for row in brain.rec['frames']:
            if row['frame'] == frame and row['phase'] != 'done':
                observed[row['state_key']].update(m['name'] for m in row['members'])
        destination = 'CNVStateTF' if frame == 301 or never else 'CNVReleaseAttack'
        assert observed[destination] == original
        assert observed['CNVReleaseAttack' if destination == 'CNVStateTF' else 'CNVStateTF'] == set()
