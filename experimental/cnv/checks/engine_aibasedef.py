"""Engine probe: the skirmish AI team's EnterBaseDefenses (missions/aibasedef_bench.py; docs/engine/aiteamstate.md).

  a  进炮塔     s1's objects with status ENCLOSED (someone is inside a turret)
     炮塔数     AlliedBaseDefense s1 owns
     步兵数     Peacekeepers s1 owns (in a turret too)
     到远厂     Peacekeepers of s1 within 300 of the far power plant
     once a second, AFTER seconds after the wake

Expectations are the model's (l4_micro_engage.md 1.7); a FAIL is a reading too:
  aibd1     进炮塔 reaches 1 or more
  aibd0 / aibdidle  进炮塔 stays 0
  aibdwho   (counters 进炮塔 旁1 旁2 旁3: Peacekeepers of s1 within NEXT of turret 1 / 2 / 3, in it too) 进炮塔 reaches 1
  aibdpre   (as aibdwho; turret 1 holds a fifth Peacekeeper from s0) 进炮塔 reaches 2 (the full turret skipped)

aibdidle: <AIMicroManagerData EnterBaseDefensesWhenIdle> true with EnterBaseDefenses false; aibd1 / aibdwho:
EnterBaseDefenses true, WhenIdle false (missions/aibasedef_bench.py).

Readings (11-09, all PASS; counters 进炮塔 炮塔数 步兵数 到远厂; the AI's 4 AlliedBaseDefense 200 north of the far plant):
  aibd1     s1-s14 0 4 4 0 | s15-17 到远厂 2,3,4 | s18-s20 0 3 4 4 | s21-s25 1 3 4 4 | s26-s32 1 2 3 3 | s33-s75 1 2 2 2
            -- one Peacekeeper in a turret from s21 to the end (alive: the others die by s33, a turret lost per ~5 s)
  aibd0     s18-s25 0 3 4 4 | s26-s28 0 2 4 4 | s29 0 2 3 3 | s30 0 2 2 2 | s31-32 0 2 1 1 | s33-s75 0 2 0 0
  aibdidle  the same as aibd0 (进炮塔 0 all along; team dead by s33)
  aibdwho   PASS (进炮塔 旁1 旁2 旁3): s16 0 0 1 0 | s17-18 0 0 2 1 | s19-20 0 1 2 0 | s21 1 2 1 0 | s22 1 3 0 0 | s23 1 2 1 0 |
            s24 1 2 2 0 | s25 1 1 1 1 | s26-76 1 0 0 2 -- the men gather at turret 1 (3 next to it at s22), one goes in at
            s21, the rest drift off: read as all sent to the first turret of the list in one pass (no place kept for
            the earlier ones), not as 'the others were beyond 150'. Not proved (a man inside is not counted in 旁k).
  aibdpre   FAIL (11-09, 进炮塔 旁1 旁2 旁3): s1-15 1 1 0 0 (the sitter, counted in 旁1) | s16 1 1 1 0 | s17 1 1 2 1 |
            s18-19 1 1 3 0 | s20-25 1 2 3 0 | s26-29 0 1 3 0 (turret 1 lost, the sitter with it) | ... | s46-75 0 0 0 0
            -- 进炮塔 never passes 1: with turret 1 full nobody goes into turret 2 or 3, though 3 stand by turret 2
            (s18-25); one walks up to the full turret 1 (旁1 2, s20-25). Read: the full turret is NOT skipped -- the
            pass still takes the list's first turret (0x8de960's 0x864100 'can the order be done' does not look at
            room, INFERRED), the men leave the team for it and stay out. Not a 'one per pass' rule: then one would have
            gone into turret 2.
"""
from checks import engine_aitarget as at
from parts import Script, Test, counted, square, status

AFTER = 60.0
NEXT = 40.0                              # the turrets stand 80 apart: the squares do not overlap


def a(m, build):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    o = m.find(m.role('far plant').name)
    t.areas[at.FAR] = square(o.x, o.y, 300.0)
    (inf,) = m.cnv_units
    counted('CNV_BD_In', '进炮塔', t, status=status('ENCLOSED'), player=s1)
    if build == 'aibdpre':
        t.scripts.append(Script('Test - sit', [], [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY',
                                                       m.role('sitter').name, m.role('turret 1').name)]))
    if build in ('aibdwho', 'aibdpre'):
        for k in (1, 2, 3):
            tur = m.find(m.role(f'turret {k}').name)
            area = f'CNV_BD_Next{k}'
            t.areas[area] = square(tur.x, tur.y, NEXT)
            counted(f'CNV_BD_N{k}', f'旁{k}', t, template=inf, area=area, player=s1)
    else:
        counted('CNV_BD_Turrets', '炮塔数', t, template=m.role('turret 1').template, player=s1)
        counted('CNV_BD_Count', '步兵数', t, template=inf, player=s1)
        counted('CNV_BD_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
    wake = m.facts['wake at']
    end = wake + AFTER
    if build in ('aibd1', 'aibdwho'):
        t.expect += [('进炮塔', 1, 'ever>=', 1, end)]
    elif build == 'aibdpre':                 # the model: a full turret is skipped, one more goes into turret 2
        t.expect += [('进炮塔', 1, 'ever>=', 2, end)]
    else:
        t.expect += [('进炮塔', 1, '==', 0, end)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('aibd1', 'aibd0', 'aibdidle', 'aibdwho', 'aibdpre')}
