"""Engine probe: SKIRMISH_AI_SET_FAVORED_ENEMY(ai player, enemy) (retail: a04 Japan01 / Japan02 -> Player_1 right
after the AI's setup, ...). Engine line A round 220; the mission is engine line B's build aipriodef
(from the registry, its module untouched) plus the favored enemy; the counters are checks/engine_aiprio.py's.

The program (work/re a219_skirmish_transfer.md section 2): with both players, the AI brain, its strategy manager
and its enemy manager there, the enemy table is emptied (the re-sort off) and the one enemy is put back at score 10
-- SET_ENEMY_PLAYER_PRIORITY(enemy, 10) after a clear.
  aipriofav  the wake as aipriodef (SET_ALL_ENEMY_PLAYERS_PRIORITIES 20: Player_1 and Soviet_4 one tier; the bench
             11-10 went for the far plant, the player's), then SET_FAVORED_ENEMY(Soviet_1, Soviet_4) in the same
             script. Predicted: the near plant (Soviet_4's) and never the far one. Without the clear (only "Soviet_4
             at 10") Player_1 at 20 would stay the top tier -> the far plant: the two readings tell them apart.
  [simulator predicted: 到远厂 (simai tells the clear as a priority of nobody: the model has no clear yet --
   work/re a220_favored_enemy.md, asked of engine line B)]
  BENCH 11-14 (round 220, run_queue, CampAIPrioFavA_mcp_1114_035402) PASS: 步兵在家 / 到近厂 / 到远厂 s1-s13 4 0 0 |
    s14 4 2 0 | s15 2 4 0 | s16-s21 0 4 0 | s22-s23 0 3 0 (then fewer: the turrets), 到远厂 0 to s69. The clear holds:
    Soviet_4 alone in the table, at 10 (aipriodef, without it: the far plant s25). Simulator after (sim.py records
    the clear, simai not yet): Player_1 20 / Soviet_4 10; simai since holds it (engine_aifav.readings.toml).
A295 (11-22), the same wake and expectations (program, work/re a295_clear_priorities.md: CLEAR_ALL calls the favored
enemy's clear itself; CLEAR_ONE takes one entry out, re-sort off; AUTO sets the sort, the override off, re-sorts):
  aiprioclr   CLEAR_ALL, then Soviet_4 10 (s07's use)  PASS CampAIPrioClrA_mcp_1122_003028: 到近厂 s16, 到远厂 never
  aiprioclr1  CLEAR_ONE Player_1                       PASS CampAIPrioClr1A_mcp_1122_002725: 到近厂 s15, 到远厂 never
  aiprioauto  AUTO NearestFirst_AllowTies              PASS CampAIPrioAutoA_mcp_1122_003641: 到近厂 s15, 到远厂 never --
              the re-sort puts the nearer enemy a tier above (aipriodef alone: the far plant). The simulator does not
              do it (no sort command in the model, asked of B) and takes the near plant by its one-tier rule: no reading.
"""
import registry
from checks import engine_aiprio as ap

FAVORED = 'SKIRMISH_AI_SET_FAVORED_ENEMY'
CLEAR_ALL = 'SKIRMISH_AI_CLEAR_ALL_ENEMY_PLAYERS_PRIORITIES'
CLEAR_ONE = 'SKIRMISH_AI_CLEAR_ENEMY_PLAYER_PRIORITY'
AUTO = 'SKIRMISH_AI_USE_AUTOMATIC_ENEMY_PLAYER_PRIORITY_SCHEME'
# build -> (mod name, what the wake adds after aipriodef's SET_ALL 20: (action, arguments after Soviet_1))
SET_ONE = 'SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY'
EXTRA = {     # fav / clr1: Player_1 a tier up first (30), so the action undone sends them to the far plant (review ss #6)
    'aipriofav': ('CampAIPrioFav', [(SET_ONE, 'p1', 30), (FAVORED, 's4')]),
    'aiprioclr': ('CampAIPrioClr', [(CLEAR_ALL,), (SET_ONE, 's4', 10)]),
    'aiprioclr1': ('CampAIPrioClr1', [(SET_ONE, 'p1', 30), (CLEAR_ONE, 'p1')]),
    'aiprioauto': ('CampAIPrioAuto', [(AUTO, 'NearestFirst_AllowTies')]),
}


def mission(build):
    m = registry.get().builds['aipriodef']()      # engine line B's build, through the registry (not its module)
    m.name, extra = EXTRA[build]
    wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
    arg = lambda x: m.player(x) if x in ('s4', 'p1') else x
    wake.do = list(wake.do) + [(act, m.player('s1'), *map(arg, rest)) for act, *rest in extra]
    return m


def a(m):
    """engine_aiprio's counters and its 到近厂 expectation (aiprio1's), plus never 到远厂 in the same window."""
    t = ap.a(m, 'aiprio1')
    t.expect.append(('到远厂', 1, '==', 0, m.facts['wake at'] + ap.AFTER))
    return t


MISSION = {k: (lambda k=k: mission(k)) for k in EXTRA}
CHECKS = {k: {'a': a} for k in EXTRA}
