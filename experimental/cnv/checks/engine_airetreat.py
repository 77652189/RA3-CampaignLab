"""Engine probe: the skirmish AI team's retreat and its EngagePassiveTargets switch (missions/airetreat_bench.py;
not benched yet: the readings and docs/engine/airetreat.md come with the first run).

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
