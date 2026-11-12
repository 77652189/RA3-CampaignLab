"""A8's Liberty rewind (engine line D, user 11-11; missions/rewind_bench.py has the rules, units/rewind.py the
carrier). Counters: 血 = the carrier's health %, 回溯 = presses of its belt, 原处 = 1 while it is within 150 of
where it started, 归我 = 1 while it is the player's.

auto  (item 1) GO: health set to 60 %; GO + 3: teleported 400 east; GO + 5: NAMED_DAMAGE 100000 (fatal) -- alive,
      back where it was 3 s ago (原处 1) with that health (60); GO + 12, inside the cooldown: fatal again -- dead.
own   (item 2) GO: ours (control); GO + 1.5: fatal -- rewound to Soviet_1's carrier (ours 3 s ago: no), 归我 0.
ctrl  (item 3) GO: ours for CONTROL s, then Soviet_1's again (归我 1 then 0); nothing else.
trick (items 2 + 3) GO: ours; GO + 4: health 10 %, our two Multigunners force-attack it (NAMED_FORCE_ATTACK_NAMED:
      can they shoot an aircraft of their own?) and are stopped at the first rewind; ours 3 s before the fatal
      shot, so ours for good: 归我 1 after the control ends.
"""
from parts import Script, Test, counted, square

GO = 10.0
CONTROL = 15.0      # the launcher's hold, the mission's rule (control: ours, back CONTROL s later unless Rw Perm)


def _control(at):
    """Starts the mission's control rule at `at` (its timer Rw Control): checks ask the mission, never import it."""
    return Script('Test - control at', [], [('SET_MILLISECOND_TIMER', 'Rw Control', at), ('SET_FLAG', 'Rw Control On', 1)])


def _base(m, run, owner=False):
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test Go', GO)]))
    counted('Test Health', '血', t, health=m.role("carrier").name)
    t.counters.append(('Rw Rewinds', '回溯'))
    if owner:
        counted('Test Ours', '归我', t, owner=m.role("carrier").name)
    else:
        t.areas['Test Start'] = square(*m.waypoints[m.mark('start')], 150.0)
        counted('Test Home', '原处', t, named=m.role("carrier").name, area='Test Start')
    t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=len(t.counters)))]
    return t


def _at(t, tag, at, actions):
    t.scripts += [Script(f'Test - {tag} timer', [('TIMER_EXPIRED', 'Test Go')],
                         [('SET_MILLISECOND_TIMER', f'Test {tag}', at)]),
                  Script(f'Test - {tag}', [('TIMER_EXPIRED', f'Test {tag}')], actions)]


def still(m):
    """auto without the move: H1 (a moving carrier is not held at 1 hp) against H2 (one below full health is not)."""
    t = auto(m)
    t.scripts = [s if s.name != 'Test - hurt' else Script(s.name, s.when, s.do[:1]) for s in t.scripts]
    return t


def auto(m):
    """Bench 11-11 round 1 (CampRwAuto_mcp_1111_161159): UNIT_SET_HEALTH and UNIT_TELEPORT_TO_WAYPOINT did nothing
    to this carrier (血 100, 原处 1 throughout); the fatal blow was survived and rewound (回溯 1, 血 100), the one
    inside the cooldown killed it. So: hurt by NAMED_DAMAGE, moved by a move order, its track from ra3ext's probe."""
    t = _base(m, GO + 22)
    _at(t, 'hurt', 0.01, [('NAMED_DAMAGE', m.role("carrier").name, 2400), ('MOVE_NAMED_UNIT_TO', m.role("carrier").name, m.mark('away'))])
    _at(t, 'fatal', 8.0, [('NAMED_DAMAGE', m.role("carrier").name, 100000)])
    _at(t, 'fatal2', 15.0, [('NAMED_DAMAGE', m.role("carrier").name, 100000)])
    t.expect += [('血', GO + 2, '==', 60), ('回溯', GO + 11, '==', 1), ('血', GO + 11, '==', 60)]
    return t


def own(m):
    t = _base(m, GO + 8, owner=True)
    t.scripts.append(_control(GO))
    _at(t, 'fatal', 1.5, [('NAMED_DAMAGE', m.role("carrier").name, 100000)])
    t.expect += [('归我', GO + 1, '==', 1), ('回溯', GO + 5, '==', 1), ('归我', GO + 5, '==', 0)]
    return t


def ctrl(m):
    t = _base(m, GO + CONTROL + 6, owner=True)
    t.scripts.append(_control(GO))
    t.expect += [('归我', GO - 2, '==', 0), ('归我', GO + 3, '==', 1), ('归我', GO + CONTROL + 4, '==', 0)]
    return t


def trick(m):
    t = _base(m, GO + CONTROL + 8, owner=True)
    t.scripts.append(_control(GO))
    guns = [m.role(f'gun {k}').name for k in (1, 2)]
    _at(t, 'shoot', 4.0, [('UNIT_SET_HEALTH', m.role("carrier").name, 10)] + [('NAMED_FORCE_ATTACK_NAMED', g, m.role("carrier").name) for g in guns])
    t.scripts.append(Script('Test - hold fire', [('COUNTER', 'Rw Rewinds', 3, 1)], [('NAMED_STOP', g) for g in guns]))
    t.expect += [('归我', GO + 3, '==', 1), ('回溯', GO + CONTROL, '>=', 1), ('归我', GO + CONTROL + 6, '==', 1)]
    return t


def fire(m):
    """Item 3's question alone: ours (control) at GO, our two Multigunners ordered at GO + 2 to force-attack it
    (NAMED_FORCE_ATTACK_NAMED); 血 < 100 by GO + 12 = they shoot an aircraft of their own side."""
    t = _base(m, GO + 14, owner=True)
    t.scripts.append(_control(GO))
    _at(t, 'shoot', 2.0, [('NAMED_FORCE_ATTACK_NAMED', m.role(f'gun {k}').name, m.role("carrier").name) for k in (1, 2)])
    t.expect += [('归我', GO + 3, '==', 1), ('血', GO + 12, '<', 100)]
    return t


def swap(m):
    """rewind_swap (the show version): ours at 1 s for CONTROL s; our two Multigunners, 100 south of it, ordered at
    5 s to force-attack it (旧血 falling while 旧归我 1 = they shoot an aircraft of their own); at 24 s NAMED_DAMAGE
    5200 (whatever is left: the swap comes then at the latest). 新归我 / 新血: the new carrier's owner and health
    (50 % expected; its owner is whoever held the old one at the swap)."""
    new = m.role("new carrier").name
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test Go', 0.01)]))
    t.scripts.append(_control(1.0))
    _at(t, 'shoot', 5.0, [('NAMED_FORCE_ATTACK_NAMED', m.role(f'gun {k}').name, m.role("carrier").name) for k in (1, 2)])
    _at(t, 'finish', 10.0, [('NAMED_DAMAGE', m.role("carrier").name, 99999)])
    counted('Test Health', '旧血', t, health=m.role("carrier").name)
    counted('Test Ours', '旧归我', t, owner=m.role("carrier").name)
    counted('Test New Ours', '新归我', t, owner=new)
    counted('Test New Health', '新血', t, health=new)
    # bench CampRwSSwap_mcp_1111_163719: 旧血 98 -> 90 while ours (s1-s10: our guns shoot their own aircraft), the
    # swap at s12 (old deleted, its counters frozen), 新归我 1 and 新血 48-49 to the end (s37)
    t.expect += [('旧归我', 4, '==', 1, 10), ('旧血', 10, '<', 95), ('新血', 14, '>=', 45), ('新归我', 20, '==', 1)]
    t.bench = [('bench_watch', dict(seconds=34, every=1, sheet=False, lines=4))]
    return t


_ALL = {'fire': fire,'auto': auto, 'still': still, 'own': own, 'ctrl': ctrl, 'trick': trick}
CHECKS = {'rewind': _ALL, 'rewind_imm': _ALL, 'rewind_swap': {'swap': swap}}
