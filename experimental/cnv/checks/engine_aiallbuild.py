"""Native all-enemies construction contrast; work/re/c_allbuild_report.md.

INFERRED prediction: including the secondary twenty-tank enemy changes the
native candidate scores or chosen anti-vehicle mix versus the primary ten
infantry enemy alone. Friendship at 70s tests removal from that enemy set.
Opening orders may ignore this input: inspect bpick/border same-pass choices,
not money or an empty candidate list. No expected exact clock is invented.
"""
from parts import Script, Test, counted
from checks import engine_scripts8 as s8


def a(m):
    t = Test()
    m.spawns.update(('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'))
    t.scripts.append(Script('Test AllB reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_AllB_PK', '维和', t, template='AlliedAntiInfantryInfantry', player=m.player('s1'))
    counted('CNV_AllB_Jav', '标枪', t, template='AlliedAntiVehicleInfantry', player=m.player('s1'))
    counted('CNV_AllB_Tanks', '次敌坦克', t, template='SovietAntiVehicleVehicleTech1', player=m.player('s5'))
    s8.frames(t, 'CNV_AllB_Frame', '逻辑帧', [])
    s8.watch(t, 150., 2.)
    return t


CHECKS = {'aiallbuildon': {'a': a}, 'aiallbuildoff': {'a': a}}
