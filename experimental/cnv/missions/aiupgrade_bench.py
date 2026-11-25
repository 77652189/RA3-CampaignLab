"""C-line BuildEntry.Upgrade probe; stock Allied Tech2, with its refinery prerequisite preplaced.

The two personalities differ only in the presence of the constant Upgrade state. Retail tech entries
wait at least 180 seconds, beyond this probe. No MinTime is changed or tested here.
"""
from missions import aiskirm_bench


def personality(enabled, heuristic='<ConstantHeuristic/>', pid='CNVCUpgrade'):
    state = f'''<AIBuildStateDefinition id="CNVCUpgradeBuild">
    <Heuristic>{heuristic}</Heuristic>
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
  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="1AlliedBalanced">
    {link}
  </AIPersonalityDefinition>
</AssetDeclaration>
'''


def mission(enabled, name=None, pid='CNVCUpgrade', **kw):
    """kw: personality's heuristic (aiopath_bench.in_state: the state's PathToTargetHeuristic)."""
    m = aiskirm_bench.mission(name or ('CampCUpOn' if enabled else 'CampCUpOff'), lib=False)
    m.facts['upgrade entry'] = int(enabled)
    m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{pid}'
    m.assets.append((f'{pid}.xml', personality(enabled, pid=pid, **kw), f'AIPersonalityDefinition:{pid}'))
    m.put('AlliedRefinery', 'east refinery', side='s1', role='upgrade prerequisite')
    m.put('AlliedPowerPlant', 'east base', -250, 250, side='s1', role='upgrade power')
    return m


def path_test(condition, surface='Land', tester='JapanAntiAirVehicleTech1', tag=None):
    """B 11-25, PathToTargetHeuristic.LocomotorConditionToUseForTest where the heuristic is judged with both bases
    known (a build state; the opening is drawn at f4 before them, D108 why=early:nobase): aicupgon's state with its
    heuristic one PathToTarget PathExists="true" tested by the stock Jet Tengu (JapanAntiAirVehicleTech1: NORMAL =
    GROUND, SUPERSONIC = AIR, no PANIC set), ra3ext on (ptt rows). Prediction: NORMAL -- a land way, Tech2 as
    aicupgon; PANIC -- no set for it (why=noloco), no way, none as aicupgoff."""
    test = (f'<PathToTargetHeuristic Surface="{surface}" PathExists="true" ObjectTypeToUseForTest="{tester}"'
            f' LocomotorConditionToUseForTest="{condition}" />')
    tag = tag or condition.title()
    m = mission(True, name=f'CampPTT{tag}', pid=f'CNVPTT{tag}', heuristic=test)
    m.facts['upgrade entry'], m.ext = int(condition == 'NORMAL' and surface == 'Land'), True
    return m


MISSION = {'aicupgon': lambda: mission(True), 'aicupgoff': lambda: mission(False),
           'aipttn': lambda: path_test('NORMAL'), 'aipttp': lambda: path_test('PANIC'),
           'aipttw': lambda: path_test('NORMAL', 'Water', 'AlliedAntiNavalScout', 'WNav'),
           'aipttwg': lambda: path_test('NORMAL', 'Water', tag='WGnd')}
