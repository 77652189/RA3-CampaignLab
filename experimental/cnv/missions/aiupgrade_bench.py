"""C-line BuildEntry.Upgrade probe; stock Allied Tech2, with its refinery prerequisite preplaced.

The two personalities differ only in the presence of the constant Upgrade state. Retail tech entries
wait at least 180 seconds, beyond this probe. No MinTime is changed or tested here.
"""
from missions import aiskirm_bench


def personality(enabled):
    state = '''<AIBuildStateDefinition id="CNVCUpgradeBuild">
    <Heuristic><ConstantHeuristic/></Heuristic>
    <BuildEntry Upgrade="Upgrade_AlliedTech2" Heuristic="UPGRADE_TECH"/>
  </AIBuildStateDefinition>''' if enabled else ''
    link = ('<BuildState id="CNVCUpgradeBuild" State="CNVCUpgradeBuild" '
            'Difficulty="EASY MEDIUM HARD BRUTAL"/>') if enabled else ''
    return f'''<?xml version="1.0" encoding="utf-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Tags/>
  <Includes>
    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml"/>
  </Includes>
  {state}
  <AIPersonalityDefinition id="CNVCUpgrade" PersonalityType="CNVCUpgrade" inheritFrom="1AlliedBalanced">
    {link}
  </AIPersonalityDefinition>
</AssetDeclaration>
'''


def mission(enabled):
    m = aiskirm_bench.mission('CampCUpOn' if enabled else 'CampCUpOff', lib=False)
    m.facts['upgrade entry'] = int(enabled)
    m.sides['s1']['aiPersonality'] = 'AIPersonalityDefinition:CNVCUpgrade'
    m.assets.append(('CNVCUpgrade.xml', personality(enabled), 'AIPersonalityDefinition:CNVCUpgrade'))
    m.put('AlliedRefinery', 'east refinery', side='s1', role='upgrade prerequisite')
    m.put('AlliedPowerPlant', 'east base', -250, 250, side='s1', role='upgrade power')
    return m


MISSION = {'aicupgon': lambda: mission(True), 'aicupgoff': lambda: mission(False)}
