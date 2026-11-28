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


def infiltrator_money_share(with_templates=False):
    """Coordinator's per-configuration closure: E193 measured transfer only.

    Income blocking, other hosts and exact entry clock remain explicit gaps.
    Match every field so other economic variants receive no bench credit.
    """
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="STEAL_MONEY" Amount="2000" BlockedDuration="30s"/>''')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_vehicle_share(with_templates=False):
    """E194 complete vehicle configuration; entry coverage does not close sight."""
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="VISION_UNITS" Duration="30s" UnitDuration="30s"
        ObjectRef="UnitVisionObserver" UnitFilter="InfiltrationVehicleObjectFilter"
        StructureFilter="InfiltrationVehicleStructuresFilter"/>''')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_aircraft_share(with_templates=False):
    """E197 aircraft signature; entry alone grants no observer/filter credit."""
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="VISION_UNITS" Duration="30s" UnitDuration="30s"
        ObjectRef="UnitVisionObserver" UnitFilter="InfiltrationAircraftObjectFilter"
        StructureFilter="InfiltrationAircraftStructuresFilter"/>''')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_infantry_share(with_templates=False):
    """E198 infantry signature; entry alone grants no observer/filter credit."""
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="VISION_UNITS" Duration="30s" UnitDuration="30s"
        ObjectRef="UnitVisionObserver" UnitFilter="InfiltrationInfantryObjectFilter"
        StructureFilter="InfiltrationInfantryStructuresFilter"/>''')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_ship_share(with_templates=False):
    """E200 ship signature; entry alone grants no observer/filter credit."""
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="VISION_UNITS" Duration="30s" UnitDuration="30s"
        ObjectRef="UnitVisionObserver" UnitFilter="InfiltrationShipObjectFilter"
        StructureFilter="InfiltrationShipStructuresFilter"/>''')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_kill_share(with_templates=False):
    """E205 complete KILL signature; entry readings do not grant effect credit."""
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="KILL" Amount="1.5" EvaEventForInfiltratedPlayer=""/>''')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_paralyze_share(with_templates=False):
    """E202 complete retail signature; credit requires named consumer replays."""
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="PARALYZE" Duration="30s" UnitFilter="InfiltrationParalyzeObjectFilter"/>''')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_port_share(with_templates=False):
    """E201 complete blocked-port signature; static matching grants no credit."""
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="VISION" Duration="-1s" BlockedDuration="9999999s"
        ObjectRef="VisionObserver"/>''')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_vision_share(with_templates=False):
    """E196 yard configuration; VISION timing and sibling RADAR_FREEZE stay gaps."""
    measured = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContain"
        Effect="VISION" Duration="-1s" ObjectRef="VisionObserver"/>''')
    radar = rm.ET.fromstring('''<InfiltratorContain id="ModuleTag_InfiltratorContainRadarFreeze"
        Effect="RADAR_FREEZE" Duration="60s"/>''')
    wanted = tuple(sorted((signature(measured), signature(radar))))
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def infiltrator_reset_share(with_templates=False):
    """E195 complete RESET configuration; entry does not prove cooldown reset."""
    measured = rm.ET.fromstring('<InfiltratorContain id="ModuleTag_InfiltratorContain" Effect="RESET"/>')
    wanted = (signature(measured),)
    rows = [r for r in engineer_audit.audit('InfiltratorContain')['rows']
            if tuple(sorted(signature(rm.ET.fromstring(m['xml'])) for m in r['modules'])) == wanted]
    share = dict(campaign=sum(bool(r['maps']) for r in rows), templates=len(rows))
    if with_templates:
        share['template_ids'] = [r['template'] for r in rows]
    return share


def attach_share(shape, with_templates=False):
    """Templates whose one AttachUpdate is engine/modules/attach.py's whole retail block `shape` ('TERROR', 'C4'),
    compared as the simulator does (its _native: Flags a set, C4's ForbiddenParentStatus free)."""
    from engine.modules import attach
    want, kids, keep = dict(TERROR=(attach.TERROR, attach.TERROR_KIDS, ()),
                            C4=(attach.C4, attach.C4_KIDS, ('ForbiddenParentStatus',)))[shape]

    def native(xml):
        el = rm.ET.fromstring(xml)
        for e in el.iter():
            e.tag = rm._tag(e)
        head = ' '.join(f'{k}="{v}"' for k, v in el.attrib.items())
        return attach._native(head, ''.join(rm.ET.tostring(c, encoding='unicode') for c in el), want, kids, keep)
    rows = [r for r in engineer_audit.audit('AttachUpdate')['rows']
            if len(r['modules']) == 1 and native(r['modules'][0]['xml']) is not None]
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
