"""AI targets checks."""
from functools import cache
from types import SimpleNamespace


def engine_aibridge():
    """Count actual generated native bridge parts; native tgt rows judge selection.

    Prediction at 700 units: End/End2/Center/Center2/GateHouse = 1/1/2/2/2.
    Ordinary neutral plants control: all five zero. Counts encode n as n+1;
    an unavailable condition cannot pass as zero. Endpoint identities are observed
    separately without assuming that the builder's named objects survive generation.
    Evidence and unresolved semantics: work/re/c_bridge_report.md.
    BENCH: on/off PASS, encoded parts 322/33 and 111/11; endpoint alive 1/0
    and 1/1. Both Bridge slots at f16 found=false with zero published candidates.
    True bridge NamedObject finds only the start; this is not a Bridge positive.
    """
    from parts import Script, Test


    def a(m):
        t = Test()
        t.scripts.append(Script('Bridge reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.counters += [('BrEnds', 'ends'), ('BrCenters', 'centers')]
        t.scripts.append(Script('Bridge reset', [], [('SET_COUNTER', c, 0)
                                                    for c in ('BrEnds', 'BrCenters')], once=False))
        for suffix, counter, weight in zip(('End', 'End2', 'Center', 'Center2', 'GateHouse'),
                                           ('BrEnds', 'BrEnds', 'BrCenters', 'BrCenters', 'BrEnds'),
                                           (1, 10, 1, 10, 100)):
            for n in range(8):
                t.scripts.append(Script('Bridge ' + suffix + str(n), [
                    ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('neutral'),
                     2, n, 'HB_Bridge_02_' + suffix, 'Bridge count')],
                    [('INCREMENT_COUNTER', (n+1)*weight, counter)], once=False))
        t.expect += [('ends', 2, '==', 322 if m.facts['native bridge'] else 111, 15),
                     ('centers', 2, '==', 33 if m.facts['native bridge'] else 11, 15)]
        for i in range(2):
            counter = f'BrNamed{i}'
            t.counters.append((counter, f'endpoint {i} alive'))
            t.scripts += [Script(counter + ' reset', [], [('SET_COUNTER', counter, 0)], once=False),
                          Script(counter + ' read', [('NAMED_NOT_DESTROYED', m.role(f'bridge {i}').name)],
                                 [('SET_COUNTER', counter, 1)], once=False)]
        t.bench = [('bench_watch', dict(seconds=15, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {build: {'a': a} for build in ('aibridgeon', 'aibridgeoff')}
    return dict(CHECKS=CHECKS)


def engine_aibuildexclude():
    """C ExcludeThing contrast; original readings and orders: work/re/c_buildexclude_report.md.

    Original prediction (superseded by D103): excluding an explicitly included
    request would remove its structure-basket priority. Direct factory observations
    show IncludeThing wins instead. Category-only probes below isolate exclusion.

    Measured 2026-11-13: both variants first own CNVNewPK at frame 501 and
    CNVDearPK at frame 570. Neither template occurs in an order line, so the
    positive production controls do not establish basket choice. D103's build picks
    and direct orders resolve the filter and basket boundary; whole-game production
    timing is still a separate gap (work/re/c_buildexclude_follow_report.md).
    """
    from benches.ai.production.checks import engine_aiskirm
    yc = engine_aiskirm()["shared"].yc


    def r(m):
        t = yc(m)
        t.bench = [('bench_watch', dict(seconds=175, every=1, sheet=False, lines=len(t.counters)))]
        t.expect = [('新维和', 30, 'ever>=', 1, 45), ('贵维和', 30, 'ever>=', 1, 45)]
        return t


    def x(m):
        """Category includes both infantry; only aibxo excludes Dear (no IncludeThing).

        Prediction: New passes in both; Dear passes only in aibxi. New's score
        wins the structure basket in both. Read build_picks/build_orders, since
        production counters alone cannot identify this filter.
        """
        t = r(m)
        t.bench = [('bench_watch', dict(seconds=55, every=1, sheet=False, lines=len(t.counters)))]
        t.expect = [('新维和', 30, 'ever>=', 1, 55), ('贵维和', 30, 'ever>=', 1, 55)]
        return t


    CHECKS = {'aibex': {'r': r}, 'aibin': {'r': r}, 'aibxo': {'x': x}, 'aibxi': {'x': x},
              'aibxall': {'x': x}, 'aibxany': {'x': x}}
    return dict(CHECKS=CHECKS)


def engine_aiclosestenemy():
    """Four land ClosestToEnemy hosts; predicted four members at each selected structure.

    Measured s16-80: 4/4/0/0 versus predicted 4/4/4/4.
    Raw readings and unresolved candidate qualifications: work/re/c_closest_report.md.
    """
    from parts import Script, Test, counted, square


    def a(m):
        t = Test()
        for i, unit in enumerate(m.cnv_units):
            target = m.find(m.role(f'closest goal {i}').name)
            area = f'Closest area {i}'
            t.areas[area] = square(target.x, target.y, 250)
            label = ('普通数量', '非矿数量', '非塔数量', '原关数量')[i]
            counted(f'Closest_count{i}', label, t, template=unit, area=area, player=m.player('s1'))
            t.expect.append((label, 55, '==', 4, 60))
        for i, role in enumerate(('closest plant', 'closest turret', 'closest enemy')):
            t.scripts.append(Script(f'Closest keep {i}', [],
                [('UNIT_SET_HEALTH', m.role(role).name, 100.0)], once=False))
        for i, role in enumerate(r for r in m.cast if r.startswith(('peacekeeper ', 'guardian ', 'closest extra '))):
            t.scripts.append(Script(f'Closest member keep {i}', [],
                [('UNIT_SET_HEALTH', m.role(role).name, 100.0)], once=False))
        t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {'aiclosest': {'a': a}}
    return dict(CHECKS=CHECKS)


def engine_aiconyard():
    """C conyard minimum-distance diagnostic, not distance acceptance.

    Observe core / total plant / local plant / host before and after 15s. Read
    teamlog.target_picks and team membership from the same run; no movement proxy
    can establish the real conyard exit or a placement candidate's eligibility.
    Evidence and gate: work/re/c_conyard_report.md.
    """
    from parts import Test, counted, square


    def a(m):
        t = Test()
        core = m.find(m.role('core').name)
        t.areas['CNV Yard Local'] = square(core.x, core.y, 250)
        for key, label, template, area in (
            ('Core', '核心', 'JapanPowerPlantEgg', None),
            ('Plant', '电厂', 'JapanPowerPlant', None),
            ('Local', '近处电厂', 'JapanPowerPlant', 'CNV Yard Local'),
            ('Host', '宿主', 'CNVTeamsHost', None),
        ):
            counted('CNV_Yard_' + key, label, t, template=template, player=m.player('s1'), area=area)
        # Readings only: no distance verdict before eligibility and exit facts.
        t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {key: {'a': a} for key in ('aicyard0', 'aicyard300')}
    return dict(CHECKS=CHECKS)


def engine_aicrate():
    """Crate/native named-slot selection; evidence work/re/c_crate_report.md.

    Counter verifies the placed control survives through the selection window.
    Only target_picks establishes the native heuristic's selection verdict.
    """
    from parts import Test, Script


    def a(m):
        t = Test()
        names = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
        names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
        t.scripts.append(Script('Crate keep', [],
            [('UNIT_SET_HEALTH', n, 100.0) for n in names], once=False))
        t.scripts.append(Script('Crate reveal', [],
            [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.counters.append(('CrateControl', 'control alive'))
        control = m.role('crate control').name
        t.scripts.append(Script('Crate alive reset', [], [('SET_COUNTER', 'CrateControl', 0)], once=False))
        t.scripts.append(Script('Crate alive', [('NAMED_NOT_DESTROYED', control)],
            [('SET_COUNTER', 'CrateControl', 1)], once=False))
        t.expect = [('control alive', 2, '==', 1, 3)]
        t.bench = [('bench_watch', dict(seconds=15, every=1, sheet=False, lines=1))]
        return t


    CHECKS = {build: {'a': a} for build in ('aicrateon', 'aicrateoff')}
    return dict(CHECKS=CHECKS)


def engine_aienemyfilter():
    """EnemyFilter.Include: predict enemy HARVESTER leaves, ENGINEER stays.

    Relation control SAME_PLAYER has no own harvester and should stay.
    Counters are the measured host's home/target-area tanks; no target-sort claim.
    """
    from benches.ai.production.checks import engine_aipoweradv
    a = engine_aipoweradv()["shared"].a

    CHECKS = {build: {'a': a} for build in ('aiefharv', 'aiefeng', 'aiefself', 'aiefall', 'aiefnone')}
    return dict(CHECKS=CHECKS)


def engine_aienemygarr():
    """EnemyGarrison occupancy/ownership guard; native tgt records judge selection.

    Prediction: occupied enemy row house selected; same-site ordinary enemy plant
    not eligible. Both NamedObject slots identify the surviving placed control.
    Evidence: work/re/c_enemygarr_report.md.
    """
    from model import status
    from parts import Test, Script


    def a(m):
        t = Test()
        control, occupant = (m.role(r).name for r in ('garr control', 'garr occupant'))
        names = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
        names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
        names += [control, occupant]
        t.scripts.append(Script('EGarr keep', [],
            [('UNIT_SET_HEALTH', n, 100.0) for n in names], once=False))
        t.scripts.append(Script('EGarr reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        rows = [('control alive', ('NAMED_NOT_DESTROYED', control)),
                ('enemy owner', ('NAMED_OWNED_BY_PLAYER', m.player('p1'), control)),
                ('occupant inside', ('UNIT_HAS_OBJECT_STATUS', occupant, status('ENCLOSED')))]
        for i, (label, cond) in enumerate(rows):
            c = f'EGarr{i}'
            t.counters.append((c, label))
            t.scripts.append(Script(c + ' reset', [], [('SET_COUNTER', c, 0)], once=False))
            t.scripts.append(Script(c + ' read', [cond], [('SET_COUNTER', c, 1)], once=False))
            t.expect.append((label, 1, '==', int(i != 2 or m.facts['enemy garrison']), 15))
        t.bench = [('bench_watch', dict(seconds=15, every=1, sheet=False, lines=3))]
        return t


    CHECKS = {build: {'a': a} for build in ('aiegarron', 'aiegarroff')}
    return dict(CHECKS=CHECKS)


def engine_aiforbid():
    """Native status and target-area counters; work/re/c_forbid_report.md.

    Read the named plant's original status every frame alongside area counts.
    The mission's observer records candidate eligibility and selection by state/index.
    Raw status bits and the runtime filter mask remain unobserved gaps.
    """
    from model import Test, Script, counted, square, status


    def a(m):
        t = Test()
        plant = m.role('plant').name
        t.counters.append(('CNV_Forbid_Status', '状态'))
        condition = ('UNIT_HAS_OBJECT_STATUS', plant, status('UNDER_IRON_CURTAIN'))
        t.scripts.append(Script('Test - forbid reset', [],
                               [('SET_COUNTER', 'CNV_Forbid_Status', 0)], once=False))
        t.scripts.append(Script('Test - forbid on', [condition],
                               [('SET_COUNTER', 'CNV_Forbid_Status', 1)], once=False))
        if m.facts.get('read unattackable'):
            t.scripts.append(Script('Test - unattackable on',
                [('UNIT_HAS_OBJECT_STATUS', plant, status('UNATTACKABLE'))],
                [('INCREMENT_COUNTER', 2, 'CNV_Forbid_Status')], once=False))
        keep = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
        keep += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
        t.scripts.append(Script('Test - forbid keep', [],
            [('UNIT_SET_HEALTH', n, 100.0) for n in keep], once=False))
        t.scripts.append(Script('Test - forbid reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        for role, label in [('plant', '近处'), ('barracks', '远处')]:
            o = m.find(m.role(role).name)
            area = 'CNV Forbid ' + role
            t.areas[area] = square(o.x, o.y, 340)
            counted('CNV_Forbid_' + role, label, t, template=m.cnv_units[0], area=area, player=m.player('s1'))
            t.expect.append((label, 40, '==', m.facts['expect ' + role], 41))
        x, y = m.site('east base')
        t.areas['CNV Forbid Home'] = [(x-300,y-400),(x+300,y-400),(x+300,y+450),(x-300,y+450)]
        counted('CNV_Forbid_Home', '在家', t, template=m.cnv_units[0], area='CNV Forbid Home', player=m.player('s1'))
        t.expect += [('在家', 40, '==', 0, 41), ('状态', 5, '==', m.facts['status set'], 41)]
        t.bench = [('bench_watch', dict(seconds=54, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a} for k in ('aiforbidnone', 'aiforbidset', 'aiforbidclear',
                                  'aifmasknone', 'aifmaskiron', 'aifmaskboth',
                                  'aifunanone', 'aifunasingle', 'aifunaboth',
                                  'aifdualnone', 'aifdualboth')}
    return dict(CHECKS=CHECKS)


def engine_aifrdistance():
    """Three-MCV FriendlyUnit probe; counters preserve independent survival.

    Tactical target identity must be read from the same-frame team log and
    matched to the idle MCV IDs/coordinates, not inferred from arrival counts.
    Pre-run prediction: nearest MCV; see work/re/c_friendly_distance_report.md.
    """
    original = engine_aifriendly()["shared"].a
    from parts import Script


    def a(m):
        t = original(m)
        t.expect = [('友车存活', 30, '==', 3, 31), ('敌车存活', 30, '==', 1, 31)]
        t.scripts.append(Script('Keep extra MCVs', [], [
            ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('second', 'third')], once=False))
        t.bench = [('bench_watch', dict(seconds=34, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('aifrnear', 'aifrswap')}
    return dict(CHECKS=CHECKS)


@cache
def engine_aifriendly():
    """E85 FriendlyUnit: count arrivals and surviving MCV targets through Mission.

    Prediction s40: aifriend friendly/enemy=4/0, aienemy=0/4; MCVs=2.
    StaticDefense and SAME_PLAYER follow SDK consumers; only HeuristicType changes.
    No internal target score is an engine observation. See work/re/e_friendly_e85.md.
    E85 engine: both builds FAIL their original prediction; s40 arrivals=0/0,
    MCVs alive=1/1 (friendly s1-s55, enemy s1-s71). Predictions remain unchanged.
    The pair cannot distinguish target selection from StaticDefense recruitment.
    """
    from parts import Script, Test, counted, square


    def a(m):
        t = Test()
        t.scripts.append(Script('Friendly reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Friendly keep', [], [
            ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('friendly', 'enemy')], once=False))
        for role, label in (('friendly', '到友车'), ('enemy', '到敌车')):
            o = m.find(m.role(role).name)
            area = 'Friendly ' + role
            t.areas[area] = square(o.x, o.y, 340.0)
            counted('Friendly_' + role, label, t, template=m.cnv_units[0], area=area, player=m.player('s1'))
            t.expect.append((label, 40, '==', m.facts['expect ' + role], 41))
        for role, label, player in (('friendly', '友车存活', 's1'), ('enemy', '敌车存活', 'p1')):
            counted('Friendly_alive_' + role, label, t, template='AlliedMCV', player=m.player(player))
            t.expect.append((label, 40, '==', 1, 41))
        t.bench = [('bench_watch', dict(seconds=54, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('aifriend', 'aienemy')}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a))


def engine_aihusk():
    """Selection-only Husk probe; expectations recorded in work/re/c_husk_report.md.

    Only survival/placed-derrick controls use counters. Native selection is read
    from target_picks, never inferred from whether a team moves or attacks.
    """
    from model import Test, Script, counted


    def a(m):
        t = Test()
        names = [m.role(r).name for r in ('plant', 'barracks', 'tank', 'husk oil control')]
        names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
        t.scripts.append(Script('Husk keep', [],
            [('UNIT_SET_HEALTH', n, 100.0) for n in names], once=False))
        t.scripts.append(Script('Husk reveal', [],
            [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('Husk_all', '总数', t, template=m.cnv_units[0], player=m.player('s1'))
        t.expect.append(('总数', 20, '==', 4, 21))
        t.bench = [('bench_watch', dict(seconds=25, every=1, sheet=False, lines=1))]
        return t


    CHECKS = {build: {'a': a} for build in ('aihusknone', 'aihusknamed')}
    return dict(CHECKS=CHECKS)


def engine_ailocation():
    """AITargetingHeuristic.Location: count arrivals at the published land/water targets.

    Targets stay at full health. At s40 the selected plant must have all four
    Twinblades nearby and the other none. Engine E81, one run each, all PASS:
    Land and Water Land: land=4/water=0 from s13-s51; Water: 0/4 from s16-s51.
    E87 replays all three with terrain-backed Location filtering. Shorelines, bridges
    and airborne targets remain INFERRED. Evidence: work/re/e_location_e87.md.
    """
    from parts import Script, Test, counted, square


    def a(m):
        t = Test()
        t.scripts.append(Script('Location reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Location keep', [], [
            ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('land', 'water')], once=False))
        for role, label in (('land', '到陆厂'), ('water', '到水厂')):
            o = m.find(m.role(role).name)
            area = 'Location ' + role
            t.areas[area] = square(o.x, o.y, 340.0)
            counted('Location_' + role, label, t, template=m.cnv_units[0], area=area, player=m.player('s1'))
            t.expect.append((label, 40, '==', 4 * m.facts['expect ' + role], 41))
        t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=2))]
        return t


    CHECKS = {name: {'a': a} for name in ('ailocland', 'ailocwater', 'ailocboth')}
    return dict(CHECKS=CHECKS)


def engine_aimindist():
    """Tech minimum-distance contrast: oil/barracks/tank/home at s40.

    The oil uses the host's plant counter. Predicted zero/control: 4/0/0/0;
    2000: 0/0/0/4. Counters establish movement, not live candidate distance.
    Original evidence: work/re/c_mindist_report.md.
    Two-oil contrast: minimum 0 selects near oil (4/0/0/4), 350 stays home
    (0/0/4/4), contradicting the model's far-oil prediction. Qualification and
    fallback remain gaps; see work/re/c_mindist_pair_report.md.
    TechBuilding type contrast: aitechkind oil / aitechnon ordinary neutral plant.
    Native f16 includes/selects the oil but never includes the ordinary plant;
    the negative stays home (B 11-27, under its own heuristic id: work/re/b1127_techdup.md).
    """
    a = engine_aitargetpick()["shared"].a
    from parts import Script, Test, counted, square


    def pair(m):
        """Read both neutral oil destinations and survival, at s40.

        Prediction: minimum 0 -> near/far/home/total 4/0/0/4;
        minimum 350 -> 0/4/0/4. See work/re/c_mindist_pair_report.md.
        Observed: 0 -> 4/0/0/4; 350 -> 0/0/4/4 (original prediction FAIL).
        No claim about exact boundary, far qualification or fallback order.
        """
        t = Test()
        t.scripts.append(Script('Minimum pair reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Minimum pair keep', [],
            [('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('plant', 'barracks', 'tank')], once=False))
        tank, = m.cnv_units
        for role, label, key in (('plant', '近油井', 'near'), ('barracks', '远油井', 'far')):
            obj = m.find(m.role(role).name)
            area = 'Minimum pair ' + key
            t.areas[area] = square(obj.x, obj.y, 340)
            counted('CMP_' + key, label, t, template=tank, player=m.player('s1'), area=area)
            t.expect.append((label, 40, '==', m.facts['expect ' + key + ' oil'], 41))
        x, y = m.site('east base')
        t.areas['Minimum pair home'] = [(x-300, y-400), (x+300, y-400), (x+300, y+450), (x-300, y+450)]
        counted('CMP_home', '在家', t, template=tank, player=m.player('s1'), area='Minimum pair home')
        counted('CMP_total', '总数', t, template=tank, player=m.player('s1'))
        t.expect += [('在家', 40, '==', 0, 41), ('总数', 40, '==', 4, 41)]
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
        return t

    CHECKS = {build: {'a': a} for build in ('aimind0', 'aimindhi', 'aimindctl')}
    CHECKS.update({build: {'a': pair} for build in ('aimindpair0', 'aimindpair350', 'aimindpairclr', 'aimindpairfar', 'aimindpairwal')})
    CHECKS.update({build: {'a': a} for build in ('aitechkind', 'aitechnon')})
    return dict(CHECKS=CHECKS)


def engine_aiminvalue():
    """MinEnemyValue retail 1000/2500, single/summed enemy cost and inversion.

    Corrected data predictions s40-60: low 0/4/4/0, high 0/4/0/4. Source and raw results:
    Measured s40-60: low 0/4/4/1 (last lane differs), high 0/4/0/4 (PASS).
    work/re/c_minvalue_report.md. Equality at 2500 and damaged-unit valuation remain gaps.
    """
    from parts import Script, Test, counted, square


    def a(m):
        t = Test()
        t.areas['MinValue home'] = square(*m.site('east base'), 450)
        roles = ('player target',) + tuple(f'value miner {i}' for i in range(m.facts['min value miners']))
        for i, role in enumerate(roles):
            t.scripts.append(Script(f'MinValue keep {i}', [],
                [('UNIT_SET_HEALTH', m.role(role).name, 100.0)], once=False))
        for i, (unit, label, expected) in enumerate(zip(m.cnv_units,
                ('一千单矿', '二五单矿', '二五合计', '合计反向'), m.facts['min value home'])):
            counted(f'MinValue_home{i}', label, t, template=unit,
                    player=m.player('s1'), area='MinValue home')
            t.expect.append((label, 40, '==', expected, 60))
        t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('aiminvalue', 'aiminvaluehi', 'aiminvaluet')}
    return dict(CHECKS=CHECKS)


def engine_ainamed():
    """Engine probe: an AI attack team sent to a target named in the data (benches/ai/targets/scenes.py#ainamed_bench).

      a  步兵在家 / 到近厂 / 到远厂 / 到路点   Peacekeepers of s1 within 450 of the AI's base, within 300 of the near
                                              power plant, of the far one, of the waypoint -- once a second for 60 s
                                              after the wake

    The first of 到近厂 / 到远厂 / 到路点 to go above 0 is the reading (afterwards RAMPAGE may take the team on).
    Expectation per build (the model, RA3-EngineModel ra3model/ai/targets.py): ainmfar -> far; ainmwp -> the waypoint;
    ainmrel / ainmnone -> nobody leaves. A FAIL is a reading too.

    读数
    Bench 2026-11-08 (one run each; all PASS):
      ainmfar   到远厂 2 @ s15, 4 s17-s33, 0 from s35 (the plant down); 到近厂 0 till s42, 3 @ s43, 4 s44-s51 (RAMPAGE);
                步兵在家 4 -> 2 @ s10, 0 from s12. NamedObject goes to the named plant, not the nearest.
      ainmwp    到路点 2 @ s6, 3 @ s7, 4 from s8 to s75; 到近厂 / 到远厂 0 all along: at the point the team stays.
      ainmrel   步兵在家 4 all 75 s: Relationship NEUTRAL drops the player's (enemy) plant -- no target, no team.
      ainmnone  步兵在家 4 all 75 s: a name nobody has, no target.
    """
    from parts import Script, Test, counted, square
    at = engine_aitarget()["shared"]

    AFTER = 60.0
    WPA = 'CNV AI WP Target Area'


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[at.HOME] = square(*m.site('east base'), 450.0)
        for area, role in ((at.NEAR, 'near plant'), (at.FAR, 'far plant')):
            o = m.find(m.role(role).name)
            t.areas[area] = square(o.x, o.y, 300.0)
        t.areas[WPA] = square(*m.point('wp target'), 300.0)
        (inf,) = m.cnv_units
        counted('CNV_AT_Home', '步兵在家', t, template=inf, area=at.HOME, player=s1)
        counted('CNV_AT_Near', '到近厂', t, template=inf, area=at.NEAR, player=s1)
        counted('CNV_AT_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
        counted('CNV_AT_WP', '到路点', t, template=inf, area=WPA, player=s1)
        end = m.facts['wake at'] + AFTER
        pick, (kind, name, extra) = None, m.cnv_heuristic
        if kind == 'Waypoint':
            pick = '到路点'
        elif 'Far Plant' in name and not extra:
            pick = '到远厂'
        if pick:
            t.expect += [('步兵在家', end, '<', 4, end + 1), (pick, 1, 'ever>=', 1, end)]
        else:
            t.expect += [('步兵在家', 1, '==', 4, end)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a} for k in ('ainmfar', 'ainmwp', 'ainmrel', 'ainmnone')}
    return dict(CHECKS=CHECKS)


def engine_aipoint():
    """Point selection is read through teamlog.target_picks, not inferred from arrival.

    Only the survival control is asserted by on-screen counters. Selection and
    search-range predictions are recorded before running in work/re/c_point_report.md.
    """
    from model import Test, Script, counted


    def a(m):
        t = Test()
        names = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
        names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
        t.scripts.append(Script('Test - point keep', [],
            [('UNIT_SET_HEALTH', name, 100.0) for name in names], once=False))
        t.scripts.append(Script('Test - point reveal', [],
            [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_Point_All', '总数', t, template=m.cnv_units[0], player=m.player('s1'))
        x, y = m.site('east base')
        t.areas['CNV Point Home'] = [(x-300, y-400), (x+300, y-400),
                                    (x+300, y+450), (x-300, y+450)]
        counted('CNV_Point_Home', '在家', t, template=m.cnv_units[0],
                player=m.player('s1'), area='CNV Point Home')
        t.expect.append(('总数', 25, '==', 4, 26))
        t.bench = [('bench_watch', dict(seconds=32, every=1, sheet=False, lines=2))]
        return t


    CHECKS = {build: {'a': a} for build in ('aipointwater', 'aipointtiny')}
    return dict(CHECKS=CHECKS)


def engine_aiprio():
    """Engine probe: SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY (benches/ai/targets/scenes.py#aiprio_bench; program: work/re l4_aiswitches.md;
    model: RA3-EngineModel ra3model/ai/player.py set_enemy_priority, simai.Brain.switches).

      a  步兵在家 / 到近厂 / 到远厂   Peacekeepers of s1 within 450 of the AI's base / 300 of the near (Soviet_4's) / far
         (the player's) power plant, once a second, 60 s after the wake

    Expectations are the program's (read, work/re l4_aiswitches.md 2b: the re-sort off, the player's entry taken out,
    put back at score n when n > 0 without asking the enemy list; tiers by score, the top one searched first):
      aipriodef  到远厂 (the program says both enemies one tier -> 到近厂; the bench said otherwise, see 读数)
      aiprio1    到近厂 (Soviet_4 30 above Player_1 10)
      aiprio0    到近厂 (Player_1 0: out of the table, Soviet_4 alone in it)
      aipriorm   nobody leaves (the table empty at the wake: only what the script names is in it)

    读数
    Bench 2026-11-10 (one run each):
      aipriodef  CampAIPrioDefA_mcp_1110_234833: 步兵在家 4 to s19, 0 from s21; 到远厂 2 @ s25, 4 s26-s44, 0 from s47 (the
                 plant down); 到近厂 2 @ s55, 3 s56-s75 (RAMPAGE). Soviet_4 is an enemy to the objects (RAMPAGE goes for
                 its plant), and in SET_ALL's table (aiprio0); with two enemies in one tier the farther structure won.
                 Why is NOT READ (the in-tier count rule with ties by id says near): tests/test_simai.py strict xfail.
      aiprio1    CampAIPrio1A_mcp_1110_235356 PASS: 到近厂 2 @ s14, 4 s15-s21, then fewer (the turrets), never 到远厂.
      aiprio0    CampAIPrio0A_mcp_1110_235746: 到近厂 2 @ s15, 4 s16-s22, never 到远厂 -- the first expectation (nobody
                 leaves) was wrong: Soviet_4 was in SET_ALL's table, Player_1 0 left it alone in the top tier.
      aipriorm   CampAIPrioRmA_mcp_1111_000210: 步兵在家 4 s1-s75, nobody anywhere -- the table was empty when the script
                 changed it: an entry not named is not there (Player_1 out too).
    """
    from checks.engine_aiprio import PICK, a


    CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in PICK}
    return dict(CHECKS=CHECKS)


def engine_aisearch():
    """EnemySearchDistanceVisionMultiplier A/B (benches/ai/targets/scenes.py#aisearch_bench), before the far target falls.

    Prediction, using the already measured aipas geometry: high 1.5 attacks the side plant
    before wake+25 and never reaches the far plant; low 0.25 leaves side HP 100 through that
    window and reaches the far plant. Both have EngagePassiveTargets=true. Four counters
    retain home/far/side counts and side HP, so departure and damage are separate evidence.
    Only a passive structure, these two multipliers and this geometry are covered.

    Bench 2026-11-11, both PASS (counters home/far/side/sideHP):
      aisrchhi: s1-10 4/0/0/100; s11 sideHP94, s25 5, s26-40 1; far0 throughout.
      aisrchlo: sideHP100 s1-39; far2 s15, far3 s16, far4 s17-37. At s40 sideHP85
                (after the comparison window, RAMPAGE can pick the side plant).
    The simulator replays the early damage versus no-damage/destination split in
    tests/test_simai_search.py; no claim about exact radius boundaries or fog visibility.
    """
    from benches.ai.tactics.checks import engine_airetreat
    ar = engine_airetreat()["shared"]


    def a(m, high):
        t = ar.a(m, 'aipas1' if high else 'aipas0')
        end = m.facts['wake at'] + 25.0
        if high:
            t.expect.append(('到远厂', 1, '==', 0, end))
        t.bench = [('bench_watch', dict(seconds=end + 4, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {
        'aisrchhi': {'a': lambda m: a(m, True)},
        'aisrchlo': {'a': lambda m: a(m, False)},
    }
    return dict(CHECKS=CHECKS)


def engine_aishore():
    """MaxDistanceToShore: 2000 leaves, 1 stays; ordinary structure control leaves.

    Only the primary pair's distance limit differs. Original expectations are
    retained if the host fails; see work/re/c_shore_report.md for interpretation.
    """
    from benches.ai.production.checks import engine_aipoweradv
    a = engine_aipoweradv()["shared"].a

    CHECKS = {build: {'a': a} for build in ('aishorehi', 'aishorelo', 'aishorectl')}
    return dict(CHECKS=CHECKS)


@cache
def engine_aistate():
    """Engine probe: strategic states switched by map flags (benches/ai/targets/scenes.py#aistate_bench) -- which of the AI's units leave
    its base, and how many frames after their state's flag went on.

      a  步兵在家 / 坦克在家   Peacekeepers / Guardians of s1 inside the base area (450 around the east base), once a second
         步兵等帧 / 坦克等帧   frames from the flag going on while all four are still home (stops at the first to leave)

    Expected if ScriptedFlagHeuristic follows SET_FLAG and a team takes only what its filter names: the infantry go
    after INF_AT and the tanks stay home till TANK_AT, then the tanks go. The waits are the reading (the model,
    RA3-EngineModel ra3model/ai/states.py, re-weighs states every 15 frames).
    Builds: aistate (target only the player's yard, ~2600 away), aistatenear (+ a player power plant ~750 away),
    aistateconst (near, and both states always on: does a team go at all), aistatefar (both states always on, only the
    yard ~2600 away: not run yet; A round 67 reads no distance limit, so the expected reading is aistateconst's -- both
    teams leave ~5 s after the wake; 坦克在家 == 4 at TANK_AT then fails, as on aistateconst).
    NB: aistate's "nobody left" below says nothing about distance: its flags had no '/', and aistatenear (750) with the
    same flags did not move either.

    读数
    Bench 2026-11-06 aistate a (CampAIStateA, one run): nobody left -- 步兵在家 / 坦克在家 4 / 4 from s1 to s127;
      步兵等帧 grows from s19 (the flag is on) to 600 at s58 and stays (the flag off), 坦克等帧 from s58 to 1065 at
      s127. So both flags were set (the FLAG condition saw them) and neither state sent a unit. FAIL 2 of 3.
    Bench 2026-11-06 aistateconst a (CampAIConstA): both states always on, the near power plant there -- 步兵在家
      4 -> 0 @ s14, 坦克在家 4 -> 3 @ s14, -> 1 @ s15, -> 0 @ s16 (the wake is s9 on this bench clock, so ~5 s after
      SKIRMISH_AI_MAKE_BASE), all four of each, both teams together. So a state's team does recruit pre-placed units,
      and the far-only target of aistate is one reason nothing went there.
    Bench 2026-11-06 aistatenear a (CampAINear): the near target, the flags as aistate -- nobody left (4 / 4 to
      s127), the flags seen by FLAG from s19 / s58. So ScriptedFlagHeuristic did not see SET_FLAG's flags here,
      against the program read (work/re l4_states.md 3: the same table).
    Bench 2026-11-06 aistateplain a (CampAIPlain): flag names of letters only -- the same, nobody left (4 / 4 to
      s127; 步兵等帧 s19 -> 600 at s58, 坦克等帧 s58 -> 1064). Not the name's spaces.
    Why (program, round 8): one flag table keyed (scope, name); a script list runs under its player's scope, so a bare
      name SET_FLAG writes is that player's, while ScriptedFlagHeuristic reads the empty scope. 'scope/name' sets the
      scope by hand: '/name' is the empty one.
    Bench 2026-11-06 aistateslash a (CampAISlash): the scripts write '/CNVAIInfantry', '/CNVAITanks', the AI's FlagName
      stays bare -- PASS 3 of 3. 步兵在家 4 -> 0 @ s23 (步兵等帧 stops at 74: ~5 s after the flag), 坦克在家 4 at s60,
      4 -> 0 @ s63 (坦克等帧 77). The flags switch the AI's states, as fast as an always-on state goes (~5 s).
    Bench 2026-11-06 aistateoff off (CampAIOffOff, EndBehavior RAMPAGE) and aistateoffhome off (CampAIHomeOff,
      RETURN_HOME_AND_DISBAND), the infantry flag on at 20 s, off at 28 s: PASS 1 of 1 each. 步兵在家 4 -> 0 @ s23-24,
      步兵到目标 0 -> 3/4 @ s28, 4 @ s29 and 4 to s62, in both. So turning the flag off on the way did not end the
      tactic: the team went on to the target and stayed, nobody came home (EndIfStateTurnsOff="true" on both).
    Bench 2026-11-06 aistateoff1 off (CampAIOff1Off, off 1 s after on) and aistateoffh off (CampAIOffHOff, off 0.5 s
      after on), RAMPAGE: FAIL 1 of 1 each, against the guess "off while home = they stay": 步兵在家 4 -> 0 @ s24 / s23,
      步兵到目标 0 -> 4 @ s28 and 4 to the end, in both -- as aistateoff. So once a state has its slot (the first
      evaluation that saw the flag), the flag going off does not stop its team, even before it leaves home.
    Bench 2026-11-06 aihunt hunt (CampAIHuntHunt, Targetless Hunt, a team of one, no MaxRunningCopies) PASS: 步兵在家
      4 -> 0 @ s13; 在家4帧 / 3 / 2 stop at 59 / 60 / 60. aihunt2 hunt (CampAIHunt2Hunt, MaxRunningCopies 2) PASS:
      4 -> 2 @ s13 and 2 to s55; 在家4帧 / 3 stop at 59 / 60, 在家2帧 grows to the end. So a targetless state runs as
      many copies as it may (one team each), all within a few frames of the wake, and MaxRunningCopies caps them.
    aistatefar is the SearchRange test: the enemy structure / unit heuristics measure no distance, only the tech
    heuristic reads <AITargetingHeuristic SearchRange> (benches/ai/targets/scenes.py#aistate_bench); its readings follow.
    Bench 2026-11-07 aistatefar a (CampAIFarA, Sonnet, one run): both states always on, only the player's yard ~2600
      away -- 坦克在家 4 -> 3 @ s13, -> 0 @ s14 (as aistateconst), 步兵在家 4 all run (FAIL 2 of 3 as expected for the
      tanks, not for the infantry). So 2600 does not stop a team (A round 67's read holds for the tanks). Why the
      infantry stayed: INFERRED, not tested -- one structure only, and a target one state holds is not given to another
      (aistateconst had two: the yard and the power plant).
    Bench 2026-11-07 aistatefar2 a (CampAIFar2A, Sonnet, one run; B round 19): aistatefar plus the player's power plant
      on its own base (base power, ~2400 away) -- 步兵在家 and 坦克在家 4 -> 0 @ s14, both teams out (FAIL on 坦克在家 == 4
      at s60, the aistate expectation; the run ended at ~s84 so no s120 reading). So one target per state: the data's
      ClosestStructureHeuristic has RequireUniqueTarget="true" and skips a structure another state holds (RA3-EngineModel
      targets.pick claims; tests/test_ai_bench.py test_states_far2_const_both_go).
    """
    from parts import Script, Test, counted, square

    AREA = 'CNV AI Base Area'
    LAG = 4.0
    SECONDS = 120.0


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 450.0)
        inf, tank = m.cnv_units                 # the mission says (benches/ai/targets/scenes.py#aistate_bench), the check asks
        counted('CNV_AS_InfHome', '步兵在家', t, template=inf, area=AREA, player=s1)
        counted('CNV_AS_TankHome', '坦克在家', t, template=tank, area=AREA, player=s1)
        f_inf, f_tank = m.cnv_flags
        for c, lab, flag, unit in (('CNV_AS_InfWait', '步兵等帧', f_inf, inf),
                                   ('CNV_AS_TankWait', '坦克等帧', f_tank, tank)):
            t.counters.append((c, lab))
            t.scripts.append(Script(f'Test - wait {c}', [
                ('FLAG', flag, 1), ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 4, unit, AREA)],
                [('INCREMENT_COUNTER', 1, c)], once=False))
        w, i, k = (m.facts[x] for x in ('wake at', 'infantry at', 'tanks at'))
        t.expect += [('步兵在家', k, '<', 4, k + 1), ('坦克在家', k, '==', 4, k + 1), ('坦克在家', SECONDS, '<', 4, SECONDS + 1)]
        t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    THERE = 'CNV AI Target Area'
    OFF_SECONDS = 58.0                          # before the tank flag (60 s)


    def off(m):
        """aistateoff / aistateoffhome: the infantry flag on at 'infantry at', off at 'infantry off at' (on the way).
        步兵在家 / 步兵到目标 (Peacekeepers of s1 within 300 of the player's power plant) once a second; the rest are
        between. Ended where they were: neither count grows after the flag goes off; went on: 步兵到目标 -> 4; came
        home: 步兵在家 -> 4."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 450.0)
        goal = m.find(m.role('player target').name)             # the placed object (x, y)
        t.areas[THERE] = square(goal.x, goal.y, 300.0)
        inf, _ = m.cnv_units
        counted('CNV_AS_InfHome', '步兵在家', t, template=inf, area=AREA, player=s1)
        counted('CNV_AS_InfThere', '步兵到目标', t, template=inf, area=THERE, player=s1)
        o, i = m.facts['infantry off at'], m.facts['infantry at']
        if o - i >= LAG:
            t.expect += [('步兵在家', o, '<', 4, o + 1)]       # they had left when the flag went off
        else:
            # aistateoff1 / aistateoffh: off before they left -- the guess under test: the tactic ends, they stay home
            t.expect += [('步兵在家', OFF_SECONDS, '==', 4, OFF_SECONDS + 1)]
        t.bench = [('bench_watch', dict(seconds=OFF_SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    HUNT_SECONDS = 50.0


    def hunt(m):
        """aihunt / aihunt2: one always-on Targetless Hunt state, a team of one Peacekeeper.
        步兵在家 once a second; 在家4帧 / 在家3帧 / 在家2帧: frames from the wake while at least 4 / 3 / 2 Peacekeepers are
        still home -- the frames the 1st / 2nd / 3rd left at. Program read (work/re l4_states.md 8): no slot, every
        pass with weight > 0 starts another copy up to the copies cap. Guess under test: aihunt2 (cap 2) keeps 2 home."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 450.0)
        inf, _ = m.cnv_units
        counted('CNV_AS_InfHome', '步兵在家', t, template=inf, area=AREA, player=s1)
        t.scripts += [Script('Test - wake timer', [], [('SET_MILLISECOND_TIMER', 'CNV Test Wake', m.facts['wake at'])]),
                      Script('Test - awake', [('TIMER_EXPIRED', 'CNV Test Wake')], [('SET_FLAG', 'CNVTestAwake', 1)])]
        for n in (4, 3, 2):
            c = f'CNV_AS_Home{n}'
            t.counters.append((c, f'在家{n}帧'))
            t.scripts.append(Script(f'Test - home {n}', [
                ('FLAG', 'CNVTestAwake', 1), ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, n, inf, AREA)],
                [('INCREMENT_COUNTER', 1, c)], once=False))
        if m.facts['hunt copies'] == 2:
            t.expect += [('步兵在家', HUNT_SECONDS, '==', 2, HUNT_SECONDS + 1)]
        else:
            t.expect += [('步兵在家', HUNT_SECONDS, '<', 4, HUNT_SECONDS + 1)]
        t.bench = [('bench_watch', dict(seconds=HUNT_SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    BEACON_SECONDS = 40.0


    def beacon(m):
        """aibeaconex / aibeacontg (benches/ai/targets/scenes.py#aistate_bench; nobody places a co-op command beacon): the tanks' state
        sends its team, the infantry's never -- 坦克在家 0, 步兵在家 4 by BEACON_SECONDS (a's counters)."""
        t = a(m)
        t.expect = [('坦克在家', BEACON_SECONDS, '==', 0, BEACON_SECONDS + 1),
                    ('步兵在家', BEACON_SECONDS, '==', 4, BEACON_SECONDS + 1)]
        t.bench = [('bench_watch', dict(seconds=BEACON_SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'aibeaconex': {'bcn': beacon}, 'aibeacontg': {'bcn': beacon}, 'aistate': {'a': a}, 'aistatenear': {'a': a}, 'aistateconst': {'a': a}, 'aistatefar': {'a': a}, 'aistatefar2': {'a': a},'aistateplain': {'a': a},
              'aistateslash': {'a': a}, 'aistateoff': {'off': off}, 'aistateoffhome': {'off': off},
              'aistateoff1': {'off': off}, 'aistateoffh': {'off': off}, 'aihunt': {'hunt': hunt}, 'aihunt2': {'hunt': hunt}}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a))


@cache
def engine_aitarget():
    """Engine probe: which of the player's structures an AI attack team goes for first (benches/ai/targets/scenes.py#aitarget_bench).

      a  步兵在家 / 到近厂 / 到远厂   Peacekeepers of s1 within 450 of the AI's base, within 300 of the near (defended)
                                      power plant, within 300 of the far (undefended) one -- once a second for 60 s
                                      after the wake

    The first of 到近厂 / 到远厂 to go above 0 is the reading (afterwards RAMPAGE may take the team on to the other).
    The model (RA3-EngineModel ra3model/ai/targets.py): aitargetsafe (SafestToGroundStructureHeuristic, ThreatToGround)
    -> far; aitargetnear (ClosestStructureHeuristic, Distance) -> near. The expectation says the model's pick; a FAIL
    is a reading too.

    读数
    Bench 2026-11-06 aitargetsafe a (CampAISafeA, one run): PASS 2 of 2. 步兵在家 4 -> 2 @ s28, 0 @ s30; 到远厂 3 @ s35,
      4 s36-s60, 2 / 1 / 0 @ s61-63 (the plant down, RAMPAGE on); 到近厂 1 @ s69, 4 @ s72. The safest structure first,
      as the model; the team left ~15 s later than with SimpleAttack (not modelled: DefenseAvoidanceAttack's start).
    Bench 2026-11-06 aitargetnear a (CampAINearestA): PASS 2 of 2. 到近厂 2 @ s13 (步兵在家 still 4: the two squares
      touch), 4 @ s14-21, shot down 3 / 2 / 1 / 0 by s35 (the turrets); 到远厂 0 all 76 s. The nearest first, as the
      model.
    Bench 2026-11-06 aitargetidle5 a (CampAIIdle5A): PASS 2 of 2. DefenseAvoidanceAttack with MaxTeamIdleTime 5s (a
      flattened copy of StandardMicroManager_MEDIUM; the type cannot be inherited from). 步兵在家 4 -> 3 @ s17, 0 @ s21;
      到远厂 1 @ s22, 4 s26-s41, 3 @ s42, 0 from s43; 到近厂 1 @ s51 (RAMPAGE on). The far plant first, as aitargetsafe,
      ~11 s earlier (s28 -> s17 leaving, s35 -> s22 arriving).
    Bench 2026-11-06 aitargetidle30 a (CampAIIdle30A): PASS 2 of 2. Same with MaxTeamIdleTime 30s. 步兵在家 4 -> 3 @ s28,
      0 @ s30; 到远厂 3 @ s35, 4 s36-s60, 2 @ s61, 0 from s63; 到近厂 2 @ s70, 4 @ s73. Identical to aitargetsafe (15 s
      default): 15 s -> 30 s changes nothing, so the wait is not (only) the idle release.
    Bench 2026-11-06 aitargetflank a (CampAIFlankA): PASS 2 of 2. SafestToGroundStructureHeuristic + FlankAttack, default
      micro manager. 步兵在家 4 -> 3 @ s25, 0 @ s26; 到远厂 1 @ s58, 3 @ s59, 4 from s61; 到近厂 0 all 76 s. The far plant
      first, but ~23 s later than DefenseAvoidanceAttack (s35) -- a longer way round, or a later start.
    Bench 2026-11-07 b (frames from frame 0; 出发帧 = 1000 x last out of the start box + first out):
      aitargetidle5 (two runs)   出发帧 197170, 到达帧 355, 离家帧 280 (the first run had no 离家帧)
      aitargetsafe (two runs)    出发帧 192175, 到达帧 548, 离家帧 443 -- the two runs alike to the frame
      aitargetstill              出发帧 192175, 到达帧 548, 离家帧 443 -- MaxTeamIdleTime and MaxUnitIdleTime 600 s,
                                 to the frame as 15 s: neither idle time lets the team go
      Every team leaves the start box 20-25 frames after the wake (frame 150): the first leg goes at once (members with
      no order are idle, work/re/l4_micro_engage.md); the 5 s team then sends the rest at once (straight), the others walk leg by leg.
      The 193 frames at the plant are the DA route's extra walk (RA3-EngineModel tests/test_ai_tactics.py, strict xfail).
    """
    from parts import Script, Test, counted, square

    LAG = 4.0
    AFTER = 60.0
    HOME = 'CNV AI Base Area'
    NEAR = 'CNV AI Near Plant Area'
    FAR = 'CNV AI Far Plant Area'


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[HOME] = square(*m.site('east base'), 450.0)
        for area, role in ((NEAR, 'near plant'), (FAR, 'far plant')):
            o = m.find(m.role(role).name)
            t.areas[area] = square(o.x, o.y, 300.0)
        (inf,) = m.cnv_units
        counted('CNV_AT_Home', '步兵在家', t, template=inf, area=HOME, player=s1)
        counted('CNV_AT_Near', '到近厂', t, template=inf, area=NEAR, player=s1)
        counted('CNV_AT_Far', '到远厂', t, template=inf, area=FAR, player=s1)
        w = m.facts['wake at']
        end = w + AFTER
        pick = '到远厂' if m.cnv_heuristic.startswith('Safest') else '到近厂'
        t.expect += [('步兵在家', end, '<', 4, end + 1), (pick, 1, 'ever>=', 1, end)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    START = 'CNV AI Start Area'


    def b(m):
        """Departure / arrival to the frame (for the 5 s vs 15 s MaxTeamIdleTime gap; check a reads once a second).

          出发帧   1 x frames from frame 0 while all four Peacekeepers stand in a tight box round their start spots
                   + 1000 x frames while at least one does (first to leave / last to leave)
          到达帧   frames from frame 0 until the first Peacekeeper is inside the far plant's 300 square (stops then)
          在家     Peacekeepers in the box (a sanity readout)
          离家帧   frames from frame 0 until a Peacekeeper is first outside check a's 450 square round the base
        Both builds walk to the far plant first, so the box's exit lag and the way there cancel in the difference."""
        t = Test()
        s1 = m.player('s1')
        (inf,) = m.cnv_units
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        x, y = m.site('east base')
        t.areas[START] = [(x - 280.0, y - 110.0), (x - 240.0, y - 110.0), (x - 240.0, y + 110.0), (x - 280.0, y + 110.0)]
        o = m.find(m.role('far plant').name)
        t.areas[FAR] = square(o.x, o.y, 300.0)
        has = lambda cmp, n, area: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, cmp, n, inf, area)
        t.counters.append(('CNV_AT_Leave', '出发帧'))
        t.scripts += [Script('Test - all home', [has(2, 4, START)], [('INCREMENT_COUNTER', 1, 'CNV_AT_Leave')], once=False),
                      Script('Test - any home', [has(3, 1, START)], [('INCREMENT_COUNTER', 1000, 'CNV_AT_Leave')],
                             once=False)]
        t.counters.append(('CNV_AT_Arrive', '到达帧'))
        t.scripts += [Script('Test - arrived', [has(3, 1, FAR)], [('SET_FLAG', 'Test Arrived', 1)]),
                      Script('Test - on the way', [('FLAG', 'Test Arrived', 0)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AT_Arrive')], once=False)]
        counted('CNV_AT_Box', '在家', t, template=inf, area=START, player=s1)
        t.areas[HOME] = square(x, y, 450.0)
        t.counters.append(('CNV_AT_Out', '离家帧'))
        t.scripts += [Script('Test - out', [has(0, 4, HOME)], [('SET_FLAG', 'Test Out', 1)]),
                      Script('Test - not out', [('FLAG', 'Test Out', 0)], [('INCREMENT_COUNTER', 1, 'CNV_AT_Out')],
                             once=False)]
        end = m.facts['wake at'] + AFTER
        t.expect += [('在家', end, '<', 4, end + 2)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a, 'b': b} for k in ('aitargetsafe', 'aitargetnear', 'aitargetidle5', 'aitargetidle30',
                                             'aitargetstill', 'aitargetflank')}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(FAR=FAR, HOME=HOME, LAG=LAG, NEAR=NEAR))


@cache
def engine_aitargetpick():
    """Engine probe: which target a team picks (benches/ai/targets/scenes.py#aitargetpick_bench) -- AITargetingHeuristic VitalKindOf /
    ForbiddenKindOf / HeuristicType EnemyUnit, the TargetHeuristic Priority order, MaxTargets.

      a  到电厂  s1's Guardians within 340 of the player's power plant (FS_POWER), once a second
         到兵营  within 340 of the player's barracks (FS_BARRACKS)
         到坦克  within 340 of the player's Guardian's start spot (a VEHICLE unit)
         在家    in the AI's base (x +-300, y -400..+450 round its centre: every start spot)
    All three targets are set to full health every frame, so a team stays at its first pick.

    Expected (the mission's facts, the model's guess): the picked target's counter reaches 3 or more by s40 (one of four
    may be lost to the player's tank), the others are 0 at s40, 在家 == expect home at s40.

    读数
    Bench 2026-11-09 (B round 80, run_queue --jobs 2, one run each, all PASS; counters 到电厂 到兵营 到坦克 在家):
      aitpnear  ClosestStructureHeuristic: 到电厂 1 @ s13, 4 from s15 to s55; the rest 0.
      aitpvk    VitalKindOf FS_BARRACKS: 在家 0 from s19, 到兵营 1 @ s22, 4 from s23 to s55; 到电厂 0 throughout.
      aitpfk    VitalKindOf STRUCTURE, ForbiddenKindOf FS_POWER: the same to the second (到兵营 4 from s23).
      aitpunit  HeuristicType EnemyUnit, VitalKindOf VEHICLE: 到坦克 3 @ s14, 4 s15-29, then 3 / 2 (lost to the tank).
      aitpphi   CNVHBarracks Priority 20 + Closest 10: barracks, as aitpvk to the second -- the higher Priority first.
      aitpplo   CNVHBarracks Priority 5 + Closest 10: plant, as aitpnear to the second.
      aitpmt1   MaxTargets 1, 8 Guardians: 到电厂 4 from s13, 在家 4 to s55 -- one team.
      aitpmt2   MaxTargets 2: 到电厂 4 from s13, 到兵营 4 from s26 (the second team left s19-21), 在家 0 -- a team per
                slot, the second slot's unique nearest = the barracks (the plant is the first slot's).
    (aitpmt1's first run read 在家 2: the home area was then a 300 square that held 6 of the 8 start spots; widened.)
    The simulator (simai) gives the same eight (benches/ai/targets/readings.toml#engine_aitargetpick target_pick_as_on_the_bench).
    Bench 2026-11-09 (B round 82, TeamTemplate.Priority: two always-on states over the same 4 Guardians, P = the plant
    (ClosestStructure), B = the barracks (CNVHBarracks); one run each, run first with the model's guess plant 4 for all):
      aitpprs   P STANDARD / B STANDARD: 在家 4 to s16, 3/2/1/0 s17-s20; 到兵营 2 @ s21, 4 s23-s55; 到电厂 0 throughout.
      aitpprh   P STANDARD / B HIGH: the same to the second.
      aitpprl   P LOW / B STANDARD: the same (到兵营 3 @ s22).
      aitpprp   P HIGH / B STANDARD: 在家 2 @ s12, 0 @ s14; 到电厂 4 s15-s56; 到兵营 0 -- the plant, a second earlier than
                aitpnear alone.
    Read: the higher team Priority takes the units; on a tie the barracks' state (listed second) wins, though its target
    is found later (s19 in aitpvk) -- nobody went to the plant first. Not split: a tie by list order or by state draw.
    simai sends all four to the plant (mismatch, benches/ai/targets/readings.toml#engine_aitargetpick team_priority_as_on_the_bench_on_a_tie).
    Bench 2026-11-09 (B round 85, EndBehavior, the check script kills the plant at s35; one run each; 到电厂 到兵营 到坦克 在家):
      all four: out s13-s14, 到电厂 4 s15-s34 (the Guardians did not kill it by s32 as the simulator has).
      aiendd   DISBAND:                 到电厂 2 @ s37, 0 s38-s39, 到兵营 2 @ s40, 4 from s42 -- PASS (as the model)
      aiendh   RETURN_HOME_AND_DISBAND: the same, 到兵营 4 from s41, never home -- PASS (as the model)
      aiendr   RAMPAGE: 到电厂 0 @ s37, 到兵营 1 @ s38, 4 from s40; 到坦克 0 -- FAIL: the barracks, not the nearest
               enemy unit (the model's tank); RAMPAGE here looks like DISBAND (a nearer structure? the tank parked further?)
      aiendp   PICK_NEW_TARGET: 到电厂 4 to s85 -- FAIL: they stay where the plant was; the model sends them to the
               barracks (the slot re-picked). Not yet a strict xfail in tests/test_simai.py.
    """
    from parts import Test, counted, square, Script

    HOME = 'CNV TP Home'
    AREAS = (('CNV TP Plant Area', 'plant', 'CNV_TP_Plant', '到电厂'),
             ('CNV TP Barracks Area', 'barracks', 'CNV_TP_Barracks', '到兵营'),
             ('CNV TP Tank Area', 'tank', 'CNV_TP_Tank', '到坦克'))
    LAG = 4.0
    AT, SECONDS = 40.0, 50.0
    END = 75.0                    # the EndBehavior variants (aiend*): where they stand at s75 (the plant dies at s35)


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        kill = m.facts.get('kill plant at')
        keep = [m.role(r).name for _, r, _, _ in AREAS if not (kill is not None and r == 'plant')]
        keep += [m.role('kirov').name] if 'expect kirov' in m.facts else []
        t.scripts.append(Script('Test - targets keep', [], [('UNIT_SET_HEALTH', n, 100.0) for n in keep], once=False))
        if kill is not None:          # EndBehavior variants: the plant dies, where do they stand at the end
            t.scripts += [Script('Test - kill set', [], [('SET_MILLISECOND_TIMER', 'Test Kill Plant', kill)]),
                          Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Plant')],
                                 [('NAMED_KILL', m.role('plant').name)])]
        end = END if kill is not None else AT
        (tank,) = m.cnv_units
        areas = AREAS
        if 'expect kirov' in m.facts:         # four counter lines fit: the Kirov's in the barracks' place
            areas = tuple(a for a in AREAS if a[1] != 'barracks') + (('CNV TP Kirov Area', 'kirov', 'CNV_TP_Kirov', '到飞艇'),)
        for area, role, counter, label in areas:
            o = m.find(m.role(role).name)
            t.areas[area] = square(o.x, o.y, 180.0 if role == 'kirov' else 340.0)    # the Kirov's clear of home
            counted(counter, label, t, template=tank, area=area, player=s1)
            want = m.facts['expect ' + role]
            if kill is not None:
                t.expect.append((label, end, '>=', 3, end + 1) if want else (label, end, '==', 0, end + 1))
            else:
                t.expect.append((label, 1, 'ever>=', 3, AT) if want else (label, AT, '==', 0, AT + 1))
        x, y = m.site('east base')        # every start spot (x -280..-200, y +160..+370), clear of the plant's square
        t.areas[HOME] = [(x - 300, y - 400), (x + 300, y - 400), (x + 300, y + 450), (x - 300, y + 450)]
        counted('CNV_TP_Home', '在家', t, template=tank, area=HOME, player=s1)
        t.expect.append(('在家', end, '==', m.facts['expect home'], end + 1))
        secs = END + 5.0 if kill is not None else SECONDS
        t.bench = [('bench_watch', dict(seconds=secs + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a} for k in ('aitpnear', 'aitpvk', 'aitpfk', 'aitpunit', 'aitpphi', 'aitpplo', 'aitpmt1',
                                     'aitpmt2', 'aitpairn', 'aitpairf', 'aitpairr', 'aitpunr', 'aitpprs', 'aitpprh', 'aitpprp', 'aitpprl',
                                     'aiendr', 'aiendd', 'aiendh', 'aiendp')}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a))


def engine_aitoponly():
    """Priority fallback contrast: plant/barracks/tank/home counters at s40.

    aitopon predicts 0/0/0/4; aitopoff and positive host aitopctl 0/4/0/0.
    The host keeps targets alive; explicit s4=30, p1=10 priorities are set at wake.
    Evidence: work/re/c_toponly_report.md. No same-frame priority readback claimed.
    """
    a = engine_aitargetpick()["shared"].a

    CHECKS = {build: {'a': a} for build in ('aitopon', 'aitopoff', 'aitopctl')}
    return dict(CHECKS=CHECKS)


@cache
def engine_aiunderattack():
    """UnderAttack set / clear on the bench: Hammer A shoots the AI's power plant and is deleted mid-fight (source deleted);
    Hammer B shoots it after A's window ran out and is then stopped, staying alive (ceasefire, source alive).

    Readings come from ra3ext `ua:` lines (experimental/cnv/teamlog.py under_attack); the check itself only orders the
    fight and stops it. Record: work/re/d161_underattack.md.
    """
    from parts import Script, Test


    def a(m):
        t = Test()
        tank, tank_b, plant = m.role('ua tank').name, m.role('ua tank b').name, m.role('closest plant').name
        f = m.facts   # SET_MILLISECOND_TIMER takes seconds (d163)
        t.scripts.append(Script('Test - start', [], [('SET_MILLISECOND_TIMER', 'UA Attack', f['attack at']),
                                                     ('SET_MILLISECOND_TIMER', 'UA Stop', f['stop at']),
                                                     ('SET_MILLISECOND_TIMER', 'UA B Attack', f['b attack at']),
                                                     ('SET_MILLISECOND_TIMER', 'UA B Stop', f['b stop at']),
                                                     ('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Test - attack', [('TIMER_EXPIRED', 'UA Attack')], [('NAMED_FORCE_ATTACK_NAMED', tank, plant)]))
        t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'UA Stop')], [('NAMED_DELETE', tank)]))
        t.scripts.append(Script('Test - b attack', [('TIMER_EXPIRED', 'UA B Attack')],
                                [('NAMED_FORCE_ATTACK_NAMED', tank_b, plant)]))
        t.scripts.append(Script('Test - b stop', [('TIMER_EXPIRED', 'UA B Stop')], [('NAMED_STOP', tank_b)]))
        t.bench = [('bench_watch', dict(seconds=200, every=10, sheet=False, lines=4))]
        return t


    CHECKS = {'aiunderatk': {'a': a}}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a))


def engine_aiunderattack_gate_c():
    """Read delayed UnderAttack / ordinary friendly gates; no episode is a gate reading."""
    a = engine_aiunderattack()["shared"].a

    CHECKS = {'aiuagate': {'a': a}}
    return dict(CHECKS=CHECKS)


def engine_aiunderattackby():
    """UnderAttackBy diagnostic: read tgt candidates together with ua hit sources.

    The prediction is land selects the real attacker / water rejects it. A missing
    source in the candidate list is a world-fact gate, not a location verdict.
    No counter or movement proxy establishes source registration. Evidence:
    work/re/c_underattackby_fight_report.md.
    """
    fight = engine_aiunderattack()["shared"].a


    def a(m):
        t = fight(m)
        t.bench = [('bench_watch', dict(seconds=100, every=10, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('aiuabl', 'aiuabw')}
    return dict(CHECKS=CHECKS)


def engine_aivital():
    """Packed native status (100) + goal count (10 each) + home count, four lanes.

    The mask reads original UNIT_HAS_OBJECT_STATUS, never model target selection.
    Script-set bits do not establish real flight, links or candidate qualification.
    """
    from parts import Script, Test, counted, square, status


    def a(m):
        t = Test()
        for i, bit in enumerate(m.facts['vital bits']):
            name = m.role(f'vital sample {i}').name
            counter = f'Vital_packed{i}'
            t.scripts.append(Script(f'Vital reset {i}', [], [('SET_COUNTER', counter, 0)], once=False))
            t.scripts.append(Script(f'Vital read {i}', [('UNIT_HAS_OBJECT_STATUS', name, status(bit))],
                [('INCREMENT_COUNTER', 100, counter)], once=False))
            t.scripts.append(Script(f'Vital keep sample {i}', [], [('UNIT_SET_HEALTH', name, 100.0)], once=False))
        x, y = m.site('east base')
        t.areas['Vital home'] = [(x-400,y-400),(x+400,y-400),(x+400,y+500),(x-400,y+500)]
        for i, unit in enumerate(m.cnv_units):
            goal = m.find(m.role(f'vital goal {i}').name)
            area = f'Vital goal {i}'
            t.areas[area] = square(goal.x, goal.y, 340)
            for location, label, ar in [('goal', f'目标{i}', area), ('home', f'家{i}', 'Vital home')]:
                counted(f'Vital_{location}{i}', label, t, template=unit, area=ar, player=m.player('s1'))
                for n in range(1, 9):
                    t.scripts.append(Script(f'Vital pack {location} {i} {n}',
                        [('COUNTER', f'Vital_{location}{i}', 2, n)],
                        [('INCREMENT_COUNTER', n * (10 if location == 'goal' else 1), f'Vital_packed{i}')], once=False))
        members = [r for r in m.cast if r.startswith(('peacekeeper ', 'guardian ', 'vital member '))]
        t.scripts.append(Script('Vital keep teams', [], [
            ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in members], once=False))
        t.counters = [(f'Vital_packed{i}', f'路{i}') for i in range(4)]
        for _, label in t.counters:
            t.expect += [(label, 2, '>=', 100, 3), (label, 4.5, '<=', 99, 5.5),
                         (label, 55, '==', 140 if m.facts['vital matching'] else 4, 60)]
        t.bench = [('bench_watch', dict(seconds=65, every=0.5, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {name: {'a': a} for name in ('aivitalon', 'aivitaloff')}
    return dict(CHECKS=CHECKS)


def engine_aiwake():
    """Read benches/ai/targets/scenes.py#aiwake_bench's aialobsw: when the AI's pre-placed Peacekeepers leave home, against the gated wake.

    Prediction (H-a, the cheaper reading, handoff-b section 160): the old wake ran at f0; gated, nothing leaves before
    the wake -- 步兵在家 4 to s29, someone at the far plant after it. A FAIL with 步兵在家 0 by ~s10 is H-b (the side
    runs its teams before the wake); the team log (ra3ext.log, CNVTeams) gives the frame the named team fills.

    MEASURED (bench 11-13, CampAlObsWW_mcp_1113_003603, FAIL as a prediction): the wake ran at pass 450 (唤醒前 stops
    at 450, ~s28), yet 步兵在家 4 -> 0 over s10-s12 and 到远厂 4 from s17 -- the 10 s wake's timeline unchanged; the
    team log has the SimpleAttack team empty at f17, 4 members at f21, the first team move at f26, as aialobslo.
    H-a no (the old wake did not run at f0); H-b yes: a side with a personality runs its states and teams from the
    start, before UNIT_AI_TRANSFER_ALL / MAKE_BASE. The simulator's AI starts at the wake (simai.SimAI.attach) -- to fix.
    """
    from benches.ai.tactics.checks import engine_airetreat
    ar = engine_airetreat()["shared"]
    st = engine_aistate()["shared"]


    def probe(m):
        f = m.facts                         # the mission publishes its counters and wake tick (checks ask the mission)
        t = ar.a(m, 'airet')
        t.counters = [c for c in t.counters if c[1] in ('步兵在家', '到远厂')] + [(f['tick counter'], '帧'),
                                                                         (f['pre counter'], '唤醒前')]
        t.expect = [('步兵在家', 1, '==', 4, 29), ('唤醒前', 31, '>=', f['wake tick'] - 1, 60), ('到远厂', 31, 'ever>=', 1, 70)]
        t.bench = [('bench_watch', dict(seconds=72, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def const(m):
        """aistateconstw: H-g predicts 步兵在家 / 坦克在家 4 to ~s30 and 0 by ~s36; out by s16 = targets found before
        the wake."""
        f = m.facts
        t = st.a(m)
        t.counters = [c for c in t.counters if c[1] in ('步兵在家', '坦克在家')] + [(f['tick counter'], '帧'),
                                                                            (f['pre counter'], '唤醒前')]
        t.expect = [('步兵在家', 1, '==', 4, 26), ('坦克在家', 1, '==', 4, 26), ('步兵在家', 31, 'ever==', 0, 45)]
        t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'aialobsw': {'w': probe}, 'aistateconstw': {'w': const}}
    return dict(CHECKS=CHECKS)


def engine_aiwater():
    """Three original counters for ThreatToWater; work/re/c_water_report.md.

    No threat value or same-frame candidate eligibility is published by this host.
    Keep all named units healthy so combat losses cannot masquerade as sorting.
    """
    from parts import Test, Script, counted, square


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - water reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        keep = [m.role(r).name for r in ('plant', 'barracks', 'tank', 'water sample', 'air sample') if r in m.cast]
        keep += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
        t.scripts.append(Script('Test - water keep', [], [('UNIT_SET_HEALTH', n, 100.0) for n in keep], once=False))
        for role, label in [('plant', '近处'), ('barracks', '远处')]:
            o = m.find(m.role(role).name)
            area = 'CNV Water ' + role
            t.areas[area] = square(o.x, o.y, 340)
            counted('CNV_Water_' + role, label, t, template=m.cnv_units[0], area=area, player=s1)
            t.expect.append((label, 40, '==', m.facts['expect ' + role], 41))
        x, y = m.site('east base')
        t.areas['CNV Water Home'] = [(x-300, y-400), (x+300, y-400), (x+300, y+450), (x-300, y+450)]
        counted('CNV_Water_Home', '在家', t, template=m.cnv_units[0], area='CNV Water Home', player=s1)
        t.expect.append(('在家', 40, '==', 0, 41))
        t.bench = [('bench_watch', dict(seconds=54, every=1, sheet=False, lines=3))]
        return t


    CHECKS = {k: {'a': a} for k in ('aiwaterdist', 'aiwaterthreat', 'aiwaternear', 'aiwaterfar', 'aiairnone', 'aiairsamp')}
    return dict(CHECKS=CHECKS)


BENCHES = (
    engine_aibridge, engine_aibuildexclude, engine_aiclosestenemy, engine_aiconyard,
    engine_aicrate, engine_aienemyfilter, engine_aienemygarr, engine_aiforbid,
    engine_aifrdistance, engine_aifriendly, engine_aihusk, engine_ailocation,
    engine_aimindist, engine_aiminvalue, engine_ainamed, engine_aipoint,
    engine_aiprio, engine_aisearch, engine_aishore, engine_aistate,
    engine_aitarget, engine_aitargetpick, engine_aitoponly, engine_aiunderattack,
    engine_aiunderattack_gate_c, engine_aiunderattackby, engine_aivital, engine_aiwake,
    engine_aiwater,
)
