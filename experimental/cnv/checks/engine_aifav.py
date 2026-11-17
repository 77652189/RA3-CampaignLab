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
    the clear, simai not yet): Player_1 20 / Soviet_4 10 -- tests/test_simai_favored.py strict xfail.
"""
import registry
from checks import engine_aiprio as ap

FAVORED = 'SKIRMISH_AI_SET_FAVORED_ENEMY'


def mission():
    m = registry.get().builds['aipriodef']()      # engine line B's build, through the registry (not its module)
    m.name = 'CampAIPrioFav'
    wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
    wake.do = list(wake.do) + [(FAVORED, m.player('s1'), m.player('s4'))]
    return m


def a(m):
    """engine_aiprio's counters and its 到近厂 expectation (aiprio1's), plus never 到远厂 in the same window."""
    t = ap.a(m, 'aiprio1')
    t.expect.append(('到远厂', 1, '==', 0, m.facts['wake at'] + ap.AFTER))
    return t


MISSION = {'aipriofav': mission}
CHECKS = {'aipriofav': {'a': a}}
