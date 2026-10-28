"""敌方AI 分档 tests (missions/aistep_bench.py). Counted: the AI's IFVs, and latches at 1 if it had a war factory / an
IFV before its step let them go (the step's flag CNV_AS_AI_Step_1 still 0). Bench 2026-10-27, the step at 90 s after
waking: its factory came only after; held back guardians it never built, held or not (aistep_free).

stepped: with a war factory up before the step, no IFV until the step; some once it let them go.
free: the control, nothing held back -- it builds IFVs (before the step's time too).
"""
from parts import Script, Test, counted

FACTORY, IFV = 'AlliedWarFactory', 'AlliedAntiAirVehicleTech1'


def watch(m, t):
    ai = m.ai_player()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('Test IFV', 'AI步兵车', t, template=IFV, player=ai)
    m.spawns |= {FACTORY.lower(), IFV, IFV.lower()}
    run = m.facts['wake at'] + m.facts['watch']
    return ai, run


def stepped(m):
    t = Test()
    ai, run = watch(m, t)
    t.counters.append(('Test Ready', '放开前有工厂'))
    t.scripts += [Script('Test - ready zero', [], [('SET_COUNTER', 'Test Ready', 0)]),
                  Script('Test - ready', [('PLAYER_HAS_OBJECT_COMPARISON', ai, 3, 1, FACTORY.lower()),
                                          ('FLAG', 'CNV_AS_AI_Step_1', 0)], [('SET_COUNTER', 'Test Ready', 1)])]
    t.counters.append(('Test Early', '放开前就有'))
    t.scripts += [Script('Test - early zero', [], [('SET_COUNTER', 'Test Early', 0)]),
                  Script('Test - early', [('PLAYER_HAS_OBJECT_COMPARISON', ai, 3, 1, IFV.lower()),
                                          ('FLAG', 'CNV_AS_AI_Step_1', 0)], [('SET_COUNTER', 'Test Early', 1)])]
    t.expect += [('放开前就有', 1, '==', 0), ('放开前有工厂', 1, 'ever==', 1), ('AI步兵车', 1, 'ever>=', 1)]
    t.bench = [('bench_watch', dict(seconds=run, every=6, sheet=False, lines=len(t.counters)))]
    return t


def free(m):
    t = Test()
    _, run = watch(m, t)
    t.expect += [('AI步兵车', 1, 'ever>=', 1)]
    t.bench = [('bench_watch', dict(seconds=run, every=6, sheet=False, lines=len(t.counters)))]
    return t
