"""Synthetic knock landing classifier: KindOf versus NORMAL Locomotor.

Reuse kindgate b's unfiltered positive shock. Only the synthetic noninf
neighbours change: a adds VEHICLE, b swaps HUMAN for the Hammer locomotor
without adding VEHICLE. Physics, geometry, speed and all other data stay.
Predict a keeps the infantry grid, b uses the vehicle grid if locomotion
determines the landing. Neither check claims retail vehicle coverage.
"""
import re

from checks import engine_knock_kindgate as kg

HUMAN = 'TestReactiveLocomotorHUMAN'
TREADS = 'SovietAntiVehicleVehicleTech1Locomotor'


def mission():
    m = kg.mission()
    m.name = 'CampKGrid'
    return m


def check(m, locomotor=False):
    t = kg.check(m, without_filter=True)
    other = next(u for u in m.units if u.id == kg.NONINF)
    if locomotor:
        assert other.xml.count('Locomotor="' + HUMAN + '"') == 1
        other.xml = other.xml.replace('Locomotor="' + HUMAN + '"', 'Locomotor="' + TREADS + '"')
    else:
        other.xml, n = re.subn(r'(\bKindOf=")([^"]*)(")',
                              lambda x: x[1] + x[2] + ' VEHICLE' + x[3], other.xml)
        assert n == 1
    other.what = '合成落点对照：仅改VEHICLE标签或NORMAL移动器，非原版车辆'
    return t


MISSION = {'engine_knock_grid': mission}
CHECKS = {'engine_knock_grid': {'a': check, 'b': lambda m: check(m, locomotor=True)}}
