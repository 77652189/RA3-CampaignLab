"""Isolate the Sickle XML exclusion from an independent collision-status gate.

a retains retail XML; b removes only StatusBitFlagsExclude. Both have enemy
infantry neighbours 20 east, yuri NO_COLLISIONS=1 and rocket=0.
Prediction: a rejects yuri; b admits both if XML is the only gate, otherwise
still rejects yuri. Native status creation/cleanup is outside this slice.
"""
from checks import engine_knock_nocoll as nocoll


def mission():
    m = nocoll.mission()
    m.name = 'CampKSG'
    return m


def check(m, without_exclusion=False):
    t = nocoll.check(m)
    if without_exclusion:
        for unit in m.units:
            if unit.id in ('CNV_KnockYuri', 'CNV_KnockRocket'):
                old = 'StatusBitFlagsExclude="NO_COLLISIONS"'
                assert unit.xml.count(old) == 1
                unit.xml = unit.xml.replace(old, '')
    return t


MISSION = {'engine_knock_statusgate': mission}
CHECKS = {'engine_knock_statusgate': {
    'a': check, 'b': lambda m: check(m, without_exclusion=True)}}
