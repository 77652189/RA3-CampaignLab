"""Construction scene factory shared with the script benches."""
from missions.aiskirm_bench import mission as base, ARMY_INF, FRIEND, NEW_BARRACKS
from benches.ai.tactics.scenes import aiorders_bench
MODULE = aiorders_bench()["shared"].MODULE
from parts import Script


def mission(enabled):
    m = base('CampAllBOn' if enabled else 'CampAllBOff', lib=False,
             new=False, observe=True, army=ARMY_INF)
    m.facts['consider all'] = int(enabled)
    enemy = (0, 0.0, 'Enemy')
    ai, primary, secondary = (m.player(s) for s in ('s1', 'p1', 's5'))
    start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
    start.do += [('PLAYER_RELATES_PLAYER', a, b, enemy)
                 for a, b in ((ai, primary), (primary, ai), (ai, secondary), (secondary, ai))]
    wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
    wake.do += [('SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY', ai, primary, 100),
                ('SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY', ai, secondary, 1),
                ('MAP_REVEAL_ALL_PERM', ai)]
    if enabled:
        wake.do.append(('SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING', ai))
    for k in range(20):
        m.put('SovietAntiVehicleVehicleTech1', 'base yard',
              -250.+100.*(k % 5), 650.+100.*(k // 5), side='s5',
              name=f'CNV AllB tank {k}', role=f'secondary tank {k}')
    unit, = [u for u in m.units if u.id == NEW_BARRACKS]
    assert unit.xml.count('<Behaviors>') == 1
    unit.xml = unit.xml.replace('<Behaviors>', '<Behaviors>'+MODULE, 1)
    m.scripts.append(Script('CNV AllB friend timer', [], [
        ('SET_MILLISECOND_TIMER', 'CNV AllB Friend', 70.)]))
    m.scripts.append(Script('CNV AllB secondary friend', [('TIMER_EXPIRED', 'CNV AllB Friend')], [
        ('PLAYER_RELATES_PLAYER', ai, secondary, FRIEND),
        ('PLAYER_RELATES_PLAYER', secondary, ai, FRIEND)]))
    return m
