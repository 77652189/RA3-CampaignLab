"""E-line SpecificUnitCap experiment on the existing skirmish scene.

All three builds run MEDIUM. The control has no extra cap; the other two
cap Peacekeepers at two for MEDIUM or HARD respectively. Only the difficulty
mask changes between the capped personalities. Evidence: work/re/e_aicap_e80.md.
"""
from missions.aiskirm_bench import mission as skirmish


def mission(mask=None):
    suffix = {'MEDIUM': 'Med', 'HARD': 'Hard', None: 'Ctrl'}[mask]
    m = skirmish('CampAICap' + suffix)
    m.facts['cap active'] = int(mask == 'MEDIUM')
    if mask is not None:
        pid = 'CNVCap' + suffix
        xml = '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset">',
            '  <Includes><Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml"/></Includes>',
            f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="1AlliedBalanced">',
            f'    <SpecificUnitCap Unit="AlliedAntiInfantryInfantry" Difficulty="{mask}" Cap="2"/>',
            '  </AIPersonalityDefinition>', '</AssetDeclaration>', ''])
        m.sides['s1']['aiPersonality'] = 'AIPersonalityDefinition:' + pid
        m.assets.append((pid + '.xml', xml, 'AIPersonalityDefinition:' + pid))
    return m


MISSION = {'aicapctrl': mission, 'aicapmed': lambda: mission('MEDIUM'),
           'aicaphard': lambda: mission('HARD')}
