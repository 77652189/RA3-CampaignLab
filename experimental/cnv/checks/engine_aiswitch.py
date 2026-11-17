"""Engine probe: the skirmish AI's script switches SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES, SKIRMISH_AI_USE_REPAIRS,
SKIRMISH_AI_USE_REBUILD_SYSTEM (missions/aiswitch_bench.py; docs/engine/aiswitches.md).

  a  步兵在家 / 到近厂 / 到远厂   Peacekeepers of s1 within 450 of the AI's base / 300 of the near / far power plant
     电厂血量 (aiswrep*)       the AI's own plant's health in percent (set to 50 at the start)
     电厂数 (aiswreb*)         AlliedPowerPlants s1 owns (its own one is killed 5 s after the wake)
     once a second, AFTER seconds after the wake

Expectations are the model's (RA3-EngineModel ra3model/ai/player.py, simai.Brain.switches); a FAIL is a reading too:
  aisw0near  nobody leaves (priorities 0 empty the enemy table: ClosestStructure finds no enemy structure)
  aisw0far   the team reaches the far plant (a NamedObject target does not look at the enemy table)
  aiswrep1 / aiswrep0   the plant stays at 50 (the program's gate would let 1 repair; the bench says it does not)
  aiswreb1 / aiswreb0   no plant again after the kill (the model rebuilds nothing; who reads the list is NOT READ)

读数
Bench 2026-11-08 (one run each; Sonnet ran, B read):
  aisw0near  PASS. 步兵在家 4 s1-s75, nobody at either plant: priorities 0 empty the enemy table, no team goes.
  aisw0far   PASS. 步兵在家 0 from s12; 到远厂 2 @ s15, 4 s17-s33, 0 from s35 (the plant down); then 到近厂 1 @ s42,
             4 s44-s51 (RAMPAGE), 0 from s66: a NamedObject target ignores the enemy table, RAMPAGE too.
  aiswrep1   FAIL against the first expectation (>= 51): 电厂血量 50 s1-s75 -- repairs 1 did not repair in 60 s
             (money 0 at the time? a brain flag? the personality bit? open). The team went to the near plant at s13.
  aiswrep0   电厂血量 50 s1-s107 (the watch ran slow after s75, so the s69 reading was missing: FAIL by no row).
  aiswreb1   PASS. 电厂数 1 to s12, 0 from s14 to s120 (5000 money): rebuild 1 did not put the plant back in 105 s.
  aiswreb0   PASS. 电厂数 0 from s14 to s119, as reb1.
"""
from checks import engine_aitarget as at
from parts import Script, Test, counted, square

AFTER = {'aiswreb1': 90.0, 'aiswreb0': 90.0}
PLANT = 'AlliedPowerPlant'


def a(m, build):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[at.HOME] = square(*m.site('east base'), 450.0)
    for area, role in ((at.NEAR, 'near plant'), (at.FAR, 'far plant')):
        o = m.find(m.role(role).name)
        t.areas[area] = square(o.x, o.y, 300.0)
    (inf,) = m.cnv_units
    counted('CNV_AS_Home', '步兵在家', t, template=inf, area=at.HOME, player=s1)
    counted('CNV_AS_Near', '到近厂', t, template=inf, area=at.NEAR, player=s1)
    counted('CNV_AS_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
    wake = m.facts['wake at']
    end = wake + AFTER.get(build, 60.0)
    if build.startswith('aiswrep'):
        counted('CNV_AS_Health', '电厂血量', t, health=m.facts['own plant'])
        t.expect += [('电厂血量', end - 1, '==', 50, end)]
    elif build.startswith('aiswreb'):
        counted('CNV_AS_Plants', '电厂数', t, template=PLANT, player=s1)
        t.expect += [('电厂数', m.facts['kill at'] + 2, '==', 0, end)]
    elif build == 'aisw0near':
        t.expect += [('步兵在家', 1, '==', 4, end)]
    else:
        t.expect += [('到远厂', 1, 'ever>=', 1, end)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in
          ('aisw0near', 'aisw0far', 'aiswrep1', 'aiswrep0', 'aiswreb1', 'aiswreb0')}
