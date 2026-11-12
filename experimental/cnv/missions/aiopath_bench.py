"""Engine probe: PathToTargetHeuristic in the opening pick -- does the AI judge "no way to the enemy" by the unit the
heuristic names (checks/engine_aiopath.py; private ai/opening._holds, simai.Brain.path_to_target)?

aiopen_bench as is (Niagara, the enemy s1 Allied with one yard, woken at 10 s with 50000 money), but s1's
personality is the probe's: inheritFrom AlliedCoopBaseSkirmishPersonality (it and its parents have no OpeningMove),
two lines only, every difficulty:
  AlliedStandard  PathToTargetHeuristic PathExists="true"   (barracks first, power plant at +10 s: engine_aiopen)
  AlliedIsland    PathToTargetHeuristic PathExists="false"  (power plant first, no barracks in the list)
both tested with the same ObjectTypeToUseForTest:
  aiopath1  CNVPathP: AlliedPowerPlant -- no locomotor, so (program read, l4_states.md 3) no path: Island expected
  aiopath0  CNVPathI: SovietAntiInfantryInfantry -- the stock test unit, Niagara is land: Standard expected
  aiopathi  CNVPathO: ONE line, AlliedIsland with PathExists="true", the infantry tester -- does the probe's
            personality take at all (a power plant first = yes; barracks first = the stock opening, it did not)
  aiopathr  CNVPathR: aiopath1's two lines, order reversed (Island first) -- if both lines hold, the draw (same
            weights) takes the first: Island here; if the power plant really has a path, Standard again
"""
from missions import aiopen_bench

BASE = 'AlliedCoopBaseSkirmishPersonality'


def personality_xml(pid, tester, moves=(('AlliedStandard', 'true'), ('AlliedIsland', 'false')),
                    condition='NORMAL'):
    test = (f'<PathToTargetHeuristic PathExists="{{}}" ObjectTypeToUseForTest="{tester}"'
            f' LocomotorConditionToUseForTest="{condition}" />')
    lines = []
    for move, exists in moves:
        lines += [f'    <OpeningMove Name="{move}" Weight="100%" Difficulty="EASY MEDIUM HARD BRUTAL">',
                  '      <Heuristic>', '        ' + test.format(exists), '      </Heuristic>',
                  '    </OpeningMove>']
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
        *lines,
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])


def mission(name, pid, tester, **kw):
    m = aiopen_bench.mission(name=name)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    m.assets.append((f'{pid}.xml', personality_xml(pid, tester, **kw), f'AIPersonalityDefinition:{pid}'))
    return m


MISSION = {
    # Same tester and land endpoints: deep-water NORMAL versus flying SUPERSONIC.
    'aiopwater': lambda: mission('CampPathWater', 'CNVPathWater', 'JapanAntiAirShip'),
    'aiopair': lambda: mission('CampPathAir', 'CNVPathAir', 'JapanAntiAirShip', condition='SUPERSONIC'),
    'aiopath1': lambda: mission('CampAIPath1', 'CNVPathP', 'AlliedPowerPlant'),
    'aiopath0': lambda: mission('CampAIPath0', 'CNVPathI', 'SovietAntiInfantryInfantry'),
    'aiopathi': lambda: mission('CampAIPathI', 'CNVPathO', 'SovietAntiInfantryInfantry',
                                moves=(('AlliedIsland', 'true'),)),
    'aiopathr': lambda: mission('CampAIPathR', 'CNVPathR', 'AlliedPowerPlant',
                                moves=(('AlliedIsland', 'false'), ('AlliedStandard', 'true'))),
}
