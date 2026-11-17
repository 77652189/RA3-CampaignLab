"""Finite AlphaStrikeTargetHealthPct contrast, not an exact boundary probe.

Named far plant starts at 70%; guards match the existing retreat probe.
High 0.9 should
finish its tactical target before retreat; low 0.01 should retreat first.
TimeToKill stays deliberately permissive in both, all other fields equal.
"""
from missions import airetreat_bench as ar
from parts import Script


def mission(high):
    m = ar.mission('CampAlphaHi' if high else 'CampAlphaLo', guards=ar.GUARDS,
                   RetreatPowerAdvantage='0.2', AlphaStrikeTargetHealthPct='0.9' if high else '0.01',
                   AlphaStrikeTargetTimeToKill='1000.0', Crush='false')
    plant = m.role('far plant').name
    m.scripts.append(Script('CNV Alpha - target health', [], [('UNIT_SET_HEALTH', plant, 70.0)]))
    m.facts['alpha target'] = plant
    return m


MISSION = {'aialphalo': lambda: mission(False), 'aialphahi': lambda: mission(True)}
