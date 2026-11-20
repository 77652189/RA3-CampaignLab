"""One open recruitment slot, a Guardian in pre-attack, and an idle fallback."""

from dataclasses import replace
from pathlib import Path
import re

import labpaths
from missions.aicombat_bench import mission as combat_mission
from missions.aiteamfilter_bench import TANK
from missions.aiteams_bench import HOST, host_unit
from parts import Script, Unit


FIGHTER = 'CNVK2Guardian'
PRE_ATTACK = 60
ORDER_AT = 2.0


def pre_attack_guardian():
    sage = Path(labpaths.SDK3) / 'SageXML'
    cannon = TANK + 'Cannon'
    marker = FIGHTER + 'Cannon'
    xml = (sage / 'Allied' / 'Units' / f'{TANK}.xml').read_text(encoding='utf-8')
    xml = xml.replace(f'id="{TANK}"', f'id="{FIGHTER}"')
    xml = xml.replace(f'EditorName="{TANK}"', f'EditorName="{FIGHTER}"')
    xml = xml.replace(f'Template="{cannon}"', f'Template="{marker}"')
    weapons = (sage / 'GlobalData' / 'Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(rf'<WeaponTemplate\s+id="{cannon}".*?</WeaponTemplate>', weapons, re.S).group()
    assert '<PreAttackDelay' not in weapon and 'AttackRange="150.0"' in weapon
    weapon = weapon.replace(f'id="{cannon}"', f'id="{marker}"')
    pre_attack = f'<PreAttackDelay MinSeconds="{PRE_ATTACK}s" MaxSeconds="{PRE_ATTACK}s"/>'
    weapon = weapon.replace('<FiringDuration', pre_attack + '\n\t\t<FiringDuration')
    return Unit(FIGHTER, xml.replace('</AssetDeclaration>', weapon + '\n</AssetDeclaration>'),
                link=[f'WeaponTemplate:{marker}'], what='守护者探针，主炮预瞄 60 秒')


def mission(allow):
    m = combat_mission(allow)
    m.name = f'CampK2Gate{int(allow)}'
    m.ext = True
    m.units += [pre_attack_guardian(), host_unit()]
    m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
    fighter = m.role('candidate fighter').name
    foe = m.role('player foe').name
    m.find(fighter).template = FIGHTER
    m.cast['candidate fighter'] = replace(m.role('candidate fighter'), template=FIGHTER)
    # With no return fire, a 100% foe health sample is a clean no-hit check.
    m.scripts = [script for script in m.scripts if script.name != 'CNV Combat - hold health']
    m.scripts.append(Script('CNV K2 - passive target', [], [('UNIT_CHANGE_OBJECT_STATUS', foe, 'NO_ATTACK', 1)]))
    m.facts |= {'order at': ORDER_AT, 'pre-attack': PRE_ATTACK}
    return m


MISSION = {'k2gate0': lambda: mission(False), 'k2gate1': lambda: mission(True)}
