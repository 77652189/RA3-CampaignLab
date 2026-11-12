"""PassiveTargetSearchDistance diagnostic, not coverage from damage alone.

Read team state/target/member positions from the same run's CNVTeams log.
The script frame counter and index anchors prevent wall-clock substitution.
INFERRED prediction: radius 600 hurts the side plant, 0/200 leave it intact
before logic frame 525. Preserve rejected predictions; never fit thresholds.
Evidence and open distance-origin hypotheses: work/re/e104_passive_distance.md.

MEASURED: aipsdz/aipsdt/aipsds/aipsdl all select the side plant at frame 140
(state 6, four members, tactical target differs), state 0 at 320. The target
command supplies the side plant's coordinates. At selection the team centre
is 350.3 away; every member is 324.3 or farther away, including radius 1/200.
All four diagnostics retain the rejected survival prediction (FAIL): later
defences kill the team; by frame 605 its membership is empty. The >=600-frame
gate passes. Preserve these readings, not wall-clock HP comparisons.
"""
from model import Script, Test, counted, square


def probe(m):
    t = Test()
    t.scripts = [Script('Passive - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                 Script('Passive - clock', [], [('INCREMENT_COUNTER', 1, 'CNV_PD_Frame')], once=False)]
    t.counters.append(('CNV_PD_Frame', '帧数'))
    counted('CNV_PD_Own', '存活', t, template=m.cnv_units[0], player=m.player('s1'))
    counted('CNV_PD_HP', '旁厂血量', t, health=m.facts['side plant'])
    far = m.find(m.role('far plant').name)
    t.areas['CNV_PD_Far'] = square(far.x, far.y, 300)
    counted('CNV_PD_Far', '到远厂', t, template=m.cnv_units[0],
            player=m.player('s1'), area='CNV_PD_Far')
    t.expect = [('帧数', 1, 'ever>=', 600, 55), ('存活', 1, '==', 4, 55)]
    t.bench = [('bench_watch', dict(seconds=57, every=2, sheet=False, lines=4))]
    return t


CHECKS = {name: {'r': probe} for name in ('aipsdz', 'aipsdt', 'aipsds', 'aipsdl')}
