"""Engine line D round 148: GatherWaypoint, MaxTypesOfUnits, Priority=HOTSPOT (missions/aiteamfields_bench.py).
Three counters a build (a fourth reads '?'), once a second; the team states and members are in the CNVTeams log.

  aigath*   步兵在家 / 到路点 / 到远厂   Peacekeepers of s1 within 450 of the AI base, within 300 of the gather
            waypoint ('route 2'), within 300 of the far plant; 60 s after the wake
            expected (the program, work/re d130 section 1): aigathwp -- 到路点 ever >= 2, then 到远厂 ever >= 1;
            aigathno / aigathbad -- 到路点 0 all along, 到远厂 ever >= 1
  aimaxty*  坦克在家 / 步兵在家 / 标枪在家   Guardians / Peacekeepers / Javelins of s1 within 450 of the AI base
            expected at s40 (the model, ra3model/ai/teams.py: the first type met, in the order the units are offered;
            simai offers the Peacekeepers first, out s16): aimaxty1 -- 2 / 0 / 2; aimaxty3 -- 0 / 0 / 0 (out s18-21)
  aihot*    坦克总数 / 坦克在家 / 到目标   s1's Guardians; within 450 of the AI base; within 300 of the player's plant
            (the attack's ClosestStructure) -- to s69 (the attack state from s35, airelprio's transfer f541)
            expected: released (aihotstd, aihotscr, aicoophi, aidefhst) -- 到目标 ever >= 1 by s69; kept (aihotdef,
            aicoopsc, aidefhhi) -- 到目标 0 all along
"""
from checks import engine_aitarget as at
from parts import Script, Test, counted, square

HOME = 'CNV AI Base Area'
GATHER = 'CNV AI Gather Area'
TARGET = 'CNV AI Target Area'


def _reveal(m, t):
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[HOME] = square(*m.site('east base'), 450.0)


def gather(m):
    t = Test()
    _reveal(m, t)
    s1, (inf,) = m.player('s1'), m.cnv_units
    t.areas[GATHER] = square(*m.point('wp target'), 300.0)
    o = m.find(m.role('far plant').name)
    t.areas[at.FAR] = square(o.x, o.y, 300.0)
    counted('CNV_GW_Home', '步兵在家', t, template=inf, area=HOME, player=s1)
    counted('CNV_GW_Gather', '到路点', t, template=inf, area=GATHER, player=s1)
    counted('CNV_GW_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
    end = m.facts['wake at'] + 60.0
    if m.facts['gather waypoint']:
        t.expect += [('到路点', 1, 'ever>=', 2, end), ('到远厂', 1, 'ever>=', 1, end)]
    else:
        t.expect += [('到路点', 1, '==', 0, end), ('到远厂', 1, 'ever>=', 1, end)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


def max_types(m):
    t = Test()
    _reveal(m, t)
    s1 = m.player('s1')
    labels = ('坦克在家', '步兵在家', '标枪在家')
    for k, (unit, label) in enumerate(zip(m.cnv_units, labels)):
        counted(f'CNV_MT_{k}', label, t, template=unit, area=HOME, player=s1)
    want = (2, 0, 2) if m.facts['max types'] == 1 else (0, 0, 0)
    t.expect += [(label, 40.0, '==', n) for label, n in zip(labels, want)]
    t.bench = [('bench_watch', dict(seconds=50.0 + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


def hotspot(m):
    t = Test()
    _reveal(m, t)
    s1, tank = m.player('s1'), m.cnv_units[0]
    o = m.find(m.role('player target').name)
    t.areas[TARGET] = square(o.x, o.y, 300.0)
    counted('CNV_HS_Live', '坦克总数', t, template=tank, player=s1)
    counted('CNV_HS_Home', '坦克在家', t, template=tank, area=HOME, player=s1)
    counted('CNV_HS_Tgt', '到目标', t, template=tank, area=TARGET, player=s1)
    end = 69.0
    t.expect += [('坦克总数', 1, '==', 2)]
    t.expect += [('到目标', 1, 'ever>=', 1, end)] if m.facts['released'] else [('到目标', 1, '==', 0, end)]
    t.bench = [('bench_watch', dict(seconds=end, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {**{k: {'a': gather} for k in ('aigathwp', 'aigathno', 'aigathbad')},
          **{k: {'a': max_types} for k in ('aimaxty1', 'aimaxty3')},
          **{k: {'a': hotspot} for k in ('aihotstd', 'aihotdef', 'aihotscr', 'aicoophi', 'aicoopsc', 'aidefhst',
                                         'aidefhhi')}}
