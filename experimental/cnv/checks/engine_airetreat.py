"""Engine probe: the skirmish AI team's retreat and its EngagePassiveTargets switch (missions/airetreat_bench.py;
docs/engine/aiteamstate.md; the simulator against these readings: tests/test_simai.py).

The probe's micro manager: StandardMicroManager_MEDIUM flattened, RetreatPowerAdvantage 0.2 and
<AIMicroManagerData RetreatMinDistanceFromBase> 300 instead of retail 900 (missions/airetreat_bench.py).
It reaches the team only through the TeamTemplate's MicroManager="..." naming it: airet / airet0 and aipas1 / aipas0
differ in one field of that data and nothing else, so the two pairs below are also the bench reading of TeamTemplate
MicroManager (the team runs the micro data its MicroManager names; B round 110).

Bench 2026-11-08 (all four PASS; wake at s10):
  airet   (步兵在家, 到远厂, 步兵数) 4 0 4 to s9 | out s10-s12 | 到远厂 2 @ s15-s16, 1 @ s17-s18 | home 1 @ s20 ... 4 @
          s26-s41 | out s42-s46 | 到远厂 2 @ s47-s48 | home 1 @ s49 ... 4 @ s54-s68 | out s69-s73 | 到远厂 2 @ s74-s76 |
          home 4 from s82; 步兵数 4 all along: the team turns round at the far plant's edge, walks home through the
          guards unhurt (a plain move), stands ~15 s, goes again -- a ~27-32 s cycle
  airet0  out s10-s12 | 到远厂 2 @ s15 ... 4 @ s17-s18 | 步兵数 3 @ s19, 2 @ s22, 1 @ s23, 0 from s25; never home again
  aipas1  旁厂血量 94 @ s11 (1 s after the wake), 3 @ s25, 1 from s26; the team within 450 of its base all the while
          (到旁厂 0: it shoots from beyond 120); 到远厂 0 to s85
  aipas0  out s10-s12 | 到远厂 2 @ s15, 4 @ s17-s34 | 旁厂血量 100 to s35, then (RAMPAGE: the nearest) 97 @ s36 ... 2 @
          s50; 到旁厂 3-4 @ s55-s57

  a  步兵在家 / 到远厂     Peacekeepers of s1 within 450 of the AI's base / 300 of the far power plant
     步兵数 (airet*)      Peacekeepers s1 owns
     到旁厂 / 旁厂血量 (aipas*)   s1's Peacekeepers within 120 of the side plant; its health in percent
     once a second, AFTER seconds after the wake

Expectations are the model's (RA3-EngineModel ra3model/ai/tactics.py TacticsBlock._team_state, simai.Brain.fight); a
FAIL is a reading too:
  airet   the team leaves, then some of it is back home (retreat) while alive
  airet0  the team leaves and nobody comes home (no retreat with RetreatPowerAdvantage 0)
  aipas1  the side plant is hurt (the team attacked the passive target on its way)
  aipas0  the side plant stays at 100 (EngagePassiveTargets off) and the team reaches the far plant
"""
from checks import engine_aitarget as at
from parts import Script, Test, counted, square

AFTER = 70.0
SIDE_AREA = 'CNV AI Side Plant Area'


def a(m, build):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[at.HOME] = square(*m.site('east base'), 450.0)
    o = m.find(m.role('far plant').name)
    t.areas[at.FAR] = square(o.x, o.y, 300.0)
    (inf,) = m.cnv_units
    counted('CNV_AR_Home', '步兵在家', t, template=inf, area=at.HOME, player=s1)
    counted('CNV_AR_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
    wake = m.facts['wake at']
    end = wake + AFTER
    if build.startswith('airet'):
        counted('CNV_AR_Count', '步兵数', t, template=inf, player=s1)
        t.expect += [('步兵在家', wake + 5, 'ever==', 0, end)]          # it left
        if build == 'airet':
            t.expect += [('步兵在家', wake + 15, 'ever>=', 1, end)]     # and some came back
        else:
            t.expect += [('步兵在家', wake + 15, '==', 0, end)]
    else:
        side = m.find(m.facts['side plant'])
        t.areas[SIDE_AREA] = square(side.x, side.y, 120.0)
        counted('CNV_AR_Side', '到旁厂', t, template=inf, area=SIDE_AREA, player=s1)
        counted('CNV_AR_SideHp', '旁厂血量', t, health=m.facts['side plant'])
        soon = wake + 25.0                      # before the far plant falls and RAMPAGE takes the nearest one
        if build == 'aipas1':
            t.expect += [('旁厂血量', 1, 'ever<', 100, soon)]
        else:
            t.expect += [('旁厂血量', 1, '==', 100, soon), ('到远厂', 1, 'ever>=', 1, soon)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('airet', 'airet0', 'aipas1', 'aipas0')}
