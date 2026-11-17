"""出动 + 齐步 on the bench (missions/pace_placed_bench.py, docs/engine/pathing.md 5b): the harbour's two tanks and two
warriors sent off at SEND to the west field, with (`paceplaced`) and without (`paceplacedn`) 齐步.

go: counters (every frame) -- how many of the tanks stand in the goal (a square of GOAL round the west field), how
  many of the warriors, and how many enemy units hold the pace upgrade (0 in paceplacedn). Read, not judged: with
  齐步 the tanks come in with the warriors (and the upgrade count drops to 0 once one is inside the west field's
  area); without, the tanks well ahead.

Read (bench 11-12, bench seconds):
  paceplaced CampPacePlGo_mcp_1112_124725: 限速 2 s33-s84 (granted as sent, held by both tanks), 0 from s88; 坦克 1 at
    s88, 2 at s90; 武士 1 at s90, 2 at s93 -- together, the last warrior 5 s after the first tank.
    The simulator: 81 / 82 / 83 (bench s runs a few seconds ahead of the mission clock).
  paceplacedn CampPacePlNGo_mcp_1112_125222: 坦克 2 from s74 (0 at s71); 武士 1 at s91, 2 at s93 -- the tanks 17-19 s
    ahead. The simulator: tanks 65 / 66, warriors 82 / 83 (17 s). (A first run, CampPacePlNGo_mcp_1112_124000, read 0
    0 0 to s220: its start lost the popup connection at 38 s; the four stood short of the goal. Not a reading.)
"""
from parts import Script, Test, counted, square

GOAL = 250.0
RUN = 150.0


def go(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas['Test PP goal'] = square(*m.site('west field'), GOAL)
    s1 = m.player('s1')
    counted('Test PP tank', '坦克', t, template=m.cast['tank 1'].template, player=s1, area='Test PP goal', most=3)
    counted('Test PP foot', '武士', t, template=m.cast['foot 1'].template, player=s1, area='Test PP goal', most=3)
    up = next((u.names['pace'] for u in m.units if u.id.startswith('CNV_Pace')), None)
    t.counters.append(('Test PP up', '限速'))
    t.scripts.append(Script('Test - pp up zero', [], [('SET_COUNTER', 'Test PP up', 0)], once=False))
    if up:
        t.scripts += [Script(f'Test - pp up {n}', [('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', s1, n, up)],
                             [('SET_COUNTER', 'Test PP up', n)], once=False) for n in (1, 2)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=3))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {'paceplaced': {'go': go}, 'paceplacedn': {'go': go}}

# bench seconds the counters first read (坦克 / 武士) 1 and 2, and the span the upgrade was held
BENCH = {'paceplaced': {'tank': (88, 90), 'foot': (90, 93), 'held': (33, 84)},
         'paceplacedn': {'tank': (74, 74), 'foot': (91, 93)}}
