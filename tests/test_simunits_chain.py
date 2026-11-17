"""The walk up a template's inheritFrom chain (simunits.xml_chain): a campaign override -- a GameObject that inherits
from its own id (CampaignOverrides.xml, or a mission's file patching a retail unit) -- is followed by the file of the
template's own name, not taken for the chain's end. Engine line B round 229: weapon_sets, declared_weapons,
simcoverage's declared_picks / inherited_text and simlevel.rules stopped at the override, so the Hammer and seven more
armed units read no weapon lines (the AI's efficiency and status-switched weapons lost) and ten units no veterancy."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    # loaded by file: the cnv modules put their folders on the path themselves (guard G4)
    spec = importlib.util.spec_from_file_location(name, ROOT / 'experimental' / 'cnv' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


simunits = sys.modules.setdefault('simunits', _load('simunits'))     # simlevel imports it by name
simlevel = _load('simlevel')

HAMMER = 'SovietAntiVehicleVehicleTech1'
SELF = f'<GameObject id="{HAMMER}" inheritFrom="{HAMMER}"></GameObject>'   # a mission file patching the Hammer


def _keys(weapons):
    return [w.get('weapon_key') for w in weapons]


def test_a_self_inheriting_override_reads_the_retail_weapons():
    own = {HAMMER: SELF}
    assert [t for t, _ in simunits.xml_chain(HAMMER, own)][:2] == [HAMMER, HAMMER]
    assert 'SovietAntiVehicleVehicleTech1CannonWeapon' in simunits.declared_weapons(HAMMER, own)
    ws = simunits.weapon_sets(HAMMER, own)
    assert ws is not None
    # the cannon is held under its toggle's status (its first state's, from the start), the leech beam without it
    assert _keys(simunits.pick_weapons(ws, {'GENERIC_TOGGLE_STATE'})) == ['SovietAntiVehicleVehicleTech1CannonWeapon']
    assert _keys(simunits.template_weapons(HAMMER, own)) == ['SovietAntiVehicleVehicleTech1LeechBeamWeapon']
    assert simlevel.rules(HAMMER, own)


def test_every_armed_campaign_override_reads_its_weapons():
    """The class, over the retail index: every template the index sends to a self-inheriting override whose own
    file declares a WeaponSetUpdate reads weapon lines through it (8 on 11-16)."""
    simunits._xml('')                              # loads the index
    armed = [k for k, v in simunits._index.items()
             if (v.get('inheritFrom') or '').lower() == k and 'WeaponSetUpdate' in simunits.retail_xml(k)]
    assert len(armed) >= 8
    assert [k for k in armed if not simunits.declared_weapons(k)] == []
    assert HAMMER.lower() in armed and simunits.weapon_sets(HAMMER) is not None
