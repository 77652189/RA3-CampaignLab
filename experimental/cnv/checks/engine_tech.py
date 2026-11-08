"""Engine probe: the Allied tech upgrade (Upgrade_AlliedTech2) and what it lets a war factory build (the Guardian
tank, AlliedAntiVehicleVehicleTech1, NeededUpgrade Upgrade_AlliedTech2, 950). Mission missions/tech_bench.py: yard,
power plant, a war factory inside the yard's TechUpgrade radius (600 rectangular) and one outside; variants delete
the factory they do not use.

  a  nothing given, click the Guardian         b  GIVE_PLAYER_UPGRADE Tech2, click the Guardian
  c  yard NAMED_RECEIVE_UPGRADE (near factory) d  same, only the far factory
  e  the player buys Tech2 on the yard, then the Guardian    g  only the near factory receives Tech2
  h  yard AND the far factory (750 from the yard) both receive Tech2 by script, only the far factory stands
The yard's Tech2 button (structures tab, row 3 col 2) needs an ore refinery (tooltip: needs refinery), so the mission
places one. Counters: 资金, 守护者, 二级持有 / 三级持有 (0..3: PLAYER_HAS_NUM_UNITS_WITH_UPGRADE n = 1, 2, 3 -> the
highest n that holds, i.e. how many of the player's objects carry the upgrade), 帧数 (e: frames from the first money
below the start while no Guardian).

Bench 11-07 (Guardian clicked by hand coordinates at ~s16; the missions' money 4000, Guardian 950):
  a CampTechA  nothing given: money stays 4000, no Guardian; 二级持有 0 and 三级持有 0 all run (nobody holds Tech2/3).
  b CampTechB  GIVE_PLAYER_UPGRADE (Player_1, Upgrade_AlliedTech2): 二级持有 0 (no object takes it), money 4000, no
               Guardian: the player-level give does not unlock the Guardian.
  c CampTechC  yard NAMED_RECEIVE_UPGRADE, near factory (300 away): 二级持有 2 from s1 (yard + factory), money 4000 ->
               3050 over s17..s19 (950 paid), Guardian 1 from s19. PASS (expect ever>= 1).
  d CampTechD  same, only the far factory (750 from the yard): 二级持有 1 (the yard alone), money 4000 flat, no
               Guardian: the TechUpgrade radius (600, rectangular) does govern buildability.
  g CampTechG  only the near factory receives Tech2 directly: 二级持有 1 (the factory), money flat, no Guardian.
  h CampTechH  yard and the far factory both receive: 二级持有 2, no Guardian (money only rises: refinery income).
  e CampTechE  the player buys Tech2 on the yard (tab click ~s16.6): money falls ~6.1-7 a frame net of income (3626 at
               帧数 94 -> 3013 at 186, then 3000), 二级持有 2 at 帧数 195 (~15 s = 225 frames from the click), then
               the Guardian button works (3050 paid, Guardian 1 at 帧数 824).
"""
from parts import Script, Test, counted, square

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'      # the Guardian (NeededUpgrade Upgrade_AlliedTech2): G5, no mission import

MONEY = 4000
UP2, UP3 = 'Upgrade_AlliedTech2', 'Upgrade_AlliedTech3'
RUN = {'a': 25.0, 'b': 25.0, 'c': 25.0, 'd': 25.0, 'e': 60.0, 'g': 25.0, 'h': 25.0}
DELETE = {'a': ('Far',), 'b': ('Far',), 'c': ('Far',), 'd': ('Near',), 'e': ('Far',), 'g': ('Far',), 'h': ('Near',)}
# sidebar coordinates (screen pixels 1280 x 720); None until found by hand
VEH_TAB, GUARD_BUTTON = (1200.0, 251.0), (1136.0, 368.0)      # vehicle tab, the Guardian's button (greyed: needs Tech2)
STR_TAB, YARD_UP_BUTTON = (1120.0, 251.0), (1188.0, 415.0)    # structures tab, row 3 col 2 (tech upgrade)


def _n(part):
    return f'UNIT - CNV Tech {part}'


def _holders(t, counter, label, up, p1):
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    for n in (1, 2, 3):
        t.scripts.append(Script(f'Test - {counter} {n}', [('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', p1, n, up)],
                                [('SET_COUNTER', counter, n)], once=False))


def tech_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, MONEY)]
    start += [('NAMED_DELETE', _n(p)) for p in DELETE[which]]
    keep = 'Far' if which in ('d', 'h') else 'Near'
    if which == 'b':
        start.append(('GIVE_PLAYER_UPGRADE', p1, UP2))
    if which in ('c', 'd', 'h'):
        start.append(('NAMED_RECEIVE_UPGRADE', UP2, _n('Yard')))
    if which in ('g', 'h'):
        start.append(('NAMED_RECEIVE_UPGRADE', UP2, _n(keep)))
    t.scripts.append(Script('Test - start', [], start))
    t.counters.append(('CNV_Tech_Money', '资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Tech_Money')], once=False))
    t.scripts.append(Script('Test - paying', [('COUNTER', 'CNV_Tech_Money', 0, MONEY)], [('SET_FLAG', 'Test Paying', 1)]))
    counted('CNV_Tech_Made', '守护者', t, template=GUARDIAN, most=3)
    _holders(t, 'CNV_Tech_Up2', '二级持有', UP2, p1)
    if which == 'a':
        _holders(t, 'CNV_Tech_Up3', '三级持有', UP3, p1)
    if which == 'e':
        t.counters.append(('CNV_Tech_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [('FLAG', 'Test Paying', 1), ('COUNTER', 'CNV_Tech_Made', 2, 0)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Tech_Frames')], once=False))
    t.expect = [('守护者', 0, 'ever>=', 1, 40.0)] if which == 'c' else []     # c: the one variant that builds by script
    watch = dict(every=0.5, sheet=False, lines=len(t.counters))
    steps = [('bench_watch', dict(watch, seconds=2.0))]
    if which == 'e' and YARD_UP_BUTTON[0] is not None:
        steps += [('bench_click', dict(x=STR_TAB[0], y=STR_TAB[1], world=False, look=False)),
                  ('bench_click', dict(x=YARD_UP_BUTTON[0], y=YARD_UP_BUTTON[1], world=False, look=False)),
                  ('bench_watch', dict(watch, seconds=25.0))]
    if VEH_TAB[0] is not None:
        steps += [('bench_click', dict(x=VEH_TAB[0], y=VEH_TAB[1], world=False, look=False)),
                  ('bench_click', dict(x=GUARD_BUTTON[0], y=GUARD_BUTTON[1], world=False, look=False))]
    steps.append(('bench_watch', dict(watch, seconds=RUN[which])))
    t.bench = steps
    return t


CHECKS = {'engine_tech': {w: (lambda m, w=w: tech_test(m, w)) for w in 'abcdegh'}}
