"""E82: fixed Allied AI, one explicitly mounted opening; only its Side changes.

The opening builds three power plants, then waits 120 seconds. Both Side
values occur in retail SDK openings. Default model prediction: three plants
for both (it stores Side but does not filter the opening by it). That prediction
failed for Soviet (engine two plants, one barracks). The fallback source is
unverified; evidence belongs in work/re/e_openside_e82.md.
"""
from missions.aiskirm_bench import acct_xml, mission as skirmish


def mission(side, suffix):
    m = skirmish('CampAIOpen' + suffix, lib=False)
    xml = acct_xml('PRODUCTION')
    head, rest = xml.split('  <SkirmishOpeningMove', 1)
    _, tail = rest.split('  </SkirmishOpeningMove>', 1)
    xml = (head + f'  <SkirmishOpeningMove id="CNVAcctOpen" Side="PlayerTemplate:{side}">\n'
           + '    <Order Build="AlliedPowerPlant"/>\n' * 3
           + '    <Order Time="120s"/>\n  </SkirmishOpeningMove>' + tail)
    m.sides['s1']['aiPersonality'] = 'AIPersonalityDefinition:CNVAcct'
    m.assets.append(('CNVAcct.xml', xml, 'AIPersonalityDefinition:CNVAcct'))
    m.facts['side matches'] = int(side == 'Allies')
    return m


MISSION = {'aiosallies': lambda: mission('Allies', 'A'),
           'aiossoviet': lambda: mission('Soviet', 'S')}
