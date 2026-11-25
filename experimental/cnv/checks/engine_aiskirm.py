"""Skirmish counter helpers shared with the script benches."""
from parts import Script


RIPTIDE = 'AlliedAntiInfantryVehicle_Ground'     # the one a Riptide on land is (aiopen b counts both alike)

DOG = 'AlliedScoutInfantry'

TOWERS = ('AlliedBaseDefense', 'AlliedBaseDefenseAdvanced')

BUILDINGS = ('AlliedConstructionYard', 'AlliedPowerPlant', 'AlliedBarracks', 'AlliedRefinery', 'AlliedWarFactory')

ARMY = ('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', RIPTIDE, DOG)

CAP = 24                            # a sum reads at most this many per template

def _sum(t, m, s1, counter, label, templates, weights=None, cap=CAP):
    """A shown counter that is the total of what s1 owns over `templates`: each template is counted into a hidden
    counter every frame, the shown one is zeroed first and gets +weight per unit (hidden >= n for n = 1..cap;
    weights default 1 each)."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    for i, tpl in enumerate(templates):
        m.spawns.add(tpl)
        h = f'{counter}_H{i}'
        wt = weights[i] if weights else 1
        t.scripts.append(Script(f'Test - {counter} own {i}', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, s1, h)],
                                once=False))
        for n in range(1, cap + 1):
            t.scripts.append(Script(f'Test - {counter} {i} >= {n}', [('COUNTER', h, 3, n)],
                                    [('INCREMENT_COUNTER', wt, counter)], once=False))
