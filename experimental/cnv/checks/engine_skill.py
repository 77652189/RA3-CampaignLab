"""Engine probe: the ice engineer's skill (AssembleStructureSpecialAbilityUpdate, ReloadTime 20 s, ForbiddenObjectRange 32,
PATHABLE_ONLY) cast by script, NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT (missions/skill_bench.py; docs/engine/specialpower.md
sec. 2 found a script ignores a super power's reload -- does a unit's skill too?).

Every spot's counter, from its order: 1 x frames before its core is first seen + 1000 x frames a core stands in the
square (half 40) round it. So units = the frame the core came (counted from that order; if it never comes, the frames
of the run), thousands = how long it stood (~82 frames if it did).
  a  one engineer, three points in range: C1 at ORDER, C2 at ORDER+8 s (assembly over, reload not), C3 at ORDER+25 s
  b  three engineers, a tank (NO_ATTACK) beside each spot at 20 / 40 / 60: 禁20 禁40 禁60 (all ordered at ORDER)
  c  engineer Ec on the plaza top: P1 (60 away, cliff edge) at ORDER, P2 (120 away, on the face) at ORDER+25 s;
     engineer Ed 400 from a plain point D: 悬1 悬2 平D, and 走D (Ed's frames away from his start after the order)
  w  engineer on the west shore, the point 100 out in the sea: 水
bench 2026-11-07 (units = frames from the order to the core; thousands = frames it stood; the order itself at s21):
  a CampSkillA  C1 82002, C2 82003, C3 82003: C2 (ordered 8 s after C1: assembly over, 20 s reload NOT) came at once,
                2-3 frames after its order -- a script's cast ignores the unit skill's ReloadTime (and BusyDuringAssembly).
  b CampSkillB  禁20 / 禁40 / 禁60 all 82002: a tank 20, 40 or 60 (centre) from the point blocks nothing -- the core came
                in 2 frames each; ForbiddenObjectRange 32 does not act on a scripted cast (the tank, our own and idle).
  c CampSkillC  悬1 82004 (dark cliff cell), 悬2 82002 (grey strip on the cliff's foot, maybe walkable -- not proof):
                cores came 2-4 frames after the order, the engineer did not walk. 平D (point 400 away): core at
                frame 103 (he walks first), 走D from frame 13 after the order: he walks first, as expected.
  w CampSkillW  水 82004: a core stands 100 out in the sea, 4 frames after the order: PATHABLE_ONLY not checked for
                a scripted cast either. (Player-click variant d not run.)
"""
from parts import Script, Test, square

ORDER, LATE, RUN_FOR = 21.0, 25.0, 15.0


def skill_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    cases = []      # (counter id, label, engineer role, spot part, order timer name, delay)
    if which == 'a':
        cases = [('A1', 'C1', 'engineer a', 'a1', 0.0), ('A2', 'C2', 'engineer a', 'a2', 8.0),
                 ('A3', 'C3', 'engineer a', 'a3', 25.0)]
    elif which == 'b':
        cases = [(f'B{k}', f'禁{int(d)}', f'engineer b{k}', f'b{k}', 0.0) for k, d in ((1, 20), (2, 40), (3, 60))]
    elif which == 'w':
        cases = [('W', '水', 'engineer w', 'w', 0.0)]
    elif which == 'c':
        cases = [('P1', '悬1', 'engineer c', 'c1', 0.0), ('P2', '悬2', 'engineer c', 'c2', 25.0),
                 ('QD', '平D', 'engineer d', 'd', 0.0)]
    start = [('MAP_REVEAL_ALL_PERM', p1)]
    start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'tank {k}').name, 'NO_ATTACK', 1) for k in (1, 2, 3)]
    delays = sorted({c[4] for c in cases})
    start += [('SET_MILLISECOND_TIMER', f'Test Ord {int(d)}', ORDER + d) for d in delays]
    t.scripts.append(Script('Test - start', [], start))
    run = ORDER + max(delays) + RUN_FOR
    for ident, label, role, part, d in cases:
        flag, seen, cname = f'Test Ordered {ident}', f'Test Seen {ident}', f'CNV_Skill_{ident}'
        t.areas[f'Test Skill {ident}'] = square(*m.point(part), 40.0)
        t.scripts.append(Script(f'Test - order {ident}', [('TIMER_EXPIRED', f'Test Ord {int(d)}')],
                                [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(role).name, m.ability(role, 'freeze'),
                                  m.mark(part)), ('SET_FLAG', flag, 1)]))
        core = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, 'CNV_SkillSeed', f'Test Skill {ident}')
        t.scripts += [
            Script(f'Test - seen {ident}', [('FLAG', flag, 1), core], [('SET_FLAG', seen, 1)], once=False),
            Script(f'Test - before {ident}', [('FLAG', flag, 1), ('FLAG', seen, 0)],
                   [('INCREMENT_COUNTER', 1, cname)], once=False),
            Script(f'Test - core {ident}', [('FLAG', flag, 1), core], [('INCREMENT_COUNTER', 1000, cname)], once=False)]
        t.counters.append((cname, label))
    if which == 'c':
        # Ed's walk: frames since his order that no engineer stands within 30 of his start
        t.areas['Test Skill Dstart'] = square(*m.point('d start'), 30.0)
        t.scripts.append(Script('Test - Ed away', [('FLAG', 'Test Ordered QD', 1),
                                                   ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 2, 0,
                                                    'CNV_SkillEng', 'Test Skill Dstart')],
                                [('INCREMENT_COUNTER', 1, 'CNV_Skill_Walk')], once=False))
        t.counters.append(('CNV_Skill_Walk', '走D'))
    t.bench = [('bench_watch', dict(seconds=run, every=4, sheet=False, lines=len(t.counters)))]
    t.expect = []
    return t


CHECKS = {'engine_skill': {w: (lambda m, w=w: skill_test(m, w)) for w in 'abcw'}}
