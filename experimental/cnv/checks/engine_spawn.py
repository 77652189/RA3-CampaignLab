"""Engine unit test: spawned and slaved objects (ADR 0019 layer 2, batch 4; docs/engine/spawn.md) -- the Allied war
factory's repair drones (SpawnBehavior: 3 at once, a dead one replaced 10 s later, all killed with the factory;
the drones' SlavedUpdate leash 200, their AttachUpdate flies to a hurt allied vehicle within 200).

On the range probe map (maps/probe_range.py, flat), three of the player's war factories, three power plants so none
is short of power (KillSpawnsOnDisabled):

  kill     'base gun'    NAMED_KILL at KILL: do its drones die with it?
  delete   'high gun'    NAMED_DELETE at KILL: are its drones taken away?
  keep     'order gun'   the control; a hurt Guardian ('near', NEAR north of it, 20 %) and another ('far', FAR
                         east, 20 %): which do its drones fly to? At ZAP everything of the player's within ZAP_R
                         of near is killed (UNIT_KILL_ALL_IN_AREA): near and the drone mending it. When is it
                         replaced?

Counters (the bench reads all four):
  无人机总数  the player's AlliedWarFactoryRepairDrone count
  厂旁     drones within AROUND of the keep factory (ones), the kill one (tens), the delete one (hundreds); 4 = 4+
  车旁     drones within 60 of near (ones), of far (tens)
  近车血量  near's health % (mended from 20 by an attached drone, 0 once zapped)
All drone counts by KindOf DRONE (see spawn_test: a template count does not see them).

Read (测, 2026-11-05, run CampSpawnSpawn_mcp_1105_052200, PASS; the bench's seconds ~1 s ahead of the timers):
  总数 9, 厂旁 333 from s1; s11 both doomed factories' drones gone together (9 -> 3, 333 -> 3); 车旁 1 from s1
  (3 at s2), 0 from s12; 近车 20 -> 58 by s10 (~5.5 %/s), 0 at s11. The zap killed near but not its drone (total
  stayed 3): the replace delay was not measured. docs/engine/spawn.md.
"""
from maps import probe_range
from parts import Script, Test, counted, kindof, square

FACTORY, DRONE = 'AlliedWarFactory', 'AlliedWarFactoryRepairDrone'
POWER, GUARDIAN = 'AlliedPowerPlant', 'AlliedAntiVehicleVehicleTech1'
SITES = {'kill': 'base gun', 'delete': 'high gun', 'keep': 'order gun'}
NEAR, FAR = 170.0, 380.0         # from the keep factory's centre (its footprint radius 60; the leash 200)
AROUND, ZAP_R = 300.0, 45.0
ZAP, KILL, RUN = 12.0, 12.0, 40.0


def mission():
    from parts import Mission
    m = Mission(name='CampSpawn', map=probe_range, units=[], facts={})
    for part, site in SITES.items():
        m.put(FACTORY, site, side='p1', role=f'{part} factory', name=f'UNIT - CNV Spawn {part.title()}')
    for k in (1, 2, 3):
        m.put(POWER, f'power {k}', side='p1', role=f'power {k}', name=f'UNIT - CNV Spawn Power {k}')
    m.put(GUARDIAN, SITES['keep'], 0, NEAR, side='p1', role='near', name='UNIT - CNV Spawn Near')
    m.put(GUARDIAN, SITES['keep'], FAR, 0, side='p1', role='far', name='UNIT - CNV Spawn Far')
    m.spawns.add(DRONE)                         # the factories make them: the counters may name the template
    return m


def spawn_test(m):
    t = Test()
    for part, site in SITES.items():
        t.areas[f'Test {part.title()}'] = square(*m.site(site), AROUND)
    t.areas['Test Near'] = square(*m.site(SITES['keep'], 0, NEAR), 60)
    t.areas['Test Far'] = square(*m.site(SITES['keep'], FAR, 0), 60)
    t.areas['Test Zap'] = square(*m.site(SITES['keep'], 0, NEAR), ZAP_R)
    p1 = m.player('p1')
    n = lambda part: m.role(part).name          # noqa: E731
    t.scripts.append(Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p1), ('UNIT_SET_HEALTH', n('near'), 20.0), ('UNIT_SET_HEALTH', n('far'), 20.0),
        ('SET_MILLISECOND_TIMER', 'Test Zap', ZAP), ('SET_MILLISECOND_TIMER', 'Test Kill', KILL)]))
    t.scripts.append(Script('Test - zap', [('TIMER_EXPIRED', 'Test Zap')],
                            [('UNIT_KILL_ALL_IN_AREA', p1, 'Test Zap')]))
    t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill')],
                            [('NAMED_KILL', n('kill factory')), ('NAMED_DELETE', n('delete factory'))]))
    # the drones are counted by KindOf DRONE (only the player has any): bench 11-05 run 051912, a template count
    # (SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER, PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA) read 0 throughout
    # while the drones flew about the keep factory
    drone = kindof('DRONE')
    t.areas['Test All'] = square(2500.0, 2500.0, 2700.0)
    counted('CNV_Spawn_All', '无人机总数', t, kind=drone, area='Test All', player=p1, most=12)

    def digits(counter, label, rows):
        """counter = sum over (area, step) of step x min(drones in the area, 4)"""
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for area, step in rows:
            for k in (1, 2, 3, 4):
                t.scripts.append(Script(f'Test - {counter} {area} {k}', [
                    ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 3, k, drone, area)],
                    [('INCREMENT_COUNTER', step, counter)], once=False))

    digits('CNV_Spawn_By', '厂旁', [('Test Keep', 1), ('Test Kill', 10), ('Test Delete', 100)])
    digits('CNV_Spawn_Car', '车旁', [('Test Near', 1), ('Test Far', 10)])
    counted('CNV_Spawn_Near', '近车血量', t, health=n('near'))
    # judged loosely (the bench's seconds run ~1 s ahead of the timers): 9 drones early; the killed and the deleted
    # factory's drones gone soon after KILL (厂旁 below 10); the keep factory has 3 again by the end
    t.expect = [('无人机总数', 0, 'ever>=', 9, ZAP - 2), ('厂旁', KILL + 8, '<', 10), ('厂旁', RUN - 2, '>=', 3)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
    return t


def _digits(t, counter, label, player, rows):
    """counter = sum over (step, condition maker) of step x min(k, 4) where condition(k) holds (k = 1 .. 4)."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    for step, cond in rows:
        for k in (1, 2, 3, 4):
            t.scripts.append(Script(f'Test - {counter} {step} {k}', [cond(k)], [('INCREMENT_COUNTER', step, counter)],
                                    once=False))


# --- engine_spawn_refill: how long until a dead drone is replaced? -------------------------------------------------
# Drones cannot be shot (KindOf AIRCRAFT DRONE NOT_AUTOACQUIRABLE, no VEHICLE: an airborne non-vehicle has victim
# mask 0 in Generals) and UNIT_KILL_ALL_IN_AREA passes them by (engine_spawn), so they are blown up: retail's
# S02_ExplodingMig (MaxHealth 1, FireWeaponWhenDead BaseExplodingPropVehicleWeapon: radius 100, 1000 GRENADE, allies
# enemies neutrals) is put by each of two hurt Guardians the keep factory's drones fly to mend, and killed by name.
# SpawnBehavior here: 3, InitialBurst 3, SpawnReplaceDelayData 10s.
# Read (测, 11-05, run CampFillRefill_mcp_1105_064054, PASS): 总数 3, 车旁 1111 by s4 (one drone on each car); blast 1
# at s8 -> 2 (the north mig gone, its drone with it), blast 2 at s11 -> 1; back to 2 at s18, 3 at s21: 10 s after
# each death. Both cars' health counters froze there (42, 53): dead. docs/engine/spawn.md 5.
MIG = 'S02_ExplodingMig'
REFILL_SITE, MIG_DX = 'order gun', 40.0
BLAST1, BLAST2, REFILL_RUN = 8.0, 11.0, 32.0


def refill_mission():
    from parts import Mission
    m = Mission(name='CampFill', map=probe_range, units=[], facts={})
    m.put(FACTORY, REFILL_SITE, side='p1', role='keep factory', name='UNIT - CNV Refill Keep')
    for k in (1, 2, 3):
        m.put(POWER, f'power {k}', side='p1', role=f'power {k}', name=f'UNIT - CNV Refill Power {k}')
    # north and west of the factory, NEAR from its centre; each mig MIG_DX further out (factory edge > 100 from it)
    m.put(GUARDIAN, REFILL_SITE, 0, NEAR, side='p1', role='north', name='UNIT - CNV Refill North')
    m.put(GUARDIAN, REFILL_SITE, -NEAR, 0, side='p1', role='west', name='UNIT - CNV Refill West')
    m.put(MIG, REFILL_SITE, MIG_DX, NEAR + MIG_DX, side='s1', role='north mig', name='UNIT - CNV Refill Mig North')
    m.put(MIG, REFILL_SITE, -NEAR - MIG_DX, -MIG_DX, side='s1', role='west mig', name='UNIT - CNV Refill Mig West')
    m.spawns.add(DRONE)
    return m


def refill_test(m):
    t = Test()
    p1 = m.player('p1')
    n = lambda part: m.role(part).name          # noqa: E731
    t.scripts.append(Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p1), ('UNIT_SET_HEALTH', n('north'), 20.0), ('UNIT_SET_HEALTH', n('west'), 20.0),
        ('SET_MILLISECOND_TIMER', 'Test Blast 1', BLAST1), ('SET_MILLISECOND_TIMER', 'Test Blast 2', BLAST2)]))
    t.scripts.append(Script('Test - blast 1', [('TIMER_EXPIRED', 'Test Blast 1')], [('NAMED_KILL', n('north mig'))]))
    t.scripts.append(Script('Test - blast 2', [('TIMER_EXPIRED', 'Test Blast 2')], [('NAMED_KILL', n('west mig'))]))
    drone = kindof('DRONE')
    t.areas['Test All'] = square(2500.0, 2500.0, 2700.0)
    t.areas['Test North'] = square(*m.site(REFILL_SITE, 0, NEAR), 60)
    t.areas['Test West'] = square(*m.site(REFILL_SITE, -NEAR, 0), 60)
    counted('CNV_Refill_All', '无人机总数', t, kind=drone, area='Test All', player=p1, most=6)
    in_area = lambda area: lambda k: ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 3, k, drone, area)  # noqa
    alive = lambda part: lambda k: ('NAMED_NOT_DESTROYED', n(part)) if k == 1 else ('NAMED_DESTROYED', n(part))  # noqa
    # ones: drones by north, tens: by west; hundreds: the north mig still there (k=1 only; k=2..4 add when it is
    # gone -- so 100 = there, 300 = gone), thousands: the west mig the same way
    _digits(t, 'CNV_Refill_By', '车旁', p1, [(1, in_area('Test North')), (10, in_area('Test West')),
                                            (100, alive('north mig')), (1000, alive('west mig'))])
    counted('CNV_Refill_North', '北车血量', t, health=n('north'))
    counted('CNV_Refill_West', '西车血量', t, health=n('west'))
    t.expect = [('无人机总数', 0, 'ever>=', 3, BLAST1 - 2),
                ('无人机总数', 13, '==', 1, 16), ('无人机总数', 19, '==', 2, 20),
                ('无人机总数', 24, '==', 3)]
    t.bench = [('bench_watch', dict(seconds=REFILL_RUN, every=1, sheet=False, lines=4))]
    return t


# --- engine_spawn_count: which objects does a template count miss? -------------------------------------------------
# engine_spawn: a template count read 0 for the factory's drones. Three cases, each in its own area of the player's:
#   factory  'order gun'    a war factory's 3 drones (SpawnBehavior, KindOf DRONE SUMMONED)
#   placed   'low gun'      one AlliedWarFactoryRepairDrone put on the map (a DRONE nobody spawned)
#   refinery 'probe refinery'  an Allied refinery's ore collector (SpawnBehavior, one shot, SpawnOnUnpack; HARVESTER)
#   miner    'removed gun'  one AlliedMiner put on the map (the control: a placed, not spawned, collector)
# Read (测, 11-05, run CampCountCount_mcp_1105_064248, PASS): 按模板 1100, 按种类 1113 (from s5 the placed miner has
# driven off: 100 / 113), 拥有无人机 0, 拥有矿车 2 -- no drone is counted by template, spawned or placed; the
# spawned miner is. docs/engine/spawn.md 2.
MINER, REFINERY = 'AlliedMiner', 'AlliedRefinery'
COUNT_SITES = {'factory': 'order gun', 'placed': 'low gun', 'refinery': 'probe refinery', 'miner': 'removed gun'}
COUNT_RUN = 20.0


def count_mission():
    from parts import Mission
    m = Mission(name='CampCount', map=probe_range, units=[], facts={})
    m.put(FACTORY, COUNT_SITES['factory'], side='p1', role='factory', name='UNIT - CNV Count Factory')
    m.put(DRONE, COUNT_SITES['placed'], side='p1', role='drone', name='UNIT - CNV Count Drone')
    # on the map's pad: it turns to face the pad's ore node (the map's)
    m.put(REFINERY, COUNT_SITES['refinery'], side='p1', role='refinery', name='UNIT - CNV Count Refinery')
    m.put(MINER, COUNT_SITES['miner'], side='p1', role='miner', name='UNIT - CNV Count Miner')
    for k in (1, 2, 3):
        m.put(POWER, f'power {k}', side='p1', role=f'power {k}', name=f'UNIT - CNV Count Power {k}')
    m.spawns.add(MINER)
    return m


def count_test(m):
    t = Test()
    p1 = m.player('p1')
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    for part, site in COUNT_SITES.items():
        t.areas[f'Test {part.title()}'] = square(*m.site(site), AROUND)
    tpl = lambda what, area: lambda k: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, k, what, area)  # noqa
    kind = lambda what, area: lambda k: ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 3, k, kindof(what),
                                         area)  # noqa: E731
    order = [('factory', DRONE, 'DRONE'), ('placed', DRONE, 'DRONE'), ('refinery', MINER, 'HARVESTER'),
             ('miner', MINER, 'HARVESTER')]
    # digit by digit in that order (ones = factory ... thousands = miner), each min(count, 4)
    _digits(t, 'CNV_Count_Tpl', '按模板', p1,
            [(10 ** i, tpl(what, f'Test {part.title()}')) for i, (part, what, _) in enumerate(order)])
    _digits(t, 'CNV_Count_Kind', '按种类', p1,
            [(10 ** i, kind(k, f'Test {part.title()}')) for i, (part, _, k) in enumerate(order)])
    counted('CNV_Count_OwnDrone', '拥有无人机', t, template=DRONE, player=p1)
    counted('CNV_Count_OwnMiner', '拥有矿车', t, template=MINER, player=p1)
    t.expect = [('按种类', 0, 'ever>=', 3, COUNT_RUN - 2)]
    t.bench = [('bench_watch', dict(seconds=COUNT_RUN, every=1, sheet=False, lines=4))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_spawn': mission, 'engine_spawn_refill': refill_mission, 'engine_spawn_count': count_mission}
CHECKS = {'engine_spawn': {'spawn': spawn_test}, 'engine_spawn_refill': {'refill': refill_test},
          'engine_spawn_count': {'count': count_test}}
