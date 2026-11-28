"""Enemy-priority counters shared with the script benches."""
from benches.ai.targets.checks import engine_aitarget
at = engine_aitarget()["shared"]
from parts import Script, Test, counted, square

AFTER = 60.0
PICK = {'aipriodef': '到远厂', 'aiprio1': '到近厂', 'aiprio0': '到近厂', 'aipriorm': None,
        'aisortf': None, 'aisortp': None, 'aisorts': '到近厂'}     # aisort*: the far plant is Soviet_4's


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
