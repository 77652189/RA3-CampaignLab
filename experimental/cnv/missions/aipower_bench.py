"""Engine probe: which protocol a skirmish AI buys with its point (PowerChoice lottery; checks/engine_aipower.py;
simtech.power_choices / Book.ai_buy). The island map and cast of protocol_bench (no units needed); the enemy (s1,
Soviet) is a computer player with starting point 1 (InitialTechPoints), its personality the probe's:
  aipwra  CNVPowerA: DefaultPersonality's children with ONE PowerChoice, X (PlayerTech_Soviet_MagneticSatellite_Rank_1,
          1 point, needs only PlayerTech_Soviet, which Soviet holds)
  aipwrb  CNVPowerB: two lines, Y (PlayerTech_Soviet_OrbitalRefuse_Rank1, Weight 0%) first, then X (100%)
  aipwrd  the stock DefaultPersonality (no PowerChoice at all): the model says it never buys
"""
from missions import scripts1_bench
from parts import Mission

X = 'PlayerTech_Soviet_MagneticSatellite_Rank_1'
Y = 'PlayerTech_Soviet_OrbitalRefuse_Rank1'
BASE = 'DefaultPersonality'


def personality_xml(pid, lines):
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
        *[f'    <PowerChoice PlayerPower="{p}" Weight="{w}"/>' for p, w in lines],
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, pid=None, lines=()):
    m = scripts1_bench.mission(name=name)
    m.cnv_power = lines
    if pid:
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Soviet', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((f'{pid}.xml', personality_xml(pid, lines), f'AIPersonalityDefinition:{pid}'))
    else:
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Soviet', 'aiPersonality': f'AIPersonalityDefinition:{BASE}'}
    return m


MISSION = {
    'aipwra': lambda: mission('CampAIPwrA', 'CNVPowerA', [(X, '100%')]),
    'aipwrb': lambda: mission('CampAIPwrB', 'CNVPowerB', [(Y, '0%'), (X, '100%')]),
    'aipwrd': lambda: mission('CampAIPwrD'),
}
