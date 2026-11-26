"""HealCrateCollide (retail: a neutral HealCrate placed on 7 of the 27 maps). Four lanes of probe_range, each a neutral
crate at the lane's gun pad and a mover 200 west of it sent 200 east of it at 2 s -- through the crate:
On (switch) the retail crate, a Peacekeeper mover, and three Guardian tanks at rest: p1's 70 north and 180 north of
the crate, s2's 70 south; Off (low) the same with HealCrateCollide removed; Foe (removed) the retail crate, an s2
Peacekeeper mover; Veh (order) the retail crate, a p1 Guardian mover. Every mover and tank starts at 50%, NO_ATTACK.

Prediction from the data (HealCrate.xml: Range 100, filter INFANTRY HORDE VEHICLE HUGE_VEHICLE, CrateCollide's
IsHumanOnlyPickupInSinglePlayerCampaign default true; E146's movers sent *onto* the crate never took it): the On and
Veh movers take their crate as they pass -- it goes; the collector and the collector's units within 100 go to full
(On man, On near), not the far one, not s2's; Off's crate stays and heals none; Foe's s2 mover leaves its crate.
"""
from maps import probe_range
from parts import Mission, Script, Test, square
from checks import engine_scripts8 as s8
from checks.engine_objectbatch import clone, remove

MAN, TANK = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'
LANES = (('On', 'switch'), ('Off', 'low'), ('Foe', 'removed'), ('Veh', 'order'))
# lane: [(part, template, side, dx, dy)]; the mover is the first
CAST = {'On': [('man', MAN, 'p1', -200, 0), ('near', TANK, 'p1', 0, 70), ('far', TANK, 'p1', 0, 180),
               ('foe', TANK, 's2', 0, -70)],
        'Foe': [('man', MAN, 's2', -200, 0)], 'Veh': [('tank', TANK, 'p1', -200, 0)]}
CAST['Off'] = CAST['On']


def mission(real=False):
    """real (engine_healcrate_r, hypothesis 5): On, Foe and Veh place the retail HealCrate by its own name, no clone."""
    m = Mission(name='CampHCReal' if real else 'CampHealCrate', map=probe_range, units=[])
    for tag, lane in LANES:
        crate = clone('Neutral/Crates/HealCrate.xml', 'HealCrate', 'CNVHC' + tag)
        if tag == 'Off':
            remove(crate, 'HealCrateCollide')
        if not real or tag == 'Off':
            m.units.append(crate)
        m.put(crate.id if crate in m.units else 'HealCrate', lane + ' gun', side='neutral', role=tag + ' crate', name=f'HC {tag} crate')
        for part, template, side, dx, dy in CAST[tag]:
            m.put(template, lane + ' gun', dx, dy, side=side, role=f'{tag} {part}', name=f'HC {tag} {part}')
    return m


def check(m):
    t = Test()
    hurt = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    go = []
    for tag, lane in LANES:
        for part, *_ in CAST[tag]:
            name = m.role(f'{tag} {part}').name
            hurt += [('UNIT_SET_HEALTH', name, 50.0), ('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1)]
        x, y = m.site(lane + ' gun')
        t.waypoints[f'HC {tag} goal'] = (x + 200, y)
        go.append(('MOVE_NAMED_UNIT_TO', m.role(f'{tag} {CAST[tag][0][0]}').name, f'HC {tag} goal'))
    t.scripts.append(Script('Test - HC hurt', [], hurt))
    s8.at(t, 'go', 2., go)
    s8.total(t, 'HCCrate', '箱子位', [(2**k, ('NAMED_NOT_DESTROYED', m.role(tag + ' crate').name))
                                     for k, (tag, _) in enumerate(LANES)])
    full = [(tag, part) for tag in ('On', 'Off') for part in ('near', 'far', 'foe')] + [('Foe', 'man'), ('Veh', 'tank')]
    s8.total(t, 'HCFull', '满血位', [(2**k, ('UNIT_HEALTH', m.role(f'{tag} {part}').name, 3, 99))
                                    for k, (tag, part) in enumerate(full)])
    for tag in ('On', 'Off'):
        t.counters.append((f'HC{tag}Man', tag + ' 兵血'))
        t.scripts.append(Script(f'Test - HC {tag} man', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                              m.role(tag + ' man').name, f'HC{tag}Man')], once=False))
    s8.watch(t, 16., .5)
    return t


def passed(m):
    """b: a's 满血位 (0 throughout in a) traded for 路过位 -- a lane's bit once its mover has stood within 12 of its
    crate's centre (the crate's radius 9.7; latched): did the movers cross the crates at all?"""
    t = check(m)
    t.counters[1] = ('HCOver', '路过位')
    for k, (tag, lane) in enumerate(LANES):
        area = f'HC {tag} over'
        t.areas[area] = square(*m.site(lane + ' gun'), 12)
        t.scripts.append(Script(f'Test - HC {tag} over', [('NAMED_INSIDE_AREA', m.role(f'{tag} {CAST[tag][0][0]}').name,
                                                           area)], [('INCREMENT_COUNTER', 2**k, 'HCOver')]))
    return t


def ordered(m):
    """c: a without the script move -- the camera goes to On's crate at s1 and stays (the bench's steps take mission
    seconds: a move back at s6 came before the box), the bench boxes On's Peacekeeper and right-clicks 200 east of the
    crate: does the player's own order take it?"""
    t = check(m)
    t.scripts = [s for s in t.scripts if 'S8 go' not in s.name]
    x, y = m.site('switch gun')
    t.waypoints['HC view'] = (x, y)
    s8.at(t, 'view', 1., [('MOVE_CAMERA_TO', 'HC view', 0.5, 0.0, 1.0, 1.0)])
    run = t.bench[0][1]
    t.bench = [('bench_watch', dict(run, seconds=2.0)), ('bench_view', dict(x=x, y=y, look=True)),
               ('bench_box', dict(x0=x - 240, y0=y - 40, x1=x - 160, y1=y + 40, look=True)),
               ('bench_click', dict(x=x + 200, y=y, right=True, look=True)),
               ('bench_watch', dict(run, seconds=run['seconds'] - 2.0))]
    return t


HUMAN = 'id="ModuleTag_HealCrateCollide" IsHumanOnlyPickupInSinglePlayerCampaign="false"'
REL = 'Rule="ANY" Relationship="ALLIES ENEMIES NEUTRAL SAME_PLAYER"'
# engine_healcrate_h (D191's hypotheses): lane: (gun pad, crate edits, mover starts on the crate's centre, mover sent east)
HYP = {'Hum': ('switch', (HUMAN,), False, True), 'Sit': ('low', (), True, False),
       'Rel': ('removed', (REL,), False, True), 'All': ('order', (HUMAN, REL), True, True)}


def hypotheses():
    """engine_healcrate_h: a p1 Peacekeeper (50%, NO_ATTACK) per lane. Hum: the clone with
    IsHumanOnlyPickupInSinglePlayerCampaign false (H2: the bench is no campaign / p1 no human seat), mover sent through
    at 2 s as in a; Sit: the plain clone, the mover placed on the crate's centre and never ordered (H1: no collision
    ever happens); Rel: the clone's filter given Relationship ALLIES ENEMIES NEUTRAL SAME_PLAYER (H3), sent through;
    All: both edits, placed on the centre and sent through. Counters 箱子位 (lane k's crate stands: 2**k) and 满血位
    (lane k's mover >= 99%)."""
    m = Mission(name='CampHCHyp', map=probe_range, units=[])
    for tag, (lane, edits, sit, _) in HYP.items():
        crate = clone('Neutral/Crates/HealCrate.xml', 'HealCrate', 'CNVHC' + tag)
        for new in edits:
            old = new.split(' ')[0] if new.startswith('id=') else 'Rule="ANY"'
            crate.xml = crate.xml.replace(old, new, 1)
            assert new in crate.xml
        m.units.append(crate)
        m.put(crate.id, lane + ' gun', side='neutral', role=tag + ' crate', name=f'HC {tag} crate')
        m.put(MAN, lane + ' gun', 0 if sit else -200, 0, side='p1', role=tag + ' man', name=f'HC {tag} man')
    return m


def hyp_check(m):
    t = Test()
    hurt, go = [('MAP_REVEAL_ALL_PERM', m.player('p1'))], []
    for tag, (lane, _, _, move) in HYP.items():
        name = m.role(tag + ' man').name
        hurt += [('UNIT_SET_HEALTH', name, 50.0), ('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1)]
        if move:
            x, y = m.site(lane + ' gun')
            t.waypoints[f'HC {tag} goal'] = (x + 200, y)
            go.append(('MOVE_NAMED_UNIT_TO', name, f'HC {tag} goal'))
    t.scripts.append(Script('Test - HC hurt', [], hurt))
    s8.at(t, 'go', 2., go)
    s8.total(t, 'HCCrate', '箱子位', [(2**k, ('NAMED_NOT_DESTROYED', m.role(tag + ' crate').name))
                                     for k, tag in enumerate(HYP)])
    s8.total(t, 'HCFull', '满血位', [(2**k, ('UNIT_HEALTH', m.role(tag + ' man').name, 3, 99))
                                    for k, tag in enumerate(HYP)])
    s8.watch(t, 16., .5)
    return t


MISSION = {'engine_healcrate': mission, 'engine_healcrate_r': lambda: mission(True), 'engine_healcrate_h': hypotheses}
CHECKS = {'engine_healcrate': {'a': check, 'b': passed, 'c': ordered}, 'engine_healcrate_r': {'a': check},
          'engine_healcrate_h': {'a': hyp_check}}
CONTROL_ARMS = {'engine_healcrate': ('On', 'Off')}
