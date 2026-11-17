"""Static EngineerContain placement and BridgeBuilder reference census.

No game execution. Campaign means placed template, not proven engineer entry.
"""
import collections
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'campaign')]
import labpaths
import retailmodules as rm


def audit(module_type='EngineerContain'):
    objects = {}
    skipped = []
    for path in sorted(Path(rm.SAGEXML).rglob('*.xml')):
        text = path.read_text(encoding='utf-8', errors='replace')
        if '<GameObject' not in text:
            continue
        root = rm._parse(str(path))
        if root is None:
            skipped.append(str(path.relative_to(rm.SAGEXML)))
            assert module_type not in text, path
            continue
        for obj in root.iter():
            if rm._tag(obj) != 'GameObject' or not obj.get('id'):
                continue
            key = obj.get('id').lower()
            if key in objects and 'CampaignOverrides' in str(path):
                continue
            modules = {}
            for group in obj:
                if rm._tag(group) == 'Behaviors':
                    for module in rm._group_modules(str(path), group):
                        modules[module.get('id') or module.get('ID') or ''] = module
            objects[key] = (obj.get('id'), (obj.get('inheritFrom') or '').lower(), modules)

    def effective(key, chain=()):
        assert key not in chain, (key, chain)
        if key not in objects:
            return {}
        _, parent, own = objects[key]
        return {**(effective(parent, chain + (key,)) if parent else {}), **own}

    placements = collections.defaultdict(collections.Counter)
    for path in sorted(Path(rm.RETAILREF).glob('*.json')):
        if path.name == 'index.json':
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        for obj in data.get('objects', []):
            if isinstance(obj, dict) and obj.get('t'):
                placements[obj['t'].lower()][path.stem] += 1
    assert placements and objects
    rows = []
    for key, (name, _, _) in sorted(objects.items()):
        modules = [m for m in effective(key).values() if rm._tag(m) == module_type]
        if not modules:
            continue
        rows.append(dict(template=name, maps=dict(placements[key]),
                         modules=[dict(attributes=dict(m.attrib),
                                       children=[rm._tag(c) for c in m],
                                       xml=rm.ET.tostring(m, encoding='unicode')) for m in modules]))
    bridge = [r for r in rows if any(m['attributes'].get('id') ==
              'ModuleTag_EngineerContainBridge' for m in r['modules'])]
    replace = [r for r in rows if any('ReplaceWith' in m['attributes'] or
               'ReplaceWith' in m['children'] for m in r['modules'])]
    bridge_keys = {r['template'].lower() for r in bridge}
    builders = []
    for key, (name, _, _) in sorted(objects.items()):
        for module in effective(key).values():
            if rm._tag(module) == 'BridgeBuilder' and module.get('GateHouse', '').lower() in bridge_keys:
                builders.append(dict(template=name, gatehouse=module.get('GateHouse'),
                                     maps=dict(placements[key])))
    return dict(kind='static placed-template reachability, not a bench comparison',
                templates=len(rows), campaign_templates=sum(bool(r['maps']) for r in rows),
                bridge_templates=len(bridge),
                bridge_campaign_templates=sum(bool(r['maps']) for r in bridge),
                bridge_placements=sum(sum(r['maps'].values()) for r in bridge),
                replacement_templates=len(replace),
                replacement_campaign_templates=sum(bool(r['maps']) for r in replace),
                bridge_builder_campaign_templates=sum(bool(r['maps']) for r in builders),
                bridge_builder_placements=sum(sum(r['maps'].values()) for r in builders),
                bridge_builders=builders,
                bridge=bridge, replacements=replace, rows=rows,
                # rm's parse counter may already contain a previous census;
                # this audit calls _parse directly and records its own skips.
                unresolved=dict(include=rm.unresolved['include'], parse=len(skipped)),
                skipped_parse=skipped)


if __name__ == '__main__':
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
