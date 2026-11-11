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


def engineer_capture_share(allies=False, with_templates=False):
    """Exact generic (a/b/c/d) or three-engineer ALLIES (a/e/f) configuration.

    Match every field and child, so new filters or values stay in the gap.
    Counts use the same placed-template weight as module_census.
    """
    measured = rm.ET.fromstring('''<EngineerContain id="ModuleTag_EngineerContain"
        NameOfVoiceToUseForFriendlyEnter="VoiceEngineerRepair"
        NameOfVoiceToUseForHostileEnter="VoiceCaptureBuilding"
        EvaEventForRepair="BuildingRepaired" EvaEventForCapture="EnemyBuildingCaptured"
        FXForRepair="FX_Building_Repaired" FXForCapture="FX_Building_Captured"
        FXForCaptureAndReplace="FX_Building_Captured" ImmediatelyEnabled="true">
        <CanEnterFilter Rule="NONE"><IncludeThing>SovietEngineer</IncludeThing>
        <IncludeThing>JapanEngineer</IncludeThing><IncludeThing>AlliedEngineer</IncludeThing>
        </CanEnterFilter></EngineerContain>''')
    if allies:
        # a/e/f measure the entire three-engineer ALLIES filter. This form has
        # no capture EVA event; keep all other fields and children exact.
        measured.attrib.pop('EvaEventForCapture')
        measured.find('CanEnterFilter').set('Relationship', 'ALLIES')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit()['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_energy_share(with_templates=False):
    """ENERGY form closed by coordinator after retail a/b/c/d comparisons.

    This credits the form, not every power level or repeated infiltration.
    Match the complete module so different fields/filters remain gaps.
    """
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="ENERGY" Amount="0.2" ObjectRef="EnergyDisabler"
        StructureFilter="InfiltrationEnergyStructuresFilter"/>''')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


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
