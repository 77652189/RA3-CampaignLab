"""A line: SKIRMISH_AI_START and PLAYER_TOGGLE_SKIRMISH_AI on B's aiskirm map (missions/aiskirm_bench.py).

Program (work/re a270_skirmish_start.md): SKIRMISH_AI_START = only the wake UNIT_AI_TRANSFER_ALL ends with (the AI's
started byte set, its start frame = now; no team moves); PLAYER_TOGGLE_SKIRMISH_AI(p, on) writes the AI's paused byte
= not on, and the AI's per-frame update does nothing while it is set (no opening, building, protocols, states).
Builds (s1 AlliedBalanced, 50000 at the 10 s wake; the control aiskirm d: 建筑数 2 at ~11 s after the wake, 3 at ~21):
  aistart   no script library (aiskirmnl), the wake's UNIT_AI_TRANSFER_ALL replaced by SKIRMISH_AI_START.
            Prediction: as aiskirm d -- 建筑数 2 ~11 s after the wake, money falling.
  ainowake  no library and no wake at all (MAKE_BASE and the money only). Prediction: the opening never starts --
            50000 and 建筑数 1 throughout (INFERRED: other subsystems might still order).
  aipause   aiskirm (library on), toggled off at 25 s, on at 85 s. Prediction: no new order from 25 s -- money and
            建筑数 flat (a structure already paid for may still finish), no unit; at 85 s it goes on.
  aistartx  no library, UNIT_AI_TRANSFER(the yard, 1) then SKIRMISH_AI_START (retail a07's way). Added after aistart.
  aixfer    no library, SKIRMISH_AI_TRANSFER_ALL(s1, 1) alone (the team step, no wake). Added after aistart.
Counters: AI钱, 建筑数, 兵数, 逻辑帧 (as aibgate).
BENCH 11-16 (A270, all NOEXPECT, work/bench_results/<build>__a.json):
  aistart   50000 / 1 / 0 from the money (f158) to f1154 -- the prediction failed: START wakes, but the yard is still
            on teamSoviet_1, not the AI's.
  ainowake  50000 / 1 / 0 to f746.   aixfer  50000 / 1 / 0 to f1104 (handed, never woken).
  aistartx  paying at f169 (49943), 建筑数 2 at f312 (f290 still 1), 3 at f461 -- as aiskirm's own wake.
  aipause   paying to 48300 at f457 (兵数 2 at f419: what was under way), then flat to f1262; 建筑数 3 at f1280 (the
            structure finished while paused is placed at the resume), paying again from f1300.
"""
from parts import Script, Test
from checks import engine_scripts8 as s8
from checks import engine_aiskirm as ak

OFF_AT, ON_AT = 25.0, 85.0


def _counters(t, m, key):
    s1 = m.player('s1')
    t.scripts.append(Script(f'Test - {key} setup', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters.append((f'CNV_{key}_Money', 'AI钱'))
    t.scripts.append(Script(f'Test - {key} money', [], [
        ('SET_PLAYER_MONEY_TO_COUNTER', s1, f'CNV_{key}_Money')], once=False))
    ak._sum(t, m, s1, f'CNV_{key}_Built', '建筑数', ak.BUILDINGS + ak.TOWERS)
    ak._sum(t, m, s1, f'CNV_{key}_Army', '兵数', ak.ARMY)
    s8.frames(t, f'CNV_{key}_Clock', '逻辑帧', [])
    return s1


def wake(m):
    """aistart / ainowake: the readings from the wake on."""
    t = Test()
    _counters(t, m, 'AIStart')
    t.bench = [('bench_watch', dict(seconds=60., every=1., sheet=False, lines=4))]
    return t


def pause(m):
    """aipause: PLAYER_TOGGLE_SKIRMISH_AI(s1, 0) at OFF_AT, (s1, 1) at ON_AT."""
    t = Test()
    s1 = _counters(t, m, 'AIPause')
    s8.at(t, 'aipause off', OFF_AT, [('PLAYER_TOGGLE_SKIRMISH_AI', s1, 0)])
    s8.at(t, 'aipause on', ON_AT, [('PLAYER_TOGGLE_SKIRMISH_AI', s1, 1)])
    t.bench = [('bench_watch', dict(seconds=125., every=1., sheet=False, lines=4))]
    return t


CHECKS = {'aistart': {'a': wake}, 'ainowake': {'a': wake}, 'aistartx': {'a': wake}, 'aixfer': {'a': wake},
          'aipause': {'a': pause}}
