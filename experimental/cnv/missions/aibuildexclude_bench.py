"""C: identical two-factory requests, with only ExcludeThing changed.

CNVNewPK scores 1000; CNVDearPK scores 1 and costs 200. aibex/aibin
include Dear explicitly (IncludeThing wins over ExcludeThing); aibxo/aibxi
include infantry by category, and only aibxo excludes Dear.
The observer is attached to an existing copied barracks (no yard swap).
"""
from missions.aiskirm_bench import mission as base, NEW_BARRACKS
from missions.aiorders_bench import MODULE


def mission(exclude, category=False):
    name = ('CampBXO' if exclude else 'CampBXI') if category else ('CampBEx' if exclude else 'CampBIn')
    m = base(name, new=True, dear='cs', dear_cost=200)
    path, xml, asset = m.assets[-1]
    old = '<BuildEntry Build="CNVNewPK" Heuristic="FEWEST_UNIT"/>'
    assert xml.count(old) == 1
    xml = xml.replace(old, '<BuildEntry Build="CNVNewPK" Heuristic="CONSTANT" Score="1000"/>')
    if category:
        xml = xml.replace('Include="STRUCTURE UNPACKS_INTO_BUILDING"',
                          'Include="STRUCTURE UNPACKS_INTO_BUILDING INFANTRY"')
        xml = xml.replace('<IncludeThing>CNVDearPK</IncludeThing>', '')
    if exclude:
        xml = xml.replace('</CountAsStructureForBuildPurposesFilter>',
                          '<ExcludeThing>CNVDearPK</ExcludeThing></CountAsStructureForBuildPurposesFilter>')
    m.assets[-1] = path, xml, asset
    unit, = [u for u in m.units if u.id == NEW_BARRACKS]
    assert unit.xml.count('<Behaviors>') == 1
    unit.xml = unit.xml.replace('<Behaviors>', '<Behaviors>' + MODULE, 1)
    m.ext = True
    return m


MISSION = {'aibex': lambda: mission(True), 'aibin': lambda: mission(False),
           'aibxo': lambda: mission(True, category=True), 'aibxi': lambda: mission(False, category=True)}
