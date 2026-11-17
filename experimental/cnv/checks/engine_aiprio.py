"""Engine probe: SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY (missions/aiprio_bench.py; program: work/re l4_aiswitches.md;
model: RA3-EngineModel ra3model/ai/player.py set_enemy_priority, simai.Brain.switches).

  a  步兵在家 / 到近厂 / 到远厂   Peacekeepers of s1 within 450 of the AI's base / 300 of the near (Soviet_4's) / far
     (the player's) power plant, once a second, 60 s after the wake

Expectations are the program's (read, work/re l4_aiswitches.md 2b: the re-sort off, the player's entry taken out,
put back at score n when n > 0 without asking the enemy list; tiers by score, the top one searched first):
  aipriodef  到远厂 (the program says both enemies one tier -> 到近厂; the bench said otherwise, see 读数)
  aiprio1    到近厂 (Soviet_4 30 above Player_1 10)
  aiprio0    到近厂 (Player_1 0: out of the table, Soviet_4 alone in it)
  aipriorm   nobody leaves (the table empty at the wake: only what the script names is in it)

读数
Bench 2026-11-10 (one run each):
  aipriodef  CampAIPrioDefA_mcp_1110_234833: 步兵在家 4 to s19, 0 from s21; 到远厂 2 @ s25, 4 s26-s44, 0 from s47 (the
             plant down); 到近厂 2 @ s55, 3 s56-s75 (RAMPAGE). Soviet_4 is an enemy to the objects (RAMPAGE goes for
             its plant), and in SET_ALL's table (aiprio0); with two enemies in one tier the farther structure won.
             Why is NOT READ (the in-tier count rule with ties by id says near): tests/test_simai.py strict xfail.
  aiprio1    CampAIPrio1A_mcp_1110_235356 PASS: 到近厂 2 @ s14, 4 s15-s21, then fewer (the turrets), never 到远厂.
  aiprio0    CampAIPrio0A_mcp_1110_235746: 到近厂 2 @ s15, 4 s16-s22, never 到远厂 -- the first expectation (nobody
             leaves) was wrong: Soviet_4 was in SET_ALL's table, Player_1 0 left it alone in the top tier.
  aipriorm   CampAIPrioRmA_mcp_1111_000210: 步兵在家 4 s1-s75, nobody anywhere -- the table was empty when the script
             changed it: an entry not named is not there (Player_1 out too).
"""
from checks import engine_aitarget as at
from parts import Script, Test, counted, square

AFTER = 60.0
PICK = {'aipriodef': '到远厂', 'aiprio1': '到近厂', 'aiprio0': '到近厂', 'aipriorm': None}


def a(m, build):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[at.HOME] = square(*m.site('east base'), 450.0)
    for area, role in ((at.NEAR, 'near plant'), (at.FAR, 'far plant')):
        o = m.find(m.role(role).name)
        t.areas[area] = square(o.x, o.y, 300.0)
    (inf,) = m.cnv_units
    counted('CNV_AP_Home', '步兵在家', t, template=inf, area=at.HOME, player=s1)
    counted('CNV_AP_Near', '到近厂', t, template=inf, area=at.NEAR, player=s1)
    counted('CNV_AP_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
    end = m.facts['wake at'] + AFTER
    t.expect += [(PICK[build], 1, 'ever>=', 1, end)] if PICK[build] else [('步兵在家', 1, '==', 4, end)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in PICK}
