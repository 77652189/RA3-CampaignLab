"""E175: retail turbine upgrade, normal/advanced plants and module deletion.

Prediction from EnergyProduction/EnergyBonus: 100/350 before grant, 110/360
after Upgrade_PowerPlantTurbine only with PowerUpgrade. INFERRED until bench.
Four isolated owners; f60 baseline, f90 grant, f180 upgraded, f210 remove,
f300 removed. Frozen bits assert exact excess power (no power consumers).
No purchased-upgrade, exact update-frame, death or ownership claim.
MEASURED a: final 330/11/10/11. b: power stays 100/100/500/350 and
upgrade-holder stays zero through grant/removal. Campaign override explains
500 vs the raw SDK clone's 350. Trigger Upgrade_PowerPlantTurbine has no
definition in SDK GlobalData/Upgrade.xml; no positive module-effect claim.
See work/re/e175_powerupgrade.md. Both failed predictions remain unchanged.
"""
from model import Script, Test

UP = 'Upgrade_PowerPlantTurbine'
ROWS = [('normalon', 'p1', 'base gun', False, True),
        ('normaloff', 's1', 'high gun', False, False),
        ('advancedon', 's2', 'removed gun', True, True),
        ('advancedoff', 's3', 'switch gun', True, False)]


def check(m):
    t = Test()
    t.counters = [('E175Frame', 'frame'), ('E175Base', 'baseline'),
                  ('E175Grant', 'upgraded'), ('E175Remove', 'removed')]
    t.scripts = [
        Script('Test - frame', [('COUNTER', 'E175Frame', 0, 330)],
               [('INCREMENT_COUNTER', 1, 'E175Frame')], once=False),
        Script('Test - grant', [('COUNTER', 'E175Frame', 2, 90)],
               [('NAMED_RECEIVE_UPGRADE', UP, m.role(tag).name) for tag, *_ in ROWS]),
        Script('Test - remove', [('COUNTER', 'E175Frame', 2, 210)],
               [('NAMED_REMOVE_UPGRADE', UP, m.role(tag).name) for tag, *_ in ROWS])]
    for frame, counter in [(60, 'E175Base'), (180, 'E175Grant'), (300, 'E175Remove')]:
        for bit, (tag, side, _, advanced, enabled) in enumerate(ROWS):
            power = (350 if advanced else 100) + (10 if frame == 180 and enabled else 0)
            t.scripts.append(Script(f'Test - power {frame} {tag}', [
                ('COUNTER', 'E175Frame', 2, frame),
                ('PLAYER_EXCESS_POWER_COMPARE_VALUE', m.player(side), 2, power)],
                [('INCREMENT_COUNTER', 1 << bit, counter)]))
    t.expect = [(label, 0, 'ever>=', value) for label, value in
                [('frame', 330), ('baseline', 15), ('upgraded', 15), ('removed', 15)]]
    t.bench = [('bench_watch', dict(seconds=120, every=1, sheet=False, lines=4, until='c1>=330'))]
    return t


def diagnostic(m):
    """Second and final run: exact candidate power, upgrade possession and frame.

    Each line = frame*100000 + upgrade-holder*10000 + exact power; 9999
    means no candidate matched. This preserves the first run's failed prediction.
    """
    t = Test()
    t.counters = [('E175Read' + str(i), tag) for i, (tag, *_) in enumerate(ROWS)]
    t.scripts = [
        Script('Test - clock', [('COUNTER', 'E175Frame', 0, 330)],
               [('INCREMENT_COUNTER', 1, 'E175Frame')], once=False),
        Script('Test - grant', [('COUNTER', 'E175Frame', 2, 90)],
               [('NAMED_RECEIVE_UPGRADE', UP, m.role(tag).name) for tag, *_ in ROWS]),
        Script('Test - remove', [('COUNTER', 'E175Frame', 2, 210)],
               [('NAMED_REMOVE_UPGRADE', UP, m.role(tag).name) for tag, *_ in ROWS])]
    for i, (tag, side, *_) in enumerate(ROWS):
        c = 'E175Read' + str(i)
        active = [('COUNTER', 'E175Frame', 0, 331)]
        t.scripts.append(Script('Test - clear ' + tag, active, [('SET_COUNTER', c, 9999)], once=False))
        for value in (0, 10, 100, 110, 200, 300, 350, 360, 500, 510, 1000, 1010, 1100, 3500, 3510, 3850):
            t.scripts.append(Script(f'Test - read {tag} {value}', active + [
                ('PLAYER_EXCESS_POWER_COMPARE_VALUE', m.player(side), 2, value)],
                [('SET_COUNTER', c, value)], once=False))
        t.scripts.append(Script('Test - held ' + tag, active + [
            ('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', m.player(side), 1, UP)],
            [('INCREMENT_COUNTER', 10000, c)], once=False))
        t.scripts.append(Script('Test - stamp ' + tag, active, [
            ('SET_COUNTER_TO_COUNTER', 'E175Stamp', 'E175Frame'),
            ('COUNTER_MATH_VALUE', 'E175Stamp', 2, 100000),
            ('COUNTER_MATH_COUNTER', c, 0, 'E175Stamp')], once=False))
    t.bench = [('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4, until='c1>=33000000'))]
    return t


CHECKS = {'engine_powerupgrade_e': {'a': check, 'b': diagnostic}}
