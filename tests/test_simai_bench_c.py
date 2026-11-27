"""C-line replays of named AI bench counters; evidence: work/re/c_release_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


def test_engineer_pair_isolates_tactic_with_named_capture_candidate():
    """The experiment fixes candidates, geometry, micro and the wake clock."""
    from benches.ai.tactics.scenes import aiengineer_bench
    mission = aiengineer_bench()["shared"].mission
    engineer, control = mission(True), mission(False)
    assert engineer.assets[0][1].replace('Tactic="Engineer"', 'Tactic="SimpleAttack"') == control.assets[0][1]
    assert engineer.objects == control.objects
    assert engineer.scripts == control.scripts
    assert engineer.waypoints == control.waypoints
    candidates = [o for o in engineer.objects if o.template == 'AlliedEngineer']
    assert len(candidates) == 1
    assert candidates[0].name == engineer.cnv_named['engineer']


def test_never_release_pair_changes_only_release_type():
    """Fixed candidates, states, target and clock; only release policy changes."""
    from benches.ai.tactics.scenes import airelease_bench
    mission = airelease_bench()["shared"].mission
    never, priority = mission(True), mission(False)
    assert never.assets[0][1].replace('NEVER_RELEASE', 'RELEASE_TO_PRIORITY') == priority.assets[0][1]
    assert never.objects == priority.objects
    assert never.scripts == priority.scripts


def test_alpha_close_pair_has_only_one_changed_field():
    """Independent pair: the guard schedule, health hold and units are identical."""
    from benches.ai.tactics.scenes import aialphaclose_bench
    mission = aialphaclose_bench()["shared"].mission
    low, high = mission(False), mission(True)
    assert low.assets[0][1] == high.assets[0][1].replace(
        'AlphaStrikeTargetHealthPct="0.9"', 'AlphaStrikeTargetHealthPct="0.01"')
    assert low.objects == high.objects
    assert low.scripts == high.scripts


@pytest.mark.parametrize('high', [False, True])
def test_alpha_observer_preserves_the_measured_scenario(high):
    """Observe on the existing yard without changing any tactical or combat input."""
    from dataclasses import replace
    import labpaths
    from benches.ai.tactics.scenes import aialphaclose_bench
    mission = aialphaclose_bench()["shared"].mission
    from benches.ai.tactics.checks import engine_aialphaclose
    observe = engine_aialphaclose()["shared"].observe
    stock, observed = mission(high), mission(high, observe=True)
    assert observed.ext and not stock.ext
    assert len(observed.objects) == len(stock.objects)
    assert observed.assets == stock.assets
    assert observed.scripts == stock.scripts
    assert observed.waypoints == stock.waypoints
    assert observed.facts == stock.facts
    yard = stock.role('ai yard')
    assert [replace(o, template=yard.template) if o.name == yard.name else o
            for o in observed.objects] == stock.objects
    host, = observed.units
    original = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures' / (yard.template + '.xml')).read_text(encoding='utf-8')
    behavior = '\n  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>'
    assert host.xml.count(behavior) == 1
    assert host.xml.replace(behavior, '').replace(f'id="{host.id}"', f'id="{yard.template}"') == original
    assert observed.role('ai yard').template == observed.find(yard.name).template == host.id
    test = observe(observed)
    assert ('目标血量', 39, '==', 34 if high else 59, 55) in test.expect


@pytest.mark.parametrize('build', ['aialobslo', 'aialobshi'])
def test_alpha_observer_replays_measured_early_team_membership(build):
    """Earliest nonempty named-team sample, on the original shared logic frame (E99 / E101: 4 at f21). The
    personality side runs its states and teams from the first frame, not from the wake (bench aialobsw, B round
    161), so the model's team fills before the wake too."""
    w = simai_run.run(build, 'a', until=11, lib=simai.model()['xmldata'].Library(), record=True)
    brain, = w.brains.values()
    rows = [r for r in brain.rec['frames'] if r['frame'] == 21]
    assert len(rows) == 1, ('missing measured team at frame 21',
                            min((r['frame'] for r in brain.rec['frames']), default=None))
    assert len(rows[0]['members']) == 4


@pytest.mark.parametrize('build', ['aialobslo', 'aialobshi'])
def test_alpha_observer_forms_up_then_leaves_then_attacks(build):
    """E99 command log (work/re e99_compare.json, aialobslo): the SimpleAttack first forms up beside itself (f26 a
    formation move to 3601.6 / 3294.6, the members idle again one by one f48-f71), then the move to the target (f74),
    then state 6 (f230). The model (B round 194 form-up) runs the same order; its frames are the strict xfail below."""
    w = simai_run.run(build, 'a', until=16, lib=simai.model()['xmldata'].Library(), record=True)
    brain, = w.brains.values()
    first = {}
    for r in brain.rec['frames']:
        first.setdefault(r['phase'], r['frame'])
        if r['state'] == 6:
            first.setdefault('state 6', r['frame'])
    assert first['form'] < first['go'] < first['state 6'], first
    at_go, = [r for r in brain.rec['frames'] if r['frame'] == first['go']]
    centre_y = sum(m['pos'][1] for m in at_go['members']) / len(at_go['members'])
    assert abs(centre_y - 3294.6) < 25.0, centre_y


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'B round 200: E99 frames form f26 / go f74 / state 6 f230; the model since its form-up (model b830b09) form f2 / '
    'go f55 / state 6 f240 -- its team fills at f1 (bench f21) and the walk to state 6 takes 185 frames (bench 156); '
    'passed before only because the model had no form-up. Needs the bench members positions on the walk, not a '
    'constant.'))
@pytest.mark.parametrize('build', ['aialobslo', 'aialobshi'])
def test_alpha_observer_replays_measured_same_frame_state(build):
    """Assert the qualified observer reading on its original shared logic frame (E99: micro state 6 at f230; the
    model had 8 while its team formed only at the wake, right with the team filling before it)."""
    w = simai_run.run(build, 'a', until=16, lib=simai.model()['xmldata'].Library(), record=True)
    brain, = w.brains.values()
    row, = [r for r in brain.rec['frames'] if r['frame'] == 230]
    assert row['state'] == 6


def test_micro_update_time_pair_changes_only_micro_period():
    """Keep the measured pair independent of tactical clocks and scripted powers."""
    from benches.ai.tactics.scenes import aimicro_bench
    update_time = aimicro_bench()["shared"].update_time
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
    observed_fast = update_time('CampMicObsFast', 0.5, observe=True)
    observed_slow = update_time('CampMicObsSlow', 4, observe=True)
    assert not fast.ext and not slow.ext
    assert observed_fast.ext and observed_slow.ext
    assert observed_fast.units == observed_slow.units
    assert observed_fast.objects == observed_slow.objects
    assert observed_fast.scripts == fast.scripts == observed_slow.scripts
    assert observed_fast.assets == fast.assets
    assert observed_slow.assets == slow.assets
    hosts = [u for u in observed_fast.units if 'ModuleTag_CNVTeams' in u.xml]
    assert len(hosts) == 1
    assert 'MinFrames="15"' in hosts[0].xml


def test_release_eight_carrier_only_adds_passive_logging_to_existing_yard():
    import labpaths
    from missions.aiskirm_bench import mission
    m = mission(observe=True)
    # D round 105: the yard keeps its retail id (a renamed copy changed the AI: aiskxn vs aiskxo on check l)
    assert m.units == []
    (fname, xml, link), = m.assets
    assert link == 'GameObject:AlliedConstructionYard' and m.replaces == [link]
    original = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedConstructionYard.xml').read_text(encoding='utf-8')
    behavior = '\n  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>'
    assert xml.count(behavior) == 1 and xml.replace(behavior, '') == original
    assert m.ext
    assert len(m.objects) == 4
    assert {o.template for o in m.objects if 'Yard' in o.template} == {'AlliedConstructionYard'}
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


def test_release_eight_kept_pair_goes_to_the_capture_tech_team_with_its_new_engineer():
    """Where the two Cleanup left behind go (A round 190): AlliedCaptureTech_MEDIUM (Engineer tactic, CreateUnits
    AlliedEngineer 1, MaxUnits 4, NEVER_RELEASE) first appears, empty, in the same sample as Cleanup; the two stay
    in defense, unclaimed by Cleanup, until the team commits three at once -- a new id (the engineer, which carries
    IGNORES_SELECT_ALL and no CAN_ATTACK) and the kept pair."""
    import teamlog
    source = ROOT / 'tests/fixtures/c_release_teams/aiskirm_m.txt'
    capture = teamlog._wants('AlliedCaptureTech_MEDIUM_EngineerTactic_0_0')
    defense = teamlog._wants('LandDefense_MEDIUM_StaticDefense_0_0')
    seen = [(f, t) for f, teams in teamlog.samples(source) for t in teams if teamlog._named(t, capture)]
    assert seen[0][0] == 1966 and seen[0][1]['n'] == 0
    frame, first = next((f, t) for f, t in seen if t['n'])
    assert frame == 2206 and first['active'] == 1
    assert {m[0] for m in first['ids']} == {3171, 3172, 3181}
    kept = {f: {m[0] for t in teams if teamlog._named(t, defense) for m in t['ids']}
            for f, teams in teamlog.samples(source) if 1966 <= f <= 2206}
    assert all(ids == {3171, 3172} for f, ids in kept.items() if f < 2206), kept
    assert not kept[2206]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'The unique-yard carrier diagnostic measures defense 9 -> 2, Cleanup 0 -> 7; '
    'stock model predicts an entire eight-member transfer. The original eight-member '
    'scenario is not validated by this carrier. See work/re/handoff-c.md and '
    'work/re/c_release_eight_report.md.'))
def test_release_eight_named_model_replays_carrier_partial_transfer():
    """Assert the measured carrier result; do not change the stock model or clock."""
    before, after = _release_eight_transition()
    w = simai_run.run('aiskirmc', 'm', until=170, record=True, lib=simai.model()['xmldata'].Library())
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


def test_capture_tech_opens_with_the_cleanup_on_the_tech_building_share():
    """aiskirmc:m (C's live log, tests/fixtures/c_release_teams/aiskirm_m.txt): AlliedCaptureTech_MEDIUM's team is
    absent at f1951 and present (empty, inactive) at f1966, the same sample as BalancedCleanup's first team. Its
    TechBuildingShare (100%, Above false) reads simai's 'tech buildings' (own, all, players): the map's one
    neutral OilDerrick (KindOf NEUTRAL_TECH) owned by nobody -> share 0 -> on. Without the fact the state never
    opened (A round 191).
    The state can be drawn from the f1951 evaluation on (weight > 0, a target), the window's; which evaluation's
    weighted draw (~25 draws over ~15 equal candidates) takes it is the draw's: model 929e5a8 (the egg state takes no
    draw) moved it, seeds 1-6 made it f1952 / f1967 half and half (seed 1 f1967). One evaluation's slack, not the
    sample shared with Cleanup."""
    w = simai_run.run('aiskirmc', 'm', until=132, lib=simai.model()['xmldata'].Library())
    brain, = w.brains.values()
    own, total, players = brain.facts()['tech buildings']
    assert (own, total) == (0, 1) and players >= 2
    made = {}
    for frame, what, key, *_ in brain.ai.teams.log:
        if what == 'team':
            made.setdefault(key[0], frame)
    assert 1951 < made.get('AlliedCaptureTech_MEDIUM', 0) <= 1966 + brain.ai.states.every


def test_capture_tech_holds_two_escorts_out_of_the_cleanup():
    """aiskirmc:m (tests/fixtures/c_release_teams/aiskirm_m.txt, A round 193): Cleanup's first commit (f1966) leaves
    exactly two in defense -- the two lowest ids, held by AlliedCaptureTech_MEDIUM while it has no engineer (model
    teams.escort_count, INFERRED 2 = MaxUnits 4 - the CreateUnits slot's 1 + 1); the model's Cleanup commits at
    f1953. Only the hold at that commit is asserted: in the model the capture team expires at f2028 and Cleanup then
    takes the pair (retail keeps them held to f2206), and nobody builds the named engineer yet.
    A round 194: the team orders its engineer itself (model AIPlayer.order_wanted, D round 96's read of the team maker's missing-unit order) and,
    waiting for it, does not expire; at f2206 it has gone with the engineer and the same pair, as retail (3181,
    3172, 3171). The engineer was ordered once. Retail commits between f2191 and f2206 (its barracks made 3180,
    f1966-f2041, before the 10 s engineer); the model's barracks is idle at the order and it commits at f2116 -- the
    unit builder's draw upstream, not asserted. The AlliedScout teams are not asserted (A round 199): on this carrier
    (CNVSkirmTeamsYard) they never get a dog and defense keeps both, while on the stock yard, same head and hour, one
    takes a dog from defense at s72 (aiskirmc l / aiskirm l, bench 2026-11-13) -- the carrier changes them.
    A round 200: the pair held are the two lowest ids wherever they are (model teams.recruit, INFERRED) -- on stock
    aiskirm m Cleanup takes all of defense (8 -> 0 at s129) with both dogs in the scout teams. The simulator does not
    model the carrier's scouts, so here its scouts hold the dogs and the hold falls on them: asserted is the rule
    (the two lowest ids stay out of Cleanup's commit, and whoever of them was in defense stays there), not retail's
    two left in defense."""
    w = simai_run.run('aiskirmc', 'm', until=148, record=True, lib=simai.model()['xmldata'].Library())
    brain, = w.brains.values()
    rows = brain.rec['frames']
    first = next(r for r in rows if r['state_key'] == 'BalancedCleanup' and r['members'])
    left = [m['name'] for r in rows if r['state_key'] == 'LandDefense_MEDIUM' and r['frame'] == first['frame']
            and r['phase'] != 'done' for m in r['members']]

    def ids(names):                     # '#made <id> <template>'
        return sorted(int(n.split()[1]) for n in names)
    every = {m['name'] for r in rows if r['frame'] == first['frame'] and r['phase'] != 'done' for m in r['members']}
    low = ids(every)[:2]                # the hold: the two lowest ids wherever they are (A round 200)
    assert not set(low) & set(ids(m['name'] for m in first['members'])), (low, first['members'])
    assert set(ids(left)) <= set(low), (first['frame'], left, low)
    at = [r for r in rows if r['state_key'] == 'AlliedCaptureTech_MEDIUM' and r['frame'] == 2206]
    assert len(at) == 1 and at[0]['phase'] != 'done', at       # a tactic run's row: the team has gone
    got = [m['name'] for m in at[0]['members']]
    # the size is not asserted (A round 199): retail's pool held no free unit at its commit, the model's a Riptide
    # made the moment before, which the team takes -- whether retail would, that run cannot tell
    assert set(left) <= set(got) and sum(n.endswith(' AlliedEngineer') for n in got) == 1, (got, left)
    assert [e[2] for e in brain.ai.log if e[1] == 'team order'].count('AlliedEngineer') == 1
    gone = next(r['frame'] for r in rows if r['state_key'] == 'AlliedCaptureTech_MEDIUM' and r['members'])
    home = {}                           # frame -> names in defense
    for r in rows:
        if r['state_key'] == 'LandDefense_MEDIUM' and r['phase'] != 'done' and first['frame'] <= r['frame'] < gone:
            home.setdefault(r['frame'], set()).update(m['name'] for m in r['members'])
    assert (home or not left) and all(set(left) <= names for names in home.values()), gone
