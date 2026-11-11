"""Reproducible containment coverage census; static data never grants bench credit.

Counts are the inventory's placed template kinds, not placement instances or
routes. Every template belongs to one complete effective-module signature.
"""
import collections
import json

import engineer_audit
import retailmodules as rm


def signature(element):
    """Keep all attributes/children; ignore XML namespace spelling and whitespace."""
    return (rm._tag(element), tuple(sorted(element.attrib.items())),
            (element.text or '').strip(), tuple(sorted(signature(c) for c in element)))


def audit():
    result = {}
    for kind in ('EngineerContain', 'InfiltratorContain'):
        raw = engineer_audit.audit(kind)
        groups = collections.defaultdict(list)
        for row in raw['rows']:
            key = tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in row['modules']))
            groups[key].append(row)
        forms = []
        for key, rows in sorted(groups.items()):
            forms.append(dict(signature=key, campaign=sum(bool(r['maps']) for r in rows),
                              templates=len(rows), rows=rows))
        census = rm.module_census()['Behaviors', kind]
        assert sum(f['campaign'] for f in forms) == census['campaign']
        assert sum(f['templates'] for f in forms) == census['templates']
        result[kind] = dict(campaign=census['campaign'], templates=census['templates'],
                            forms=forms, unresolved=raw['unresolved'],
                            skipped_parse=raw['skipped_parse'])
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
