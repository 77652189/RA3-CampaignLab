"""Rule tests of the skirmish AI's build states that a reading cannot hold: a personality written by enemy_ai,
and an empty IFV's weapons. The bench readings of engine_aiskirm z (aiskvinf / aiskvveh / aiskvd9 / aiskvd0) are
in experimental/cnv/checks/engine_aiskirm.readings.toml (tests/conformance/test_readings.py)."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental' / 'cnv' / 'simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


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
