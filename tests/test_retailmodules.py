"""experimental/cnv/retailmodules.py: the retail module / weapon-effect census behind the inventory (ADR 0026)."""
import importlib.util
import os

# loaded by file (guard G4: no new sys.path edits)
_spec = importlib.util.spec_from_file_location('retailmodules', os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experimental', 'cnv', 'retailmodules.py'))
rm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rm)


def test_module_census_shape():
    c = rm.module_census()
    assert c
    for (g, t), r in c.items():
        assert g in rm.GROUPS and t
        assert isinstance(r['templates'], int) and r['templates'] > 0
        assert isinstance(r['campaign'], int) and 0 <= r['campaign'] <= r['templates']


def test_includes_resolved():
    mods = rm.effective_modules('AlliedAntiVehicleVehicleTech1')
    assert any(g == 'Body' for g, _, _ in mods)
    # this module only comes in through an xi:include in the unit's Behaviors group
    assert ('Behaviors', 'AttributeModifierUpgrade', 'ModuleTag_HighTechnologyUpgrade') in mods
    assert rm.effective_modules('no_such_template') == []


def test_weapon_census():
    w = rm.weapon_census()
    assert w['DamageNugget']['weapons'] > 50
