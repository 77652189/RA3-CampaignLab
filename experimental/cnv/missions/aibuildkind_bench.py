"""C: IsBuildingHeuristic.KindOf against an active power-plant opening.

Retail AlliedBaseStates uses STRUCTURE and FS_TECHNOLOGY SUPER_WEAPON
to exclude construction periods. Here only KindOf differs: FS_POWER matches
the opening's eight power plants, FS_BARRACKS does not. Existing yards are
present from map load; construction begins after the standard s10 wake.
Prediction at s40: matching target/home=4/0, nonmatching=0/4; at least two
completed plants independently establish that the opening actually builds.
Multiple tokens and individual queue phases remain unmeasured.
"""
from missions import ailocation_bench as location


def mission(matches):
    suffix = 'Y' if matches else 'N'
    m = location.mission('Land', suffix)
    m.name = 'CampAIBKind' + suffix
    filename, xml, asset = m.assets[0]
    kind = 'FS_POWER' if matches else 'FS_BARRACKS'
    xml = xml.replace('<ConstantHeuristic/>',
                      f'<IsBuildingHeuristic KindOf="{kind}" PassIfBuilding="true"/>')
    opening = ('  <SkirmishOpeningMove id="CNVBKindOpen" Side="PlayerTemplate:Allies">\n'
               '    <Order Time="0s" Account="PRODUCTION" Deposit="10000"/>\n'
               + '    <Order Build="AlliedPowerPlant"/>\n' * 8
               + '    <Order Time="120s"/>\n  </SkirmishOpeningMove>\n')
    xml = xml.replace('  <AIPersonalityDefinition ', opening + '  <AIPersonalityDefinition ', 1)
    xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                      '    <OpeningMove Name="CNVBKindOpen" Weight="100%" '
                      'Difficulty="EASY MEDIUM HARD BRUTAL"/>\n'
                      '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>')
    m.assets[0] = (filename, xml, asset)
    # Both start and wake scripts set the balance; fund both identically.
    for script in m.scripts:
        script.do = [(action[0], action[1], 50000) if action[0] == 'PLAYER_SET_MONEY'
                     else action for action in script.do]
    m.spawns.add('AlliedPowerPlant')
    m.facts.update({'building matches': matches, 'expect target': 4 if matches else 0,
                    'expect home': 0 if matches else 4})
    return m


MISSION = {'aibkindyes': lambda: mission(True), 'aibkindno': lambda: mission(False)}
