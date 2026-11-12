"""Iron Curtain host-module controls, with the existing superweapon geometry."""
import os
import re

import labpaths
from missions import super_bench
from parts import Unit


def mission(mode):
    m = super_bench.mission('CampOcl' + mode.title())
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Structures',
                           'SovietSuperWeapon.xml'), encoding='utf-8-sig') as f:
        xml = f.read()
    ident = 'CNVOcl' + mode.title()
    xml = xml.replace('id="SovietSuperWeapon"', f'id="{ident}"', 1)
    pattern = r'<OCLSpecialPower\b[^>]*/>'
    modules = re.findall(pattern, xml, re.S)
    assert len(modules) == 1
    if mode == 'none':
        xml = re.sub(pattern, '', xml, flags=re.S)
    elif mode == 'wrong':
        xml = xml.replace(modules[0], modules[0].replace(
            'SpecialPowerIronCurtain', 'SpecialPowerVacuumBomb'))
    elif mode == 'empty':
        xml = xml.replace(modules[0], modules[0].replace(
            'OCL="OCL_IronCurtain"', 'OCL="CNVOclEmptyList"'))
        # AssetTypeObjectCreationList.xsd: every nugget has minOccurs=0.
        xml = xml.replace('</AssetDeclaration>',
                          '<ObjectCreationList id="CNVOclEmptyList" /></AssetDeclaration>')
    elif mode == 'copy':
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData',
                               'ObjectCreationLists.xml'), encoding='utf-8-sig') as f:
            lists = f.read()
        payload = re.search(r'<ObjectCreationList\s+id="OCL_IronCurtain"\s*>.*?'
                            r'</ObjectCreationList>', lists, re.S)
        assert payload is not None
        xml = xml.replace(modules[0], modules[0].replace(
            'OCL="OCL_IronCurtain"', 'OCL="CNVOclCopyList"'))
        xml = xml.replace('</AssetDeclaration>', payload.group(0).replace(
            'id="OCL_IronCurtain"', 'id="CNVOclCopyList"', 1) + '</AssetDeclaration>')
    m.units.append(Unit(ident, xml, what='Iron Curtain module control ' + mode))
    m.role('curtain').template = ident
    for obj in m.objects:
        if obj.name == m.role('curtain').name:
            obj.template = ident
    return m


MISSION = {'engine_oclcurtain': lambda: mission('valid'),
           'engine_oclcopy': lambda: mission('copy'),
           'engine_oclempty': lambda: mission('empty'),
           'engine_oclnone': lambda: mission('none'),
           'engine_oclwrong': lambda: mission('wrong')}
