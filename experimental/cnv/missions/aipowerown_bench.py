"""C: IncludeOwnDefenses only, fixed 4:8 Guardians and a powered Spectrum Tower.

Value=0.5, Above=true; predict off home=4, on home=0 at s40.
Exact army ratio and other defense categories remain gaps.
"""
from missions import aipoweradv_bench as setup


def mission(include):
    gate = ('<PowerAdvantageHeuristic Value="0.5" Above="true" '
            f'IncludeOwnDefenses="{str(include).lower()}" IncludeEnemyDefenses="false"/>')
    m = setup.mission('CampAIPOwn', 4, 8, gate=gate, expect=int(include))
    m.name = 'CampAIPOwnOn' if include else 'CampAIPOwnOff'
    tower = 'AlliedBaseDefenseAdvanced'
    m.put(tower, 'east base', 300.0, -200.0, side='s1',
          name='UNIT - CNV Own Tower', role='own tower')
    m.put('AlliedPowerPlant', 'east base', 300.0, 200.0, side='s1',
          name='UNIT - CNV Own Power', role='own power')
    m.spawns |= {tower, 'AlliedPowerPlant'}
    m.facts.update({'home at 40': 0 if include else 4, 'defense template': tower})
    return m


MISSION = {'aipownoff': lambda: mission(False), 'aipownon': lambda: mission(True)}
