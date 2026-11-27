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
import re

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


def collect(m):
    """Right-click the visible retail crate itself. The same camera in c puts its top at screen (640, 346)."""
    t = ordered(m)
    t.bench[3] = ('bench_click', dict(x=640, y=346, world=False, right=True, look=True))
    t.expect = [('箱子位', 0, 'ever==', 14), ('On 兵血', 0, 'ever==', 100)]
    return t


def recalled(m):
    """c (G1 of a397_crate.md): b's crate click, then -- On's Peacekeeper halfway, inside 20 of 100 west of the crate --
    a script move to 200 east of it, through it (the bench's steps are ~10 s apart: a second click comes after the
    pickup). 满血位 traded for 改令位: 1 the move given, 2 within 12 of the crate's centre after it (latched).
    Predicted the crate kept (the new order ending the collect state); measured: he ends on the crate and takes it."""
    t = collect(m)
    t.counters[1] = ('HCRecall', '改令位')
    x, y = m.site('switch gun')
    man = m.role('On man').name
    t.areas['HC half'], t.areas['HC over'] = square(x - 100, y, 20), square(x, y, 12)
    t.scripts += [Script('Test - HC recall', [('NAMED_INSIDE_AREA', man, 'HC half')],
                         [('MOVE_NAMED_UNIT_TO', man, 'HC On goal'), ('INCREMENT_COUNTER', 1, 'HCRecall')]),
                  Script('Test - HC recalled over', [('NAMED_INSIDE_AREA', man, 'HC over'), ('COUNTER', 'HCRecall', 2, 1)],
                         [('INCREMENT_COUNTER', 2, 'HCRecall')])]
    t.expect.append(('改令位', 0, 'ever==', 3))
    return t


HUMAN = 'id="ModuleTag_HealCrateCollide" IsHumanOnlyPickupInSinglePlayerCampaign="false"'
REL = 'Rule="ANY" Relationship="ALLIES ENEMIES NEUTRAL SAME_PLAYER"'
# engine_healcrate_h (D191's hypotheses): lane: (gun pad, crate edits, mover starts on the crate's centre, mover sent east)
HYP = {'Hum': ('switch', (HUMAN,), False, True), 'Sit': ('low', (), True, False),
       'Rel': ('removed', (REL,), False, True), 'All': ('order', (HUMAN, REL), True, True)}


LIFE = ('<Behaviors>', '<Behaviors><LifetimeUpdate id="ModuleTag_CNVLife" MinLifetime="12s" MaxLifetime="12s" />')


def hypotheses(verify=False):
    """engine_healcrate_h (verify: engine_healcrate_v, each edited clone also given a 12 s LifetimeUpdate -- its crate
    gone from 箱子位 at ~14 s says the game ran the edited XML): a p1 Peacekeeper (50%, NO_ATTACK) per lane. Hum: the clone with
    IsHumanOnlyPickupInSinglePlayerCampaign false (H2: the bench is no campaign / p1 no human seat), mover sent through
    at 2 s as in a; Sit: the plain clone, the mover placed on the crate's centre and never ordered (H1: no collision
    ever happens); Rel: the clone's filter given Relationship ALLIES ENEMIES NEUTRAL SAME_PLAYER (H3), sent through;
    All: both edits, placed on the centre and sent through. Counters 箱子位 (lane k's crate stands: 2**k) and 满血位
    (lane k's mover >= 99%)."""
    m = Mission(name='CampHCHyp' + 'V' * verify, map=probe_range, units=[])
    for tag, (lane, edits, sit, _) in HYP.items():
        crate = clone('Neutral/Crates/HealCrate.xml', 'HealCrate', 'CNVHC' + tag)
        edits += (LIFE[1],) * (verify and bool(edits))
        for new in edits:
            old = new.split(' ')[0] if new.startswith('id=') else LIFE[0] if new == LIFE[1] else 'Rule="ANY"'
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


SECRET_FILES = (('CNVSecretFile1', 'switch'), ('CNVSecretFile2', 'low'), ('HealCrate', 'removed'))
FILE_TEAM = 'PlyrNeutral/teamCNVSecretFiles'


def secret_file(k):
    """Uprising's SS_SecretFile<k> (Y01 / Y02; in no RA3 stream or map) with the HealCrate's art and RA3's schema:
    RA3's CrateCollide has no KillOnPickup, its AttributeCrateCollide no ApplyToSelf (the build stops on them), so
    both go -- what is left is RA3's crate: modifier to the collector, crate gone on pickup. Its modifier (Uprising's
    static stream: ModelConditionsSet USER_1, nothing else -- a400_ocl_attack.md) comes along under a new id; the
    client sound, portraits and collapse OCL (Uprising-only assets) go."""
    new = f'CNVSecretFile{k}'
    u = clone(f'Civilian/Shiro_Sanitarium_SS/Buildings/SS_SecretFile{k}.xml', f'SS_SecretFile{k}', new)
    heal = clone('Neutral/Crates/HealCrate.xml', 'HealCrate', new).xml
    x = re.sub(r'<Include[^>]*source="(ART|DATA:(Civilian|BaseObjects))[^"]*"\s*/>|(KillOnPickup|ApplyToSelf)="\w+"',
               '', u.xml)
    x = x.replace('</Includes>', '<Include type="all" source="ART:NPHealCrate.w3x" /></Includes>')
    for tag in ('Draws', 'ClientBehaviors', 'CreateObjectDie', 'ObjectCreationList'):
        x = re.sub(rf'<{tag}\b.*?</{tag}>', re.search(rf'<{tag}\b.*?</{tag}>', heal, re.S).group()
                   if tag == 'Draws' else '', x, count=1, flags=re.S)
    x = re.sub(r'(SelectPortrait|ButtonImage)="\w+"', lambda g: re.search(g.group(1) + '="\\w+"', heal).group(), x)
    x = x.replace('"AttributeModifier_SecretFile"', f'"{new}Mod"').replace(
        '</AssetDeclaration>', f'<AttributeModifier id="{new}Mod" ModelConditionsSet="USER_1" /></AssetDeclaration>')
    u.xml = x
    return u


def secret_files_mission():
    """E270 (A400 ②): the two secret-file clones and the retail HealCrate, created by one script action."""
    m = Mission(name='CampSecretFile', map=probe_range, units=[secret_file(1), secret_file(2)])
    m.ext = True
    m.teams['secretFiles'] = FILE_TEAM
    for template, lane in SECRET_FILES:
        site = lane + ' gun'
        m.spawns.add(template)
        m.waypoint(lane, 'File point ' + lane, site)
        m.put(MAN, site, -130, -12, side='p1', role=lane + ' mover', name='File mover ' + lane)
    return m


def secret_files(m):
    """Three neutral crates made by one script action, a Peacekeeper sent through each by a script move.

    Predicted: all three made and kept (mask 7: a script move is no collect order, a397_crate.md), all movers
    cross (7), no crate shows USER_1 (0: RA3 hangs the modifier on the collector, and none collects).
    E270's first run measured 4/7/0 on a build the files were never in (a400_ocl_attack.md).
    """
    t = Test()
    create, move = [], []
    live = []
    for k, (template, lane) in enumerate(SECRET_FILES):
        crate = 'File ' + lane
        mover = m.role(lane + ' mover').name
        bit = 2**k
        create.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', crate, template,
                       FILE_TEAM, m.mark(lane)))
        live.append((bit, ('NAMED_NOT_DESTROYED', crate)))
        x, y = m.site(lane + ' gun')
        point = 'File goal ' + lane
        t.waypoints[point] = (x + 130, y - 12)
        area = 'File footprint ' + lane
        t.areas[area] = square(x, y - 12, 10)
        move.append(('MOVE_NAMED_UNIT_TO', mover, point))
        t.scripts.append(Script('Test - file crossed ' + lane, [('NAMED_INSIDE_AREA', mover, area)],
                                [('INCREMENT_COUNTER', bit, 'FileCross')]))
        if k < 2:
            t.scripts.append(Script('Test - file lid ' + lane, [('UNIT_HAS_MODELCONDITION', crate, 'USER_1')],
                                    [('INCREMENT_COUNTER', bit, 'FileLid')]))
    s8.at(t, 'file create', 1., create)
    s8.at(t, 'file move', 3., move)
    s8.total(t, 'FileLive', '存活', live)
    t.counters.extend([('FileCross', '经过'), ('FileLid', '箱盖')])
    s8.frames(t, 'FileClock', '帧', [])
    t.expect = [('存活', 0, '==', 7), ('经过', 0, 'ever==', 7), ('箱盖', 0, '==', 0)]
    s8.watch(t, 14., .5)
    return t


def collect_file(m):
    """b: a without the script moves -- r b's camera, box and crate pixel on secret file 1 (the switch lane): its
    Peacekeeper (set to 50%) right-clicks the file. a's 经过 and 箱盖 traded for 盖 (recounted: lane k's mover shows
    USER_1 2**k, file k's 8 * 2**k) and 兵血 (the collector's). Predicted from the clone: that file goes (存活 6), its
    collector wears USER_1 and keeps it (盖 1; the modifier has no Duration), its HealCrateCollide fills him (兵血 100).
    Measured (CampSecretFileB_mcp_1127_062800): 6 and 1 as predicted, 兵血 50 throughout -- the heal did not run."""
    t = secret_files(m)
    t.scripts = [s for s in t.scripts if not s.name.startswith(('Test - S8 file move', 'Test - file '))]
    t.counters = [c for c in t.counters if c[0] not in ('FileCross', 'FileLid')]
    x, y = m.site('switch gun')
    man = m.role('switch mover').name
    t.scripts += [Script('Test - file hurt', [], [('UNIT_SET_HEALTH', man, 50.0)]),
                  Script('Test - file man', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', man, 'FileMan')], once=False)]
    t.counters.append(('FileMan', '兵血'))
    s8.total(t, 'FileWear', '盖', [(2**k, ('UNIT_HAS_MODELCONDITION', m.role(lane + ' mover').name, 'USER_1'))
                                   for k, (_, lane) in enumerate(SECRET_FILES)] +
             [(8 * 2**k, ('UNIT_HAS_MODELCONDITION', 'File ' + lane, 'USER_1')) for k, (_, lane) in enumerate(SECRET_FILES[:2])])
    t.waypoints['File view'] = (x, y)
    s8.at(t, 'file view', 1., [('MOVE_CAMERA_TO', 'File view', 0.5, 0.0, 1.0, 1.0)])
    run = t.bench[0][1]
    t.bench = [('bench_watch', dict(run, seconds=2.0)), ('bench_view', dict(x=x, y=y, look=True)),
               ('bench_box', dict(x0=x - 170, y0=y - 52, x1=x - 90, y1=y + 28, look=True)),
               ('bench_click', dict(x=640, y=346, world=False, right=True, look=True)),
               ('bench_watch', dict(run, seconds=run['seconds'] - 2.0))]
    t.expect = [('存活', 0, 'ever==', 6), ('盖', 0, 'ever==', 1), ('兵血', 0, '==', 50)]
    return t


def pickup_mission(veterancy=False):
    m = Mission(name='CampVetCrate' if veterancy else 'CampMoneyCrate', map=probe_range, units=[])
    m.ext = True
    for lane in ('switch', 'low'):
        m.put('VeterancyCrate' if veterancy else 'MoneyCrate', lane + ' gun',
              side='neutral', role=lane + ' cash', name=lane + ' cash')
        m.put(MAN, lane + ' gun', -130, side='p1', role=lane + ' man', name=lane + ' man')
    if veterancy:
        m.put(MAN, 'switch gun', 0, 40, side='p1', role='near', name='near')
    return m


def money_pickup(m):
    """Retail MoneyProvided=1000. Predict the clicked crate pays p1 once and disappears.
    A script move across the identical control crate leaves it standing and pays nothing."""
    t = pickup(m)
    for side, label, counter in (('p1', '玩家资金', 'CashOwn'), ('s2', '对手资金', 'CashOther')):
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter}', [],
                                [('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), counter)], once=False))
    t.expect += [('玩家资金', 0, 'ever==', 1000), ('对手资金', 0, '==', 0)]
    pickup_view(m, t)
    return t


def pickup(m):
    t = Test()
    p1, s2 = m.player('p1'), m.player('s2')
    x, y = m.site('switch gun')
    low_x, low_y = m.site('low gun')
    walker = m.role('low man').name
    t.waypoints.update({'Cash view': (x, y), 'Cash goal': (low_x + 130, low_y)})
    t.areas['Cash crossing'] = square(low_x, low_y, 12)
    t.scripts.extend([
        Script('Test - Cash start', [], [('PLAYER_SET_MONEY', p1, 0), ('PLAYER_SET_MONEY', s2, 0),
                                        ('MAP_REVEAL_ALL_PERM', p1)]),
        Script('Test - Cash crossing', [('NAMED_INSIDE_AREA', walker, 'Cash crossing')],
               [('SET_COUNTER', 'CashCross', 1)]),
    ])
    s8.at(t, 'cash view', 1., [('MOVE_CAMERA_TO', 'Cash view', 0.5, 0.0, 1.0, 1.0)])
    s8.at(t, 'cash move', 2., [('MOVE_NAMED_UNIT_TO', walker, 'Cash goal')])
    s8.total(t, 'CashLive', '箱位', [(2**k, ('NAMED_NOT_DESTROYED', m.role(lane + ' cash').name))
                                   for k, lane in enumerate(('switch', 'low'))])
    t.counters.append(('CashCross', '过点'))
    t.expect = [('箱位', 0, 'ever==', 3), ('箱位', 0, 'ever==', 2), ('过点', 0, 'ever==', 1)]
    return t


def pickup_view(m, t):
    x, y = m.site('switch gun')
    s8.watch(t, 16., .5)
    watch = t.bench[0][1]
    t.bench = [('bench_watch', dict(watch, seconds=2.0)), ('bench_view', dict(x=x, y=y, look=True)),
               ('bench_box', dict(x0=x - 170, y0=y - 40, x1=x - 90, y1=y + 40, look=True)),
               ('bench_click', dict(x=640, y=346, world=False, right=True, look=True)),
               ('bench_watch', dict(watch, seconds=14.0))]


def veterancy_pickup(m):
    """Predict one rank on pickup for the veteran collector and the ally within RangeOfEffect=50.
    A veteran with 150 HP reads 80% after 30 script damage; an elite with 187.5 HP reads 84%.
    The scripted walker crosses its crate and remains a veteran."""
    t = pickup(m)
    start, damage = [], []
    for role in ('switch man', 'near', 'low man'):
        unit = m.role(role).name
        start += [('UNIT_GIVE_EXPERIENCE_POINTS', unit, 600), ('SET_COUNTER', role, -1)]
        damage += [('NAMED_DAMAGE', unit, 30), ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', unit, role)]
    t.counters.append(('switch man', '拾取血量'))
    t.scripts += [Script('Test - start veteran', [], start),
                  Script('Test - measure rank', [('NAMED_DESTROYED', m.role('switch cash').name)], damage)]
    # Four HUD lines fit. Encode the near ally and walker separately in one line.
    s8.total(t, 'Other ranks', '旁证', [(1, ('COUNTER', 'near', 2, 84)), (2, ('COUNTER', 'low man', 2, 80)),
                                    (4, ('COUNTER', 'near', 2, 80)), (8, ('COUNTER', 'low man', 2, 84))])
    t.expect += [('拾取血量', 0, 'ever==', 84), ('旁证', 0, 'ever==', 3)]
    pickup_view(m, t)
    return t


MISSION = {'engine_healcrate': mission, 'engine_healcrate_r': lambda: mission(True), 'engine_healcrate_h': hypotheses,
           'engine_healcrate_v': lambda: hypotheses(True), 'engine_secretfile_e': secret_files_mission,
           'engine_moneycrate_e': pickup_mission, 'engine_vetcrate_e': lambda: pickup_mission(True)}
CHECKS = {'engine_healcrate': {'a': check, 'b': passed, 'c': ordered}, 'engine_healcrate_r': {'a': check, 'b': collect, 'c': recalled},
          'engine_healcrate_h': {'a': hyp_check}, 'engine_healcrate_v': {'a': hyp_check},
          'engine_secretfile_e': {'a': secret_files, 'b': collect_file}, 'engine_moneycrate_e': {'a': money_pickup},
          'engine_vetcrate_e': {'a': veterancy_pickup}}
CONTROL_ARMS = {'engine_healcrate': ('On', 'Off')}
