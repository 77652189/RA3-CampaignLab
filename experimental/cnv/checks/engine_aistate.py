"""Engine probe: strategic states switched by map flags (missions/aistate_bench.py) -- which of the AI's units leave
its base, and how many frames after their state's flag went on.

  a  步兵在家 / 坦克在家   Peacekeepers / Guardians of s1 inside the base area (450 around the east base), once a second
     步兵等帧 / 坦克等帧   frames from the flag going on while all four are still home (stops at the first to leave)

Expected if ScriptedFlagHeuristic follows SET_FLAG and a team takes only what its filter names: the infantry go
after INF_AT and the tanks stay home till TANK_AT, then the tanks go. The waits are the reading (the model,
RA3-EngineModel ra3model/ai/states.py, re-weighs states every 15 frames).
"""
from missions import aistate_bench as ab
from parts import Script, Test, counted, square

AREA = 'CNV AI Base Area'
LAG = 4.0
SECONDS = 120.0


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 450.0)
    counted('CNV_AS_InfHome', '步兵在家', t, template=ab.INF, area=AREA, player=s1)
    counted('CNV_AS_TankHome', '坦克在家', t, template=ab.TANK, area=AREA, player=s1)
    for c, lab, flag, unit in (('CNV_AS_InfWait', '步兵等帧', ab.FLAG_INF, ab.INF),
                               ('CNV_AS_TankWait', '坦克等帧', ab.FLAG_TANK, ab.TANK)):
        t.counters.append((c, lab))
        t.scripts.append(Script(f'Test - wait {c}', [
            ('FLAG', flag, 1), ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 4, unit, AREA)],
            [('INCREMENT_COUNTER', 1, c)], once=False))
    w, i, k = (m.facts[x] for x in ('wake at', 'infantry at', 'tanks at'))
    t.expect += [('步兵在家', k, '<', 4, k + 1), ('坦克在家', k, '==', 4, k + 1), ('坦克在家', SECONDS, '<', 4, SECONDS + 1)]
    t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aistate': {'a': a}}
