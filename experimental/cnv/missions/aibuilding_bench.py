"""IsBuildingHeuristic idle boundary: an existing yard is not queued construction.

The Location bench's land target and four Twinblades, with no build funds.
Only PassIfBuilding differs. Prediction at s40: false -> four at the plant;
true -> four at home. KindOf=STRUCTURE. Active construction and KindOf
matching during construction remain unmeasured; see work/re/e_building_e83.md.
"""
from missions import ailocation_bench as location


def mission(pass_if_building, suffix):
    m = location.mission('Land', suffix)
    m.name = 'CampAIBuild' + suffix
    filename, xml, asset = m.assets[0]
    xml = xml.replace('<ConstantHeuristic/>',
                      '<IsBuildingHeuristic KindOf="STRUCTURE" '
                      f'PassIfBuilding="{str(pass_if_building).lower()}"/>')
    m.assets[0] = (filename, xml, asset)
    m.facts['expect target'] = 0 if pass_if_building else 4
    m.facts['expect home'] = 4 if pass_if_building else 0
    return m


MISSION = {'aibldtrue': lambda: mission(True, 'T'),
           'aibldfalse': lambda: mission(False, 'F')}
