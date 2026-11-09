"""Engine probe, the inferred script items (docs/engine/inventory-levels-a.md): mission missions/scripts2_bench.py.
What the simulator predicts is in brackets; the readings go below.

Counters (both checks): A血 = the player's MCV in the west (only the enemy's Guardian can shoot it), B血 = the enemy's
MCV in the east (only the player's Guardian can shoot it), in percent; 比较数 = how many Guardians the player has by
PLAYER_HAS_OBJECT_COMPARISON (==, n = 0..3), 类型数 = by SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER. tank 1 is killed at
KILL_AT (the player then has gun b + tank 2: 3 -> 2).

  one   PLAYER_RELATES_PLAYER(Soviet_1, Player_1, Neutral) at the start, (Soviet_1, Player_1, Enemy) at BACK_AT.
        [A血 100 until BACK_AT, then falls: the enemy's view of the player is its own; B血 falls from the start:
        the player's view of the enemy is unchanged (one way)]. 比较数 [3 -> 2 at KILL_AT: LINGER 0, the dying
        counted only while in the name cache]
  all   PLAYER_RELATES_PLAYER(Soviet_1, <All Players>, Neutral) at the start (retail a01's retreat), (Player_1,
        Soviet_1, Neutral) at BACK_AT. [simulator before this probe: '<All Players>' never matched a pair, A血 falls
        from the start; B血 falls until BACK_AT, then stays]

读数
Bench 2026-11-09 (one run each; the bench's seconds ~2 s behind the game's; sim pairs tests/test_simbench.py
test_scripts2_*):
  one   CampScr2One_mcp_1109_054230: A血 100 to s8, 98 s9, 86 s25 -- one way, and Enemy again takes at once. 比较数 3
        -> 2 at s2 with 类型数: the killed tank is not counted while it dies (Generals' ignoreDead false is not RA3's;
        docs/engine/script-semantics.md 6 was a guess).
  all   CampScr2All_mcp_1109_054518: A血 98 s1 -> 80 s25: '<All Players>' as the second player changes nothing (the
        simulator never matched it: right). Retail a01's retreat line does not stop Soviet_1's fire.
  both  B血 98 s1 -> 95 s5, then 96 -> 99 by s25, in both runs (the player's view of Soviet_1 untouched in one,
        Neutral from BACK_AT in all): the player's Guardian stops shooting the unarmed MCV after ~4 s and the MCV
        heals. Not explained (auto-acquire of an unarmed target? an MCV's self-repair?) -- not this probe's question.
"""
from parts import Script, Test, counted

KILL_AT, BACK_AT = 3.0, 10.0
RUN = {'one': 24.0, 'all': 24.0}
TANK = 'AlliedAntiVehicleVehicleTech1'
REL = {'Enemy': 0, 'Neutral': 1, 'Friend': 2}


def _rel(a, b, r):
    return ('PLAYER_RELATES_PLAYER', a, b, (REL[r], 0.0, r))


def _at(t, key, secs, actions):
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def _common(t, m):
    counted('CNV_S2_A', 'A血', t, health=m.role('mcv a').name)
    counted('CNV_S2_B', 'B血', t, health=m.role('mcv b').name)
    t.counters.append(('CNV_S2_Cmp', '比较数'))
    t.scripts += [Script(f'Test - cmp {n}', [('PLAYER_HAS_OBJECT_COMPARISON', m.player('p1'), 2, n, TANK)],
                         [('SET_COUNTER', 'CNV_S2_Cmp', n)], once=False) for n in range(4)]
    counted('CNV_S2_Type', '类型数', t, template=TANK)
    _at(t, 'kill', KILL_AT, [('NAMED_KILL', m.role('tank 1').name)])
    t.bench = [('bench_watch', dict(seconds=RUN['one'], every=0.5, sheet=False, lines=len(t.counters)))]


def one(m):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), _rel(s1, p1, 'Neutral')]))
    _at(t, 'back', BACK_AT, [_rel(s1, p1, 'Enemy')])
    _common(t, m)
    return t


def all_(m):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), _rel(s1, '<All Players>', 'Neutral')]))
    _at(t, 'back', BACK_AT, [_rel(p1, s1, 'Neutral')])
    _common(t, m)
    return t


CHECKS = {'engine_scripts2': {'one': one, 'all': all_}}
