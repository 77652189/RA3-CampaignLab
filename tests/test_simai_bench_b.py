"""The skirmish AI on the plan simulator against bench probes no other test replays (B round 108): each test names the
probe (checks/engine_X.py) whose docstring holds the readings it asserts -- the bench's, never the simulator's own
expectation. Rules (who goes where, who first, counts at a time point, never / always), not exact seconds, unless the
simulator and the bench already agree. A reading the simulator misses is a strict xfail saying both numbers. Skipped
where ra3model.ai is not on this computer, as test_simai.py is. The counter readings now live in
experimental/cnv/checks/*.readings.toml (tests/conformance/test_readings.py); this file keeps the ones that read the
AI's internals."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental' / 'cnv' / 'simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


@pytest.fixture(scope='module')
def lib():
    return simai.model()['xmldata'].Library()


def _probe_run(build, lib, until, check='a'):
    """(world, rows): the probe's counters once a second, row i ~ second i+1, each row {label: value}."""
    w = simai.run(build, check, until, lib=lib)
    labels = [lab for _, lab in w.sim.test.counters]
    return w, [dict(zip(labels, v)) for _, v in w.sim.series]


def _vals(rows):
    """The rows as plain lists, in the probe's counter order (for probes whose labels are long)."""
    return [list(r.values()) for r in rows]


def _first_row(rows, key, pred=lambda v: v >= 1):
    return next((i for i, r in enumerate(rows) if pred(r[key])), None)


def test_a_level_personality_lists_our_units_in_a_build_state_of_its_own():
    """enemy_ai.personality(new_units=...) writes what aisknew2 benched (a ConstantHeuristic state, FEWEST_UNIT,
    the unit's file included): read by the engine model, the personality's build states list it with its
    CountModifier, and its AI orders it from an idle factory that makes it."""
    spec = importlib.util.spec_from_file_location('enemy_ai', ROOT / 'experimental' / 'cnv' / 'enemy_ai.py')
    enemy_ai = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(enemy_ai)
    m = simai.model()
    xml = enemy_ai.personality('CNVTestNew', '盟军', new_units={'CNVNewPK': 2})
    assert 'DATA:CNVUnits/Data/CNVNewPK.xml' in xml and 'UnitModifier' not in xml
    data = m['data'].AIData()
    data.add_text(xml.split('\n', 1)[1])
    states = {b.id: b for b in data.personality_build_states('CNVTestNew', 'MEDIUM')}
    assert states['CNVTestNewNew'].entries == [('CNVNewPK', 'FEWEST_UNIT')]
    assert states['CNVTestNewNew'].params[0]['CountModifier'] == '2'
    ai = m['player'].AIPlayer(data, 'CNVTestNew')
    made = []
    ai.builder = lambda t: made.append(t) or True
    ai.units = lambda ai, f: []
    ai.offers = lambda ai, f: [m['teams'].Offer('CNVNewPK', state=0, cost=200)]
    ai.accounts['PRODUCTION'] = 1000
    ai.tell(m['player'].Command('make base'))
    ai.tick(0)
    assert 'CNVNewPK' in made
    assert enemy_ai.new_units_state('x', None) == '' and 'BuildState' not in enemy_ai.personality('y', '盟军')


# ---- checks/engine_aiskirm.py z (bench 2026-11-11, readings in z's RESULTS): the barracks builds only the counter
@pytest.mark.parametrize('build, best, other', [('aiskvinf', 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'),
                                                ('aiskvveh', 'AlliedAntiVehicleInfantry', 'AlliedAntiInfantryInfantry')])
def test_the_expected_efficiency_ranks_the_counter_first(lib, build, best, other):
    """aiskvinf (the player owns 10 conscripts): bench Peacekeepers only; aiskvveh (10 Hammers): Javelins only.
    The simulator's expected efficiency (work/re/l4_efficiency.md: B/A with the unit over B/A without) ranks the
    same one first (the orders it gives: the two tests below) -- the barracks' first pick, made once the AI owns
    its dog. B round 228: asked at s25 instead (the AI owning nothing yet, no bench reading) the ranking is only
    the candidates' health once the Hammer counts its leech beam alone (MAGIC, 100% on both), and the
    Peacekeeper led there."""
    w = simai.run(build, 'z', 40, lib=lib)
    b = next(iter(w.brains.values()))
    # the player's map-placed war factory has its 3 repair drones (sim.py SpawnBehavior, Codex E 7b9bb57) and the
    # AI does not count them (SimAI.living; counted, nothing of the barracks hits them and the ranking flips)
    slaves = [x for x in w.sim.living() if getattr(x, 'spawn_parent', None) is not None]
    assert len(slaves) == 3 and not set(map(id, slaves)) & set(map(id, b.living())), slaves
    outs = [t for f, what, t in b.trace if what == 'out' and t in (best, other)]
    assert outs and outs[0] == best, outs


@pytest.mark.parametrize('build, best, other', [('aiskvd9', 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'),
                                                ('aiskvd0', 'AlliedAntiVehicleInfantry', 'AlliedAntiInfantryInfantry')])
def test_the_defensive_preference_turns_the_first_pick_against_tanks(lib, build, best, other):
    """aiskvd9 / aiskvd0 (aiskvveh's ten Hammers, only UnitBuilderOverallDefensivePreference 1000% / 0%): bench B199
    -- d9 维和 first (s30), 标枪 only from s151; d0 标枪 only. The first barracks pick after the dog (the AI owns only
    the dog then) turns on the two rules read in B rounds 225 / 227: K's time in frames (75 for a 5 s unit, not 5)
    and the template rate's weapons (one per slot, none needing an upgrade or an ObjectStatus: the Hammer counts
    its leech beam, 20 MAGIC, and not its gun). With either one alone d9 still builds a Javelin first."""
    w = simai.run(build, 'z', 40, lib=lib)
    b = next(iter(w.brains.values()))
    outs = [t for f, what, t in b.trace if what == 'out' and t in (best, other)]
    assert outs and outs[0] == best, outs


# the build states order by the expected efficiency (SimAI.efficiency, on by default since B round 131; set here so
# these two keep asserting it if the default is ever turned off): the barracks' counter
def test_against_tanks_the_barracks_builds_javelins(lib, monkeypatch):
    """aiskvveh (the player owns 10 Hammers): bench 标枪 14 by s185, 维和 0. The simulator (B round 129, the Land
    build state on once ObjectOfTypeExists Rule=ALL reads any enemy object): 标枪 12, 维和 1 (the unit builder's, s68,
    while the states order nothing) by s170."""
    monkeypatch.setattr(simai.SimAI, 'efficiency', True)
    _, rows = _probe_run('aiskvveh', lib, 170, 'z')
    assert rows[-1]['标枪总数'] >= 10 and rows[-1]['标枪总数'] >= 5 * rows[-1]['维和总数']


def test_against_conscripts_the_barracks_builds_no_javelin(lib, monkeypatch):
    """aiskvinf (the player owns 10 conscripts): bench 维和 7 by s164, 标枪 0 to s169. B round 129's strict xfail
    (sim 5 / 9, the Javelin ranked first) was the player's war factory drones in the AI's count (aircraft: only the
    Javelin hits them); without them (SimAI.living) the simulator builds no Javelin."""
    monkeypatch.setattr(simai.SimAI, 'efficiency', True)
    w, rows = _probe_run('aiskvinf', lib, 170, 'z')
    assert rows[-1]['维和总数'] >= 4
    # the bench's 标枪 0 split by source (B round 140): none from the build states; a Javelin the unit builder's
    # uniform draw gives (the model's s136 draw, seed 1) is luck -- the bench's draws here were dogs / an engineer
    log = [(k, t) for b in w.brains.values() for f, k, t in b.ai.log]
    assert ('state build', 'AlliedAntiVehicleInfantry') not in log
    assert rows[-1]['标枪总数'] == log.count(('produce', 'AlliedAntiVehicleInfantry'))


# the war factory (B round 132): an empty IFV held its passenger guns (slots 3-7 of its WeaponSetUpdate, one
# <Weapon Upgrade="Uprade_IFV_*"> line each: a 750-dps pistol, a 484-dps rifle ...), so the AI's expected efficiency
# put it at 7.6 vs conscripts (a Riptide 1.37) and the war factory built IFVs only, no Riptide. simunits.weapon_sets
# now reads Upgrade as a need (pick_weapons' upgrades; passengers granting it are not modelled)
def test_an_empty_ifv_holds_only_its_missiles():
    simunits = simai.simunits
    ws = simunits.weapon_sets('AlliedAntiAirVehicleTech1')
    held = [w.get('weapon_key') for w in simunits.pick_weapons(ws, set())]
    assert held == ['AlliedAntiAirVehicleTech1MissileGroundLauncher', 'AlliedAntiAirVehicleTech1MissileLauncher']
    shot = [w.get('weapon_key') for w in simunits.pick_weapons(ws, {'CONTAINER_OCCUPIED'}, {'Uprade_IFV_Shotgun'})]
    assert shot == ['AAAVT1_ShotgunWeapon']


def test_against_conscripts_the_war_factory_builds_riptides(lib, monkeypatch):
    """aiskvinf (z, bench 2026-11-11): 激流 1 s111 .. 6 s165. Three Riptides are a team's order (s101 in the
    simulator, the same in both builds); the other three are the amphibious build state's -- with the IFV fix its
    Riptide (1.16) outranks the IFV (1.04): 3 more by s169 (before: none, 4 IFVs). The war factory makes the land
    form AlliedAntiInfantryVehicle_Ground, which the probe's counter (AlliedAntiInfantryVehicle) does not count in
    the simulator: both forms are counted here."""
    monkeypatch.setattr(simai.SimAI, 'efficiency', True)
    w = simai.run('aiskvinf', 'z', 175, lib=lib)
    assert _riptides(w) >= 5


def _riptides(w):
    b = next(iter(w.brains.values()))
    return sum(1 for x in b.living() if x.owner == b.player
               and x.template in ('AlliedAntiInfantryVehicle', 'AlliedAntiInfantryVehicle_Ground'))


def test_against_tanks_only_the_teams_riptides(lib, monkeypatch):
    """aiskvveh (z, bench 2026-11-11): 激流 1 s112 .. 3 s133 against 10 Hammers, no more to s185 -- the team's three
    only; the build state's war factory pick is not a Riptide (simulator: the IFV 1.041 over the Riptide 1.019; the
    bench's z does not count IFVs)."""
    monkeypatch.setattr(simai.SimAI, 'efficiency', True)
    w = simai.run('aiskvveh', 'z', 175, lib=lib)
    assert _riptides(w) == 3


