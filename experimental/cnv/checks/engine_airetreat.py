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
Bench 2026-11-10 (B round 112, both PASS; the state on a map flag at the wake s10, off at s18; the two differ only in
the tactic's DisbandAfterRetreatTeamSize):
  airetf  (0, xsd default) out s19-s21 | 到远厂 2 @ s24-s25 | home 4 @ s31-s48 | out again s49-s54 | 到远厂 2-3 @
          s54-s58 | home 3 @ s64-s79 (步兵数 3 from s57) | out again s80-s84: the tactic goes on with its state off
  airetfd (999) out s18-s20 | 到远厂 2 @ s24-s25 | home 1 @ s29, 2 @ s30, 4 from s31 to s85: the retreat's end ended
          the tactic, the team was let go, and with the state off no new team -- DisbandAfterRetreatTeamSize as read
          (retreat check, work/re/l4_states.md: was state 1, now 8, members <= the size -> end)

  a  步兵在家 / 到远厂    Peacekeepers of s1 within 450 of the AI's base / 300 of the far power plant
     步兵数 (airet*)      Peacekeepers s1 owns
     到旁厂 / 旁厂血量 (aipas*)   s1's Peacekeepers within 120 of the side plant; its health in percent
     once a second, AFTER seconds after the wake

Expectations are the model's (RA3-EngineModel ra3model/ai/tactics.py TacticsBlock._team_state, simai.Brain.fight); a
FAIL is a reading too:
  airet   the team leaves, then some of it is back home (retreat) while alive
  airetd  as airet (DisbandAfterRetreatTeamSize 999 under an always-on state: a new team at once, no reading)
  airetf  the state on a flag, off 8 s after the wake: the team comes home, then out again (simulator s32 home, s42 out)
  airetfd airetf + DisbandAfterRetreatTeamSize 999: home, and all four home from wake + 35 to the end (simulator: the
          tactic ends at s36, no new team)
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
        if build in ('airet', 'airetd'):
            t.expect += [('步兵在家', wake + 15, 'ever>=', 1, end)]     # and some came back
        elif build == 'airetf':                                         # back, then out again (the tactic goes on)
            t.expect += [('步兵在家', wake + 15, 'ever==', 4, end), ('步兵在家', wake + 35, 'ever==', 0, end)]
        elif build == 'airetfd':                                        # back, and home for good (the tactic ended)
            t.expect += [('步兵在家', wake + 15, 'ever==', 4, end), ('步兵在家', wake + 35, '==', 4, end)]
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


CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('airet', 'airetd', 'airetf', 'airetfd', 'airet0', 'aipas1', 'aipas0')}
