"""AI production checks."""
from functools import cache
from types import SimpleNamespace


def ai():
    """The skirmish AI probe (benches/ai/production/scenes.py#ai_bench), read off the counters (all the enemy's: Soviet_1):

    wake: asleep it neither builds nor spends; woken it spends and builds (a power plant); told to attack, its army
      comes over to the player's base.
    asleep: the control, never woken: no power plant, no money spent, nobody at the player's base the whole run.
    capped: the plan's 敌方AI (benches/ai/production/scenes.py#ai_plan_bench), the standard way -- see there.

    Bench 2026-10-25 (wake): asleep it spent nothing; woken it built a barracks and two power plants and spent the 10000
    in ~80 s; with that personality (Mount Rushmore's president) nothing reached the player's base by 390 s.
    """
    from parts import Script, Test, counted, square

    LAG = 4.0                                       # the bench's clock runs ~3 s behind the mission's
    HOME = 700.0                                    # half-side of the area counted around the player's start
    RUN_AFTER_ATTACK = 240.0


    def readout(m):
        """Not kind-in-area counts: the engine counts every player's with those (probe/count, 2026-10-25). By template
        (the player's own count) and the has-units test instead."""
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        s1 = m.player('s1')
        t.counters.append(('CNV_AI_Money', '敌方资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AI_Money')], once=False))
        counted('CNV_AI_Power', '敌方电厂', t, template='AlliedPowerPlant', player=s1)
        counted('CNV_AI_Barracks', '敌方兵营', t, template='AlliedBarracks', player=s1)
        t.areas['Test home'] = square(*m.site('start'), HOME)
        t.counters.append(('CNV_AI_Home', '在我方'))
        t.scripts += [Script('Test - home zero', [], [('SET_COUNTER', 'CNV_AI_Home', 0)], once=False),
                      Script('Test - home', [('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', s1, 'Test home')],
                             [('SET_COUNTER', 'CNV_AI_Home', 1)], once=False)]
        return t


    def wake(m):
        t, f = readout(m), m.facts
        w, a = f['wake at'], f['attack at']
        t.expect += [('敌方电厂', 1, '==', 0, w - LAG), ('敌方资金', 1, '==', 0, w - LAG),
                     ('在我方', 1, '==', 0, w - LAG),
                     ('敌方资金', w + LAG, 'ever>', 0, w + 30),                   # given its money
                     ('敌方电厂', w + LAG, 'ever>=', 1, a),                       # and builds with it
                     ('在我方', a, 'ever==', 1, a + RUN_AFTER_ATTACK)]             # sent over once told to
        t.bench = [('bench_watch', dict(seconds=a + RUN_AFTER_ATTACK, every=5, sheet=False, lines=len(t.counters)))]
        return t


    def capped(m):
        """The plan's 敌方AI (benches/ai/production/scenes.py#ai_plan_bench): the generated personality in use -- asleep it builds nothing,
        woken it builds, never past its caps -- and its army hurts the player's base: guardians lost (bench 2026-10-25:
        "enemy units by the player's start" was its miner at the player's ore, not an attack). That day's runs: the
        first guardian lost ~60 s after waking, all three and the yard to 2 % by ~175 s -- and the same run without
        SKIRMISH_AI_TRANSFER_ALL (once the plan's 进攻) alike second for second, so the plan has no such word."""
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        f, ai = m.facts, m.ai_player()
        counted('CNV_AI_Power', '敌方电厂', t, template='AlliedPowerPlant', player=ai)
        counted('CNV_AI_Barracks', '敌方兵营', t, template='AlliedBarracks', player=ai)
        counted('CNV_AI_Yard', '我方建造厂血量', t, health=m.role('player yard').name)
        counted('CNV_AI_Guards', '我方守护者', t, template='AlliedAntiVehicleVehicleTech1')
        w, run = f['wake at'], f['watch']
        t.expect += [('敌方电厂', 1, '==', 0, w - LAG), ('敌方电厂', w + LAG, 'ever>=', 1, w + 90),
                     ('敌方电厂', 1, '<=', f['power cap']), ('敌方兵营', 1, '<=', f['barracks cap']),
                     ('我方守护者', 1, '==', 3, w + 30), ('我方守护者', w + 30, 'ever<', 3, w + run)]
        x, y = m.site('base edge')                  # the frames show the attack coming
        t.bench = [('bench_camera', dict(x=x, y=y, look=False)),
                   ('bench_watch', dict(seconds=w + run, every=6, sheet=False, lines=len(t.counters)))]
        return t


    def asleep(m):
        t, f = readout(m), m.facts
        t.expect += [('敌方电厂', 1, '==', 0), ('敌方资金', 1, '==', 0), ('在我方', 1, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=f['attack at'] + 30, every=5, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'ai': {'wake': wake},
        'ai_asleep': {'asleep': asleep},
        'ai_plan': {'capped': capped},
    }
    return dict(CHECKS=CHECKS)


def aistep():
    """敌方AI 分档 tests (benches/ai/production/scenes.py#aistep_bench). Counted: the AI's IFVs, and latches at 1 if it had a war factory / an
    IFV before its step let them go (the step's flag CNV_AS_AI_Step_1 still 0). Bench 2026-10-27, the step at 90 s after
    waking: its factory came only after; held back guardians it never built, held or not (aistep_free).

    stepped: with a war factory up before the step, no IFV until the step; some once it let them go.
    free: the control, nothing held back -- it builds IFVs (before the step's time too).
    """
    from parts import Script, Test, counted

    FACTORY, IFV = 'AlliedWarFactory', 'AlliedAntiAirVehicleTech1'


    def watch(m, t):
        ai = m.ai_player()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('Test IFV', 'AI步兵车', t, template=IFV, player=ai)
        m.spawns |= {FACTORY.lower(), IFV, IFV.lower()}
        run = m.facts['wake at'] + m.facts['watch']
        return ai, run


    def stepped(m):
        t = Test()
        ai, run = watch(m, t)
        t.counters.append(('Test Ready', '放开前有工厂'))
        t.scripts += [Script('Test - ready zero', [], [('SET_COUNTER', 'Test Ready', 0)]),
                      Script('Test - ready', [('PLAYER_HAS_OBJECT_COMPARISON', ai, 3, 1, FACTORY.lower()),
                                              ('FLAG', 'CNV_AS_AI_Step_1', 0)], [('SET_COUNTER', 'Test Ready', 1)])]
        t.counters.append(('Test Early', '放开前就有'))
        t.scripts += [Script('Test - early zero', [], [('SET_COUNTER', 'Test Early', 0)]),
                      Script('Test - early', [('PLAYER_HAS_OBJECT_COMPARISON', ai, 3, 1, IFV.lower()),
                                              ('FLAG', 'CNV_AS_AI_Step_1', 0)], [('SET_COUNTER', 'Test Early', 1)])]
        t.expect += [('放开前就有', 1, '==', 0), ('放开前有工厂', 1, 'ever==', 1), ('AI步兵车', 1, 'ever>=', 1)]
        t.bench = [('bench_watch', dict(seconds=run, every=6, sheet=False, lines=len(t.counters)))]
        return t


    def free(m):
        t = Test()
        _, run = watch(m, t)
        t.expect += [('AI步兵车', 1, 'ever>=', 1)]
        t.bench = [('bench_watch', dict(seconds=run, every=6, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'aistep': {'stepped': stepped},
        'aistep_free': {'free': free},
    }
    return dict(CHECKS=CHECKS)


def engine_aiaesthetics():
    """UseAestheticsManager true/false at fixed Distance=2000.

    Named square occupancy, a post-timer displacement latch and survival separate
    movement from loss or failed teleport. No dynamic membership or exact circle
    geometry is claimed. Predictions/evidence: work/re/c_aesthetics_report.md.

    RESULTS: both builds PASS (5/5). Enabled leaves 300 before displacement,
    returns inside 900, then leaves again. Disabled returns inside both squares.
    Both survive and latch displacement. Model location replays strict xfail;
    stand-point/readiness consumers need B investigation, no inventory promotion.
    """
    from model import Script, Test, counted, square


    def a(m):
        t = Test()
        name = m.role('ai guardian 1').name
        for radius in (300, 900):
            area = f'CNV Aes Ring {radius}'
            t.areas[area] = square(*m.site('east base'), radius)
            counted(f'CNV_Aes_R{radius}', f'圈{radius}', t, named=name, area=area)
        t.counters += [('CNV_Aes_Pushed', '传送出圈')]
        t.scripts += [Script('Aesthetics - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                      Script('Aesthetics - displacement',
                             [('TIMER_EXPIRED', 'CNV Distance Push'),
                              ('NAMED_OUTSIDE_AREA', name, 'CNV Aes Ring 900')],
                             [('SET_COUNTER', 'CNV_Aes_Pushed', 1)])]
        counted('CNV_Aes_Alive', '坦克总数', t, template=m.cnv_units[0], player=m.player('s1'))
        home = 1 - m.facts['aesthetics enabled']
        t.expect = [('圈900', 20, '==', 1, 21), ('传送出圈', 65, '==', 1, 66),
                    ('坦克总数', 65, '==', 1, 66), ('圈300', 65, '==', home, 66),
                    ('圈900', 65, '==', home, 66)]
        t.bench = [('bench_watch', dict(seconds=74, every=1, sheet=False, lines=4))]
        return t


    def p(m):
        """B 11-27 patrol builds: the Guardian in 300 / 900 by the second; the stand orders are read off the ext log."""
        t = Test()
        name = m.role('ai guardian 1').name
        for radius in (300, 900):
            area = f'CNV Aes Ring {radius}'
            t.areas[area] = square(*m.site('east base'), radius)
            counted(f'CNV_Aes_R{radius}', f'圈{radius}', t, named=name, area=area)
        t.scripts += [Script('Aesthetics - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
        counted('CNV_Aes_Alive', '坦克总数', t, template=m.cnv_units[0], player=m.player('s1'))
        t.expect = [('坦克总数', 60, '==', 1, 61)]
        t.bench = [('bench_watch', dict(seconds=64, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('aiaeson', 'aiaesoff')} | \
        {name: {'p': p} for name in ('aiaesi10', 'aiaesi0', 'aiaesh300', 'aiaesh0')}
    return dict(CHECKS=CHECKS)


def engine_aiallbuild():
    """Native all-enemies construction contrast; work/re/c_allbuild_report.md.

    INFERRED prediction: including the secondary twenty-tank enemy changes the
    native candidate scores or chosen anti-vehicle mix versus the primary ten
    infantry enemy alone. Friendship at 70s tests removal from that enemy set.
    Opening orders may ignore this input: inspect bpick/border same-pass choices,
    not money or an empty candidate list. No expected exact clock is invented.
    """
    from checks.engine_aiallbuild import a


    CHECKS = {'aiallbuildon': {'a': a}, 'aiallbuildoff': {'a': a}}
    return dict(CHECKS=CHECKS)


def engine_aibuilding():
    """IsBuildingHeuristic empty-queue probe, PassIfBuilding true versus false.

    Prediction: at s40 false has four Twinblades at the land plant, true four
    at home. No money is supplied; the existing AI yard remains standing.
    This checks only the idle boundary, not KindOf matching in an active queue.
    E83 engine readings: false s13-s51 = 4/0/1; true s1-s51 = 0/4/1
    (target/home/yard); both PASS, default simulator replay passes at s40.
    Evidence: work/re/e_building_e83.md.
    """
    from parts import Script, Test, counted, square


    def a(m):
        t = Test()
        t.scripts.append(Script('Building reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Building keep', [], [
            ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('land', 'water')], once=False))
        target = m.find(m.role('land').name)
        t.areas['Building target'] = square(target.x, target.y, 340.0)
        x, y = m.site('east base')
        t.areas['Building home'] = [(x - 300, y - 400), (x + 300, y - 400),
                                    (x + 300, y + 450), (x - 300, y + 450)]
        for key, label in (('target', '到陆厂'), ('home', '在家')):
            counted('Building_' + key, label, t, template=m.cnv_units[0],
                    area='Building ' + key, player=m.player('s1'))
            t.expect.append((label, 40, '==', m.facts['expect ' + key], 41))
        counted('Building_yards', '基地数', t, template='AlliedConstructionYard', player=m.player('s1'))
        t.expect.append(('基地数', 40, '==', 1, 41))
        t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=3))]
        return t


    CHECKS = {name: {'a': a} for name in ('aibldtrue', 'aibldfalse')}
    return dict(CHECKS=CHECKS)


def engine_aibuildkind():
    """C active-queue KindOf match/nonmatch probe; prediction recorded before runs.

    At s40 matching FS_POWER sends four helicopters to the target; FS_BARRACKS
    keeps four home. Both must complete at least two power plants, and retain
    one yard. See work/re/c_buildkind_report.md for observations and limits.
    Measured: both PASS, s40 target/home/plants/yard=4/0/4/1 and 0/4/4/1.
    The multi-token OR controls reproduce these readings with FS_BARRACKS
    FS_POWER and FS_BARRACKS FS_TECHNOLOGY; see work/re/c_buildkind_or_report.md.
    False variants measured 0/4/4/1 (match) and 4/0/4/1 (nonmatch), both PASS;
    model match diverges, see work/re/c_buildkind_false_report.md.
    """
    from parts import Script, Test, counted, square


    def check(m):
        t = Test()
        t.scripts.append(Script('Kind reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Kind keep', [], [
            ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('land', 'water')], once=False))
        target = m.find(m.role('land').name)
        t.areas['Kind target'] = square(target.x, target.y, 340)
        x, y = m.site('east base')
        t.areas['Kind home'] = [(x - 300, y - 400), (x + 300, y - 400),
                                (x + 300, y + 450), (x - 300, y + 450)]
        for key, label in (('target', '到陆厂'), ('home', '在家')):
            counted('Kind_' + key, label, t, template=m.cnv_units[0],
                    area='Kind ' + key, player=m.player('s1'))
            t.expect.append((label, 40, '==', m.facts['expect ' + key], 41))
        counted('Kind_plants', '电厂数', t, template='AlliedPowerPlant', player=m.player('s1'))
        counted('Kind_yards', '基地数', t, template='AlliedConstructionYard', player=m.player('s1'))
        t.expect += [('电厂数', 40, '>=', 2, 41), ('基地数', 40, '==', 1, 41)]
        t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': check} for name in
              ('aibkindyes', 'aibkindno', 'aibkindoryes', 'aibkindorno',
               'aibkindfalseyes', 'aibkindfalseno')}
    return dict(CHECKS=CHECKS)


def engine_aicap():
    """SpecificUnitCap: MEDIUM cap two, HARD-only cap two, and uncapped control.

    Prediction (INFERRED model rule): MEDIUM Peacekeepers reach two and never
    exceed it; HARD-only and control reach at least three. Javelins remain
    available in every build. Counts are living owned units, not queue entries.
    All builds run on the same MEDIUM setting, so the mask alone is varied.
    Evidence and scope: work/re/e_aicap_e80.md.
    """
    from parts import Script, Test, counted


    def a(m):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        for counter, label, template in (
                ('CNV_CapPk', '维和总数', 'AlliedAntiInfantryInfantry'),
                ('CNV_CapJav', '标枪总数', 'AlliedAntiVehicleInfantry')):
            m.spawns.add(template)
            counted(counter, label, t, template=template, player=m.player('s1'))
        active = m.facts['cap active']
        t.expect = [('维和总数', 70., '<=', 2, 100.)] if active else []
        t.expect += [('维和总数', 70., 'ever>=', 2 if active else 3, 100.),
                     ('标枪总数', 70., 'ever>=', 3, 100.)]
        t.bench = [('bench_watch', dict(seconds=104., every=1, sheet=False, lines=2))]
        return t


    def b(m):
        """Discriminate an opening-only bypass from caps ignored after the opening.

        First aicapmed:a made three Peacekeepers by s54 despite cap two.
        Preserve that failed prediction in a; this longer run tests whether the
        same cap prevents further production once the opening finishes.
        """
        t = a(m)
        active = m.facts['cap active']
        t.expect = [('维和总数', 150., '<=', 2, 200.)] if active else []
        t.expect += [('维和总数', 150., 'ever>=', 2 if active else 4, 200.),
                     ('标枪总数', 150., 'ever>=', 4, 200.)]
        t.bench = [('bench_watch', dict(seconds=204., every=1, sheet=False, lines=2))]
        return t


    CHECKS = {name: {'a': a, 'b': b} for name in ('aicapctrl', 'aicapmed', 'aicaphard')}
    return dict(CHECKS=CHECKS)


def engine_aiconstweight():
    """C: ConstantHeuristic.Weight, named zero/one engine control.

    Pre-run s40 prediction: zero infantry home/total=4/4, one=0/4;
    unregistered tank control home=4 in both. Relative positive odds are gap.
    Measured 2026-11-13: both PASS, one run each; zero s1-s46=4/4/4,
    one s1-s13=4/4/4 then s14-s46=0/4/4 (home/total/tank control).
    See work/re/c_constweight_report.md. Consumes only published mission roles.
    """
    from parts import Script, Test, counted, square


    def check(m):
        t = Test()
        t.areas['Weight home'] = square(*m.site('east base'), 450)
        t.scripts.append(Script('Weight reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Weight keep target', [],
            [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
        inf, tank = m.cnv_units
        for key, label, unit, area, expected in (
                ('CW_home', '步兵在家', inf, 'Weight home', m.facts['expect infantry home']),
                ('CW_total', '步兵总数', inf, None, 4),
                ('CW_tank', '坦克在家', tank, 'Weight home', 4)):
            counted(key, label, t, template=unit, area=area, player=m.player('s1'))
            t.expect.append((label, 40, '==', expected, 41))
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=3))]
        return t


    CHECKS = {name: {'a': check} for name in ('aicwzero', 'aicwone')}
    return dict(CHECKS=CHECKS)


def engine_aiexpansion():
    """C Expansion readings; candidate field eligibility remains INFERRED.

    Two candidate-field areas and ordinary entity control, plus home.
    Team/command logs come from the mission's passive CNVTeams host. First Expansion
    reading: east=4, bluff=0, entity=0 at s30; expectations below retain those values.
    """
    from parts import Test, Script, counted, square


    def a(m):
        t = Test()
        s1 = m.player('s1')
        tank, = m.cnv_units
        plant = m.find(m.role('plant').name)
        points = [('east', m.facts['candidate east'], '候选东'),
                  ('bluff', m.facts['candidate bluff'], '候选崖'),
                  ('entity', (plant.x, plant.y), '普通实体'),
                  ('home', m.site('east base'), '在家')]
        for key, xy, label in points:
            area = 'CNV Expansion ' + key
            t.areas[area] = square(*xy, 350.0)
            counted('CNV_Exp_' + key, label, t, template=tank, player=s1, area=area)
        t.scripts.append(Script('Test - keep targets', [],
                               [('UNIT_SET_HEALTH', m.role(r).name, 100.0)
                                for r in ('plant', 'barracks', 'tank')], once=False))
        if 'base preferred not' in m.facts:
            # Readings only: captured base type/eligibility is not observed.
            # See work/re/c_basenot_report.md; ore fields do not establish bases.
            pass
        elif 'base sort order' in m.facts:
            # BaseSelection.SortOrder contrast: readings only. Two ore fields do
            # not establish two eligible bases or their ages. See work/re/c_basesort_report.md.
            pass
        elif m.facts['expansion']:
            t.expect += [('候选东', 30, '==', 4, 40), ('候选崖', 30, '==', 0, 40),
                         ('普通实体', 30, '==', 0, 40)]
        else:
            # Reach the entity by s30. A one-second terminal window can contain no
            # capture on a busy bench (first run: s14..68 all four, no s30 sample).
            t.expect.append(('普通实体', 1, 'ever>=', 4, 30))
        t.bench = [('bench_watch', dict(seconds=79 if m.facts.get('dual bases') else 49,
                                      every=1, sheet=False, lines=4))]
        return t


    CHECKS = {key: {'a': a} for key in ('aiexpc', 'aiexpw', 'aiexpctl', 'aibsold', 'aibsnew', 'aibncap', 'aibnnone',
                                      'aibs2old', 'aibs2new')}


    def buildings(m):
        """Second-round control: confirm both physical yards, beside the team readings.

        Physical yards are not proof of two AI base records or their eligibility.
        """
        t = Test()
        s1 = m.player('s1')
        tank, = m.cnv_units
        points = [('east', m.facts['candidate east'], tank, '候选东'),
                  ('bluff', m.facts['candidate bluff'], tank, '候选崖'),
                  ('old yard', m.site('east base'), 'AlliedConstructionYard', '东建厂'),
                  ('new yard', m.point('new yard'), 'AlliedConstructionYard', '崖建厂')]
        for key, xy, template, label in points:
            area = 'CNV Dual ' + key
            t.areas[area] = square(*xy, 350.0)
            counted('CNV_Dual_' + key.replace(' ', '_'), label, t,
                    template=template, player=s1, area=area)
        t.scripts.append(Script('Test - keep targets', [],
                               [('UNIT_SET_HEALTH', m.role(r).name, 100.0)
                                for r in ('plant', 'barracks', 'tank')], once=False))
        t.expect = [('东建厂', 30, '==', 1, 40), ('崖建厂', 30, '==', 1, 40)]
        t.bench = [('bench_watch', dict(seconds=79, every=1, sheet=False, lines=4))]
        return t


    CHECKS['aibs2old']['b'] = buildings
    CHECKS['aibs2new']['b'] = buildings
    CHECKS['aibs3old'] = {'b': buildings}
    CHECKS['aibs3new'] = {'b': buildings}
    CHECKS['aibn2old'] = {'b': buildings}
    CHECKS['aibn2new'] = {'b': buildings}
    CHECKS['aibp1old'] = {'b': buildings}
    CHECKS['aibp1new'] = {'b': buildings}
    return dict(CHECKS=CHECKS)


def engine_aiintervalfrom():
    """C: IntervalHeuristic.CountFrom MAP_START/AI_START named controls.

    Same map, personality, army and s10 wake; only CountFrom changes.
    Pre-run prediction home/total: s24 both 4/4; s32 map=0/4, ai=4/4;
    s42 both 0/4. IntervalTime=25s/ActiveTime=30s. First window only,
    repeated cycling and exact evaluation frames remain gap.
    Measured 2026-11-13, one PASS each: map home=4 s1-27 then 0 s28-46;
    ai home=4 s1-37, 2 s38, 0 s39-46; total=4 throughout both runs.
    See work/re/c_intervalfrom_report.md. Uses only published mission data.
    """
    from parts import Script, Test, counted, square


    def check(m):
        t = Test()
        t.areas['Interval home'] = square(*m.site('east base'), 450)
        t.scripts.append(Script('Interval reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Interval keep target', [],
            [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
        tank, = m.cnv_units
        counted('CIF_home', '坦克在家', t, template=tank, area='Interval home', player=m.player('s1'))
        counted('CIF_total', '坦克总数', t, template=tank, player=m.player('s1'))
        for second, home in ((24, 4), (32, m.facts['home at 32']), (42, 0)):
            t.expect += [('坦克在家', second, '==', home, second + 1),
                         ('坦克总数', second, '==', 4, second + 1)]
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=2))]
        return t


    CHECKS = {name: {'a': check} for name in ('aiintmap', 'aiintai')}
    return dict(CHECKS=CHECKS)


def engine_ailastexp():
    """TimeSinceLastExpansionHeuristic.Time: retail 60s / 240s, constant control.

    Pre-run predictions are retained in the expectations. Only initial, no-expansion
    timing is observed; reset after expansion and exact-frame equality remain gaps.
    The check reads the mission's published units, roles and site, with no content
    imports. See work/re/c_lastexp_report.md for source scope and raw readings.

    Measured one run PASS: s19-s62 home=4/4/0, s64-s242=0/4/0,
    s244-s345=0/0/0. All twelve predeclared windows pass. Sampling does not
    establish the exact activation frame or reset after a real expansion.
    """
    from parts import Script, Test, counted, square


    def a(m):
        t = Test()
        t.areas['LastExp home'] = square(*m.site('east base'), 450)
        t.scripts.append(Script('LastExp keep target', [],
            [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
        for i, (unit, label) in enumerate(zip(m.cnv_units, ('六十在家', '二四零家', '常量在家'))):
            counted(f'LastExp_home{i}', label, t, template=unit,
                    player=m.player('s1'), area='LastExp home')
        for second, values in ((40, (4, 4, 0)), (100, (0, 4, 0)),
                               (220, (0, 4, 0)), (275, (0, 0, 0))):
            for label, value in zip(('六十在家', '二四零家', '常量在家'), values):
                t.expect.append((label, second, '==', value, second + 10))
        t.bench = [('bench_watch', dict(seconds=290, every=2, sheet=False, lines=3))]
        return t


    def x(m):
        """B 11-22 (ailastx200 / ailastx50): the Time=150s gate's two cannons on their spots (their team goes for the
        player's yard across the river; the simulator's stop ~270 on to shell the healed plant at the gate) and the AI's
        outposts; aiexpb's heals kept (its escorts shoot the player's base)."""
        t = Test()
        s1 = m.player('s1')
        t.areas['LastExp home'] = square(*m.site('east base', 150.0, -110.0), 100.0)
        counted('LastExp_outpost', '前哨', t, template=m.facts['outpost'], player=s1)
        counted('LastExp_cannons', '炮在家', t, template=m.facts['cannon'], player=s1, area='LastExp home')
        t.scripts.append(Script('LastExp keep targets', [], [('UNIT_SET_HEALTH', m.role(r).name, 100.0)
                                                              for r in ('plant', 'barracks', 'tank', 'player yard')],
                                once=False))
        t.expect += [('炮在家', 120, '==', 2, 140)]
        t.bench = [('bench_watch', dict(seconds=300, every=2, sheet=False, lines=3))]
        return t


    CHECKS = {'ailastexp': {'a': a}, 'ailastx200': {'x': x}, 'ailastx50': {'x': x}, 'ailastxe': {'x': x}}
    return dict(CHECKS=CHECKS)


def engine_ainodesfull():
    """B208: AllNearbyNodesFullHeuristic -- the Peacekeepers (CNVNodesFull) and Guardians (control) at home.

    Prediction (benches/ai/production/scenes.py#ainodesfull_bench; B210: a node is full at 3 own collectors, the refinery's own included):
    Guardians leave on every build; Peacekeepers leave only on ainf3 (two refineries, three collectors each).
    aiopn*: the Peacekeepers (CNVNodesFull with OpenNodeHeuristic) leave only on aiopn1900 (the farthest node 2074 from
    an enemy object).
    """
    from parts import Script, Test, counted, square

    LABELS = ('满态在家', '常量在家')


    def a(m):
        t = Test()
        t.areas['NodesFull home'] = square(*m.site('east base'), 450)
        t.scripts.append(Script('NodesFull keep target', [],
                                [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
        for i, (unit, label) in enumerate(zip(m.cnv_units, LABELS)):
            counted(f'NodesFull_home{i}', label, t, template=unit, player=m.player('s1'), area='NodesFull home')
        # B210: a refinery's node is full at 3 collectors (its own + 2 placed): only ainf3
        full = m.facts.get('ai refineries') == 2 and m.facts.get('ai miners', 0) >= 2
        if m.facts.get('open node') is not None:
            full = m.facts['open node'] < 2074
        # woken at 10 s: on aiopn* both teams leave s15 (bench 11-24), so the at-home window ends at s13
        later = (0 if full else 4, 0)
        if m.facts.get('share'):     # ains*: home (4) iff own / known x 8 players >= the percent, known 2 x (nodes - 1)
            share = 100 * m.facts['ai refineries'] / (2 * (m.facts['ore nodes'] - 1)) * 8
            later = tuple(4 * (share >= p) for p in m.facts['share'])
        if m.facts.get('surface'):   # aicb* as benched 11-27: LAND ~2000..12499 cells, some WATER cell at the east base
            later = {'W': (4, 0), 'M': (4, 4)}.get(m.name[-1], (0, 4))
        windows = ((8, (4, 4), 13), (60, later, 70), (110, later, 120))
        if m.facts.get('income'):    # aiinc*: woken at 100 s, own / enemy ~1 (a refinery each) or 0; home iff not passed
            above, values, kill = m.facts['income']
            ratio = 1.0 if m.facts['ai refineries'] else 0.0
            home = tuple(4 * ((ratio > v) != (above == 'true')) for v in values)
            windows = ((8, (4, 4), 95), (110, home, 120), (170, home, 180))
            if kill is not None:     # the player's deposits all leave the window by kill + 90 s: enemy 0 -> 9999
                windows += ((kill + 110, tuple(4 * (above != 'true') for _ in values), kill + 120),)
        for second, values, until in windows:
            for label, value in zip(LABELS, values):
                t.expect.append((label, second, '==', value, until))
        t.bench = [('bench_watch', dict(seconds=windows[-1][2] + 5, every=2, sheet=False, lines=3))]
        return t


    CHECKS = {k: {'a': a} for k in ('ainf0', 'ainf1', 'ainf2', 'ainf3', 'ainf4', 'ainf5', 'aiopn1900', 'aiopn2250',
                                    'ains1', 'ains2', 'ains2l', 'ains2a', 'ains2b', 'ains2c', 'ains2d', 'ains2n',
                                    'aiinca', 'aiincb', 'aiincc', 'aicbl', 'aicbw', 'aicbn', 'aicbm')}
    return dict(CHECKS=CHECKS)


def engine_aiomove():
    """Engine probe: which opening is drawn, and OpeningMoveHeuristic (benches/ai/production/scenes.py#aiomove_bench).

      a  电厂 / 兵营   power plants / barracks s1 owns, once a second
         坦克在家     (aiohc*) Guardians of s1 inside the base area (450 around the east base)

    Expected (the model, private ai/opening.py choose: the lines of the difficulty, drawn by Weight; ai/states.py
    OpeningMoveHeuristic: Complete == the opening done): the mission's plants / barracks at s40; aiohc* all Guardians
    home at 'home until', fewer by 'out by'.

    读数
    Bench 2026-11-09 (B round 83, one run each):
      aiowt / aiowt2 / aiodf / aiodf2 FAIL: 电厂 0 兵营 0 to s80 -- nothing built at all (two OpeningMove lines, each one
        Build order, no Time). Not found why: aiotime / aiohc* (one line, the 5-order opening) build. Next: one line of
        CNVOpenP alone; then two lines both 100%; then a Time order after the Build.
      aiohc1 (Complete true): 坦克在家 4 to s42, 2 @ s43, 0 from s44; 电厂 1 s19, 2 s49 -- the opening counts as done
        at s40 (wake + Time 30s: the orders after it are builds and Time points already passed), not when the last
        plant stands (s59). simai gives the same (out s44-45). Expectation set to the reading afterwards.
      aiohc0 (Complete false): PASS, out s14-15.
    Bench 2026-11-09 (B round 84, narrowing aiowt*'s nothing; one run each, 电厂 兵营):
      aiom1  one line, opening = Build plant:                0 0 to s80 -- nothing
      aiom2  two lines P / B both 100%:                      0 0 to s80 -- nothing
      aiom3  T 100% + B 0%:                                  PASS (plants s19 / s49 / s59 as aiotime): a 0% line is harmless
      aiom4  one line, Build barracks then Time 5s:          0 0 to s81 -- nothing
      aiom5  one line, Build plant, Build plant (no Time):   1 plant from s19, never a second
    Not found why: one Build -> none, two Builds -> one, T (plant / Time / plant / Time / plant) -> all three.
    Bench 2026-11-09 (B round 85, one run each, 电厂 兵营):
      aiom6  P P P:              1 0 (s19) -- one of three
      aiom7  P, Time 5s:         0 0 -- a trailing Time does not save the lone Build
      aiom8  Time 5s, P:         0 0 -- nor does issuing it after the wake frame
      aiom9  B, P:               1 0 -- the LAST Build of the batch is the one built
      aiom10 P, B:               0 1 -- the same the other way round (so the barracks is buildable: aiom4 is not that)
    Read: several Builds issued in one go -> only the last is built; a Build alone in its batch (aiom1 / 4 / 7 / 8) ->
    nothing; yet T's first plant (alone at the wake, 30 s before the next order) is built, and its two at s40 both are.
    Guesses not tried: the build orders share one slot and a newer one replaces an unstarted older one (but then the
    lone one should stand); the opening's done-ness or how long before the next order matters (P + Time 30s untried).
    Round 86: aiom11 (P, Time 30s), aiom12 (P, Time 15s), aiom13 (P, P, Time 30s), aiom14 (Time 30s, P) written; the
    first run (17:22) all ERROR -- the game's DirectX error box at start (another game, gamemd, held the screen), not read.
    Guess they test: the plant takes ~9 s; a lone Build survives only if the opening is not over before it stands.
    Bench 2026-11-09 (B round 88, run_queue --jobs 2, the bench free again; counters 电厂 兵营, wake s10):
      aiom11 (P, Time 30s) PASS: plant s19.   aiom12 (P, Time 15s) PASS: plant s19.   (aiom7, P + Time 5s: none)
      aiom13 (P, P, Time 30s) PASS: plants s19 and s29 -- both, where P, P with no Time (aiom5) gave one.
      aiom14 (Time 30s, P) FAIL by timing only: the plant stands at s49 (ordered at s40, the opening's last order) --
        where Time 5s, P (aiom8) gave none.
      aiom15 (P, P, Time 30s Account PRODUCTION Deposit 2000) PASS: plants s23 and s33 -- both, 4 s later than aiom13.
      aiom16 (one P, the money given before SKIRMISH_AI_MAKE_BASE) FAIL: nothing, as aiom1 -- not the money at the wake.
    Not settled; what the eight lone-Build readings fit: a Build stands if a Time >= 15 s follows it, or if it is
    issued >= 30 s after the wake; a Build alone in the first seconds with the opening ending within ~5 s is dropped.
    Bench 2026-11-09 (B round 89): the whole opening's end decides, not each Build's own wait --
      aiom17 (B, Time 3s, P, Time 30s) PASS: barracks s19, plant s29 -- both (the barracks' own wait is 3 s).
      aiom18 (B, P, Time 5s) PASS: plant s19, no barracks -- the last Build, begun at the wake.
      aiom19 (P, P, Time 8s) one plant s19 (guessed 2; the expectation is the bench's now).
      aiom20 (P, Time 10s) PASS: plant s19.
    Rule fitted to aiom1-20, aiotime T and aiopen AlliedStandard (private ai/opening.py kept_orders, mechanism not
    read): the last Time point >= X s after the wake (8 < X <= 10; the model takes 10) keeps every order; a shorter
    opening keeps only its last Build, worked as if alone, and none when it has one Build.
    Bench 2026-11-09 (B round 90, the two lines now Build + Time 30s, CNVOpenPT30 / CNVOpenBT30; all PASS):
      aiowt  (P 0%, B 100%): barracks s19, no plant.     aiowt2 (P 100%, B 0%): plant s20, no barracks.
      aiodf  (P EASY, B MEDIUM HARD BRUTAL): barracks s19.  aiodf2 (P MEDIUM HARD BRUTAL, B EASY): plant s19.
    Read: a 0% line is never drawn, either order (not "the first / last line"); lines are kept by Difficulty and the
    bench plays MEDIUM (as aidiff). The round-83 nothing was the lone-Build rule, not the draw.
    """
    from parts import Script, Test, counted, square

    AREA = 'CNV AI Base Area'
    LAG = 4.0
    AT, SECONDS = 40.0, 75.0


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_OM_Plants', '电厂', t, template='AlliedPowerPlant', player=s1)
        counted('CNV_OM_Barracks', '兵营', t, template='AlliedBarracks', player=s1)
        t.expect += [('电厂', AT, '==', m.facts['plants'], AT + 1), ('兵营', AT, '==', m.facts['barracks'], AT + 1)]
        if 'ai tanks' in m.facts:
            t.areas[AREA] = square(*m.site('east base'), 450.0)
            tank, = m.cnv_units
            counted('CNV_OM_Home', '坦克在家', t, template=tank, area=AREA, player=s1)
            n = m.facts['ai tanks']
            if 'home until' in m.facts:
                hu = m.facts['home until']
                t.expect += [('坦克在家', hu, '==', n, hu + 1)]
            by = m.facts['out by']
            t.expect += [('坦克在家', by, '<', n, by + 1)]
        t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a} for k in ('aiowt', 'aiowt2', 'aiodf', 'aiodf2', 'aiohc1', 'aiohc0',
                                      'aiom1', 'aiom2', 'aiom3', 'aiom4', 'aiom5',
                                      'aiom6', 'aiom7', 'aiom8', 'aiom9', 'aiom10',
                                      'aiom11', 'aiom12', 'aiom13', 'aiom14', 'aiom15', 'aiom16',
                                      'aiom17', 'aiom18', 'aiom19', 'aiom20')}
    return dict(CHECKS=CHECKS)


def engine_aiopath():
    """Engine probe: the opening a PathToTargetHeuristic picks (benches/ai/production/scenes.py#aiopath_bench). s1 (Allied, woken at 10 s,
    50000 money) has two openings only, AlliedStandard (PathExists true: barracks, then power plant at +10 s) and
    AlliedIsland (PathExists false: power plant, refinery x2, power plant, naval yard; no barracks), both tested with the
    mission's ObjectTypeToUseForTest. Counted once a second for 90 s after the wake: 兵营 电厂 精炼厂 船坞 (s1's own).

      p  aiopath1 (AlliedPowerPlant tests: no locomotor = no path)  -> Island: a power plant by wake+15, never a barracks
      s  aiopath0 (SovietAntiInfantryInfantry, the stock tester)    -> Standard: a barracks by wake+15, no power plant yet
      p  aiopathi (one line, Island with PathExists true)           -> the probe's personality takes at all
      p  aiopathr (aiopath1, Island listed first)                   -> both lines held? then the first (Island) is drawn

    读数
    Bench 2026-11-09 (one run each, 105 frames s1-s105; counters 兵营 电厂 精炼厂 船坞; mods CampAIPath1P / IP / RP):
      aiopath1  兵营 s19, 电厂 s29, 精炼厂 s49 / s69, 电厂2 s79, 船坞 never   FAIL: the Standard opening (= engine_aiopen a)
      aiopathi  电厂 s19, 精炼厂 s39 / s59, 电厂2 s69, 船坞 s89, 兵营 never     PASS: the Island list, the personality takes
      aiopathr  兵营 s19, 电厂 s29, ... the same as aiopath1                   FAIL: Standard again, though listed second
    So with a tester that has no locomotor the heuristic says "a way": PathExists="true" holds, "false" fails (not
    "both hold, the first is drawn"). The program read (work/re l4_states.md 3, "no locomotor -> no way") is wrong or
    misread. aiopath0 not run (the infantry tester on land is aiopen's own opening). A true "no way" (an island map)
    not measured. Simulator: simai.Brain.path_to_target no locomotor -> True; its .readings.toml holds the three.
    """
    from parts import Script, Test, counted

    LAG = 4.0
    AFTER = 90.0


    def _run(m, island):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        for c, lab, tpl in (('CNV_AP_Barracks', '兵营', 'AlliedBarracks'), ('CNV_AP_Power', '电厂', 'AlliedPowerPlant'),
                            ('CNV_AP_Refinery', '精炼厂', 'AlliedRefinery'), ('CNV_AP_Naval', '船坞', 'AlliedNavalYard')):
            counted(c, lab, t, template=tpl, player=s1)
        w = m.facts['wake at']
        if island:
            t.expect += [('电厂', w + LAG, 'ever>=', 1, w + 15.0), ('兵营', 2, '==', 0, w + AFTER)]
        else:
            t.expect += [('兵营', w + LAG, 'ever>=', 1, w + 15.0), ('电厂', 2, '==', 0, w + 15.0)]
        t.bench = [('bench_watch', dict(seconds=w + AFTER + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'aiopath1': {'p': lambda m: _run(m, True)}, 'aiopath0': {'s': lambda m: _run(m, False)},
              'aiopathi': {'p': lambda m: _run(m, True)}, 'aiopathr': {'p': lambda m: _run(m, True)}}
    return dict(CHECKS=CHECKS)


def engine_aiopathcond():
    """E84: PathToTargetHeuristic.LocomotorConditionToUseForTest, same JapanAntiAirShip.

    SDK JapanAntiAirShip NORMAL names a DEEP_WATER locomotor; SUPERSONIC names AIR.
    Niagara's two construction yards are on land. Prediction before running:
    aiopwater chooses Island (power plant first, no barracks); aiopair chooses
    Standard (barracks first). Only the condition differs in the heuristic input.
    Count the opening's actual buildings, not an internal path score.
    Bench 2026-11-12: aiopwater FAIL, aiopair PASS; both have barracks=1,
    power=0 at s22-s24. The failed water prediction below is retained. These
    equal readings do not establish that the condition selects a locomotor.
    benches/ai/production/readings.toml#engine_aiopathcond holds the observed counts, not that prediction.
    Evidence and any mismatch: work/re/e_pathcond_e84.md.
    """
    from parts import Script, Test, counted


    def opening(m, island):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        for counter, label, template in (
                ('CNV_PC_Barracks', '兵营', 'AlliedBarracks'),
                ('CNV_PC_Power', '电厂', 'AlliedPowerPlant')):
            counted(counter, label, t, template=template, player=m.player('s1'))
        wake = m.facts['wake at']
        t.expect += [('兵营', wake + 12, '==', 0 if island else 1, wake + 15),
                     ('电厂', wake + 12, '==', 1 if island else 0, wake + 15)]
        t.bench = [('bench_watch', dict(seconds=wake + 20, every=1, sheet=False, lines=2))]
        return t


    CHECKS = {'aiopwater': {'a': lambda m: opening(m, True)},
              'aiopair': {'a': lambda m: opening(m, False)}}
    return dict(CHECKS=CHECKS)


def engine_aiopen():
    """Engine probe: the skirmish AI's opening (benches/ai/production/scenes.py#aiopen_bench) -- when each structure / unit first appears
    for the enemy (s1, AlliedBalanced, woken at 10 s with 50000 money), counted once a second for 150 s after waking.

      a  兵营 / 电厂 / 精炼厂 / 战车工厂   AlliedBarracks, AlliedPowerPlant, AlliedRefinery, AlliedWarFactory
      b  反步兵车 / 激流 / 资金 / 采矿车   AlliedAntiInfantryVehicle, AlliedAntiInfantryVehicle_Ground, money, AlliedMiner
      c  船坞                           AlliedNavalYard

    Four lines a check (the counter display). Counts are the player's own, capped at 8. The expectation is loose; the
    point is the reading.

    读数
    Bench 2026-11-06 (one run each; bench seconds, the money first moves at s9 = the wake, so after-wake = s - 9):
      a CampAIOpenA: 兵营 0->1 @ s19 (wake+10); 电厂 0->1 @ s29 (+20), ->2 @ s79, ->3 @ s137, ->4 @ s147;
        精炼厂 0->1 @ s49 (+40), ->2 @ s69 (+60); 战车工厂 0->1 @ s99 (+90), stays 1.
      b CampAIOpenB: 资金 50000 at the wake, 49966 s9, 49371 s20, 45006 s52, ~42300 s77-80, ~40700 s111, 33397 s167
        (spending is slow and steady, no big single drops; income from the miners flattens it now and then);
        采矿车 0->1 @ s53 (+44), ->2 @ s73 (+64); 反步兵车 and 激流 (_Ground, same unit counted by both templates)
        0->1 @ s111 (+102), ->2 @ s123, ->3 @ s131, ->4 @ s142, ->5 @ s153.
      c CampAIOpenC: 船坞 stays 0 all 167 s.
      (b again in round 11: the same seconds. But its Riptides 2 -> 3 in 8 s cannot be: one factory, 10 s a build. The
      watch's seconds drift from the game's; the frame checks below are the authority.)

      f1 / f2 / f3 (frames from the wake, round 11; f2 run twice, the same): 兵营 152, 电厂1 305, 精炼厂1 607,
        精炼厂2 909, 电厂2 1062, 战车工厂 1364, 激流1 1555, 激流2 1716, 激流3 1877; 采矿车1 667 (= refinery + 60: its
        UnpackTime 4 s), 电厂3 1960 (past the opening). 放下 (any UNDER_CONSTRUCTION) never stopped: 2450, i.e. the AI's
        Allied structures were never seen under construction by that condition (op 0 '<' not proven for it; not chased).
        So: a structure is owned 1 frame after its head is full, the yard starts the next the frame after; the war
        factory makes nothing till unpacked (UnpackTime 2 s = 30 frames); a unit leaves the door 10 frames after its head
        is full and the next starts then (161 frames each). The opening's frame-10 lottery adds nothing here.
      m CampAIPoorM (aiopenpoor, 3000 at the wake): 2963 at s9, 兵营 s19, 电厂 s29, money 23 at s37 and 0 s38-s125 --
        the refinery is never finished (精炼厂 0 all run) and nothing after it starts: the opening stalls in order on the
        order it cannot pay, the 2000 Deposit into PRODUCTION buys nothing. s126 money jumps to 1000 and is spent
        (106 at s135), s136 +200 to 250, s138 兵营 1 -> 0 (sold?), money 3 from s139 to the end. Read 11-26
        (aiopenpoort): the no-income emergency -- it cancels the stalled builds (the refund), then sells to make 100.
    """
    from parts import Script, Test, counted, status

    LAG = 4.0
    SECONDS = 160.0                      # wake 10 s + 150 s


    def _base(m):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        return t, m.player('s1')


    def _finish(t, m):
        w = m.facts['wake at']
        t.expect += [('兵营', 1, 'ever>=', 1, w + 150.0)] if any(c[1] == '兵营' for c in t.counters) else []
        t.bench = [('bench_watch', dict(seconds=w + 150.0 + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def a(m):
        t, s1 = _base(m)
        for c, lab, tpl in (('CNV_AO_Barracks', '兵营', 'AlliedBarracks'), ('CNV_AO_Power', '电厂', 'AlliedPowerPlant'),
                            ('CNV_AO_Refinery', '精炼厂', 'AlliedRefinery'), ('CNV_AO_Factory', '战车工厂', 'AlliedWarFactory')):
            counted(c, lab, t, template=tpl, player=s1)
        return _finish(t, m)


    def b(m):
        t, s1 = _base(m)
        counted('CNV_AO_AIV', '反步兵车', t, template='AlliedAntiInfantryVehicle', player=s1)
        counted('CNV_AO_AIVG', '激流', t, template='AlliedAntiInfantryVehicle_Ground', player=s1)
        t.counters.append(('CNV_AO_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AO_Money')], once=False))
        counted('CNV_AO_Miner', '采矿车', t, template='AlliedMiner', player=s1)
        w = m.facts['wake at']
        t.expect += [('资金', w + LAG, 'ever>', 0, w + 30)]
        t.bench = [('bench_watch', dict(seconds=w + 150.0 + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def c(m):
        t, s1 = _base(m)
        counted('CNV_AO_Naval', '船坞', t, template='AlliedNavalYard', player=s1)
        return _finish(t, m)


    #: frame checks: counter, label, template (None = any object of s1 UNDER_CONSTRUCTION), the how-many-th one
    FRAMES = {
        'f1': (('CNV_AO_F_Placed', '放下', None, 1), ('CNV_AO_F_Barracks', '兵营', 'AlliedBarracks', 1),
               ('CNV_AO_F_Power1', '电厂1', 'AlliedPowerPlant', 1), ('CNV_AO_F_Ref1', '精炼厂1', 'AlliedRefinery', 1)),
        'f2': (('CNV_AO_F_Ref2', '精炼厂2', 'AlliedRefinery', 2), ('CNV_AO_F_Power2', '电厂2', 'AlliedPowerPlant', 2),
               ('CNV_AO_F_Factory', '战车工厂', 'AlliedWarFactory', 1),
               ('CNV_AO_F_AIV1', '激流1', 'AlliedAntiInfantryVehicle_Ground', 1)),
        'f3': (('CNV_AO_F_AIV2', '激流2', 'AlliedAntiInfantryVehicle_Ground', 2),
               ('CNV_AO_F_AIV3', '激流3', 'AlliedAntiInfantryVehicle_Ground', 3),
               ('CNV_AO_F_Miner1', '采矿车1', 'AlliedMiner', 1), ('CNV_AO_F_Power3', '电厂3', 'AlliedPowerPlant', 3)),
    }


    def frames(m, which):
        """Exact frames instead of the 1 s samples: every counter counts the frames from the wake (the wake timer has
        expired, and at least 30 frames in so an unset timer cannot count) while s1 owns fewer than n of its template --
        so its last value is the frame the n-th one first counts (one that never comes counts the whole run). Read once
        at the end; the frame of the wake itself is +-1 (the mission's wake script and the flag run in the same frame)."""
        t, s1 = _base(m)
        t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AO_Tick')], once=False),
                      Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AO_Tick', 3, 30)],
                             [('SET_FLAG', 'Test Woke', 1)])]
        owned = {}
        for counter, label, tpl, n in FRAMES[which]:
            t.counters.append((counter, label))
            if tpl is None:
                have = ('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', s1, 0, n, status('UNDER_CONSTRUCTION'))
            else:
                if tpl not in owned:
                    owned[tpl] = f'CNV_AO_Own{len(owned)}'
                    t.scripts.append(Script(f'Test - own {tpl}', [],
                                            [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, s1, owned[tpl])], once=False))
                have = ('COUNTER', owned[tpl], 0, n)
            t.scripts.append(Script(f'Test - wait {counter}', [('FLAG', 'Test Woke', 1), have],
                                    [('INCREMENT_COUNTER', 1, counter)], once=False))
        w = m.facts['wake at']
        t.expect += [(FRAMES[which][0][1], w + LAG, 'ever>=', 1, w + 150.0)]
        t.bench = [('bench_watch', dict(seconds=w + 150.0 + LAG, every=10, sheet=False, lines=len(t.counters)))]
        return t


    def poor(m):
        """aiopenpoor (3000 at the wake): what the opening builds when the money runs out, once a second."""
        t, s1 = _base(m)
        for c, lab, tpl in (('CNV_AO_Barracks', '兵营', 'AlliedBarracks'), ('CNV_AO_Power', '电厂', 'AlliedPowerPlant'),
                            ('CNV_AO_Refinery', '精炼厂', 'AlliedRefinery')):
            counted(c, lab, t, template=tpl, player=s1)
        t.counters.append(('CNV_AO_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AO_Money')], once=False))
        w = m.facts['wake at']
        t.expect += [('资金', w + LAG, 'ever>', 0, w + 30)]
        t.bench = [('bench_watch', dict(seconds=w + 150.0 + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def mcv(m):
        """aiopenmcv* (no yard, a war factory, 50000): what the no-conyard emergency orders, once a second."""
        t, s1 = _base(m)
        for c, lab, tpl in (('CNV_AO_Yard', '建造厂', 'AlliedConstructionYard'), ('CNV_AO_MCV', '基地车', 'AlliedMCV'),
                            ('CNV_AO_Miner', '采矿车', 'AlliedMiner')):
            counted(c, lab, t, template=tpl, player=s1)
        t.counters.append(('CNV_AO_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AO_Money')], once=False))
        w = m.facts['wake at']
        t.expect += [('资金', w + LAG, 'ever>', 0, w + 30)]
        t.bench = [('bench_watch', dict(seconds=w + 190.0 + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'aiopen': {'a': a, 'b': b, 'c': c, **{k: (lambda m, k=k: frames(m, k)) for k in FRAMES}},
              'aiopenpoor': {'m': poor}, 'aiopenpoort': {'m': poor}, 'aiopenpoortp': {'m': poor},
              'aiopenmcv': {'v': mcv}, 'aiopenmcvm': {'v': mcv}}
    return dict(CHECKS=CHECKS)


def engine_aiopenside():
    """SkirmishOpeningMove.Side: explicit opening on a fixed Allied player.

    Only the opening's Side changes Allies/Soviet. Three consecutive power-plant
    orders make its execution visible independently of infantry production.
    Pre-bench default model prediction: at s55 three plants, zero barracks in
    both builds. E82 bench: Allies PASS (3/0), Soviet FAIL (2/1), [s55,s60).
    The original failed prediction stays here; the replay uses engine readings,
    with strict xfail for Soviet. Side selection/fallback remains a model gap.
    Evidence: work/re/e_openside_e82.md.
    """
    from parts import Script, Test, counted


    def a(m):
        t = Test()
        t.scripts.append(Script('Side reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        for key, label, template in (('Power', '电厂数', 'AlliedPowerPlant'),
                                     ('Barracks', '兵营数', 'AlliedBarracks')):
            m.spawns.add(template)
            counted('Side' + key, label, t, template=template, player=m.player('s1'))
        t.expect = [('电厂数', 55, '==', 3, 60), ('兵营数', 55, '==', 0, 60)]
        t.bench = [('bench_watch', dict(seconds=64, every=1, sheet=False, lines=2))]
        return t


    CHECKS = {name: {'a': a} for name in ('aiosallies', 'aiossoviet')}
    return dict(CHECKS=CHECKS)


def engine_aiotime():
    """Engine probe: an opening's Time order (benches/ai/production/scenes.py#aiotime_bench) -- power plant / Time 30s / power plant / Time 20s
    / power plant: when do the three stand?

      a  电厂   power plants s1 owns, once a second

    Expected (the model: Time counts from the wake, mission s10): 1 at s45, 2 at s55, 3 at s65 (since the previous Time:
    2 at s65; since the mission start: 2 at s45).

    读数
    Bench 2026-11-09 (B round 79, one run, PASS 3 of 3): 电厂 0 to s18, 1 s19-s48, 2 s49-s58, 3 from s59 -- Time counts
    from the wake (the opening's start); a Time point already passed holds nothing up. The simulator has the gaps
    (30 s, 10 s) but every plant 3 s late (benches/ai/production/readings.toml#engine_aiotime, the absolute times a mismatch mark).
    """
    from parts import Test, counted, Script

    LAG = 4.0
    SECONDS = 75.0


    def a(m):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_OT_Plants', '电厂', t, template='AlliedPowerPlant', player=m.player('s1'))
        t.expect += [('电厂', 45.0, '==', 1, 46.0), ('电厂', 55.0, '==', 2, 56.0), ('电厂', 65.0, '==', 3, 66.0)]
        t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'aiotime': {'a': a}}
    return dict(CHECKS=CHECKS)


@cache
def engine_aipathbanks():
    """C: condition selection between physically disconnected river banks.

    Before running: land control stays off the far bank, amphibious control arrives.
    Opening prediction at s22-24: NORMAL power=1/barracks=0, SUPERSONIC power=0/
    barracks=1. Physical controls are independent of the opening heuristic. Equal
    opening readings leave condition/endpoint/path-result semantics unresolved;
    see work/re/c_pathbanks_report.md. No coverage promotion without a split.
    Bench 2026-11-13: both builds give barracks/power=1/0 at s22-24;
    both physical counters are 1 (alive, not arrived) at s40-44. Both checks
    FAIL their pre-run hypotheses. The amphibious positive control is unproven.
    The early-registration follow-up aipclandy also yields 1/0 and 1/1: its
    opening still returns before bases are available. See work/re/c_pathready_report.md.
    """
    from parts import Script, Test, counted, square


    def check(m):
        t = Test()
        orders = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for role in ('land control', 'amphib control'):
            orders += m.order('move', [m.role(role).name], m.mark('crossing goal'))
        t.scripts.append(Script('Test - crossing', [], orders))
        area = 'CNV PC Arrival'
        t.areas[area] = square(*m.point('crossing goal'), 160)
        for counter, label, template in (
                ('CNV_PC_Barracks', '兵营', 'AlliedBarracks'),
                ('CNV_PC_Power', '电厂', 'AlliedPowerPlant')):
            counted(counter, label, t, template=template, player=m.player('s1'))
        # Pack survival (1) and arrival (10) into one line per control.
        for counter, label, role in (
                ('CNV_PC_Land', '陆路', 'land control'),
                ('CNV_PC_Amph', '两栖', 'amphib control')):
            name = m.role(role).name
            t.counters.append((counter, label))
            t.scripts += [
                Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                Script(f'Test - {counter} alive', [('NAMED_NOT_DESTROYED', name)],
                       [('INCREMENT_COUNTER', 1, counter)], once=False),
                Script(f'Test - {counter} arrived', [('NAMED_INSIDE_AREA', name, area)],
                       [('INCREMENT_COUNTER', 10, counter)], once=False)]
        amphib = m.facts['path amphibious']
        t.expect = [('兵营', 22, '==', int(amphib), 25),
                    ('电厂', 22, '==', int(not amphib), 25),
                    ('陆路', 40, '==', 1, 45), ('两栖', 40, '==', 11, 45)]
        t.bench = [('bench_watch', dict(seconds=46, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': check} for name in ('aipcland', 'aipcamph', 'aipclandy', 'aipcamphy', 'aipclandt', 'aipcampht')}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(check=check))


def engine_aipathx():
    """Engine line D round 108: benches/ai/production/checks.py#engine_aipathbanks's check on the ra3ext builds (benches/ai/production/scenes.py#aipathx_bench).

    The expectations are C's pre-registered ones (they FAILed on 2026-11-13); this build is for the `ptt:` lines in
    the run's ra3ext.log, read in work/re (handoff-c.md PathToTarget).
    """
    check = engine_aipathbanks()["shared"].check

    CHECKS = {name: {'a': check} for name in ('aipclandx', 'aipcamphx')}
    return dict(CHECKS=CHECKS)


def engine_aiplacement():
    """C unpack placement: raw core, total plant, local plant and host counts.

    Predictions remain hypotheses until the named bench runs have been read.
    See work/re/c_placement_report.md for evidence and unresolved eligibility.
    """
    from parts import Test, counted, square


    def a(m):
        t = Test()
        s1 = m.player('s1')
        core = m.find(m.role('core').name)
        t.areas['CNV Placement Local'] = square(core.x, core.y, 250)
        for key, label, template, area in (
            ('Core', '核心', 'JapanPowerPlantEgg', None),
            ('Plant', '电厂', 'JapanPowerPlant', None),
            ('Local', '近处电厂', 'JapanPowerPlant', 'CNV Placement Local'),
            ('Host', '宿主', 'CNVTeamsHost', None),
        ):
            counted('CNV_Placement_' + key, label, t, template=template, player=s1, area=area)
        plant = int(m.facts['placement distance'] == 200)
        t.expect += [('核心', 35, '==', 1 - plant, 40), ('电厂', 35, '==', plant, 40),
                     ('近处电厂', 35, '==', plant, 40), ('宿主', 35, '==', 1, 40)]
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
        return t


    def b(m):
        """aiplb*: the AI's own core; the plant counted in squares round the yard (half-sides 450 / 1000). No total plant
        count: the type-ownership counter never counted the unpacked plant (bench 11-24: 0 while both squares read 1)."""
        t = Test()
        s1 = m.player('s1')
        yard = m.find(m.role('ai yard').name)
        for key, label, template, half in (('Core', '核心', 'JapanPowerPlantEgg', 0), ('Near', '近450', 'JapanPowerPlant', 450),
                                           ('Mid', '近1000', 'JapanPowerPlant', 1000)):
            area = f'CNV PlB {key}' if half else None
            if area:
                t.areas[area] = square(yard.x, yard.y, half)
            counted('CNV_PlB_' + key, label, t, template=template, player=s1, area=area)
        near = int(m.facts['placement distance'] < 1000)
        t.expect += [('核心', 55, '==', 0, 60), ('近450', 55, '==', near, 60), ('近1000', 55, '==', 1, 60)]
        t.bench = [('bench_watch', dict(seconds=60, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {key: {'a': a} for key in ('aiplace1', 'aiplace200', 'aiplacej200')}
    CHECKS |= {key: {'b': b} for key in ('aiplb600', 'aiplb1500')}
    return dict(CHECKS=CHECKS)


def engine_aipower():
    """Engine probe: the protocol a computer player buys (benches/ai/production/scenes.py#aipower_bench; simtech.Book.ai_buy). The enemy s1
    (Soviet, one starting point, AI not woken) with a personality of the probe's (its <PowerChoice PlayerPower Weight>
    lines); X = PlayerTech_Soviet_MagneticSatellite_
    Rank_1, Y = PlayerTech_Soviet_OrbitalRefuse_Rank1 (both 1 point, only PlayerTech_Soviet needed). Counters: 有X, 有Y
    (PLAYER_HAS_PLAYER_TECH of s1), 点数 (s1's protocol points, every frame). The model (program read) in brackets:
      aipwra  one PowerChoice X                      [X bought, 点数 1 -> 0 from frame 10]
      aipwrb  Y Weight 0% then X Weight 100%         [X bought, never Y]
      aipwrd  stock DefaultPersonality, no PowerChoice  [nothing bought, 点数 stays 1]
      aipwre  X 50% then Y 50%  /  aipwrf  Y 50% then X 50%   [check e: only 点数 == 0 from s8, no pick expected]
      aipwrg  X 30% then Y 70%  /  aipwrh  X 10% then Y 90%   [check e: where the draw falls]

    读数
    Bench 2026-11-09 (one run each, 76 frames s0.7-s75.7; counters 有X, 有Y, 点数; mods CampAIPwrAA / BA / DA):
      aipwra  s1-s76: 1 0 0   PASS (X bought by s1 -- the first reading -- and the point gone)
      aipwrb  s1-s76: 1 0 0   PASS (X bought, never Y, though Y is listed first at 0%)
      aipwrd  s1-s76: 0 0 1   PASS (nothing bought, the point kept all 75 s)
    Bench 2026-11-09, check e (16 frames s1.1-s16.1; counters 有X, 有Y, 点数; first reading s1 = final s16; mods CampAIPwrEE / FE):
      aipwre  run 1: 1 0 0   X bought (X listed first)
      aipwre  run 2: 1 0 0   X bought
      aipwre  run 3: 1 0 0   X bought
      aipwre  run 4: 1 0 0   X bought
      aipwrf  run 1: 0 1 0   Y bought (Y listed first)
      aipwrf  run 2: 0 1 0   Y bought
      aipwrf  run 3: 0 1 0   Y bought
    Bench 2026-11-09, check e (mods CampAIPwrGE / HE, one run each, first reading s1 = final s16):
      aipwrg  s1-s16: 1 0 0   X bought (X 30% first, Y 70%)
      aipwrh  s1-s16: 0 1 0   Y bought (X 10% first, Y 90%)
    So the draw is not "the heaviest line": it falls at the same place every run (single-player seed 0, INFERRED from
    Generals), there between 10% and 30% of the sum. simtech.DRAW = 0.2; tests/test_simtech_powerchoice.py holds the seven.
    """
    from parts import Script, Test
    from checks import engine_protocol as ep

    RUN = 75.0


    def _check(m, want_x, want_pts):
        t = Test()
        s1 = m.player('s1')
        ep._sum(t, 'CNV_PW_X', '有X', [(1, ('PLAYER_HAS_PLAYER_TECH', s1, 'PlayerTech_Soviet_MagneticSatellite_Rank_1'))])
        ep._sum(t, 'CNV_PW_Y', '有Y', [(1, ('PLAYER_HAS_PLAYER_TECH', s1, 'PlayerTech_Soviet_OrbitalRefuse_Rank1'))])
        ep._points(t, 'CNV_PW_Pts', '点数', s1)
        t.expect += [('有X', 8, '==', want_x, RUN), ('有Y', 1, '==', 0, RUN), ('点数', 8, '==', want_pts, RUN)]
        ep._watch(t, RUN, 1.0)
        return t


    def a(m):
        return _check(m, 1, 0)


    def d(m):
        return _check(m, 0, 1)


    def e(m):
        """Two equal-weight lines: no expectation on which, only that one point was spent (点数 0 at s8)."""
        t = Test()
        s1 = m.player('s1')
        ep._sum(t, 'CNV_PW_X', '有X', [(1, ('PLAYER_HAS_PLAYER_TECH', s1, 'PlayerTech_Soviet_MagneticSatellite_Rank_1'))])
        ep._sum(t, 'CNV_PW_Y', '有Y', [(1, ('PLAYER_HAS_PLAYER_TECH', s1, 'PlayerTech_Soviet_OrbitalRefuse_Rank1'))])
        ep._points(t, 'CNV_PW_Pts', '点数', s1)
        t.expect += [('点数', 8, '==', 0, 15.0)]
        ep._watch(t, 15.0, 1.0)
        return t


    CHECKS = {'aipwra': {'a': a}, 'aipwrb': {'a': a}, 'aipwrd': {'a': d},
              'aipwre': {'e': e}, 'aipwrf': {'e': e}, 'aipwrg': {'e': e}, 'aipwrh': {'e': e}}
    return dict(CHECKS=CHECKS)


def engine_aipowerabove():
    """C: Above true/false with fixed 4:8 Guardians and Value=1.0.

    Pre-run s40 prediction: true home/total/player=4/4/8, false=0/4/8.
    Measured 2026-11-13, one PASS each: true s1-s46=4/4/8;
    false s1-s13=4/4/8, s14=3/4/8, s15-s46=0/4/8.
    Only published mission sites, roles, units, players and facts are consumed.
    See work/re/c_powerabove_report.md for predictions and engine evidence.
    """
    from parts import Script, Test, counted, square


    def check(m):
        t = Test()
        t.areas['Power above home'] = square(*m.site('east base'), 450)
        t.scripts.append(Script('Power above reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Power above keep target', [],
            [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
        tank, = m.cnv_units
        for key, label, area, player, expected in (
                ('CPA_home', '坦克在家', 'Power above home', 's1', m.facts['home at 40']),
                ('CPA_total', '坦克总数', None, 's1', 4),
                ('CPA_enemy', '玩家坦克', None, 'p1', 8)):
            counted(key, label, t, template=tank, area=area, player=m.player(player))
            t.expect.append((label, 40, '==', expected, 41))
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=3))]
        return t


    CHECKS = {name: {'a': check} for name in ('aipabtrue', 'aipabfalse')}
    return dict(CHECKS=CHECKS)


@cache
def engine_aipoweradv():
    """Engine probe: PowerAdvantageHeuristic switches a strategic state (benches/ai/production/scenes.py#aipoweradv_bench) -- do the AI's
    Guardians leave its base when its army out-kills the player's, and stay when it does not?

      a  坦克在家   Guardians of s1 inside the base area (450 around the east base), once a second
         坦克出门   Guardians of s1 within 300 of the player's power plant ~750 west of them (the state's target)

    Expected (program read, work/re l4_states.md 11; the mission's 'expect on'): on -- 坦克在家 below the AI's count by
    s40 (an always-on state's team leaves ~5 s after the wake, engine_aistate); off -- all still home at s60.

    读数
    Bench 2026-11-09 (B round 77, one run each, PASS 1 of 1 each):
      aipadv1 a (CampAIPAdv1A, 4 against 8): 坦克在家 4 / 坦克出门 0 from s1 to s65 -- off.
      aipadvc a (CampAIPAdvCA, 4 against 8, ConstantHeuristic): 坦克在家 4 -> 3 @ s14, 0 @ s15; 坦克出门 4 s18-s31
        (then 0: the plant dead) -- the control, so aipadv1's stay is the heuristic's.
      aipadv2 a (CampAIPAdv2A, 8 against 4): 坦克在家 8 -> 7 @ s13, 5 @ s14, 1 @ s15, 0 @ s16; 坦克出门 8 s21-s26 -- on.
      aipadvh a (CampAIPAdvHA, 4 against an Ore Collector only): 坦克在家 4 -> 3 @ s15, 0 @ s16; 坦克出门 4 s20-s31 -- on.
    The simulator (simai) gives the same four (benches/ai/production/readings.toml#engine_aipoweradv power_advantage_gates_the_state_as_on_the_bench).
    Bench 2026-11-09 (B round 82, the team's MinPowerAdvantage, the state ConstantHeuristic; one run each):
      aipadm1 (8 v 4, 1.0): 坦克在家 8 -> 0 s13-15; 坦克出门 4 @ s18.
      aipadm0 (4 v 8, 1.0): 坦克在家 4 -> 0 s14-15; 坦克出门 4 s18-31 -- goes (the first guess said stay).
      aipadm5 (8 v 4, 5.0; ratio 4 < 5): 坦克在家 8 -> 0 s13-16; 坦克出门 8 s21-26 -- goes (the guess said stay).
    Read: MinPowerAdvantage holds no team back here (as the model: parsed, not used); what it gates, if anything, not
    found. simai agrees (it ignores the field): benches/ai/production/readings.toml#engine_aipoweradv team_min_power_advantage_holds_nobody_back.
    Bench 2026-11-09 (B round 83, the condition heuristics, 4 Guardians against none; one run each, all PASS):
      aihtim  (Timer 30s, MAP_START):         home 4 to s32, 0 @ s34 -- on after 30 s from the mission start.
      aihtima (Timer 25s AI_START, wake s10): home 4 to s37, 0 @ s39 -- from the wake.
      aihtimx (Timer 20s EndTime 10s):        home 4 to s22, 0 @ s23; out s27-s65 (they stay out after s30).
      aihint  (Interval 25s off, 30s on):     home 4 to s27, 0 @ s28 -- off first, then on.
      aihen1  (EnemyNearby 700 true, the player's Ore Collector ~527 off at the ore node): out s14-16.
      aihen0  (the same, no collector): home 4 to s65.   aihenn (EnemyNearby false, none): out s14-16.
      aihoe1  (ObjectOfTypeExists ENEMIES AlliedMiner, the player has one): out s15-17 -- the model said off.
      aihoe0  (none): home to s65.   aihoef (PassIfExists false, the player has one): home to s65 -- the model said on.
      aihoea  (ALLIES, only the player's): home to s65.   aihoes (ALLIES, s1's own collector): out s15-17 -- ALLIES
              includes oneself.
    Bench 2026-11-25 (B, its Location; ENEMIES, the player's yard on land, its power plant at x 2850 on terrain below
    the water, a Dolphin in the river south of Goat Island; one run each):
      aihol (Land, Rule ALL) out s14-18; aihow (Water, ALL, no Dolphin) out s14-18 -- the plant counts as afloat;
      aihoww (Water, ALL, the Dolphin) out s15-19; aihold (Land, ANY IncludeThing the Dolphin) home to s65.
    Read: Timer / Interval / EnemyNearby as the model; ObjectOfTypeExists counts the filter's Relationship (the model
    looks only at its own templates: benches/ai/production/readings.toml#engine_aipoweradv object_of_type_exists_counts_the_relationship_as_on_the_bench strict xfail).
    """
    from parts import Script, Test, counted, square

    AREA, THERE = 'CNV AI Base Area', 'CNV AI Target Area'
    LAG = 4.0
    ON_BY, SECONDS = 40.0, 60.0


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 450.0)
        goal = m.find(m.role('player target').name)
        t.areas[THERE] = square(goal.x, goal.y, 300.0)
        tank, = m.cnv_units
        counted('CNV_PA_Home', '坦克在家', t, template=tank, area=AREA, player=s1)
        counted('CNV_PA_There', '坦克出门', t, template=tank, area=THERE, player=s1)
        n = m.facts['ai tanks']
        if 'home until' in m.facts:                  # round 83: still all home that second
            hu = m.facts['home until']
            t.expect += [('坦克在家', hu, '==', n, hu + 1)]
        if m.facts['expect on']:
            by = m.facts.get('out by', ON_BY)
            t.expect += [('坦克在家', by, '<', n, by + 1)]
        else:
            t.expect += [('坦克在家', SECONDS, '==', n, SECONDS + 1)]
        t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a} for k in ('aipadv2', 'aipadv1', 'aipadvh', 'aipadvc', 'aipadm1', 'aipadm0', 'aipadm5',
                                     # round 83: the condition heuristics
                                     'aihtim', 'aihtima', 'aihtimx', 'aihint', 'aihen1', 'aihen0', 'aihenn',
                                     'aihoe1', 'aihoe0', 'aihoef', 'aihoea', 'aihoes',
                                     'aihol', 'aihow', 'aihoww', 'aihold')}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a))


def engine_aipowerenemy():
    """C: enemy-defense inclusion, measured s40 0/8/4/1 vs 8/8/4/1.

    Only IncludeEnemyDefenses changes; see work/re/c_powerenemy_report.md.

    Consumes published mission sites, roles, players, units and facts only.
    """
    from parts import Script, Test, counted, square


    def check(m):
        t = Test()
        t.areas['Enemy defense home'] = square(*m.site('east base'), 450)
        t.scripts.append(Script('Enemy defense reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Enemy defense keep target', [],
            [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
        tank, = m.cnv_units
        for key, label, template, area, player, expected in (
                ('CPE_home', '坦克在家', tank, 'Enemy defense home', 's1', m.facts['home at 40']),
                ('CPE_total', '坦克总数', tank, None, 's1', 8),
                ('CPE_enemy', '玩家坦克', tank, None, 'p1', 4),
                ('CPE_tower', '玩家防御塔', m.facts['defense template'], None, 'p1', 1)):
            counted(key, label, t, template=template, area=area, player=m.player(player))
            t.expect.append((label, 40, '==', expected, 41))
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': check} for name in ('aipenoff', 'aipenon')}
    return dict(CHECKS=CHECKS)


def engine_aipowerown():
    """C: own-defense inclusion, measured s40 home/total/enemy/tower=4/4/8/1 vs 0/4/8/1.

    Only IncludeOwnDefenses changes; see work/re/c_powerown_report.md.
    Measured 2026-11-13: off s1-s46=4/4/8/1; on s15-s46=0/4/8/1.
    Consumes published mission sites, roles, players, units and facts.
    """
    from parts import Script, Test, counted, square


    def check(m):
        t = Test()
        t.areas['Own defense home'] = square(*m.site('east base'), 450)
        t.scripts.append(Script('Own defense reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Own defense keep target', [],
            [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
        tank, = m.cnv_units
        for key, label, template, area, player, expected in (
                ('CPO_home', '坦克在家', tank, 'Own defense home', 's1', m.facts['home at 40']),
                ('CPO_total', '坦克总数', tank, None, 's1', 4),
                ('CPO_enemy', '玩家坦克', tank, None, 'p1', 8),
                ('CPO_tower', '己方防御塔', m.facts['defense template'], None, 's1', 1)):
            counted(key, label, t, template=template, area=area, player=m.player(player))
            t.expect.append((label, 40, '==', expected, 41))
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': check} for name in ('aipownoff', 'aipownon')}
    return dict(CHECKS=CHECKS)


def engine_aipowervalue():
    """C: Value=1.0/0.1 with fixed Above=true and 4:8 Guardians.

    Pre-run s40 prediction: 1.0 home/total/player=4/4/8, 0.1=0/4/8.
    Measured 2026-11-13, one PASS each: 1.0 s1-s46=4/4/8;
    0.1 s1-s13=4/4/8, s14=2/4/8, s15-s46=0/4/8.
    Only published sites, roles, units, players and facts are consumed.
    See work/re/c_powervalue_report.md for predictions and engine evidence.
    """
    from parts import Script, Test, counted, square


    def check(m):
        t = Test()
        t.areas['Power value home'] = square(*m.site('east base'), 450)
        t.scripts.append(Script('Power value reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Power value keep target', [],
            [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
        tank, = m.cnv_units
        for key, label, area, player, expected in (
                ('CPV_home', '坦克在家', 'Power value home', 's1', m.facts['home at 40']),
                ('CPV_total', '坦克总数', None, 's1', 4),
                ('CPV_enemy', '玩家坦克', None, 'p1', 8)):
            counted(key, label, t, template=tank, area=area, player=m.player(player))
            t.expect.append((label, 40, '==', expected, 41))
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=3))]
        return t


    CHECKS = {name: {'a': check} for name in ('aipval1', 'aipval01', 'aipval1t')}
    return dict(CHECKS=CHECKS)


def engine_aisimpleexp():
    """D round 154: SimpleExpansion readings (benches/ai/production/scenes.py#aisimpleexp_bench; aiexpse / aiexpd50 / aiexpd400 differ in
    Tactic.Distance only). Counters (four fit): the AI's outposts on the whole map, its outposts and miners within 150 of the Expansion pick
    (bench aiexpc f151: (4173, 2987)), its Guardians in C's 350 square round the east candidate. The exact unpack point
    and frame come from the CNVTeams host's cmd log (ra3ext.log). Expectations: the simulator's prediction (round 154).
    """
    from parts import Test, Script, counted, square


    def a(m):
        t = Test()
        s1 = m.player('s1')
        MINER, OUTPOST = m.facts['miner'], m.facts['outpost']
        tank, = m.cnv_units
        near, east = 'CNV SExp near', 'CNV SExp east'
        t.areas[near] = square(*m.facts['expansion pick'], 150.0)
        t.areas[east] = square(*m.facts['candidate east'], 350.0)
        counted('CNV_SExp_out', '前哨', t, template=OUTPOST, player=s1)
        counted('CNV_SExp_outnear', '前哨近', t, template=OUTPOST, player=s1, area=near, most=2)
        counted('CNV_SExp_minernear', '矿车近', t, template=MINER, player=s1, area=near, most=2)
        counted('CNV_SExp_tanks', '坦克东', t, template=tank, player=s1, area=east, most=5)
        t.scripts.append(Script('Test - keep targets', [],
                               [('UNIT_SET_HEALTH', m.role(r).name, 100.0)
                                for r in ('plant', 'barracks', 'tank')], once=False))
        # bench round 154, all three alike: the miner harvests on its own (default team, moving from f9, near s17), the
        # SimpleExpansion team is made empty at f152 and again f230 -- the placed miner is never taken, nor the escorts;
        # no outpost to s68. (The prediction, the model taking the miner: outpost s15 within 150 -- refuted.)
        t.expect += [('前哨', 30, '==', 0, 60), ('矿车近', 30, '==', 1, 60), ('坦克东', 30, '==', 0, 60)]
        t.bench = [('bench_watch', dict(seconds=60, every=1, sheet=False, lines=4))]
        return t


    def h(m):
        """D round 155 (aiexph200 / aiexph50 / aiexph400): the AI builds the miner (refinery, money, a PRODUCTION
        deposit, no AlliedNeededUnits). Counters: outposts on the map, outposts within 150 of the pick, miners on the
        map, miners within 150 of the pick. The unpack point itself: the teams host's cmd log."""
        t = Test()
        MINER, OUTPOST = m.facts['miner'], m.facts['outpost']
        s1 = m.player('s1')
        near = 'CNV SExp near'
        t.areas[near] = square(*m.facts['expansion pick'], 150.0)
        counted('CNV_SExp_out', '前哨', t, template=OUTPOST, player=s1)
        counted('CNV_SExp_outnear', '前哨近', t, template=OUTPOST, player=s1, area=near, most=2)
        counted('CNV_SExp_miners', '矿车', t, template=MINER, player=s1, most=5)
        counted('CNV_SExp_minernear', '矿车近', t, template=MINER, player=s1, area=near, most=2)
        t.scripts.append(Script('Test - keep targets', [],
                               [('UNIT_SET_HEALTH', m.role(r).name, 100.0)
                                for r in ('plant', 'barracks', 'tank')], once=False))
        # bench round 155, all three alike (s1-s102..s126): one miner throughout (the refinery's free one, harvesting
        # the bluff), no outpost; the teams host: the SimpleExpansion team made f152 with n=0 and still n=0 at f1741,
        # no build order logged -- the CreateUnits slot orders no miner by itself (d154's H1 refuted).
        if not m.facts.get('opener builds miner'):
            t.expect += [('前哨', 30, '==', 0, 90), ('矿车', 30, '==', 1, 90), ('前哨近', 30, '==', 0, 90)]
        # bench round 156 (aiexpb*, the opener builds one miner): the SimpleExpansion team takes it at f465 with the four
        # Guardians; the miner unpacks the first frame it is within Distance of the Expansion node (400: f995 at
        # (3887, 2717), outpost (3885, 2733) counted s95; 200: f1061 at (3998, 2903), outpost (4012, 2903) s106); with
        # 50 the team's destination is 98 from the node, the miner never gets within 50 and never unpacks (to f1936).
        elif m.facts.get('gap node removed'):
            # D round 172 (aiexpb50n): the reading is the miner's stop in the teams host's log (it arrives ~f1150). The
            # watch is long (bench_watch runs at most 120 s a call): on 11-16 this map ran 1.6-6 logic frames a bench
            # second (11-15 02:52: 15), so 130 s ended near f800 with the miner still on its way.
            t.expect += [('前哨', 30, '==', 0, 480)]
            t.bench = [('bench_watch', dict(seconds=120, every=2, sheet=False, lines=4))] * 4
            return t
        elif m.facts['tactic distance'] == 50:
            t.expect += [('前哨', 30, '==', 0, 130), ('矿车近', 80, '==', 1, 130)]
        else:
            t.expect += [('前哨', 112, '==', 1, 130), ('前哨近', 30, '==', 0, 130)]
        t.bench = [('bench_watch', dict(seconds=130 if m.facts.get('opener builds miner') else 90, every=1,
                                        sheet=False, lines=4))]
        return t


    CHECKS = {key: {'a': a} for key in ('aiexpse', 'aiexpd50', 'aiexpd400')}
    CHECKS |= {key: {'a': h} for key in ('aiexph200', 'aiexph50', 'aiexph400', 'aiexpb200', 'aiexpb50', 'aiexpb400', 'aiexpb50n')}
    return dict(CHECKS=CHECKS)


@cache
def engine_aiskirm():
    """Engine probe: when the skirmish AI's first attack team leaves its base (missions/aiskirm_bench.py: s1 AlliedBalanced
    with a yard, woken at 10 s with 50000 money; the player has a yard, a war factory and a power plant on the west bank),
    read for the plan simulator (simai.py: first team BalancedAttackGround = 4 Riptides + 4 dogs leaves ~157 s after the
    wake; the player's 3 buildings die 232-261 s after).

      a  激流总数 / 激流在家   Riptides (AlliedAntiInfantryVehicle) s1 owns / of them inside 600 around the east base
         出门帧             frames from the wake until the first Riptide stands outside the area (stops there; never
                            out = counts the whole run). 15 frames a second.
         我方建筑           how many of the player's yard / war factory / power plant are still alive (0-3)

    The units counted are the Riptides only (the team's dogs are not read: the Riptides are the first to be built and the
    ones that leave with the team). Four lines a check. Once the first leaves, the other readings are the timeline.

    读数
    RESULTS (bench 2026-11-07; bench s; counters 激流总数 激流在家 出门帧 我方建筑; the check logs 1-s rows; PASS):
      wake: 出门帧 starts counting at ~s8.1 bench (the check's wake = timer 10 s + 30 ticks; bench s runs ~2 s ahead of
        the mission clock), 15 frames a second. Seconds below are bench s; "after wake" = minus ~8.1.
      first Riptide: 激流总数 1 at s111 (~103 s after wake), 2 at s123, 3 at s131, 4 at s142, 5 s174, 6 s185, 7 s248,
        8 s259, 9 s269, 10 s280, 11 s291, 12 s317, 13 s325 (total counts all Riptides, the AI keeps building).
      leaves: 出门帧 stops at 1992 (= 132.8 s) at s139: 激流在家 3 at s138, 1 at s139 (two out at once) = first team
        leaves ~131-133 s after the wake (sim said ~157 s: the sim is ~25 s late).
      player buildings 我方建筑: 3 until s202, 2 from s203, 1 from s221, 0 from s223 = first dies ~195 s after the wake,
        the last (all three gone) ~215 s after (sim said 232-261 s: the sim is ~35-45 s late).
      Reading: the first attack team leaves ~132 s after the wake, 20 s after the first Riptide stands (s111), and the
      player's 3 buildings are gone ~83 s after it leaves; the sim's 157 s / 232-261 s are too late.

      b  激流在家 / 警犬总数 / 警犬在家 / 出圈帧   (dogs = AlliedScoutInfantry; 出圈帧 stops at the first dog out)
    RESULTS b (bench 2026-11-07; PASS; wake = ~s8.1 bench, so after-wake seconds = bench s minus 8.1):
      dogs: total 1 at s23, 2 at s26 (built before the first Riptide); 出圈帧 stops at 661 (= 44 s after wake) at s52:
        警犬在家 2 -> 1 at s52 -> 0 at s55; back 2 at s68-86; 0 again from s87 on (the whole 120-170 window). So the dogs
        scout on their own, they are NOT in the team that leaves with the Riptides.
      Riptides: 在家 1 at s111, 2 at s123, 3 at s131-138, 1 at s139, 0 at s140-141 (the two leave at s139).
      120-145 s after wake (s128-153), 激流在家/警犬总数/警犬在家: s128-130 2/2/0; s131-138 3/2/0; s139 1/2/0;
        s140-141 0/2/0; s142 1/2/0; s143-150 2/2/0; s151-153 1/2/0. Dogs stay at 0 home, so no dog leaves with them.
      145-170 s after wake (s153-178): 激流在家 1 (to s158; the 4th, built s142, left at s151), 0 (s159-173; the 2nd team
        out), 1 from s174, 2 from s185 -- these are the new builds of a's total (5th at s174, 6th at s185); no dog or
        Riptide is seen coming home (home count only rises at build seconds).
      Reading: the first team's two Riptides leave without dogs; the dogs left earlier (~44 s after wake) and are away.

      c  维和总数 / 维和在家 / 标枪总数 / 工程师总数   (Peacekeeper AlliedAntiInfantryInfantry, Javelin soldier
         AlliedAntiVehicleInfantry, AlliedEngineer; home = inside 600 around the east base; runs to ~s188)
    RESULTS c (bench 2026-11-07; PASS; after-wake seconds = bench s minus 8.1; templates all exist in the SDK):
      Peacekeepers total: 1 at s43 (35 s after wake), 2 s49 (41), 3 s54 (46), 4 s133 (125), 5 s150 (142), 6 s162 (154),
        7 s168 (160), 8 s179 (171). Javelin: 1 s32 (24), 2 s37 (29), 3 s60 (52), 4 s156 (148), 5 s173 (165), 6 s185 (177).
        Engineer: 1 at s144 (136), only one in the whole run. So the barracks never stops: ~1 infantry per 5-25 s, a long
        gap 52-125 s (nothing built; 3 Peacekeepers + 3 Javelins stand home s69-132).
      Peacekeepers at home 125-145 s after wake (s133-153): 4 (s133-140), 1 at s141 (= 132.9 s after wake: THREE leave
        in the same second, the same moment the first Riptide team leaves), 0 s142-144, 3 at s145 (the 3 back or new ones:
        total stays 4, so they return), 4 at s150, 1 at s152 (3 out again). Engineer built s144 (136 s).
      Reading: the first attack team leaves ~133 s after wake with 3 Peacekeepers (plus the Riptides); the barracks'
        4th Peacekeeper (125 s) is built just before and stays or comes back.

      d  AI钱 / 塔数 / 建筑数 / 兵数   (AI钱 = s1's money each frame; 塔数 = AlliedBaseDefense + AlliedBaseDefenseAdvanced;
         建筑数 = yard + power + barracks + refinery + war factory + towers; 兵数 = Peacekeeper + Javelin + Riptide + dog.
         Mission aiskirm (50000) and aiskirmlow (15000, CampAISkLow). f = d + PLAYER_GIVE_MONEY 20000 to s1, aiskirmlow only.
         aiskirm20 (20000, CampAISk20): B handoff 120 hypothesis 3 -- does the DEFENSE share build up from the budget
         switch (a tower some time after the opening although 5 % x the money stays under 800), or is it 5 % x the money
         now (no tower: the opening leaves ~11000)? Simulator (round 119, before the bench): no tower.
    RESULTS d aiskirm20 (bench 2026-11-10, CampAISk20D; PASS; first money at s8, so after-wake = bench s minus 8):
      NO tower in the whole run (塔数 0 to s229 = ~221 s after wake). AI钱 at 0/60/100/120/140/160/180/200 s after wake:
        19993, 13089, 10949, ~10314, 6936, 5098, 3118, 770; under 100 at s214, 2 at s215-217, then income only (~945 at
        s229). 建筑数 2 at 10 s, 3 at 21, 4 at 41, 5 at 61, 6 at 70, 7 at 91,
        8 at 130, 9 at 140 (not towers). 兵数 8 from 52 s to 104, 10 at 114, 12 at 126, 15 at 148, 18 at 164, 24 at 189,
        26 at 203.
      Reading: 5 % x the money is under 800 from the opening's end on and no tower comes in ~90 s after it -- the share
        does not build up from the budget switch fast enough to matter; the simulator (5 % x the money now) agrees.)
    RESULTS d (bench 2026-11-07; PASS; after-wake seconds = bench s minus the first-money second: s8 for aiskirm, s9 for
      aiskirmlow; the run ends ~245 s after wake, longer than the 200 s asked):
      aiskirm d, AI钱 at 0/60/100/110/120/130/140/160/180/200 s after wake: 49996, 43050, 41063, 40810, 40790, 40389,
        39740, 38300, 35685, 33608. Per 10 s: ~1160 (0-60 s), ~500 (60-100), ~260 (100-110), ~0-20 (110-120), ~400 (120-130),
        ~650 (130-140), ~720 (140-160), ~1300 (160-180), ~1040 (180-200). No cliff at 120 s: money goes out steadily.
        Towers: first at s184 (176 s after wake), second at s204 (196 s) [re-run 2026-11-10 (b121_bench2.log, PASS): towers
        s150 / s170 = 141 / 161 s after the wake s9, 建筑数 8 at 131 s, 10 at 142 s, 11 at 161 s; see x]. 建筑数 1, 2 at 11 s, 3 at 21, 4 at 41, 5 at 61,
        6 at 71, 7 at 95, 8 at 163, 10 at 176 (a tower + one more), 11 at 196. 兵数: 8 from 52 s to 114 s, 9 at 115, 10 at 129,
        11 at 145, 12 at 147, 13 at 170, ... 18 at 201, 26 at 237.
      aiskirmlow d: AI钱 at 0/60/100/110/120/130/140/160/180/200: 14966, 8089, 5989, 5700, 5670, 5405, 4830, 2400, 1183,
        800. Per 10 s: ~1150 (0-60), ~525 (60-100), ~290 (100-110), ~30 (110-120), ~265 (120-130), ~575 (130-140), ~1215
        (140-160), ~610 (160-180), ~190 (180-200). Money under 1300 from 166 s on, 85 at s234, 50 at s235 (floor). NO tower
        in the whole run (0 to s279). 建筑数 2 at 10 s, 3 at 20, 4 at 42, 5 at 61, 6 at 71, 7 at 92, 8 at 153, 9 at 162 (not
        towers). 兵数 8 from 52 s to 103, 9 at 104, 10 at 125, 12 at 147, 13 at 157, 15 at 171, 19 at 241.
    RESULTS f (aiskirmlow, 20000 given at s166 = ~157 s after wake s9, not 160: the timer starts a bit early; PASS):
      AI钱 at 0/60/100/110/120/130/140/160 s after wake: 14960, 7986, 5835, 5630, 4853, 3315, 1671, ~410 (s165, just before
        the gift); the gift: 405 -> 20276 at s166. After it: 161 s 19812, 170 s 18578 (s179), 180 s 17022 (s189), 190 s
        15644 (s199), 200 s 14491 (s209), 210 s 13586 (s219), 230 s 11740 (s239). Spent after the gift: 1355 in the first 10 s,
        ~2670 in 20 s, ~4120 in 30 s (income included), ~5800 in 43 s, ~8500 in 70 s (s236).
        Before the gift this run spent faster than aiskirmlow d (money 5300 at s126 vs s142 there).
      Tower: the first at s186 (177 s after wake, ~20 s after the gift), one only. 建筑数 9 at 138 s, 10 at 177 (that tower).
        兵数 9 at 102 s, 10 at 114, 12 at 123, 13 at 133, 15 at 145, 16 at 151, 17 at 157, 18 at 162, 22 at 174, 27 at 197,
        30 at 238. The tower came at the same ~176 s as in aiskirm d (50000), so it does not look tied to the gift but to
        time plus having money then (aiskirmlow d, money ~1500 at 177 s, had none).

      e  标枪近院 / 出门帧 / 维和在家 / 标枪在家   (aiskjav only: s1 has a named Javelin soldier 'UNIT - CNV AI Jav' 100 west of
         the yard; at mission second 100 (90 s after the wake) it is teleported to OUT, 1200 straight south of the yard.
         标枪近院 = that soldier inside 300 around the yard (1/0); 出门帧 and 维和在家 as in a / c; 标枪在家 = all of s1's
         Javelin soldiers inside 600. Question: does the AI's LandDefense team still hold its soldiers 90 s after the wake?
         Runs to ~170 s of the mission. Weak expectation: the readings are complete.)
    RESULTS e (bench 2026-11-08, aiskjav, CampAISkJavE; PASS (weak); bench s, which runs ~2 s ahead of the mission clock, so
      the teleport at mission 100 shows at ~s102):
      标枪近院: 1 from the start to s20, 0 s21-s32 (it walked out of 300 and back), 1 from s33 to s99 -- so NOT a constant 1
        before the teleport, it left the 300 square for ~12 s once. 0 from s102 (the teleport, out 1200 south) to s154;
        1 again at s155-s161 (inside 300 again ~53 s after the teleport); 0 from s162 on (out again, to the end).
      出门帧: counts 15 a second from s9, stops at 2004 at s158 (first Riptide out; ~19 s later than aiskirm a's s139).
      维和在家: 1 at s37, 2 at s49, 3 at s60, stays 3 to s165; 1 at s166 (two leave), 2 at s167-170, 1-2 after.
      标枪在家: 1 to s31, 2 at s32, 3 at s43, 4 at s54, stays 4 THROUGH the teleport (s102) to s122; 3 at s123-s146, 4 at
        s147, 5 at s150, 2 at s166 (three leave, same second as the Peacekeepers), 1-2 after. No drop at the teleport
        second: the count has other soldiers besides the named one -- read it with 标枪近院, not alone.
      Reading: the named Javelin soldier teleported 1200 away at 90 s after the wake is inside 300 again at ~s155 (so the
        AI does not leave it out there), then is out again from s162, just before the first team (Peacekeepers + Javelins)
        leaves at s166.
      B's reading (round 51): the s21-32 walk is the defense team taking it (MinUnits 1) and placing it; it is brought
        back after the teleport, but in ~53 s, not the ~18 s aidefense b's StaticDefense team took for the same 1200 --
        so likely not held the whole time (re-recruited by a later defense team copy, SortByDistance). It then seems to
        leave with the first attack team (out of 300 at s162, three Javelins leave at s166): the general recruit path
        never takes a unit of another team, so at ~s162 it was in no team -- defense membership is not sticky (disband /
        re-recruit), which is candidate 2 of handoff-b 50, not a gate on AlwaysRecruit. The preplaced soldier also moves
        the first team out from s139 to s158-166 (it gets Javelins: the type mix changed). Not proven: which team it left
        with (no team read on the bench).

      g / h  AI teams counted by name (missions/aiskirm_bench.AI_TEAMS; 99 = no team of that name answered that frame).
         g: 池兵 = the pool's CAN_ATTACK members, 防御型 / 防御名 = LandDefense_MEDIUM_<StaticDefense | Defense>_0_0,
         兵数 = army owned (as d). h: 池全 = all the pool's members, 地图队 = teamSoviet_1, 进攻型 / 进攻名 =
         BalancedAttackGround_MEDIUM_<DefenseAvoidanceAttack | Attack>_0_0. aiskirmnl = aiskirm with Soviet_1's
         Lib_Skirmish_Setup emptied.
    RESULTS g / h (bench 2026-11-10, aiskirm g / h and aiskirmnl g, all PASS (weak); bench s):
      names: the tactic's TYPE is the name ('..._StaticDefense_0_0', '..._DefenseAvoidanceAttack_0_0' answer), the
        Tactic id never does (防御名 / 进攻名 99 the whole run). An empty team flickers 0 / 99 (instance made and gone).
      aiskirm g: every new combat unit goes into LandDefense _0_0 within ~1-2 s (池兵 1 for a second, then 0):
        防御型 = 兵数 from s26 (1) to s69 (8); 7 at s79, 6 from s80 (two leave it -- dogs, b's scouts, likely), 7 at
        s121, 8 at s131-134; then 0 at s136 (all eight at once, ~the second the first attack team leaves: a a/c) and
        it stays 0 / 99 to s203; new units after s136 sit in the pool 1-2 s and go to some other team (not _0_0).
      aiskirm h: pool = 2 at the start (the yard + one more), grows with the buildings and the passing units (14 at
        s150); 地图队 0 the whole run (the library's transfer: handoff.md round 135); 进攻型 _0_0 0 / 99 every ~5 s and
        never a member, also when the attack leaves -- the team that leaves is another instance (other indices).
      aiskirmnl g: the same story ~2-8 s earlier (8 in defense at s62, 0 at s128): the library does not change it.
      Reading: the defense team DOES take every new unit (the model's keep_on=True is right about the pool); the first
        attack team is made of the defense team's eight, released all at once at ~132 s after the wake.

      i / j / k / l  other instances and states (aiskirm; bench 2026-11-10, all PASS (weak); bench s). Labels are words:
         '进攻0_1'-style labels read back as '?' on the bench.
         i / j: BalancedAttackGround_MEDIUM_DefenseAvoidanceAttack and LandDefense_MEDIUM_StaticDefense _0_1 / _1_0 /
           _0_2 / _1_1: 99 the whole run (no such team). the program (work/re/l4_states.md) names '<state>_<tactic type>_<the tactic's index in
           the state>_<copy>' -- both states have one tactic, so the first index is 0.
         k: BalancedAttackOverwhelm_MEDIUM _0_0 flickers 0 / 99 every ~5 s (never a member), BalancedDefense and
           LandEmergencyDefense_MEDIUM 99; **BalancedCleanup_SimpleAttack_0_0 99 -> 8 at s131** (the defense team's
           eight at once), 9 s138, 10 s139, 11 s149, 12 s155, 13 s159, 14 s161 (MaxUnits 14) and stays.
         l: AlliedScout _0_0 1 from s72 (the defense team drops 8 -> 7 -> 6 then: a dog leaves for it), _1_0 and
           EscortMCV 99; LandDefense _0_0 8 -> 0 at s128 in this run.
         l again, stock aiskirm and carrier aiskirmc side by side (bench 2026-11-13, same head, both PASS; log
           a199_l.log): stock AlliedScout _0_0 1 from s72 (defense 8 -> 7 -> 6 at s72-74), as before; **carrier
           AlliedScout _0_0 0 the whole run, defense 9 from s67 to s127** -- the dogs stay in defense. The carrier yard
           (CNVSkirmTeamsYard, a renamed copy of the yard) changes the scout teams, so aiskirmc readings say nothing
           about them (its team log: both scout teams made ~s13, tgt -1 and n 0 throughout, never expire).
         D round 105 (bench 2026-11-13, same head): the rename alone does it -- aiskxn (renamed copy, no behavior, no
           ra3ext) scout 0 / defense 9 from s68 like the old carrier; aiskxo (stock yard, ra3ext loaded, no host) scout 1
           from s71, defense 8 -> 7 -> 6 like stock. Retail data names AlliedConstructionYard (AlliedPowerPlant's
           GameDependency, budget-state filters). The carrier now recompiles the retail yard under its own id with the
           behavior: aiskirmc l scout 1 from s71, defense 8 -> 7 -> 6 at s71-73, 0 at s129 -- stock aiskirm l beside it
           s71 / s71-74 / s128 (one-second jitter). Its log (pri= = the team template's stored Priority): DEFAULT 0, DEFENSE 1, LOW 2,
           STANDARD 3, SCRIPTED 7 -- the xsd order; the scout team (LOW) takes dog 3172 from LandDefense (DEFENSE) at f1101.
      Reading: the first team out is BalancedCleanup (OpeningMove complete, no enemy within 700, income and power
        advantage >= 3: the player has no army and no refinery), not BalancedAttackGround; it takes the LandDefense
        team's members whole the moment it is drawn (~123 s after the wake).

      m  池兵 (pool CAN_ATTACK) / 防御型 (LandDefense _0_0) / 清扫 (BalancedCleanup _0_0) / 池峰 (the most CAN_ATTACK pool
         members seen in any single frame from s110, latched by per-frame scripts). Bench 2026-11-10, aiskirm m PASS (weak):
         防御型 8 at s128-130, **s131: 防御型 0, 清扫 8, 池峰 stays 1** (it reached 1 at s112, a new unit); the pool never
         held more than 1 in any frame, so the eight went defense -> Cleanup within one frame (no script pass saw them in
         the pool). After: the defense team exists empty (0, 99 every ~6 s as at s10-s22), new units sit 1-2 s in the
         pool and go to Cleanup (10 s138, 14 s161 = MaxUnits); only then one goes to defense (1 at s166, gone at s167).
      Reading: not a pool round trip a script could see. With the code (a running StaticDefense instance is never
        reselected: the re-pick check returns false while the instance has started; handoff-b 95 / aiar9-10: a quiet base never releases),
        the release is caused by Cleanup turning on: Cleanup (STANDARD, RELEASE_TO_PRIORITY) takes the DEFENSE team's
        members in one commit, and wins the pool over the defense team until full.

      n  防御型 (LandDefense _0_0) / 清扫 (BalancedCleanup _0_0) / 清扫二 (BalancedCleanup _0_1) / 防御二 (LandDefense _0_1)
         to s203. Bench 2026-11-10, aiskirm n PASS (weak; the first try hung at bench_stop, log b102_n.log; this is
         b102_n2.log): 防御型 8 at s126, 0 from s130; 清扫 8 s130, 10 s137, 14 s158 and stays; 防御型 1 at s165 only;
         **清扫二 and 防御二 99 the whole run** -- no second copy of either team is ever made.
      Reading (corrected round 103, B handoff 105): the second index is not a slot copy. the team-naming routine builds the AI's team
        name table once: for each state, each tactic (index a), each of that tactic's TeamTemplates (index b, count at
        tactic's index field) one name '<state>_<tactic type>_<a>_<b>' (no TeamTemplate: '_default'). BalancedCleanup and
        LandDefense have one TeamTemplate each, so their '_0_1' names do not exist (99 always): n says nothing about a
        second slot, whose team would share the name '_0_0' (MaxTargets 3: the model's (..., 0, 1) / (..., 0, 2)).
        A name answers for one of the same-named teams only; o counts around the names instead.

      o  兵数 (the AI's Peacekeepers + Javelins + Riptides, no dogs) / 清扫 (Cleanup _0_0) / 防御型 / 池兵 to s203:
         兵数 - 清扫 - 防御型 - 池兵 = units in teams no name reads (another Cleanup slot; a dog in Cleanup is noise).
         The model (b100_keep.log): Cleanup's second slot team holds 1 at ~s157 (148.5 s after the wake), 7 by ~s183.
         Bench 2026-11-10, aiskirm o PASS (weak): 清扫 8 s128, 14 from s157 and stays; 兵数 one behind 清扫 to s160 (a
         dog in Cleanup), then 14 s161 -> 15 s166 -> 18 s178 -> 21 s189; 防御型 0 (1 at s162 only), 池兵 0-1.
      Reading: after Cleanup _0_0 is full the new units go to a team no name reads -- about 1 at s162, 7 at s188 (dog
        corrected), as the model's second Cleanup slot. Round 102's mismatch was the name, not the model.

      p  我方建筑 / 清扫 (Cleanup _0_0) / 防御型 (LandDefense _0_0) / 兵数 (no dogs) to s249. Bench 2026-11-10, aiskirm p
         PASS (weak; log work/logs/b104_p.log): 清扫 8 s129, 14 from s159; 兵数 26 by s230; player buildings 3 to s205,
         2 s206, 1 s222, **0 s224**; 防御型 2 at s224 (the dogs' team ended), **s226: 清扫 99, 防御型 14** and so to s249.
      Reading: the player's last building gone, the Cleanup teams end within ~2 s and their units go to the defense
        team (to its MaxUnits 14); no Cleanup team holds anyone again for 23 s (a new one would answer to _0_0). The
        model ends them the same way (B handoff 106), but its third Cleanup copy, still gathering, takes the 14 back
        from defense at once -- not modelled yet (dropping gathering teams whose slot lost its target also killed
        the defense teams: tried and reverted).

      q  进攻型 (BalancedAttackGround _0_0) / 进攻次 (times it appeared, 99 -> a count, latched per frame) / 压倒
         (BalancedAttackOverwhelm _0_0) / 压倒次, to s174. aiskirm (Base personality: SecondsTillTargetsExpire 5) and
         aiskexp (CampAISkExp: a personality = 1AlliedBalanced with SecondsTillTargetsExpire 12). Bench 2026-11-10, both
         PASS (weak; bench s):
         aiskirm: from s9 (the wake) one of the two answers (0 members) for exactly 5 s, then the other: BAG s9-13,
           Overwhelm s14-18, BAG s19-23 ... to s174 -- 17 BAG + 18 Overwhelm instances, each 5 s, never both, never a
           member (LandDefense holds every unit).
         aiskexp: the same with 12 s blocks: Overwhelm s9-20, BAG s21-32, Overwhelm s33-44, **Overwhelm again s45-56**
           (a new instance: the count goes 2 -> 3), BAG s57-67 ... to s174.
      Reading: a not-started instance (its team still gathering) is ended and its slot drawn again every
        SecondsTillTargetsExpire (the re-pick check's interval half, l4_states.md 1.2), the new draw in the same second; the
        draw is the weighted one (Overwhelm twice in a row at 12 s), not a turn-about. So BAG's gathering team is
        replaced every 5 s in a retail skirmish (Base writes 5; the XSD default 15 is never used by the stock AIs).

      r  进攻型 / 进攻帧 / 压倒 / 压倒帧: 帧 = script passes the instance's team answered (0 when it appears, +1 a frame,
         kept once it is gone, so a 99 row shows the last instance's whole life). Bench 2026-11-10, aiskirm r PASS (weak):
         of ~34 instances to s174, most lived **76** frames, a few 75 / 74 / 73 (s34, s139, s159); the next state's team
         is there in the same second (often the same frame) the old one goes.
      Reading: life = 75 frames (5 s x 15) counted from the team's first frame, + 1 for counting both ends (the script
        pass order against the AI update is not known); the 73-74 ones read as the slot assigned (work/re/l4_states.md) a frame or
        two before its team appears. The model (Team.made = the team's frame, ends after 75) is within a frame.

      u  维和总数 / 标枪总数 / 警犬总数 / 工程师总数 to 80 s after the wake. aiskmod (CampAISkMod: 1AlliedBalanced +
         UnitModifier Peacekeeper and Javelin soldier at OffensiveModifier = DefensiveModifier = 0). Bench 2026-11-10,
         aiskmod u PASS (bench s): dogs 1 s23, 2 s26; Javelins 1 s32, 2 s37, 3 s60; Peacekeepers 1 s43, 2 s49, 3 s54;
         no Engineer -- the same seconds as aiskirm c's stock run.
      Reading: UnitModifier at 0 changes nothing in what the barracks builds: the zeroed units are drawn as before. It
        scales only the builder's score (work/re/l4_unitbuilder.md), which no SDK personality's draw uses (no UnitBuilderUnitChoiceStrategy;
        l4_unitbuilder.md round 35). A level cannot steer or forbid a unit with it (caps / build states do that).

      v  步兵 / 塔数 / 建筑数 / AI钱 to ~110 s after the wake. aiskacp / aiskacd (1AlliedBalanced rebuilt on
         AlliedCoopBaseSkirmishPersonality, its one opening = retail AlliedStandard with the Time 10s Deposit 2000 into
         PRODUCTION / DEFENSE). Bench 2026-11-10, both PASS (bench s):
      aiskacp: 步兵 1 s25, 2 s26, 3 s33, 4 s38, 5 s44, 6 s50, 7 s56, 8 s62, then 8 to s134 (9 s136); 塔数 0 throughout;
        建筑数 2 s20, 3 s30, 4 s50, 5 s71, 6 s81, 7 s100, 8 s144 -- aiskirm c's timeline: the rebuilt AI is the stock one.
      aiskacd: 步兵 0 to the end (s128); 塔数 1 at s49, 2 at s69 (2 x 800 of the 2000), no third; 建筑数 2 s19, 3 s29,
        5 s49, 7 s69, 8 s85, 9 s106; AI钱 ~41100 at s128 (aiskacp ~41000 at s128: the same spend, towers for infantry).
      Reading: the opening's Account picks what the Deposit buys: PRODUCTION feeds the barracks, DEFENSE buys towers
        (the base defense builder spends DEFENSE) and the barracks stays idle through the opening (its budget gives
        PRODUCTION 0 %). The simulator matches the infantry, not the towers (keeps the DEFENSE 2000).
    """
    from parts import Script, Test, counted, square, status
    from checks.engine_aiskirm import ARMY, BUILDINGS, TOWERS, CAP, DOG, RIPTIDE, _sum

    AREA = 'CNV AI Base Area'
    YOURS = ('AlliedConstructionYard', 'AlliedWarFactory', 'AlliedPowerPlant')
    SECONDS = 310.0                     # after the wake


    def a(m):
        t = Test()
        m.spawns.add(RIPTIDE)               # published for the contract: the AI makes it, the check counts it
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 600.0)
        counted('CNV_AK_Total', '激流总数', t, template=RIPTIDE, player=s1)
        counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
        t.counters.append(('CNV_AK_OutFrames', '出门帧'))
        t.counters.append(('CNV_AK_Built', '我方建筑'))
        p1 = m.player('p1')
        t.scripts.append(Script('Test - built zero', [], [('SET_COUNTER', 'CNV_AK_Built', 0)], once=False))
        for i, tpl in enumerate(YOURS):
            m.spawns.add(tpl)
            t.scripts += [Script(f'Test - own {i}', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, p1, f'CNV_AK_Own{i}')],
                                 once=False),
                          Script(f'Test - built {i}', [('COUNTER', f'CNV_AK_Own{i}', 3, 1)],
                                 [('INCREMENT_COUNTER', 1, 'CNV_AK_Built')], once=False)]
        t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                      Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                             [('SET_FLAG', 'Test Woke', 1)])]
        for n in range(1, 9):                # more of them owned than at home = one is out
            t.scripts.append(Script(f'Test - out {n}', [('COUNTER', 'CNV_AK_Total', 2, n), ('COUNTER', 'CNV_AK_Home', 0, n)],
                                    [('SET_FLAG', 'Test Out', 1)], once=False))
        t.scripts.append(Script('Test - wait out', [('FLAG', 'Test Woke', 1), ('FLAG', 'Test Out', 0)],
                                [('INCREMENT_COUNTER', 1, 'CNV_AK_OutFrames')], once=False))
        w = m.facts['wake at']
        t.expect += [('激流总数', w + 150.0, 'ever>=', 1, w + SECONDS)]
        t.bench = [('bench_watch', dict(seconds=w + SECONDS + 4.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def b(m):
        """Same wake and area as a; reads the Riptides together with the dogs (AlliedScoutInfantry): do the dogs leave in
        the same second as the two Riptides?  出圈帧 stops at the first dog out (dogs owned > dogs at home)."""
        t = Test()
        m.spawns.add(RIPTIDE)
        m.spawns.add(DOG)
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 600.0)
        counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
        counted('CNV_AK_DogTotal', '警犬总数', t, template=DOG, player=s1)
        counted('CNV_AK_DogHome', '警犬在家', t, template=DOG, area=AREA, player=s1)
        t.counters.append(('CNV_AK_OutFrames', '出圈帧'))
        t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                      Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                             [('SET_FLAG', 'Test Woke', 1)])]
        for n in range(1, 9):                # more dogs owned than at home = one is out
            t.scripts.append(Script(f'Test - out {n}', [('COUNTER', 'CNV_AK_DogTotal', 2, n), ('COUNTER', 'CNV_AK_DogHome', 0, n)],
                                    [('SET_FLAG', 'Test Out', 1)], once=False))
        t.scripts.append(Script('Test - wait out', [('FLAG', 'Test Woke', 1), ('FLAG', 'Test Out', 0)],
                                [('INCREMENT_COUNTER', 1, 'CNV_AK_OutFrames')], once=False))
        w = m.facts['wake at']
        t.expect += [('警犬总数', w + 150.0, 'ever>=', 1, w + 170.0)]
        t.bench = [('bench_watch', dict(seconds=w + 174.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def c(m):
        """Same wake and area as a; counts the barracks' infantry: Peacekeepers (AlliedAntiInfantryInfantry) total and at
        home, Javelin soldiers (AlliedAntiVehicleInfantry) total, Engineers (AlliedEngineer) total. Runs to ~170 s after
        the wake. Home = inside 600 around the east base."""
        t = Test()
        PK, JAV, ENG = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', 'AlliedEngineer'
        for tpl in (PK, JAV, ENG):
            m.spawns.add(tpl)
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 600.0)
        counted('CNV_AK_PkTotal', '维和总数', t, template=PK, player=s1)
        counted('CNV_AK_PkHome', '维和在家', t, template=PK, area=AREA, player=s1)
        counted('CNV_AK_JavTotal', '标枪总数', t, template=JAV, player=s1)
        counted('CNV_AK_EngTotal', '工程师总数', t, template=ENG, player=s1)
        w = m.facts['wake at']
        t.expect += [('维和总数', w + 150.0, 'ever>=', 1, w + 170.0)]
        t.bench = [('bench_watch', dict(seconds=w + 174.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def u(m):
        """UnitModifier (aiskmod: Peacekeeper and Javelin soldier at OffensiveModifier = DefensiveModifier = 0; aiskirm
        the stock one, same check): totals of the barracks' four -- Peacekeepers, Javelin soldiers, dogs, Engineers --
        to 80 s after the wake. The model's guess: the zeros change nothing (no choice strategy in the SDK chain), so
        both builds make Peacekeepers and Javelins in the first minute (aiskirm c: 3 + 3 by ~52 s after the wake)."""
        t = Test()
        PK, JAV, ENG = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', 'AlliedEngineer'
        for tpl in (PK, JAV, ENG, DOG):
            m.spawns.add(tpl)
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_AK_UPk', '维和总数', t, template=PK, player=s1)
        counted('CNV_AK_UJav', '标枪总数', t, template=JAV, player=s1)
        counted('CNV_AK_UDog', '警犬总数', t, template=DOG, player=s1)
        counted('CNV_AK_UEng', '工程师总数', t, template=ENG, player=s1)
        w = m.facts['wake at']
        t.expect += [('维和总数', w + 70.0, 'ever>=', 1, w + 80.0), ('标枪总数', w + 70.0, 'ever>=', 1, w + 80.0)]
        t.bench = [('bench_watch', dict(seconds=w + 84.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def v(m):
        """Order Account (aiskacp / aiskacd: 1AlliedBalanced rebuilt with retail AlliedStandard as its one opening, the
        `Time 10s` line's Deposit 2000 into PRODUCTION (retail) / DEFENSE): 步兵 = the barracks' four (Peacekeeper, Javelin,
        dog, Engineer) s1 owns, 塔数 (the two Allied towers), 建筑数 (yard, power, barracks, refinery, war factory, towers),
        AI钱, to 110 s after the wake. The model's guess (private ai/player.py UNIT_ACCOUNT, the barracks spends PRODUCTION
        only; OpeningMoveBudget gives PRODUCTION / DEFENSE 0 %): PRODUCTION builds as aiskirm c (8 infantry by ~52 s after
        the wake), DEFENSE builds no infantry while the opening runs (to ~120 s)."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        _sum(t, m, s1, 'CNV_AK_VInf', '步兵', ('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', DOG,
                                               'AlliedEngineer'))
        _sum(t, m, s1, 'CNV_AK_VTow', '塔数', TOWERS)
        _sum(t, m, s1, 'CNV_AK_VBlt', '建筑数', BUILDINGS + TOWERS)
        t.counters.append(('CNV_AK_VMoney', 'AI钱'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AK_VMoney')], once=False))
        w = m.facts['wake at']
        if m.facts['production deposit']:
            t.expect += [('步兵', w + 10.0, 'ever>=', 6, w + 70.0)]
        else:
            t.expect += [('步兵', w + 5.0, '<=', 0, w + 100.0)]
        t.bench = [('bench_watch', dict(seconds=w + 114.0, every=1, sheet=False, lines=len(t.counters)))]
        return t






    def _spend(m, give=None):
        """d / f: money, towers, buildings, army of s1."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.counters.append(('CNV_AK_Money', 'AI钱'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AK_Money')], once=False))
        _sum(t, m, s1, 'CNV_AK_Towers', '塔数', TOWERS)
        _sum(t, m, s1, 'CNV_AK_Built', '建筑数', BUILDINGS + TOWERS)
        _sum(t, m, s1, 'CNV_AK_Army', '兵数', ARMY)
        w = m.facts['wake at']
        t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                      Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                             [('SET_FLAG', 'Test Woke', 1)])]
        run = 230.0 if give else 200.0
        if give:
            t.scripts += [Script('Test - give set', [('FLAG', 'Test Woke', 1)], [('SET_MILLISECOND_TIMER', 'Test Give', give)]),
                          Script('Test - give', [('FLAG', 'Test Woke', 1), ('TIMER_EXPIRED', 'Test Give')],
                                 [('PLAYER_GIVE_MONEY', s1, 20000)])]
        t.expect += [('兵数', w + 150.0, 'ever>=', 1, w + run)]
        t.bench = [('bench_watch', dict(seconds=w + run + 4.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def d(m):
        """s1's money every frame, towers (AlliedBaseDefense + AlliedBaseDefenseAdvanced), all buildings (yard, power,
        barracks, refinery, war factory, towers) and army (Peacekeeper + Javelin + Riptide + dog). To ~200 s after wake."""
        return _spend(m)


    def f(m):
        """Same as d, plus PLAYER_GIVE_MONEY 20000 to s1 160 s after the wake; to ~230 s after the wake."""
        return _spend(m, give=160.0)


    def w(m):
        """Same as f with the gift earlier: PLAYER_GIVE_MONEY 20000 at timer 128 s (~125 s after the wake, f's 160 gave at
        ~157). B handoff 121 hypothesis 1: a tower ~20 s after the gift (~145 s) = no fixed gate after the opening; still
        ~176 s = a gate (in f the tower came 20 s after the gift, at the same ~176 s as aiskirm d). Simulator (round 120,
        before the bench): the tower at 148.1 s.

        RESULTS w (bench 2026-11-10, aiskirmlow, CampAISkLowW; PASS; first money at s9, after-wake = bench s minus 9):
          the gift: 4292 -> 24063 at s135 (126 s after wake). The tower: 塔数 1 at s156 (147 s after wake, 21 s after the
          gift), one only to s253 (244 s). 建筑数 8 at s138 (129 s), 9 at s149 (140), 10 at s156 (the tower). Money after:
          ~20770 at the tower, ~16450 at 191 s, ~9950 at 244 s.
          Reading: no fixed gate after the opening -- the tower comes ~20 s after the money is there (as f: 20 s after its
          gift), as the simulator. aiskirm d's late first tower (176 s with the money there from 120) is something else:
          there the 8th building is at 163 s, here at 129 -- the tower follows the post-opening buildings (round 120)."""
        return _spend(m, give=128.0)


    KINDS = ('AlliedPowerPlant', 'AlliedRefinery', 'AlliedBarracks', 'AlliedWarFactory')   # 建筑码 digits, ones first
    TECH = ('AlliedTechStructure', 'AlliedSuperWeaponAdvanced', 'AlliedNavalYard')


    def x(m):
        """Which buildings s1 builds after the opening (B handoff 122 (1): aiskirm d's 8th building at 163 s and the one
        with the first tower at 176 s are not known). 建筑码 = power plants + 10 x refineries + 100 x barracks + 1000 x war
        factories (each read to 9; four counters at most, so the four kinds share one), 空军 = AlliedAirfield, 科技 =
        AlliedTechStructure + AlliedSuperWeaponAdvanced + AlliedNavalYard, 塔数 as d. To ~200 s after the wake. The
        candidates are 1AlliedBalanced's build states after OpeningMove Complete (private ai/data.py):
        NonPathDependentStructure (power POWER, refinery REFINERY, barracks / airfield FACTORY) and Tech (airfield /
        tech structure / superweapon TECH, no enemy within 700); the simulator builds none of them (towers only):
        建筑码 1122 from ~91 s after the wake, towers 140.1 / 160.2 s (work/logs/b121_pred.log).

        RESULTS x (bench 2026-11-10, aiskirm, CampAISkirmX; two runs, both PASS and the same to the second; wake ~s8, so
          after-wake = bench s minus 8; logs work/logs/b121_bench.log, b121_bench2.log):
          建筑码 100 s19 (barracks), 101 s29, 111 s49, 121 s69, 122 s79, 1122 s99 (war factory: the opening's six, as the
          simulator), **1123 s138, 1124 s148** (a 3rd and 4th power plant, ~130 / ~140 s after the wake); 塔数 1 s148, 2
          s168 (~140 / ~160 s); **空军 1 at s202** (~194 s); 科技 0 to s219.
          Reading: the post-opening buildings are two power plants (NonPathDependentStructure's POWER line) and an airfield
          (FACTORY or TECH); no refinery, barracks, war factory, tech structure. The towers come at 140 / 160 as the
          simulator; a d re-run the same day (b121_bench2.log) too: towers s150 / s170 with the money at s9 = 141 / 161 s,
          建筑数 8 at s140 (131 s). The 2026-11-07 d run's 176 / 196 (8th building 163 s) is the one run that differs.

        RESULTS x on aiskpw0 / aiskpw3 (bench 2026-11-10, both PASS; log work/logs/b122_bench.log): the same AI with
          DesiredExcessPowerBuffer 0 / 300 (retail BasePersonality 100). The opening's six as above (1122 s99-s102).
          aiskpw0: **no plant after the opening** (1122 to s228), 塔数 1 s154, 2 s174, **空军 0 to s228**.
          aiskpw3: **four plants** -- 1123 s138, 1124 s148, 1125 s158, 1126 s168 (to s220); 塔数 1 s147, 2 s167; 空军 1 s219.
          Reading: the post-opening plants follow the buffer: 0 -> 0, 100 -> 2, 300 -> 4. Excess after the opening = 250 -
          175 = 75 (yard 50 counted) or 25 (not): "build while excess < buffer + 100" fits 100 and 300 either way, but not 0
          (75 < 100 would build one) unless 0 turns POWER off; B handoff 124 has the table."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        _sum(t, m, s1, 'CNV_AK_XKind', '建筑码', KINDS, weights=(1, 10, 100, 1000), cap=9)
        _sum(t, m, s1, 'CNV_AK_XAir', '空军', ('AlliedAirfield',), cap=9)
        _sum(t, m, s1, 'CNV_AK_XTech', '科技', TECH, cap=9)
        _sum(t, m, s1, 'CNV_AK_XTow', '塔数', TOWERS, cap=9)
        w = m.facts['wake at']
        t.expect += [('建筑码', w + 100.0, 'ever>=', 1, w + 200.0)]
        t.bench = [('bench_watch', dict(seconds=w + 204.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def y(m):
        """Does the AI build a unit of ours (aisknew / aisknew2: s1 owns, besides what it builds, a copied barracks that
        also builds CNVNewPK = the Peacekeeper under a new id)? Totals of s1's new Peacekeepers, retail Peacekeepers,
        Javelin soldiers, and 兵营码 = retail barracks + 10 x copied ones, to 150 s after the wake.
        Data's prediction (B handoff 126, l4_buildstate.md, l4_unitbuilder.md): the build states list units by template
        (none lists CNVNewPK), so aisknew builds none of it -- unless the UnitBuilder, whose candidates are 'the templates
        the player can build' (work/re/l4_unitready.md), takes it from the copied barracks; aisknew2 lists it in a build state of its own
        (FEWEST_UNIT), so >= 1 there.

        RESULTS y (bench 2026-11-11, both PASS; log work/logs/b125_bench.log, work/bench_results/aisknew*__y.json; wake
          ~s9; 兵营码 10 from s1 = the copied barracks, 11 from s19 = the opening's retail one too):
          aisknew (stock personality): **新维和 0 to s168**; 维和 6, 标枪 12 by s168 (from both barracks).
          aisknew2 (+ CNVNewBuild): 新维和 1 at s27 (the first infantry), 4 by s44, **9 by s167**; 维和 4, 标枪 6.
          Reading: the AI builds a unit of ours only when a build state of its personality lists it by template -- owning
          a factory that builds it is not enough (the UnitBuilder's candidates do not take it either). With one listed it
          takes about half the barracks' output (FEWEST_UNIT among four). So a level's 偏好 / UnitModifier cannot make it
          build our units (aiskmod u: no effect at all); plan.py would need a BuildState line, and the AI a factory of its
          own that builds the unit (the copies are the player's only).

        RESULTS y on aiskcap (bench 2026-11-12, PASS; run work/testbench/runs/CampAISkCapY_mcp_1112_043040): aisknew2 +
          the child personality's SpecificUnitCap CNVNewPK Cap 2 at all four difficulties (no parent lists CNVNewPK; the
          simulator predicted 2 to s167, work/logs/b145_pred.log). 新维和 1 s27, **2 from s33 to s149** (aisknew2: 3 s38,
          4 s44) while 标枪 went 1 -> 6 and 维和 0 -> 2; then **3 at s150, 4 from s155** to s168 (维和 5, 标枪 9).
          Reading: the cap binds (template match, the MEDIUM bit, the value) -- the barracks' other units take the
          capped one's turns; after ~s150 the capped unit is built again with none lost, so what the engine counts
          against the cap is not simply the units owned (not known; tests/test_simai_bench_b.py strict xfail).

        RESULTS y on aiskblk* (bench 2026-11-12, all three PASS; runs work/testbench/runs/CampAISkBlk{N,F,R}Y_mcp_1112_*):
          aisknew2 whose CNVNewPK entry carries BlockIfThingNearFactory Rule ANY Relationship NEUTRAL IncludeThing <a
          neutral blocker north of the copied barracks>, default distance 150.
          aiskblkn (bear 120 away): **新维和 0 to s168**; 维和 6, 标枪 11 (the barracks build the rest).
          aiskblkf (bear 400 away): 新维和 1 s28, 4 s45, **9 s167** -- as aisknew2 (1 s27, 9 s167).
          aiskblkr (an allied power plant whose centre is 190 away): **新维和 0 to s168**; 维和 9, 标枪 9.
          Reading: as D59 read it -- an entry scores 0 while a thing passing the filter is within the distance of the
          factory; 'within' adds the thing's bounding circle (centre 190 > 150, circle in reach), and NEUTRAL matches a
          neutral thing.

        RESULTS y on aiskoff (bench 2026-11-12, PASS; run work/testbench/runs/CampAISkOffY_mcp_1112_111724): aisknew2
          whose build state's heuristic is ScriptedFlagHeuristic on a flag nobody sets (the state never scores, CNVNewPK
          still listed): **新维和 0 to s168**; 维和 6, 标枪 12 (as aisknew). Reading: the unit builder never takes our
          unit, even listed in a build state of the mission's own -- every new Peacekeeper of aisknew2 / aiskblkf is the
          build state's, and aiskblkn / aiskblkr's 0 is the block alone."""
        NEW_PK, NEW_BARRACKS = 'CNVNewPK', 'CNVAIBarracks'      # missions/aiskirm_bench.py's (G5: no content import)
        t = Test()
        PK, JAV = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'
        for tpl in (PK, JAV):
            m.spawns.add(tpl)
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_AK_YNew', '新维和', t, template=NEW_PK, player=s1)
        counted('CNV_AK_YPk', '维和总数', t, template=PK, player=s1)
        counted('CNV_AK_YJav', '标枪总数', t, template=JAV, player=s1)
        _sum(t, m, s1, 'CNV_AK_YBar', '兵营码', ('AlliedBarracks', NEW_BARRACKS), weights=(1, 10), cap=9)
        w = m.facts['wake at']
        t.expect += [('兵营码', w + 140.0, 'ever>=', 10, w + 150.0)]
        t.bench = [('bench_watch', dict(seconds=w + 154.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def yc(m):
        """aiskcu / aiskcs (check yc): does a unit counted as a structure by the personality's
        CountAsStructureForBuildPurposesFilter block the AI's other unit orders? Both builds: aisknew2 + CNVDearPK (the
        Peacekeeper at build cost 100000, from a second copied barracks, CONSTANT 1 in the build state); aiskcs also adds
        CNVDearPK to the filter. Counters: 新维和 (CNVNewPK), 贵维和 (CNVDearPK, expected 0), 维和总数, 标枪总数, per second
        to 170 s after the wake. Prediction: aiskcu builds CNVNewPK as aisknew2; aiskcs builds none from the state."""
        NEW_PK, DEAR_PK = 'CNVNewPK', 'CNVDearPK'      # missions/aiskirm_bench.py's (G5: no content import)
        t = Test()
        PK, JAV = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'
        for tpl in (PK, JAV):
            m.spawns.add(tpl)
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_AK_YCNew', '新维和', t, template=NEW_PK, player=s1)
        counted('CNV_AK_YCDear', '贵维和', t, template=DEAR_PK, player=s1)
        counted('CNV_AK_YCPk', '维和总数', t, template=PK, player=s1)
        counted('CNV_AK_YCJav', '标枪总数', t, template=JAV, player=s1)
        w = m.facts['wake at']
        t.expect += [('贵维和', w + 160.0, 'ever>=', 0, w + 170.0)]
        t.bench = [('bench_watch', dict(seconds=w + 170.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def ycm(m):
        """yc with AI钱 (s1's money, each frame) in place of 标枪总数: B handoff 157's K1 / K2 -- when CNVDearPK
        (100000 against the 50000 the AI holds) is ordered (yc: s134 aiskcu / s138 aiskcs), is the money at some gate,
        and after it does aiskcs's barracks stay idle while the money sits?
        Bench 11-12 (work/bench_results/aiskc[su]__ycm.json, both PASS): AI钱 50000 -> ~41000 by s120 (the opening and
        two new Peacekeepers), then ~36000 paid within s128-s133 and 贵维和 1 at s133 (cs) / s134 (cu), the money ~5300
        after; 新维和 3 at s133 / s134, 4 at s196 (cs) / s172 (cu), 6 at s216 / s184. So the dear one is paid fast at the
        end, not refused for want of 100000 (K1 / K3); aiskcs did not stall this time (yc's 3-to-the-end not repeated).
        aiskcu3 (the same at 30000, bench 11-12 work/bench_results/aiskcu3__ycm.json, PASS): money 41055 at s127, paid
        down to 9585 by s132 (~31500 in the same five seconds), 贵维和 1 at s133 -- the same order time as at 100000, so the
        cost does not gate the order; at 100000 the payment stops ~36000 in (money ~5300 left) and the unit still comes."""
        t = yc(m)
        t.counters = [c for c in t.counters if c[1] != '标枪总数']
        t.counters.append(('CNV_AK_YCMoney', 'AI钱'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('s1'), 'CNV_AK_YCMoney')],
                                once=False))
        return t


    def yb(m):
        """aiskcap diagnosis (B handoff 148): is the SpecificUnitCap overrun at s150 / s155 (check y: 新维和 3, 4) a second
        barracks? Counters, each as owned objects of s1 by template (counted(); whether one under construction counts is
        what the reading shows): 兵营 = retail AlliedBarracks, 复制兵营 = CNVAIBarracks (the player's copy), 新维和 =
        CNVNewPK, 标枪总数. Per second to 170 s after the wake (read from the watch rows).
        RESULTS (bench 2026-11-12, run CampAISkCapYb_mcp_1112_095845, PASS): 兵营 0 to s18, 1 from s19 to the end; 复制兵营 1
        throughout; 新维和 2 from s33 to s149, 3 at s150, 4 at s156; 标枪 6 at s150, 7-9 by s172. No barracks appears near the
        overrun: the AI has the same two (retail + copy) from s19 on."""
        NEW_PK, NEW_BARRACKS = 'CNVNewPK', 'CNVAIBarracks'
        t = Test()
        JAV = 'AlliedAntiVehicleInfantry'
        m.spawns.add(JAV)
        for tpl in ('AlliedBarracks', NEW_BARRACKS):
            try:
                m.spawns.add(tpl)
            except Exception:
                pass
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_AK_YBBar', '兵营', t, template='AlliedBarracks', player=s1)
        counted('CNV_AK_YBCopy', '复制兵营', t, template=NEW_BARRACKS, player=s1)
        counted('CNV_AK_YBNew', '新维和', t, template=NEW_PK, player=s1)
        counted('CNV_AK_YBJav', '标枪总数', t, template=JAV, player=s1)
        w = m.facts['wake at']
        t.expect += [('兵营', w + 140.0, 'ever>=', 1, w + 150.0)]
        t.bench = [('bench_watch', dict(seconds=w + 170.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def s(m):
        """RANDOM_UNIT percents and BuildState.Difficulty (aiskrand / aiskdiff: s1 owns, besides what it builds, a copied
        barracks that also builds CNVNewPK / CNVNewJav = Peacekeeper / Javelin under new ids). Totals of s1's new
        Peacekeepers, new Javelins, retail Peacekeepers and Javelins, to 150 s after the wake.
        Data's prediction (l4_buildstate.md 2: RANDOM 10000 when PercentLow < roll < PercentHigh, one roll in [0, 1) an
        evaluation): aiskrand -- 新维和 (0%..30%) wins about 3 evaluations in 10; 新标枪 ("30".."100", no '%') never if a
        bare number is read as itself (the engine model's _percent), about 7 in 10 if it is a percent. aiskdiff -- the
        HARD-only state never runs at MEDIUM: 新维和 0; the MEDIUM one does: 新标枪 >= 1 (FEWEST_UNIT, as aisknew2).

        RESULTS s (bench 2026-11-11, both PASS; runs CampAISkRandS_mcp_1111_223512, CampAISkDiffS_mcp_1111_223815):
          aiskrand: 新维和 1 s38, 4 s161; **新标枪 1 s27, 4 s167**; 维和 4, 标枪 7 beside (the retail barracks).
          Reading: a bare "30" is 30 % (the Percentage type), not 30 -- retail AlliedBarracksBuildState_RANDOM's bare
          0..100 are percents. The split 4 : 4 (30 : 70 predicted) is too few to tell more.
          aiskdiff: **新维和 0 to s169**; 新标枪 1 s27, 8 s167; 维和 5, 标枪 6.
          Reading: a build state hung at HARD only does not run at MEDIUM; Difficulty gates the state."""
        NEW_PK, NEW_JAV = 'CNVNewPK', 'CNVNewJav'      # missions/aiskirm_bench.py's (G5: no content import)
        t = Test()
        PK, JAV = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'
        for tpl in (PK, JAV):
            m.spawns.add(tpl)
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_AK_SPk', '新维和', t, template=NEW_PK, player=s1)
        counted('CNV_AK_SJav', '新标枪', t, template=NEW_JAV, player=s1)
        counted('CNV_AK_SRPk', '维和总数', t, template=PK, player=s1)
        counted('CNV_AK_SRJav', '标枪总数', t, template=JAV, player=s1)
        w = m.facts['wake at']
        t.expect += [('新标枪' if m.facts['difficulty gate'] else '新维和', w + 140.0, 'ever>=', 1, w + 150.0)]
        t.bench = [('bench_watch', dict(seconds=w + 154.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def z(m):
        """Does the AI build against the player's army (aiskvinf: the player owns 10 conscripts, aiskvveh: 10 Hammer
        tanks, idle behind its yard on the west bank; otherwise aiskirm)? Totals of s1's Peacekeepers, Javelin soldiers,
        Guardian tanks and Riptides, to 150 s after the wake. Data's prediction (l4_buildstate.md 1): 1AlliedBalanced
        at MEDIUM lists those in AlliedLandUnitBuildState as BEST_UNIT_EXPECTED (score = the expected efficiency against
        the enemy), so vs conscripts more Peacekeepers, vs tanks more Javelins (and Guardians once a war factory stands)
        than the other build -- beside the UnitBuilder's uniform draw (l4_unitbuilder.md)."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        names = (('AlliedAntiInfantryInfantry', 'CNV_AK_ZPk', '维和总数'), ('AlliedAntiVehicleInfantry', 'CNV_AK_ZJav', '标枪总数'),
                 ('AlliedAntiVehicleVehicleTech1', 'CNV_AK_ZGrd', '守护者总数'),
                 ('AlliedAntiInfantryVehicle', 'CNV_AK_ZRip', '激流总数'))     # four counter lines at most
        for tpl, counter, label in names:
            m.spawns.add(tpl)
            counted(counter, label, t, template=tpl, player=s1, most=16)
        w = m.facts['wake at']
        t.expect += [('标枪总数' if m.facts['player vehicles'] else '维和总数', w + 140.0, 'ever>=', 4, w + 150.0)]
        t.bench = [('bench_watch', dict(seconds=w + 154.0, every=1, sheet=False, lines=len(t.counters)))]
        return t
    # RESULTS z (bench 2026-11-11, work/logs/b128_counter.log, work/bench_results/aiskv*__z.json; wake ~s10):
    #   aiskvinf (10 conscripts): 维和 1 s32, 4 s60, 7 s164; **标枪 0 to s169**; 守护者 0; 激流 1 s111 .. 6 s165.
    #   aiskvveh (10 Hammers):    **维和 0 to s185**; 标枪 1 s29, 6 s57, 14 s185; 守护者 0; 激流 1 s112 .. 3 s133.
    #   Reading: the barracks builds only the counter -- no draw among its units (the unit builder's uniform pick would
    #   give ~1/3 Peacekeepers vs the tanks): BEST_UNIT_EXPECTED decides the barracks (l4_efficiency.md). (The first
    #   aiskvinf run expected a Javelin and FAILed on it; the expectation is now the counter's.)
    # RESULTS z, UnitBuilderOverallDefensivePreference (bench 2026-11-14, work/logs/b199_defpref*.log, aiskvd*__z.json):
    #   aiskvd9 (1000%) FAIL on the Javelin expectation: 维和 1 s30, 5 s52, 9 s75, 10 s134, 14 s196 (13 at s235);
    #     **标枪 0 to s150**, 1 s151, 3 s161, 5 s179, 7 s222; 守护者 0; 激流 1 s112, 4 s144, 10 s228.
    #     Prediction ("Javelins only, like the stock 25%") was WRONG: 1000% gives Peacekeepers first, Javelins only after s150.
    #   aiskvd0 (0%) PASS (third try; the first two builds died of a MemoryError while unpacking, not the personality):
    #     维和 0 to s169; 标枪 1 s29, 2 s35, 3 s40, 4 s46, 5 s52, 6 s58, 7 s134 .. 11 s167; 守护者 0; 激流 1 s112, 3 s133.
    #     So 0% builds like the stock 25% (Javelins only) and 1000% turns the barracks to Peacekeepers: the preference is
    #     not the candidate-health scale the model has (that keeps the ranking and makes 0% score nothing).


    def t(m):
        """Where does the opening's last 200 go (aiskvveh: six Javelins = 1800 of the PRODUCTION Deposit 2000)? z counts
        no dogs or engineers; this counts s1's Peacekeepers, Javelins, attack dogs and engineers to 150 s after the wake.
        The model (unit builder: a uniform draw among the barracks' units, the drawn one bought if it fits the account)
        spends it on a Peacekeeper or a dog (200 each; 5 of 6 seeds a Peacekeeper) about s58-s85; z's bench had no
        Peacekeeper. Prediction: one dog, no Peacekeeper -- the draw, not a rule; no dog either = the 200 stays."""
        tt = Test()
        s1 = m.player('s1')
        tt.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        names = (('AlliedAntiInfantryInfantry', 'CNV_AK_TPk', '维和总数'), ('AlliedAntiVehicleInfantry', 'CNV_AK_TJav', '标枪总数'),
                 ('AlliedScoutInfantry', 'CNV_AK_TDog', '警犬总数'), ('AlliedEngineer', 'CNV_AK_TEng', '工程师总数'))
        for tpl, counter, label in names:
            m.spawns.add(tpl)
            counted(counter, label, tt, template=tpl, player=s1, most=16)
        w = m.facts['wake at']
        tt.expect += [('警犬总数', w + 140.0, 'ever>=', 1, w + 150.0)]
        tt.bench = [('bench_watch', dict(seconds=w + 154.0, every=1, sheet=False, lines=len(tt.counters)))]
        return tt
    # RESULTS t (bench 2026-11-12, work/testbench/runs/CampAISkVVehT_mcp_1112_011517): PASS. 警犬 1 s23 (before the first
    #   Javelin, s29), 标枪 6 s57 .. 11 s166, 维和 0 to s168, 工程师 1 s144. The barracks' first unit is the unit builder's
    #   draw; the build states then take it (B handoff 142).


    JAV_OUT_AT = 100.0                 # mission second the named Javelin soldier is teleported out (e)


    def e(m):
        t = Test()
        PK, JAV = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'
        for tpl in (PK, JAV, RIPTIDE):
            m.spawns.add(tpl)
        s1 = m.player('s1')
        jav = m.role('ai jav').name
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 600.0)
        t.areas['CNV AI Yard 300'] = square(*m.site('east base'), 300.0)
        counted('CNV_AK_JavNear', '标枪近院', t, named=jav, area='CNV AI Yard 300')
        counted('CNV_AK_Total', '激流总数', t, template=RIPTIDE, player=s1)
        counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
        t.counters[1:3] = []                # the two Riptide counters work, they are not shown (four lines fit)
        t.counters.append(('CNV_AK_OutFrames', '出门帧'))
        counted('CNV_AK_PkHome', '维和在家', t, template=PK, area=AREA, player=s1)
        counted('CNV_AK_JavHome', '标枪在家', t, template=JAV, area=AREA, player=s1)
        t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                      Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                             [('SET_FLAG', 'Test Woke', 1)])]
        for n in range(1, 9):
            t.scripts.append(Script(f'Test - out {n}', [('COUNTER', 'CNV_AK_Total', 2, n), ('COUNTER', 'CNV_AK_Home', 0, n)],
                                    [('SET_FLAG', 'Test Out', 1)], once=False))
        t.scripts += [Script('Test - wait out', [('FLAG', 'Test Woke', 1), ('FLAG', 'Test Out', 0)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AK_OutFrames')], once=False),
                      Script('Test - jav timer', [], [('SET_MILLISECOND_TIMER', 'Test Jav Out', JAV_OUT_AT)]),
                      Script('Test - jav out', [('TIMER_EXPIRED', 'Test Jav Out')],
                             [('UNIT_TELEPORT_TO_WAYPOINT', jav, 'CNV AI Out')])]
        t.expect += [('标枪近院', 20.0, '>=', 0, 21.0)]            # weak: the readings exist
        t.bench = [('bench_watch', dict(seconds=174.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    UNKNOWN = 99                        # g / h: a team count shows this when no team of that name answered this frame
    POOL_MOST = 20
    PEAK_FROM = 110.0                   # m: mission second the pool peak latch starts (the eight leave ~s128-136)


    def _built(t, m):
        """我方建筑: how many of the player's yard / war factory / power plant are alive (0-3), as in a."""
        p1 = m.player('p1')
        t.counters.append(('CNV_AK_Built', '我方建筑'))
        t.scripts.append(Script('Test - built zero', [], [('SET_COUNTER', 'CNV_AK_Built', 0)], once=False))
        for i, tpl in enumerate(YOURS):
            m.spawns.add(tpl)
            t.scripts += [Script(f'Test - own {i}', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, p1, f'CNV_AK_Own{i}')],
                                 once=False),
                          Script(f'Test - built {i}', [('COUNTER', f'CNV_AK_Own{i}', 3, 1)],
                                 [('INCREMENT_COUNTER', 1, 'CNV_AK_Built')], once=False)]


    def _members(t, counter, label, team, most=POOL_MOST):
        """`team`'s member count (TEAM_COMPARE_NUM_MEMBERS ==), UNKNOWN when it is none of 0 .. most-1."""
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} unknown', [], [('SET_COUNTER', counter, UNKNOWN)], once=False))
        t.scripts += [Script(f'Test - {counter} {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                             [('SET_COUNTER', counter, n)], once=False) for n in range(most)]


    def _appearances(t, counter, n_counter, label):
        """How many times the team `counter` reads (_members) has appeared (99 -> a count), latched every frame."""
        seen = n_counter + 'S'
        t.counters.append((n_counter, label))
        t.scripts += [Script(f'Test - {n_counter} on', [('COUNTER', counter, 0, UNKNOWN), ('COUNTER', seen, 2, 0)],
                             [('INCREMENT_COUNTER', 1, n_counter), ('SET_COUNTER', seen, 1)], once=False),
                      Script(f'Test - {n_counter} off', [('COUNTER', counter, 2, UNKNOWN)], [('SET_COUNTER', seen, 0)],
                             once=False)]


    def _lifetime(t, counter, f_counter, label):
        """Frames the team `counter` reads has answered since it last appeared (reset to 0 when it appears, +1 every frame
        it answers, kept while it is gone): read while it shows 99, it is the last instance's whole life in frames."""
        seen = f_counter + 'S'
        t.counters.append((f_counter, label))
        t.scripts += [Script(f'Test - {f_counter} new', [('COUNTER', counter, 0, UNKNOWN), ('COUNTER', seen, 2, 0)],
                             [('SET_COUNTER', f_counter, 0), ('SET_COUNTER', seen, 1)], once=False),
                      Script(f'Test - {f_counter} tick', [('COUNTER', counter, 0, UNKNOWN)],
                             [('INCREMENT_COUNTER', 1, f_counter)], once=False),
                      Script(f'Test - {f_counter} off', [('COUNTER', counter, 2, UNKNOWN)], [('SET_COUNTER', seen, 0)],
                             once=False)]


    def _kind_members(t, counter, label, team, kind, most=POOL_MOST):
        """How many of `team`'s members have KindOf `kind` (TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF, tried from `most`
        down: the last that holds is n = count + 1); UNKNOWN when none holds (count >= most, or no such team)."""
        from model import kindof
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} unknown', [], [('SET_COUNTER', counter, UNKNOWN)], once=False))
        t.scripts += [Script(f'Test - {counter} <{n}', [('TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF', team, n, kindof(kind))],
                             [('SET_COUNTER', counter, n - 1)], once=False) for n in range(most, 0, -1)]


    def _teams(m, which):
        """g / h: AI team sizes read by name. The engine names a strategic state's team instances '%s_%s_%u_%u'
        (work/re/l4_states.md: state, a tactic string, two indices; retail maps query e.g. 'Player_2/AIState_J09_LandAttack_
        SimpleAttack_0_0'); the pool is 'defaultSkirmishTeam' + player (work/re/l4_states.md). Which tactic string (the Tactic id
        'Defense' / 'Attack' or its type 'StaticDefense' / 'DefenseAvoidanceAttack') is what g / h tell apart."""
        t = Test()
        for tpl in ARMY:
            m.spawns.add(tpl)
        s1 = m.player('s1')
        ai = m.map.AI_TEAMS                                     # missions/aiskirm_bench.AI_TEAMS
        pool = ai['pool']
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        if which == 'g':
            _kind_members(t, 'CNV_AK_Pool', '池兵', pool, 'CAN_ATTACK')
            _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
            _members(t, 'CNV_AK_DefI', '防御名', ai['defense id'])
            _sum(t, m, s1, 'CNV_AK_Army', '兵数', ARMY)
        elif which in ('i', 'j'):          # other instances of the same tactic type: '<state>_<type>_<a>_<b>'
            kind = 'attack type' if which == 'i' else 'defense type'
            word = '进攻' if which == 'i' else '防御'
            # labels in words: '进攻0_1'-style labels read back as '?' on the bench (2026-11-10)
            for idx, say in (('0_1', '二份'), ('1_0', '乙头'), ('0_2', '三份'), ('1_1', '乙二')):
                _members(t, f'CNV_AK_{which.upper()}{idx.replace("_", "")}', f'{word}{say}', ai[f'{kind} {idx}'])
        elif which == 'k':
            for key, ctr, say in (('overwhelm', 'Ovw', '压倒'), ('bal defense', 'BDef', '均防'),
                                  ('cleanup', 'Cln', '清扫'), ('emergency', 'Emg', '急防')):
                _members(t, f'CNV_AK_{ctr}', say, ai[key])
        elif which in ('l', 'inc'):
            for key, ctr, say in (('scout', 'Sct', '侦察'), ('scout 2', 'Sct2', '侦察乙'), ('escort', 'Esc', '护送')):
                _members(t, f'CNV_AK_{ctr}', say, ai[key])
            _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
        elif which == 'm':                 # does the defense team's eight pass through the pool on the way to Cleanup?
            _kind_members(t, 'CNV_AK_Pool', '池兵', pool, 'CAN_ATTACK')
            _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
            _members(t, 'CNV_AK_Cln', '清扫', ai['cleanup'])
            # 池峰: the most CAN_ATTACK pool members any single frame from PEAK_FROM s (scripts run every frame; the 1 s
            # sheet would miss a pool that holds the eight for under a second)
            t.counters.append(('CNV_AK_Peak', '池峰'))
            t.scripts.append(Script('Test - peak timer', [], [('SET_MILLISECOND_TIMER', 'Test Peak From', PEAK_FROM)]))
            t.scripts += [Script(f'Test - peak {n}', [('TIMER_EXPIRED', 'Test Peak From'), ('COUNTER', 'CNV_AK_Pool', 3, n),
                                                      ('COUNTER', 'CNV_AK_Peak', 0, n), ('COUNTER', 'CNV_AK_Pool', 0, UNKNOWN)],
                                 [('SET_COUNTER', 'CNV_AK_Peak', n)], once=False) for n in range(1, POOL_MOST)]
        elif which == 'n':                 # Cleanup full (14 at s161): does the next unit go to Cleanup _0_1 or to defense?
            _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
            _members(t, 'CNV_AK_Cln', '清扫', ai['cleanup'])
            _members(t, 'CNV_AK_Cln2', '清扫二', ai['cleanup 0_1'])
            _members(t, 'CNV_AK_Def2', '防御二', ai['defense type 0_1'])
        elif which == 'o':                 # units outside every team a name reads (a second Cleanup slot shares _0_0)
            _sum(t, m, s1, 'CNV_AK_Army', '兵数', ARMY[:3])
            _members(t, 'CNV_AK_Cln', '清扫', ai['cleanup'])
            _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
            _kind_members(t, 'CNV_AK_Pool', '池兵', pool, 'CAN_ATTACK')
        elif which == 'q':                 # is a gathering (not started) instance re-picked every SecondsTillTargetsExpire?
            for key, ctr, say, nsay in (('attack type', 'AtkT', '进攻型', '进攻次'), ('overwhelm', 'Ovw', '压倒', '压倒次')):
                _members(t, f'CNV_AK_{ctr}', say, ai[key])
                _appearances(t, f'CNV_AK_{ctr}', f'CNV_AK_{ctr}N', nsay)
        elif which == 'r':                 # how many frames does one gathering instance last (team made -> gone)?
            for key, ctr, say, fsay in (('attack type', 'AtkT', '进攻型', '进攻帧'), ('overwhelm', 'Ovw', '压倒', '压倒帧')):
                _members(t, f'CNV_AK_{ctr}', say, ai[key])
                _lifetime(t, f'CNV_AK_{ctr}', f'CNV_AK_{ctr}F', fsay)
        elif which in ('p', 'pr'):         # past the player's last building: do the attack teams end and hand back?
            _built(t, m)
            _members(t, 'CNV_AK_Cln', '清扫', ai['cleanup'])
            if which == 'p':
                _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
            else:                          # pr: does Cleanup ride its Riptides (UseTransports, the XSD default true)?
                m.ext = True               # team: lines -- where and when the riders get out
                counted('CNV_AK_In', '车内步兵', t, status=status('ENCLOSED'), player=s1)
            _sum(t, m, s1, 'CNV_AK_Army', '兵数', ARMY[:3])
        else:
            _members(t, 'CNV_AK_PoolAll', '池全', pool, most=40)
            _members(t, 'CNV_AK_Map', '地图队', f'{s1}/team{s1}')
            _members(t, 'CNV_AK_AtkT', '进攻型', ai['attack type'])
            _members(t, 'CNV_AK_AtkI', '进攻名', ai['attack id'])
        w = m.facts['wake at']
        t.expect += [(t.counters[0][1], w + 20.0, '>=', 0, w + 21.0)]      # weak: the readings exist
        t.bench = [('bench_watch', dict(seconds=w + {'n': 175.0, 'o': 175.0, 'p': 232.0, 'pr': 232.0, 'inc': 330.0}.get(which, 160.0), every=1, sheet=False,
                                        lines=len(t.counters)))]
        return t


    def g(m):
        """Pool CAN_ATTACK members / LandDefense_MEDIUM team by tactic type / by tactic id / army owned (as d)."""
        return _teams(m, 'g')


    def h(m):
        """Pool all members / the map team teamSoviet_1 / BalancedAttackGround_MEDIUM by tactic type / by tactic id."""
        return _teams(m, 'h')


    def i(m):
        """BalancedAttackGround_MEDIUM_DefenseAvoidanceAttack _0_1 / _1_0 / _0_2 / _1_1: who takes the defense team's 8."""
        return _teams(m, 'i')


    def j(m):
        """LandDefense_MEDIUM_StaticDefense _0_1 / _1_0 / _0_2 / _1_1: the defense team's other copies."""
        return _teams(m, 'j')


    def k(m):
        """_0_0 of the other MEDIUM land states: Overwhelm / BalancedDefense / BalancedCleanup / LandEmergencyDefense."""
        return _teams(m, 'k')


    def l(m):  # noqa: E743
        """AlliedScout _0_0 / _1_0 / EscortMCV _0_0 / LandDefense _0_0 (the time base: 8 -> 0 at ~s136)."""
        return _teams(m, 'l')


    def inc(m):
        """l run to s330 for ra3ext's inc: lines (IncomeAdvantage's input past its 90 s window: B 11-25)."""
        return _teams(m, 'inc')


    def m(mm):
        """Pool CAN_ATTACK members / LandDefense _0_0 / BalancedCleanup _0_0 / the pool's per-frame peak from PEAK_FROM s."""
        return _teams(mm, 'm')


    ORE_TARGET = (4278.8, 3093.3)       # et: the ore node the model's ClosestTechBuildingHeuristic picks (model fca219e)


    def et(m):
        """Where does AlliedCaptureTech_MEDIUM's Engineer tactic take its engineer, and does it capture? (line A round
        203). 工程队 = the team by its engine name (AlliedCaptureTech_MEDIUM_EngineerTactic_0_0), 油井 = OilDerricks s1 owns (the map's one, neutral, at niagara DERRICKS), 到油井 / 到矿点 =
        s1's engineers inside 250 of the derrick / 120 of ORE_TARGET. Two predictions: the model (fca219e) sends the engineer
        to the ore node ~s155 and captures nothing (its act is a no-op); the data (the state's TechBuildingShare reads
        the derrick, KindOf of the tech buildings) -- to the derrick, which turns s1's and the engineer is gone.
        MEASURED (bench 2026-11-13, head 7020cbfc, work/bench_results/aiskirm__et.json, PASS): s1-127 99 0 0 0 |
        s128-143 0 0 0 0 | s144-215 1 0 0 0 | s216-221 1 0 1 0 | s222 0 1 0 0 | s223-284 99 1 0 0 -- the derrick: the
        engineer reaches it s216, s1 owns it s222 and the team is gone that second; never at the ore node. The model
        (fca219e) got the team, not the target or the capture; the simulator now does both (the readings data)."""
        t = Test()
        for tpl in ARMY:
            m.spawns.add(tpl)
        s1 = m.player('s1')
        m.spawns |= {'AlliedEngineer', 'OilDerrick'}          # the scripts' contract: templates the counters name
        team = m.map.AI_TEAMS['capture tech']
        (dx, dy), = m.map.DERRICKS
        t.areas['Test Derrick'] = square(dx, dy, 250)
        t.areas['Test Ore'] = square(*ORE_TARGET, 120)      # small: the AI's base is ~600 away
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        _members(t, 'CNV_AK_ETeam', '工程队', team)
        counted('CNV_AK_EOil', '油井', t, template='OilDerrick', player=s1)
        counted('CNV_AK_EAtD', '到油井', t, template='AlliedEngineer', area='Test Derrick', player=s1)
        counted('CNV_AK_EAtO', '到矿点', t, template='AlliedEngineer', area='Test Ore', player=s1)
        w = m.facts['wake at']
        t.expect += [('工程队', w + 20.0, '>=', 0, w + 21.0)]      # weak: the readings exist
        t.bench = [('bench_watch', dict(seconds=w + 260.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    EP_X = [4400.0 - 200.0 * k for k in range(19)]      # ep: 4400 .. 800, west-of lines
    EP_Y = [3800.0 - 150.0 * k for k in range(10)]      # ep: 3800 .. 2450, north-of lines


    def ep(m):
        """Which way does the Engineer tactic's engineer go to the derrick, and from where? (line A round 235). The
        simulator (model 11ac6fc) walks it from the barracks (4067, 3562) north round the river's steep banks (y ~2840)
        and reaches 'Test Derrick' at s230; et's bench did it in 72 s (s144 -> s216), less than the straight line at 40.
        工程X = how many EP_X lines s1's westmost engineer stands west of (x ~ 4400 - 200 n), 工程Y = how many EP_Y
        lines its northmost stands north of (y ~ 3800 - 150 n), 到油井 / 油井 as et.
        PREDICTED (simulator, model 11ac6fc): X 2 s146, 3 s148, 4 s154, 5 s159 .. 18 s229, 19 s234; Y 2 -> 7 (north
        round the banks) -> 5; 到油井 s231, 油井 s237.
        MEASURED (bench 2026-11-14, CampAISkirmEp_mcp_1114_225826, readings read off the archived frames): 油井 到油井
        X Y = 0 0 0 0 to s143 | 0 0 4 3 s144-s222 | 1 0 0 0 from s223 -- the strips never move and 到油井 never
        lights, though the derrick turns s1's (et's bench: 到油井 s216). EXPLAINED (round 236, eb / es): the readings
        froze -- the engineer stands in 7 of these nested half-planes at once from the start; the same 31 areas as strips
        that do not overlap (es) read live. Kept as the record of that pitfall; read positions with es."""
        t = et(m)
        t.counters = [(c, lab) for c, lab in t.counters if lab in ('油井', '到油井')]
        t.expect = []                                                   # readings only (et's expectation reads 工程队)
        s1 = m.player('s1')
        for c, lab, lines, axis in (('CNV_AK_EpX', '工程X', EP_X, 0), ('CNV_AK_EpY', '工程Y', EP_Y, 1)):
            t.counters.append((c, lab))
            t.scripts.append(Script(f'Test - {c} zero', [], [('SET_COUNTER', c, 0)], once=False))
            for i, v in enumerate(lines, 1):
                area = f'Test Ep {c} {i}'
                t.areas[area] = ([(0.0, 0.0), (v, 0.0), (v, 5000.0), (0.0, 5000.0)] if axis == 0 else
                                 [(0.0, 0.0), (5000.0, 0.0), (5000.0, v), (0.0, v)])
                t.scripts.append(Script(f'Test - {c} {i}', [
                    ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, 'AlliedEngineer', area)],
                    [('INCREMENT_COUNTER', 1, c)], once=False))
        t.bench = [('bench_watch', dict(seconds=m.facts['wake at'] + 240.0, every=1, sheet=False,
                                        lines=len(t.counters)))]
        return t


    EB_X = [(3900.0, 5000.0), (3500.0, 3900.0), (2350.0, 3500.0), (0.0, 2350.0)]   # eb: bands 1-4, east to west
    EB_Y = [(3300.0, 5000.0), (2950.0, 3300.0), (0.0, 2950.0)]                     # eb: bands 1-3, south to north


    def eb(m):
        """ep on 8 trigger areas (line A round 236): did ep's readings freeze because of its 31 areas, or did the engineer
        not move? The derrick's square + 4 X bands + 3 Y bands, none overlapping on its axis: an engineer stands in at
        most 3 at once (ep's half-planes put it in 7 at the start). 工程X = the band (1 x >= 3900, 2 3500-3900, 3
        2350-3500 east of the river, 4 west of x 2350) of s1's westmost engineer, 工程Y = the band (1 y >= 3300, 2
        2950-3300, 3 north of y 2950) of its northmost, 0 if none; 到油井 / 油井 as et.
        PREDICTED (simulator, model 11ac6fc): X 1 s146, 2 s151, 3 s162, 4 s194; Y 1 -> 2 s160 -> 3 s178 -> 2 s218;
        到油井 s231, 油井 s237.
        MEASURED (bench 2026-11-14, work/logs/a236_eb_bench.keep.log, NOEXPECT): X 2 s145, 3 s149, 4 s180; Y 2 s145,
        3 s163-170, 2, 3 s183-205, 2; 到油井 s217-222, 油井 s223 -- the readings move: ep froze on its areas, the
        engineer walked. Same way round the north as the simulator, ~12 s ahead from s145 on (es has it finer)."""
        t = et(m)
        t.counters = [(c, lab) for c, lab in t.counters if lab in ('油井', '到油井')]
        del t.areas['Test Ore']
        t.scripts = [s for s in t.scripts if 'CNV_AK_EAtO' not in s.name and 'CNV_AK_ETeam' not in s.name]
        t.expect = []
        s1 = m.player('s1')
        for c, lab, bands, axis in (('CNV_AK_EbX', '工程X', EB_X, 0), ('CNV_AK_EbY', '工程Y', EB_Y, 1)):
            t.counters.append((c, lab))
            t.scripts.append(Script(f'Test - {c} zero', [], [('SET_COUNTER', c, 0)], once=False))
            for i, (lo, hi) in enumerate(bands, 1):       # in order: the last band that holds one wins
                area = f'Test Eb {c} {i}'
                t.areas[area] = ([(lo, 0.0), (hi, 0.0), (hi, 5000.0), (lo, 5000.0)] if axis == 0 else
                                 [(0.0, lo), (5000.0, lo), (5000.0, hi), (0.0, hi)])
                t.scripts.append(Script(f'Test - {c} {i}', [
                    ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, 'AlliedEngineer', area)],
                    [('SET_COUNTER', c, i)], once=False))
        t.bench = [('bench_watch', dict(seconds=m.facts['wake at'] + 240.0, every=1, sheet=False,
                                        lines=len(t.counters)))]
        return t


    def es(m):
        """ep's 31 trigger areas, but as strips that do not overlap (line A round 236): is it how many areas the map has,
        or how many one engineer stands in at once (ep: 7 at the start, eb: 3), that froze ep? The derrick's and the ore
        node's squares as et, 19 X strips (工程X = n: s1's westmost engineer in x 4400 - 200 n .. +200, 0 east of 4400)
        and 10 Y strips (工程Y = n: its northmost in y 3800 - 150 n .. +150, 0 south of 3800) -- the same numbers as
        ep's counts of lines, at most 3 areas at once.
        MEASURED (bench 2026-11-14, work/logs/a236_es_bench.log, NOEXPECT): live, so it is the areas one unit stands in
        at once, not the map's count (docs/engine/know-how.md). X 4 s144, 5 s145, 6 s150, 7 s155, 8 s162, 9 s167, 10 s172,
        11 s177, 12 s182, 13 s188, 14 s194, 15 s199, 16 s204, 17 s209, 18 s215, 19 s220 (~37/s west); Y 5 s145, 6 s159,
        7 s185-201, 6 s202, 5 s211; 到油井 s216-221, 油井 s222. So at s145 the engineer is at x ~3600, y < 3200 -- by
        aiskin0's barracks (rpb: the opening's first structure, s19, strips x11 y17 = 3600-3650, 3200-3250, south-west
        of the yard 3850,3400); the simulator's yard rings put the barracks at (4067, 3544), ~590 further along the
        same northern way: its 14 s late is the start, not the route or the speed (line A round 236)."""
        t = et(m)
        t.counters = [(c, lab) for c, lab in t.counters if lab in ('油井', '到油井')]
        t.expect = []
        s1 = m.player('s1')
        for c, lab, lines, axis, step in (('CNV_AK_EsX', '工程X', EP_X, 0, 200.0), ('CNV_AK_EsY', '工程Y', EP_Y, 1, 150.0)):
            t.counters.append((c, lab))
            t.scripts.append(Script(f'Test - {c} zero', [], [('SET_COUNTER', c, 0)], once=False))
            for i, v in enumerate(lines, 1):
                lo, hi, area = v - step, v, f'Test Es {c} {i}'
                t.areas[area] = ([(lo, 0.0), (hi, 0.0), (hi, 5000.0), (lo, 5000.0)] if axis == 0 else
                                 [(0.0, lo), (5000.0, lo), (5000.0, hi), (0.0, hi)])
                t.scripts.append(Script(f'Test - {c} {i}', [
                    ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, 'AlliedEngineer', area)],
                    [('SET_COUNTER', c, i)], once=False))
        assert len(t.areas) == 31
        t.bench = [('bench_watch', dict(seconds=m.facts['wake at'] + 240.0, every=1, sheet=False,
                                        lines=len(t.counters)))]
        return t


    def n(m):
        """LandDefense _0_0 / BalancedCleanup _0_0 / BalancedCleanup _0_1 / LandDefense _0_1 to s185: where the unit
        after Cleanup's 14th goes (the model: Cleanup _0_1; m saw one in defense at s166)."""
        return _teams(m, 'n')


    def o(m):
        """Army owned (no dogs) / BalancedCleanup _0_0 / LandDefense _0_0 / pool CAN_ATTACK to s185: the difference is
        held by teams no name reads -- do Cleanup's other slots (same name _0_0) take the units after the 14th?"""
        return _teams(m, 'o')


    def q(m):
        """BalancedAttackGround _0_0 / its appearances / BalancedAttackOverwhelm _0_0 / its appearances to s170: is a
        not-started instance re-picked every SecondsTillTargetsExpire (work/re/l4_states.md 1.2; Base writes 5 s; aiskexp writes 12)?"""
        return _teams(m, 'q')


    def r(m):
        """BalancedAttackGround _0_0 / frames its last instance lived / Overwhelm _0_0 / the same: does a gathering
        instance last exactly SecondsTillTargetsExpire x 15 = 75 frames from its team's first frame (the model's rule)?"""
        return _teams(m, 'r')


    def p(m):
        """我方建筑 / BalancedCleanup _0_0 / LandDefense _0_0 / army owned (no dogs) to ~s240: when the player's last
        building dies, do the attack teams end at once and hand their units back to the defense team (the model, ~197 s
        after the wake: AlliedScout target gone -> DISBAND, both Cleanups 'rampage: nobody left', LandDefense takes them)?"""
        return _teams(m, 'p')


    def pr(m):
        """p with 车内步兵 (s1's objects carrying ENCLOSED) for 防御型: does the Cleanup team board its Riptides first?"""
        return _teams(m, 'pr')


    def pt(m):
        """Which name does PLAYER_IS_HUMAN_OR_AI_PERSONALITY match (aiskpt: s1's personality has the id CNVPtId and the
        PersonalityType CNVPtType; aiskpti: the same id, no PersonalityType written)? 人格位 = the sum, every frame, of
        1 (s1, CNVPtType), 2 (s1, CNVPtId), 4 (s1, 1AlliedBalanced = the parent's id and type), 8 (Player_1, Human);
        to 30 s after the wake.
        Data's prediction (D59, work/re/d59_b_fields.md 1: the condition compares the AI's PersonalityType by name; what
        a child that writes none holds was not read): aiskpt 1 + 8 = 9 (the simulator, comparing the side's asset id,
        says 2 + 8 = 10); aiskpti 8 if an unwritten type is empty, 4 + 8 if it inherits, 2 + 8 if it falls back to the
        id. Before the wake the bits may differ (Lib_Skirmish_Setup hands s1 to its AI at frame 0).

        RESULTS pt (bench 2026-11-12, both PASS; runs work/testbench/runs/CampAISkPtPt_mcp_1112_115516,
          CampAISkPtIPt_mcp_1112_115743): aiskpt **人格位 10 every second s1-s41**, aiskpti **10 s1-s42** -- (s1, CNVPtId)
          and (Player_1, Human) hold, (s1, CNVPtType) and (s1, 1AlliedBalanced) never. Reading: the condition matches the
          personality's asset id (the side's aiPersonality), not its PersonalityType (D59's reading does not hold), and
          whether PersonalityType is written changes nothing; the simulator (comparing the id) gives 10 on both."""
        t = Test()
        s1, p1 = m.player('s1'), m.player('p1')
        counter = 'CNV_AK_PtBits'
        t.counters.append((counter, '人格位'))
        parts = [(1, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, 'CNVPtType')),
                 (2, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, 'CNVPtId')),
                 (4, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, '1AlliedBalanced')),
                 (8, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', p1, 'Human'))]
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', wt, counter)], once=False)
                      for k, (wt, c) in enumerate(parts)]
        w = m.facts['wake at']
        t.expect += [('人格位', w + 5.0, '>=', 8)]          # Player_1 is Human the whole run (scripts1 cond)
        t.bench = [('bench_watch', dict(seconds=w + 30.0, every=1, sheet=False, lines=len(t.counters)))]
        return t

    SD_BITS = (('CNVSideX', 1), ('HuntPersonality', 2), ('1AlliedBalanced', 4), ('1JapanBalanced', 16),
               ('2JapanAmbushDivision', 32), ('3JapanFleetCommand', 64), ('2JapanMechaWarfare', 128))


    def sd(m):
        """Which personality s1's AI ends up with (work/re/d123_side.md 3; PLAYER_IS_HUMAN_OR_AI_PERSONALITY matches the
        asset id, check pt). 人格位 = the sum of 1 CNVSideX, 2 HuntPersonality, 4 1AlliedBalanced, 8 (Player_1, Human),
        16 / 32 / 64 / 128 the four Japanese skirmish personalities; to 30 s after the wake.
        Data's prediction (D123): aisksd1 (CNVSideX: Side Soviet, SkirmishPersonality false; s1 Japan) 1 + 8 = 9 -- a
        closed gate takes the personality whatever its Side; aisksd2 (the same, SkirmishPersonality true) no 1: a random
        library personality whose Side holds Japan (a Japanese bit, or Hunt); aisksd4 (no aiPersonality, a campaign
        mode) 2 + 8 = 10 -- HuntPersonality (the simulator's fallback is 1AlliedBalanced: 4 + 8)."""
        t = Test()
        s1, p1 = m.player('s1'), m.player('p1')
        counter = 'CNV_AK_SdBits'
        t.counters.append((counter, '人格位'))
        parts = [(wt, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, pid)) for pid, wt in SD_BITS]
        parts.append((8, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', p1, 'Human')))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', wt, counter)], once=False)
                      for k, (wt, c) in enumerate(parts)]
        w = m.facts['wake at']
        t.expect += [('人格位', w + 5.0, '>=', 8)]
        t.bench = [('bench_watch', dict(seconds=w + 30.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def mt(m):
        """When does s1 start its first AlliedTechStructure (aiskmt: its own ConstantHeuristic state's one entry, TECH
        MinTime 150 s ForceTime 151 s; aiskmto: MinTime 250 s ForceTime 151 s; s1 owns an airfield and a refinery from
        s0, the tech building's prerequisites)? 科技楼 = how many s1 owns; 科技帧 = frames from the wake (+30) while it
        owns none (stops at the first); 电厂 = power plants owned (3 placed); AI钱. To 300 s after the wake.
        First run (2026-11-12, without the 3 plants, run CampAISkMTMt_mcp_1112_122317): no tech building to s322 -- the
        opening + the airfield + the refinery draw 275 against 250, so the power gate held it (the plants added since).
        Second run (with the 3 plants, run CampAISkMTMt_mcp_1112_123106, PASS): **still no tech building to s377**
        (~365 s after the wake, past ForceTime 151); 电厂 3 -> 4 at s29 -> 5 at s80 (the opening's two), money 50000 ->
        8900 on units. Power is not what holds it: some other gate (B handoff 154's table). aiskmto not run yet.
        aiskmtc (CONSTANT 300 tower, run CampAISkMTCMt_mcp_1112_125012): towers at s148 / s172 / s258; aiskmtt (the same
        tower TECH MinTime 200 ForceTime 201, run CampAISkMTTMt_mcp_1112_125641): s149 / s169 / s265 -- the same, so the
        towers are the inherited stock state's, not this entry's: neither run tells (B handoff 155; the yard's gate is
        asked of D). A rerun needs a building no stock state builds.
        Data's prediction (D59, work/re/d59_b_fields.md 3): aiskmt forced (200) from t > 151 s after the wake -> 科技帧
        stops at ~151 x 15 (plus the yard's queue: the opening may still hold it); aiskmto: if t < MinTime is tested
        first, ~250 s; if ForceTime first, ~151 s as aiskmt. The stock tech state (MinTime 360 s) cannot come first. The
        simulator scores no TECH entry: none in either.
        aiskmt0 (TECH MinTime 0 ForceTime 1, three more plants = 6, D82 G1 + G2 in one run; bench 11-12
        work/bench_results/aiskmt0__mt.json, PASS): 科技帧 stops at 2256 (~150 s after the wake), 科技楼 1 by s177, money
        50000 -> ~9800 by s376 -- the TECH entry does build here. G1 / G2 not yet split (next: 0 / 1 with 3 plants).
        aiskmt03 (TECH 0 / 1, the three plants only; bench 11-12 work/bench_results/aiskmt03__mt.json, PASS): 科技帧
        stops at 2256 again, 科技楼 1 at s227 (电厂 3 -> 5 by s102) -- the very frame of aiskmt0: power is not the gate
        (G1 no). aiskmt2 (TECH 200 / 201, six plants; aiskmt2__mt.json, PASS): no tech building to s367 (科技帧 4721,
        ~315 s after the wake) -- MinTime 200 is not "200 s after the wake" (G2: the evaluator's clock or MinTime's unit
        differs; next MinTime 20 / 21: ~150 s -> seconds, ~300 s -> MinTime counted x15).
        aiskmt20 (TECH 20 / 22, six plants, watched 600 s; bench 11-12 aiskmt20__mt.json, PASS; 20 / 21 compiled a map
        stream the game crashed on, see the build list): 科技帧 stops at 2256 again, 科技楼 1 at s158 -- the very
        frame of 0 / 1 (MinTime x15 = 300 s is out). MinTime <= 20 all start at f2256, 150 / 200 never: as if the
        entry were judged once, near f2256, and a t < MinTime then never came back (next: 140 / 142 against 160 / 162).
        aiskmt14 / aiskmt16 (140 / 142, 160 / 162, six plants, 600 s; aiskmt14__mt.json / aiskmt16__mt.json, PASS): both
        stop at 科技帧 5857 (3601 frames ~ 240 s after 2256). aiskmt15 (150 / 152) and aiskmt40 (400 / 402), six plants
        (bench 11-13 aiskmt15__mt.json / aiskmt40__mt.json, PASS): BOTH stop at 5857 too, though 5857 frames after the
        wake is ~390 s < 400. So the TECH entry starts at one of two frames, 2256 (MinTime <= 20) or 5857 (140 .. 400);
        a gate "seconds since the wake >= MinTime" fits neither 140 (no at 2256, ~150 s) nor 400 (yes at 5857, ~390 s).
        aiskmt99 (1000 / 1002, six plants; aiskmt99__mt.json, PASS): 5857 again, 科技楼 1 -- the second look (~240 s
        after the first) builds whatever MinTime says (INFERRED: MinTime is checked at the first look only, or that
        later look is a path that does not read it). Between 20 and 140 the first-look threshold is not measured."""
        t = Test()
        s1 = m.player('s1')
        if m.facts['min time'] is None and m.facts.get('const') == 'AlliedTechStructure':   # aiskmtk: CONSTANT tech
            _sum(t, m, s1, 'CNV_AK_Tech', '科技楼', ('AlliedTechStructure',))
        elif m.facts['build'] != 'AlliedTechStructure' or m.facts['min time'] is None:   # aiskmtc / aiskmtt: the tower
            _sum(t, m, s1, 'CNV_AK_Tech', '塔', ('AlliedBaseDefense',))
        else:
            _sum(t, m, s1, 'CNV_AK_Tech', '科技楼', ('AlliedTechStructure',))
        _sum(t, m, s1, 'CNV_AK_Pow', '电厂', ('AlliedPowerPlant',))
        t.counters.append(('CNV_AK_Money', 'AI钱'))
        t.counters.append(('CNV_AK_TechF', '科技帧'))
        t.scripts += [Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AK_Money')], once=False),
                      Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                      Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                             [('SET_FLAG', 'Test Woke', 1)]),
                      Script('Test - tech frames', [('FLAG', 'Test Woke', 1), ('COUNTER', 'CNV_AK_Tech', 0, 1)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AK_TechF')], once=False)]
        w = m.facts['wake at']
        t.expect += [('电厂', w + 5.0, '>=', 3)]
        t.bench = [('bench_watch', dict(seconds=w + m.facts.get('mt secs', 300.0), every=1, sheet=False,
                                        lines=len(t.counters)))]
        return t


    WEST = 'CNV AI West Area'
    PK = 'AlliedAntiInfantryInfantry'


    def fm(m):
        """aiskfon / aiskfof (the global AIData overridden in the map stream, UseFormations true / false; aiskad's canary
        first): the first attack team (2 Riptides + 3 Peacekeepers, check a / c) leaving home and reaching the player's
        base. 激流在家 = s1's inside 600 around the east base, 激流到 / 维和到 = inside 600 around the player's yard, 矿车 =
        s1's AlliedMiner (维和在家 until 11-26; aiskga's Gatherer canary); 1-s rows to 250 s after the wake: who leaves and who arrives in which second (the team's spread in time).
        aiskad's canary: the map-stream copy of AIData did not take (11-12, CampAISkADA_mcp_1112_130959 read as stock);
        spliced into the global stream (missions/aiskirm_bench.AIDataPack) it does -- Optimization_NumTeamsToRecruit 0
        (11-25, CampAISkADA_mcp_1125_233101): 13 Riptides made, none leaves (出门帧 never stops, to 5254), the
        player's 3 buildings stand to s355 (stock: first out at 1992, gone s209-s231). aiskfon PASS through the same
        pack (CampAISkFOnFm_mcp_1125_233236). aiskfof (UseFormations false) and aiskgf (SkirmishGroupFudgeValue 200)
        read as aiskfon shifted by a start jitter of up to 10 s (11-26). aiskna (the nine unread fields at extremes, all
        nine seen changed in the built global.bin) reads second for second as aiskfon run beside it, both PASS
        (CampAISkNAFm_mcp_1126_015445 / CampAISkFOnFm_mcp_1126_015604). aiskmrd (MaxRecruitDistance 1) and aiskts
        (TeamSeconds 600) read the same too (11-26): neither reaches the skirmish team maker. aiskn1 / aiskn10
        (NumTeamsToRecruit 1 / 10, both with the teams host; CampAISkN1Fm_mcp_1126_042022 / CampAISkN10Fm_mcp_1126_041859,
        up to 12 teams logged a sample): the first LandDefense team active at f417 / f389, HarvesterController's at f857 / f821
        -- the cap of 1 slows each team's turn; the counters differ by the draws (one run each), no reading yet."""
        t = Test()
        m.spawns.add(RIPTIDE)
        m.spawns.add(PK)
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 600.0)
        t.areas[WEST] = square(*m.site('base yard'), 600.0)
        counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
        m.spawns.add('AlliedMiner')
        counted('CNV_AK_Miner', '矿车', t, template='AlliedMiner', player=s1)
        counted('CNV_AK_West', '激流到', t, template=RIPTIDE, area=WEST, player=s1)
        counted('CNV_AK_PkWest', '维和到', t, template=PK, area=WEST, player=s1)
        w = m.facts['wake at']
        t.expect += [('激流在家', w + 150.0, 'ever>=', 1, w + 250.0)]
        t.bench = [('bench_watch', dict(seconds=w + 250.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    UC_UNITS = ('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', DOG, 'AlliedEngineer', RIPTIDE,
                'AlliedAntiInfantryVehicle', 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiAirVehicleTech1',
                'AlliedAntiStructureVehicle', 'AlliedAntiVehicleVehicleTech3', 'AlliedFighterAircraft',
                'AlliedAntiGroundAircraft', 'AlliedMCV')


    def uc(m):
        """UnitCap (aiskuc: 1AlliedBalanced + UnitCap Cap 3 MEDIUM and Cap 1 EASY HARD BRUTAL; the bench plays MEDIUM):
        兵数 = s1's units but miners (the barracks' four, Riptides, IFV, Guardian, AA, Athena, Mirage, two jets, MCV), 矿车 =
        AlliedMiner, 建筑数 (yard, power, barracks, refinery, war factory, towers), to 200 s after the wake. Engine: the
        unit builder and the build states' unit entries stop while the AI owns strictly more units than the smallest Cap
        whose difficulty matches (3); stock aiskirm c has 8 infantry ~52 s after the wake. Tells apart: the count takes in
        structures (no unit ever), miners (兵数 + 矿车 stops at 4), neither (兵数 stops at 4), or the EASY/HARD line (2)."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        _sum(t, m, s1, 'CNV_AK_UcArmy', '兵数', UC_UNITS, cap=12)
        _sum(t, m, s1, 'CNV_AK_UcMiner', '矿车', ('AlliedMiner',), cap=8)
        _sum(t, m, s1, 'CNV_AK_UcBlt', '建筑数', BUILDINGS + TOWERS, cap=12)
        w = m.facts['wake at']
        cap = m.facts['unit cap']
        if cap == 3:
            t.expect += [('兵数', w + 5.0, '<=', 5, w + 200.0), ('建筑数', w + 150.0, 'ever>=', 6, w + 200.0)]
        else:                                # aiskuc7 (D 124 U1): only to s110, before the late overshoot
            t.expect += [('兵数', w + 5.0, '<=', cap + 1, w + 100.0), ('兵数', w + 30.0, 'ever>=', 4, w + 100.0)]
        t.bench = [('bench_watch', dict(seconds=w + 204.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def ucn(m):
        """UnitCap on the build states' unit entries (aiskucn, D round 124 U2: aisknew2 -- a ConstantHeuristic state
        listing CNVNewPK FEWEST_UNIT -- plus UnitCap Cap 3 MEDIUM in that personality; no SpecificUnitCap). 兵数 = UC_UNITS
        + CNVNewPK, 新维和, 矿车, 建筑数, to 200 s after the wake. Engine (work/re d124_unitcap.md 1, read): the build
        state's order checks UnitCap after the money, units only -> 新维和 stops with the rest at 兵数 + 矿车 = 4; aisknew2
        (no cap) had 9 新维和 by s167. The model before D 124 let the build state's units through."""
        NEW_PK = 'CNVNewPK'                  # missions/aiskirm_bench.py's (G5: no content import)
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        _sum(t, m, s1, 'CNV_AK_UnArmy', '兵数', UC_UNITS + (NEW_PK,), cap=12)
        counted('CNV_AK_UnNew', '新维和', t, template=NEW_PK, player=s1)
        _sum(t, m, s1, 'CNV_AK_UnMiner', '矿车', ('AlliedMiner',), cap=8)
        _sum(t, m, s1, 'CNV_AK_UnBlt', '建筑数', BUILDINGS + TOWERS, cap=12)
        w = m.facts['wake at']
        t.expect += [('兵数', w + 5.0, '<=', 5, w + 100.0), ('新维和', w + 30.0, 'ever>=', 1, w + 100.0)]
        t.bench = [('bench_watch', dict(seconds=w + 204.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def ib(m):
        """One run for a batch of fields read as acting nowhere (aiskinb: 1AlliedBalanced with seven of them at extreme
        values, missions/aiskirm_bench.py INERT) against stock aiskirm: AI钱 every frame, 建筑码 as x, 兵数 as uc, 我方建筑
        as a (the player's yard / war factory / power plant still alive: the attack's timing and targets), to 230 s after
        the wake. The same readings to the second as aiskirm ib = none of the seven acts here."""
        t = Test()
        s1, p1 = m.player('s1'), m.player('p1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        t.counters.append(('CNV_AK_Money', 'AI钱'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AK_Money')], once=False))
        _sum(t, m, s1, 'CNV_AK_IbKind', '建筑码', KINDS, weights=(1, 10, 100, 1000), cap=9)
        _sum(t, m, s1, 'CNV_AK_IbArmy', '兵数', UC_UNITS, cap=16)
        t.counters.append(('CNV_AK_IbYours', '我方建筑'))
        t.scripts.append(Script('Test - yours zero', [], [('SET_COUNTER', 'CNV_AK_IbYours', 0)], once=False))
        for i, tpl in enumerate(YOURS):
            m.spawns.add(tpl)
            t.scripts += [Script(f'Test - yours own {i}', [],
                                 [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, p1, f'CNV_AK_IbOwn{i}')], once=False),
                          Script(f'Test - yours {i}', [('COUNTER', f'CNV_AK_IbOwn{i}', 3, 1)],
                                 [('INCREMENT_COUNTER', 1, 'CNV_AK_IbYours')], once=False)]
        w = m.facts['wake at']
        t.expect += [('建筑码', w + 100.0, 'ever>=', 1, w + 230.0)]
        t.bench = [('bench_watch', dict(seconds=w + 234.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    ORE = (('东矿', (4225.0, 3040.0)), ('东北矿', (3400.0, 1300.0)), ('西南矿', (1177.0, 3797.0)),
           ('北矿', (2127.0, 1113.0)), ('西矿', (950.0, 1985.0)))   # the map's five ore groups (niagara, measured)
    ORE_HALF = 600.0                      # half the square counted around a group (the groups are >= ~1280 apart)


    def rp(m):
        """Where s1's refineries stand (B round 186: RefineryPlacement's far rings gave a third refinery, aiskinp ib --
        which of StartDistanceDelta 1000 / NumberOfIncreaseTicksBeforeGivingUp 0 does it, and at which ore). 建筑码 as
        ib; 矿区码 = refineries in a square around each ore group, 东 x1 + 东北 x10 + 西南 x100 + 北 x1000 (each to 3);
        西矿 = the player's own group; AI钱 every frame. To 230 s after the wake."""
        t = Test()
        s1, p1 = m.player('s1'), m.player('p1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        _sum(t, m, s1, 'CNV_AK_RpKind', '建筑码', KINDS, weights=(1, 10, 100, 1000), cap=9)
        m.spawns.add('AlliedRefinery')
        for c, lab, groups in (('CNV_AK_RpOre', '矿区码', ORE[:4]), ('CNV_AK_RpWest', '西矿', ORE[4:])):
            t.counters.append((c, lab))
            t.scripts.append(Script(f'Test - {c} zero', [], [('SET_COUNTER', c, 0)], once=False))
            for i, (name, (x, y)) in enumerate(groups):
                area = f'Test Ore {c} {i}'
                t.areas[area] = square(x, y, ORE_HALF)
                for n in range(1, 4):
                    t.scripts.append(Script(f'Test - {c} {i} >= {n}', [
                        ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, n, 'AlliedRefinery', area)],
                        [('INCREMENT_COUNTER', 10 ** i, c)], once=False))
        t.counters.append(('CNV_AK_Money', 'AI钱'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AK_Money')], once=False))
        w = m.facts['wake at']
        t.expect += [('建筑码', w + 100.0, 'ever>=', 1, w + 230.0)]
        t.bench = [('bench_watch', dict(seconds=w + 234.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    RPX_X = (3100.0, 4900.0)             # rpx: the strips cover the east field and the AI yard's rings
    RPX_Y = (2400.0, 4100.0)
    RPX_STEP = 50.0


    def rpx(m):
        """rp plus where each of s1's refineries stands (B round 188: D136 section 5 reads a fixed default spot per ore
        node, then rings in +-33.75 degrees of the node's facing; the bench had only the +-600 squares). 矿场X / 矿场Y =
        the sum over s1's refineries of their 50-wide strip's number (strip 1 = x RPX_X[0]..+50, y likewise), so the step
        a new refinery adds is its strip: x = RPX_X[0] + 50 x (step - 1) .. +50. Refineries come one at a time."""
        t = rp(m)
        t.counters = [(c, lab) for c, lab in t.counters if lab in ('建筑码', '矿区码')]   # four lines fit on the bench
        _strips(t, m, ('AlliedRefinery',), (('CNV_AK_RpX', '矿场X'), ('CNV_AK_RpY', '矿场Y')))
        return t


    def _strips(t, m, templates, counters):
        """矿场X / 矿场Y-style strip sums of s1's `templates` (rpx's 50-wide strips; up to 3 of a template a strip)."""
        s1 = m.player('s1')
        for (c, lab), (lo, hi), axis in zip(counters, (RPX_X, RPX_Y), (0, 1)):
            t.counters.append((c, lab))
            t.scripts.append(Script(f'Test - {c} zero', [], [('SET_COUNTER', c, 0)], once=False))
            other = RPX_Y if axis == 0 else RPX_X
            for i in range(1, int((hi - lo) / RPX_STEP) + 1):
                a0, a1 = lo + RPX_STEP * (i - 1), lo + RPX_STEP * i
                area = f'Test Strip {c} {i}'
                t.areas[area] = ([(a0, other[0]), (a1, other[0]), (a1, other[1]), (a0, other[1])] if axis == 0 else
                                 [(other[0], a0), (other[1], a0), (other[1], a1), (other[0], a1)])
                for tpl in templates:
                    m.spawns.add(tpl)
                    for n in range(1, 4):
                        t.scripts.append(Script(f'Test - {c} {i} {tpl} >= {n}', [
                            ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, n, tpl, area)],
                            [('INCREMENT_COUNTER', i, c)], once=False))
        t.bench = [('bench_watch', dict(seconds=m.facts['wake at'] + 234.0, every=1, sheet=False,
                                        lines=len(t.counters)))]


    def rpb(m):
        """Where s1's other structures stand (B190, F1: is a refinery that finds no spot by its node put where the yard
        puts everything else?): 建筑码 as rp, 矿区码, 其他X / 其他Y = rpx's strip sums over s1's power plants, barracks and
        war factories (建筑码 says which kind each step is). Read beside rpx of the same build.
        RESULTS (bench 2026-11-14, B190, all PASS; work/bench_results/<build>__rpx.json / __rpb.json):
          aiskirmr rpx (east nodes facing pi): refineries s49 x17 y15, s68 x19 y17, no third to s264 (aiskirm: x26 y9,
            x28 y11) -- the mirror: each node's facing - 3 pi / 16.
          aiskin0r rpx = aiskin0 rpx to the second: x27 y18, x16 y8, x27 y25, x9 y10, x16 y12 (s49/69/148/189/223).
          rpb steps (power s19, barracks s28, power s79, war factory s99, power s159/169, ...): aiskin0 x11 y17, x17 y15,
            x14 y26, x13 y15, x18 y26, x19 y17; aiskin0r x11 y17, x13 y15, x21 y20, x9 y21, x19 y17, x11 y24."""
        t = rp(m)
        t.counters = [(c, lab) for c, lab in t.counters if lab in ('建筑码', '矿区码')]
        _strips(t, m, KINDS[:1] + KINDS[2:], (('CNV_AK_RbX', '其他X'), ('CNV_AK_RbY', '其他Y')))
        return t


    CHECKS = {'aiskirm': {'a': a, 'b': b, 'c': c, 'd': d, 'g': g, 'h': h, 'i': i, 'j': j, 'k': k, 'l': l, 'm': m,
                          'n': n, 'o': o, 'p': p, 'pr': pr, 'q': q, 'r': r, 'u': u, 'x': x, 'et': et, 'ep': ep, 'eb': eb, 'es': es, 'ib': ib, 'rp': rp, 'rpx': rpx},
              'aiskinb': {'ib': ib},
              'aiskinc': {'ib': ib},
              'aiskind': {'ib': ib},
              'aiskine': {'ib': ib},
              'aiskinp': {'ib': ib, 'rp': rp},
              'aiskin1': {'rp': rp, 'rpx': rpx},
              'aiskin0': {'rp': rp, 'rpx': rpx, 'rpb': rpb},
              'aiskin0r': {'rpx': rpx, 'rpb': rpb},
              'acbr0': {'rpb': rpb, 'rpx': rpx}, 'acbr1': {'rpb': rpb, 'rpx': rpx},   # B213 CanBuildInAlliedBuildRadii
              'aiskirmr': {'rpx': rpx},
              'aiskst40': {'rpx': rpx}, 'aiskst20': {'rpx': rpx}, 'aiskpnw': {'rpx': rpx}, 'aiskpnp': {'rpx': rpx},   # B192: StartDistanceDelta -40 / -20
              'aiskins': {'ib': ib},
              'aiskmtp': {'mt': mt},
              'aiskirmc': {'l': l, 'm': m, 'u': u},  # opt-in carrier diagnostic; stock aiskirm stays unchanged
              'aiskxn': {'l': l}, 'aiskxo': {'l': l, 'inc': inc},  # D 105: which half of the carrier moves the scout team
              'aiskexp': {'q': q},
              'aiskmod': {'u': u},
              'aiskuc': {'uc': uc},
              'aiskuc7': {'uc': uc},
              'aiskucn': {'ucn': ucn},
              'aiskacp': {'v': v},
              'aiskacd': {'v': v},
              'aiskirmnl': {'g': g, 'h': h},
              'aiskjav': {'e': e},
              'aiskirmlow': {'d': d, 'f': f, 'w': w},
              'aiskirm20': {'d': d},
              'aiskpw0': {'x': x},
              'aiskpw3': {'x': x},
              'aisknew': {'y': y},
              'aisknew2': {'y': y},
              'aiskcap': {'y': y, 'yb': yb},
              'aiskblkn': {'y': y},
              'aiskblkf': {'y': y},
              'aiskblkr': {'y': y},
              'aiskoff': {'y': y},
              'aiskcu': {'yc': yc, 'ycm': ycm},
              'aiskcs': {'yc': yc, 'ycm': ycm},
              'aiskcu3': {'ycm': ycm},
              'aiskpt': {'pt': pt},
              'aiskpti': {'pt': pt},
              'aisksd1': {'sd': sd},
              'aisksd2': {'sd': sd},
              'aisksd4': {'sd': sd},
              'aiskmt': {'mt': mt},
              'aiskmto': {'mt': mt},
              'aiskmt0': {'mt': mt},
              'aiskmt03': {'mt': mt},
              'aiskmt2': {'mt': mt},
              'aiskmt20': {'mt': mt},
              'aiskmt14': {'mt': mt},
              'aiskmt16': {'mt': mt},
              'aiskmt15': {'mt': mt},
              'aiskmt40': {'mt': mt},
              'aiskmt99': {'mt': mt},
              'aiskmtc': {'mt': mt},
              'aiskmtt': {'mt': mt},
              'aiskmtk': {'mt': mt},
              'aiskmtl': {'mt': mt},
              'aiskrand': {'s': s},
              'aiskdiff': {'s': s},
              'aiskvinf': {'z': z, 't': t},
              'aiskvveh': {'z': z, 't': t},
              'aiskvd0': {'z': z},
              'aiskvd9': {'z': z},
              'aiskad': {'a': a},
              'aiskfon': {'fm': fm},
              'aiskfof': {'fm': fm},
              'aiskna': {'fm': fm},
              'aiskmrd': {'fm': fm},
              'aiskts': {'fm': fm},
              'aiskgf': {'fm': fm},
              'aiskga': {'fm': fm},
              'aiskew': {'fm': fm},
              'aiskn1': {'fm': fm},
              'aiskn10': {'fm': fm}}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a, fm=fm, y=y, yc=yc))


def engine_aislush():
    """AccountShare.Account=SLUSH_FUND: opening plants at s40, isolated share swap.

    Prediction before measurement: 100% slush -> 2 plants; 0% -> 0 (INFERRED).
    The PRODUCTION share is the complement; no deposit is made. The test measures
    the opening's sensitivity, not account balances. See work/re/c_slush_report.md.
    """
    f = engine_aitower()["shared"].f
    from parts import Script, Test, counted


    def a(m):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_Slush_Plants', '电厂', t, template='AlliedPowerPlant', player=m.player('s1'))
        t.expect = [('电厂', 40, '==', m.facts['plants'], 41)]
        t.bench = [('bench_watch', dict(seconds=49, every=1, sheet=False, lines=1))]
        return t


    CHECKS = {build: {'a': a} for build in ('aislush100', 'aislush0')}


    def d(m):
        """Round two, same income host: slush-only cannot fund ordinary defense."""
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_Slush_Defense', '炮塔', t, template=m.cnv_turret, player=m.player('s1'))
        t.expect = [('炮塔', 60, '==' if m.facts['slush only'] else '>', 0, 61)]
        t.bench = [('bench_watch', dict(seconds=69, every=1, sheet=False, lines=1))]
        return t


    CHECKS.update({build: {'d': d} for build in ('aislsdef', 'aislddef')})
    CHECKS['aislrich'] = {'f': f}                # aitowerinc10r's: 塔在基地 and AI钱
    return dict(CHECKS=CHECKS)


def engine_aitechshare():
    """Initial OilDerrick ownership: below75 / above75 / below125 home counts.

    Expectations: the mission's cnv_tech_home (share = owned / 4 x 8 players, B 11-25 after C's two runs read 4/0/4).
    Check consumes published mission roles.
    """
    from parts import Script, Test, counted, square


    def check(m):
        t = Test()
        player = m.player('s1')
        t.areas['Tech home'] = square(*m.site('east base'), 450)
        t.scripts.append(Script('Tech reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.scripts.append(Script('Tech keep target', [],
            [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
        for i, (unit, expected) in enumerate(zip(m.cnv_units, m.cnv_tech_home)):
            label = ('低阈下', '低阈上', '高阈下')[i]
            counted(f'Tech_home{i}', label, t, template=unit, area='Tech home', player=player)
            t.expect.append((label, 40, '==', expected, 41))
        counted('Tech_owned', '油井数', t, template='OilDerrick', player=player)
        t.expect.append(('油井数', 1, '==', m.facts['tech own'], 41))
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': check} for name in ('aitechlow', 'aitechhigh', 'aitechsl', 'aitechsh', 'aitechsn')}
    return dict(CHECKS=CHECKS)


@cache
def engine_aitower():
    """Engine probe: where a skirmish AI puts its base defence tower (benches/ai/production/scenes.py#aitower_bench; l4_defense2.md section 7,
    items 2-3).

      a  塔近 0.5 / 0.75 / 1.0   s1's Multigunner turrets in three bands south of the AI's power plant (the AI building
                                  nearest the enemy): 250 / 375 / 475-500 from it (the radius for BaseCompactness 0.5 /
                                  0.75 / 1.0), x within 180 of the plant's (the first try's angle, straight south)
         落塔帧                   frames from frame 0 until s1 has a turret anywhere near its base (stops then; a turret
                                  outside every band is "elsewhere": around the yard, or another angle)

    The model (RA3-EngineModel ra3model/ai/defense.py tower_centre / tower_site / tower_spots): centre = the AI plant,
    angle = base centre -> nearest enemy (south), radius (BaseCompactness +- 0.05) x 500 clamped to 500. The expectation
    says the build's band; a FAIL is a reading too (a turret elsewhere: 落塔帧 stops with every band 0).

    读数 (bench 2026-11-07)
    aitowerstate a (the probe's own budget PRODUCTION 50 / DEFENSE 50, AlliedDefenseBuildState only, money 1700 at the
      wake; two runs, 0.5 and 0.75): no turret in 70 s (落塔帧 never stops). The always-on build state alone does not build.
    aitower50 a (the opener: deposit 1000 PRODUCTION + one AlliedBaseDefense; retail budgets): 落塔帧 451 (the wake is
      frame 150: 20 s, the build time), every band 0. Looked (keep=true, one run): the turret at ~(4092, 3570) -- ~296 from
      the yard at +35 deg (north-east, away from the enemy), nowhere near the AI plant; two refineries by the east ore.
      So the opener's turret is centred on the base anchor at an angle of k x 36 deg: the model's "no enemy found" branch
      (centre = base anchor, angle = random 0..9 x 36 deg) -- the player's plant 1250 south was not found (fog? the AI's
      vision?), or the opener places by another path.
    aitower50 b: 落塔帧 451, 塔距场 350 内 1 from s33 (560 内 1). aitower100 b (two runs): 落塔帧 451, 350 / 560 内 0, 700 内
      1 from s29. Radius 0.5 -> ~296, 1.0 -> 560-700: r = BaseCompactness x ~600, not x 500 (the model's R when the
      radius table is empty, l4_defense2.md 2.1) -- the table is not empty, or the default is not 500.
    Round 70 (bench 2026-11-07, all 落塔帧 451):
    aitower100 c (two runs): 560 / 590 内 0, 620 / 650 内 1 from s31 -> r in (590, 620]. aitower75 c: 420 内 0, 442 内 1
      from s30 -> r in (420, 442]. aitower75 b: 350 内 0, 560 / 700 内 1. So R in [590, 631]: ~600 (the model's
      TOWER_LIST_R, INFERRED: who fills the radius list is not read).
    aitower50 d (two runs), aitower100 d (one): FAIL -- 塔在厂南 and 塔在厂南带 0 throughout; 0.5's 塔距场 350 内 1 (s29 /
      s31), 1.0's 0 (its r ~600). Revealed for the AI too, the turret still stands round the yard, not by the plant:
      not the fog (the fog routine reads none either, work/re/l4_tower_r.md Q3). The model's centre / angle is a strict xfail.
    Round 71 (bench 2026-11-07):
    aitowerfoe e (own budget 50 / 50, only AlliedDefenseBuildState, 4 Guardians 600 south of the AI plant, revealed for
      both; 120 s): FAIL -- no turret anywhere (塔在基地 0 to s139, 落塔帧 never stops). An enemy army does not wake the
      build state either.
    aitowerdep e (as aitowerfoe, but an opener that only deposits 1000 to DEFENSE, no Build order; retail budgets): PASS
      -- 落塔帧 451 (as the opener's), 塔距场 350 内 1 from s29, 塔在厂南带 0 throughout. So the build state builds once
      the DEFENSE account has money (PLAYER_SET_MONEY never reaches the accounts: aitowerstate / aitowerfoe were broke),
      and its turret stands round the yard just as the opener's, the enemy tanks 600 south of the plant notwithstanding.
    Round 133 (bench 2026-11-11, work/logs/b136_bench.log; which of handoff-b section 125's hypotheses):
    aitowerinc e (as aitowerstate, + an AI refinery on the east ore and a miner): PASS -- 落塔帧 451, 塔距场 350 内 1 from
      s29, 2 from s49, 3 from s69, 4 from s89, 5 at s128 (塔在厂南带 0 throughout): one turret a build time.
    aitoweropen e (as aitowerstate, + an opener of one empty Time 0s order, own budget kept): FAIL -- no turret to s143.
      So the share pays nothing without income; an unfinished opening is not the reason. Money at the wake was the same
      1700 in both.
    Round 135 (bench 2026-11-11, work/logs/b138_bench.log; handoff-b section 137's table):
    aitowerinc10 e (as aitowerinc, DEFENSE 10 % / PRODUCTION 90 %, watched to s466): PASS -- 落塔帧 451 (ordered at the
      wake, as at 50 %), 塔距场 350 内 1 from s29, and NO second turret to s466. 10 % x 1700 = 170 < 800 bought the first:
      "share x the money now" is out (it waits for 8000 in the bank, ~s330); the share borrows against something at once,
      and then stops for 7+ minutes -- what it owes after the first is not paid back by the income in that time.
    aitowerinc10 f (= e + AI钱, work/logs/b138_bench2.log): PASS, the same -- 落塔帧 451, one turret to s477. AI钱 1700 at
      the wake, paid down to 1189 by s27 (the turret paid as it builds), then +250 every ~12.3 s (one miner: ~20.4/s;
      the simulator's miner ~14.7/s): 5400 at s235, 10400 at s477 -- 10 % of it is 1040 and still no second turret.
    aitowerinc5 f (DEFENSE 5 %): FAIL -- no turret to s454; AI钱 1700 never paid down, 10700 at s454.
      Reading (handoff-b section 138): the money in the bank does not decide; the first turret at 10 % and none at 5 %
      fit "share x income rate x build time x window, less what the share has paid (never paid back)": R(10 %) in
      [800, 1600), so R(5 %) < 800 and R(50 %) in [4000, 8000) (aitowerinc's 5, money-limited). INFERRED.
    Round 136 (bench 2026-11-11, work/logs/b139_bench.log):
    aitowerinc10r f (as aitowerinc10, 20000 at the wake; mod CampAITowRich): PASS -- 塔在基地 1 from s29, 2 from s49, no
      third to s174 (AI钱 ~19150 after the two, 21600 at s174). So the bank does count: 10 % x 20000 = 2000 buys two
      (a third needs 2400). With aitowerinc10 / 5: the share spends the larger of share x the bank and share x income
      rate x build time x W, less what it has paid (handoff-b section 139: tried, not merged -- with the simulator's
      miners it buys aiskirmlow a tower the bench never built, so the rate there must be smaller: net cash flow?).
    """
    import math

    from parts import Script, Test, counted, square

    LAG = 4.0
    AFTER = 60.0
    HALF_X = 180.0
    BANDS = ((0.5, '塔近 0.5', 'CNV AT Band 50', 170.0, 310.0), (0.75, '塔近 0.75', 'CNV AT Band 75', 310.0, 435.0),
             (1.0, '塔近 1.0', 'CNV AT Band 100', 435.0, 570.0))    # (compactness, label, area, r from, r to)
    ANY = 'CNV AT Any'


    def _band(x, y, near, far):
        """The strip from `near` to `far` south of (x, y), x within HALF_X: the tower's distance r from the plant."""
        return [(x - HALF_X, y - far), (x + HALF_X, y - far), (x + HALF_X, y - near), (x - HALF_X, y - near)]


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        o = m.find(m.role('ai plant').name)
        pick = None
        for comp, label, area, near, far in BANDS:
            t.areas[area] = _band(o.x, o.y, near, far)
            counted(f'CNV_AT_B{int(comp * 100)}', label, t, template=m.cnv_turret, area=area, player=s1)
            if comp == m.cnv_compactness:
                pick = label
        x, y = m.site('east base')
        t.areas[ANY] = square(x, y, 1500.0)
        t.counters.append(('CNV_AT_First', '落塔帧'))
        t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, m.cnv_turret,
                                                 ANY)], [('SET_FLAG', 'Test Tower', 1)]),
                      Script('Test - no tower yet', [('FLAG', 'Test Tower', 0)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AT_First')], once=False)]
        end = m.facts['wake at'] + AFTER
        t.expect += [(pick, 1, 'ever>=', 1, end)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
        return t


    def _disc(x, y, r, n=24):
        return [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


    RINGS = ((350.0, '塔距场 350 内', 'CNV AT Yard 350'), (560.0, '塔距场 560 内', 'CNV AT Yard 560'),
             (700.0, '塔距场 700 内', 'CNV AT Yard 700'))


    def b(m):
        """Bench 11-07 a: the opener's turret stood ~300 from the yard, not by the plant. So count round the yard:

          塔距场 350 / 560 内   s1's turrets within 350 / 560 of the yard (24-gons): BaseCompactness 0.5 -> 225-275 x
                               something, 1.0 -> 475-500 (radius (BaseCompactness +- 0.05) x 500 clamped to 500)
          塔距厂 300 内         within 300 of the AI plant (the read centre when an enemy is found)
          落塔帧                as a"""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        x, y = m.site('east base')
        for r, label, area in RINGS:
            t.areas[area] = _disc(x, y, r)
            counted(f'CNV_AT_Y{int(r)}', label, t, template=m.cnv_turret, area=area, player=s1)
        t.areas[ANY] = square(x, y, 1500.0)
        t.counters.append(('CNV_AT_First', '落塔帧'))
        t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, m.cnv_turret,
                                                 ANY)], [('SET_FLAG', 'Test Tower', 1)]),
                      Script('Test - no tower yet', [('FLAG', 'Test Tower', 0)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AT_First')], once=False)]
        end = m.facts['wake at'] + AFTER
        # centre = the yard (no enemy found, bench a); 0.5 -> within 350; 1.0 -> 560-700 (bench 11-07)
        ring = '塔距场 350 内' if m.cnv_compactness < 0.6 else '塔距场 700 内'
        t.expect += [(ring, 1, 'ever>=', 1, end)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
        return t


    FINE = (560.0, 590.0, 620.0, 650.0)         # x BaseCompactness: R's candidates round 600


    def c(m):
        """Round 70: pin R. Four rings round the yard at BaseCompactness x 560 / 590 / 620 / 650 (no 落塔帧: the turret is
        down by frame 451 in every run so far). Read r = (BaseCompactness +- 0.05) x R clamped to R (l4_defense2.md 2.2):
        at 1.0, r is in [0.95 R, R] -- the first ring that counts the turret bounds R from above, the one before from
        below (R >= that / 1.05 at 1.0). The expectation: the outer ring (bench b put 1.0 inside 700)."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        x, y = m.site('east base')
        k = m.cnv_compactness
        labels = []
        for f in FINE:
            r = k * f
            label, area = f'塔距场 {int(r)} 内', f'CNV AT Fine {int(f)}'
            t.areas[area] = _disc(x, y, r, n=48)
            counted(f'CNV_AT_F{int(f)}', label, t, template=m.cnv_turret, area=area, player=s1)
            labels.append(label)
        end = m.facts['wake at'] + AFTER
        t.expect += [(labels[-1], 1, 'ever>=', 1, end)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
        return t


    AIM = 296.0                                 # bench a/b: the 0.5 turret ~296 from its centre


    def d(m):
        """Round 70: is "no enemy found" the AI's fog? As b, but the map is revealed for s1 too (MAP_REVEAL_ALL_PERM s1).
        Read: centre = the AI building nearest an enemy (the AI plant), first angle = base centre -> nearest enemy (south).

          塔在厂南        s1's turret within 120 of the AI plant + (0, -BaseCompactness x 592) (the enemy-found spot)
          塔在厂南带      south of the AI plant by 100 or more, x within 400 (any of the 5 tries' angles round south)
          塔距场 350 内   round the yard as b (the no-enemy spot at 0.5)
          落塔帧          as a
        Revealed and still round the yard -> the fog is not why (the opener's own placement path, or the fog routine's filter, work/re/l4_tower_r.md Q3)."""
        t = Test()
        s1 = m.player('s1')
        t.scripts += [Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                      Script('Test - reveal for the AI', [], [('MAP_REVEAL_ALL_PERM', s1)])]
        o = m.find(m.role('ai plant').name)
        r = m.cnv_compactness * 2 * AIM
        t.areas['CNV AT Spot'] = _disc(o.x, o.y - r, 120.0)
        counted('CNV_AT_Spot', '塔在厂南', t, template=m.cnv_turret, area='CNV AT Spot', player=s1)
        t.areas['CNV AT South'] = [(o.x - 400, o.y - 900), (o.x + 400, o.y - 900), (o.x + 400, o.y - 100),
                                   (o.x - 400, o.y - 100)]
        counted('CNV_AT_South', '塔在厂南带', t, template=m.cnv_turret, area='CNV AT South', player=s1)
        x, y = m.site('east base')
        t.areas['CNV AT Yard 350'] = _disc(x, y, 350.0)
        counted('CNV_AT_Y350', '塔距场 350 内', t, template=m.cnv_turret, area='CNV AT Yard 350', player=s1)
        t.areas[ANY] = square(x, y, 1500.0)
        t.counters.append(('CNV_AT_First', '落塔帧'))
        t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, m.cnv_turret,
                                                 ANY)], [('SET_FLAG', 'Test Tower', 1)]),
                      Script('Test - no tower yet', [('FLAG', 'Test Tower', 0)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AT_First')], once=False)]
        end = m.facts['wake at'] + AFTER
        t.expect += [('塔在厂南带', 1, 'ever>=', 1, end)]      # the read rule; a FAIL is the reading "still the yard"
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
        return t


    LONG = 120.0                                # the build state is not timed like the opener: give it two minutes


    def e(m):
        """Round 71 (aitowerfoe): the regular build state, not the opener. As aitowerstate (own budget, only
        AlliedDefenseBuildState) plus the player's tanks 600 south of the AI plant (HOLD_FIRE), map revealed for both.
        Does BEST_UNIT_EXPECTED build a turret once there is an enemy army, and round which building?

          塔在厂南带      s1's turret south of the AI plant by 100-900, x within 400 (read: centre = the AI building nearest
                          an enemy = the plant, first angle south, r 0.5 x 600 = 300)
          塔距场 350 内   round the yard (the opener's spot at 0.5, bench round 69 / 70)
          塔在基地        anywhere in the 1500 square round the yard (built at all)
          落塔帧          as a
        The expectation: built at all (a FAIL is the reading "the build state builds nothing even with an enemy army")."""
        t = Test()
        s1 = m.player('s1')
        t.scripts += [Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                      Script('Test - reveal for the AI', [], [('MAP_REVEAL_ALL_PERM', s1)])]
        o = m.find(m.role('ai plant').name)
        t.areas['CNV AT South'] = [(o.x - 400, o.y - 900), (o.x + 400, o.y - 900), (o.x + 400, o.y - 100),
                                   (o.x - 400, o.y - 100)]
        counted('CNV_AT_South', '塔在厂南带', t, template=m.cnv_turret, area='CNV AT South', player=s1)
        x, y = m.site('east base')
        t.areas['CNV AT Yard 350'] = _disc(x, y, 350.0)
        counted('CNV_AT_Y350', '塔距场 350 内', t, template=m.cnv_turret, area='CNV AT Yard 350', player=s1)
        t.areas[ANY] = square(x, y, 1500.0)
        counted('CNV_AT_Any', '塔在基地', t, template=m.cnv_turret, area=ANY, player=s1)
        t.counters.append(('CNV_AT_First', '落塔帧'))
        t.scripts += [Script('Test - a tower', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, m.cnv_turret,
                                                 ANY)], [('SET_FLAG', 'Test Tower', 1)]),
                      Script('Test - no tower yet', [('FLAG', 'Test Tower', 0)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AT_First')], once=False)]
        end = m.facts['wake at'] + m.facts.get('watch', LONG)
        t.expect += [('塔在基地', 1, 'ever>=', 1, end)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
        return t


    def f(m):
        """Round 135: e + AI钱 (s1's money each frame) -- the miner's income rate and the money when a second turret is
        (not) ordered: which of handoff-b section 138's budget models."""
        t = e(m)
        t.counters = [c for c in t.counters if c[1] != '塔在厂南带']     # four lines fit (never 1 in e's runs)
        t.counters.append(('CNV_AT_Money', 'AI钱'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('s1'), 'CNV_AT_Money')],
                                once=False))
        t.bench = [('bench_watch', dict(seconds=m.facts['wake at'] + m.facts.get('watch', LONG) + LAG, every=2,
                                        sheet=False, lines=len(t.counters)))]
        return t


    TRIP = 250                                  # a miner's load (aitowerinc10 f: +250 every ~12.3 s at x1)


    def g(m):
        """B round 172 (aicheat2 / aicheat1): ResourceMultiplierCheat. DEFENSE 0 %, so nothing is bought and AI钱 only
        grows by the miner's trips. Read (work/re/l2_mining.md 4): a deposit is the load x the AI's cheat multiplier.

          AI钱    s1's money each second (a step = one trip: 250 x the multiplier)

        The expectation: the MEDIUM line's Percentage is the multiplier (200 % -> 500 a trip; 100 % -> 250, and a line
        for EASY HARD BRUTAL is skipped at MEDIUM). In the 90 s watched ~7 trips: x1 stays under the wake money + 2500,
        x2 passes the wake money + 5 x 500.

        读数 (bench 2026-11-13, B round 172, work/logs/b172_bench.log, one run each, both PASS):
        aicheat1 g (EASY HARD BRUTAL 300 %, MEDIUM 100 %): 1700 at the wake, +250 a trip (1950 s18, 2200 s30, ...
          3450 s92, 3700 s104) -- the 300 % line is skipped at MEDIUM, 100 % = x1.
        aicheat2 g (MEDIUM 200 %): +500 a trip (2200 s18, 2700 s31, ... 5200 s92) -- the Percentage is the factor."""
        t = Test()
        t.counters.append(('CNV_AT_Money', 'AI钱'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('s1'), 'CNV_AT_Money')],
                                once=False))
        wake, end = m.facts['wake at'], m.facts['wake at'] + m.facts.get('watch', LONG)
        if m.cnv_cheat == 1.0:
            t.expect += [('AI钱', wake + 5, '<', m.facts['money'] + 10 * TRIP, end)]
        else:
            t.expect += [('AI钱', wake + 5, 'ever>=', m.facts['money'] + 5 * round(TRIP * m.cnv_cheat), end)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=1))]
        return t


    def h(m):
        """B round 173 (aibsprod): BudgetState.State. The personality declares its own budget (DEFENSE 50 %, which buys a
        turret soon after the wake in aitowerinc) but its one BudgetState line names retail ProductionOnlyBudget
        (OpeningMoveHeuristic Complete=true -> PRODUCTION 100 %, DEFENSE 0 %); 20000 at the wake, no opening move.

          塔在基地   s1's turrets in the 1500 square round the yard
          AI钱      s1's money each 2 s

        The expectation: the State is the budget used -- DEFENSE 0 %, so no turret however rich (the own 50 % one, were it
        used, buys one within ~30 s as aitowerinc)."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        x, y = m.site('east base')
        t.areas[ANY] = square(x, y, 1500.0)
        counted('CNV_AT_Any', '塔在基地', t, template=m.cnv_turret, area=ANY, player=s1)
        t.counters.append(('CNV_AT_Money', 'AI钱'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AT_Money')], once=False))
        wake, end = m.facts['wake at'], m.facts['wake at'] + m.facts.get('watch', LONG)
        t.expect += [('塔在基地', wake + 5, '<=', 0, end)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
        return t


    def i(m):
        """B round 178 (aibsmax / aibstie / aibszero; work/re d122_ai_rules.md 1, R1-R3): which of two budget states runs.
        The personality's two own states, in list order: DEFENSE 100 % (turrets from the 20000 bank) and PRODUCTION 100 %
        (buys nothing -- no unit build state left). Read: each state's weight is the product of its heuristics; the one
        with the largest weight runs, its shares alone (not mixed); ties go to the earlier line; all 0 -> the first line.

          塔在基地   s1's turrets in the 1500 square round the yard

        aibsmax  DEFENSE 0.4 first, PRODUCTION 0.6: PRODUCTION runs -> no turret (mixed shares or "the first line": turrets)
        aibstie  0.5 and 0.5: the earlier (DEFENSE) runs -> turrets
        aibszero DEFENSE weight 0 first, PRODUCTION while the opening is not done (done 40 s after the wake): no turret
                 before, then every weight 0 -> the first line (DEFENSE) -> turrets ("keep the budget it had": none)

        RESULTS i (bench 2026-11-13, B round 178, work/logs/b178_bench.log in the B worktree, all three PASS):
          aibsmax 塔在基地 0 s1-s171; aibstie 0 to s27, 1 from s29, then one every ~20 s (5 from s109);
          aibszero 0 to s67 (the opening done at s50), 1 from s69, 5 from s149. The simulator: none / s32 / s71."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        x, y = m.site('east base')
        t.areas[ANY] = square(x, y, 1500.0)
        counted('CNV_AT_Any', '塔在基地', t, template=m.cnv_turret, area=ANY, player=s1)
        wake, end = m.facts['wake at'], m.facts['wake at'] + m.facts.get('watch', LONG)
        # aibsdiff: a line whose Difficulty leaves out the bench's MEDIUM is not weighed (aibsmax's pair -> turrets)
        weights = [w for _, w, _, *diff in m.cnv_bsets if not diff or 'MEDIUM' in diff[0].split()]
        if 'opening' in weights:                # aibszero
            done = wake + m.facts['opening']
            t.expect += [('塔在基地', wake + 5, '<=', 0, done), ('塔在基地', done, 'ever>=', 1, end)]
        elif len(weights) == 1:                 # aibsdiff: only DEFENSE is left -> turrets
            t.expect += [('塔在基地', wake + 5, 'ever>=', 1, end)]
        elif len(weights) < 2:                  # a build without the budget-state pair: readings only
            pass
        elif float(weights[1]) > float(weights[0]):     # aibsmax: the second (PRODUCTION) is larger
            t.expect += [('塔在基地', wake + 5, '<=', 0, end)]
        else:                                   # aibstie: the first (DEFENSE) holds the tie
            t.expect += [('塔在基地', wake + 5, 'ever>=', 1, end)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=2, sheet=False, lines=len(t.counters)))]
        return t


    def r4(m):
        """B round 184 (aibsback; work/re d122_ai_rules.md 1, R4): the retail budgets switch back when the enemy leaves.
        The opening is done at once; 5000 at the wake, Coop 85/5/10 -> DEFENSE 250, no turret. Raid in (4 Guardians,
        3800, 650 from the yard) -> Defense 80/20, the idle money re-split: DEFENSE ~1000 -> one turret; raid out -> Coop
        again the next second; +5000 after: Coop's 5 % (~460 with the rest) buys none, Defense's 20 % (~1200) would.

          塔在基地   s1's turrets in the 1500 square round the yard
          敌在       the raiders standing
          AI钱       s1's money"""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        x, y = m.site('east base')
        t.areas[ANY] = square(x, y, 1500.0)
        counted('CNV_AT_Any', '塔在基地', t, template=m.cnv_turret, area=ANY, player=s1)
        counted('CNV_AT_Raid', '敌在', t, template='AlliedAntiVehicleVehicleTech1', area=ANY, player=m.player('p1'))
        t.counters.append(('CNV_AT_Money', 'AI钱'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AT_Money')], once=False))
        w = m.facts['wake at']
        t_in, t_out = (w + m.facts[k] for k in ('raid in', 'raid out'))
        end = w + m.facts['watch']
        t.expect += [('塔在基地', w + 5, '<=', 0, t_in), ('塔在基地', t_in, 'ever>=', 1, t_out),
                     ('塔在基地', w + 5, '<=', 1, end)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a, 'b': b, 'c': c, 'd': d, 'e': e, 'f': f, 'g': g, 'h': h, 'i': i}
              for k in ('aitower50', 'aitower75', 'aitower100', 'aitowerstate', 'aitowerfoe',
                       'aitowerdep', 'aitowerinc', 'aitoweropen', 'aitowerinc10', 'aitowerinc5', 'aitowerinc10r',
                       'aicheat2', 'aicheat1', 'aibsprod', 'aibsmax', 'aibstie', 'aibszero', 'aibsdiff')}
    CHECKS['aibsback'] = {'r4': r4}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(f=f))


def engine_aiupgrade():
    """BuildEntry.Upgrade presence pair (C line): aicupgon:a / aicupgoff:a.

    Prediction from retail AlliedTechBuildState and Upgrade_AlliedTech2: with a refinery,
    money and a yard, the constant state's UPGRADE_TECH entry can buy the object upgrade
    (1500, 15s). On should acquire Tech2 within 90s after wake; off omits that dedicated
    state and should hold none.
    Retail tech entries have MinTime >=180s, outside the observation. Timing, seller choice,
    budget account, Tech3 and Japanese upgrades remain gaps. Evidence: work/re/c_upgrade_report.md.

    RESULTS 2026-11-12: aicupgon archived rows s39..s120 show 2 Tech2 holders;
    yard=1 throughout, refinery=1 then 2/3 as the opening continues. Saved frames rejudged
    after correcting an unsupported expectation operator; no second engine run needed.
    aicupgoff: Tech2 holders=0 throughout s1..105; yard=1, refinery>=1. All three
    expectations PASS. This pair establishes upgrade-state effect, not the holder identities.
    """
    from parts import Script, Test, counted


    def a(m):
        t = Test()
        player = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counter = 'CNVCUpHolders'
        t.counters.append((counter, '二级持有'))
        t.scripts.append(Script('Test - holders zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for n in range(1, 11):
            t.scripts.append(Script(f'Test - holders {n}',
                                   [('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', player, n, 'Upgrade_AlliedTech2')],
                                   [('SET_COUNTER', counter, n)], once=False))
        counted('CNVCUpRef', '矿厂数', t, template='AlliedRefinery', player=player)
        counted('CNVCUpYard', '建造厂数', t, template='AlliedConstructionYard', player=player)
        t.counters.append(('CNVCUpMoney', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', player, 'CNVCUpMoney')], once=False))
        wake = m.facts['wake at']
        t.expect = [('矿厂数', wake + 30, '>=', 1, wake + 90),
                    ('建造厂数', wake + 30, '>=', 1, wake + 90),
                    ('二级持有', wake, 'ever>=', 1, wake + 90) if m.facts['upgrade entry'] else
                    ('二级持有', 0, '==', 0, wake + 90)]
        t.bench = [('bench_watch', dict(seconds=wake + 92, every=1, sheet=False, lines=4))]
        return t


    BAN_UNTIL = 40.0


    def ban(m):
        """ALLOW_DISALLOW_ONE_UPGRADE (engine A, round 257): aicupgon:a with s1's Upgrade_AlliedTech2 banned at the start
        (allow 0) and allowed again (1) at 40 s. Simulator prediction (Sim.upgrade_sellers skips a banned upgrade; the
        unbanned run buys at s20.5 and holds 2 from s36, bench s39): holders 0 to the allow, then the yard sells it again
        -- bought s40.5, 15 s to research, 2 holders from s56. Ignored ban: holders by ~s39 as aicupgon:a (the first
        expectation runs to s50 to catch that); a ban outliving the allow, or the AI giving the entry up after a refusal:
        0 to the end. (Not 60 s: by then the model's AI has spent its PRODUCTION account to 0 on units and buys nothing,
        which would not tell the allow.)
        RESULTS A264 (PASS, CampCUpOnBan_mcp_1116_065219): holders 0 s1-s62, 2 from s63 (refinery 1 then 2 at s115, yard 1).
        The ban holds and the allow gives the entry back; the bench holds 7 s after the simulator (s56) -- the AI's
        rebuy after the allow is later than the model's immediate s40.5 (INFERRED: the build list is re-tried on its own
        clock; not measured)."""
        t = a(m)
        player = m.player('s1')
        t.counters = [c for c in t.counters if c[0] != 'CNVCUpMoney']
        t.scripts = [s for s in t.scripts if s.name != 'Test - money']
        t.scripts.append(Script('Test - ban Tech2', [], [('ALLOW_DISALLOW_ONE_UPGRADE', player, 'Upgrade_AlliedTech2', 0),
                                                         ('SET_MILLISECOND_TIMER', 'CNVCUpBan', BAN_UNTIL)]))
        t.scripts.append(Script('Test - allow Tech2', [('TIMER_EXPIRED', 'CNVCUpBan')],
                                [('ALLOW_DISALLOW_ONE_UPGRADE', player, 'Upgrade_AlliedTech2', 1)]))
        end = m.facts['wake at'] + 92
        t.expect = [('二级持有', 0, '==', 0, BAN_UNTIL + 10),
                    ('二级持有', BAN_UNTIL + 12, 'ever>=', 1, end - 2)]
        t.bench = [('bench_watch', dict(seconds=end, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {build: {'a': a} for build in ('aicupgon', 'aicupgoff', 'aipttn', 'aipttp', 'aipttw', 'aipttwg')}   # aiptt*: path_test
    CHECKS['aicupgon']['ban'] = ban
    return dict(CHECKS=CHECKS)


BENCHES = (
    ai, aistep, engine_aiaesthetics, engine_aiallbuild,
    engine_aibuilding, engine_aibuildkind, engine_aicap, engine_aiconstweight,
    engine_aiexpansion, engine_aiintervalfrom, engine_ailastexp, engine_ainodesfull,
    engine_aiomove, engine_aiopath, engine_aiopathcond, engine_aiopen,
    engine_aiopenside, engine_aiotime, engine_aipathbanks, engine_aipathx,
    engine_aiplacement, engine_aipower, engine_aipowerabove, engine_aipoweradv,
    engine_aipowerenemy, engine_aipowerown, engine_aipowervalue, engine_aisimpleexp,
    engine_aiskirm, engine_aislush, engine_aitechshare, engine_aitower,
    engine_aiupgrade,
)
