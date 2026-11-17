"""WallBuilder configuration census and the isolated startup bench replay."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('wall_simbench', ROOT / 'experimental/cnv/simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


def test_wallbuilder_configuration_and_no_module_control():
    import retailmodules as rm
    from missions.wallbuilder_bench import wall

    state = rm._load()
    carriers = {name for name, _, _ in state['objs'].values()
                if any(t == 'WallBuilderBehavior' for _, t, _ in rm.effective_modules(name))}
    assert carriers == {side + 'Wall' + suffix for side in ('Allied', 'Japan', 'Soviet')
                        for suffix in ('Piece', 'SegmentPiece')}
    c = rm.module_census()['Behaviors', 'WallBuilderBehavior']
    assert (c['campaign'], c['templates']) == (6, 6)
    assert not any(t == 'WallBuilderBehavior' for _, t, _ in rm.effective_modules('BaseWallPiece'))
    for side in ('Allied', 'Japan', 'Soviet'):
        for suffix in ('Piece', 'SegmentPiece'):
            root = rm._parse(str(Path(rm.SAGEXML) / side / 'Structures' / (side + 'Wall' + suffix + '.xml')))
            obj = next(n for n in root if rm._tag(n) == 'GameObject')
            mod = next(n for n in obj.iter() if rm._tag(n) == 'WallBuilderBehavior')
            if suffix == 'Piece':
                assert obj.get('inheritFrom') == 'BaseWallPiece'
                assert mod.attrib == {'id': 'ModuleTag_WallBuilder', 'MaxNumSegments': '10'}
                filt = list(mod)[0]
                assert rm._tag(filt) == 'ConnectingObjectFilter' and filt.attrib == {'Rule': 'NONE'}
                assert [n.text for n in filt] == [side + 'WallPiece', side + 'WallSegmentPiece']
            else:
                assert obj.get('inheritFrom') == side + 'WallPiece'
                assert mod.attrib == {'id': 'ModuleTag_WallBuilder', 'StartInSecondaryModel': 'true'}
                assert list(mod) == []
    # Same source, parent and everything else: only the module differs.
    import re
    strip = lambda u: re.sub(r'<WallBuilderBehavior\b.*?</WallBuilderBehavior>', '',
                             u.xml.replace(u.id, 'CONTROL'), flags=re.S)
    assert strip(wall('hub')) == strip(wall('segment')) == strip(wall('none'))
    # Complete module-specific schema surface; defaults are data, not measured rules.
    import xml.etree.ElementTree as ET
    schema = ET.parse(str(Path(rm.labpaths.SDK3) / 'Schemas/xsd/Modules/WallBuilderBehavior.xsd'))
    ns = {'xs': 'http://www.w3.org/2001/XMLSchema'}
    ext = schema.find('.//xs:extension', ns)
    assert ext.get('base') == 'BehaviorModuleData'
    assert {n.get('name'): n.get('default') for n in ext.findall('xs:attribute', ns)} == {
        'MaxNumSegments': '5', 'SecondaryModelConditions': 'WALL_SEGMENT',
        'SecondaryObjectStatus': 'WALL_SEGMENT', 'StartInSecondaryModel': 'false'}
    assert [(n.get('name'), n.get('type')) for n in ext.findall('.//xs:element', ns)] == [
        ('ConnectingObjectFilter', 'ObjectFilter')]


def test_wallbuilder_startup_replays_named_bench_readings():
    """engine_wallinit:a, s1-s14: hub/segment/none = 10/11/10 (work/re/e_wallbuilder_e58.md)."""
    import build
    import sim
    m, t, _ = build.resolve('engine_wallinit', 'a')
    e = sim.Sim(m, t)
    readings = [tuple(row) for at, row in e.run(12).series if 2 <= at <= 12]
    assert readings and all(row == (10, 11, 10) for row in readings), readings
    assert e.body(m.role('segment').name).status == {'WALL_SEGMENT'}
    assert not e.body(m.role('none').name).status
    assert ('WallBuilderBehavior', 'CNVWallSegment') in e.unmodeled
    assert '建墙/连接' in e.unmodeled['WallBuilderBehavior', 'CNVWallSegment']['what']
