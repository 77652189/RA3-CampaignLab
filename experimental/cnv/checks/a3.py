"""A3 checks (the plan's, docs/story/plans/a3.md; the time-stop zone devices/stasis.py).

win: the three phases by test script: the observatory crowd teleported to the first pier, then a peacekeeper to the
  trapped squad and the engineers to the dock, then the church's people to the dock: the goals complete, the mission
  is won (ended, and no lost flag). The player's part (the chase, the lane, the zone's edge) is the live play's.
freeze: nobody does anything for ~2:10 (no endings, so a lost fight does not end it): the zone's rings are read
  (device flags: ring one on from the start, ring two 2:00 into phase 1); the player's objects IN_STASIS and the
  enemy's (the allied platoon and the Soviet raiders inside ring one are stopped, whoever they belong to; the start
  platoon, outside, is not); ring two's growth stops the east road's new tanks where they are made.
"""
import hashlib

from checks.a6 import lost_counter
from parts import Script, Test, counted, status

GO = 3.0
STEP = 6.0
WIN_BY = GO + 3 * STEP + 18.0
FREEZE_RUN = 135.0      # ring two comes at 2:00 (the bench's seconds run up to ~1 s ahead of the mission's timers)
FROZEN_ALLIES = 3       # the plan's 'frozen ally' platoon, inside ring one from the first frame
FROZEN_FOES = 3         # 'frozen soviet'


def ring_flag(k, device='时停区', tag='A3'):
    """The flag the zone device sets while its ring k is on (devices/stasis.py ring_flag: a check does not import the
    device; tests/test_stasis.py holds the two spellings together)."""
    return f'CNV_{tag}_Beat{hashlib.sha1(device.encode("utf-8")).hexdigest()[:5]}_Ring_{k}'


def _timer(t, name, at, acts):
    t.scripts += [Script(f'Test - {name} set', [], [('SET_MILLISECOND_TIMER', f'Test {name}', at)]),
                  Script(f'Test - {name}', [('TIMER_EXPIRED', f'Test {name}')], acts)]


def _parts(m, group):
    return [r.name for r in (m.roles(group) or [m.role(group)])]


def win(m):
    t = Test()
    for site in ('greenwich pier', 'trapped squad', 'deptford dock'):
        t.waypoints[f'Test {site}'] = tuple(m.site(site))
    _timer(t, 'one', GO, [('UNIT_TELEPORT_TO_WAYPOINT', n, 'Test greenwich pier') for n in _parts(m, 'civ a')])
    _timer(t, 'two', GO + STEP, [('UNIT_TELEPORT_TO_WAYPOINT', _parts(m, 'peace')[0], 'Test trapped squad')] +
           [('UNIT_TELEPORT_TO_WAYPOINT', n, 'Test deptford dock') for n in _parts(m, 'eng')])
    _timer(t, 'three', GO + 2 * STEP, [('UNIT_TELEPORT_TO_WAYPOINT', n, 'Test deptford dock')
                                       for n in _parts(m, 'civ c')])
    lost_counter(t)
    t.expect += [('输了', 0, '==', 0, GO + 2 * STEP - 1), ('ENDED', WIN_BY, '', None)]
    t.bench = [('bench_watch', dict(seconds=WIN_BY, every=3, sheet=False, lines=len(t.counters)))]
    return t


def freeze(m):
    m.drop_endings()
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    rings = [ring_flag(k) for k in range(5)]
    t.counters.append(('Test Rings', '圈开着'))
    t.scripts.append(Script('Test - rings zero', [], [('SET_COUNTER', 'Test Rings', 0)], once=False))
    t.scripts += [Script(f'Test - rings {k}', [('FLAG', f, 1)], [('INCREMENT_COUNTER', 10 ** k, 'Test Rings')], once=False)
                  for k, f in enumerate(rings)]
    counted('Test Stop Mine', '我方停住', t, status=status('IN_STASIS'), most=12)
    counted('Test Stop Foe', '敌方停住', t, status=status('IN_STASIS'), player=m.player('s1'), most=12)
    # ring one on after the first frames; the allied platoon stopped and nothing else of ours (the start platoon is out)
    t.expect = [('圈开着', 5, '==', 1, 100.0), ('我方停住', 5, '==', FROZEN_ALLIES, 100.0),
                ('敌方停住', 5, '>=', FROZEN_FOES, 100.0), ('圈开着', FREEZE_RUN, '==', 11, FREEZE_RUN + 5)]
    t.bench = [('bench_watch', dict(seconds=FREEZE_RUN + 5, every=5, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a3': {'win': win, 'freeze': freeze},
}
