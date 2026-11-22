"""A round 294: the AI's subsystem switches (missions/aichange_bench.py) -- s1's units out by kind, by logical frame."""
from checks import engine_scripts8 as s8
from parts import Test, counted


def a(m):
    t = Test()
    m.spawns.update(('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', 'AlliedScoutInfantry'))
    for counter, label, template in (('CNV_AISw_PK', '维和', 'AlliedAntiInfantryInfantry'),
                                     ('CNV_AISw_Jav', '标枪', 'AlliedAntiVehicleInfantry'),
                                     ('CNV_AISw_Dog', '警犬', 'AlliedScoutInfantry')):
        counted(counter, label, t, template=template, player=m.player('s1'))
    s8.frames(t, 'CNV_AISw_Frame', '逻辑帧', [])
    s8.watch(t, 90., 2.)
    return t


CHECKS = {name: {'a': a} for name in ('aiubon', 'aiuboff', 'aiubback', 'aitboff')}
