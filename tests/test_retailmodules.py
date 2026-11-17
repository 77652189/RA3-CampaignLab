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


def test_substructure_storage_retail_probe_has_no_configured_payload_producer():
    """Configuration gate, not a runtime comparison: enabling a producer requires a new probe."""
    import xml.etree.ElementTree as ET

    storage = 'SubStructureStorageBehavior'
    state = rm._load()
    carriers = {name for name, _, _ in state['objs'].values()
                if any(t == storage for _, t, _ in rm.effective_modules(name))}
    assert carriers == {f'{side}MCV{suffix}' for side in ('Allied', 'Japan', 'Soviet')
                        for suffix in ('', '_Naval')}
    census = rm.module_census()
    assert (census['Behaviors', storage]['campaign'], census['Behaviors', storage]['templates']) == (6, 6)
    assert ('Behaviors', 'SubStructureBuild') not in census
    # Child-side modules survive in unused templates; their presence alone is not a producer.
    assert census['Behaviors', 'SubStructureBehavior']['templates'] == 11
    schema = ET.parse(os.path.join(rm.labpaths.SDK3, 'Schemas', 'xsd', 'Modules', storage + '.xsd'))
    xs = {'xs': 'http://www.w3.org/2001/XMLSchema'}
    extension = schema.find('.//xs:extension', xs)
    assert extension.get('base') == 'BehaviorModuleData'
    assert extension.findall('.//xs:attribute', xs) == []
    assert extension.findall('.//xs:element', xs) == []
    for side in ('Allied', 'Japan', 'Soviet'):
        source = os.path.join(rm.SAGEXML, side, 'Units', side + 'MCV.xml')
        root = rm._parse(source)
        modules = [n for n in root.iter() if rm._tag(n) == storage]
        assert len(modules) == 1
        assert modules[0].attrib == {'id': 'ModuleTag_SubStructureStorageBehavior'}
        assert list(modules[0]) == []
