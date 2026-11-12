"""Tech probe mission (engine_tech check): the player's construction yard, a power plant and two war factories on
the Niagara map -- one 300 east of the start (inside the yard's TechUpgrade radius 600, rectangular), one 750 east of
the yard (outside). The check's variants delete what they do not need. Published (the cast): yard, power, near
factory, far factory.
"""
import resources
from maps import niagara
from parts import Mission

WAR_FACTORY, GUARDIAN = 'AlliedWarFactory', 'AlliedAntiVehicleVehicleTech1'
FAR_DX = 450.0                          # from 'base factory' (yard at 300 west of it): far factory 750 from the yard


def _n(part):
    return f'UNIT - CNV Tech {part}'


def mission(name='CampTech'):
    m = Mission(name=name, map=resources.measured(niagara), units=[], facts={})
    m.spawns |= {GUARDIAN}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power', name=_n('Power'))
    m.put('AlliedRefinery', 'base refinery', role='refinery', name=_n('Refinery'))   # the Tech2 button needs one
    m.put(WAR_FACTORY, 'base factory', angle=3.1416, role='near factory', name=_n('Near'))
    m.put(WAR_FACTORY, 'base factory', FAR_DX, 0.0, angle=3.1416, role='far factory', name=_n('Far'))
    return m


MISSION = {'engine_tech': mission}
