"""AI tactics checks."""
from functools import cache
from types import SimpleNamespace


@cache
def engine_aialphaclose():
    """Read target health, arrival, home and survival for the delayed-guard pair.

    Model prediction before measurement: both thresholds retreat with target HP64;
    the high lane still fails the model's reach predicate despite shooting.
    The high-lane finishing expectation is the competing hypothesis, retained as
    a diagnostic FAIL if disproved, never tuned to the measurement.

    MEASURED: low target HP59, home4/live4; high HP34, home0/live0,
    stable capture s39-55. High finishes neither target nor return: its original
    kill expectation remains FAIL. Thresholds distinguish outcomes, but the
    model retreats in both lanes (HP64/home3/live3); strict replay xfails and
    GUESSED inventory remain. See work/re/c_alpha_close_report.md.
    """
    ar = engine_airetreat()["shared"]
    from parts import counted


    def probe(m):
        t = ar.a(m, 'airet')
        counted('CNV_AlClose_HP', '目标血量', t, health=m.facts['alpha target'])
        t.expect = [('目标血量', 1, '==', 70, 29), ('到远厂', 15, 'ever>=', 1, 29)]
        if m.facts['alpha high']:
            t.expect.append(('目标血量', 30, 'ever<=', 1, 65))
        else:
            t.expect.append(('步兵在家', 35, 'ever>=', 1, 65))
        t.bench = [('bench_watch', dict(seconds=66, every=2, sheet=False, lines=4))]
        return t


    def observe(m):
        """Check observer equivalence against the original measured plateaus.

        D81 fixed the observer overhead and added a shared logic-frame anchor.
        Record changes plus a one-second heartbeat to cover the guard/Alpha
        confrontation. Qualify both lanes before using their internal states;
        never shift the clock to fit the original bench. E99 reproduced both plateaus;
        the high lane required RA3_BENCH_SPEED=1 to sustain 15 logic frames per
        sampled second. See work/re/e99_alpha_observer.md.
        """
        t = probe(m)
        alpha = m.facts['alpha high'] and m.facts.get('alpha kill', 1000.0) > 1.0
        # aialobttk (B219): the high lane with AlphaStrikeTargetTimeToKill 0.01. Prediction (model): health x kill
        # time never under 0.01, so no alpha strike -> the low lane's retreat plateau.
        hp, home, live = (34, 0, 0) if alpha else (59, 4, 4)
        t.expect = [('目标血量', 1, '==', 70, 29), ('到远厂', 17, '==', 4, 27)]
        t.expect += [(label, 39, '==', value, 55) for label, value in
                     (('目标血量', hp), ('步兵在家', home), ('步兵数', live))]
        return t


    CHECKS = {b: {'a': probe} for b in ('aialcloselo', 'aialclosehi')}
    CHECKS.update({b: {'a': observe} for b in ('aialobslo', 'aialobshi', 'aialobttk')})
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(observe=observe))


def engine_aialphahp():
    """AlphaStrike health contrast: target damage and surviving return, not internal state.

    Prediction: the named target's guards cause retreat in the low lane;
    the high lane gives priority to finishing the 70% target. No exact boundary
    or exact order frame is claimed. See benches/ai/tactics/scenes.py#aialphahp_bench.

    Bench 2026-11-11, corrected float health script: low PASS / high FAIL.
    Both target HP70 s1-85, far2 s15-16, home4 s26-41, all four live to s85.
    The high-lane finishing hypothesis below is retained as a diagnostic FAIL,
    not retuned to the observation. This pair does not isolate AlphaStrike.
    Only first-cycle arrival/return/unchanged HP replay is tested; no field
    promotion. Missing target applicability evidence: work/re/handoff-c.md.
    The first pair used integer70 (empty float slot, target dead s1); invalid,
    not an AlphaStrike negative. The corrected pair changes only 70 -> 70.0.
    """
    ar = engine_airetreat()["shared"]
    from parts import counted


    def a(m, high):
        t = ar.a(m, 'airet')
        counted('CNV_Alpha_Hp', '目标血量', t, health=m.facts['alpha target'])
        wake = m.facts['wake at']
        t.expect = [('目标血量', 1, 'ever==', 70, wake),
                    ('到远厂', wake, 'ever>=', 1, wake + 30)]
        if high:
            t.expect += [('目标血量', wake, 'ever<=', 1, wake + 50)]
        else:
            t.expect += [('步兵在家', wake + 15, 'ever>=', 1, wake + 50)]
        return t


    CHECKS = {'aialphalo': {'a': lambda m: a(m, False)}, 'aialphahi': {'a': lambda m: a(m, True)}}
    return dict(CHECKS=CHECKS)


def engine_aibasedef():
    """Engine probe: the skirmish AI team's EnterBaseDefenses (benches/ai/tactics/scenes.py#aibasedef_bench; docs/engine/aiteamstate.md).

      a  进炮塔     s1's objects with status ENCLOSED (someone is inside a turret)
         炮塔数     AlliedBaseDefense s1 owns
         步兵数     Peacekeepers s1 owns (in a turret too)
         到远厂     Peacekeepers of s1 within 300 of the far power plant
         once a second, AFTER seconds after the wake

    Expectations are the model's (l4_micro_engage.md 1.7); a FAIL is a reading too:
      aibd1     进炮塔 reaches 1 or more
      aibd0 / aibdidle  进炮塔 stays 0
      aibdwho   (counters 进炮塔 旁1 旁2 旁3: Peacekeepers of s1 within NEXT of turret 1 / 2 / 3, in it too) 进炮塔 reaches 1
      aibdpre   (as aibdwho; turret 1 holds a fifth Peacekeeper from s0) 进炮塔 reaches 2 (the full turret skipped)

    aibdidle: <AIMicroManagerData EnterBaseDefensesWhenIdle> true with EnterBaseDefenses false; aibd1 / aibdwho:
    EnterBaseDefenses true, WhenIdle false (benches/ai/tactics/scenes.py#aibasedef_bench).

    Readings (11-09, all PASS; counters 进炮塔 炮塔数 步兵数 到远厂; the AI's 4 AlliedBaseDefense 200 north of the far plant):
      aibd1     s1-s14 0 4 4 0 | s15-17 到远厂 2,3,4 | s18-s20 0 3 4 4 | s21-s25 1 3 4 4 | s26-s32 1 2 3 3 | s33-s75 1 2 2 2
                -- one Peacekeeper in a turret from s21 to the end (alive: the others die by s33, a turret lost per ~5 s)
      aibd0     s18-s25 0 3 4 4 | s26-s28 0 2 4 4 | s29 0 2 3 3 | s30 0 2 2 2 | s31-32 0 2 1 1 | s33-s75 0 2 0 0
      aibdidle  the same as aibd0 (进炮塔 0 all along; team dead by s33)
      aibdwho   PASS (进炮塔 旁1 旁2 旁3): s16 0 0 1 0 | s17-18 0 0 2 1 | s19-20 0 1 2 0 | s21 1 2 1 0 | s22 1 3 0 0 | s23 1 2 1 0 |
                s24 1 2 2 0 | s25 1 1 1 1 | s26-76 1 0 0 2 -- the men gather at turret 1 (3 next to it at s22), one goes in at
                s21, the rest drift off: read as all sent to the first turret of the list in one pass (no place kept for
                the earlier ones), not as 'the others were beyond 150'. Not proved (a man inside is not counted in 旁k).
      aibdpre   FAIL (11-09, 进炮塔 旁1 旁2 旁3): s1-15 1 1 0 0 (the sitter, counted in 旁1) | s16 1 1 1 0 | s17 1 1 2 1 |
                s18-19 1 1 3 0 | s20-25 1 2 3 0 | s26-29 0 1 3 0 (turret 1 lost, the sitter with it) | ... | s46-75 0 0 0 0
                -- 进炮塔 never passes 1: with turret 1 full nobody goes into turret 2 or 3, though 3 stand by turret 2
                (s18-25); one walks up to the full turret 1 (旁1 2, s20-25). Read: the full turret is NOT skipped -- the
                pass still takes the list's first turret (the turret-order routine's 'can the order be done' check, work/re/l4_micro_engage.md 1.7, does not look at
                room, INFERRED), the men leave the team for it and stay out. Not a 'one per pass' rule: then one would have
                gone into turret 2.
      (11-13, D round 132; the idle StaticDefense team, missions idle_mission; counters 进炮塔 炮塔数 步兵数)
      aibdi1    PASS: s1 0 4 4 | s2-s5 1 4 4 | s6-s55 2 4 4 -- enter orders from the base-defense routine only (the host's
                order log: 4 at frame 50, all to turret 1; 3 at frame 98, turret 2)
      aibdi0    FAIL: s1-s3 0 | s4-s55 1 -- no order from the base-defense routine; the one man inside from 4 enter
      aibdi2    FAIL: the same       orders at frame 80 of another routine, which neither switch gates (work/re/d132_whenidle.md)
    """
    from benches.ai.targets.checks import engine_aitarget
    at = engine_aitarget()["shared"]
    from parts import Script, Test, counted, square, status

    AFTER = 60.0
    IDLE_BUILDS = ('aibdi1', 'aibdi0', 'aibdi2')   # not aibdidle (the fighting team's idle-only control)
    IDLE_AFTER = 40.0                       # aibdi*: the team forms by ~wake + 2 s and stands there
    NEXT = 40.0                             # the turrets stand 80 apart: the squares do not overlap


    def a(m, build):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        if build in IDLE_BUILDS:
            return idle(m, build, t, s1)
        o = m.find(m.role('far plant').name)
        t.areas[at.FAR] = square(o.x, o.y, 300.0)
        (inf,) = m.cnv_units
        counted('CNV_BD_In', '进炮塔', t, status=status('ENCLOSED'), player=s1)
        if build == 'aibdpre':
            t.scripts.append(Script('Test - sit', [], [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY',
                                                           m.role('sitter').name, m.role('turret 1').name)]))
        if build in ('aibdwho', 'aibdpre'):
            for k in (1, 2, 3):
                tur = m.find(m.role(f'turret {k}').name)
                area = f'CNV_BD_Next{k}'
                t.areas[area] = square(tur.x, tur.y, NEXT)
                counted(f'CNV_BD_N{k}', f'旁{k}', t, template=inf, area=area, player=s1)
        else:
            counted('CNV_BD_Turrets', '炮塔数', t, template=m.role('turret 1').template, player=s1)
            counted('CNV_BD_Count', '步兵数', t, template=inf, player=s1)
            counted('CNV_BD_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
        wake = m.facts['wake at']
        end = wake + AFTER
        if build in ('aibd1', 'aibdwho'):
            t.expect += [('进炮塔', 1, 'ever>=', 1, end)]
        elif build == 'aibdpre':                 # the model: a full turret is skipped, one more goes into turret 2
            t.expect += [('进炮塔', 1, 'ever>=', 2, end)]
        else:
            t.expect += [('进炮塔', 1, '==', 0, end)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def idle(m, build, t, s1):
        """aibdi*: the StaticDefense team at the AI's yard, no enemy (missions idle_mission). 进炮塔 as above, 炮塔数,
        步兵数 (Peacekeepers s1 owns, in a turret too). d131 2: aibdi1 (both switches on) -> someone goes in (state 8);
        aibdi0 (WhenIdle off) / aibdi2 (EnterBaseDefenses off) -> nobody."""
        (inf,) = m.cnv_units
        counted('CNV_BD_In', '进炮塔', t, status=status('ENCLOSED'), player=s1)
        counted('CNV_BD_Turrets', '炮塔数', t, template=m.role('turret 1').template, player=s1)
        counted('CNV_BD_Count', '步兵数', t, template=inf, player=s1)
        end = m.facts['wake at'] + IDLE_AFTER
        t.expect += [('进炮塔', 1, 'ever>=' if build == 'aibdi1' else '==', 1 if build == 'aibdi1' else 0, end)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('aibd1', 'aibd0', 'aibdidle', 'aibdwho', 'aibdpre',
                                                               'aibdi1', 'aibdi0', 'aibdi2')}
    return dict(CHECKS=CHECKS)


def engine_aicannot():
    """CannotAttackTargetReaction measured lifecycle, read in benches/ai/tactics/readings.toml#engine_aicannot.

    SDK predicts Ignore continues, Disband releases, TreatLikeSuccess uses RAMPAGE.
    Counters only validate the scene and its game clock. Team lifecycle/aims must
    be read from CNVTeams, not inferred from no damage. See work/re/c_cannot_report.md.

    MEASURED 2026-11-13, one three-build round: all scene checks PASS.
    Ignore: two members from carrier frame 21, air tactical target from 51,
    retained through frame 1771. Disband: target at 51, zero members at 95,
    two again at 97, repeated clearing/recruitment. TreatLikeSuccess/RAMPAGE:
    air target at 51, ground yard target at 92, enemy micro state 6 at 500.
    All three keep two living Guardians and zero air-target damage. Carrier
    frames are not map-counter frames. Exact dispatch timing, ReturnHomeAndDisband
    and other tactics remain gaps; consumer boundaries are in work/re/e122_cannot.md.
    """
    from model import Script, Test, counted, square


    def probe(m):
        t = Test()
        t.counters += [('CNV_CA_Frame', '帧数'), ('CNV_CA_Hurt', '空靶受伤')]
        t.scripts += [Script('Cannot - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                      Script('Cannot - frame', [], [('INCREMENT_COUNTER', 1, 'CNV_CA_Frame')], once=False),
                      Script('Cannot - hurt', [('UNIT_HEALTH', m.role('air target').name, 0, 100)],
                             [('SET_COUNTER', 'CNV_CA_Hurt', 1)])]
        counted('CNV_CA_Own', '坦克数', t, template=m.cnv_units[0], player=m.player('s1'))
        t.areas['CNV Cannot Home'] = square(*m.site('east base'), 450)
        counted('CNV_CA_Home', '在家', t, template=m.cnv_units[0], player=m.player('s1'), area='CNV Cannot Home')
        t.expect = [('帧数', 1, 'ever>=', 900, 125), ('坦克数', 1, '==', 2, 125),
                    ('空靶受伤', 1, '==', 0, 125)]
        t.bench = [('bench_watch', dict(seconds=127, every=3, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'r': probe} for name in ('aicantig', 'aicantdi', 'aicantsu')}
    return dict(CHECKS=CHECKS)


@cache
def engine_aicombat():
    """AllowRecruitUnitsInCombat: does a team take a unit that is shooting at an enemy in range?

    benches/ai/tactics/scenes.py#aicombat_bench: fighter (inserted first, in a held fight until `fight ends`) and idle (out of sight).
    First departure identity: 0 none, 1 fighter, 2 idle, 3 both in the same frame. 80-unit square per candidate.
    Prediction (recruit gate read rule): off -> idle goes first, the fighter stays even after the fight (the team is
    full at one); on -> the fighter is taken, the idle one stays home throughout.

    RESULTS (2026-11-16, run_queue, both PASS): aicombat0 -- s1-s10 1 1 0 0, s11-s55 1 0 2 184 (idle leaves f184, the
    fighter stays). aicombat1 -- s1-s28 1 1 0 0, s29-s55 0 1 1 462: the fighter is taken but shoots on where it stands
    until its foe is deleted (s30), leaves f462; the idle one never leaves. Readings: benches/ai/tactics/readings.toml#engine_aicombat.
    """
    from model import Script, Test, counted, square


    def a(m):
        t = Test()
        t.scripts += [Script('Combat - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                      Script('Combat - clock', [], [('INCREMENT_COUNTER', 1, 'CNV_RC_Clock')], once=False)]
        outside = []
        for identity, name, pos in m.cnv_candidates:
            area = f'CNV Combat {identity}'
            t.areas[area] = square(*pos, m.facts['departure radius'])
            counted(f'CNV_RC_{identity}', '战者在原位' if identity == 'fighter' else '闲者在原位',
                    t, named=name, area=area)
            outside.append(('NAMED_OUTSIDE_AREA', name, area))
        t.counters += [('CNV_RC_First', '首离身份'), ('CNV_RC_Frame', '首离帧')]
        for identity, conditions in ((3, outside), (1, outside[:1]), (2, outside[1:])):
            t.scripts.append(Script(f'Combat - first {identity}',
                                    [('COUNTER', 'CNV_RC_First', 2, 0), *conditions],
                                    [('SET_COUNTER', 'CNV_RC_First', identity),
                                     ('SET_COUNTER_TO_COUNTER', 'CNV_RC_Frame', 'CNV_RC_Clock')]))
        allow = m.facts['allow in combat']
        if allow:
            t.expect = [('闲者在原位', 1, '==', 1, 9), ('闲者在原位', 25, '==', 1, 26),
                        ('闲者在原位', 50, '==', 1, 51), ('战者在原位', 50, '==', 0, 51)]
        else:
            t.expect = [('闲者在原位', 1, '==', 1, 9), ('首离身份', 25, '==', 2, 26),
                        ('战者在原位', 25, '==', 1, 26), ('战者在原位', 50, '==', 1, 51)]
        t.bench = [('bench_watch', dict(seconds=54, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('aicombat0', 'aicombat1')}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a))


@cache
def engine_aicreate():
    """CreateUnits.UnitName / MinUnits isolated slot probe (C line).

    aicr1:a / aicr3:a: the same opener produces three Guardians, no placed tanks.
    Four unrelated Peacekeepers start at home. Prediction: only the named Guardians
    join the attack team; minimum 3 waits for the third, minimum 1 can leave earlier.
    TeamTemplate.MinUnits=1 and CreateUnits.MaxUnits=3 in both variants. Production
    itself is supplied by the opener: this does not claim CreateUnits creates units.
    No exact timing, replacement, multiple slots or MaxUnits rule is established.
    Evidence and model gaps: work/re/c_create_report.md.

    RESULTS (2026-11-11; owned / home Guardians, home Peacekeepers, named team):
    aicr1:a FAIL: s19 first Guardian, s29 1/0/2/99; s41-85 3/2/2/99.
    aicr3:a PASS: s19 1/1/4/99, s30 2/2/4/99, s41 3/3/4/99,
    s48 3/2/4/99, s49-85 3/0/4/99. Named-team membership is NOT established.
    The original aicr1 all-tanks-out / no-infantry-out expectations are retained
    as a failed prediction, not widened to PASS. Model replay is strict xfail;
    neither field is promoted. INFERRED: slot minimum plus general recruitment
    can explain the mixed departure at minimum 1; exact members are still a gap.

    FOLLOW-UP (2026-11-12, aicr1c / aicr3c, passive CNVTeams host):
    minimum 1: f301 empty/inactive -> f316 three members/active, IDs 3176/3166/3167;
    minimum 3: f316 one/inactive -> f481 two/inactive -> f646 three/active,
    IDs 3176/3177/3178. Exact activation is bounded by the previous 15-frame sample.
    Initial-position matching identifies 3166/3167 as placed Peacekeepers; attributing
    new IDs to the isolated Guardian production is INFERRED (no template log field).
    The model still dispatches three Peacekeepers at f152; no field is promoted.
    Model reading: readings.toml#engine_aicreate (the samples above in its bench text);
    full evidence: work/re/c_create_teams_report.md.
    """
    from parts import Test, Script, counted, square


    def a(m):
        t = Test()
        tank, infantry = m.cnv_units
        s1 = m.player('s1')
        area = 'CNV Create Home'
        t.areas[area] = square(*m.site('east base'), m.facts['home radius'])
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_CR_Total', '坦克总数', t, template=tank, player=s1)
        counted('CNV_CR_Home', '坦克在家', t, template=tank, player=s1, area=area)
        counted('CNV_CR_Inf', '步兵在家', t, template=infantry, player=s1, area=area)
        team = m.map.AI_TEAMS['create team']
        t.counters.append(('CNV_CR_Team', '招人队员'))
        t.scripts.append(Script('Test - unknown', [], [('SET_COUNTER', 'CNV_CR_Team', 99)], once=False))
        for n in range(9):
            t.scripts.append(Script(f'Test - members {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                                    [('SET_COUNTER', 'CNV_CR_Team', n)], once=False))
        t.expect = [('坦克总数', 70.0, '==', 3, 71.0), ('步兵在家', 70.0, '==', 4, 71.0),
                    ('坦克在家', 70.0, '==', 0, 71.0)]
        t.bench = [('bench_watch', dict(seconds=84.0, every=1, sheet=False, lines=4))]
        return t


    # c variants add the passive CNVTeams carrier, retaining the original prediction.
    # Read frame/member/active observations with teamlog; see work/re/c_create_teams_report.md.
    CHECKS = {name: {'a': a} for name in ('aicr1', 'aicr3', 'aicr1c', 'aicr3c')}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a))


def engine_aicrush():
    """Engine probe: the skirmish AI team's Crush / CrushPreference (benches/ai/tactics/scenes.py#aicrush_bench; docs/engine/aiteamstate.md).

      a  守军数     Peacekeepers the player (p1) owns (12 at the start; the guards)
         坦克数     Hammers s1 owns
         到远厂     Hammers of s1 within 300 of the far power plant
         once a second, AFTER seconds after the wake

    Expectations are the model's (l4_micro_engage.md 1.5); a FAIL is a reading too: read the speed the guards die at --
    a crush kills at once on contact, a gun takes many seconds.
      aicrush1   the guards fall below 8 within 25 s of the wake (aicrush1t too: aicrush1 with the CNVTeams carrier)
      aicrush0 / aicrushlo   the guards are still 8 or more at 25 s of the wake

    Readings (11-09, all PASS; counters 守军数 坦克数 到远厂; the AI's 4 Hammers SovietAntiVehicleVehicleTech1, the player's 12
    Peacekeepers; tanks reach the plant s15):
      aicrush1   s1-s18 12 4 4 | s19 11 | s20 9 | s21 7 | s22 4 | s23 3 | s24-25 2 | s26-27 1 | s28-s33 0 (4 tanks alive all
                 along, 9 s for 12 men); then 1 @ s34-35 and s71-74 (a stray guard counted again), tanks 4 to s79
      aicrush0   s15-s22 12 4 4 | s23-s30 12 3 3 | s31-37 11 2 2 | s38-s85 11 0 0 (the guards win: shot down, 1 guard lost)
      aicrushlo  s15-s22 12 4 4 | s23-s30 12 3 3 | s31-36 11 2 2 | s37 11 1 1 | s38-s85 11 0 0 (as aicrush0)
    """
    from benches.ai.targets.checks import engine_aitarget
    at = engine_aitarget()["shared"]
    from parts import Script, Test, counted, square

    AFTER = 70.0
    SOON = 25.0


    def a(m, build):
        t = Test()
        s1, p1 = m.player('s1'), m.player('p1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        o = m.find(m.role('far plant').name)
        t.areas[at.FAR] = square(o.x, o.y, 300.0)
        inf, tank = m.cnv_units
        counted('CNV_CR_Guards', '守军数', t, template=inf, player=p1, most=13)
        counted('CNV_CR_Tanks', '坦克数', t, template=tank, player=s1)
        counted('CNV_CR_Far', '到远厂', t, template=tank, area=at.FAR, player=s1)
        wake = m.facts['wake at']
        end = wake + AFTER
        if build in ('aicrush1', 'aicrush1t', 'aicrush1g'):
            t.expect += [('守军数', wake + SOON, '<', 8)]
        else:
            t.expect += [('守军数', wake + SOON, '>=', 8)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('aicrush1', 'aicrush0', 'aicrushlo', 'aicrush1t', 'aicrush1g')}
    return dict(CHECKS=CHECKS)


def engine_aidefense():
    """Engine probe: the AI's StaticDefense tactic, the Distance circle and the pull-back (benches/ai/tactics/scenes.py#aidefense_bench).

      a  圈300 / 圈450 / 圈650 / 圈900   Peacekeepers of s1 inside a square of half-width r centred on the AI's yard
                                      (r = 300 / 450 / 650 / 900) -- once a second from the wake to ~65 s after it

    The Peacekeepers are ordered (plain MOVE, mission second 30) to FAR, 1150 from the yard (1200, on two trees, for every
    reading below: see benches/ai/tactics/scenes.py#aidefense_bench) toward the east gate, almost due west
    (direction (-0.990, -0.141)), so a square of half-width r is the circle of radius r to within the small sideways
    drift (the yard-to-unit distance is the x-distance times ~1.01). The reading is how low each ring goes after s30 and
    when it is back at 4 (the team dragging them back inside Distance). The expectation is weak (the 900 ring holds >= 1
    at the end, readings complete); a FAIL is a reading too.

    读数
    Bench 2026-11-06 aidef250 a (CampAIDef250A, one run): FAIL 0 of 1 (the weak 圈900 >= 1 at s75). 圈300 4 -> 3 @ s33,
      1 @ s34, 0 @ s42; 圈450 4 -> 3 @ s36, 1 @ s38, 0 @ s45; 圈650 4 -> 3 @ s41, 1 @ s43, 0 @ s49; 圈900 4 -> 3 @ s48,
      1 @ s50, 0 @ s57 and 0 to the end (s80). The four Peacekeepers walked out to FAR (1200) and stayed: no pull-back.
    Bench 2026-11-06 aidef450 a (CampAIDef450A): FAIL, the same: 圈300 2 @ s33, 1 @ s34, 0 @ s41; 圈450 0 @ s45; 圈650
      0 @ s49; 圈900 0 @ s57, no return. Distance 450 instead of 250 changes nothing (+-1 s noise).
    Bench 2026-11-06 aidefupd4 a (CampAIDefUpd4A): FAIL, the same (0 @ s42 / s45 / s49 / s57; no return): UpdateTime 4 s
      changes nothing.
    Bench 2026-11-06 aidefslack a (CampAIDefSlackA): FAIL, the same: CombatLeashSlack 3.0 changes nothing.
      Caveat for all four: the move order goes through m.order (UNIT_SET_TEAM into a script team, the contract refuses a
      single-unit MOVE_NAMED_UNIT_TO), which may take the Peacekeepers out of the AI's team, so "no pull-back" may be that,
      not StaticDefense. Not yet separated; the next probe is an order that leaves the AI's team (a unit pushed by
      something else) or the unit left to walk by itself.

      b  (round 62: aidefctl / aidefctl4 / aidefmv) the four start 700 out toward the gate, no m.order; at s55 this check
         moves them to FAR by name (teleport, or MOVE_NAMED_UNIT_TO), no UNIT_SET_TEAM. Expectation: the control, 圈300
         >= 1 just before the push (the team brought them to the yard).
    Bench 2026-11-06 aidefctl b (CampAIDefCtlB, D=250 U=1 s, teleport): PASS. The control: 圈900 4 @ s1, 圈650 4 @ s2,
      圈450 4 @ s6, 圈300 4 @ s9 -- they walk to the yard from the first second, before the s10 wake script (the AI's
      state runs from the start; the wake's UNIT_AI_TRANSFER_ALL is not what starts it). The teleport: all rings 0 @ s55
      (1 left @ s54, the watch clock ~1 s off); back: 圈900 4 @ s66, 圈650 4 @ s72, 圈450 4 @ s76, 圈300 4 @ s80, and 4 4 4 4
      to the end (s120). Pulled back: StaticDefense holds the team that the earlier m.order probes had taken away.
    Bench 2026-11-06 aidefctl4 b (CampAIDefCtl4B, U=4 s): PASS. The control the same (圈300 4 @ s9); after the teleport
      圈900 4 @ s68, 圈650 4 @ s75, 圈450 4 @ s79, 圈300 4 @ s82: ~2 s later than U=1 (the next update comes up to 4 s on).
    Bench 2026-11-07 (round 70) with FAR at 1150: both teleports moved no one (4 4 4 4 from s9 to s120, PASS all the same:
      FAR sits on the river bank). So the teleports go to OUT, 1200 straight south, and a second expectation wants 圈900
      empty right after the push. Rerun: aidefctl b out at s54 (the control expectation then sat on s54; moved a second
      earlier), back 圈900 4 @ s61, 圈650 @ s66, 圈450 @ s70, 圈300 @ s73; aidefctl4 b out at s56, back s63 / s68 / s72 / s74
      (1-2 s later per ring). The straight walk back over open grass is 7-8 s quicker than 11-06's westward one.
    Bench 2026-11-06 aidefmv b (CampAIDefMvB, MOVE_NAMED_UNIT_TO): PASS. The control the same; after the move order no ring
      ever drops (4 4 4 4 from s9 to s120): never 300 out.
      c  (aidefmv) the same with rings 100 / 175 / 225 / 275, to see how far the script move gets.
    Bench 2026-11-06 aidefmv c (CampAIDefMvC): PASS. 圈100 1 @ s54-55, 2 @ s56, 4 @ s57 to the end; 圈175 / 225 / 275 hold 4
      throughout: called back before 175, long before Distance 250, and no back and forth. Read as the aesthetics-off
      re-gather (ready and the centre more than 100 off -> attack-move to the point), with the members' ready test using
      their stale standing records; the model matches it since round 64 (RA3-EngineModel tests/test_ai_defense.py).
    """
    from parts import Script, Test, counted, square

    LAG = 4.0
    AFTER = 65.0
    RINGS = (300.0, 450.0, 650.0, 900.0)


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        (inf,) = m.cnv_units
        x, y = m.site('east base')
        for r in RINGS:
            area = f'CNV AD Ring {int(r)}'
            t.areas[area] = square(x, y, r)
            counted(f'CNV_AD_{int(r)}', f'圈{int(r)}', t, template=inf, area=area, player=s1)
        w = m.facts['wake at']
        end = w + AFTER
        t.expect += [('圈900', end, '>=', 1, end + 1)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    PUSH_AFTER = 105.0


    def push(how, rings=RINGS, to='CNV AI Far'):
        """Round 62 (missions aidefctl / aidefctl4 / aidefmv): the four start 700 out, so the rings filling after the wake
        is the control (the team formed and walks to the yard it defends); at 'push at' this script moves them out to `to`
        by name, with no UNIT_SET_TEAM (how: UNIT_TELEPORT_TO_WAYPOINT or MOVE_NAMED_UNIT_TO). A teleport must empty the
        outer ring right after (round 70: the teleport to FAR at 1150 moved no one and the check still passed)."""
        def b(m):
            t = Test()
            s1 = m.player('s1')
            t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
            (inf,) = m.cnv_units
            x, y = m.site('east base')
            for r in rings:
                area = f'CNV AD Ring {int(r)}'
                t.areas[area] = square(x, y, r)
                counted(f'CNV_AD_{int(r)}', f'圈{int(r)}', t, template=inf, area=area, player=s1)
            t.scripts.append(Script('Test - push', [('TIMER_EXPIRED', 'CNV AI Push')],
                                    [(how, m.role(f'peacekeeper {k}').name, to) for k in range(1, 5)]))
            w, p = m.facts['wake at'], m.facts['push at']
            end = w + PUSH_AFTER
            # the control: the team brought them to the yard (a second early: the watch clock runs ~1 s off, round 70)
            t.expect += [(f'圈{int(rings[-1])}', p - 2, '>=', 1, p - 1)]
            if how == 'UNIT_TELEPORT_TO_WAYPOINT':
                t.expect += [(f'圈{int(rings[-1])}', p, 'ever<=', 0, p + 5)]     # the teleport took them out
            t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
            return t
        return b


    CHECKS = {k: {'a': a} for k in ('aidef250', 'aidef450', 'aidefupd4', 'aidefslack')}
    CHECKS |= {'aidefctl': {'b': push('UNIT_TELEPORT_TO_WAYPOINT', to='CNV AI Out')},
               'aidefctl4': {'b': push('UNIT_TELEPORT_TO_WAYPOINT', to='CNV AI Out')},
               'aidefmv': {'b': push('MOVE_NAMED_UNIT_TO'), 'c': push('MOVE_NAMED_UNIT_TO', (100.0, 175.0, 225.0, 275.0))}}
    return dict(CHECKS=CHECKS)


def engine_aidelay():
    """MaximumDelay-only pair on the successful aimicspon Hunt team.

    Prediction before bench: zero permits both warriors to charge together; long
    still permits the first charge, then samples a RUSH_ATTACK cooldown in 0..999s.
    Thus long is expected to have no simultaneous pair in the automatic window,
    but that is a sampled prediction, NOT a deterministic lower-bound guarantee.
    Both builds keep MinimumDelay=0, no team delay, the same update/health/targets.
    The old aimicmed all-zero run is not a successful delay control.
    Only the automatic window is measured; remove the inherited manual warrior.

    Bench 2026-11-11, aidelay0:a PASS: two warriors from s20, charging one at
    s33 and two at s34-s42; Ever grows from 11 at s33 to 146 at s42.
    aidelay999:a PASS: two warriors from s20, one charging at s33-s42,
    none from s43; Ever 11 at s33 and 142 at s42. Both first-seen clocks
    give Frames - Ever = 362 after wake (24 positive samples per build).
    This is the latched script observation clock, not an internal dispatch frame.
    This single pair does not measure the RNG distribution. Sim.cond now supports
    the player status count (A round 164); benches/ai/tactics/readings.toml#engine_aidelay replays these
    script counters.
    """
    ac = engine_aimicro()["shared"]
    from parts import Script, Test, counted, status


    def check(m):
        t = ac.probe_built(m, 'aimicspon')
        t.scripts = [s for s in t.scripts if s.name not in ('Test - control make', 'Test - control press')]
        t.expect = [('造出', 14, 'ever>=', 2, 50), ('曾冲', 14, 'ever>=', 1, 50)]
        t.expect += [('冲', 14, '<=', 1, 50)] if m.facts['delayed'] else [('冲', 14, 'ever>=', 2, 50)]
        t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
        return t


    Y_LO, Y_HI, Y_STEP = 2480, 3160, 10     # the bands: the conscripts walk north from y 2520, the warriors south
    X_LO, X_HI = 3300.0, 4400.0              # wide in x: only the y of each side is read
    W_EDGES = [2000, *range(2700, 3061, 30), 3600]   # run 2: 14 non-overlapping warrior bands [lo, hi), read as lo


    def where(m):
        """p (A round 248, H1: where do the two sides stop): four counters show world y in 10-unit steps, every frame:
          动1y / 动2y  conscript k's y: the largest Y with it in {y > Y}  -> its y in (Y, Y + 10]
          武前y / 武后y  the southmost / northmost s1 warrior: the band [lo, hi) of W_EDGES it is in, read as lo
                       (run 2; 2000 = below 2700, 3060 = 3060 or above)
        0 = nobody in any band. Each counter is zeroed, then the band scripts run in order and the last true one wins
        (scripts run in order: model.counted's owner readout). The approach is along y (sim: dx ~26 at the stop), so the
        y gap is the stop distance less a few units. The conscripts stand at y 2520 till the go: their first rows calibrate
        how a band counts a unit (centre or footprint).
        Sim (model 9880258): 动1y / 动2y 2520 to s23, stop at 2700 from s28; 武前y 2850, 武后y 2860.
        Bench 2026-11-15 aidelay0:p FAIL (CampADZeroP_mcp_1115_151702, one run): 动1y / 动2y 2510 (placed at 2520: the
        centre, strict) to s19, walk from s20, 2740 / 2700 at s24, 3030 / 2950 from s31 to s42 (the barracks centre is
        y 3000, the attack-move's end), conscript 1 out of every band from s43, 2 from s45 -- they walk ~300 past the
        simulator's stop. 武前y 0 throughout and 武后y 2540 from s15 to s46: not a position (a warrior below no
        {y < Y} yet above only {y > 2540}). INFERRED: the type-in-area count sees only the first few areas (the bands
        2480..2540, 14 areas) -- an area cap or a per-object cap on the areas it is counted in; NAMED_INSIDE_AREA
        is not affected. Where the warriors stood is not read.
        Run 2 (A round 249): the warrior readouts moved to 14 non-overlapping bands written first in the areas (83 areas,
        the Test S half dropped). Sim: 武前y 2910 s19-s23, 2820 s28-s34, 2850 to s42; 武后y 2850-2970; conscripts as above.
        Bench 2026-11-15 aidelay0:p PASS (CampADZeroP_mcp_1115_153330): the warrior readouts are positions now (front <=
        back every second), so the run-1 failure was the area count / order (H5 supported; cap or order not split).
        Conscripts 2510 to s19, 2730 / 2700 s24, 2750 / 2700 s25 (conscript 2 pauses at the sim's stop 2700), 2780 / 2740
        s26, then on to 3030 / 2950 from s32. Warriors: 2940 s15, 2910 s16-s22, 2850 s23-s26 (the sim's 2820-2850), then
        NORTH: 2910 s27, 2970 s28, 3000 s29, >= 3060 s30-s33, back south from s34 (3030 ... 2910 s39-s46). So the two
        sides first meet at the sim's gap (H1, a deeper stop, not supported; H4, warriors staying home, not either); the
        bench differs after: the warriors withdraw north s27-s30 and the conscripts follow to the attack-move's end
        (INFERRED; only y is read, x unknown)."""
        t = check(m)
        s1 = m.player('s1')
        warrior = m.cnv_units[0]
        ys = list(range(Y_LO, Y_HI + 1, Y_STEP))
        areas = {f'Test W {lo}': [(X_LO, lo), (X_HI, lo), (X_HI, hi), (X_LO, hi)] for lo, hi in zip(W_EDGES, W_EDGES[1:])}
        areas.update({f'Test N {y}': [(X_LO, y), (X_HI, y), (X_HI, 3600.0), (X_LO, 3600.0)] for y in ys})   # y > Y
        t.areas = {**areas, **t.areas}   # the warrior bands first (run 1: the type count saw only the first ~14 areas)
        t.counters = []
        readouts = [(f'CNV_AD_C{k}', f'动{k}y', lambda y, n=r.name: ('NAMED_INSIDE_AREA', n, f'Test N {y}'), ys)
                    for k, r in enumerate(m.roles('conscript'), 1)]
        bands = W_EDGES[:-1]
        readouts += [('CNV_AD_WF', '武前y', lambda y: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1,
                                                        warrior, f'Test W {y}'), bands[::-1]),
                     ('CNV_AD_WB', '武后y', lambda y: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1,
                                                        warrior, f'Test W {y}'), bands)]
        for counter, label, cond, order in readouts:
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
            t.scripts += [Script(f'Test - {counter} {y}', [cond(y)], [('SET_COUNTER', counter, y)], once=False)
                          for y in order]
        t.expect = [('动1y', 1, 'ever>=', Y_LO, 50), ('武前y', 1, 'ever>=', W_EDGES[0], 50)]
        t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
        return t


    def toggled(m):
        """t (aidelaytog*): s1's always-switching Peacekeepers, counted by player every frame, shown each second:
          造出  how many s1 owns          盾  how many have the shield up (GENERIC_TOGGLE_STATE)
          曾落 / 曾双  frames since s1 first had none up again after one was / two up at once
        Predicted (benches/ai/tactics/scenes.py#aidelay_bench): the TOGGLE_ALWAYS line -- one up for good, 曾落 and 曾双 never; the
        TOGGLE_DEFAULT line -- 曾落 and 曾双 both (the two switch together every round)."""
        t = Test()
        p1, s1, shield = m.player('p1'), m.player('s1'), status('GENERIC_TOGGLE_STATE')
        t.scripts += [Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]),
                      Script('Test - keep the conscripts up', [],
                             [('UNIT_SET_HEALTH', r.name, 100.0) for r in m.roles('conscript')], once=False),
                      Script('Test - one up', [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', s1, 3, 1, shield)],
                             [('SET_FLAG', 'Test One Up', 1)])]
        counted('CNV_AD_Owned', '造出', t, template=m.cnv_units[0], player=s1)
        counted('CNV_AD_Up', '盾', t, status=shield, player=s1)
        seen = [('CNV_AD_Down', '曾落', [('FLAG', 'Test One Up', 1), (2, 0)]), ('CNV_AD_Two', '曾双', [(3, 2)])]
        for counter, label, (*flag, (op, n)) in seen:
            t.counters.append((counter, label))
            cond = [*flag, ('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', s1, op, n, shield)]
            t.scripts += [Script(f'Test - {counter} seen', cond, [('SET_FLAG', f'Test {counter}', 1)]),
                          Script(f'Test - {counter} count', [('FLAG', f'Test {counter}', 1)],
                                 [('INCREMENT_COUNTER', 1, counter)], once=False)]
        end = 80 if 'lock team' in m.facts else 50      # ailock*: the angels build 10 s each (aidelay_bench.lock)
        up = [('盾', 14, 'ever>=', 1, end), ('曾双', 14, '==', 0, end)] if m.facts['delayed'] \
            else [('盾', 14, '==', 0, end)] if 'lock team' in m.facts \
            else [('曾落', 14, 'ever>=', 1, end), ('曾双', 14, 'ever>=', 1, end)]
        if m.facts['delayed'] and 'lock team' not in m.facts:
            up.append(('曾落', 14, '==', 0, end))
        t.expect = [('造出', 14, 'ever>=', 2, end), *up]
        t.bench = [('bench_watch', dict(seconds=end, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {key: {'a': check} for key in ('aidelay0', 'aidelay999', 'aidelaytype', 'aidelaymin', 'aidelayteam',
                                                 'aidelayteammin')}
    CHECKS.update({key: {'t': toggled} for key in ('aidelaytog', 'aidelaytogdef', 'ailock2', 'ailock1', 'ailockm')})
    CHECKS['aidelay0']['p'] = where
    return dict(CHECKS=CHECKS)


def engine_aidiff():
    """Engine probe: StrategicState Difficulty (benches/ai/tactics/scenes.py#aidiff_bench) -- two always-on states, one listed for MEDIUM,
    one for EASY HARD BRUTAL, each sending one unit type: which type leaves, and at which campaign difficulty?

      a  难度       the campaign difficulty the bench walked into: 1 easy, 2 normal, 3 hard (scripts with one
                    difficulty bit each, the script header's bits)
         坦克在家   Guardians of s1 inside the base area (450 around the east base), once a second
         步兵在家   Peacekeepers of s1 there

    Expected (the mission's facts, the model's guess): 难度 2 and at s40 坦克在家 / 步兵在家 == expect tanks / infantry
    home (only the state listed for MEDIUM runs).

    读数
    Bench 2026-11-09 (B round 79, one run each, PASS 3 of 3 each):
      aidiff  a: 难度 2 throughout (the bench walks the campaign at normal); 坦克在家 4 -> 1 @ s15, 0 from s16 to s55;
              步兵在家 4 to s55 -- only the state listed MEDIUM sent its team.
      aidiffx a (the lists swapped): 难度 2; 步兵在家 4 -> 1 @ s16, 0 from s17; 坦克在家 4 to s55.
    So campaign normal = AI difficulty MEDIUM (simai's DIFFICULTY map), and a state not listed for it never runs.
    The simulator gives the same two (benches/ai/tactics/readings.toml#engine_aidiff only_the_states_listed_for_the_difficulty_run).
    """
    from parts import Test, counted, square, Script

    AREA = 'CNV AI Base Area'
    LAG = 4.0
    AT, SECONDS = 40.0, 50.0
    DIFF = 'CNV_Diff'


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.counters.append((DIFF, '难度'))
        t.scripts += [Script(f'Test - difficulty {k + 1}', [], [('SET_COUNTER', DIFF, k + 1)], once=False,
                             levels=tuple(j == k for j in range(3))) for k in range(3)]
        t.areas[AREA] = square(*m.site('east base'), 450.0)
        tank, inf = m.cnv_units
        counted('CNV_D_Tanks', '坦克在家', t, template=tank, area=AREA, player=s1)
        counted('CNV_D_Inf', '步兵在家', t, template=inf, area=AREA, player=s1)
        t.expect += [('难度', 5.0, '==', 2, 6.0),
                     ('坦克在家', AT, '==', m.facts['expect tanks home'], AT + 1),
                     ('步兵在家', AT, '==', m.facts['expect infantry home'], AT + 1)]
        t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a} for k in ('aidiff', 'aidiffx')}
    return dict(CHECKS=CHECKS)


def engine_aidistance():
    """Distance 250/2000: retained StaticDefense Guardian displaced 1200 south.

    Only Distance differs in the original pair. The 2000 build now also carries
    CNVTeams (15-frame samples); named square occupancy alone does not observe
    dynamic team membership or exact radial geometry. The per-frame displacement latch
    proves teleport success independently of screenshot timing. Predictions are
    recorded before bench execution in work/re/c_distance_report.md.

    RESULTS: both builds PASS (five endpoint checks each). Small returns to the
    900 square at s33, 300 at s41. Large leaves 300 at s15 before the teleport,
    returns inside 900 at s34, then leaves 900 again at s56. Both remain alive.
    The model then matched endpoints but missed the large group's excursion; it
    now holds: readings.toml#engine_aidistance. Aesthetics remains gap.

    E92: the initial Guardian's ID persists across 68 position samples. Its
    (300, 900) square occupancy changes at frames 166/256/451/541/871:
    11 -> 01 -> 00 -> 01 -> 00. The model only reproduces 11 -> 00.
    One extra member appears only at frame 391; its identity remains a gap.
    Raw log, trajectory assertions and same-frame comparison: work/re/e_distance_e92.md.
    """
    from model import Script, Test, counted, square


    def a(m):
        t = Test()
        name = m.role('ai guardian 1').name
        for radius in (300, 900):
            area = f'CNV Distance Ring {radius}'
            t.areas[area] = square(*m.site('east base'), radius)
            counted(f'CNV_D_R{radius}', f'圈{radius}', t, named=name, area=area)
        t.counters += [('CNV_D_Pushed', '曾出圈')]
        t.scripts += [Script('Distance - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                      Script('Distance - displacement', [('NAMED_OUTSIDE_AREA', name, 'CNV Distance Ring 900')],
                             [('SET_COUNTER', 'CNV_D_Pushed', 1)])]
        counted('CNV_D_Alive', '坦克总数', t, template=m.cnv_units[0], player=m.player('s1'))
        home = int(m.facts['distance'] == 250)
        t.expect = [('圈900', 20, '==', 1, 21), ('曾出圈', 65, '==', 1, 66),
                    ('坦克总数', 65, '==', 1, 66), ('圈300', 65, '==', home, 66),
                    ('圈900', 65, '==', home, 66)]
        t.bench = [('bench_watch', dict(seconds=74, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('aidist250', 'aidist2000')}
    return dict(CHECKS=CHECKS)


def engine_aidodge():
    """DodgeThreats on/off, native precision-strike beacon, recruited Hunt warriors.

    Prediction: both warriors fight inside the 150-half-side square before s30;
    with DodgeThreats on at least one leaves during s30..34, off both stay.
    Conscripts are kept healthy; powers and injured pullback are off. The beacon
    dispatches no damage or push (the ordinary infantry fight still deals damage).
    This square tests a movement difference, not the exact 200 safety radius.

    MEASURED: named beacon on/off both present, two living warriors; on leaves
    (frame 468: near 1, 479: 0), off stays (456..501: near 2). The bench capture
    seconds drift against the frame counter: on's automatic seconds-window verdict
    is FAIL, off PASS. Keep that diagnostic failure visible; replay by game frames
    in tests/test_ai_dodge.py. A clock-stable engine acceptance check remains a gap,
    the bounded single-beacon consumer is replayed there. Exact timing, safety-circle
    boundaries, general filters and multi-threat choice remain gaps (work/re/e116_dodge.md).
    """
    from model import Script, Test, counted, square, status


    def probe(m):
        t = Test()
        s1 = m.player('s1')
        warrior = m.cnv_units[0]
        at = m.facts['threat at']
        end = at + m.facts['threat lifetime']
        area = 'CNV Dodge Sample'
        t.areas[area] = square(*m.point('dodge spot'), m.facts['sample half size'])
        t.scripts += [Script('Dodge - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                      Script('Dodge - frame', [], [('INCREMENT_COUNTER', 1, 'CNV_Dodge_Frame')], once=False),
                      Script('Dodge - health', [],
                             [('UNIT_SET_HEALTH', r.name, 100.0) for r in m.roles('conscript')], once=False)]
        t.counters.append(('CNV_Dodge_Frame', '帧数'))
        counted('CNV_Dodge_Own', '造出', t, template=warrior, player=s1)
        counted('CNV_Dodge_Near', '范围', t, template=warrior, player=s1, area=area)
        # The native beacon's player ownership count stayed 0 on this probe.
        # Query the named object itself, so 0 cannot be mistaken for no threat.
        t.counters.append(('CNV_Dodge_Beacon', '威胁'))
        beacon = m.cnv_named['beacon']
        t.scripts += [Script('Dodge - beacon alive', [('NAMED_NOT_DESTROYED', beacon)],
                             [('SET_COUNTER', 'CNV_Dodge_Beacon', 1)], once=False),
                      Script('Dodge - beacon gone', [('NAMED_DESTROYED', beacon)],
                             [('SET_COUNTER', 'CNV_Dodge_Beacon', 0)], once=False)]
        t.expect += [('造出', at - 3, '==', 2, end), ('范围', at - 3, '==', 2, at - 1),
                     ('威胁', at, 'ever>=', 1, end),
                     ('范围', at + 1, 'ever<=' if m.facts['dodge enabled'] else '==',
                      1 if m.facts['dodge enabled'] else 2, end)]
        t.bench = [('bench_watch', dict(seconds=end + 3, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'r': probe} for name in ('aidodgeon', 'aidodgeoff')}


    def timing(m):
        """Fixed 0/2 second contrast, latched in game frames (work/re/e117_dodge_clock.md).

        Prediction: both start with two living warriors in the same square; zero
        leaves sooner after the beacon. Leaving includes walking time, so neither
        latch measures the exact reaction frame. Random ranges remain a gap.

        MEASURED: both born f451; zero first leaves f454, two f486; bad stays 0.
        Replay asserts their order, not exact departure frames (model: 475/505).
        """
        t = probe(m)
        frame, born, left, bad = ('CNV_Dodge_Frame', 'CNV_Dodge_Born',
                                  'CNV_Dodge_Left', 'CNV_Dodge_Bad')
        live = [('NAMED_NOT_DESTROYED', m.cnv_named['beacon'])]
        t.scripts += [
            Script('Dodge - born latch', live,
                   [('SET_COUNTER_TO_COUNTER', born, frame)]),
            Script('Dodge - leave latch', live + [('COUNTER', born, 3, 1),
                                                 ('COUNTER', 'CNV_Dodge_Near', 0, 2)],
                   [('SET_COUNTER_TO_COUNTER', left, frame)])]
        # Keep the same count scripts, but display the latches within the four-line HUD.
        # Any missing member, or a pre-beacon departure, invalidates this contrast.
        for counter in ('CNV_Dodge_Own', 'CNV_Dodge_Near'):
            for op, value in ((0, 2), (4, 2)):
                t.scripts.append(Script(f'Dodge - prerequisite {counter} {op}',
                    [('COUNTER', frame, 3, 405), ('COUNTER', frame, 0, 450),
                     ('COUNTER', counter, op, value)], [('SET_COUNTER', bad, 1)]))
        for op in (0, 4):
            t.scripts.append(Script(f'Dodge - survival {op}', live +
                [('COUNTER', 'CNV_Dodge_Own', op, 2)], [('SET_COUNTER', bad, 1)]))
        t.counters = [(frame, '帧数'), (born, '出现'), (left, '离开'), (bad, '失配')]
        t.expect = [('出现', 1, 'ever>=', 1, 45), ('离开', 1, 'ever>=', 1, 45),
                    ('失配', 1, '==', 0, 45)]
        t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
        return t


    def death(m):
        """timing, the fourth line the first frame a warrior is gone (A round 258).

        Prediction (model after A round 230, attack-movers aim from the frame they get in range): both conscripts
        shoot the nearer warrior from ~f392, 2 x ~10.6 dps on its 160 HP, dead ~f505 -- before the beacon ends
        (~f511), so 'two''s first-leave latch is that death, not a departure. The bench kept both alive while the
        beacon lived (timing: bad 0), so its death latch is > ~f511 or 0 (none by s45).
        """
        t = timing(m)
        frame, dead = 'CNV_Dodge_Frame', 'CNV_Dodge_Dead'
        t.scripts.append(Script('Dodge - death latch', [('COUNTER', frame, 3, 405),
                                                        ('COUNTER', 'CNV_Dodge_Own', 0, 2)],
                                [('SET_COUNTER_TO_COUNTER', dead, frame)]))
        t.counters = t.counters[:3] + [(dead, '阵亡')]
        # Bench 11-16 (A258): the game ran ~5 frames a second, the frame counter was at f301 by s73 -- no reading.
        # Watch long enough to pass the beacon even when the bench runs slow.
        # 11-16 (A259): 200 s, the CPU was still at 100 % (other lines' tests); the game ran ~12 frames a second.
        # RESULTS A259 (PASS, 257 s): born 451, left 454, first warrior gone at f706 -- the simulator's f511 is ~195
        # frames early. Simulator (a259_hp): both conscripts shoot warrior 289 from f398 (2 x 10.6 dps, 160 HP), the
        # beacon (3850, 2900) sends it radially north to (3842, 2700), into the conscripts (2709), dead f510. Unsplit:
        # later first shot, split fire, or another escape direction (the radial escape is INFERRED, micro.dodge_tick).
        t.expect = [('出现', 1, 'ever>=', 1, 200), ('离开', 1, 'ever>=', 1, 200)]
        t.bench = [('bench_watch', dict(seconds=200, every=1, sheet=False, lines=4))]
        return t


    def split(m):
        """death's mission unchanged; tells apart the three readings of its f706 (A round 260).

        Named, handed-over warriors would not do: the recruiters refuse handed-over units (engine_aimicro, round 18),
        so the AI-built pair stays and the check latches both deaths instead of reading health. Lines: frame, the first
        and the second warrior gone (Own 2 -> 1, Own -> 0, from f405), and how many warriors stand in a band north of the
        sample square (150 deep, toward the conscripts), every second.
        Focus fire (both conscripts on one warrior, 2 x 10.6 dps, 160 HP) puts the second death >= ~110 frames after the
        first; split fire (one each) puts them close together. The band tells whether the dodge goes north (the
        simulator's radial escape, INFERRED) or elsewhere.
        Simulator (model RA3-EngineModel-a, work/logs/a260_s.py): zero 511 / 867, band 2 at s33, 1 at s34..35, then 0;
        two 511 / 918.
        RESULTS A260 zero (PASS, 235 s, ~15 frames a second): deaths 706 / 724 -- 18 frames apart: split fire (or both
        hit together), not the simulator's focus fire; the band 0 every second (s1..s218): no warrior dodged north.
        """
        t = death(m)
        frame, dead, dead2, band = 'CNV_Dodge_Frame', 'CNV_Dodge_Dead', 'CNV_Dodge_Dead2', 'CNV_Dodge_North'
        x, y = m.point('dodge spot')
        half = m.facts['sample half size']
        area = 'CNV Dodge North'
        t.areas = {area: [(x - half, y - half - 150), (x + half, y - half - 150), (x + half, y - half),
                          (x - half, y - half)], **t.areas}
        t.scripts.append(Script('Dodge - second death latch', [('COUNTER', frame, 3, 405),
                                                               ('COUNTER', 'CNV_Dodge_Own', 2, 0)],
                                [('SET_COUNTER_TO_COUNTER', dead2, frame)]))
        counted(band, '北带', t, template=m.cnv_units[0], player=m.player('s1'), area=area)
        t.counters = [(frame, '帧数'), (dead, '阵亡'), (dead2, '再亡'), (band, '北带')]
        t.expect = [('阵亡', 1, 'ever>=', 1, 200)]
        t.bench = [('bench_watch', dict(seconds=200, every=1, sheet=False, lines=4))]
        return t


    def unpowered(m):
        """split's mission with s1's protocol points taken away; tells whether H6 makes the bench's f706 (A round 263).

        A round 262: on the bench s1 (Allied, starting point 1) put a freezing power on the east conscript (red f382,
        frozen white f397, ice and a sky beam f427..f503); the simulator's AI casts no player power. The program buys
        from frame 10 (simtech.Book.ai_buy), so a frame-0 script with points and their cap at 0 (as plan.py's
        '技能 否') leaves it nothing to buy or cast. Lines: the first and second warrior gone (as split), how many
        frames any p1 object is UNDER_FROZEN (AttributeModifer_CryoBeam_10's status; only adds), and how many
        conscripts stand deep, past the simulator's stop (y >= 2780, up to the sample square's far edge).
        H6 holds if the first death comes back near the simulator's ~511, frozen stays 0 and deep stays 0 before it.
        Simulator (powers never cast): deaths 511 / 867, frozen 0, deep 0 (conscripts stop at ~2710).
        RESULTS A263 zero (PASS, 221 s): deaths 527 / 777, frozen 0 all 204 s, deep 1 from s31 (s36-37 0), 2 from s52.
        H6 holds: without s1's power the first death is back to 527 (split's 706 was the freeze); focus fire (250
        frames apart). Left: one conscript stands past 2780 before the first death (the simulator's stop ~2710), and
        the second death is 90 frames before the simulator's -- the H5a gap (start / speed / stop depth), not H6.
        """
        t = split(m)
        s1, p1 = m.player('s1'), m.player('p1')
        frame, frozen, deep = 'CNV_Dodge_Frame', 'CNV_Dodge_Frozen', 'CNV_Dodge_Deep'
        x, y = m.point('dodge spot')
        half = m.facts['sample half size']
        area = 'CNV Dodge Deep'
        t.areas.pop('CNV Dodge North')
        t.areas = {area: [(x - half, 2780.0), (x + half, 2780.0), (x + half, y + half), (x - half, y + half)],
                   **t.areas}
        t.scripts = [s for s in t.scripts if 'CNV_Dodge_North' not in str(s)]
        t.scripts.insert(0, Script('Dodge - no powers', [], [('PLAYER_SET_MAX_PLAYER_POWER_POINTS', s1, 0),
                                                             ('PLAYER_SET_PLAYER_POWER_POINTS', s1, 0)]))
        t.scripts.append(Script('Dodge - frozen frames',
                                [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', p1, 3, 1, status('UNDER_FROZEN'))],
                                [('INCREMENT_COUNTER', 1, frozen)], once=False))
        counted(deep, '深入', t, template='SovietAntiInfantryInfantry', player=p1, area=area)
        t.counters = [('CNV_Dodge_Dead', '阵亡'), ('CNV_Dodge_Dead2', '再亡'), (frozen, '冻住'), (deep, '深入')]
        assert frame in str(t.scripts)
        return t


    BANDS = (2550.0, 2750.0, 2850.0, 2950.0, 3050.0, 3150.0, 3350.0)


    def where(m):
        """timing's latches with s1's powers off (as unpowered), plus where the two warriors stand (A round 265, H7).

        The simulator cannot cast the AI's player powers (A round 262), so timing's bench reading (powers on) is not
        the simulator's mission. Lines: frame, born, left (timing's latches) and the warriors' y bands as digits --
        digit k (units = k 0) = how many of s1's warriors stand in band k, north to south: y 2550-2750 (toward the
        conscripts), 2750-2850, 2850-2950 (the beacon at 2900), 2950-3050, 3050-3150, 3150-3350; x 3600-4100. So 1100
        = one in 2850-2950 and one in 2950-3050. The sample square is y 2750-3050 (bands 1..3).
        Simulator (model RA3-EngineModel-a 8f5d7c3, work/logs/a265_y.py): before the beacon one warrior at y 2841, one
        at 2863 (110); both in 2750-2850 by f465 (20); zero leaves f482, two's first warrior dies f511 at y 2818 (the
        latch is the death).
        RESULTS A265 (zero 183 s -- the run's judge crashed on a stale expectation, the frames re-read with
        work/logs/a265_reread.py; two PASS 165 s): both born f451; before it both warriors in 2850-2950 (200) from f339;
        zero: 20 by f466, left f490, 11 at f504, 2 at f526, one gone by f535, none by f777; two: 20 at f497, one gone
        and left f506, the other alone at 10, none by f785. So H7 is false: without the power the warriors stand where
        the simulator puts them (within one band) and both dodge north; e117's three-frame departure was the freeze.
        """
        t = timing(m)
        s1 = m.player('s1')
        x, _ = m.point('dodge spot')
        band = 'CNV_Dodge_Band'
        areas = {}
        parts = []
        for k, (y0, y1) in enumerate(zip(BANDS, BANDS[1:])):
            area = f'CNV Dodge Band {k}'
            areas[area] = [(x - 250, y0), (x + 250, y0), (x + 250, y1), (x - 250, y1)]
            parts += [Script(f'Dodge - band {k} {n}',
                             [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 2, n,
                               m.cnv_units[0], area)],
                             [('INCREMENT_COUNTER', n * 10 ** k, band)], once=False) for n in (1, 2)]
        # non-overlapping bands first: a type-in-area count keeps only the first ~7 declared areas (know-how, H5)
        t.areas = {**areas, **t.areas}
        t.scripts.insert(0, Script('Dodge - no powers', [], [('PLAYER_SET_MAX_PLAYER_POWER_POINTS', s1, 0),
                                                             ('PLAYER_SET_PLAYER_POWER_POINTS', s1, 0)]))
        t.scripts.append(Script('Dodge - band zero', [], [('SET_COUNTER', band, 0)], once=False))
        t.scripts += parts
        t.counters = t.counters[:3] + [(band, '武士带')]
        t.expect = [('出现', 1, 'ever>=', 1, 55), ('离开', 1, 'ever>=', 1, 55)]
        t.bench = [('bench_watch', dict(seconds=60, every=0.5, sheet=False, lines=4))]
        return t


    CHECKS.update({name: {'r': timing, 'd': death, 's': split, 'n': unpowered, 'y': where}
                   for name in ('aidodgezero', 'aidodgetwo')})
    return dict(CHECKS=CHECKS)


def engine_aiengineer():
    """Engineer tactic isolation: named target ownership, approach and survival.

    INFERRED competing prediction: Engineer captures the enemy plant and consumes
    the engineer; SimpleAttack only approaches it. CaptureAnything micro and
    CreateUnits are intentionally absent in both lanes. A failure narrows this
    prediction, rather than establishing that Engineer cannot capture in retail.
    Four direct counters avoid uncallable dynamic team names. See
    work/re/c_engineer_report.md for pre-run model prediction and measured scope.

    MEASURED (2026-11-12): Engineer s1-63 and control s1-74 both read
    owner0/near0/live1/HP100. Both retain the original diagnostic FAIL.
    The model replays these counters, but neither lane establishes recruitment
    or a target dispatch. Engineer stays a gap; no tactic rule is promoted.
    """
    from model import Script, Test, counted, square


    def a(m):
        t = Test()
        engineer, target = m.cnv_named['engineer'], m.cnv_named['target']
        t.areas['Engineer target'] = square(*m.point('engineer target'), 180)
        t.scripts.append(Script('Engineer - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        counted('CNV_E_Owner', '目标归属', t, owner=target, player=m.player('s1'))
        counted('CNV_E_Near', '到目标量', t, named=engineer, area='Engineer target')
        counted('CNV_E_Live', '工程师量', t, template='AlliedEngineer', player=m.player('s1'))
        counted('CNV_E_HP', '目标血量', t, health=target)
        t.expect = [('目标归属', 1, '==', 0, 7), ('工程师量', 1, '==', 1, 7),
                    ('到目标量', 12, 'ever==', 1, 50), ('目标血量', 1, '==', 100)]
        if m.facts['engineer tactic']:
            t.expect += [('目标归属', 20, 'ever==', 1, 60), ('工程师量', 20, 'ever==', 0, 60)]
        else:
            t.expect += [('目标归属', 1, '==', 0), ('工程师量', 1, '==', 1)]
        t.bench = [('bench_watch', dict(seconds=62, every=2, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('aieng', 'aiengctl')}
    return dict(CHECKS=CHECKS)


def engine_aifallback():
    """RetreatMinDistanceToFallback diagnostic (benches/ai/tactics/scenes.py#aifallback_bench).

    Prediction: both leave home and enter the far-plant area alive. A 500-unit
    continuation latch carries the team farther home than 100 once the hostile
    list clears. Keep FromBase=300 and every other airetf setting unchanged.
    Home/far/midway counts observe the outward and return trips, not the internal
    state's exact exit or its distance from the dynamically chosen retreat start.
    No exact-distance or independent exit-condition claim can be made from these
    four counters alone.

    Bench 2026-11-11, both positive-control checks PASS (home/far/alive/midway):
      short100: home0 s21-32; far2 s24-25; midway4 s26-32; home4 s35-52;
                home2 s53 (leaves again), alive4 through s60, 3 from s61.
      long500:  home0 s21-28; far2 s24-25; midway4 s26-28; home4 s31-48;
                home2 s49 (leaves again), alive4 through s56, 3 from s57.
    Both stay home about 18 seconds. The old model departed short before long
    (rows38/42). Recording the outstanding retreat order fixes premature readiness:
    the model now returns at rows36/32 and departs at rows53/49, waiting 17 samples
    in both builds. Row indices are not exact engine seconds.
    tests/test_simai_fallback.py asserts alive return, a 15..20 sample home wait
    and long-before-short departure. Registration covers this fixed FromBase=300
    behavioral replay; internal exit position, exact-distance boundaries and other
    base choices remain unmeasured.
    """
    ar = engine_airetreat()["shared"]
    from parts import counted, square


    def a(m):
        t = ar.a(m, 'airetf')
        # Keep only the common departure positive control: do not pre-assume home.
        t.expect = [('步兵在家', m.facts['wake at'] + 5, 'ever==', 0, 60)]
        x, y = m.facts['fallback midway']
        area = 'CNV Fallback Midway'
        t.areas[area] = square(x, y, 150)
        (inf,) = m.cnv_units
        counted('CNV_FB_Mid', '中途人数', t, template=inf, area=area, player=m.player('s1'))
        t.expect.append(('到远厂', 1, 'ever>=', 1, m.facts['wake at'] + 35))
        t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {k: {'a': a} for k in ('aifbshort', 'aifbshortt', 'aifblong')}
    return dict(CHECKS=CHECKS)


def engine_aigarrison():
    """Engine probe: the skirmish AI team's EnterGarrisons (benches/ai/tactics/scenes.py#aigarrison_bench; docs/engine/aiteamstate.md; the
    simulator against these readings: benches/ai/tactics/readings.toml#engine_aigarrison).

      a  步兵在家 / 到远厂     Peacekeepers of s1 within 450 of the AI's base / 300 of the far power plant
         步兵数               Peacekeepers s1 owns (in the house too)
         楼归AI               the house is s1's (a garrisoned civilian building is its first occupant's: garrison.md 2)
         once a second, AFTER seconds after the wake

    Expectations are the model's (l4_micro_engage.md 1.7); a FAIL is a reading too:
      aigar1    the house turns the AI's (someone of the team went in)
      aigar0    the house never the AI's
      aigarfar  the house never the AI's

    Readings (11-09, all PASS; counters 步兵在家 到远厂 步兵数 楼归AI, 步兵数 counts the ones inside too):
      aigar1    s17 0 4 4 0 | s18-s75 0 3 3 1   -- one dead on the way in, the house the AI's at s18, the 3 alive to s75
                                                   (aigar0's die by s28): read as all three went in
      aigar0    s17 0 4 4 0 | s18 3 3 | s24 2 2 | s27 1 1 | s28-s75 0 0 0 0
      aigarfar  (house 450 south) s17 0 4 4 0 | s19 3 3 | s22 2 2 | s24 1 1 | s30-s75 0 0 0 0
                (first made 450 north, on the way in: s20 楼归AI 1, 到远厂 2 / 步兵数 3 -- ONE went in, the northernmost
                fighter within 150: the distance is each member's own)
    """
    from benches.ai.targets.checks import engine_aitarget
    at = engine_aitarget()["shared"]
    from parts import Script, Test, counted, square

    AFTER = 60.0


    def a(m, build):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[at.HOME] = square(*m.site('east base'), 450.0)
        o = m.find(m.role('far plant').name)
        t.areas[at.FAR] = square(o.x, o.y, 300.0)
        (inf,) = m.cnv_units
        counted('CNV_AG_Home', '步兵在家', t, template=inf, area=at.HOME, player=s1)
        counted('CNV_AG_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
        counted('CNV_AG_Count', '步兵数', t, template=inf, player=s1)
        house = m.role('house')
        counted('CNV_AG_House', '楼归AI', t, template=house.template, player=s1)
        wake = m.facts['wake at']
        end = wake + AFTER
        t.expect += [('步兵在家', wake + 5, 'ever==', 0, end)]              # it left
        if build in ('aigar1', 'aigar1t'):
            t.expect += [('楼归AI', 1, 'ever>=', 1, end)]
        else:
            t.expect += [('楼归AI', 1, '==', 0, end)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('aigar1', 'aigar0', 'aigarfar', 'aigar1t')}
    return dict(CHECKS=CHECKS)


def engine_aihome():
    """Engine probe: DefaultTacticHomeBaseCriteria -- which of two AI bases a RETURN_HOME_AND_DISBAND team walks home to
    (benches/ai/tactics/scenes.py#aihome_bench).

      a  家A / 家B / 敌存活 (aihomecl) or 到电厂 (aihmg*)   s1 units inside a square around base A (the first yard,
         half-width 450) / around base B (the second yard, 1350 north, half-width 750) / the player's Peacekeepers within
         2500 of the foe spot (aihomecl) or s1 units within 300 of the plant (aihmg*) -- once a second to wake + 70 s.
         aihmg*: the plant is killed by the check at the mission's 'kill plant at' (35 s).

    Model prediction (defense.home_for: pick_base with the personality's criteria, the team centre as PREFER_CLOSEST's
    point): first guess aihmgcl -> back to A (wrong, see below); aihmgnw, aihmgno -> to B (家B 4).

    读数
    Bench 2026-11-14 aihomecl a (run_queue, PASS on the weak expectation): 家A 4 to s7 (s8 3, s9 2, s10 1, s11 0), 家B 1
      @ s11, 2 @ s12, 3 @ s13, 4 from s14 to the end (s95); 敌存活 1 throughout. With two bases and no TargetBaseCriteria
      the ReactiveDefense team walks to B (the newer base: the xsd default sort PREFER_NEWEST) and never chases the foe
      1000 south of A. The same runs with SortOrder PREFER_NEWEST or PreferredNotBaseTypes OLDEST_OF_TYPE in the
      personality's DefaultTacticHomeBaseCriteria (builds aihomenw / aihomeno, retired) read the same to the second:
      ReactiveDefense never ends (the model: no EndBehavior), so those criteria were never asked.
    Bench 2026-11-14 (run_queue; 家A 家B 到电厂; the tanks leave s5-s8, 到电厂 4 from s7-s10):
      aihmgnw  PREFER_NEWEST: the tanks kill the plant themselves (到电厂 2 @ s27, 0 @ s28), walk past A (家A 1-2
               s28-s32) to B: 家B 1 @ s34, 2 @ s35, 4 from s36 to the end (s93) -- PASS.
      aihmgno  PREFER_CLOSEST + PreferredNotBaseTypes OLDEST_OF_TYPE: the plant gone s23-s24, 家A 1-2 s24-s27, 家B 2 @ s29,
               4 from s30 to the end (s87) -- PASS: the preferred-not type outweighs the closer base.
      aihmgcl  PREFER_CLOSEST: 到电厂 4 from s7 to the end (s88), 家A 0, 家B 0 -- FAIL against the model's first guess (back
               to A). The closest base is A and the team (firing from range, ~700 from A's yard at the plant) is within
               600 of it: the engine's go-home check says home, disband where they stand, no move order (work/re l4_tactics.md 4). The model
               ordered the move first and disbanded at 600 with the order on; fixed (B round 201), now the same.
    """
    from parts import Script, Test, counted, square

    LAG = 4.0
    AFTER = 70.0
    NEAR_A = 450.0
    NEAR_B = 750.0
    NEAR_PLANT = 300.0
    BIG = 2500.0
    FOE_DIST = 1000.0   # benches/ai/tactics/scenes.py#aihome_bench
    HOME = {'aihomecl': 'B', 'aihmgnw': 'B', 'aihmgno': 'B'}      # aihmgcl: neither (bench), asserted on 到电厂


    def a(m):
        t = Test()
        s1, p1 = m.player('s1'), m.player('p1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        (unit,) = m.cnv_units
        x, y = m.site('east base')
        bx, by = m.site('east base', 0.0, m.facts['north'])
        t.areas['CNV HB A'] = square(x, y, NEAR_A)
        t.areas['CNV HB B'] = square(bx, by, NEAR_B)
        counted('CNV_HB_A', '家A', t, template=unit, area='CNV HB A', player=s1)
        counted('CNV_HB_B', '家B', t, template=unit, area='CNV HB B', player=s1)
        end = m.facts['wake at'] + AFTER
        if m.facts['probe'] == 'reactive':
            fx, fy = m.site('east base', 0.0, -FOE_DIST)
            t.areas['CNV HB FoeBig'] = square(fx, fy, BIG)
            counted('CNV_HB_ALIVE', '敌存活', t, template=unit, area='CNV HB FoeBig', player=p1)
        else:
            px, py = m.site('east gate')
            t.areas['CNV HB Plant'] = square(px, py, NEAR_PLANT)
            counted('CNV_HB_PLANT', '到电厂', t, template=unit, area='CNV HB Plant', player=s1)
            kill = m.facts['kill plant at']
            t.scripts += [Script('Test - kill set', [], [('SET_MILLISECOND_TIMER', 'Test Kill Plant', kill)]),
                          Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Plant')],
                                 [('NAMED_KILL', m.role('plant').name)])]
        home = HOME.get(_key(m))
        t.expect += [('家B' if home == 'B' else '到电厂', end, '==', 4, end + 1)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def _key(m):
        return next(k for k, n in NAMES.items() if n == m.name)


    NAMES = {'aihomecl': 'CampAIHomeCl', 'aihmgcl': 'CampAIHmGCl', 'aihmgnw': 'CampAIHmGNw', 'aihmgno': 'CampAIHmGNo'}
    CHECKS = {k: {'a': a} for k in NAMES}
    return dict(CHECKS=CHECKS)


@cache
def engine_aiignore():
    """Base-distance IgnoreTargets gate contrast with unarmed, stationary engineers.

    INFERRED prediction from the field name and retail 700/0 values: radius 0
    ignores the engineers; radius 2000 allows attacks near the base. Both cases
    have identical geometry, Hunt recruitment and disabled powers/pullback/dodge.
    Engineers appear only after 26 s and two warriors are owned: the rejected
    initial probe let the first warrior attack before a two-member team existed.
    The hit latch uses game frames; capture seconds are only an observation window.
    Damage alone cannot distinguish a micro pick from a Hunt/weapon target pick.
    An equal outcome leaves that dispatch boundary unresolved; never tune the model
    to this indirect measurement. See work/re/c_ignore_distance_report.md.

    MEASURED: delayed targets, radius 0 first hurt frame 397; radius 2000 frame
    396. Both own two warriors and pass the pre-target no-damage check. Radius 0
    keeps its original diagnostic FAIL; radius 2000 PASS. Named replay asserts
    the observed damage in both, not the rejected filtering prediction. The model
    candidate eligibility, general base selection and exact distance boundary
    remain gaps.

    E120 repeats the observed pair with base-selection telemetry: both choose
    the sole base at (3850, 3400), equal to the model home. The selection reference
    is the team centre (3770, 2930); it is not the target position. The high pair's
    member aims locate the two targets at (3800, 2900) and (3900, 2900), each
    502.49 from the selected base. Named input replay covers this single-base
    geometry; candidate eligibility, multiple bases and exact boundaries remain
    gaps. See work/re/e120_ignore_base.md.

    B 11-24: the observer pair's team states are the readings in
    benches/ai/tactics/readings.toml#engine_aiignore (0 keeps the team at 8, 2000 gives state 0 with
    the engineer as target) -- the field's item hangs there.
    """
    from model import Script, Test, counted


    def probe(m):
        t = Test()
        t.scripts += [Script('Ignore - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                      Script('Ignore - frame', [], [('INCREMENT_COUNTER', 1, 'CNV_I_Frame')], once=False)]
        t.counters.append(('CNV_I_Frame', '帧数'))
        counted('CNV_I_Own', '造出', t, template=m.cnv_units[0], player=m.player('s1'))
        t.counters += [('CNV_I_Hit', '受伤'), ('CNV_I_First', '首伤')]
        for role, target in sorted(m.cnv_named.items()):
            t.scripts.append(Script('Ignore - hit ' + role,
                                    [('NAMED_NOT_DESTROYED', target), ('UNIT_HEALTH', target, 0, 100),
                                     ('COUNTER', 'CNV_I_Hit', 2, 0)],
                                    [('SET_COUNTER', 'CNV_I_Hit', 1),
                                     ('SET_COUNTER_TO_COUNTER', 'CNV_I_First', 'CNV_I_Frame')]))
        t.expect = [('造出', 20, 'ever>=', 2, 50), ('受伤', 1, '==', 0, 24),
                    ('受伤', 28, 'ever>=' if m.facts['ignore base distance'] else '==',
                     1 if m.facts['ignore base distance'] else 0, 50)]
        t.bench = [('bench_watch', dict(seconds=52, every=3, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'r': probe} for name in ('aiignzero', 'aiignnear')}


    def observe(m):
        """Separate CNVTeams diagnostics; coverage is checked on the game clock.

        The rejected damage prediction is kept; the team states these runs read
        are the coverage (benches/ai/tactics/readings.toml#engine_aiignore).
        Evidence: work/re/c_ignore_state_report.md.
        """
        t = probe(m)
        t.expect = [('帧数', 1, 'ever>=', 600, 240),
                    ('造出', 1, 'ever>=', 2, 240),
                    ('受伤', 1, '==', 0, 24),
                    ('受伤', 28, 'ever>=' if m.facts['ignore base distance'] else '==',
                     1 if m.facts['ignore base distance'] else 0, 240)]
        t.bench = [('bench_watch', dict(seconds=242, every=5, sheet=False, lines=4))]
        return t


    CHECKS.update({name: {'r': observe} for name in ('aiignzt', 'aiignnt')})
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(probe=probe))


def engine_aiignore_rule():
    """IgnoreTargets.Rule ANY/ALL with the retail EASY inclusion mask.

    Prediction: ANY permits the engineers, ALL filters their micro target slots.
    Damage is latched separately because ordinary attacks can bypass that slot.
    Read CNVTeams state/target/members on the same run's game clock; a damage PASS
    alone never establishes Rule coverage. See work/re/e118_ignore_rule.md.

    MEASURED: ANY first hurt f396 and state 0/nonempty target at f406/421;
    ALL first hurt f397 and state 8/empty target at those frames. Both have two
    members at f376/391 and prerequisite bad=0. ALL retains diagnostic FAIL:
    the wall-clock s22..24 owned count is still 1, although game-frame recruitment
    preconditions pass. Do not change that window to fit this run. Model ALL state
    replays; ANY candidate/Alpha eligibility remains a strict xfail, no promotion.
    aiignrinc (ANY Include ENGINEER) / aiignrexc (ALL Exclude ENGINEER), B 11-24:
    state 8 / 0 the same way (readings in benches/ai/tactics/readings.toml#engine_aiignore_rule).
    """
    from model import Script
    distance_probe = engine_aiignore()["shared"].probe


    def probe(m):
        t = distance_probe(m)
        frame, own, hit, first, bad = ('CNV_I_Frame', 'CNV_I_Own', 'CNV_I_Hit',
                                       'CNV_I_First', 'CNV_IR_Bad')
        # A target cannot contaminate the two-member recruitment window. Latch any
        # violated prerequisite rather than hiding it between HUD samples.
        for counter, op, value in ((own, 0, 2), (own, 4, 2), (hit, 4, 0)):
            t.scripts.append(Script(f'Rule - prerequisite {counter} {op}',
                [('COUNTER', frame, 3, 375), ('COUNTER', frame, 0, 390),
                 ('COUNTER', counter, op, value)], [('SET_COUNTER', bad, 1)]))
        t.counters = [(frame, '帧数'), (own, '造出'), (first, '首伤'), (bad, '失配')]
        t.expect = [('帧数', 1, 'ever>=', 600, 50), ('造出', 22, '==', 2, 50),
                    ('首伤', 1, 'ever>=', 390, 50), ('失配', 1, '==', 0, 50)]
        t.bench = [('bench_watch', dict(seconds=52, every=2, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'r': probe} for name in ('aiignrany', 'aiignrall', 'aiignrinc', 'aiignrexc')}
    return dict(CHECKS=CHECKS)


def engine_aikeep():
    """TimeToKeepTargetMin fixed-duration observation, E123; RandomTargetScoreModifier 0 / 1000 on the same carrier (B).

    Read target_orders/keep_passes from CNVTeams; counters only establish the
    existing carrier's live micro path. Clock acceptance is in test_ai_keep_target.
    See work/re/e123_keep_target.md for prediction and raw evidence.
    """
    probe_engage_clock = engine_aimicro()["shared"].probe_engage_clock

    CHECKS = {b: {'a': probe_engage_clock} for b in ('aikeeptwo', 'aikeeprng', 'airands0', 'airandsx')}
    return dict(CHECKS=CHECKS)


@cache
def engine_aimicro():
    """Engine probe: when the AI's micro manager fires the Imperial Warriors' Bonzai charge (benches/ai/tactics/scenes.py#aimicro_bench).

    s1's StaticDefense team is the two warriors; an unarmed player engineer stands D west of each (90 or 140), kept at
    full health every frame. The charge is read as the warrior's ObjectStatus WEAPON_UPGRADED_02 (10 s; reload 30 s).
    One check per build, r (aimicnear also c: the control, the script presses warrior 2's charge at frame PRESS_AT):
      aimicnear (D 90, HARD)   aimicmed (D 90, MEDIUM)   aimicfar (D 140, HARD)   aimichurt (D 140, HARD, health 70 %)
      aimicmade (D 90, HARD, the warriors created on s1's team by script 1 s after the wake)
    The verdicts after 帧数 are the model's answer (FIRES): 冲1 / 冲2 ever >= 1 where it charges, == 0 throughout where it
    does not -- a FAIL there is the bench reading otherwise, the charge count readable without the rows.
    Counters (four lines), from the wake on (run 60 s after it):
      帧数   frames since the wake (the wake frame is +-1)
      冲1    frames since warrior 1 was first seen charging  -> charged at frame = 帧数 - 冲1
      冲2    the same for warrior 2
      再冲1  frames since warrior 1 was seen charging again, once 冲1 >= 200 (the first charge ends at 150)
    Before the wake: a charge seen before the wake makes 冲k > 帧数.

    读数
    Bench 2026-11-06 (one run each; charged at = 帧数 - 冲k at the last row):
      aimicpre r (first design: the warriors s1's from the start, as aimicnear but no hand-over; run as CampAIMicNearR):
        冲1 冲2 再冲1 all 0 through 帧数 947 -- never charged, though the engineer stood 90 away in gun range. Read
        afterwards: a unit's AI powers are registered only when it is made / changes hands with the AI brain awake.
    Bench 2026-11-07 (Sonnet, one run each, no dropout):
      aimicnear c: 冲2 counting from about frame 300 (100 at s51, 404 at s71 of 帧数 704) -- the scripted press is seen,
        so the status reads a charge.
      aimicnear r / aimicmed r / aimicfar r / aimichurt r: 冲1 冲2 再冲1 all 0 through 帧数 949 / 940 / 948 / 933 --
        nobody charged, the hand-over 1 s after the wake did not help. The model fires in near / med / hurt (strict xfail
        in RA3-EngineModel tests/test_ai_bench.py); far agrees. Not known yet why: the hand-over not registering either,
        the StaticDefense team not taking handed-over units, or one of the 6 preconditions (l4_micro_powers.md 1).
      aimicmade r (Sonnet): 冲1 冲2 再冲1 all 0 through 帧数 939 -- warriors created on s1's team after the wake did not
        charge either: not the hand-over. Same in engine_aitoggle (no shield). INFERRED: StaticDefense runs no micro.
      aimichunt r (Sonnet, round 18): 冲1 冲2 再冲1 all 0 through 帧数 943 -- a Targetless Hunt team did not charge either:
        not the tactic. Left: the units never joined the team, or a gate of the power-use routine (work/re/l4_specials.md) / the power registration.
        (engine_aitoggle aitogglehunt: the Hunt team never took the script-made units -- they stood at their spots.)
      aimicxfer r / aimicnearx r (Sonnet, round 18): 冲1 冲2 再冲1 all 0 through 帧数 951 / 943 -- UNIT_AI_TRANSFER_ALL
        run again right after the make / hand-over did not help. Program (work/re l4_micro_gate.md): the recruiter
        refuses a unit whose team's recruitable flag is 0 (teamSoviet_1; only defaultSkirmishTeam is 1), the powers live in the
        unit's own team's library -- so (INFERRED) aimicpre (placed s1's, recruited at the wake, powers never registered: made
        with the AI asleep) and the made / handed-over builds (registered, never recruited) each miss one half.
        Next: the AI produces the warriors itself.
      aimicbuilt r (Sonnet, round 19; counters 帧数 造出 冲 曾冲): the opener built both warriors by s21 (造出 2), the
        conscripts walked in and both warriors were dead by s41 (造出 0) -- 曾冲 0 throughout, the AI's own warriors never
        charged though hurt and fighting infantry. The control (named warrior made on s1's team at wake + 45 s, button
        pressed 1 s later): 冲 1 at s61, 曾冲 100 -- the by-player status count reads a charge. So not the hand-over, the
        tactic, or the team the unit was made on: even units the AI builds do not charge (whether they were recruited at
        all: aimicbuilth).
      aimicbuilth r PASS (Sonnet, round 19, mod CampAIMicBltHR; counters 帧数 造出 在家 曾冲): 造出 2 from s21, 在家 2 -> 1
        @ s31 -> 0 @ s41 -- the Targetless Hunt team took the AI-built warriors and walked them off: AI-built units ARE
        recruited (unlike the script-made ones). So the aimicbuilt silence is past recruitment: the power entry check
        (the tactic's power-use routine / the heuristic's virtual method, work/re/l4_specials.md) or the power registration, not the team.
      aimicbuiltf r PASS (B, round 20, mod CampAIMicBltFR; counters 帧数 造出 冲 曾冲): 造出 2 from s21; 冲 2 @ s41,
        曾冲 145 @ 帧数 499 -> first charge at frame ~354 after the wake; the control read at s61. AI-built warriors that a
        Hunt team took, hurt by conscripts, DO charge. Read (work/re l4_micro_gate.md 7): a team change carries the
        unit's power entries along (the team-building routines, work/re/l4_specials.md), so the aimicbuilt silence is the StaticDefense team
        (not taking them, or not running the round there) -- not followed (the layer 4 closing line).
      aimicspon / aimicspoff r PASS both (B, round 113, 2026-11-10; mods CampAIMicSpOnR / CampAIMicSpOffR): aimicbuiltf
        on this probe's own micro manager (StandardMicroManager flattened, benches/ai/tactics/scenes.py#aimicro_bench _spow_xml), only
        UseSpecialPowers differing. On: 造出 2 from s21, 冲 2 @ s41, 曾冲 127 @ 帧数 489 (first charge ~362 frames after
        the wake), the warriors alive to the end (造出 3 from s61). Off: 造出 2 s21-s41 -> 0 @ s51 (both died fighting),
        曾冲 0 until the control (冲 1 @ s61, 曾冲 108) -- a scripted press still fires. UseSpecialPowers false = the micro
        manager never uses a unit power (the model: no round, work/re/l4_specials.md). The simulator (simai) fires in neither: its Hunt
        team walks the two warriors west from s21, before the conscripts set out, so they never fight (work/logs
        b113_sim3.log) -- and its micro block reads only the retail micro library (a probe's own AIMicroManagerData
        reaches only 'tactics micro', simai.own_personalities).
        Simulator since B round 114 (tests/test_simai.py): the probe's micro data reaches the micro block, and state 2's
        per-member pick (EngageHostileTargets; tactics._assign) turns the Hunt team on the conscripts from ~s28 -- on:
        the micro wants the charge from 275 frames after the wake (bench ~362), off: never. The charge itself is not
        applied in the simulator (recorded only), so its warriors still lose the fight.
      aimicengoff r FAIL against the prediction (B, round 115, 2026-11-10; mod CampAIMicEgOffR): aimicspon with only
        EngageHostileTargets="false". Predicted: the Hunt team walks on, never fights, no charge. Bench: 造出 2 from
        s21, 曾冲 75 @ 帧数 333 -> first charge ~258 frames after the wake (on: ~362), the warriors alive to the end (造出 3
        from s61). w (where; 在家 in place of 冲): aimicengoff 在家 2 at s21-s41, 0 @ s51, 曾冲 81 @ 帧数 339; aimicspon w
        PASS the same way (在家 2 s21-s41, 0 @ s51, 曾冲 130 @ 帧数 492). So on the bench the Hunt team does not walk
        its warriors off before the conscripts arrive (they fight at home, on or off) and EngageHostileTargets off does
        not keep them out of the fight or the charge -- the fight is not the micro manager's engage pick.
    """
    from parts import Script, Test, counted, square, status

    LAG = 4.0
    RUN = 60.0
    CHARGE = 'WEAPON_UPGRADED_02'


    COMMAND = 'Command_JapanAntiInfantryInfantryBonzai'
    PRESS_AT = 300     # control c: frames after the wake at which the script presses warrior 2's charge


    def names(m, group):
        """A group's unit names in order: the cast's roles, or (units the mission's scripts create) m.cnv_named."""
        made = getattr(m, 'cnv_named', {})
        return [r.name for r in m.roles(group)] or [made[k] for k in sorted(made) if k.startswith(group + ' ')]


    # what the model (RA3-EngineModel ra3model/ai/micro.py) expects of each build: does each warrior charge within the run
    FIRES = {'aimicpre': False, 'aimicnear': True, 'aimicmed': True, 'aimicfar': False, 'aimichurt': True,
             'aimicmade': True, 'aimichunt': True, 'aimicxfer': True, 'aimicnearx': True, 'aimicbuilt': True,
             'aimicbuilth': False, 'aimicbuiltf': True,
             'aimicspon': True, 'aimicspoff': False,
             'aimicengoff': True}   # round 115: aimicspon, EngageHostileTargets off -- predicted False, the bench charges
             # round 113 (aimicspon / aimicspoff): aimicbuiltf on this probe's micro manager, UseSpecialPowers on / off; builth: the Hunt walks them off to no infantry -- nothing to charge at
    HOME, HOME_R = 'CNV AM Home Area', 400.0   # aimicbuilth: round the barracks (the units come out within it)


    def probe(m, press=False, build=''):
        t = Test()
        p1 = m.player('p1')
        wake = m.facts['wake at']
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        t.scripts.append(Script('Test - keep the engineers up', [],
                                [('UNIT_SET_HEALTH', r.name, 100.0) for r in m.roles('engineer')], once=False))
        t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AM_Tick')], once=False),
                      Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AM_Tick', 3, 30)],
                             [('SET_FLAG', 'Test Woke', 1)])]
        t.counters += [('CNV_AM_Frames', '帧数'), ('CNV_AM_Rush1', '冲1'), ('CNV_AM_Rush2', '冲2'),
                       ('CNV_AM_Again1', '再冲1')]
        t.scripts.append(Script('Test - frames', [('FLAG', 'Test Woke', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Frames')],
                                once=False))
        warriors = names(m, 'warrior')
        for k, w in enumerate(warriors, 1):
            on = ('UNIT_HAS_OBJECT_STATUS', w, status(CHARGE))
            t.scripts += [
                Script(f'Test - rush seen {k}', [on], [('SET_FLAG', f'Test Rush {k}', 1)]),
                Script(f'Test - rush count {k}', [('FLAG', f'Test Rush {k}', 1)],
                       [('INCREMENT_COUNTER', 1, f'CNV_AM_Rush{k}')], once=False)]
        if press:
            t.scripts.append(Script('Test - press 2', [('FLAG', 'Test Woke', 1), ('COUNTER', 'CNV_AM_Frames', 2, PRESS_AT)],
                                    [('NAMED_USE_COMMANDBUTTON_ABILITY', warriors[1], COMMAND)]))
        w1 = warriors[0]
        t.scripts += [
            Script('Test - again seen 1', [('UNIT_HAS_OBJECT_STATUS', w1, status(CHARGE)),
                                           ('COUNTER', 'CNV_AM_Rush1', 3, 200)], [('SET_FLAG', 'Test Again 1', 1)]),
            Script('Test - again count 1', [('FLAG', 'Test Again 1', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Again1')],
                   once=False)]
        t.expect += [('帧数', wake + LAG, 'ever>=', 1, wake + RUN)]
        # did they charge (the model's answer; FAIL = the bench reads otherwise): 冲k > 0 once warrior k was seen charging
        if press:
            t.expect += [('冲2', wake + LAG, 'ever>=', 1)]
        elif build in FIRES:
            t.expect += [(f'冲{k}', wake + LAG, 'ever>=' if FIRES[build] else '==', 1 if FIRES[build] else 0)
                         for k in (1, 2)]
        t.bench = [('bench_watch', dict(seconds=wake + RUN + LAG, every=10, sheet=False, lines=len(t.counters)))]
        return t


    CTRL_S = 45.0      # built: seconds after the wake at which the check makes a named warrior on s1's team (the control)
    CONTROL = 'UNIT - CNV AM Control'


    def probe_built(m, build='aimicbuilt', where=False):
        """aimicbuilt (round 19): the AI's own warriors are unnamed, so count by player. Counters from the wake:
          帧数  frames since the wake
          造出  warriors s1 owns (the opener built them: >= 2)
          冲    s1's objects charging now (WEAPON_UPGRADED_02)
          曾冲  frames since s1 first had one charging -> first charge at frame 帧数 - 曾冲
        Control: CTRL_S after the wake the check makes a named warrior on s1's team at the control spot and presses its
        charge one second later -- 冲 must read it (the by-player count sees the status), and 曾冲 starting only then
        means the AI's own never charged. where (check w, round 115): 冲 gives way to 在家 (as aimicbuilth) and only
        曾冲 is judged -- did the Hunt team walk its warriors off before the fight."""
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        wake = m.facts['wake at']
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        t.scripts.append(Script('Test - keep the conscripts up', [],
                                [('UNIT_SET_HEALTH', r.name, 100.0) for r in m.roles('conscript')], once=False))
        t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AM_Tick')], once=False),
                      Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AM_Tick', 3, 30)],
                             [('SET_FLAG', 'Test Woke', 1)])]
        t.counters.append(('CNV_AM_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [('FLAG', 'Test Woke', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Frames')],
                                once=False))
        counted('CNV_AM_Owned', '造出', t, template=m.cnv_units[0], player=s1)
        hunt = bool(m.facts.get('hunt')) and not m.facts.get('foes')
        if hunt or where:   # aimicbuilth: 冲 gives way to 在家 -- s1's warriors within HOME_R of the barracks (left = recruited)
            x, y = m.point('factory spot')
            t.areas[HOME] = square(x, y, HOME_R)
            counted('CNV_AM_Home', '在家', t, template=m.cnv_units[0], area=HOME, player=s1)
        else:
            counted('CNV_AM_Rush', '冲', t, status=status(CHARGE), player=s1)
        t.counters.append(('CNV_AM_Ever', '曾冲'))
        t.scripts += [
            Script('Test - rush seen any', [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', s1, 3, 1, status(CHARGE))],
                   [('SET_FLAG', 'Test Rush Any', 1)]),
            Script('Test - rush count any', [('FLAG', 'Test Rush Any', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Ever')],
                   once=False)]
        ctrl = int(CTRL_S * 15)
        t.scripts += [
            Script('Test - control make', [('FLAG', 'Test Woke', 1), ('COUNTER', 'CNV_AM_Frames', 2, ctrl)],
                   [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', CONTROL, m.cnv_units[0], m.team('s1'), m.mark('control spot'))]),
            Script('Test - control press', [('FLAG', 'Test Woke', 1), ('COUNTER', 'CNV_AM_Frames', 2, ctrl + 15)],
                   [('NAMED_USE_COMMANDBUTTON_ABILITY', CONTROL, COMMAND)])]
        fires = FIRES[build]
        t.expect += [('帧数', wake + LAG, 'ever>=', 1, wake + RUN), ('造出', wake + LAG, 'ever>=', 2, wake + CTRL_S),
                     ('曾冲', wake + LAG, 'ever>=' if fires else '==', 1 if fires else 0, wake + CTRL_S)]
        # hunt: the model recruits the built warriors -- they leave (在家 0 while 造出 is 2); else the control's charge
        t.expect += ([] if where else [('在家', wake + LAG, 'ever==', 0, wake + CTRL_S)] if hunt
                     else [('冲', wake + CTRL_S + 2, 'ever>=', 1)])
        t.bench = [('bench_watch', dict(seconds=wake + RUN + LAG, every=10, sheet=False, lines=len(t.counters)))]
        return t


    def probe_update_time(m):
        """Latch the first AI charge on the script clock, with live-unit controls.

        There is no scripted power press in this check. A positive first charge
        proves the AI-built units entered a functioning micro/power path. This does
        not expose team identity or the internal dispatch frame. Only the micro
        UpdateTime differs between builds; no Tactic.UpdateTime is changed.

        MEASURED aimicupfast:a / aimicupslow:a: first latch 363 / 317, alive 2
        in both (three checks PASS each). Model latch 271 / 309: precise replay
        remains strict xfail. Eligibility/update phase unresolved; see
        work/re/c_update_time_report.md. Longer period is not a fixed delay.
        """
        t = probe_built(m, 'aimicspon')
        t.scripts = [s for s in t.scripts if not s.name.startswith('Test - control')]
        t.counters = [('CNV_AM_Frames', '帧数'), ('CNV_AM_Owned', '造出'),
                      ('CNV_UP_First', '首冲帧'), ('CNV_UP_Alive', '首活')]
        t.scripts.append(Script('Test - latch first charge',
                                [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', m.player('s1'), 3, 1, status(CHARGE))],
                                [('SET_COUNTER_TO_COUNTER', 'CNV_UP_First', 'CNV_AM_Frames'),
                                 ('SET_COUNTER_TO_COUNTER', 'CNV_UP_Alive', 'CNV_AM_Owned')]))
        t.expect = [('造出', 14, 'ever>=', 2, 45), ('首冲帧', 14, 'ever>=', 1, 55),
                    ('首活', 14, 'ever>=', 2, 55)]
        t.bench = [('bench_watch', dict(seconds=56, every=5, sheet=False, lines=4))]
        return t


    CHECKS = {b: {'r': lambda m, b=b: probe(m, build=b)} for b in FIRES if not b.startswith(('aimicbuilt', 'aimicsp'))}
    CHECKS['aimicupfast'] = {'a': probe_update_time}
    CHECKS['aimicupslow'] = {'a': probe_update_time}
    CHECKS['aimicupft'] = {'a': probe_update_time}
    CHECKS['aimicupst'] = {'a': probe_update_time}
    CHECKS['aigathb1'] = {'a': probe_update_time}
    CHECKS['aigathb3'] = {'a': probe_update_time}
    CHECKS['aigathk1'] = {'a': probe_update_time}
    CHECKS['aimicbuilt'] = {'r': probe_built}
    CHECKS['aimicbuilth'] = {'r': lambda m: probe_built(m, 'aimicbuilth')}
    CHECKS['aimicbuiltf'] = {'r': lambda m: probe_built(m, 'aimicbuiltf')}
    CHECKS['aimicspon'] = {'r': lambda m: probe_built(m, 'aimicspon')}
    CHECKS['aimicspoff'] = {'r': lambda m: probe_built(m, 'aimicspoff')}
    CHECKS['aimicengoff'] = {'r': lambda m: probe_built(m, 'aimicengoff'),
                             'w': lambda m: probe_built(m, 'aimicengoff', where=True)}
    CHECKS['aimicspon']['w'] = lambda m: probe_built(m, 'aimicspon', where=True)
    CHECKS['aimicnear']['c'] = lambda m: probe(m, press=True)
    AGAIN = (225, 465)      # d: frames after the first press the script presses warrior 2's charge again (reload 30 s)


    def probe_presses(m):
        """d (A304, retail y01 / y03's scripted Bonzai): c's press, and again AGAIN later (inside / past the reload);
        开2 counts the frames warrior 2 has the charge on (one charge 150): 300 if a script's press heeds the reload,
        450 if not."""
        t = probe(m, press=True)
        w2 = names(m, 'warrior')[1]
        t.counters[-1] = ('CNV_AM_On2', '开2')          # in place of 再冲1 (four lines)
        t.scripts = [s for s in t.scripts if not s.name.startswith('Test - again')]
        t.scripts.append(Script('Test - on count 2', [('UNIT_HAS_OBJECT_STATUS', w2, status(CHARGE))],
                                [('INCREMENT_COUNTER', 1, 'CNV_AM_On2')], once=False))
        t.scripts += [Script(f'Test - press 2 again {k}', [('FLAG', 'Test Woke', 1),
                                                             ('COUNTER', 'CNV_AM_Frames', 2, PRESS_AT + d)],
                             [('NAMED_USE_COMMANDBUTTON_ABILITY', w2, COMMAND)]) for k, d in enumerate(AGAIN)]
        t.bench = [('bench_watch', dict(seconds=m.facts['wake at'] + 75, every=5, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS['aimicnear']['d'] = probe_presses


    def probe_engage_clock(m):
        """No scripted charge: latch first AI power and the live warrior count.

        First charge is a measurement, not an invented prediction threshold. Both
        sides must produce two warriors and charge before the 55-second deadline.
        Initial movement replay is tested separately; work/re/e107_engage_clock.md.
        """
        return probe_update_time(m)


    CHECKS['aiegon'] = {'a': probe_engage_clock}
    CHECKS['aiegoff'] = {'a': probe_engage_clock}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(probe_built=probe_built, probe_engage_clock=probe_engage_clock))


def engine_aineutralgarr():
    """NeutralGarrison/native named-slot selection; evidence work/re/c_garrison_report.md.

    Counter verifies the placed control survives through the selection window.
    Only target_picks establishes the native heuristic's selection verdict.
    """
    from parts import Test, Script


    def a(m):
        t = Test()
        names = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
        names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
        t.scripts.append(Script('Garr keep', [],
            [('UNIT_SET_HEALTH', n, 100.0) for n in names], once=False))
        t.scripts.append(Script('Garr reveal', [],
            [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.counters.append(('GarrControl', 'control alive'))
        control = m.role('garr control').name
        t.scripts.append(Script('Garr alive reset', [], [('SET_COUNTER', 'GarrControl', 0)], once=False))
        t.scripts.append(Script('Garr alive', [('NAMED_NOT_DESTROYED', control)],
            [('SET_COUNTER', 'GarrControl', 1)], once=False))
        # Original off capture missed every sample in s2-s3; keep that FAIL in
        # private evidence. Check the whole selection window, with the same value.
        t.expect = [('control alive', 1, '==', 1, 15)]
        t.bench = [('bench_watch', dict(seconds=15, every=1, sheet=False, lines=1))]
        return t


    def b(m, health=False):
        """aigarrbld: the Garrison state's team -- Peacekeepers at home / in all, the player's plant standing, the shop the
        AI's; c (health): the plant's health % in place of the Peacekeepers' count (how fast they take it down)."""
        from benches.ai.targets.checks import engine_aitarget
        at = engine_aitarget()["shared"]
        from parts import counted, square
        INF = m.role('ai inf 1').template
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Garr reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[at.HOME] = square(*m.site('east base'), 450.0)
        counted('CNV_GB_Home', '步兵在家', t, template=INF, area=at.HOME, player=s1)
        if health:
            counted('CNV_GB_Count', '电厂血', t, health=m.role('plant').name)
        else:
            counted('CNV_GB_Count', '步兵数', t, template=INF, player=s1)
        counted('CNV_GB_Plant', '电厂在', t, template='AlliedPowerPlant', player=m.player('p1'))  # the team state's fight
        counted('CNV_GB_Shop', '商店归AI', t, template='HV_Shop01', player=s1)
        t.scripts.append(Script('Test - count CNV_GB_Row', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', 'AM_RowHouse01', s1,
                                                                'CNV_GB_Row')], once=False))   # off screen (OCR reads 4)
        t.scripts += [Script('Test - CNV_GB_Row ever 0', [], [('SET_COUNTER', 'CNV_GB_RowEver', 0)]),
                      Script('Test - CNV_GB_Row ever', [('COUNTER', 'CNV_GB_Row', 3, 1)],     # latched: the row house
                             [('SET_COUNTER', 'CNV_GB_RowEver', 1)])]                         # the AI's at any time
        end = m.facts['wake at'] + 60.0
        t.expect = [('步兵在家', m.facts['wake at'] + 5, 'ever==', 0, end)]      # the model: the team leaves for a house
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {build: {'a': a} for build in ('aigarron', 'aigarroff')}
    CHECKS['aigarrbld'] = {'b': b, 'c': lambda m: b(m, health=True)}
    return dict(CHECKS=CHECKS)


def engine_aiorders():
    """Engine line D round 77: aiskcap's check y (new Peacekeepers past their SpecificUnitCap 2 at ~s150) on aiskcapo =
    aiskcap with the AI yard carrying ra3ext's CNVOrders (benches/ai/tactics/scenes.py#aiorders_bench). The bench asserts y's counters; the
    orders (which path placed the overrun Peacekeeper) are read off the run folder's ra3ext.log after the run.

    Round 79 (H4): yl = y watched to 300 s after the wake (the AI's building orders, AlliedBaseDefense among them, are in
    the CNVOrders log), on aiskcapo / aiskcapp / aiskcapd. aiskcapo makes its infantry in two waves (s28-s42, then from s135; the overrun is in
    the second); with owned plants (aiskcapp / aiskcapd) the first wave starts ~30 s later and y's window ends before the
    second.
    """
    from benches.ai.production.checks import engine_aiskirm
    y = engine_aiskirm()["shared"].y


    def yl(m):
        t = y(m)
        t.bench = [('bench_watch', dict(seconds=m.facts['wake at'] + 300.0, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'aiskcapo': {'y': y, 'yl': yl}, 'aiskcapd': {'y': y, 'yl': yl}, 'aiskcapp': {'y': y, 'yl': yl},
              'aiskcapy': {'y': y}, 'aiskcapt': {'yl': yl}}
    return dict(CHECKS=CHECKS)


def engine_aipassive_distance():
    """PassiveTargetSearchDistance diagnostic, not coverage from damage alone.

    Read team state/target/member positions from the same run's CNVTeams log.
    The script frame counter and index anchors prevent wall-clock substitution.
    INFERRED prediction: radius 600 hurts the side plant, 0/200 leave it intact
    before logic frame 525. Preserve rejected predictions; never fit thresholds.
    Evidence and open distance-origin hypotheses: work/re/e104_passive_distance.md.

    MEASURED: aipsdz/aipsdt/aipsds/aipsdl all select the side plant at frame 140
    (state 6, four members, tactical target differs), state 0 at 320. The target
    command supplies the side plant's coordinates. At selection the team centre
    is 350.3 away; every member is 324.3 or farther away, including radius 1/200.
    All four diagnostics retain the rejected survival prediction (FAIL): later
    defences kill the team; by frame 605 its membership is empty. The >=600-frame
    gate passes. Preserve these readings, not wall-clock HP comparisons.
    """
    from model import Script, Test, counted, square


    def probe(m):
        t = Test()
        t.scripts = [Script('Passive - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                     Script('Passive - clock', [], [('INCREMENT_COUNTER', 1, 'CNV_PD_Frame')], once=False)]
        t.counters.append(('CNV_PD_Frame', '帧数'))
        counted('CNV_PD_Own', '存活', t, template=m.cnv_units[0], player=m.player('s1'))
        counted('CNV_PD_HP', '旁厂血量', t, health=m.facts['side plant'])
        far = m.find(m.role('far plant').name)
        t.areas['CNV_PD_Far'] = square(far.x, far.y, 300)
        counted('CNV_PD_Far', '到远厂', t, template=m.cnv_units[0],
                player=m.player('s1'), area='CNV_PD_Far')
        t.expect = [('帧数', 1, 'ever>=', 600, 55), ('存活', 1, '==', 4, 55)]
        t.bench = [('bench_watch', dict(seconds=57, every=2, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'r': probe} for name in ('aipsdz', 'aipsdt', 'aipsds', 'aipsdl')}
    return dict(CHECKS=CHECKS)


def engine_aipathcheck():
    """Engine line D round 152: PathfindingCheckType (benches/ai/tactics/scenes.py#aipathcheck_bench). Three counters, once a second, to
    90 s after the wake; the team's members are in the CNVTeams log (the kick = members leaving with no death).

      步兵总数 / 步兵在家 / 到对岸   s1's Peacekeepers alive; within 450 of the AI base; within 600 of the player's yard
      expected (no land way across): 到对岸 0 all along, 步兵总数 never below 2 (nothing reaches them across the river)
    """
    from benches.ai.targets.checks import engine_aitarget
    at = engine_aitarget()["shared"]
    from parts import Script, Test, counted, square

    HOME = 'CNV AI Base Area'
    ACROSS = 'CNV AI Across Area'
    SPAN = 90.0


    def check(m):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[HOME] = square(*m.site('east base'), 450.0)
        o = m.find(m.role('player yard').name)
        t.areas[ACROSS] = square(o.x, o.y, 600.0)
        s1, (inf,) = m.player('s1'), m.cnv_units
        counted('CNV_PF_Live', '步兵总数', t, template=inf, player=s1)
        counted('CNV_PF_Home', '步兵在家', t, template=inf, area=HOME, player=s1)
        counted('CNV_PF_Across', '到对岸', t, template=inf, area=ACROSS, player=s1)
        end = m.facts['wake at'] + SPAN
        t.expect += [('到对岸', 1, '==', 0, end), ('步兵总数', 1, '>=', 2, end)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': check} for k in ('aipfdef', 'aipfatk', 'aipfpath', 'aipfnone')}
    return dict(CHECKS=CHECKS)


@cache
def engine_aipullback():
    """Engine probe: the skirmish AI team's PullbackInjured / ReverseMove (benches/ai/tactics/scenes.py#aipullback_bench; docs/engine/aiteamstate.md).

      aipull1 / aipull0   a  守军数 (the player's Peacekeepers), 坦克数 (s1 Hammers), 到远厂 (Hammers within 300 of the far
                             plant), 回家 (Hammers within 300 of the AI's war factory)
      airev1 / airev0     a  守军数, 坦克数, 近厂 (Hammers within 150 of the far plant), 到远厂 (within 300)
         once a second, AFTER seconds after the wake

    Expectations are the model's; a FAIL is a reading too.
      aipull1   回家 is 1 or more at some time after the wake
      aipull0   回家 stays 0 from the wake + 25 s on (the tanks are at the far plant by then)
      airev*    only that the counters exist (守军数 12 at the wake) -- the per-second readings are the result

    Readings (11-09; 4 Hammers vs 12 Peacekeepers, Crush false; tanks reach the plant s15):
      aipull1  FAIL (no retreat): 回家 1 at s1-2 (a tank near the factory at the start), 0 from s3 to the end; 4 tanks s3-24
               (到远厂 1..3 at s12-14, 4 from s15) | 3 @ s25-26 | 2 @ s27-35 | 1 @ s36-37 | 0 @ s38-85; guards 12 all along
      aipull0  PASS, second for second the same as aipull1 (no tank ever goes home)
      airev1   守军 12 -> 11 at s31; 4 tanks s1-22 (近厂 2 @ s19-22) | 3 @ s23-30 (近厂 1 @ s25-29, 0 @ s30) | 2 @ s31-37
               (近厂 1 @ s34-37) | 0 @ s38-85
      airev0   守军 12 all along; 4 tanks to s22 (近厂 1 @ s18, 2 @ s19-22) | 3 @ s23-30 | 2 @ s31-33 (近厂 1) | 1 @ s34-36 |
               0 @ s37-85
      (the first airev1 run's expectation was written as '>=' and so failed at 11 guards; changed to ever>=, same readings)
      aipullh1 FAIL: the 4 tanks set to 30 % at s12 on the road -- they drive on, 到远厂 4 by s15-16, 3 @ s17-20, 2 @ s21,
               1 @ s22-24, 0 from s25; 回家 0 from s4 to the end. Not the shot-down-too-fast window.
      aipullga FAIL: the same with Allied Guardian tanks (the AI's own faction): 4 at the plant s12, 0 by s20, 回家 0. Not the
               faction either. Not settled: the member KindOf filter (masks 0xc000 / 0x1000, not read), the
               template flag bit 13 test, the path test, or the garrison routine never reached in these states.
      aipullh0 not run (aipull0 already shows no-one goes home).
      (11-09, round 69; 血量 = tank 1's health %, read 30 from the set on: UNIT_SET_HEALTH does take)
      aipulli1 FAIL: hurt 0.5 s after the wake, ~1000 from any enemy (no AlphaStrike) -- 血量 30 s9-12, the 4 drive on,
               到远厂 1 @ s13 .. 3 @ s15-16, all dead by s23; 回家 0 from s3
      aipullr1 FAIL, second for second as aipulli1, with SKIRMISH_AI_USE_REPAIRS s1 1 at the hurt: not the repair switch
      aipullp1 FAIL: hurt before the wake (idle, ~400 from the factory): they join the team at 30 % and leave steadily,
               近家 (600) 4 @ s1-5, 3 @ s6-7, 2 @ s8, 1 @ s9-10, 0 from s11 -- no lingering (not sent home and re-recruited)
      aipullbig FAIL, the same as aipullp1 with PullbackInjuredHealthPct 100000: not the health ratio's scale
      So the garrison routine is reached (EnterGarrisons, in the same state functions, worked) and the member gates pass; left: the
      facility search -- the ArmyDef map lookup (key stored on the team / brain), the template's field against the ArmyDef's field, or the
      path test (work/re/l4_micro_engage.md 1.4).
      (11-09, round 70) The ArmyDefinition is found by the player's faction (its Side), so s1 Allied -> AlliedWarFactory
      as the probe has it. aipulli1 with the faction changed:
      aipullsov PASS (Soviet AI, a SovietCrane): 血量 30 from s9, 回家 1 @ s19 .. 4 @ s23, then 坦克数 4 -> 0 by s29 with
               血量 frozen at 39 -- the 4 hurt tanks drive home and into the Crane (SlaughterHordeContain: ground up for
               75 % cash back). Before this run's window moved to wake + 5 s it read FAIL (the window began at s35).
      aipulljp  FAIL (Japan AI, a JapanWarFactory): as aipulli1 -- they drive on, all dead by s25, 回家 0.
      So the pull-back works, but only to a repair place the vehicle can enter: retail's Allied / Japan war factories
      (no vehicle Contain) are never found (the facility search's reach test, or the template match -- not told apart);
      the Soviet AI recycles its hurt vehicles in the Crane.
      ReverseMove: airev1 / airev0 differ too little to read a back-up (近厂 2 in both at s19-22).
      (11-09, round 71; the target beside the tanks, 80-135 off, healed to 100 every frame)
      airevp1 / airevp0 (the far plant): first runs, unhealed, the tanks shot it to 2 % by s8 and both left s19-24 alike
               (target gone). Healed: airevp0 PASS 近厂 4 all 85 s; airevp1 FAIL, the same -- 近厂 4 all along. A plant is a
               tactical target (state 6), and the reverse-move routine runs in states 2 and 4 only.
      airevt1  FAIL (a player's AlliedBaseDefense instead, CleanupPowerAdvantage 1000, UseGatherState off -> state 2):
               no tank moves, 近塔 = 坦克数 = 中圈 all along; the turret kills them one by one 4 @ s1-10, 3 @ s11-22,
               2 @ s23-34, 1 @ s35-46, 0 from s47. airevt0 not run (airevt1 already shows no back-up).
      Left (work/re handoff-b 72): the reverse-move routine's first gate -- a byte flag reached through the member's locomotor data
      (read as a locomotor template flag, not named); the weapon flag check skips too.

      (11-14, B round 196) airevidx: airev1t plus a second AI side s6 (index 11; s1 is index 4), laid out the same, its
               units handed to the AI at the start (run 1 without that: they sat in the map's teamSoviet_6 and the team
               filled only at the wake's transfer, f151 -> f152). Run 2, the slot team made / full: s1 f17 / f21, s6 f18 /
               f20. Neither follows the index (+7 would put s6 at f24): the first slot draw is ~start + 15 for both, the
               fill +4 / +2 is not an index stagger (left INFERRED). PASS (guards only).
      (11-14, A round 227) the turn in place (tests/test_turn_rate.py, fixtures a_turn/): airevgt (Guardians facing
               north-west) PASS -- 24 deg a frame (360 / TurnTimeSeconds 1.0), the 51 deg form-up turn in place f26-27,
               driving from f28 (start 3 off), arrived f44-48, turned to the facing, go order f56 (96 deg: f56-59, drive
               f60). airevat (Apocalypses) PASS -- 8 a frame (3 s): 96 deg f26-37, drive f38; the facing turns f67-97, go
               order f98. With airev1t's Hammers (19 a frame): a unit drives on a frame that starts within ~9 deg of its
               way (8 drove; 10 and 15 did not), the rest of the turn made driving; under TurnThresholdHS 90 alike.
               A turn ordered while driving (airevgt f170, attack) is made driving (24 deg on a moving frame).
      (11-14, A round 231) airevit (Conscripts, TestReactiveLocomotorHUMAN: no TurnThresholdHS) PASS (s15 到远厂 1 -> s17
               4): the form-up order f26 -- every member moves ~3.2 a frame from f26 on while its heading goes -180 -135
               -90 -72..-82: no turn in place (fixtures a_turn/airevit.txt); 45 a frame (not 720 / 15 = 48); standing,
               3170 turns to the facing in place (f45-47); the go order f74-76 alike.
      E115 observer pair airev1t/airev0t: both PASS the guard prerequisite only. Initial four join at host f21;
      all acquire the far plant at f230; f260/261 are state 2 with valid goals. Each side has 23 moving-member
      observations across consecutive frames in states 2/4 with the same valid goal, all positive hull-forward
      displacement dot products (no reverse candidate in those samples). This does not cover every frame or prove
      branch eligibility. Near-plant s19-s22 is zero on both observer builds, unlike the old uninstrumented record.
      The f263 far-plant aim holds on the simulator (readings: benches/ai/tactics/readings.toml#engine_aipullback); work/re/e115_reverse_aim.md.
      (11-13, D round 132; two of the player's Guardians ~54 off the column, host observed; 坦克数 近敌 敌坦)
      airevk1  PASS, airevk0 PASS -- the same second for second: s1-12 4 4 2 | s13 4 4 1 | s14-85 4 3 1, and the host's
               samples the same frame for frame: only 2 tanks join the team (f213), go state 2 at f242 with aim = the
               far foe (the near one died s13, before the team), centre distance 166 / 190-233 > R - 10 = 135 -- the
               reverse gate not reached, no back-up point in either (agrees with the model; not a test of the switch)
      airevkg1 FAIL (invalid): the attack team never takes a Guardian (n=0 all run); 4 4 2 all along
      (11-13, D round 133; at 16.7 s the two foes deleted, a player's Guardian spawned on each Hammer)
      airevk2  PASS: s1-12 4 4 2 | s13 4 4 1 | s14 4 3 1 | s15-30 4 3 4 | s31-48 4 4 4 | s49-85 4 3 4. Host: both members
               aim a spawned foe (f272); f302 member 3171 is stopped and sent to a point 135 (R - 10) from its target,
               along target -> member, and drives there hull-first at the target (reversing); 23 such orders in the run
      airevk2o PASS: s1-12 4 4 2 | s13 4 4 1 | s14-15 4 3 1 | s16-85 4 3 4; no back-up order (readings: benches/ai/tactics/readings.toml#engine_aipullback)
      (11-14, D round 135b, "注入摆" -- PREMISE: THE START IS PLACED (前提是摆出来的), not the mission's own: at f250 the
      plan moves foe 1 / 2 50 west of members 3170 / 3171; foe 1 already dead (poke not found), foe 2 placed)
      airevkp1 PASS: s1-12 4 4 2 | s13 4 4 1 | s14-17 4 3 1 | s18-85 4 2 1; f272 both members back up to 135 (R - 10)
               from foe 2 <- ReverseMove, 19 back-up orders in the run = d133's airevk2
      airevkp0 PASS: s1-12 4 4 2 | s13 4 4 1 | s14-85 4 3 1; the same poke, no back-up order (readings: benches/ai/tactics/readings.toml#engine_aipullback)
      (11-16, D round 182) airevkh PASS (airevk1, 坦克数 swapped for the foes' health % read BEFORE the frame's keep):
               血1 血2 近敌 敌坦  s2-54 100 100|92 4 2 | s56 4 1 | s60-142 3 1 -- the keep holds (a read before it is 100, or
               92 = one 35 shell); here the near foe lived to s56, yet members 3170 / 3171 joined the team f213 exactly as in
               airevk1. The host: f166 the AI casts a special power (cmd 1ff, its own power hash, at 3545:3340 = the near foe),
               f212 the strike (object 3228) hits the foe and the AI's own 3170 / 3171 (3170 to 316 / 550); f213 they join.
               So the s13 death in airevk1 is that strike outdoing the keep in one frame; the simulator's AI casts no power.
      (11-16, D round 183; 总控 k2 = A) the s1 AI's SpecialPowerPrecisionStrike held off (countdown 3600 s every frame,
      NO_POWER); the readings above for airevk1 / 0 / 2 / 2o are the powered runs. The bench's seconds ran ~2x slow:
      airevk1  CampAIRevK1A_mcp_1116_184800: 4 4 2 all run (s1-114); the attack team n=0 all run -- no strike, no join.
               The 'ever<4' expectation (the model's, a back-up) FAILed; now airevk0's '>= 3' (the reading is 4).
      airevk2  CampAIRevK2A_mcp_1116_184946: s1-31 4 4 2 | s32 4 4 4 | s34-42 4 3 4 | s43-64 4 0 4 | s66-116 4 1 ..;
               host: before the swap (f250) the members aim 0; f253 all four (3170-3173) join, f257 the form-up move,
               f312 on back-up orders (type 236 from the ReverseMove call site), 20 in the run. 敌坦's window FAILed on the
               slow clock (4 first at bench s32), not on the spawn.
      airevk2o CampAIRevK2OffA_mcp_1116_185214: s2-26 4 4 2 | s27 4 4 4 | s29-127 4 3 4; f253 the same four join, no
               back-up order in the run (敌坦's window FAILed on the slow clock alike).
      airevk0  CampAIRevK0A_*_1116: PASS, 4 4 2 all run (s1-129) = airevk1.
      So with the power off the join waits for the swap (f250 -> f253, the members aiming 0 then); the simulator's
      in_combat gate (a body that fired last tick) keeps all four out after the swap too: the spawned foe is in range
      the same tick. The 近敌 counter reading stays a mismatch on that (B's gate, not ReverseMove).
    """
    import inject
    from benches.ai.targets.checks import engine_aitarget
    at = engine_aitarget()["shared"]
    from parts import Script, Test, counted, square

    AFTER = 70.0
    LATE = 25.0
    HURT_AT = 12.0                           # aipullh*: the tanks are on the road (at the far plant s15)
    IDLE = ('aipulli1', 'aipullr1', 'aipullp1', 'aipullbig', 'aipullsov', 'aipullsvx', 'aipulljp', 'aipullsnx', 'aipullsny',
            'aipullav', 'aipullax', 'aipullavt', 'aipullavc', 'aipullavn', 'aipullavp', 'aipullaxp')   # hurt at the wake, ~1000 from any enemy (p1: before it)
    IDLE_HURT = {'aipulli1': 0.5, 'aipullr1': 0.5, 'aipullp1': -9.0, 'aipullbig': -9.0, 'aipullsov': 0.5, 'aipullsvx': 0.5, 'aipulljp': 0.5,
                 'aipullsnx': 0.5, 'aipullsny': 0.5, 'aipullav': 0.5, 'aipullax': 0.5, 'aipullavt': 0.5, 'aipullavc': 0.5, 'aipullavn': 0.5, 'aipullavp': -9.0, 'aipullaxp': -9.0}   # s after the wake
    HURT = 30.0                              # % -- under PullbackInjuredHealthPct 0.35
    LATE_AT = 16.7                           # airevk2*: s after the start (f250: the team formed f213, state 2 f242 in airevk1)
    LATE_NAME = 'UNIT - CNV AI Rev Late'     # + ' k': the Guardian spawned on Hammer k
    NEAR_FOE = 100.0                         # airevk*: half side of the square round the player's two Guardians
    POKE_AT = 250                            # airevkp*: logic frame of the plan (airevk1: team f213, state 2 f242)
    POKE_XY = ((3530.0, 3230.0), (3553.0, 3304.0))   # 50 west of members 3170 / 3171 as they stood f242-248 (airevk1
                                                     # run 11-13, ra3ext.log team lines); foe k beside member k
    AI_POWER = 'SpecialPowerPrecisionStrike'  # airevkh f166: the s1 AI's cast (cmd 1ff, hash -918055170 = this name)
    NO_POWER_S = 3600                         # s: its countdown held far past the run every frame (engine_acts4 s17: a
                                              # positive countdown makes a player power not ready)
    NO_POWER = ('airevk1', 'airevk0', 'airevk2', 'airevk2o')   # D round 183 (总控 k2 = A): the power off on these


    def a(m, build):
        t = Test()
        s1, p1 = m.player('s1'), m.player('p1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        o = m.find(m.role('far plant').name)
        t.areas[at.FAR] = square(o.x, o.y, 300.0)
        inf, tank = m.cnv_units
        wake = m.facts['wake at']
        end = wake + AFTER
        tanks = [o.name for o in m.objects if o.template == tank and o.side == 's1']
        if build in IDLE:                    # four counters at most: 血量 (tank 1's health %) for 守军数
            t.counters.append(('CNV_PB_Health', '血量'))
            t.scripts.append(Script('Test - health', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', tanks[0],
                                                           'CNV_PB_Health')], once=False))
        elif not build.startswith(('airevp', 'airevt', 'airevk', 'airevb', 'airevs')):  # no guards
            counted('CNV_PB_Guards', '守军数', t, template=inf, player=p1, most=13)
        if build != 'airevkh':               # airevkh: the foes' two health % instead (four counters at most)
            counted('CNV_PB_Tanks', '坦克数', t, template=tank, player=s1)
        if build.startswith('aipull'):
            f = m.find(m.role('ai factory').name)
            t.areas[at.HOME] = square(f.x, f.y, 300.0)
            if build in ('aipullp1', 'aipullbig'):
                t.areas['CNV_PB_NearHome'] = square(f.x, f.y, 600.0)
                counted('CNV_PB_NearH', '近家', t, template=tank, area='CNV_PB_NearHome', player=s1)
            else:
                counted('CNV_PB_Far', '到远厂', t, template=tank, area=at.FAR, player=s1)
            counted('CNV_PB_Home', '回家', t, template=tank, area=at.HOME, player=s1)
            if build.startswith('aipullh') or build == 'aipullga' or build in IDLE:
                timer = 'Test - hurt timer'
                t.scripts += [Script('Test - hurt set', [], [('SET_MILLISECOND_TIMER', timer,
                                                              wake + IDLE_HURT[build] if build in IDLE else HURT_AT)]),
                              Script('Test - hurt tanks', [('TIMER_EXPIRED', timer)],
                                     [('UNIT_SET_HEALTH', n, HURT) for n in tanks])]
            if build == 'aipullr1':          # after the wake's SKIRMISH_AI_USE_REPAIRS 0
                t.scripts.append(Script('Test - repairs on', [('TIMER_EXPIRED', timer)],
                                        [('SKIRMISH_AI_USE_REPAIRS', s1, 1)]))
            if build in ('aipull1', 'aipullh1', 'aipullga') or build in IDLE:
                # IDLE: from 5 s after the wake (aipullsov's Soviet tanks were home s19-28, wake ~s9, then ground up)
                t.expect += [('回家', wake + (5.0 if build in IDLE else LATE), 'ever>=', 1, end)]
            else:
                t.expect += [('回家', wake + LATE, '==', 0, end)]
        elif build.startswith(('airevb', 'airevs')):
            # B 11-24 SiegeWeaponBuffer: the bears (healed every frame) stay; the result is the host's team states
            # (readings: never 4, b1 = b0); the tanks die s65-s77 on the bench (the bears or the turret reach them)
            bears = [m.role(f'rev foe {k}').name for k in (1, 2)]
            t.scripts.append(Script('Test - keep', [], [('UNIT_SET_HEALTH', n, 100.0) for n in bears], once=False))
            counted('CNV_PB_Foes', '敌熊', t, template=m.find(bears[0]).template, player=p1)
            t.expect += [('敌熊', wake, '>=', 2, end)]
        elif build.startswith('airevk'):
            # D round 132: two of the player's Guardians ~54 from the column (missions FOE_AT); both sides healed every
            # frame so the target stays; 近敌 = s1 tanks within NEAR_FOE of the foes' midpoint (start: all 4 inside;
            # backed off to R - 10 = 135 from a foe: outside)
            foes = [m.role(f'rev foe {k}').name for k in (1, 2)]
            if build == 'airevkh':           # D round 182: read before the keep -- the health the frame's fire left
                for k, n in enumerate(foes, 1):
                    t.counters.append((f'CNV_PB_FoeHp{k}', f'血{k}'))
                    t.scripts.append(Script(f'Test - foe health {k}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', n,
                                                                             f'CNV_PB_FoeHp{k}')], once=False))
            t.scripts.append(Script('Test - keep', [], [('UNIT_SET_HEALTH', n, 100.0) for n in foes + tanks], once=False))
            if build in NO_POWER:            # D round 183: the AI's f166 strike (airevkh) is not what k1 / k2 test
                t.scripts.append(Script('Test - no AI power', [], [('PLAYER_SET_SPECIAL_POWER_COUNTDOWN', s1, AI_POWER,
                                                                     NO_POWER_S)], once=False))
            fx = sum(m.find(n).x for n in foes) / 2
            fy = sum(m.find(n).y for n in foes) / 2
            t.areas['CNV_PB_NearFoe'] = square(fx, fy, NEAR_FOE)
            counted('CNV_PB_NearF', '近敌', t, template=tank, area='CNV_PB_NearFoe', player=s1)
            counted('CNV_PB_Foes', '敌坦', t, template=m.find(foes[0]).template, player=p1)
            # d131 1: on, a member with the foe as its own target backs off to R - 10 at its next micro pass; off, stays
            if build.startswith('airevkp'):
                # D round 135b: no script swap -- the plan moves the two foes beside the team's two members at POKE_AT
                # (the bench's ra3ext_cmd.txt, inject.pos); a dead foe logs id=-1. The result is inject.look's poke and
                # command records, not a counter: 坦克数 here only says the run went on
                t.inject = [inject.pos(POKE_AT, n, x, y) for n, (x, y) in zip(foes, POKE_XY)]
                t.expect += [('坦克数', 1.0, '>=', 2, end)]
            elif build.startswith('airevk2'):
                # D round 133: the two foes deleted, one Guardian spawned on each Hammer (every member's only foe a few
                # tens off); kept alive too. 敌坦 4 from LATE_AT says the spawn took; the result is the host's aim / dest
                late = [f'{LATE_NAME} {k + 1}' for k in range(len(tanks))]
                timer = 'Test - late timer'
                t.scripts += [Script('Test - late set', [], [('SET_MILLISECOND_TIMER', timer, LATE_AT)]),
                              Script('Test - late swap', [('TIMER_EXPIRED', timer)],
                                     [('NAMED_DELETE', n) for n in foes]
                                     + [('UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION', n,
                                         m.find(foes[0]).template, m.team(), k) for n, k in zip(late, tanks)]),
                              Script('Test - late keep', [], [('UNIT_SET_HEALTH', n, 100.0) for n in late], once=False)]
                t.expect += [('敌坦', LATE_AT + 2.0, 'ever>=', 3, LATE_AT + 10.0)]
            else:
                # D round 183: with the power off airevk1 = airevk0 (nobody joins: 4 near all run)
                t.expect += ([('近敌', wake, 'ever<', 4, wake + 20.0)] if build.endswith('1') and build not in NO_POWER
                             else [('近敌', wake + 2.0, '>=', 3, wake + 20.0)])
        elif build.startswith('airevp') or build.startswith('airevt'):
            # airevp: the far plant beside the tanks, no guards (missions CLOSE_AT); airevt: a player's turret there instead
            turret = build.startswith('airevt')
            g = m.find(m.role('rev turret').name) if turret else o
            near, ring = (100.0, 250.0) if turret else (150.0, 300.0)
            t.counters.append(('CNV_PB_PlantHp', '塔血' if turret else '厂血'))
            t.scripts.append(Script('Test - target health', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', g.name,
                                                                  'CNV_PB_PlantHp')], once=False))
            # first runs: the tanks shot the plant to 2 % before the wake (s8) and both builds left it s19-24 alike -- the
            # target gone, not a back-up. So the target is healed back every frame: it stays
            t.scripts.append(Script('Test - target keep', [], [('UNIT_SET_HEALTH', g.name, 100.0)], once=False))
            t.areas['CNV_PB_Near'] = square(g.x, g.y, near)
            t.areas['CNV_PB_Ring'] = square(g.x, g.y, ring)
            lab = '近塔' if turret else '近厂'
            counted('CNV_PB_NearC', lab, t, template=tank, area='CNV_PB_Near', player=s1)
            counted('CNV_PB_Far', '中圈', t, template=tank, area='CNV_PB_Ring', player=s1)
            # model: on, every tank backs off to range - 10 (out of the near square) within a micro update or two;
            # off, they stay
            t.expect += ([(lab, wake, 'ever<', 1, wake + 15.0)] if build.endswith('1')
                         else [(lab, wake + 2.0, '>=', 3, wake + 15.0)])
        else:
            t.areas['CNV_PB_Near'] = square(o.x, o.y, 150.0)
            counted('CNV_PB_NearC', '近厂', t, template=tank, area='CNV_PB_Near', player=s1)
            counted('CNV_PB_Far', '到远厂', t, template=tank, area=at.FAR, player=s1)
            t.expect += [('守军数', wake, 'ever>=', 12, end)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('aipull1', 'aipull0', 'aipullh1', 'aipullh0', 'aipullga', 'aipulli1', 'aipullr1', 'aipullp1', 'aipullbig', 'aipullsov', 'aipullsvx', 'aipulljp', 'aipullsnx', 'aipullsny',
                                                               'aipullav', 'aipullax', 'aipullavt', 'aipullavc', 'aipullavn', 'aipullwt', 'aipullavp', 'aipullaxp', 'airev1', 'airev0', 'airev1t', 'airev0t', 'airevidx', 'airevgt', 'airevat', 'airevit', 'airevp1', 'airevp0', 'airevp1t', 'airevt1', 'airevt0',
                                                               'airevk1', 'airevk0', 'airevkg1', 'airevk2', 'airevk2o', 'airevkp1', 'airevkp0', 'airevkh',
                                                               'airevb1', 'airevb0', 'airevs1', 'airevs0', 'airevsb')}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a))


def engine_aipullpct():
    """PullbackInjuredHealthPct finite contrast; reuse engine_aipullback aipullsov.

    Before measurement: HURT=30 at wake+0.5, unchanged faction/Crane/other fields.
    High 0.5 should return to the Crane then be recycled; low 0.2 should reach
    the far plant first. Count health, living tanks, far area, home area. These
    readings cannot establish an exact threshold or the internal leave frame.

    Bench 2026-11-11, both checks PASS (health, alive, far, home):
      low0.2: health30 s9-13; far3 s15-16, far4 s17; home0 s3-33;
              after further injury one survivor home s34-39, alive0 from s40.
      high0.5: health30 s9-25; far0 throughout; home1 s19-20, home4 s23;
               alive3 s24-25, 2 s26, 1 s27, 0 from s28 (Crane recycling).
    The simulator's live facility hook now distinguishes the initial return:
    high sends four vehicles home without reaching the far plant; low reaches
    the far plant first. benches/ai/tactics/readings.toml#engine_aipullpct separates the passing return
    from the Crane recycling (a mismatch). Exact seconds, late return and
    recycling are not claimed by the passing threshold tests.
    """
    original = engine_aipullback()["shared"].a


    def a(m, high):
        t = original(m, 'aipullsov')
        wake = m.facts['wake at']
        t.expect = [('血量', wake + 1, 'ever==', 30, wake + 5)]
        if high:
            t.expect += [('回家', wake + 5, 'ever>=', 1, wake + 25),
                         ('坦克数', wake + 15, 'ever==', 0, wake + 35)]
        else:
            t.expect += [('到远厂', wake + 1, 'ever>=', 3, wake + 20)]
        return t


    CHECKS = {'aipullpctlo': {'a': lambda m: a(m, False)},
              'aipullpcthi': {'a': lambda m: a(m, True)}}
    return dict(CHECKS=CHECKS)


def engine_aireactive():
    """Engine probe: the AI's ReactiveDefense tactic and ReactiveDefenseRadius (benches/ai/tactics/scenes.py#aireactive_bench).

      a  家300 / 敌300 / 敌存活   s1 Peacekeepers inside a square of half-width 300 around the AI yard / around the foe spot
                               (1000 straight south of the yard) / the player's Peacekeepers inside a half-width-2500
                               square around the foe spot (the one foe) -- once a second from the start to wake + 60 s

    Model prediction: R = 1200 -> the team (the state runs every 31st frame once the base exists after the wake's
    MAKE_BASE) attack-moves to the foe (1000 < 1200): 敌300 >= 1 and the foe dies (敌存活 0). R = 750 -> the foe is never
    chased (1000 > 750): 家300 stays 4, 敌300 stays 0, 敌存活 stays 1. Expectation (since the first readings below): 敌存活
    at mission second 30 is 0 for R > 1000, 1 otherwise.

    读数
    Bench 2026-11-14 aireact750 a (CampAIReact750A, run CampAIReact750A_mcp_1114_133453): PASS. 家300 4 / 敌300 0 / 敌存活 1
      at s1 and unchanged to the end (s80): the foe 1000 away is never chased with R = 750.
    Bench 2026-11-14 aireact1200 a (CampAIRea1200A, run CampAIRea1200A_mcp_1114_134120; the build name is CampAIRea1200:
      CampAIReact1200A is 16 characters, which the first attempt hit): FAIL 0 of 1 -- only the weak 敌存活 >= 0 at s70,
      "no reading" (the watch ran to s102.8 and the s70 frame is not in the readings; not a game result). Readings:
      家300 4 @ s1-s3, 3 @ s4, 2 @ s5, 1 @ s7, 0 @ s8-s36, 4 again from s37 to the end (s103); 敌300 0 until s12, 2 @ s14,
      3 @ s15, 4 @ s17-s27, 2 @ s28, 0 from s29 to the end; 敌存活 1 until s19, 0 from s20 to the end. So with R = 1200
      the team leaves in the first seconds (before the s10 wake: the state runs without it, as aidefense's control),
      reaches the foe at ~s14, the foe is dead by s20, and after the team disbands (EndBehavior DISBAND) the four walk
      home (out of the foe square s28-s36, back inside the home square at s37). The foe is chased at 1000 with R = 1200
      and not with R = 750: the radius gates the reaction. The prediction was right about the radius, wrong about the
      timing (it expected the state to wait for the wake's MAKE_BASE).
    """
    from parts import Script, Test, counted, square

    LAG = 4.0
    AFTER = 60.0
    NEAR = 300.0
    BIG = 2500.0
    FOE_DIST = 1000.0   # benches/ai/tactics/scenes.py#aireactive_bench
    CHASED_BY = 30.0


    def a(m):
        t = Test()
        s1, p1 = m.player('s1'), m.player('p1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        (inf,) = m.cnv_units
        x, y = m.site('east base')
        fx, fy = m.site('east base', 0.0, -FOE_DIST)
        t.areas['CNV RD Home'] = square(x, y, NEAR)
        t.areas['CNV RD Foe'] = square(fx, fy, NEAR)
        t.areas['CNV RD FoeBig'] = square(fx, fy, BIG)
        counted('CNV_RD_HOME', '家300', t, template=inf, area='CNV RD Home', player=s1)
        counted('CNV_RD_FOE', '敌300', t, template=inf, area='CNV RD Foe', player=s1)
        counted('CNV_RD_ALIVE', '敌存活', t, template=inf, area='CNV RD FoeBig', player=p1)
        end = m.facts['wake at'] + AFTER
        # bench 2026-11-14: R 1200 kills the foe 1000 out by s20, R 750 never goes -- asserted at mission second 30
        alive = 0 if m.facts['radius'] > FOE_DIST else 1
        t.expect += [('敌存活', CHASED_BY, '==', alive, CHASED_BY + 1)]
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a} for k in ('aireact750', 'aireact1200')}
    return dict(CHECKS=CHECKS)


def engine_airelease():
    """Direct named-team release observation; 99 means the instance is absent.

    Prediction (INFERRED until measured): both defense teams first hold two;
    after the timed STANDARD consumer starts, priority releases two to attack,
    NEVER_RELEASE keeps them. No production, deaths or other candidate units.

    RESULTS (2026-11-12): both diagnostic checks FAIL. Defense/attack remain
    99/99, live tanks 2, initial-hold latch 0 throughout (never s1-70,
    priority s1-73). Recruitment is unobserved; no release conclusion follows.
    Model reads 0/0 instead; strict xfails retain the observation gap.
    CNVTeams follow-up: both first defend with IDs 3166/3167 at f166;
    priority transfers the same IDs to active attack at f541, NEVER retains them.
    Tests replay logged membership and model at f301/601/976. Legacy HUD FAILs
    remain diagnostics; transient additional attack IDs are an unmodelled gap.
    See work/re/c_release_teams_report.md and c_never_release_report.md.
    """
    from model import Script, Test, counted


    def a(m):
        t = Test()
        t.scripts.append(Script('Release - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        for key, counter, label in [('release defense', 'CNV_R_Def', '防御人数'),
                                     ('release attack', 'CNV_R_Atk', '进攻人数')]:
            team = m.map.AI_TEAMS[key]
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Release - {key} absent', [], [('SET_COUNTER', counter, 99)], once=False))
            for n in range(3):
                t.scripts.append(Script(f'Release - {key} below {n}',
                                        [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                                        [('SET_COUNTER', counter, n)], once=False))
        counted('CNV_R_Live', '坦克总数', t, player=m.player('s1'), template=m.cnv_units[0])
        t.counters.append(('CNV_R_Held', '曾防御量'))
        t.scripts.append(Script('Release - held', [('COUNTER', 'CNV_R_Def', 2, 2)],
                                [('SET_COUNTER', 'CNV_R_Held', 2)]))
        never = m.facts['never release']
        t.expect = [('防御人数', 25, '==', 2, 29), ('曾防御量', 25, '==', 2),
                    ('坦克总数', 1, '==', 2),
                    ('防御人数', 55, '==', 2, 65)] if never else [
                        ('防御人数', 25, '==', 2, 29), ('曾防御量', 25, '==', 2),
                        ('坦克总数', 1, '==', 2), ('进攻人数', 55, '==', 2, 65)]
        t.bench = [('bench_watch', dict(seconds=69, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('airelnever', 'airelprio')}
    return dict(CHECKS=CHECKS)


@cache
def engine_airetreat():
    """Engine probe: the skirmish AI team's retreat and its EngagePassiveTargets switch (benches/ai/tactics/scenes.py#airetreat_bench;
    docs/engine/aiteamstate.md; the simulator against these readings: tests/test_simai.py).

    The probe's micro manager: StandardMicroManager_MEDIUM flattened, RetreatPowerAdvantage 0.2 and
    <AIMicroManagerData RetreatMinDistanceFromBase> 300 instead of retail 900 (benches/ai/tactics/scenes.py#airetreat_bench).
    It reaches the team only through the TeamTemplate's MicroManager="..." naming it: airet / airet0 and aipas1 / aipas0
    differ in one field of that data and nothing else, so the two pairs below are also the bench reading of TeamTemplate
    MicroManager (the team runs the micro data its MicroManager names; B round 110).

    Bench 2026-11-08 (all four PASS; wake at s10):
      airet   (步兵在家, 到远厂, 步兵数) 4 0 4 to s9 | out s10-s12 | 到远厂 2 @ s15-s16, 1 @ s17-s18 | home 1 @ s20 ... 4 @
              s26-s41 | out s42-s46 | 到远厂 2 @ s47-s48 | home 1 @ s49 ... 4 @ s54-s68 | out s69-s73 | 到远厂 2 @ s74-s76 |
              home 4 from s82; 步兵数 4 all along: the team turns round at the far plant's edge, walks home through the
              guards unhurt (a plain move), stands ~15 s, goes again -- a ~27-32 s cycle
      airet0  out s10-s12 | 到远厂 2 @ s15 ... 4 @ s17-s18 | 步兵数 3 @ s19, 2 @ s22, 1 @ s23, 0 from s25; never home again
      aipas1  旁厂血量 94 @ s11 (1 s after the wake), 3 @ s25, 1 from s26; the team within 450 of its base all the while
              (到旁厂 0: it shoots from beyond 120); 到远厂 0 to s85
      aipas0  out s10-s12 | 到远厂 2 @ s15, 4 @ s17-s34 | 旁厂血量 100 to s35, then (RAMPAGE: the nearest) 97 @ s36 ... 2 @
              s50; 到旁厂 3-4 @ s55-s57
    Bench 2026-11-10 (B round 112, both PASS; the state on a map flag at the wake s10, off at s18; the two differ only in
    the tactic's DisbandAfterRetreatTeamSize):
      airetf  (0, xsd default) out s19-s21 | 到远厂 2 @ s24-s25 | home 4 @ s31-s48 | out again s49-s54 | 到远厂 2-3 @
              s54-s58 | home 3 @ s64-s79 (步兵数 3 from s57) | out again s80-s84: the tactic goes on with its state off
      airetfd (999) out s18-s20 | 到远厂 2 @ s24-s25 | home 1 @ s29, 2 @ s30, 4 from s31 to s85: the retreat's end ended
              the tactic, the team was let go, and with the state off no new team -- DisbandAfterRetreatTeamSize as read
              (retreat check, work/re/l4_states.md: was state 1, now 8, members <= the size -> end)

      a  步兵在家 / 到远厂    Peacekeepers of s1 within 450 of the AI's base / 300 of the far power plant
         步兵数 (airet*)      Peacekeepers s1 owns
         到旁厂 / 旁厂血量 (aipas*)   s1's Peacekeepers within 120 of the side plant; its health in percent
         once a second, AFTER seconds after the wake

    Expectations are the model's (RA3-EngineModel ra3model/ai/tactics.py TacticsBlock._team_state, simai.Brain.fight); a
    FAIL is a reading too:
      airet   the team leaves, then some of it is back home (retreat) while alive
      airetd  as airet (DisbandAfterRetreatTeamSize 999 under an always-on state: a new team at once, no reading)
      airetf  the state on a flag, off 8 s after the wake: the team comes home, then out again (simulator s32 home, s42 out)
      airetfd airetf + DisbandAfterRetreatTeamSize 999: home, and all four home from wake + 35 to the end (simulator: the
              tactic ends at s36, no new team)
      airet0  the team leaves and nobody comes home (no retreat with RetreatPowerAdvantage 0)
      aipas1  the side plant is hurt (the team attacked the passive target on its way)
      aipas0  the side plant stays at 100 (EngagePassiveTargets off) and the team reaches the far plant
    """
    from benches.ai.targets.checks import engine_aitarget
    at = engine_aitarget()["shared"]
    from parts import Script, Test, counted, square

    AFTER = 70.0
    SIDE_AREA = 'CNV AI Side Plant Area'


    def a(m, build):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[at.HOME] = square(*m.site('east base'), 450.0)
        o = m.find(m.role('far plant').name)
        t.areas[at.FAR] = square(o.x, o.y, 300.0)
        (inf,) = m.cnv_units
        counted('CNV_AR_Home', '步兵在家', t, template=inf, area=at.HOME, player=s1)
        counted('CNV_AR_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
        wake = m.facts['wake at']
        end = wake + AFTER
        if build.startswith('airet'):
            counted('CNV_AR_Count', '步兵数', t, template=inf, player=s1)
            t.expect += [('步兵在家', wake + 5, 'ever==', 0, end)]          # it left
            if build in ('airet', 'airetd', 'airett', 'airetb3', 'airetb1'):
                t.expect += [('步兵在家', wake + 15, 'ever>=', 1, end)]     # and some came back
            elif build == 'airetf':                                         # back, then out again (the tactic goes on)
                t.expect += [('步兵在家', wake + 15, 'ever==', 4, end), ('步兵在家', wake + 35, 'ever==', 0, end)]
            elif build == 'airetfd':                                        # back, and home for good (the tactic ended)
                t.expect += [('步兵在家', wake + 15, 'ever==', 4, end), ('步兵在家', wake + 35, '==', 4, end)]
            else:
                t.expect += [('步兵在家', wake + 15, '==', 0, end)]
        else:
            side = m.find(m.facts['side plant'])
            t.areas[SIDE_AREA] = square(side.x, side.y, 120.0)
            counted('CNV_AR_Side', '到旁厂', t, template=inf, area=SIDE_AREA, player=s1)
            counted('CNV_AR_SideHp', '旁厂血量', t, health=m.facts['side plant'])
            soon = wake + 25.0                      # before the far plant falls and RAMPAGE takes the nearest one
            if build == 'aipas1':
                t.expect += [('旁厂血量', 1, 'ever<', 100, soon)]
            else:
                t.expect += [('旁厂血量', 1, '==', 100, soon), ('到远厂', 1, 'ever>=', 1, soon)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('airet', 'airett', 'airetb3', 'airetb1', 'airetd', 'airetf', 'airetfd', 'airet0', 'aipas1', 'aipas0')}
    return dict(CHECKS=CHECKS, shared=SimpleNamespace(a=a))


def engine_aisort():
    """SortByDistance: named candidate departure, latched at script-frame precision.

    First departure identity: 0 none, 1 far, 2 near, 3 both in the same frame.
    Far is inserted first; near is closer to the fixed enemy structure but farther
    from the AI yard. Prediction: off sends far, on sends near. An 80-unit square
    around each initial position observes departure, not actual team membership.
    No exact distance metric, tie rule or production/release path is established.

    RESULTS (2026-11-11): aisort0:a / aisort1:a both PASS, 5 assertions each.
    Both candidates remain in place through s9. Off: far first at frame 177,
    near stays through s45. On: near first at frame 178, far stays through s45.
    INFERRED: the switch changes selection toward the tactical target; actual
    dynamic-team membership remains a gap. See work/re/c_sort_report.md.
    """
    from model import Script, Test, counted, square


    def a(m):
        t = Test()
        t.scripts += [Script('Sort - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                      Script('Sort - clock', [], [('INCREMENT_COUNTER', 1, 'CNV_SD_Clock')], once=False)]
        outside = []
        for identity, name, pos in m.cnv_candidates:
            area = f'CNV Sort {identity}'
            t.areas[area] = square(*pos, m.facts['departure radius'])
            counted(f'CNV_SD_{identity}', '远在原位' if identity == 'far' else '近在原位',
                    t, named=name, area=area)
            outside.append(('NAMED_OUTSIDE_AREA', name, area))
        t.counters += [('CNV_SD_First', '首离身份'), ('CNV_SD_Frame', '首离帧')]
        # Evaluate the simultaneous case before either singleton: script order
        # cannot turn a same-frame departure into a false winner.
        for identity, conditions in ((3, outside), (1, outside[:1]), (2, outside[1:])):
            t.scripts.append(Script(f'Sort - first {identity}',
                                    [('COUNTER', 'CNV_SD_First', 2, 0), *conditions],
                                    [('SET_COUNTER', 'CNV_SD_First', identity),
                                     ('SET_COUNTER_TO_COUNTER', 'CNV_SD_Frame', 'CNV_SD_Clock')]))
        near = m.facts['sort by distance']
        t.expect = [('远在原位', 1, '==', 1, 9), ('近在原位', 1, '==', 1, 9),
                    ('首离身份', 35, '==', 2 if near else 1, 36),
                    ('远在原位', 35, '==', near, 36), ('近在原位', 35, '==', 1 - near, 36)]
        t.bench = [('bench_watch', dict(seconds=44, every=1, sheet=False, lines=4))]
        return t


    CHECKS = {name: {'a': a} for name in ('aisort0', 'aisort1')}
    return dict(CHECKS=CHECKS)


def engine_aispecial():
    """Engine probe: when the skirmish AI fires its superweapon and at which pile (benches/ai/tactics/scenes.py#aispecial_bench).

    s1 (AlliedBalanced, woken at 10 s, money 0) owns a proton collider (SpecialPowerParticleCannon). Piles of the player's
    structures: A 4 barracks (2000), B 3 war factories (6000), C 5 base defenses (4000) -- see the mission. The countdown
    unit of NAMED_SET_SPECIAL_POWER_COUNTDOWN is not known (engine_power: 5 s did not make it ready in 15 s, 0 does), so the
    power is made ready by countdown 0 set k frames after the wake, k = 0 / 5 / 10 (the ready frame then lands on different
    phases of the AI's 15-frame check):

      a  k = 0     b  k = 5     c  k = 10     t  k = 0, which pile is hit     (build aispecial, run 60 s after the wake)
      d  k = 0 on build aispecialhid: one pile of 5 defenses far from the AI, not revealed to s1

    Counters (four lines), all from the wake on:
      帧数    frames since the wake (the wake frame is +-1)
      就绪帧  frames since SKIRMISH_SPECIAL_POWER_READY(s1) was first seen   -> ready at frame = 帧数 - 就绪帧
      放帧    frames since PLAYER_TRIGGERED_SPECIAL_POWER(s1) was first seen -> fired at frame = 帧数 - 放帧
      受损    structures of the player that were ever hurt or destroyed, A x 1 + B x 10 + C x 100 (d: H x 1)

    (Final design: a / b / c set countdown 5 (seconds, integer) at wake frame 1 / 6 / 11; t and d set 0. A first try of a / b / c
    with 5.2 / 5.4 s: the fractions acted as 0, see below. 就绪帧 latches only when seen at frame >= delay + 3.)

    读数
    Bench 2026-11-06 (one run each; fired at / ready at = 帧数 - 放帧 / 帧数 - 就绪帧 at the last row, +-1):
      Weapon: ParticleCannonWeapon -> ParticleAcceleratorFinalWeapon, Damage 400, Radius 250, DamageTaperOff 200. Building
      AlliedSuperWeaponAdvanced (BuildCost 2500, -75 power). Piles: A 4 AlliedBarracks 500 = 2000; B 3 AlliedWarFactory 2000
      = 6000; C 5 AlliedBaseDefense 800 = 4000.
      First try, countdown 0 at frame 1 (CampAISpecialA): ready from the first frame; fired at frame 61 after the wake.
      t CampAISpecialT (countdown 0): ready ~2, fired at 61 (948-887); 受损 500 = all five of C hit, A 0, B 0 (stable
        from s21). The model (C: A and C both qualify, the dearer; B has only 3) holds.
      a CampAISpecialA (5 s at frame 1): 就绪帧 stayed 0 (READY never seen in 950 frames although it fired); fired at
        136 (950-814); 受损 500.
      b (5 s set at frame 6): 就绪帧 0, fired at 136; c (set at frame 11): 就绪帧 0, fired at 136. So the fire frame did
        NOT move with the phase of the countdown set (0 / 5 / 10 frames): 61 with ready at once, 136 = 61 + 75 (= 5 s x
        15) with a 5 s countdown. The "ready at frame 0..14 later" phase shift was not seen. 受损 500 each.
      5.2 / 5.4 s (first try, b / c at frame 1): READY seen at frame 2, fired at 61 (950-889, 953-892): a fractional
        countdown acts as 0 (the integer 5 is 5 s: +75 frames).
      d CampAIHidD (5 defenses at west field, s1 not revealed, countdown 0): ready ~2, fired at 61 (951-890); 受损 5 =
        all five hit. The model "unseen -> not fired" is REFUTED here: the AI fires at structures it was never shown
        (not chased: whether s1 shares the map's initial vision / sees all structures).
        Round 13: the program's test (work/re/l4_specials.md) is "stealthed and not detected", nothing about the shroud -- so this fits.
    Round 13 (2026-11-06, one run each; countdown 60 at frame 1 holds the power, then the late setting):
      e  0 at frame 201: ready 202, fired 256      f  0 at 208: ready 209, fired 256      g  0 at 214: ready 215, fired 271
      h  5 at frame 201: READY never seen, fired 331                                       受损 500 in all four
      One rule fits all eight fire frames (t a b c e f g h): the AI looks every 15 frames, at frames 1, 16, 31 ... after
      the wake; a countdown of N whole seconds set at frame k makes the power ready at k + 1 + 15 N; a look fires it only
      once it has been ready 45 frames (3 s). t: ready 2, the look at 46 is 44 frames on, so 61. So the 61 is not a
      start-up wait: every fire comes >= 3 s after ready. Where the 3 s comes from is not read. READY (the script
      condition) is never true after a countdown > 0, though the power fires (not chased).
    """
    from parts import Script, Test

    LAG = 4.0
    RUN = 60.0
    # countdowns set: [(frames after the wake, value)] (a first try of a / b / c with 5.2 / 5.4 read as 0)
    SETS = {'a': [(0, 5)], 'b': [(5, 5)], 'c': [(10, 5)], 't': [(0, 0)], 'd': [(0, 0)],
            # round 13: hold the power with 60 s, free it late -> is 61 a one-off start delay or a delay after ready?
            'e': [(0, 60), (200, 0)], 'f': [(0, 60), (207, 0)], 'g': [(0, 60), (213, 0)], 'h': [(0, 60), (200, 5)]}


    def probe(m, which):
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        wake, power, collider = m.facts['wake at'], m.facts['power'], m.role('collider').name
        start = [('MAP_REVEAL_ALL_PERM', p1)]
        if m.facts['reveal to ai']:
            start.append(('MAP_REVEAL_ALL_PERM', s1))
        t.scripts.append(Script('Test - reveal', [], start))
        t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AS_Tick')], once=False),
                      Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AS_Tick', 3, 30)],
                             [('SET_FLAG', 'Test Woke', 1)])]
        woke = ('FLAG', 'Test Woke', 1)
        t.counters += [('CNV_AS_Frames', '帧数'), ('CNV_AS_Ready', '就绪帧'), ('CNV_AS_Cast', '放帧'),
                       ('CNV_AS_Hit', '受损')]
        t.scripts += [
            Script('Test - frames', [woke], [('INCREMENT_COUNTER', 1, 'CNV_AS_Frames')], once=False),
            *[Script(f'Test - countdown {i}', [woke, ('COUNTER', 'CNV_AS_Frames', 2, at + 1)],
                     [('NAMED_SET_SPECIAL_POWER_COUNTDOWN', collider, power, value)])
              for i, (at, value) in enumerate(SETS[which])],
            Script('Test - ready seen', [woke, ('COUNTER', 'CNV_AS_Frames', 3, SETS[which][-1][0] + 3),
                                         ('SKIRMISH_SPECIAL_POWER_READY', s1, power)],
                   [('SET_FLAG', 'Test Ready', 1)]),
            Script('Test - ready count', [('FLAG', 'Test Ready', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AS_Ready')],
                   once=False),
            Script('Test - cast seen', [woke, ('PLAYER_TRIGGERED_SPECIAL_POWER', s1, power)],
                   [('SET_FLAG', 'Test Cast', 1)]),
            Script('Test - cast count', [('FLAG', 'Test Cast', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AS_Cast')],
                   once=False)]
        for letter, weight in m.facts['piles'].items():
            for part in m.roles(letter):
                nm = part.name
                flag = f'Test Hurt {nm}'
                act = [('SET_FLAG', flag, 1), ('INCREMENT_COUNTER', weight, 'CNV_AS_Hit')]
                t.scripts += [Script(f'Test - hurt {nm}', [('UNIT_HEALTH', nm, 0, 100)], act),
                              Script(f'Test - dead {nm}', [('NAMED_DESTROYED', nm), ('FLAG', flag, 0)], act)]
        t.expect += [('帧数', wake + LAG, 'ever>=', 1, wake + RUN)]
        t.bench = [('bench_watch', dict(seconds=wake + RUN + LAG, every=10, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'aispecial': {w: (lambda m, w=w: probe(m, w)) for w in 'abctefgh'},
              'aispecialhid': {'d': lambda m: probe(m, 'd')},
              'aispecoff': {'t': lambda m: probe(m, 't')},   # UsePlayerPowersAtDifficulty "" / "HARD BRUTAL" at MEDIUM
              'aispechb': {'t': lambda m: probe(m, 't')}}
    return dict(CHECKS=CHECKS)


def engine_aiswitch():
    """Engine probe: the skirmish AI's script switches SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES, SKIRMISH_AI_USE_REPAIRS,
    SKIRMISH_AI_USE_REBUILD_SYSTEM (benches/ai/tactics/scenes.py#aiswitch_bench; docs/engine/aiswitches.md).

      a  步兵在家 / 到近厂 / 到远厂   Peacekeepers of s1 within 450 of the AI's base / 300 of the near / far power plant
         电厂血量 (aiswrep*)       the AI's own plant's health in percent (set to 50 at the start)
         电厂数 (aiswreb*)         AlliedPowerPlants s1 owns (its own one is killed 5 s after the wake)
         once a second, AFTER seconds after the wake

    Expectations are the model's (RA3-EngineModel ra3model/ai/player.py, simai.Brain.switches); a FAIL is a reading too:
      aisw0near  nobody leaves (priorities 0 empty the enemy table: ClosestStructure finds no enemy structure)
      aisw0far   the team reaches the far plant (a NamedObject target does not look at the enemy table)
      aiswrep1 / aiswrep0   the plant stays at 50 (the program's gate would let 1 repair; the bench says it does not)
      aiswreb1 / aiswreb0   no plant again after the kill (the model rebuilds nothing; who reads the list is NOT READ)

    读数
    Bench 2026-11-08 (one run each; Sonnet ran, B read):
      aisw0near  PASS. 步兵在家 4 s1-s75, nobody at either plant: priorities 0 empty the enemy table, no team goes.
      aisw0far   PASS. 步兵在家 0 from s12; 到远厂 2 @ s15, 4 s17-s33, 0 from s35 (the plant down); then 到近厂 1 @ s42,
                 4 s44-s51 (RAMPAGE), 0 from s66: a NamedObject target ignores the enemy table, RAMPAGE too.
      aiswrep1   FAIL against the first expectation (>= 51): 电厂血量 50 s1-s75 -- repairs 1 did not repair in 60 s
                 (money 0 at the time? a brain flag? the personality bit? open). The team went to the near plant at s13.
      aiswrep0   电厂血量 50 s1-s107 (the watch ran slow after s75, so the s69 reading was missing: FAIL by no row).
      aiswreb1   PASS. 电厂数 1 to s12, 0 from s14 to s120 (5000 money): rebuild 1 did not put the plant back in 105 s.
      aiswreb0   PASS. 电厂数 0 from s14 to s119, as reb1.
    """
    from benches.ai.targets.checks import engine_aitarget
    at = engine_aitarget()["shared"]
    from parts import Script, Test, counted, square

    AFTER = {'aiswreb1': 90.0, 'aiswreb0': 90.0, 'aiswreb1z': 90.0}
    PLANT = 'AlliedPowerPlant'


    def a(m, build):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[at.HOME] = square(*m.site('east base'), 450.0)
        for area, role in ((at.NEAR, 'near plant'), (at.FAR, 'far plant')):
            o = m.find(m.role(role).name)
            t.areas[area] = square(o.x, o.y, 300.0)
        (inf,) = m.cnv_units
        counted('CNV_AS_Home', '步兵在家', t, template=inf, area=at.HOME, player=s1)
        counted('CNV_AS_Near', '到近厂', t, template=inf, area=at.NEAR, player=s1)
        counted('CNV_AS_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
        wake = m.facts['wake at']
        end = wake + AFTER.get(build, 60.0)
        if build.startswith('aiswrep'):
            counted('CNV_AS_Health', '电厂血量', t, health=m.facts['own plant'])
            t.expect += [('电厂血量', end - 1, '==', 50, end)]
        elif build.startswith('aiswreb'):
            counted('CNV_AS_Plants', '电厂数', t, template=PLANT, player=s1)
            t.expect += [('电厂数', m.facts['kill at'] + 2, '==', 0, end)]
        elif build == 'aisw0near':
            t.expect += [('步兵在家', 1, '==', 4, end)]
        else:
            t.expect += [('到远厂', 1, 'ever>=', 1, end)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in
              ('aisw0near', 'aisw0far', 'aiswrep1', 'aiswrep0', 'aiswreb1', 'aiswreb0', 'aiswreb1z')}
    return dict(CHECKS=CHECKS)


def engine_aitactical():
    """EngageTacticalTarget on/off, with hostile/passive acquisition disabled.

    Prediction before bench: the on team receives explicit attacks on the nearest
    power plant, the off team only attack-moves to its point. The unarmed plant
    cannot provoke retaliation. At 40 s on has damaged it, off leaves it at 100%.
    Both retain four Peacekeepers. This tests dispatch, not exact firing timing.

    Bench 2026-11-11: aitacon:a / aitacoff:a PASS (one run each). On reads
    100% through s12, 84% at s13, 0% from s22 through s43; off stays 100%
    through s48. Both retain four infantry. Replay: tests/test_engage_tactical.py.
    Only an object target in range, with passive/hostile dispatch disabled, is
    covered; point targets, competing enemies and the exact scan boundary are not.
    """
    from parts import Script, Test, counted


    def check(m):
        t = Test()
        t.counters.append(('Tac HP', '目标血量'))
        t.scripts = [Script('Tac reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                     Script('Tac hp', [], [('SET_COUNTER', 'Tac HP', 0),
                                          ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role('target').name, 'Tac HP')],
                            once=False)]
        counted('Tac Alive', '步兵存活', t, template=m.cnv_units[0], player=m.player('s1'))
        t.expect = [('目标血量', 40, '<' if m.facts['tactical enabled'] else '==', 100, 42),
                    ('步兵存活', 40, '==', 4, 42)]
        t.bench = [('bench_watch', dict(seconds=42, every=1, sheet=False, lines=2))]
        return t


    CHECKS = {key: {'a': check} for key in ('aitacon', 'aitacoff')}
    return dict(CHECKS=CHECKS)


def engine_aiteamfields():
    """Engine line D round 148: GatherWaypoint, MaxTypesOfUnits, Priority=HOTSPOT (benches/ai/tactics/scenes.py#aiteamfields_bench).
    Three counters a build (a fourth reads '?'), once a second; the team states and members are in the CNVTeams log.

      aigath*   步兵在家 / 到路点 / 到远厂   Peacekeepers of s1 within 450 of the AI base, within 300 of the gather
                waypoint ('route 2'), within 300 of the far plant; 60 s after the wake
                expected (the program, work/re d130 section 1): aigathwp -- 到路点 ever >= 2, then 到远厂 ever >= 1;
                aigathno / aigathbad -- 到路点 0 all along, 到远厂 ever >= 1
      aimaxty*  坦克在家 / 步兵在家 / 标枪在家   Guardians / Peacekeepers / Javelins of s1 within 450 of the AI base
                expected at s40 (the model, ra3model/ai/teams.py: the first type met, in the order the units are offered;
                simai offers the Peacekeepers first, out s16): aimaxty1 -- 2 / 0 / 2; aimaxty3 -- 0 / 0 / 0 (out s18-21)
      aihot*    坦克总数 / 坦克在家 / 到目标   s1's Guardians; within 450 of the AI base; within 300 of the player's plant
                (the attack's ClosestStructure) -- to s69 (the attack state from s35, airelprio's transfer f541)
                expected: released (aihotstd, aihotscr, aicoophi, aidefhst) -- 到目标 ever >= 1 by s69; kept (aihotdef,
                aicoopsc, aidefhhi) -- 到目标 0 all along
    """
    from benches.ai.targets.checks import engine_aitarget
    at = engine_aitarget()["shared"]
    from parts import Script, Test, counted, square

    HOME = 'CNV AI Base Area'
    GATHER = 'CNV AI Gather Area'
    TARGET = 'CNV AI Target Area'


    def _reveal(m, t):
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[HOME] = square(*m.site('east base'), 450.0)


    def gather(m):
        t = Test()
        _reveal(m, t)
        s1, (inf,) = m.player('s1'), m.cnv_units
        t.areas[GATHER] = square(*m.point('wp target'), 300.0)
        o = m.find(m.role('far plant').name)
        t.areas[at.FAR] = square(o.x, o.y, 300.0)
        counted('CNV_GW_Home', '步兵在家', t, template=inf, area=HOME, player=s1)
        counted('CNV_GW_Gather', '到路点', t, template=inf, area=GATHER, player=s1)
        counted('CNV_GW_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
        end = m.facts['wake at'] + 60.0
        if m.facts['gather waypoint']:
            t.expect += [('到路点', 1, 'ever>=', 2, end), ('到远厂', 1, 'ever>=', 1, end)]
        else:
            t.expect += [('到路点', 1, '==', 0, end), ('到远厂', 1, 'ever>=', 1, end)]
        t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def max_types(m):
        t = Test()
        _reveal(m, t)
        s1 = m.player('s1')
        labels = ('坦克在家', '步兵在家', '标枪在家')
        for k, (unit, label) in enumerate(zip(m.cnv_units, labels)):
            counted(f'CNV_MT_{k}', label, t, template=unit, area=HOME, player=s1)
        want = (2, 0, 2) if m.facts['max types'] == 1 else (0, 0, 0)
        t.expect += [(label, 40.0, '==', n) for label, n in zip(labels, want)]
        t.bench = [('bench_watch', dict(seconds=50.0 + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def hotspot(m):
        t = Test()
        _reveal(m, t)
        s1, tank = m.player('s1'), m.cnv_units[0]
        o = m.find(m.role('player target').name)
        t.areas[TARGET] = square(o.x, o.y, 300.0)
        counted('CNV_HS_Live', '坦克总数', t, template=tank, player=s1)
        counted('CNV_HS_Home', '坦克在家', t, template=tank, area=HOME, player=s1)
        counted('CNV_HS_Tgt', '到目标', t, template=tank, area=TARGET, player=s1)
        end = 69.0
        t.expect += [('坦克总数', 1, '==', 2)]
        t.expect += [('到目标', 1, 'ever>=', 1, end)] if m.facts['released'] else [('到目标', 1, '==', 0, end)]
        t.bench = [('bench_watch', dict(seconds=end, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {**{k: {'a': gather} for k in ('aigathwp', 'aigathno', 'aigathbad')},
              **{k: {'a': max_types} for k in ('aimaxty1', 'aimaxty3')},
              **{k: {'a': hotspot} for k in ('aihotstd', 'aihotdef', 'aihotscr', 'aicoophi', 'aicoopsc', 'aidefhst',
                                             'aidefhhi')}}
    return dict(CHECKS=CHECKS)


def engine_aiteamfilter():
    """Engine probe: which units a team template recruits (benches/ai/tactics/scenes.py#aiteamfilter_bench) -- ObjectFilter Rule ANY / NONE
    / ALL with IncludeThing / ExcludeThing, IncludeKindOf / ExcludeKindOf, MaxUnits: who leaves the AI's base?

      a  坦克在家   Guardians of s1 inside the base area (450 around the east base), once a second
         步兵在家   Peacekeepers of s1 there

    Expected (the mission's facts, the model's guess): at s40 坦克在家 == expect tanks home, 步兵在家 == expect infantry
    home (an always-on state's team leaves ~5 s after the wake, engine_aistate).

    读数
    Bench 2026-11-09 (B round 78, one run each, PASS 1 of 1 each; 4 Guardians + 4 Peacekeepers unless said):
      aitfany  a (ObjectFilter Rule ANY, IncludeThing Guardian): 坦克在家 4 -> 3 @ s14, 0 @ s15; 步兵在家 4 to s55.
      aitfnone a (Rule NONE, IncludeThing Guardian): 坦克在家 4 -> 2 @ s14, 0 @ s15; 步兵在家 4 to s55 -- NONE + the
               list takes only the list, as ANY (the model had NONE as no filter: all 8 out; fixed, private ai/teams.py).
      aitfall  a (Rule ALL, ExcludeThing Guardian): 步兵在家 4 -> 0 @ s15; 坦克在家 4 to s55.
      aitfki   a (IncludeKindOf INFANTRY, no ObjectFilter): 步兵在家 0 @ s15; 坦克在家 4 to s55.
      aitfke   a (IncludeKindOf CAN_ATTACK, ExcludeKindOf INFANTRY): 坦克在家 3 @ s14, 0 @ s15; 步兵在家 4 to s55.
      aitfmax  a (MaxUnits 3, 8 Guardians): 坦克在家 8 -> 6 @ s13, 5 from s14 to s55 -- one team of 3.
    The simulator (simai) gives the same six (benches/ai/tactics/readings.toml#engine_aiteamfilter team_filters_take_whom_the_bench_sent).
    Bench 2026-11-09 (B round 81, run_queue --jobs 2, all PASS; the second type: Riptide ACVs in the locomotor builds):
      aitfland  AllowedLocomotorTypes LAND: 坦克在家 2 @ s15, 0 from s16; 气垫船在家 4 to s55.
      aitfamph  AMPHIBIOUS: 气垫船在家 2 @ s13, 0 from s14; 坦克在家 4 to s55.
      aitfwat   WATER: both 4 to s55 -- an amphibious unit is not WATER.
      aitfosi   RegisteredObjectSet INFANTRY: 步兵在家 0 from s15; 坦克在家 4 to s55.
      aitfosv   VEHICLES: 坦克在家 2 @ s14, 0 from s15; 步兵在家 4 to s55.
      aitfosc   SKIRMISH_AI_NORMAL_COMBAT_UNITS: both go, later than the rest: 坦克在家 2 @ s20, 0 @ s21; 步兵在家 1 @
                s22, 0 from s23 (not modelled: the ~6 s).
    The model had the object set as no filter (private ai/teams.py OBJECT_SET_KIND now); simai gives these six
    (benches/ai/tactics/readings.toml#engine_aiteamfilter locomotor_types_and_object_sets_take_whom_the_bench_sent).
    Bench 2026-11-09 (B round 88): aiar0 / aiar1 / aiar2 (AlwaysRecruit false / true / true MaxUnits 4; 4 Guardians,
    the AI to build 2 more by an opener in an Allied war factory): all three 坦克在家 4 to s13, 3 @ s14, 0 from s15 to
    s75 -- no third tank ever seen at home: the opener most likely built nothing (no owned counter, not told apart).
    Not read for AlwaysRecruit. Next: count s1's owned Guardians (SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER, as aimicro).
    Bench 2026-11-09 (B round 89, 坦克拥有 = owned anywhere): aiar0 / aiar1 / aiar2 owned 4 from s1 to the end -- the
    opener built no Guardian at all (not the home box). aimicro's same opener (2 infantry, a script-placed barracks)
    built both. Told apart next by aiar3 (no Guardians placed: can the script-placed war factory build them) and aiar4
    (4 Guardians, the opener builds 2 Riptides: is it owning that template already) -- written, not benched.
    Bench 2026-11-09 (B round 92, PASS 1 of 1 each; aiar8's StaticDefense AlwaysRecruit team): aiar9 (new AI plant 1000
    south at s45) 坦克在新楼 0 to s107; aiar10 (placed tank 1 teleported 1200 south at s60 and s130) 坦克在外 1 for ~5 s /
    ~10 s, home again ~10 s after each -- held both times, the guard keeps its first target.
    """
    from parts import Test, counted, square, Script

    AREA = 'CNV AI Base Area'
    OUT_AREA = 'CNV AI Out Area'
    PLANT_AREA = 'CNV AI Far Plant Area'
    LAG = 4.0
    AT, SECONDS = 40.0, 50.0


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas[AREA] = square(*m.site('east base'), 450.0)
        tank, other = m.cnv_units
        lt, lo = getattr(m, 'cnv_labels', ('坦克在家', '步兵在家'))
        counted('CNV_TF_Tanks', lt, t, template=tank, area=AREA, player=s1)
        x, y = m.site('east base')
        if 'plant at' in m.facts or 'named teleport 1' in m.facts:   # aiar9 / 10: 3 counters (a 4th reads ?)
            if 'plant at' in m.facts:
                t.areas[PLANT_AREA] = square(*m.point('far plant'), 350.0)
                counted('CNV_TF_Plant', '坦克在新楼', t, template=tank, area=PLANT_AREA, player=s1)
                label, want = '坦克在新楼', m.facts['expect tanks at plant']
            else:
                t.areas[OUT_AREA] = square(x, y - 1200.0, 300.0)
                counted('CNV_TF_Out', '坦克在外', t, template=tank, area=OUT_AREA, player=s1)
                label, want = '坦克在外', m.facts['expect named out']
            counted('CNV_TF_Owned', '坦克拥有', t, template=tank, player=s1)
            at = m.facts['check at']
            t.expect += [(label, at, '==', want, at + 1)]
            t.bench = [('bench_watch', dict(seconds=at + 4 + LAG, every=1, sheet=False, lines=len(t.counters)))]
            return t
        if 'teleport at' in m.facts:          # aiar5-8: the late tanks no team holds, teleported (a 4th counter reads ?)
            t.areas[OUT_AREA] = square(x, y - 1200.0, 300.0)
            counted('CNV_TF_Out', '坦克在外', t, template=tank, area=OUT_AREA, player=s1)
            counted('CNV_TF_Owned', '坦克拥有', t, template=tank, player=s1)
            at = m.facts['check at']
            t.expect += [('坦克在外', at, '==', m.facts['expect tanks out'], at + 1)]
            t.bench = [('bench_watch', dict(seconds=at + 4 + LAG, every=1, sheet=False, lines=len(t.counters)))]
            return t
        counted('CNV_TF_Inf', lo, t, template=other, area=AREA, player=s1)
        if 'late tanks' in m.facts:           # aiar*: did the opener build them at all (owned, anywhere)
            counted('CNV_TF_Owned', '坦克拥有', t, template=tank, player=s1)
            counted('CNV_TF_Owned2', '另一种拥有', t, template=other, player=s1)
        at = m.facts.get('check at', AT)      # aiar*: later, after the AI has built its own tanks
        t.expect += [(lt, at, '==', m.facts['expect tanks home'], at + 1),
                     (lo, at, '==', m.facts['expect infantry home'], at + 1)]
        t.bench = [('bench_watch', dict(seconds=max(SECONDS, at + 10) + LAG, every=1, sheet=False,
                                        lines=len(t.counters)))]
        return t


    CHECKS = {k: {'a': a} for k in ('aitfany', 'aitfnone', 'aitfall', 'aitfki', 'aitfke', 'aitfmax', 'aitfoki', 'aitfokt',
                                     'aitfoke', 'aitfokn', 'aitfland', 'aitfamph', 'aitfwat', 'aitfosi', 'aitfosv', 'aitfosc',
                                     'aiar0', 'aiar1', 'aiar2', 'aiar3', 'aiar4', 'aiar5', 'aiar6', 'aiar7', 'aiar8', 'aiar9',
                                     'aiar10')}
    return dict(CHECKS=CHECKS)


def engine_aiteams():
    """Engine line D round 68: read the AI's teams (template name -> team -> member ids) off ra3ext's CNVTeams module, on
    the C line's aicr3 game (CreateUnits MinUnits 3: engine_aicreate). The mission (benches/ai/tactics/scenes.py#aiteams_bench) is
    aicreate_bench's aicr3 plus one object of the AI's own carrying the CNVTeams module. Every 15 frames the module logs
    the host owner's teams to the run folder's ra3ext.log; experimental/cnv/teamlog.py reads them by name:

      team_size(run, 'CNVStateTF', frame)

    The counters and expectations are engine_aicreate's (s41..: three Guardians out, four Peacekeepers home); the team
    reading is read off the log after the run, not asserted by the bench.
    """
    aicreate = engine_aicreate()["shared"].a

    CHECKS = {'aicr3t': {'a': aicreate}}
    return dict(CHECKS=CHECKS)


def engine_aitoggle():
    """Engine probe: when the AI's micro manager raises / lowers the Peacekeepers' riot shield (benches/ai/tactics/scenes.py#aitoggle_bench).

    s1's StaticDefense team is two Peacekeepers; a player Twinblade attacks Peacekeeper 1 from ATTACK_AT (20 s) and is
    deleted at STOP_AT (35 s). Shield up = ObjectStatus GENERIC_TOGGLE_STATE. Both Peacekeepers kept at full health.
    Checks: r (both builds) and c (aitogglemade: the control, the script presses Peacekeeper 2's toggle PRESS_AT frames
    after the attack starts, to show the status reads a raised shield).
    Counters (four lines), from the attack on (run to STOP_AT + 15 s):
      帧数   frames since the attack order (the order frame is +-1)
      盾1开  frames since Peacekeeper 1 was first seen shielded   -> raised at frame = 帧数 - 盾1开
      盾1关  frames since Peacekeeper 1 was seen unshielded after that -> lowered at frame = 帧数 - 盾1关
             (the stop is at frame (STOP_AT - ATTACK_AT) * 15 = 225)
      盾2    frames since Peacekeeper 2 (never targeted) was first seen shielded
      在家   aitogglehunt only, in 盾2's place: how many of s1's Peacekeepers stand within 150 of their spots (2 = the
             Hunt team never took them; it walks off with them)
    A shield seen before the attack makes 盾k > 帧数.
    The verdicts after 帧数 are the model's answer (RA3-EngineModel micro.py toggle, UpdateTime 0.5 s): 盾1 raised within
    the attack, lowered after the stop, 盾2 never -- a FAIL is the bench reading otherwise.

    读数
    Bench 2026-11-07 (Sonnet, one run each, no dropout):
      aitogglemade c PASS: 盾2 463 at 帧数 493 -> raised 30 frames after the order, the frame of the press: the status
        reads a raised shield.
      aitogglemade r / aitogglehand r FAIL: 盾1开 盾1关 盾2 all 0 through 帧数 426 / 495 -- the AI never raised the
        shield of the attacked Peacekeeper (made after the wake or handed over alike). With aimicmade (warriors made
        after the wake never charged) the silence is not the hand-over: INFERRED the StaticDefense team runs no micro,
        or a precondition (work/re l4_micro_powers.md 1) fails. Model: raises at the first round (strict xfail in
        RA3-EngineModel tests/test_ai_bench.py).
      aitogglehunt r FAIL (Sonnet, round 18): 盾1开 盾1关 盾2 all 0 through 帧数 493 -- a Targetless Hunt team never raised
        the shield either: not the StaticDefense tactic.
      aitogglehunt r again with 在家 (Sonnet, round 18): 在家 2 from s11 to s51 -- the Peacekeepers never left their spots:
        the Hunt team never took them (aistate aihunt: Peacekeepers s1's from the start left 4 s after the wake). So the
        units the script creates on s1's team after the wake are not recruited; the micro manager never had them.
      aitogglexfer r FAIL (Sonnet, round 18): 盾1开 盾1关 盾2 all 0 through 帧数 489 -- UNIT_AI_TRANSFER_ALL again right
        after the make did not help either (see engine_aimicro: next, the AI produces the units itself).
      aitogglebuilt r (Sonnet, round 19; counters 帧数 造出 盾 曾盾): first run (attack 30 s) the Allied barracks gave the
        second Peacekeeper only at ~s51, after the attack -- moved to attack 70 / stop 85. Rerun: 造出 2 from s21, the
        gunship's attack 70-85 s: 盾 / 曾盾 0 throughout; the control (named Peacekeeper made on s1's team 5 s after the
        stop, toggle pressed 1 s later): 盾 1, 曾盾 8 at s91 -- the by-player count reads a shield. NOT conclusive: 造出 stayed
        2 through 15 s of a Twinblade "attacking" them, so it most likely never shot at them (attack-move to the deleted
        barracks' spot; where the AI put them is not known). A fair try needs the gunship ordered at them (they are
        unnamed: a team hunt, or a player-area attack) -- the warriors' aimicbuilt reading is the firm one.
      aitogglebltf r (B, round 20, mod CampAITogBltFR; a Targetless Hunt team, s1's structures deleted once it owns two),
        three gunship placements, all NOT conclusive: (1) TEAM_HUNT at s70: 造出 2 throughout, never hit; (2) attack-move
        to the barracks spot the moment s1 owned two (s21): both dead by s41, 曾盾 0 -- but most likely before the Hunt
        team took them (the warriors were taken 10-20 s after being built); (3) TEAM_HUNT from the barracks spot 12 s
        after two owned: 造出 2 throughout, never hit. The control read each time (盾 1 at s91). Not followed further (the
        layer 4 closing line); engine_aimicro aimicbuiltf is the firm answer for AI-built units.
    """
    from parts import NOT, Script, Test, counted, square, status

    LAG = 4.0
    HOME, HOME_R = 'CNV AT Home Area', 150.0   # aitogglehunt: the square of half-side 150 round the two spots
    AFTER = 15.0
    SHIELD = 'GENERIC_TOGGLE_STATE'
    COMMAND = 'Command_ToggleRiotShieldSpecialPower'
    PRESS_AT = 30      # control c: frames after the attack order at which the script presses Peacekeeper 2's toggle


    def names(m, group):
        made = getattr(m, 'cnv_named', {})
        return [r.name for r in m.roles(group)] or [made[k] for k in sorted(made) if k.startswith(group + ' ')]


    def probe(m, press=False):
        t = Test()
        p1 = m.player('p1')
        attack, stop = m.facts['attack at'], m.facts['stop at']
        pks = names(m, 'peacekeeper')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        t.scripts.append(Script('Test - keep them up', [], [('UNIT_SET_HEALTH', n, 100.0) for n in pks], once=False))
        hunt = bool(m.facts.get('hunt'))
        t.counters += [('CNV_AT_Frames', '帧数'), ('CNV_AT_Up1', '盾1开'), ('CNV_AT_Down1', '盾1关')]
        if hunt:   # 盾2 gives way to 在家: did the Hunt team take the Peacekeepers (they walk off) or not (they stand)
            (x1, y1), (x2, y2) = m.point('peacekeeper 1 spot'), m.point('peacekeeper 2 spot')
            t.areas[HOME] = square((x1 + x2) / 2, (y1 + y2) / 2, HOME_R)
            counted('CNV_AT_Home', '在家', t, template=m.cnv_units[0], area=HOME, player=m.player('s1'))
        else:
            t.counters.append(('CNV_AT_Up2', '盾2'))
        t.scripts += [Script('Test - frames', [('TIMER_EXPIRED', 'CNV AT Attack')],
                             [('INCREMENT_COUNTER', 1, 'CNV_AT_Frames')], once=False)]
        for k, n in enumerate(pks if not hunt else pks[:1], 1):
            t.scripts += [
                Script(f'Test - up seen {k}', [('UNIT_HAS_OBJECT_STATUS', n, status(SHIELD))], [('SET_FLAG', f'Test Up {k}', 1)]),
                Script(f'Test - up count {k}', [('FLAG', f'Test Up {k}', 1)],
                       [('INCREMENT_COUNTER', 1, f'CNV_AT_Up{k}')], once=False)]
        t.scripts += [
            Script('Test - down seen 1', [('FLAG', 'Test Up 1', 1), ('UNIT_HAS_OBJECT_STATUS', pks[0], status(SHIELD), NOT)],
                   [('SET_FLAG', 'Test Down 1', 1)]),
            Script('Test - down count 1', [('FLAG', 'Test Down 1', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AT_Down1')],
                   once=False)]
        if press:
            t.scripts.append(Script('Test - press 2', [('COUNTER', 'CNV_AT_Frames', 2, PRESS_AT)],
                                    [('NAMED_USE_COMMANDBUTTON_ABILITY', pks[1], COMMAND)]))
        t.expect += [('帧数', attack + LAG, 'ever>=', 1)]
        if press:
            t.expect += [('盾2', attack + LAG, 'ever>=', 1)]
        else:
            t.expect += [('盾1开', attack + LAG, 'ever>=', 1, stop), ('盾1关', stop + LAG, 'ever>=', 1)]
            t.expect += [] if hunt else [('盾2', attack + LAG, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=stop + AFTER, every=10, sheet=False, lines=len(t.counters)))]
        return t


    CONTROL = 'UNIT - CNV AT Control'
    CTRL_AFTER = 5.0   # built: seconds after the stop at which the check makes a named Peacekeeper on s1's team


    def probe_built(m):
        """aitogglebuilt (round 19): the AI's own Peacekeepers are unnamed, so count by player. Counters from the attack:
          帧数  frames since the attack order
          造出  Peacekeepers s1 owns (the opener built them: >= 2 before the attack)
          盾    s1's objects with the shield up now (GENERIC_TOGGLE_STATE)
          曾盾  frames since s1 first had one up -> first raised at frame 帧数 - 曾盾 (> 帧数: before the attack)
        The model raises one within the attack and lowers it after the stop (盾 back to 0). Control: CTRL_AFTER after the
        stop the check makes a named Peacekeeper on s1's team at the control spot and presses its toggle one second later
        -- 盾 must read it."""
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        attack, stop = m.facts['attack at'], m.facts['stop at']
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
        t.counters.append(('CNV_AT_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [('TIMER_EXPIRED', 'CNV AT Attack')],
                                [('INCREMENT_COUNTER', 1, 'CNV_AT_Frames')], once=False))
        counted('CNV_AT_Owned', '造出', t, template=m.cnv_units[0], player=s1)
        counted('CNV_AT_Up', '盾', t, status=status(SHIELD), player=s1)
        t.counters.append(('CNV_AT_Ever', '曾盾'))
        t.scripts += [
            Script('Test - up seen any', [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', s1, 3, 1, status(SHIELD))],
                   [('SET_FLAG', 'Test Up Any', 1)]),
            Script('Test - up count any', [('FLAG', 'Test Up Any', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AT_Ever')],
                   once=False)]
        ctrl = int((stop - attack + CTRL_AFTER) * 15)
        t.scripts += [
            Script('Test - control make', [('COUNTER', 'CNV_AT_Frames', 2, ctrl)],
                   [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', CONTROL, m.cnv_units[0], m.team('s1'), m.mark('control spot'))]),
            Script('Test - control press', [('COUNTER', 'CNV_AT_Frames', 2, ctrl + 15)],
                   [('NAMED_USE_COMMANDBUTTON_ABILITY', CONTROL, COMMAND)])]
        t.expect += [('帧数', attack + LAG, 'ever>=', 1), ('造出', attack, 'ever>=', 2, stop),
                     ('曾盾', attack + LAG, 'ever>=', 1, stop), ('盾', stop + LAG, '==', 0, stop + CTRL_AFTER),
                     ('盾', stop + CTRL_AFTER + 2, 'ever>=', 1)]
        t.bench = [('bench_watch', dict(seconds=stop + CTRL_AFTER + AFTER, every=10, sheet=False,
                                        lines=len(t.counters)))]
        return t


    CHECKS = {'aitogglebuilt': {'r': probe_built}, 'aitogglebltf': {'r': probe_built},
              'aitogglehand': {'r': probe}, 'aitogglemade': {'r': probe, 'c': lambda m: probe(m, press=True)},
              'aitogglehunt': {'r': probe}, 'aitogglexfer': {'r': probe}}
    return dict(CHECKS=CHECKS)


def engine_aitransport():
    """Tactic UseTransports: does a SimpleAttack team with a transport put its infantry aboard before it goes?

    benches/ai/tactics/scenes.py#aitransport_bench: Niagara without bridges, four Peacekeepers and a Riptide of s1 on the east bank, the
    target plant on Goat Island. Three counters, once a second:
      车内步兵   s1's objects carrying ENCLOSED (only the Peacekeepers can be: aboard the Riptide)
      岛上步兵   s1's Peacekeepers inside Goat Island's box
      激流在岛   1 while the Riptide is inside Goat Island's box
    Prediction (b221 read rule): true -> they board (车内步兵 > 0), the Peacekeepers reach the island; false -> the
    Riptide crosses alone (激流在岛 1), 岛上步兵 stays 0.

    RESULTS (2026-11-16, run_queue, B round 221): aitrans0 PASS, aitrans1 FAIL -- both 0 0 0 from s1 to the end (s117 /
    s112); the minimap at s80 shows every s1 unit still at the east base: the team never left in either, so this pair
    does not tell the flag apart (the simulator: the same, nobody moves). Not registered. Suspects: the target heuristic
    or the team's start wants a ground way to the target (no target / no team), so no pair ever forms. Next: a home-box
    counter, and the target reachable by the Riptide but not by the infantry in some other way.
    RESULTS (2026-11-16, B round 222, the ra3ext host added, 4th counter 步兵在家): aitrans0 / aitrans1 again 0 0 0 4
    to the end (CampAITrans0A_mcp_1116_131624, CampAITrans1A_mcp_1116_131448). The logs: the state's target pick finds
    the island plant at f16 (the player's yard the other candidate, both ok); the SimpleAttack team is made at f17 with
    0 members, dropped and made again every ~90 frames to the end; every s1 unit stays in the default team -- nobody is
    recruited, it is not a team that does not move. aitransr (the Riptide alone): the same, 0 members
    (CampAITransRA_mcp_1116_132232) -- the Riptide itself is turned away, not blocked by unpairable infantry.
    aitransw0 / aitransw1 / aitransrw (the plant on the west bank's landing 'front' instead): the same in all three
    (..._1116_133119 / 132835 / 132645). aiteamfilter's aitfamph took Riptides at a land target on the east bank (with
    bridges, AllowedLocomotorTypes AMPHIBIOUS only). Not explained in two layouts: stopped (work/re handoff-b 222).
    RESULTS (2026-11-16, B round 223): aitransre (the Riptide alone, no bridges, the plant back at aiteamfilter's
    'east gate' on the east bank) PASS: 激流在岛 1 from s60 (CampAITransREA_mcp_1116_134740) -- the Riptide is taken and
    goes. So this map (no bridges, no library, LAND AMPHIBIOUS) does not turn it away; what does is the target being
    somewhere the east bank has no ground way to (the island, the west bank): the recruit turns the Riptide away there
    too. A passenger is paired only when it cannot reach the target itself, and such a unit is not recruited, so no
    layout of this bench forms a pair and UseTransports stays untold apart. Stopped, not registered (handoff-b 223).
    RESULTS (2026-11-21, B): the recruit tries a unit that cannot reach again or'd with a member that can carry it, and
    an AIR mask always passes (work/re b1121_transports.md): aitranst0 / aitranst1 put a Twinblade in for the Riptide
    (激流在岛 then counts the Twinblade). The flag tells: true -> all four board s24-27, carried off from s32; false ->
    the team takes all five (f153), nobody boards, the Peacekeepers drop out (f248), the Twinblade crosses alone (s49).
    Readings in benches/ai/tactics/readings.toml#engine_aitransport, both a mismatch (the model's recruit does not pair).
    """
    from parts import Script, Test, counted, square, status

    ISLAND = 'CNV Trans Island'     # B222 aitransw*: the target's box (the west bank's landing), not the island
    HOME = 'CNV Trans Home'
    X0, X1, Y0, Y1 = 2450.0, 2750.0, 2450.0, 3350.0      # niagara.GOAT
    AT, SECONDS = 75.0, 85.0


    def a(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        if m.facts.get('player shot'):          # E 11-21 aitranstp: the player's Twinblade at its own plant
            t.scripts.append(Script('Test - shoot', [], [('NAMED_FORCE_ATTACK_NAMED', 'UNIT - CNV Twinblade',
                                                           'UNIT - CNV AI Player Target')]))
        if m.facts['target on island']:
            t.areas[ISLAND] = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
        else:
            t.areas[ISLAND] = square(m.facts['target x'], m.facts['target y'], 350.0)   # 'front' / B223 'east gate'
        counted('CNV_TR_In', '车内步兵', t, status=status('ENCLOSED'), player=s1)
        if m.facts.get('air transport'):        # E 11-21: what the Twinblade does to the plant (four lines fit)
            counted('CNV_TR_Plant', '电厂血', t, health='UNIT - CNV AI Player Target')
        else:
            counted('CNV_TR_Isle', '岛上步兵', t, template='AlliedAntiInfantryInfantry', area=ISLAND, player=s1)
        counted('CNV_TR_Boat', '激流在岛', t, named='UNIT - CNV AI Riptide', area=ISLAND)
        t.areas[HOME] = square(*m.site('east base'), 450.0)          # B222: aiteamfilter's home box
        counted('CNV_TR_Home', '步兵在家', t, template='AlliedAntiInfantryInfantry', area=HOME, player=s1)
        if m.facts.get('air transport'):                              # B 11-21: what the bench read
            t.expect = [('车内步兵', 30, '==', 4 if m.facts['use transports'] else 0, 31)]
        elif not m.facts['ai infantry']:                                # aitransr: the Riptide alone
            t.expect = [('激流在岛', AT, '==', 1, AT + 1)]
        elif m.facts['use transports']:
            t.expect = [('岛上步兵', AT, '>=', 1, AT + 1)]
        else:
            t.expect = [('岛上步兵', AT, '==', 0, AT + 1), ('车内步兵', AT, '==', 0, AT + 1)]
        t.bench = [('bench_watch', dict(seconds=SECONDS, every=1, sheet=False, lines=3))]
        return t


    CHECKS = {name: {'a': a} for name in ('aitrans0', 'aitrans1', 'aitransr', 'aitransw0', 'aitransw1',
                                                  'aitransrw', 'aitransre', 'aitranst0', 'aitranst1', 'aitranstp')}
    return dict(CHECKS=CHECKS)


def engine_k2gate():
    """Read first departure and foe health; verify recruitment and aim in the teams log."""

    engine_aicombat_scene = engine_aicombat()["shared"]
    from parts import Script, counted


    def a(m):
        t = engine_aicombat_scene.a(m)
        fighter = m.role('candidate fighter').name
        foe = m.role('player foe').name
        timer = 'CNV K2 attack'
        t.scripts += [
            Script('Test - K2 attack timer', [], [('SET_MILLISECOND_TIMER', timer, m.facts['order at'])]),
            Script('Test - K2 aim', [('TIMER_EXPIRED', timer)], [('NAMED_ATTACK_NAMED', fighter, foe)]),
        ]
        # The archived teams log measures the actual join frame. Keep the first departure identity
        # on screen alongside the two position flags and foe health.
        t.counters.remove(('CNV_RC_Frame', '首离帧'))
        counted('CNV_K2_FoeHealth', '目标血量', t, health=foe)
        t.expect = [
            ('目标血量', 3, '==', 100, 24),
            ('首离身份', 1, 'ever==', 1 if m.facts['allow in combat'] else 2, 49),
        ]
        return t


    CHECKS = {name: {'a': a} for name in ('k2gate0', 'k2gate1')}
    return dict(CHECKS=CHECKS)


BENCHES = (
    engine_aialphaclose, engine_aialphahp, engine_aibasedef, engine_aicannot,
    engine_aicombat, engine_aicreate, engine_aicrush, engine_aidefense,
    engine_aidelay, engine_aidiff, engine_aidistance, engine_aidodge,
    engine_aiengineer, engine_aifallback, engine_aigarrison, engine_aihome,
    engine_aiignore, engine_aiignore_rule, engine_aikeep, engine_aimicro,
    engine_aineutralgarr, engine_aiorders, engine_aipassive_distance, engine_aipathcheck,
    engine_aipullback, engine_aipullpct, engine_aireactive, engine_airelease,
    engine_airetreat, engine_aisort, engine_aispecial, engine_aiswitch,
    engine_aitactical, engine_aiteamfields, engine_aiteamfilter, engine_aiteams,
    engine_aitoggle, engine_aitransport, engine_k2gate,
)
