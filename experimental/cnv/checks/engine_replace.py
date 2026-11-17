"""Engine unit test: ReplaceSelfSpecialAbility (the MCV deploying; docs/engine/construction.md) -- two questions the
round-45 reading (engine_build a: ordered to deploy at its own spot, the MCV is gone in the 7th script pass after the
order, carrying UNPACKING meanwhile) left open:

  f  far   as engine_build a, but the deploy point is FAR east of the MCV: is the wait a drive to the point (more
           frames with the distance) or a fixed delay?
  g  bad   as engine_build a with our MCV copy whose ReplacementTemplate names no object: when no new object can be
           made, does the old MCV stay or go (the code goes on to destroy it)?

Counters as engine_build (帧数, 状态帧, 建成帧 = 1 x yard frames in the area + 1000 x MCV frames in the area, 血量 by
the MCV's name). The area here is the square of half-side AREA around the MCV and the point.
"""
import os

import labpaths
from checks import engine_build as eb
from parts import Unit, square

FAR = 100.0                             # f: the deploy point this far east of the MCV
AREA = 200.0
BAD_MCV, NO_SUCH = 'CNVBadMCV', 'CNVNoSuchObject'
RUN = {'f': 14.0, 'g': 14.0}


def _sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def bad_mcv(target=NO_SUCH):
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', 'AlliedMCV.xml'), encoding='utf-8').read()
    x = _sub1(x, 'id="AlliedMCV"', f'id="{BAD_MCV}"')
    x = _sub1(x, 'EditorName="AlliedMCV"', f'EditorName="{BAD_MCV}"')
    x = _sub1(x, '<ReplacementTemplate>AlliedConstructionYard</ReplacementTemplate>',
              f'<ReplacementTemplate>{target}</ReplacementTemplate>')
    i = x.index('<GameObject\n\t\tid="AlliedMCV_Naval"')
    j = x.index('</GameObject>', i) + len('</GameObject>')
    x = x[:i] + x[j:]
    return Unit(BAD_MCV, x, what='盟军基地车的复制：展开目标模板不存在（测创建失败）')


def mission(which='f', control=False):
    m = eb.mission()
    m.name = 'CampRepl' if which == 'f' else ('CampReplCopy' if control else 'CampReplBad')
    if which == 'g':
        m.units = [bad_mcv(eb.YARD if control else NO_SUCH)]
        m.spawns |= {BAD_MCV}
        for o in m.objects:
            if o.name == eb._n('MCV'):
                o.template = BAD_MCV
        m.cast['mcv'].template = BAD_MCV
    else:
        m.waypoint('mcv spot', 'Test MCV Spot', eb.MCV_AT[0], eb.MCV_AT[1] + FAR, eb.MCV_AT[2])
    return m


def test(m, which):
    t = eb.build_test(m, 'a')
    mx, my = m.site(*eb.MCV_AT)
    t.areas['Test Target'] = square(mx + (FAR / 2 if which == 'f' else 0.0), my, AREA)
    if which == 'g':                        # the MCV counted in the area is our copy
        for s in t.scripts:
            s.when = [tuple(BAD_MCV if v == eb.MCV else v for v in c) for c in s.when]
    t.expect = [('帧数', 0, 'ever>=', 1, RUN[which])]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which]))]
    return t


MISSION = {'engine_replace': lambda: mission('f'), 'engine_replace_bad': lambda: mission('g'),
           'engine_replace_copy': lambda: mission('g', control=True)}
CHECKS = {'engine_replace': {'f': lambda m: test(m, 'f')}, 'engine_replace_bad': {'g': lambda m: test(m, 'g')},
          'engine_replace_copy': {'h': lambda m: test(m, 'g')}}
