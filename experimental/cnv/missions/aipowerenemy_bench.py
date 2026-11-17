"""C: IncludeEnemyDefenses only, fixed 8:4 Guardians and a powered Spectrum Tower.

Value=2.0, Above=true; predict off home=0, on home=8 at s40.
Exact army ratio and other defense categories remain gaps.
"""
from missions import aipoweradv_bench as setup


def mission(include):
    gate = ('<PowerAdvantageHeuristic Value="2.0" Above="true" '
            f'IncludeOwnDefenses="false" IncludeEnemyDefenses="{str(include).lower()}"/>')
    m = setup.mission('CampAIPEnemy', 8, 4, gate=gate, expect=int(not include))
    m.name = 'CampAIPEnemyOn' if include else 'CampAIPEnOff'
    tower = 'AlliedBaseDefenseAdvanced'
    m.put(tower, 'base yard', 300.0, -200.0, side='p1',
          name='UNIT - CNV Enemy Tower', role='enemy tower')
    m.put('AlliedPowerPlant', 'base yard', 300.0, 200.0, side='p1',
          name='UNIT - CNV Enemy Power', role='enemy power')
    m.spawns |= {tower, 'AlliedPowerPlant'}
    m.facts.update({'home at 40': 8 if include else 0, 'defense template': tower})
    return m


MISSION = {'aipenoff': lambda: mission(False), 'aipenon': lambda: mission(True)}
