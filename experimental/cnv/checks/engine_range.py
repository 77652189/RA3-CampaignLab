"""Engine unit tests: what an upgrade's RANGE attribute modifier does to a turret (docs/engine/upgrades.md; A8's swell,
units/platform.py tide_gun, devices/rhythm.py). On the probe map (maps/probe_range.py) six of A8's turrets (retail's
sentry gun, AttackRange 300 / VisionRange 300, with two OBJECT upgrades: High = RANGE x2, Low = RANGE x0.6), the
player's, each with its own lane of engineers standing straight north of it at fixed distances. The engineers start
neutral (nobody shoots them) and are handed to the enemy at SHOW s, after the upgrades have been granted / removed,
so each turret meets its targets already in its final state.

  base     no upgrade                                     targets 250 / 450   (control: 250 in reach, 450 not)
  high     High at s0                                     targets 450 / 550   (x2 = 600: does it pick them itself?)
  order    High at s0, told at SHOW to attack the 450     target 450          (the weapon's reach, picked or not)
  removed  High at s0, High removed at SWAP               targets 250 / 450   (does the x2 go with the upgrade?)
  switch   s0: Low removed, High granted; SWAP: High removed, Low granted (the rhythm device's own two steps)
                                                          targets 150 / 250   (Low alone = 180; both kept = 360)
  low      Low at s0                                      targets 150 / 250   (x0.6 = 180)

A target counts once it is hurt or dead (a flag each, then its worth added once). Three counters (the bench reads the
first three lines):
  range A: base 250 = 1, base 450 = 10, high 450 = 100, high 550 = 1000
  range B: removed 250 = 1, removed 450 = 10, order 450 = 100
  range C: switch 150 = 1, switch 250 = 10, low 150 = 100, low 250 = 1000

Read (测, 2026-11-04, docs/engine/upgrades.md): swell 1 / 101 / 101 from s9 -- high picks neither 450 nor 550 itself
but its forced 450 is hit; reach 1110 / 101 / 101 -- base's forced 450 not hit, the SEEN gun picks 450 and 550
itself, removed's forced 450 not hit, order's (High again) hit, switch's forced 250 not hit. So: a removed upgrade's
modifier goes, a re-granted one comes back, two never stack here; RANGE moves the weapon, VISION the picking.
"""
from maps import probe_range
from parts import Mission, Script, Test
from units import platform

GUN = 'CNV_RangeGun'
TARGET = 'AlliedEngineer'
SWAP, SHOW, RUN = 4.0, 8.0, 40.0
COUNTERS = (('CNV_Range_A', '射程甲', (('base', 250), ('base', 450), ('high', 450), ('high', 550))),
            ('CNV_Range_B', '射程乙', (('removed', 250), ('removed', 450), ('order', 450))),
            ('CNV_Range_C', '射程丙', (('switch', 150), ('switch', 250), ('low', 150), ('low', 250))))


def _key(lane, d=None):
    return lane.title() + (f'{d:g}' if d is not None else '')


SEEN = 'CNV_RangeSeen'              # reach: the high lane's gun, whose High also doubles its VISION (retail's pairing:
                                    # AttributeModifier.xml line 56, RANGE 175% with VISION 250%)


def mission(seen=False):
    u = platform.tide_gun(id=GUN, high=2.0, low=0.6, vision=None)      # the control: RANGE alone (tide_gun now pairs it)
    units = [u]
    if seen:
        v = platform.tide_gun(id=SEEN, high=2.0, low=0.6, vision=2.0)
        # two copies of one retail file in one mod: its <Define> would be defined twice (BinaryAssetBuilder:
        # Critical, the build stops)
        v.xml = v.xml.replace('SOVIET_BASE_DEFENSE_GROUND_LOCAL_UNPACK_TIME', 'CNV_RANGE_SEEN_UNPACK_TIME')
        units.append(v)
    m = Mission(name='CampRange', map=probe_range, units=units, facts={})
    for lane in probe_range.LANES:
        tmpl = SEEN if seen and lane == 'high' else GUN
        m.put(tmpl, f'{lane} gun', role=f'{lane} gun', name=f'UNIT - CNV Range {_key(lane)} Gun')
        for d in probe_range.DISTANCES[lane]:
            m.put(TARGET, f'{lane} at {d:g}', side='neutral', role=f'{lane} target {d:g}',
                  name=f'UNIT - CNV Range {_key(lane, d)} Target')
    for k in range(3):
        m.put('SovietPowerPlant', f'power {k + 1}', role=f'power {k + 1}', name=f'UNIT - CNV Range Power {k + 1}')
    return m


def swell(m):
    t = Test()
    names = next(u for u in m.units if u.id == GUN).names
    high, low = names['on'], names['off']

    def gun(lane):
        return m.role(f'{lane} gun').name

    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Test Swap', SWAP),
             ('SET_MILLISECOND_TIMER', 'Test Show', SHOW)]
    start += [('NAMED_RECEIVE_UPGRADE', high, gun(lane)) for lane in ('high', 'order', 'removed')]
    start += [('NAMED_REMOVE_UPGRADE', low, gun('switch')), ('NAMED_RECEIVE_UPGRADE', high, gun('switch')),
              ('NAMED_RECEIVE_UPGRADE', low, gun('low'))]
    swap = [('NAMED_REMOVE_UPGRADE', high, gun('removed')),
            ('NAMED_REMOVE_UPGRADE', high, gun('switch')), ('NAMED_RECEIVE_UPGRADE', low, gun('switch'))]
    s1 = m.player('s1')
    show = [('NAMED_TRANSFER_OWNERSHIP_PLAYER', m.role(f'{lane} target {d:g}').name, s1)
            for lane in probe_range.LANES for d in probe_range.DISTANCES[lane]]
    show.append(('NAMED_ATTACK_NAMED', gun('order'), m.role('order target 450').name))
    t.scripts += [Script('Test - start', [], start), Script('Test - swap', [('TIMER_EXPIRED', 'Test Swap')], swap),
                  Script('Test - show', [('TIMER_EXPIRED', 'Test Show')], show)]
    for counter, label, targets in COUNTERS:
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)]))
        for k, (lane, d) in enumerate(targets):
            name, flag = m.role(f'{lane} target {d:g}').name, f'Test Range Hit {_key(lane, d)}'
            t.scripts += [Script(f'Test - hurt {_key(lane, d)}', [('UNIT_HEALTH', name, 0, 100)], [('SET_FLAG', flag, 1)]),
                          Script(f'Test - dead {_key(lane, d)}', [('NAMED_DESTROYED', name)], [('SET_FLAG', flag, 1)]),
                          Script(f'Test - hit {_key(lane, d)}', [('FLAG', flag, 1)],
                                 [('INCREMENT_COUNTER', 10 ** k, counter)])]
    # only the control is judged (the rest is what the test is for): some turret shot something
    t.expect = [('射程甲', 0, 'ever>', 0, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=4, sheet=False, lines=3))]
    return t


BACK = 6.0
REACH = (('CNV_Range_A', '射程甲', (('base', 450), ('base', 250), ('high', 450), ('high', 550))),
         ('CNV_Range_B', '射程乙', (('removed', 250), ('removed', 450), ('order', 450))),
         ('CNV_Range_C', '射程丙', (('switch', 150), ('switch', 250), ('low', 150), ('low', 250))))
FORCED = {'base': 450, 'removed': 450, 'order': 450, 'switch': 250, 'low': 250}


def reach(m):
    """swell's questions by the weapon's reach alone: each gun but the high lane's is told to attack one target (an
    immobile gun fires only if the target is within its weapon's range), so what it picks itself does not matter.
      base     no upgrade, told to attack the 450                (control: 300 does not reach it)
      high     the SEEN gun (High = RANGE x2 and VISION x2), nobody told: does it pick 450 / 550 itself now?
      order    s0 High; SWAP High -> Low; BACK Low -> High (the device's steps), told to attack the 450 (High again?)
      removed  s0 High; SWAP High removed; told to attack the 450  (does the x2 go with the upgrade?)
      switch   s0 Low removed, High granted; SWAP High removed, Low granted; told to attack the 250 (360 if both stay)
      low      Low at s0, told to attack the 250                  (control: 180)
    Counters: range A base 450 = 1, base 250 = 10, high 450 = 100, high 550 = 1000; range B removed 250 = 1,
    removed 450 = 10, order 450 = 100; range C switch 150 = 1, switch 250 = 10, low 150 = 100, low 250 = 1000."""
    t = Test()
    names = next(u for u in m.units if u.id == GUN).names
    high, low = names['on'], names['off']
    seen_high = next(u for u in m.units if u.id == SEEN).names['on']

    def gun(lane):
        return m.role(f'{lane} gun').name

    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Test Swap', SWAP),
             ('SET_MILLISECOND_TIMER', 'Test Back', BACK), ('SET_MILLISECOND_TIMER', 'Test Show', SHOW + 1),
             ('NAMED_RECEIVE_UPGRADE', seen_high, gun('high'))]
    start += [('NAMED_RECEIVE_UPGRADE', high, gun(lane)) for lane in ('order', 'removed')]
    start += [('NAMED_REMOVE_UPGRADE', low, gun('switch')), ('NAMED_RECEIVE_UPGRADE', high, gun('switch')),
              ('NAMED_RECEIVE_UPGRADE', low, gun('low'))]
    swap = [('NAMED_REMOVE_UPGRADE', high, gun('removed'))]
    swap += [a for lane in ('order', 'switch') for a in (('NAMED_REMOVE_UPGRADE', high, gun(lane)),
                                                         ('NAMED_RECEIVE_UPGRADE', low, gun(lane)))]
    back = [('NAMED_REMOVE_UPGRADE', low, gun('order')), ('NAMED_RECEIVE_UPGRADE', high, gun('order'))]
    s1 = m.player('s1')
    show = [('NAMED_TRANSFER_OWNERSHIP_PLAYER', m.role(f'{lane} target {d:g}').name, s1)
            for lane in probe_range.LANES for d in probe_range.DISTANCES[lane]]
    show += [('NAMED_ATTACK_NAMED', gun(lane), m.role(f'{lane} target {d}').name) for lane, d in FORCED.items()]
    t.scripts += [Script('Test - start', [], start), Script('Test - swap', [('TIMER_EXPIRED', 'Test Swap')], swap),
                  Script('Test - back', [('TIMER_EXPIRED', 'Test Back')], back),
                  Script('Test - show', [('TIMER_EXPIRED', 'Test Show')], show)]
    for counter, label, targets in REACH:
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)]))
        for k, (lane, d) in enumerate(targets):
            name, flag = m.role(f'{lane} target {d:g}').name, f'Test Range Hit {_key(lane, d)}'
            t.scripts += [Script(f'Test - hurt {_key(lane, d)}', [('UNIT_HEALTH', name, 0, 100)], [('SET_FLAG', flag, 1)]),
                          Script(f'Test - dead {_key(lane, d)}', [('NAMED_DESTROYED', name)], [('SET_FLAG', flag, 1)]),
                          Script(f'Test - hit {_key(lane, d)}', [('FLAG', flag, 1)],
                                 [('INCREMENT_COUNTER', 10 ** k, counter)])]
    t.expect = []
    t.bench = [('bench_watch', dict(seconds=RUN, every=4, sheet=False, lines=3))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_range': mission, 'engine_reach': lambda: mission(seen=True)}
CHECKS = {'engine_range': {'swell': swell}, 'engine_reach': {'reach': reach}}
