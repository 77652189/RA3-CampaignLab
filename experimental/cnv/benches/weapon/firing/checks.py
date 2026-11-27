"""Weapon firing checks and inline scenes."""
from functools import cache
from types import SimpleNamespace


def engine_acquire():
    """Engine probe (R8): does a unit on its own go after an enemy out of its weapon's range -- idle, guarding,
    attack-moving (benches/weapon/firing/scenes.py#engine_acquire).

    An enemy (s1) Guardian-type tank (weapon 150, vision 200, shroud 500) is made at 1 s at S on the s1 crew 'Aq'; the
    player's named NO_ATTACK tank T stands d away (idle / guard: north of S; am: d beside the middle of the path S->E).
    Orders at 2 s: idle none; guard TEAM_GUARD the square of half-side 100 round S; am attack-move to E (600 east).
    Counters: 起点 (the attacker within 60 of S), 原地 (within 15 of S; idle / guard), 近敌 (within 200 of T),
    终点 (within 100 of E; am), 坦克血 (T's health). bench_watch 25 s, every 1 s.
    RESULTS (bench 2026-11-07; the s1 side has no reveal: it sees with its own vision 200):
      idle180   起点 1 原地 1 all along; 坦克血 100 -> 86 s2, -14 per 2 s, 3 from s14: it fired WITHOUT moving (within 15
                of S) at a tank 180 off, centre to centre -- the reach is more than the weapon's 150 (target / own
                radius counted?).
      idle200   起点 1; 原地 0 from s1 to s15 (it MOVED toward the tank: 近敌 1 all along), 原地 1 again from s16; 坦克血
                100 -> 86 s2, -14 per 2 s, 3 from s14 (it stops at 3: the same count as idle180).
      idle220   起点 1; 原地 0 s1-s15 (moved), 近敌 1 until s15 then 0 with 原地 1 from s16 (back at S, 220 off); 坦克血
                100 -> 86 s2, -14 per 2 s, 17 at s12, 3 from s13.  So at 220 it still acquires, walks in, fires and returns.
      idle240   起点 1, 原地 1, 近敌 0, 坦克血 100 all 26 s: no move, no shot.  Acquire reach: between 220 and 240
                (vision 200 + the tank's own radius?); idle180 fires in place, idle200 / 220 walk in first.
      idle260   起点 1, 坦克血 100 all 26 s: no move, no shot (beyond its vision 200).  Simulator: the same.
      guard260  (TEAM_GUARD the half-100 square round S) 起点 1, 坦克血 100: no move, no shot.  Simulator: the same.
      am260     walked straight to E (终点 1 from s7), 坦克血 100: no turn aside for a tank 260 beside the path.  Same.
      am400     the same as am260.  Simulator: the same.
      (idle400, guard400 not run: nothing is expected beyond 260.)
      Reading (both tanks a 20 x 12 BOX: bounding circle 23.3): the weapon reaches when the centre distance less both
      radii is within its range (Generals FROM_BOUNDINGSPHERE_2D: 196.6 here -- 180 in place, 200 a step in); an idle
      unit goes after an enemy within its VisionRange + the enemy's radius (223.3: 220 yes, 240 no), fires, and walks
      back to its spot; guarding / attack-moving at 260+ nothing. The simulator (sim.Sim.in_range / idle_chase, R8)
      holds all ten (tests/test_simbench.py 'R8'); its fire is steadier (no clips) and kills the tank (the bench's
      stays at 3: not explained), so it walks home at s18 against the bench's s16.
    STANCES (bench 2026-11-10, UNIT_SET_STANCE on the attacker at its birth; GUARD 0 is the default above):
      hold180   (HOLD_POSITION 2) 起点 1 原地 1 近敌 1 all along; 坦克血 100 -> 86 s2, -14 per 2 s, 3 from s14: as idle180.
      hold220   (HOLD_POSITION) 起点 1 原地 1 近敌 0 坦克血 100 all 27 s: where GUARD walks in, it never moves nor fires.
      agg220    (AGGRESSIVE 1) 原地 0 and 近敌 1 from s1 to s26; 坦克血 86 s2 ... 3 from s14: walks in, fires and STAYS
                (GUARD walks home at s16).
      agg240 / agg260  (AGGRESSIVE) 起点 1 原地 1 近敌 0 坦克血 100 all along: the same acquire reach as GUARD.
      The simulator (Body.stance in idle_chase): the same five (tests/test_simbench_c.py test_stance_*).
    """
    from parts import Script, Test, counted, square

    VARIANTS = ('idle180', 'idle260', 'idle400', 'guard260', 'guard400', 'am260', 'am400', 'idle200', 'idle220', 'idle240',
                'hold180', 'hold220', 'agg220', 'agg240', 'agg260', 'gst450', 'gsc450', 'gch450', 'grt400', 'grs400',
                'gri400', 'grj400', 'idi220', 'idm220', 'gsm450', 'gsn450', 'rfs180', 'rfz180')
    ATK, TANK = 'UNIT - CNV Aq Atk', 'UNIT - CNV Aq Tank'
    RUN = 25.0
    INF = ('gri', 'grj', 'idi', 'idm')  # a conscript (vision 200, AK 150, walks 50, cannot fire on the move)
    STANCE = {'hol': 2, 'agg': 1}   # UNIT_SET_STANCE at birth: HOLD_POSITION / AGGRESSIVE (GUARD 0 is the default)


    def frames(m):
        t = Test()
        v = VARIANTS[m.facts['variant']]
        p1 = m.player('p1')
        team = m.teams['Aq']
        sx, sy = m.point('s')
        t.areas['Test Start'] = square(sx, sy, 60.0)
        t.areas['Test Guard'] = square(sx, sy, 100.0)
        t.areas['Test End'] = square(*m.point('e'), 100.0)
        g = v[:2] in ('gs', 'gc')           # gst / gsc / gch: guard from birth, the tank in to N at 4 s, off to F at 14 s
        r = v[:2] == 'gr'                   # grt / grs: born at F, guard S from birth: the walk back passes T
        t.areas['Test Near'] = square(*m.point('n' if g else 't'), 200.0)
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                                     ('UNIT_CHANGE_OBJECT_STATUS', TANK, 'NO_ATTACK', 1),
                                                     ('SET_MILLISECOND_TIMER', 'Test Make', 1.0),
                                                     ('SET_MILLISECOND_TIMER', 'Test Go', 2.0)]))
        t.scripts.append(Script('Test - make', [('TIMER_EXPIRED', 'Test Make')],
                                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ATK, 'SovietAntiInfantryInfantry' if v[:3] in INF
                                  else 'AlliedAntiVehicleVehicleTech1',
                                  m.team('s1'), m.mark('f' if r else 's')), ('UNIT_SET_TEAM', ATK, team)]
                                + ([('UNIT_SET_STANCE', ATK, STANCE[v[:3]])] if v[:3] in STANCE else [])
                                + (m.order('guard', [ATK], 'Test Guard', 's1', crew='Aq') if g or r else [])))
        go = ('TIMER_EXPIRED', 'Test Go')
        if g or r:
            t.areas['Test Far'] = square(*m.point('f'), 180.0)
            counted('CNV_Aq_F', '远', t, named=ATK, area='Test Far')
        if g:
            t.scripts += [Script('Test - in', [], [('SET_MILLISECOND_TIMER', 'Test In', 4.0),
                                                   ('SET_MILLISECOND_TIMER', 'Test Off', 14.0)]),
                          Script('Test - tank in', [('TIMER_EXPIRED', 'Test In')],
                                 m.order('move', [TANK], m.mark('n'), crew='AqT')),
                          Script('Test - tank off', [('TIMER_EXPIRED', 'Test Off')],
                                 m.order('move', [TANK], m.mark('f'), crew='AqT'))]
        elif v.startswith('guard'):
            t.scripts.append(Script('Test - order', [go], m.order('guard', [ATK], 'Test Guard', 's1', crew='Aq')))
        elif v.startswith('am'):
            t.scripts.append(Script('Test - order', [go], m.order('attack_move', [ATK], m.mark('e'), 's1', crew='Aq')))
        t.areas['Test Still'] = square(sx, sy, 15.0)
        if not g:                           # four counter lines at most: g counts 远 instead, r 远 and not 原地
            counted('CNV_Aq_S', '起点', t, named=ATK, area='Test Start')
        if v.startswith('rf'):              # rfs / rfz: the helper's spot and the attacker's health instead
            t.areas['Test Help'] = square(*m.point('h'), 15.0)
            counted('CNV_Aq_P', '援原地', t, named='UNIT - CNV Aq Help', area='Test Help')
            counted('CNV_Aq_A', '敌血', t, health=ATK)
        elif not v.startswith('am') and not r:
            counted('CNV_Aq_Q', '原地', t, named=ATK, area='Test Still')
        if not v.startswith('rf'):
            counted('CNV_Aq_N', '近敌', t, named=ATK, area='Test Near')
        if v.startswith('am'):
            counted('CNV_Aq_E', '终点', t, named=ATK, area='Test End')
        counted('CNV_Aq_H', '坦克血', t, health=TANK)
        t.bench = [('bench_watch', dict(seconds=32.0 if g or r else RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {f'acquire_{v}': {'frames': frames} for v in VARIANTS}
    return dict(CHECKS=CHECKS)


def engine_bezier_e():
    """E168: one V4 rocket, retail Bezier module versus module removal.

    Prediction before bench: at 450 range the enabled rocket lands for 500 damage
    on a 10000 HP Hammer (95%); the module-removal control cannot fly to its
    victim (100%). Both targets start at 100%. The weapon has no preattack,
    duration or scatter, reloads in 1s, and is disabled four frames after the
    order so only one rocket launches. The projectile itself is retail except
    for its identity and, in the off lane, removal of BezierProjectile.
    Sample HP at frame 240, not a video-clock flight-time estimate. Curved flight,
    homing, launch geometry, collision and exact impact frame remain gaps.
    """
    import os
    import re

    from maps import probe_range
    from parts import Mission, Script, Test
    missile = engine_missile()["shared"]
    SAGE = missile.SAGE
    V4_ROCKET = missile.V4_ROCKET
    target = missile.target
    from benches.weapon.target_effects.checks import engine_shot
    shot = engine_shot()["shared"]
    DAMAGE = shot.DAMAGE
    _nuggets = shot._nuggets
    shot_v4 = shot.shot_v4


    def launcher(tag):
        ident = 'CNVE168' + tag
        rocket, warhead = ident + 'Rocket', ident + 'Warhead'
        with open(os.path.join(SAGE, 'Soviet', 'Props', V4_ROCKET + '.xml'), encoding='utf-8') as f:
            xml = f.read()
        xml, count = re.subn(r'\s*<GameObject\s+inheritFrom="' + V4_ROCKET + r'".*?</GameObject>', '', xml, flags=re.S)
        assert count == 1
        xml = xml.replace(V4_ROCKET, rocket)
        if tag == 'Off':
            xml, count = re.subn(r'<BezierProjectile\b[^>]*/>', '', xml, flags=re.S)
            assert count == 1
        wh = (f'<WeaponTemplate id="{warhead}" RadiusDamageAffects="ENEMIES" '
              'RequiredAntiMask="ANTI_GROUND ANTI_STRUCTURE ANTI_WATER">' +
              _nuggets(DAMAGE.format(d=500, r=40, extra='')) + '</WeaponTemplate>')
        return shot_v4(ident, _nuggets(f'<ProjectileNugget WarheadTemplate="{warhead}" '
                                     f'ProjectileTemplate="{rocket}" />'), speed=200,
                       files={rocket + '.xml': xml}, extra=wh, reload=1,
                       what='single V4 rocket with retail Bezier module or module removal')


    def mission():
        m = Mission(name='CampBezierE', map=probe_range,
                    units=[launcher('On'), launcher('Off'), target()])
        for tag, site in [('On', 'base gun'), ('Off', 'high gun')]:
            m.put('CNVE168' + tag, site, side='p1', angle=1.5708,
                  role=tag + 'gun', name='E168 ' + tag + ' gun')
            m.put('CNV_MslTarget', site, 0, 450, side='s1', angle=4.7124,
                  role=tag + 'target', name='E168 ' + tag + ' target')
        return m


    def check(m):
        t = Test()
        t.counters = [('E168Frame', '帧'), ('E168Base', '初始满血'),
                      ('E168On', '有模块血量'), ('E168Off', '删模块血量')]
        t.scripts = [Script('Test - frame', [('COUNTER', 'E168Frame', 0, 240)],
                            [('INCREMENT_COUNTER', 1, 'E168Frame')], once=False)]
        start, fire, stop = [('MAP_REVEAL_ALL_PERM', m.player('p1'))], [], []
        baseline = []
        snapshot = []
        for tag, bit in [('On', 1), ('Off', 2)]:
            gun, victim = m.role(tag + 'gun').name, m.role(tag + 'target').name
            start += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in (gun, victim)]
            fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, victim)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1)]
            baseline.append(Script('Test - baseline ' + tag,
                                   [('COUNTER', 'E168Frame', 2, 60), ('UNIT_HEALTH', victim, 2, 100)],
                                   [('INCREMENT_COUNTER', bit, 'E168Base')]))
            snapshot.append(('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, 'E168' + tag))
        t.scripts += [Script('Test - start', [], start)] + baseline + [
            Script('Test - fire', [('COUNTER', 'E168Frame', 2, 90)], fire),
            Script('Test - stop', [('COUNTER', 'E168Frame', 2, 94)], stop),
            Script('Test - snapshot', [('COUNTER', 'E168Frame', 2, 240)], snapshot)]
        # Run a ended at f216. Run b reached f240 (240/3/95/100), but late in
        # video time. Judge the frozen script-frame snapshot, not a video deadline.
        # Original time-window FAIL results are retained in work/re/e168_bezier.md.
        t.expect = [('帧', 0, 'ever==', 240), ('初始满血', 0, 'ever==', 3),
                    ('有模块血量', 0, 'ever==', 95), ('删模块血量', 0, 'ever==', 100)]
        t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
        return t


    MISSION = {'engine_bezier_e': mission}
    CHECKS = {'engine_bezier_e': {'a': check}}
    CONTROL_ARMS = {'engine_bezier_e': ('On', 'Off')}
    return dict(MISSION=MISSION, CHECKS=CHECKS, CONTROL_ARMS=CONTROL_ARMS)


def engine_charge_e():
    """E213: ChargeWeaponUpdate -- retail's one use, the Wave-Force tower JapanBaseDefenseAdvanced (ChargeTime 5 s,
    OverChargeTime 2 s, OverChargePercent 40 %, not while IS_FIRING_WEAPON / IS_RELOADING_WEAPON; its beam: PreAttackDelay
    3 s, ClipSize 1, ClipReload 0.2 s, LineDamage 350, range 350).

    Two clones for p1, On the retail XML, Off without the module; two SovietPowerPlant feed them (POWERED, -75 each;
    placed, so no StructureUnpackUpdate). Each holds fire (NO_ATTACK) until GO (16 s: charged and over-charged whatever
    the power-up takes), then is told to attack an s1 SovietPowerPlantAdvanced (4000, holding fire) 300 north.
    Prediction, one of: the charge stands for the PreAttackDelay (On's first loss ~0 frames after GO, Off's ~45), or it
    scales the first shot's damage (On 1.4 x Off's loss), or neither (presentation, the same).
    Variants (11-24, the partial charge): b GO 60 (4 s idle: short of ChargeTime), c GO 90 (6 s: charged, short of the
    over-charge). Prediction (a charge either is or is not, so is the over-charge): b as Off (48 frames, 89 %), c On's
    frames at Off's damage (89 %); a pre-attack cut by the part charged would read b ~12 frames, an over-charge in
    proportion c 86 % (1.2 x 437.5).
    Counters: frame (stops at END = GO + 150), On / Off = the target's health % x 1000 at its first loss + the frames from
    GO to it, End = On's target health % x 1000 + Off's at END.
    """
    import re
    from pathlib import Path

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, status

    HOST, TAG, TARGET = 'JapanBaseDefenseAdvanced', 'ChargeWeaponUpdate', 'SovietPowerPlantAdvanced'
    GO, LONG = 240, 150


    def mission(scan=True):
        m = Mission(name='CampChargeE' if scan else 'CampChargeN', map=probe_range, units=[])
        source = (Path(labpaths.SDK3) / 'SageXML/Japan/Structures' / (HOST + '.xml')).read_text(encoding='utf-8-sig')
        if not scan:    # engine_charge_n: no idle scan, the turret stays on the target's bearing (a/b's frames over?)
            source, n = re.subn(r'MaxIdleScanAngle="[^"]*"', 'MaxIdleScanAngle="0.0"', source)
            assert n == 1, n
        for k in (1, 2):
            m.put('SovietPowerPlant', f'power {k}', 0.0, 0.0, role=f'pp{k}', name=f'E213 pp{k}')
        for arm, dx in [('On', 0.0), ('Off', 700.0)]:
            ident = 'CNVE213' + arm
            xml = source.replace(f'id="{HOST}"', f'id="{ident}"', 1)
            if arm == 'Off':
                xml, n = re.subn(rf'\s*<{TAG}\b.*?</{TAG}>', '', xml, flags=re.S)
                assert n == 1, n
            m.units.append(Unit(ident, xml))
            m.put(ident, 'base gun', dx, 0.0, role=arm, name='E213 ' + arm, angle=1.570796)
            m.put(TARGET, 'base gun', dx, 300.0, side='s1', role=arm + ' target', name='E213 ' + arm + ' target',
                  angle=3.141593)
        return m


    def check(m, go=GO):
        end = go + LONG
        t = Test()
        t.counters = [('E213Frame', '完成帧'), ('E213On', '原版'), ('E213Off', '删模块'), ('E213End', '终血')]
        t.scripts = [Script('Test - clock', [('COUNTER', 'E213Frame', 0, end)],
                            [('INCREMENT_COUNTER', 1, 'E213Frame')], once=False),
                     Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
        for arm in ('On', 'Off'):
            shooter, target = m.role(arm).name, m.role(arm + ' target').name
            wait, hp = 'E213W' + arm, 'E213H' + arm
            t.scripts += [
                Script('Test - quiet ' + arm, [], [
                    ('UNIT_CHANGE_OBJECT_STATUS', shooter, status('NO_ATTACK'), 1),
                    ('UNIT_CHANGE_OBJECT_STATUS', target, status('NO_ATTACK'), 1)]),
                Script('Test - go ' + arm, [('COUNTER', 'E213Frame', 2, go)], [
                    ('UNIT_CHANGE_OBJECT_STATUS', shooter, status('NO_ATTACK'), 0),
                    ('NAMED_ATTACK_NAMED', shooter, target)]),
                Script('Test - wait ' + arm, [('COUNTER', 'E213Frame', 3, go), ('COUNTER', 'E213Frame', 0, end),
                                              ('UNIT_HEALTH', target, 3, 100)],
                       [('INCREMENT_COUNTER', 1, wait)], once=False),
                Script('Test - first ' + arm, [('COUNTER', 'E213Frame', 3, go), ('UNIT_HEALTH', target, 0, 100)], [
                    ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, 'E213' + arm),
                    ('COUNTER_MATH_VALUE', 'E213' + arm, 2, 1000),
                    ('COUNTER_MATH_COUNTER', 'E213' + arm, 0, wait)]),
                Script('Test - end ' + arm, [('COUNTER', 'E213Frame', 2, end)], [
                    ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, hp),
                    ('COUNTER_MATH_COUNTER', 'E213End', 0, hp)])]
            if arm == 'On':     # On's share x 1000 before Off's is added (scripts run in order; no arm named here)
                t.scripts.append(Script('Test - end shift', [('COUNTER', 'E213Frame', 2, end)],
                                        [('COUNTER_MATH_VALUE', 'E213End', 2, 1000)]))
        t.expect = [('完成帧', 0, 'ever==', end), ('原版', 0, 'ever>=', 1000), ('删模块', 0, 'ever>=', 1000)]
        t.bench = [('bench_camera', dict(x=1150, y=550, look=False)),
                   ('bench_watch', dict(seconds=end // 15 + 25, every=1, sheet=False, lines=4))]
        return t


    _GOS = {'a': check, 'b': lambda m: check(m, 60), 'c': lambda m: check(m, 90), 'd': lambda m: check(m, 75)}
    MISSION = {'engine_charge_e': mission, 'engine_charge_n': lambda: mission(scan=False)}
    CHECKS = {'engine_charge_e': _GOS, 'engine_charge_n': _GOS}
    CONTROL_ARMS = {'engine_charge_e': ('On', 'Off'), 'engine_charge_n': ('On', 'Off')}
    return dict(MISSION=MISSION, CHECKS=CHECKS, CONTROL_ARMS=CONTROL_ARMS)


def engine_circular():
    """E143: minimal CircularDamageUpdate consumer, land with no ONLY_ON_WATER flag.

    Data prediction: Lifetime controls expansion, SweepWeapon supplies damage. Three
    stationary Hammers at 50/100/150 from the carrier count frames to first damage;
    the aimed Hammer at 450 receives only a 200 MAGIC shot marker. Checks a/b/c/d:
    normal, remove activation, remove module, hold FiringDuration for Lifetime. A395 e / f (normal / no activation):
    the rows 50 / 100 / 150 from the AIMED Hammer on the shooter's side -- the ring centres on the weapon's point,
    not the shooter (a / b / c / d had the rows outside it). This does not measure
    retail water eligibility, moving centres, death, repeat activation or FX.
    """
    from maps import probe_range
    from parts import Mission, Script, Test
    from benches.weapon.target_effects.checks import engine_shot
    shot = engine_shot()["shared"]
    shot_v4 = shot.shot_v4
    _nuggets = shot._nuggets
    missile = engine_missile()["shared"]
    target = missile.target
    TARGET_ID = missile.TARGET_ID
    _sub1 = missile._sub1

    ORDER, RUN = 8.0, 15.0
    LABELS = ('近', '中', '远', '瞄')


    def mission():
        return Mission(name='CampCircular', map=probe_range, units=[target()], ext=False)


    def probe(m, activate=True, module=True, life=1.0, hold=False, around=False):
        hit = ('<WeaponTemplate id="CNV_CircleHit"><Nuggets>'
               '<DamageNugget Damage="500" DamageType="MAGIC" DeathType="NORMAL"/>'
               '</Nuggets></WeaponTemplate>')
        nuggets = ['<DamageNugget Damage="200" DamageType="MAGIC" DeathType="NORMAL"/>']
        if activate:
            nuggets.append(f'<ActivateCircularDamageNugget Lifetime="{life:g}s"/>')
        u = shot_v4('CNV_Circle', _nuggets(*nuggets), extra=hit, reload=6.0)
        if hold:
            u.xml = _sub1(u.xml, '<FiringDuration\n\t\t\tMinSeconds="0s"\n\t\t\tMaxSeconds="0s"',
                          '<FiringDuration MinSeconds="1s" MaxSeconds="1s"')
        if module:
            u.xml = _sub1(u.xml, '<Behaviors>', (
                '<Behaviors>\n'
                '            <CircularDamageUpdate id="ModuleTag_Circle" MaxRadius="175" ArcDistance="50"\n'
                '                SweepWeapon="CNV_CircleHit">\n'
                '                <ObjectFilter Rule="ANY" Relationship="ENEMIES" Include="VEHICLE"/>\n'
                '            </CircularDamageUpdate>'
            ))
        u.link.append('WeaponTemplate:CNV_CircleHit')
        m.units.append(u)
        shooter = 'UNIT - Circle Source'
        m.put(u.id, 'base gun', side='p1', role='circle source', name=shooter)
        names = [f'UNIT - Circle Target {k}' for k in range(4)]
        for k, distance in enumerate((400.0, 350.0, 300.0, 450.0) if around else (50.0, 100.0, 150.0, 450.0)):
            m.put(TARGET_ID, 'base gun', 0.0, distance, side='s1', role=f'circle target {k}', name=names[k])
        t = Test()
        t.scripts.append(Script('Test - Circle setup', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
                                + [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in [shooter] + names]
                                + [('SET_MILLISECOND_TIMER', 'Circle Order', ORDER)]))
        t.scripts.append(Script('Test - Circle order', [('TIMER_EXPIRED', 'Circle Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', shooter, 'NO_ATTACK', 0),
                                 ('NAMED_ATTACK_NAMED', shooter, names[-1]), ('SET_FLAG', 'Circle Ordered', 1)]))
        for k, (name, label) in enumerate(zip(names, LABELS)):
            counter = f'CNV_Circle_{k}'
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - Circle count {k}', [('FLAG', 'Circle Ordered', 1),
                                                        ('UNIT_HEALTH', name, 2, 100)],
                                    [('INCREMENT_COUNTER', 1, counter)], once=False))
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
        return t


    MISSION = {'engine_circular': mission}
    CHECKS = {'engine_circular': {'a': probe, 'b': lambda m: probe(m, activate=False),
                                 'c': lambda m: probe(m, module=False), 'd': lambda m: probe(m, hold=True),
                                 'e': lambda m: probe(m, around=True),
                                 'f': lambda m: probe(m, activate=False, around=True)}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


@cache
def engine_clip():
    """Engine unit test: the clip's rhythm (ADR 0019 layer 3; docs/engine/weapons.md; engine line C round 4) -- what comes
    between one shot and the next once the first has gone: PreAttackDelay, FiringDuration, ClipReloadTime, ClipSize and
    ReAcquireDetailType. engine_fire read the FIRST shot; the simulator's clip clock (Sim.shot_clock, round 2) needs the
    rest: the coil (pre-attack 2.5 s + firing 0.5 s + reload 0.1 s = 3.1 s on paper) shoots on the bench about every
    4.15 s -- a second a shot the data does not say.

    Each shooter is retail's V4 with its rocket weapon swapped for a copy that deals ONE instant 100 (1 % of the 10 000-
    health Hammer, engine_missile's target) per shot, no scatter, WeaponSpeed 999999; only the timers, ClipSize and
    ReAcquireDetailType differ (VARIANTS). One variant a check, on the 'base' lane (the other variants are deleted at the
    start, as in engine_fire); ordered at ORDER (every clip loaded), so the first reading is the order -> first hit, then
    the frames between hit a and hit b (as engine_scatter's span: health in [100 - b + 1, 100 - a] %).

    Counters (four lines): 首发 = frames from the order to the first hit; then the SPANS of the variant. The reading is
    the frame count the script saw, one more than the frame the damage landed (docs/engine/weapons.md 1).

    Bench 11-09 (round 4, work/bench_results/engine_clip__coil.json): `coil` -- first hit 40 frames after the order
    (2.5 s -> 38, + the 2 of engine_fire's late), then hits 1-2 = 48, 2-3 = 48, 3-6 = 144 (3 x 48): one shot every 48
    frames = ceil(2.5 s x 15) 38 + ceil(0.5 s) 8 + ceil(0.1 s) 2. So the coil's weapon alone is 3.2 s a shot, NOT the
    ~4.15 s the powerdef bench shows: the missing ~1 s is not in the clip rhythm. powerdef: a Tech1 tank (480 hp, TESLA
    100 %) needs 2 shots of 450 = 96 frames; the bench kills one per ~125, so ~29 frames per KILL (retarget / acquire
    after the kill), first loss 111 = ~25 acquire + 86. Next probe: a kill chain (several 480-hp tanks, a shooter that
    kills in one shot, kill -> next hit frames, auto-acquire vs ordered). The other seven variants (bare, clip3, pre, fire,
    coilpc, clip3p, clip3c) were built but not run (queue stopped at the 15万 handoff): run_queue.py engine_clip:<name>.
    """
    import os
    import re

    from maps import probe_range
    from parts import Mission, Script, Test, Unit
    missile = engine_missile()["shared"]
    FAR = missile.FAR
    SAGE = missile.SAGE
    TARGET_ID = missile.TARGET_ID
    V4 = missile.V4
    V4_WEAPON = missile.V4_WEAPON
    _sub1 = missile._sub1
    target = missile.target

    ORDER = 6.0
    HIT = 100.0                    # a hit = 1 % of the target's 10 000
    LOST_MAX = 40

    # id suffix: (pre-attack s, firing s, reload s, clip, ReAcquireDetailType, spans (hit a, hit b), run seconds, label)
    VARIANTS = {
        'coil':   (2.5, 0.5, 0.1, 1, 'PRE_FIRE', ((1, 2), (2, 3), (3, 6)), 60, '线圈同时序'),
        'coilpc': (2.5, 0.5, 0.1, 1, 'PER_CLIP', ((1, 2), (2, 3), (3, 6)), 60, '线圈同时序+PER_CLIP'),
        'pre':    (2.5, 0.0, 0.1, 1, 'PRE_FIRE', ((1, 2), (2, 3), (3, 6)), 45, '只有预瞄2.5'),
        'fire':   (0.0, 0.5, 0.1, 1, 'PRE_FIRE', ((1, 2), (2, 3), (3, 6)), 30, '只有持续0.5'),
        'bare':   (0.0, 0.0, 0.1, 1, 'PRE_FIRE', ((1, 2), (2, 3), (3, 6)), 25, '只有装填0.1'),
        'clip3':  (0.0, 0.3, 2.0, 3, 'PRE_FIRE', ((1, 2), (2, 3), (3, 4)), 45, '三发夹'),
        'clip3p': (0.5, 0.3, 2.0, 3, 'PRE_FIRE', ((1, 2), (2, 3), (3, 4)), 45, '三发夹+预瞄0.5'),
        'clip3c': (0.0, 0.3, 2.0, 3, 'PER_CLIP', ((1, 2), (2, 3), (3, 4)), 45, '三发夹+PER_CLIP'),
    }
    INSTANT = ('<Nuggets>\n\t\t\t<DamageNugget Damage="%g" DamageType="EXPLOSIVE" DeathType="EXPLODED" Radius="0" />\n'
               '\t\t</Nuggets>' % HIT)


    def _uid(k):
        return 'CNV_Clip' + k.title()


    def clip_v4(k, hit=HIT, spec=None, uid=None):
        """Retail's V4 under CNV_Clip<K>, its rocket weapon swapped for a one-DamageNugget instant copy with the
        variant's timers (ADR 0016 G5: the probe builds it)."""
        pre, firing, reload, clip, reacq, _, _, label = spec or VARIANTS[k]
        id = uid or _uid(k)
        wid = id + 'Weapon'
        x = open(os.path.join(SAGE, 'Soviet', 'Units', V4 + '.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{V4}"', f'id="{id}"')
        x = re.sub(rf'EditorName="{V4}"', f'EditorName="{id}"', x)
        x = _sub1(x, f'Template="{V4_WEAPON}"', f'Template="{wid}"')
        w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
        s = re.search(rf'\t*<WeaponTemplate\s+id="{V4_WEAPON}".*?</WeaponTemplate>\n', w, re.S).group(0)
        s = _sub1(s, f'id="{V4_WEAPON}"', f'id="{wid}"')
        s = _sub1(s, 'inheritFrom="ScatterableWeapon"', '')
        s = _sub1(s, 'WeaponSpeed="200"', 'WeaponSpeed="999999"')
        s = _sub1(s, 'ClipSize="1"', f'ClipSize="{clip}"')
        s = _sub1(s, 'ReAcquireDetailType="PRE_FIRE"', f'ReAcquireDetailType="{reacq}"')
        s, n = re.subn(r'<Nuggets>.*?</Nuggets>', INSTANT.replace('Damage="%g"' % HIT, 'Damage="%g"' % hit), s, flags=re.S)
        assert n == 1, n
        s, n = re.subn(r'\s*<ScatterRadiusVsType\s+Radius="0\.1">.*?</ScatterRadiusVsType>', '', s, flags=re.S)
        assert n == 1, n
        s = _sub1(s, 'MinSeconds=".5s"\n\t\t  MaxSeconds=".5s"', f'MinSeconds="{pre:g}s"\n\t\t  MaxSeconds="{pre:g}s"')
        s = _sub1(s, '<FiringDuration\n\t\t\tMinSeconds="1.0s"\n\t\t\tMaxSeconds="1.0s"',
                  f'<FiringDuration\n\t\t\tMinSeconds="{firing:g}s"\n\t\t\tMaxSeconds="{firing:g}s"')
        s, n = re.subn(r'(<ClipReloadTime\s+MinSeconds=")4\.5s("\s+MaxSeconds=")5\.5s"', rf'\g<1>{reload:g}s\g<2>{reload:g}s"', s)
        assert n == 1, n
        x = _sub1(x, '</AssetDeclaration>', s + '</AssetDeclaration>')
        return Unit(id, x, link=[f'WeaponTemplate:{wid}'], names=dict(unit=id, weapon=wid),
                    what=f'弹夹节奏 V4（探针）：瞬发 {hit:g} 伤害、预瞄 {pre:g} 秒、开火持续 {firing:g} 秒、装填 {reload:g} 秒、'
                         f'弹夹 {clip} 发、{reacq}，其余同原版',
                    params=dict(pre=pre, firing=firing, reload=reload, clip=clip, reacq=reacq))


    def mission():
        m = Mission(name='CampClip', map=probe_range, units=[clip_v4(k) for k in VARIANTS] + [target()], facts={})
        for k in VARIANTS:
            m.put(_uid(k), 'base gun', side='p1', role=f'clip {k}', name=f'UNIT - CNV Clip {k.title()}')
        m.put(TARGET_ID, 'base gun', 0, FAR, side='s1', role='clip target', name='UNIT - CNV Clip Target')
        return m


    def clip_test(m, k):
        pre, firing, reload, clip, reacq, spans, run, label = VARIANTS[k]
        t = Test()
        shooter, tg = m.role(f'clip {k}').name, m.role('clip target').name
        idle = [m.role(f'clip {i}').name for i in VARIANTS if i != k]
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('NAMED_DELETE', x) for x in idle]
        start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in (shooter, tg)]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', shooter, 'NO_ATTACK', 0),
                                 ('NAMED_ATTACK_NAMED', shooter, tg), ('SET_FLAG', 'Test Ordered', 1)]))
        t.counters.append(('CNV_Clip_First', '首发'))
        t.scripts.append(Script('Test - CNV_Clip_First', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Clip_First')], once=False))
        for i, (a, b) in enumerate(spans):
            c = f'CNV_Clip_S{i}'
            t.counters.append((c, f'{a}-{b}'))
            t.scripts.append(Script(f'Test - {c}', [('UNIT_HEALTH', tg, 0, 100 - a + 1), ('UNIT_HEALTH', tg, 3, 100 - b + 1)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
        a, b = spans[-1]
        t.expect = [(f'{a}-{b}', 0, 'ever>=', (b - a) * 2, run - 1)]
        t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_clip': mission}
    CHECKS = {'engine_clip': {k: (lambda m, k=k: clip_test(m, k)) for k in VARIANTS}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        ORDER=ORDER, SAGE=SAGE, clip_v4=clip_v4))


def engine_cosmetic_e():
    """E211: two modules the data says only draw -- each host cloned twice, the retail XML and the module taken out.

    AimWeapon (AimLow/HighThreshold, AimNear/FarDistance; retail: the Javelin and the Flak Trooper) sets AIM_HIGH,
    and in the SDK only Draws ConditionsYes read AIM_HIGH. Build engine_aimweapon_e: a Javelin fires on a hovering
    Twinblade 100 east (its _Aircraft launcher, range 300), On with the module, Off without.
    Build engine_aimgnd_e: the same on an Apocalypse 100 east (its ground launcher, range 175): never AIM_HIGH, so
    the one-frame hold seen on the Twinblade should be gone if the hold is the aim pitch (gate 12).

    ConvergingLaserState (a LaserState: four beams closing on the target; retail: the Athena and the Hammer's leeched
    Athena gun) has SweepWeapon / SweepFXList, unset in both retail uses; the Athena's damage is its OCL's cannon
    effect (benches/weapon/firing/checks.py#engine_ocl). Build engine_convlaser_e: an Athena fires on a Soviet advanced power plant 300
    north, Off without its four ConvergingLaserState (one module kind, four copies: the arm contract takes one
    element, so this build is not in CONTROL_ARMS).

    Prediction: each pair the same -- the frames from the order to the first loss and the health at the freeze. The
    target holds fire; the shooter is held until GO. Counters: frame (stops at END), On / Off = health % x 1000 +
    frames waiting for the first loss, gate bits: the arm's model condition (AIM_HIGH / FIRING_OR_PREATTACK_A) ever
    on 1 / 2, both targets alive at END 4 / 8. AimWeapon: 1 4 8 = 13 (Off never AIM_HIGH); the laser's trigger is the
    weapon's own condition, both arms: 15.
    """
    import re
    from pathlib import Path

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, status

    GO = 30
    CASES = {   # build: (mission, SDK file, host, module tag, copies, target, target dx dy, condition, END)
        'engine_aimweapon_e': ('CampAimWpnE', 'Allied/Units/AlliedAntiVehicleInfantry.xml', 'AlliedAntiVehicleInfantry',
                               'AimWeapon', 1, 'SovietAntiGroundAircraft', (100.0, 0.0), 'AIM_HIGH', GO + 90),
        'engine_aimgnd_e': ('CampAimGndE', 'Allied/Units/AlliedAntiVehicleInfantry.xml', 'AlliedAntiVehicleInfantry',
                            'AimWeapon', 1, 'SovietAntiVehicleVehicleTech3', (100.0, 0.0), 'AIM_HIGH', GO + 90),
        'engine_convlaser_e': ('CampConvLsrE', 'Allied/Units/AlliedAntiStructureVehicle.xml', 'AlliedAntiStructureVehicle',
                               'ConvergingLaserState', 4, 'SovietPowerPlantAdvanced', (0.0, 300.0),
                               'FIRING_OR_PREATTACK_A', GO + 200),
    }


    def mission(build, swap=False, late=False):
        name, path, host, tag, copies, target, (tx, ty), _, _ = CASES[build]
        m = Mission(name=name[:-1] + ('S' if swap else 'O' if late else 'E'), map=probe_range, units=[])
        source = (Path(labpaths.SDK3) / 'SageXML' / path).read_text(encoding='utf-8-sig')
        for arm, dx in [('On', 700.0 * swap), ('Off', 700.0 * (not swap))][::-1 if late else 1]:
            ident = 'CNVE211' + arm
            xml = source.replace(f'id="{host}"', f'id="{ident}"', 1)
            for key, value in re.findall(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"\s*/>', xml):
                xml = xml.replace('$' + key, value)
            xml = re.sub(r'<Defines>.*?</Defines>', '', xml, flags=re.S)
            if arm == 'Off':
                xml, n = re.subn(rf'\s*<{tag}\b.*?(?:/>|</{tag}>)', '', xml, flags=re.S)
                assert n == copies, (tag, n)
            m.units.append(Unit(ident, xml))
            m.put(ident, 'base gun', dx, 0.0, role=arm, name='E211 ' + arm, angle=1.570796)
            m.put(target, 'base gun', dx + tx, ty, side='s1', role=arm + ' target', name='E211 ' + arm + ' target',
                  angle=3.141593)
        return m


    def check(m, build):
        *_, condition, end = CASES[build]
        t = Test()
        t.counters = [('E211Frame', '完成帧'), ('E211On', '原版'), ('E211Off', '删模块'), ('E211Gate', '前置位')]
        t.scripts = [Script('Test - clock', [('COUNTER', 'E211Frame', 0, end)],
                            [('INCREMENT_COUNTER', 1, 'E211Frame')], once=False),
                     Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
        for arm, weight in [('On', 1), ('Off', 2)]:
            shooter, target = m.role(arm).name, m.role(arm + ' target').name
            wait = 'E211W' + arm        # the arm tag after a capital: contract.arm_drift pairs the two arms by it
            t.scripts += [
                Script('Test - quiet ' + arm, [], [
                    ('UNIT_CHANGE_OBJECT_STATUS', shooter, status('NO_ATTACK'), 1),
                    ('UNIT_CHANGE_OBJECT_STATUS', target, status('NO_ATTACK'), 1)]),
                Script('Test - go ' + arm, [('COUNTER', 'E211Frame', 2, GO)], [
                    ('UNIT_CHANGE_OBJECT_STATUS', shooter, status('NO_ATTACK'), 0),
                    ('NAMED_ATTACK_NAMED', shooter, target)]),
                Script('Test - wait ' + arm, [('COUNTER', 'E211Frame', 3, GO), ('COUNTER', 'E211Frame', 0, end),
                                              ('UNIT_HEALTH', target, 3, 100)],
                       [('INCREMENT_COUNTER', 1, wait)], once=False),
                Script('Test - condition ' + arm, [('COUNTER', 'E211Frame', 3, GO), ('COUNTER', 'E211Frame', 0, end),
                                                   ('UNIT_HAS_MODELCONDITION', shooter, condition)],
                       [('INCREMENT_COUNTER', weight, 'E211Gate')]),
                Script('Test - end ' + arm, [('COUNTER', 'E211Frame', 2, end)], [
                    ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, 'E211' + arm),
                    ('COUNTER_MATH_VALUE', 'E211' + arm, 2, 1000),
                    ('COUNTER_MATH_COUNTER', 'E211' + arm, 0, wait)]),
                Script('Test - alive ' + arm, [('COUNTER', 'E211Frame', 2, end), ('NAMED_NOT_DESTROYED', target)],
                       [('INCREMENT_COUNTER', 4 * weight, 'E211Gate')])]
        t.expect = [('完成帧', 0, 'ever==', end), ('前置位', 0, 'ever==', 15 if condition != 'AIM_HIGH' else 12 if 'gnd' in build else 13)]
        t.bench = [('bench_camera', dict(x=1150, y=550, look=False)),
                   ('bench_watch', dict(seconds=end // 15 + 25, every=1, sheet=False, lines=4))]
        return t


    VARIANTS = {k: {} for k in CASES} | {b[:-1] + 's': {'swap': True} for b in CASES} | \
        {b[:-1] + 'o': {'late': True} for b in CASES}   # s: the arms trade places; o: the control's objects made first
    MISSION = {v: (lambda v=v: mission(v[:-1] + 'e', **VARIANTS[v])) for v in VARIANTS}
    CHECKS = {v: {'a': lambda m, v=v: check(m, v[:-1] + 'e')} for v in VARIANTS}
    CONTROL_ARMS = {v: ('On', 'Off') for v in VARIANTS if v.startswith('engine_aim')}
    return dict(MISSION=MISSION, CHECKS=CHECKS, CONTROL_ARMS=CONTROL_ARMS)


def engine_discharge_e():
    """E177: retail Waveforce premature discharge versus single-module removal.

    Both attack at script frame 45, press the retail discharge button at 75.
    The weapon has a four-second preattack delay. Predict that the original
    hits before the removal control; both must eventually hit their targets.
    First-hit counters and cast-event bits freeze at 210. No damage/clock
    rule is fitted from this prediction. See work/re/e177_discharge.md.
    MEASURED: on freezes 210/76/0/1, off 210/0/109/0. The original
    off cast==1 prediction below failed and is retained. Sim hits at 47
    in both arms; two strict xfails preserve this dispatch/preattack gap.
    """
    import re
    from pathlib import Path

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, status


    def mission(enabled=True):
        m = Mission(facts={'enabled': enabled}, name='CampDisch' + ('OnE' if enabled else 'OffE'), map=probe_range, units=[])
        source = (Path(labpaths.SDK3) / 'SageXML/Japan/Units/JapanAntiStructureVehicle.xml').read_text(encoding='utf-8-sig')
        for tag, lane in [('On' if enabled else 'Off', 'base')]:
            ident = 'CNVE177' + tag
            xml = source.replace('id="JapanAntiStructureVehicle"', f'id="{ident}"', 1)
            if tag == 'Off':
                xml, n = re.subn(r'<PrematureDischargeSpecialPower\b[^>]*/>', '', xml)
                assert n == 1
            # Publishing the button permits observation; it does not prove acceptance.
            m.units.append(Unit(ident, xml, abilities={
                'fire': 'Command_JASV_FireKiCannon',
                'power': 'SpecialPower_JASV_FireKiCannon'}))
            m.put(ident, lane + ' gun', role=tag, name='E177 ' + tag, angle=1.570796)
            m.put('AlliedPowerPlant', lane + ' gun', 0, 350, side='s1',
                  role=tag + ' target', name='E177 ' + tag + ' target')
        return m


    def check(m):
        tags = ['On' if m.facts['enabled'] else 'Off']
        t = Test()
        t.counters = [('E177Frame', '完成帧'), ('E177On', '原版首伤'),
                      ('E177Off', '对照首伤'), ('E177Cast', '施放观测')]
        t.scripts = [
            Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
            Script('Test - clock', [('COUNTER', 'E177Frame', 0, 210)],
                   [('INCREMENT_COUNTER', 1, 'E177Frame')], once=False),
            Script('Test - discharge', [('COUNTER', 'E177Frame', 2, 75)], [
                ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(tag).name, 'Command_JASV_FireKiCannon')
                for tag in tags]),
            Script('Test - cast seen', [('PLAYER_TRIGGERED_SPECIAL_POWER', m.player('p1'),
                                       'SpecialPower_JASV_FireKiCannon')],
                   [('INCREMENT_COUNTER', 1, 'E177Cast')])]
        for tag in tags:
            gun, target = m.role(tag).name, m.role(tag + ' target').name
            t.scripts += [
                Script('Test - quiet ' + tag, [], [
                    ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 1)]),
                Script('Test - attack ' + tag, [('COUNTER', 'E177Frame', 2, 45)], [
                    ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 0),
                    ('NAMED_ATTACK_NAMED', gun, target)]),
                Script('Test - first hit ' + tag, [('COUNTER', 'E177Frame', 0, 210),
                    ('UNIT_HEALTH', target, 0, 100)], [
                    ('SET_COUNTER_TO_COUNTER', 'E177' + tag, 'E177Frame'),
                    ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 1)])]
        t.expect = [('完成帧', 0, 'ever==', 210), ('原版首伤' if m.facts['enabled'] else '对照首伤', 0, 'ever>=', 1), ('施放观测', 0, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=55, every=1, sheet=False, lines=4))]
        return t


    MISSION = {'dischargeon_e': mission, 'dischargeoff_e': lambda: mission(False)}
    CHECKS = {name: {'a': check} for name in MISSION}
    CONTROLS = {'dischargeoff_e': 'dischargeon_e'}
    return dict(MISSION=MISSION, CHECKS=CHECKS, CONTROLS=CONTROLS)


def engine_dot():
    """PREDICT before bench:2/1090/2/1080 (two first-hit frames + alive/HP).
    Retail DOTNugget (PlayerPowerIrradiateTargetWeapon) uses Damage, DamageInterval,
    DamageDuration, RADIATION, RemoveIfHealed. Keep the damage type and use
    400 damage every0.2s=3frames, durations1s=15frames and2s=30frames.
    Targets1000HP BaseTankArmor RADIATION5% ->20HP (2%) per tick.
    GUESSED initial tick at impact, expiry excluded: offsets0,3,...<15/30
    give5/10 ticks, HP90/80. OrderF0, object impactF1, first script seesF2.
    No separate DamageNugget: first-hit counters isolate DOT's initial phase.
    Clock scripts run after the order and count while health100%, so direct
    impact reads2. Final counters=1000*alive+HP%; four displayed lines.
    If initial tick is delayed3frames first reads5; an inclusive end adds one
    tick. These alternatives are distinguished without per-number fitting.
    No healing, repeat hits, stacking, upgrades, splash, death or OCL asserted.
    Before implementation simulator ignored DOT:151/1100/151/1100 at16s.
    MEASURED first round:2/1088/2/1078 (FAIL of initial exclusive-end prediction).
    Both first frames match; expiry INCLUSIVE gives offsets0,3,...,15/30,
    6/11 ticks ->HP88/78. Same formula for both durations, no fitted constants.
    Revised PREDICT before confirmation bench:2/1088/2/1078.
    MEASURED confirmation PASS2/1088/2/1078; `1 run: PASS 1`
    (work/logs/w6_dot_confirm_bench.log, 2026-11-10). Simulator replays both.
    Empty clip loads1s; order6s; NO_ATTACK6+4/15; float timers.
    """
    import re
    from maps import probe_range
    from parts import Mission,Script,Test
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun
    missile = engine_missile()["shared"]
    target = missile.target
    TARGET_ID = missile.TARGET_ID
    CASES=(('base',1),('high',2))

    def mission():
        m=Mission(name='CampDot',map=probe_range,units=[target(health=1000)],facts={})
        for lane,seconds in CASES:
            u=gun('CNV_Dot'+lane.title(),0)
            nugget=(f'<DOTNugget Damage="400" DamageInterval="0.2s" DamageDuration="{seconds}s" '
                    'DamageType="RADIATION" DamageFXType="RADIATION" DeathType="IRRADIATED" RemoveIfHealed="true"/>')
            u.xml,n=re.subn(r'<DamageNugget\b[^>]*/>',nugget,u.xml);assert n==1
            m.units.append(u)
            m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='DOT '+lane+' gun')
            m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name='DOT '+lane+' target')
        return m

    def check(m):
        t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','DOT Fire',6.0),('SET_MILLISECOND_TIMER','DOT Stop',6+4/15)]
        fire=[];stop=[]
        for lane,seconds in CASES:
            g='DOT '+lane+' gun';v='DOT '+lane+' target';c='CNV_DOT_'+lane
            start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
            fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
            t.counters += [(c+'First',str(seconds)+'s first'),(c+'HP',str(seconds)+'s aliveHP')]
            t.scripts += [Script('Test - clock '+lane,[('FLAG','DOT Ordered',1),('UNIT_HEALTH',v,2,100)],
                                 [('INCREMENT_COUNTER',1,c+'First')],once=False),
                          Script('Test - hp '+lane,[],[('SET_COUNTER',c+'HP',0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c+'HP')],once=False),
                          Script('Test - alive '+lane,[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,c+'HP')],once=False)]
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','DOT Fire')],fire+[('SET_FLAG','DOT Ordered',1)]))
        t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','DOT Stop')],stop))
        t.expect=[(label,14,'==',value,16) for (_,label),value in zip(t.counters,(2,1088,2,1078))]
        t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
        return t
    MISSION={'engine_dot':mission}
    CHECKS={'engine_dot':{'a':check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_emp():
    """New round PREDICT16051/31066/61096,hit1 after first-hit clock fix.
    Scripts run before object updates. OrderF0 -> object hitF1 -> observedF2;
    move6.5s rounds toF8; EMP1/2/4s endsF16/31/61, first movement there,
    observed departureF17/32/62. Origin script omits orderF0 ->raw16/31/61.
    Arrival raw counter omits move trigger ->43 moving frames +8/23/53 held
    frames =51/66/96. Remaining1 after first-hit correction was ceil(a-b)
    versus ceil(a)-ceil(b); move must independently round0.5s*15 up to8.
    Sim now predicts the full packed tuple exactly, before rerunning bench.
    Prior experiment, before the clock correction:
    Bench FAIL raw16051/31066/61096, hit1. Scripts precede fire/move,
    so add1 to raw arrival, departure and hit for trigger-relative observation:
    arrival52/67/97, departure17/32/62, hit2. Sim hit raw2 vs bench1.
    At that stage EMP was shelved without an implementation; reopened above.
    Identical EMP clone at1/2/4s, damage1.5 UNRESISTABLE on150HP infantry.
    Initially empty clip loads1s; fire6s, NO_ATTACK6+4/15; move6.5s.
    Four displayed lines: each lane encodes1000*departure_frame + arrival_frames;
    departure_frame is the first script frame outside a1-unit origin square,
    from fire order. This observes first post-EMP movement, not an EMP status bit.
    Fourth line records first damage observation from order (independent clock).
    PREDICT: damage2, departure18/33/63 (damage2+duration15/30/60+one
    script-observation frame), arrival54/69/99; packed18054/33069/63099.
    Departure prediction is GUESSED: object update vs script phase is unverified.
    Prior isolated2/4s arrival readings67/97 were2 below predictions69/99.
    If the residual changes with duration STOP; if constant inspect departure
    and hit timing, do not infer onset merely from damage or fit a2-frame fix.
    """
    from maps import probe_range
    from parts import Mission,Script,Test,square
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun

    RUN=16.0
    CASES=(('base',1),('high',2),('order',4))

    def mission():
        return Mission(name='CampEmp',map=probe_range,units=[],facts={})

    def check(m):
        t=Test(); start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),
            ('SET_MILLISECOND_TIMER','EMP Fire',6.0),
            ('SET_MILLISECOND_TIMER','EMP Stop',6.0+4/15),
            ('SET_MILLISECOND_TIMER','EMP Move',6.5)]
        fire=[]; stop=[]; move=[]
        for lane,seconds in CASES:
            u=gun('CNV_Emp'+lane.title(),1.5,
                  f'<ParalyzeNugget DurationSeconds="{seconds}s" ParalyzeType="EMP"/>')
            u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
            m.units.append(u)
            shooter='EMP '+lane+' gun'; victim='EMP '+lane+' man'
            m.put(u.id,lane+' gun',side='p1',angle=1.5708,name=shooter)
            m.put('AlliedAntiInfantryInfantry',lane+' gun',0,450,side='s1',name=victim)
            start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (shooter,victim)]
            fire += [('UNIT_CHANGE_OBJECT_STATUS',shooter,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',shooter,victim)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS',shooter,'NO_ATTACK',1)]
            m.waypoint(lane+' goal','EMP Goal '+lane,lane+' gun',0,675)
            x,y=m.point(lane+' goal'); gate='EMP Gate '+lane; origin='EMP Origin '+lane
            t.areas[gate]=square(x,y-40,40)
            t.areas[origin]=square(x,y-225,1)
            c='CNV_EMP_'+lane; dep='EMP Departed '+lane; moving='EMP Moving '+lane
            t.counters.append((c,str(seconds)+'s packed'))
            move += [('MOVE_NAMED_UNIT_TO',victim,m.mark(lane+' goal')),('SET_FLAG',moving,1)]
            # Count origin frames directly in the thousands; no dependency on HUD sampling.
            t.scripts += [
                Script('Test - origin '+lane,[('FLAG','EMP Ordered',1),('FLAG',dep,0),('NAMED_INSIDE_AREA',victim,origin)], [('INCREMENT_COUNTER',1000,c)],once=False),
                Script('Test - depart '+lane,[('FLAG','EMP Ordered',1),('NAMED_OUTSIDE_AREA',victim,origin)], [('SET_FLAG',dep,1)]),
                Script('Test - arrive '+lane,[('NAMED_INSIDE_AREA',victim,gate)],[('NAMED_STOP',victim),('SET_FLAG',moving,0)]),
                Script('Test - frames '+lane,[('FLAG',moving,1)],[('INCREMENT_COUNTER',1,c)],once=False)]
        t.counters.append(('CNV_EMP_Hit','hit frame'))
        t.scripts += [Script('Test - hit frame',[('FLAG','EMP Ordered',1),('UNIT_HEALTH','EMP high man',2,100)],
                             [('INCREMENT_COUNTER',1,'CNV_EMP_Hit')],once=False)]
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts += [Script('Test - fire',[('TIMER_EXPIRED','EMP Fire')],fire+[('SET_FLAG','EMP Ordered',1)]),
                      Script('Test - stop',[('TIMER_EXPIRED','EMP Stop')],stop),
                      Script('Test - move',[('TIMER_EXPIRED','EMP Move')],move)]
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(16051,31066,61096,1))]
        t.bench=[('bench_watch',dict(seconds=RUN,every=.5,sheet=False,lines=4))]
        return t
    MISSION={'engine_emp':mission}
    CHECKS={'engine_emp':{'phase':check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_empfire():
    """PREDICT before bench: 901090/901100/901080/901090.

    Two 1000HP V4 clones carry the same finite one-shot 100UNRES weapon.
    At6s each receives a 100UNRES marker; only high also receives EMP4s.
    At6.5s each is explicitly ordered to fire north at a passive 1000HP target;
    NO_ATTACK closes that window after4/15s. Before10s the control should have
    hit once (target90%) and the EMP gun never (target100%). At11s a second
    identical order/window, after EMP expiry, should leave targets80%/90%.
    Capture early at9s, late at14s; each packed row = gunHP%*10000 +
    1000*gunAlive + targetHP%. Marker90% and survival positively verify the
    EMP carrier was hit and remained alive. TargetHP is cleared before reading.
    The marker and first attack are separated by0.5s, so neither same-frame
    ordering nor the exact expiry frame is inferred. Movement, EMP stacking,
    filters, other paralysis types and weapon cooldown during EMP untested.

    First bench read891089/891100/891078/891089: EMP behavior separated, but
    the fixture had not neutralized retail side/rear damage multipliers105/110.
    Correct the fixture's two recipient armors to NoArmor (100% in all directions), leaving
    damage, geometry and timers unchanged; do not fit EMP rules to those HPs.
    MEASURED 2026-11-10, neutral fixture: PASS901090/901100/901080/901090
    (work/logs/c_empfire_noarmor_bench.log). The first corrected-armor build
    could not inherit a retail armor instance; NoArmor builds without that
    extra asset. Only the two firing windows, not exact expiry or ongoing
    reload behavior, are benched. Simulator before fix let both lanes fire;
    after fix it replays all four readings.
    """
    import re

    from maps import probe_range
    from parts import Mission, Script, Test
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun
    target = engine_missile()["shared"].target


    def neutral_direction_armor(u):
        """Only UNRESISTABLE is used here; NoArmor removes direction as a confound."""
        parent = re.search(r'<ArmorSet\s+Armor="([^"]+)"', u.xml).group(1)
        u.xml = u.xml.replace('Armor="'+parent+'"', 'Armor="NoArmor"')


    def mission():
        m = Mission(name='CampEmpFire', map=probe_range, units=[], facts={})
        for lane in ('base', 'high'):
            extra = '<ParalyzeNugget DurationSeconds="4s" ParalyzeType="EMP"/>' if lane == 'high' else ''
            marker = gun('CNV_EmpFireMark' + lane.title(), 100, extra)
            shooter = gun('CNV_EmpFireGun' + lane.title(), 100)
            for u in (marker, shooter):
                u.xml = u.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
            shooter.xml, n = re.subn(r'MaxHealth="[^"]+"', 'MaxHealth="1000"', shooter.xml)
            assert n == 1, n
            dummy = target('CNV_EmpFireTarget' + lane.title(), health=1000)
            neutral_direction_armor(shooter)
            neutral_direction_armor(dummy)
            m.units.extend((marker, shooter, dummy))
            m.put(marker.id, lane+' gun', -100, 0, side='p1', angle=1.5708, name='EmpFire '+lane+' marker')
            m.put(shooter.id, lane+' gun', 0, 450, side='s1', angle=1.5708, name='EmpFire '+lane+' gun')
            m.put(dummy.id, lane+' gun', 0, 900, side='p1', name='EmpFire '+lane+' target')
        return m


    def check(m):
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane in ('base', 'high'):
            marker, shooter, dummy = ['EmpFire '+lane+' '+k for k in ('marker', 'gun', 'target')]
            start.extend(('UNIT_CHANGE_OBJECT_STATUS', v, 'NO_ATTACK', 1) for v in (marker, shooter, dummy))
            for tag, at, who, victim in (('mark', 6., marker, shooter), ('early', 6.5, shooter, dummy),
                                         ('late', 11., shooter, dummy)):
                timer = 'EmpFire '+lane+' '+tag
                start.extend((('SET_MILLISECOND_TIMER', timer, at),
                              ('SET_MILLISECOND_TIMER', timer+' stop', at+4/15)))
                t.scripts.extend((Script('Test - '+timer, [('TIMER_EXPIRED', timer)],
                                         [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', who, victim)]),
                                  Script('Test - '+timer+' stop', [('TIMER_EXPIRED', timer+' stop')],
                                         [('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1)])))
        for phase, at in (('early', 9.), ('late', 14.)):
            timer = 'EmpFire read '+phase
            start.append(('SET_MILLISECOND_TIMER', timer, at))
            for lane in ('base', 'high'):
                c = 'CNV_EmpFire_'+phase+'_'+lane
                shooter, dummy = 'EmpFire '+lane+' gun', 'EmpFire '+lane+' target'
                t.counters.append((c, phase+' '+lane))
                t.scripts.extend((Script('Test - read '+c, [('TIMER_EXPIRED', timer)],
                                         [('SET_COUNTER', c, 0), ('SET_COUNTER', c+'HP', 0),
                                          ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', shooter, c),
                                          ('COUNTER_MATH_VALUE', c, 2, 10000),
                                          ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', dummy, c+'HP'),
                                          ('COUNTER_MATH_COUNTER', c, 0, c+'HP')]),
                                  Script('Test - alive '+c, [('TIMER_EXPIRED', timer), ('NAMED_NOT_DESTROYED', shooter)],
                                         [('INCREMENT_COUNTER', 1000, c)])))
        t.scripts.insert(0, Script('Test - start', [], start))
        t.expect = [(label, 15, '==', value, 16) for (_, label), value in
                    zip(t.counters, (901090, 901100, 901080, 901090))]
        t.bench = [('bench_watch', dict(seconds=16., every=.5, sheet=False, lines=4))]
        return t


    MISSION = {'engine_empfire': mission}
    CHECKS = {'engine_empfire': {'a': check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_fire():
    """Engine unit test: the firing state machine (ADR 0019 layer 3, batch "firing"; docs/engine/weapons.md) -- what fills
    the 35-40 frames between NAMED_ATTACK_NAMED and the V4's launch (docs/engine/missile.md 3: the model has only the
    0.5 s pre-attack, 8 frames).

    The flight is taken out: each shooter is retail's V4 with its rocket weapon swapped for a copy whose nuggets are one
    instant DamageNugget (500 EXPLOSIVE, radius 0, WeaponSpeed 999999: hits the frame it fires) and no scatter (an instant
    shot that scatters lands beside the victim). The copies differ only in PreAttackDelay and FiringDuration:

      I     retail's timers: pre-attack 0.5 s, firing 1.0 s, reload 4.5-5.5 s
      I0P   pre-attack 0
      I0F   firing 0
      I00   both 0

    On the range probe map (maps/probe_range.py, flat) four lanes; shooters face north, their target (engine_missile's
    10 000-health Hammer, held with NO_ATTACK) FAR straight north. The shooters are held with NO_ATTACK and at ORDER
    freed and told to attack. Counters as in engine_missile: frames from the order to the first hit, + 1000 per percent
    lost (a hit is 5 %), so later hits show in the second-by-second watch. Two checks swap the copies between the early
    lanes (base, high) and the late ones (removed, switch: ~8 frames later every run of engine_missile, not read why);
    the four all<copy> checks put one copy on every lane.

    Bench 11-05 (round 25), frames from the order to the first hit (docs/engine/weapons.md 1):

      copy \\ lane  base  high  removed  switch
      I            35    46    38       36
      I0P          33    23    30       31
      I0F          45    38    40       41
      I00          32    23    35       38

    Deterministic: timers run again gave the same four; the cells of timers / timers2 equal those of all*. Without a
    pre-attack 23-38, with one 35-46: ~23 frames + a 0-15 frame spread that goes with the unit, not the lane (the
    "late lanes" of engine_missile are this) + the pre-attack; FiringDuration is not before the launch. Hits after the
    first: I00 every ~5 s, I every ~6.5 s.

    Round 26 (read in the program, docs/engine/weapons.md 1): a weapon without InstantLoadClipOnActivate reloads its
    first clip from the frame the unit is made, a random whole ClipReloadTime (V4 4.5-5.5 s = 68-83 frames); the
    order at 45 frames gives 23-38, the pre-attack adds 8. The spread is each unit's draw.

    Bench 11-05 (round 30): shift (timers' units, the order at 4 s) 20 / 8 / 25 / 23 -- each cell exactly 15 less
    than timers, so the reload runs from the unit's creation; late (6 s, clips loaded) 10 / 2 / 10 / 2 -- without a
    pre-attack the constant 2, with it 8 more. The model is 1 frame late on the reload side (24-39) and 1 frame early
    on the order side (1): two opposite frames, not placed.
    """
    import os
    import re

    from maps import probe_range
    from parts import Mission, Script, Test, Unit
    missile = engine_missile()["shared"]
    FAR = missile.FAR
    LOST_MAX = missile.LOST_MAX
    ORDER = missile.ORDER
    SAGE = missile.SAGE
    TARGET_ID = missile.TARGET_ID
    V4 = missile.V4
    V4_WEAPON = missile.V4_WEAPON
    _sub1 = missile._sub1
    target = missile.target

    RUN = 24.0
    COPIES = {   # id: (pre-attack s, firing s, label)
        'CNV_FireI': (0.5, 1.0, '原时'),
        'CNV_FireI0P': (0.0, 1.0, '无预瞄'),
        'CNV_FireI0F': (0.5, 0.0, '无持续'),
        'CNV_FireI00': (0.0, 0.0, '都无'),
    }
    INSTANT = ('<Nuggets>\n\t\t\t<DamageNugget Damage="500.0" DamageType="EXPLOSIVE" DeathType="EXPLODED" Radius="0" />\n'
               '\t\t</Nuggets>')


    def fire_v4(id, pre, firing):
        """Retail's V4 under `id`, its rocket weapon swapped for `id`Weapon: one instant DamageNugget, no scatter,
        PreAttackDelay `pre` s, FiringDuration `firing` s; nothing else differs (ADR 0016 G5: the probe builds it)."""
        wid = id + 'Weapon'
        x = open(os.path.join(SAGE, 'Soviet', 'Units', V4 + '.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{V4}"', f'id="{id}"')
        x = re.sub(rf'EditorName="{V4}"', f'EditorName="{id}"', x)
        x = _sub1(x, f'Template="{V4_WEAPON}"', f'Template="{wid}"')
        w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
        s = re.search(rf'\t*<WeaponTemplate\s+id="{V4_WEAPON}".*?</WeaponTemplate>\n', w, re.S).group(0)
        s = _sub1(s, f'id="{V4_WEAPON}"', f'id="{wid}"')
        s = _sub1(s, 'inheritFrom="ScatterableWeapon"', '')
        s = _sub1(s, 'WeaponSpeed="200"', 'WeaponSpeed="999999"')
        s, k = re.subn(r'<Nuggets>.*?</Nuggets>', INSTANT, s, flags=re.S)
        assert k == 1, k
        s, k = re.subn(r'\s*<ScatterRadiusVsType\s+Radius="0\.1">.*?</ScatterRadiusVsType>', '', s, flags=re.S)
        assert k == 1, k
        s = _sub1(s, 'MinSeconds=".5s"\n\t\t  MaxSeconds=".5s"', f'MinSeconds="{pre:g}s"\n\t\t  MaxSeconds="{pre:g}s"')
        s = _sub1(s, '<FiringDuration\n\t\t\tMinSeconds="1.0s"\n\t\t\tMaxSeconds="1.0s"',
                  f'<FiringDuration\n\t\t\tMinSeconds="{firing:g}s"\n\t\t\tMaxSeconds="{firing:g}s"')
        x = _sub1(x, '</AssetDeclaration>', s + '</AssetDeclaration>')
        return Unit(id, x, link=[f'WeaponTemplate:{wid}'], names=dict(unit=id, weapon=wid),
                    what=f'瞬发 V4（探针）：预瞄 {pre:g} 秒、开火持续 {firing:g} 秒，伤害当场结算，无散布，其余同原版',
                    params=dict(pre=pre, firing=firing))


    LANES = {   # check: {lane: shooter}
        'timers': {'base': 'CNV_FireI', 'high': 'CNV_FireI0P', 'removed': 'CNV_FireI0F', 'switch': 'CNV_FireI00'},
        'timers2': {'base': 'CNV_FireI0F', 'high': 'CNV_FireI00', 'removed': 'CNV_FireI', 'switch': 'CNV_FireI0P'},
    }
    ALL_LANES = ('base', 'high', 'removed', 'switch')
    LANES.update({f'all{i[8:]}':{lane: i for lane in ALL_LANES} for i in COPIES})   # one copy on every lane
    ORDERS = {'shift': ('timers', 4.0), 'late': ('timers', 6.0)}   # timers' units, the order 15 / 45 frames later


    def mission():
        m = Mission(name='CampFire', map=probe_range,
                    units=[fire_v4(i, p, f) for i, (p, f, _) in COPIES.items()] + [target()], facts={})
        for lane in ALL_LANES:
            L, site = lane.title(), f'{lane} gun'
            for i in COPIES:        # every copy on every lane, the check removes the ones it does not use
                m.put(i, site, side='p1', role=f'{lane} {i}', name=f'UNIT - CNV Fire {L} {i[8:]}')
            m.put(TARGET_ID, site, 0, FAR, side='s1', role=f'{lane} target', name=f'UNIT - CNV Fire {L} Target')
        return m


    def fire_test(m, lanes, order=ORDER):
        t = Test()

        def n(part):
            return m.role(part).name

        targets = [n(f'{lane} target') for lane in lanes]
        shooters = [n(f'{lane} {lanes[lane]}') for lane in lanes]
        idle = [n(f'{lane} {i}') for lane in lanes for i in COPIES if i != lanes[lane]]
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('NAMED_DELETE', x) for x in idle]
        start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in targets + shooters]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', order)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s in shooters]
                                + [('NAMED_ATTACK_NAMED', s, tg) for s, tg in zip(shooters, targets)]
                                + [('SET_FLAG', 'Test Ordered', 1)]))
        for lane, tg in zip(lanes, targets):
            c = f'CNV_Fire_{lane.title()}'
            t.counters.append((c, f'{lane}{COPIES[lanes[lane]][2]}'))
            t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
            t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                 [('INCREMENT_COUNTER', 1000, c)]) for j in range(1, LOST_MAX + 1)]
        first = next(iter(lanes))
        t.expect = [(f'{first}{COPIES[lanes[first]][2]}', 0, 'ever>=', 1000, RUN - 2)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=6))]
        return t


    MISSION = {'engine_fire': mission}
    CHECKS = {'engine_fire': {k: (lambda m, k=k: fire_test(m, LANES[k])) for k in LANES}}
    CHECKS['engine_fire'].update({k: (lambda m, k=k: fire_test(m, LANES[ORDERS[k][0]], ORDERS[k][1])) for k in ORDERS})
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_fireobjects():
    """Wide bench FAIL1099/1100/1100/1100: broad child did not fire.
    Authorized stock-recipe followup ret: retain wide child and all positions/
    NO_ATTACK, match ProductionKickbacks CIRCLE and broad ANY kind filter,
    no relationship/status restriction. PREDICT0/0/1100/0 if dispatch occurs.
    This does not invent a required marker or alter status without data.
    Coordinator retry: wide changes only child to10000UNRESISTABLE/Radius10,
    no object/status filters, all relations and anti masks, range/speed999999,
    unlimited clip (same as original schema default). PREDICT0/0/1100/1100 if
    dispatch works; unchanged1099/1100/1100/1100 falsifies that branch.
    Parent Radius100/VEHICLE/ENEMIES, positions and NO_ATTACK remain identical.
    Original failure follows: UNEXPLAINED new bench FAIL1099/1100/1100/1100, 2026-11-10.
    Only marker damage landed; child damage was not observed. Archived0030.png
    confirms all four alive. Radius anchor, filter relationship reference and
    child firing conditions have not been separated. STOP; no prediction fitting.
    Original PREDICT1089/1090/1100/1100 before bench (1000*alive + health%).
    FireOnObjectsNugget Radius100, FireOnVictimObject true, FilterANY VEHICLE
    ENEMIES dispatches CNV_FireObjectsChild to each live selected victim.
    Child100UNRESISTABLE, Radius0, RadiusDamageAffectsSELF/ALLIES/ENEMIES/NEUTRALS.
    1000HP primary also receives10UNRESISTABLE marker ->89%; vehicle60 east
    receives100 ->90%; vehicle160 east spared; infantry80 north excluded ->100%.
    No guesses about boundary extent: selected centres are far from edges.
    Current sim ignores FireOnObjects, predicts1099/1100/1100/1100.
    One initially EMPTY clip loads1s, order6s, stop6+4/15; four packed counters.
    Each frame clears health counter before reading, so dead-object freeze cannot
    preserve a passing health+alive packed reading. Child/OCL chains, upgrades,
    status filters and FireOnVictimObject=false are outside this first check.
    """
    import re
    from maps import probe_range
    from parts import Mission,Script,Test
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun
    missile = engine_missile()["shared"]
    target = missile.target
    TARGET_ID = missile.TARGET_ID

    def mission():
        effect='<FireOnObjectsNugget Radius="100" Weapon="CNV_FireObjectsChild" FireOnVictimObject="true"><Filter Rule="ANY" Include="VEHICLE" Relationship="ENEMIES"/></FireOnObjectsNugget>'
        u=gun('CNV_FireObjectsGun',10,effect)
        u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
        child='<WeaponTemplate id="CNV_FireObjectsChild" AttackRange="500" RadiusDamageAffects="SELF ALLIES ENEMIES NEUTRALS"><Nuggets><DamageNugget Damage="100" DamageType="UNRESISTABLE" DeathType="NORMAL" Radius="0"/></Nuggets></WeaponTemplate>'
        u.xml=u.xml.replace('</AssetDeclaration>',child+'</AssetDeclaration>')
        u.link.append('WeaponTemplate:CNV_FireObjectsChild')
        m=Mission(name='CampFireObj',map=probe_range,units=[u,target(health=1000)],facts={})
        m.put(u.id,'base gun',side='p1',angle=1.5708,name='FireObj gun')
        for name,template,x,y in [('main',TARGET_ID,0,450),('inner',TARGET_ID,60,450),
                                   ('outer',TARGET_ID,160,450),('man','AlliedAntiInfantryInfantry',0,530)]:
            m.put(template,'base gun',x,y,side='s1',angle=4.7124,name='FireObj '+name)
        return m

    def check(m):
        t=Test(); names=['FireObj '+k for k in ('main','inner','outer','man')]
        start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','FireObj Fire',6.0),('SET_MILLISECOND_TIMER','FireObj Stop',6.0+4/15)]
        start += [('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in names+['FireObj gun']]
        t.scripts=[Script('Test - start',[],start),
            Script('Test - fire',[('TIMER_EXPIRED','FireObj Fire')],[('UNIT_CHANGE_OBJECT_STATUS','FireObj gun','NO_ATTACK',0),('NAMED_ATTACK_NAMED','FireObj gun','FireObj main')]),
            Script('Test - stop',[('TIMER_EXPIRED','FireObj Stop')],[('UNIT_CHANGE_OBJECT_STATUS','FireObj gun','NO_ATTACK',1)])]
        for i,v in enumerate(names):
            c='CNV_FireObj_'+str(i);t.counters.append((c,v))
            t.scripts += [Script('Test - hp '+str(i),[],[('SET_COUNTER',c,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c)],once=False),
                          Script('Test - alive '+str(i),[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,c)],once=False)]
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(1089,1090,1100,1100))]
        t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
        return t
    def wide_check(m):
        # Coordinator discriminator: change ONLY child weapon; keep parent filter/positions/statuses.
        u=next(u for u in m.units if u.id=='CNV_FireObjectsGun')
        child='<WeaponTemplate id="CNV_FireObjectsChild" AttackRange="999999" WeaponSpeed="999999" ClipSize="0" RequiredAntiMask="ANTI_GROUND ANTI_WATER ANTI_STRUCTURE ANTI_SUBMERGED ANTI_AIRBORNE_VEHICLE ANTI_AIRBORNE_INFANTRY" RadiusDamageAffects="SELF ALLIES ENEMIES NEUTRALS"><Nuggets><DamageNugget Damage="10000" DamageType="UNRESISTABLE" DeathType="NORMAL" Radius="10"/></Nuggets></WeaponTemplate>'
        u.xml,n=re.subn(r'<WeaponTemplate id="CNV_FireObjectsChild".*?</WeaponTemplate>',child,u.xml,flags=re.S)
        assert n==1
        t=check(m)
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(0,0,1100,1100))]
        return t

    def retail_check(m):
        t=wide_check(m)
        u=next(u for u in m.units if u.id=='CNV_FireObjectsGun')
        # Match the stock ProductionKickbacks parent recipe; child remains the wide diagnostic.
        u.xml=u.xml.replace('<FireOnObjectsNugget Radius="100"',
            '<FireOnObjectsNugget Radius="100" PartitionFilterTestType="CIRCLE"')
        u.xml=u.xml.replace('<Filter Rule="ANY" Include="VEHICLE" Relationship="ENEMIES"/>',
            '<Filter Rule="ANY" Include="INFANTRY VEHICLE HUGE_VEHICLE STRUCTURE"/>')
        u.xml=u.xml.replace('RadiusDamageAffects="ENEMIES"','RadiusDamageAffects="ALLIES ENEMIES NEUTRALS"',1)
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(0,0,1100,0))]
        return t

    MISSION={'engine_fireobjects':mission}
    CHECKS={'engine_fireobjects':{'a':check,'wide':wide_check,'ret':retail_check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_fwcollide():
    """Engine unit test: FireWeaponCollide (E217) -- the Flak trooper's (SovietAntiVehicleInfantry) crush revenge.

    Retail data: ModuleTag_CrushRevengeWeapon, CollideWeapon SovietAntiVehicleInfantryMagneticBombExplosion, Flags
    WHEN_BEING_CRUSHED, RequiredStatus GENERIC_TOGGLE_STATE (its magnetic bomb's ToggleState,
    Command_ToggleMagneticBombSpecialPower), FireOnce. The weapon: one DamageNugget 200 CANNON, radius 10 (taper 10),
    VEHICLE / STRUCTURE only, RadiusDamageAffects ALLIES ENEMIES NEUTRALS. The Hammer (SovietAntiVehicleVehicleTech1,
    crusher 20 against infantry's 10) has MaxHealth 550, BaseTankArmor CANNON 100 %.

    On the festival map, west field, two lanes along +x 300 apart (engine_crush's lanes): in each the player's Hammer
    200 west of an enemy Flak trooper, everyone HOLD_FIRE, the Hammers ordered at 'Test Go' (2 s) to a point 200 east of
    the trooper (straight through). Lane 1's trooper presses the toggle at once (its GENERIC_TOGGLE_STATE comes on with
    the press: engine_toggle b, PackTime 1 s delays nothing); lane 2's does not (the control).

    Counters (four lines), counted from 'Test Go' on:
      帧数  frames since Go
      一道  lane 1's Hammer: 1 x frames its health is below 100 % + 1000 x frames below 70 %
      二道  lane 2's Hammer: the same
      步兵  1 x frames lane 1's trooper is not destroyed + 1000 x frames lane 2's is not

    Predicted from the data: both troopers crushed (engine_crush: the conscript at frame 43); lane 1's Hammer from that
    frame 350 / 550 = 63 % (one hit at the centre, the taper INFERRED to leave it whole) -- 一道 n001 n001 alike
    (the same count in both parts); lane 2's Hammer whole (二道 0).
    """
    from maps import festival
    from parts import Mission, Script, Test

    HAMMER, FLAK = 'SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleInfantry'
    TOGGLE = 'Command_ToggleMagneticBombSpecialPower'
    LANES = {1: -150.0, 2: 150.0}
    RUN, HOLD_FIRE = 30.0, 3


    def _n(part):
        return f'UNIT - CNV FWColl {part}'


    def mission():
        m = Mission(name='CampFWColl', map=festival, units=[], facts={})
        for k, dy in LANES.items():
            m.put(HAMMER, 'west field', -200.0, dy, angle=0.0, role=f'tank {k}', name=_n(f'Tank {k}'))
            m.put(FLAK, 'west field', 0.0, dy, angle=180.0, side='s1', role=f'flak {k}', name=_n(f'Flak {k}'))
        return m


    def collide_test(m):
        t = Test()
        p1 = m.player('p1')
        x, y = m.site('west field')[:2]
        for k, dy in LANES.items():
            t.waypoints[f'Test Goal {k}'] = (x + 200.0, y + dy)
        names = [_n(f'{p} {k}') for k in LANES for p in ('Tank', 'Flak')]
        start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 2.0)]
        start += [('UNIT_SET_STANCE', n, HOLD_FIRE) for n in names]
        start += [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Flak 1'), TOGGLE)]
        t.scripts.append(Script('Test - start', [], start))
        go = [('MOVE_NAMED_UNIT_TO', _n(f'Tank {k}'), f'Test Goal {k}') for k in LANES]
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)
        t.counters.append(('CNV_FWColl_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_FWColl_Frames')], once=False))
        hurt = lambda k, pct: ('UNIT_HEALTH', _n(f'Tank {k}'), 0, pct)  # noqa: E731
        rows = {
            2: ('一道', [(hurt(1, 100), 1), (hurt(1, 70), 1000)]),
            3: ('二道', [(hurt(2, 100), 1), (hurt(2, 70), 1000)]),
            4: ('步兵', [(('NAMED_NOT_DESTROYED', _n('Flak 1')), 1), (('NAMED_NOT_DESTROYED', _n('Flak 2')), 1000)]),
        }
        for k, (label, conds) in rows.items():
            t.counters.append((f'CNV_FWColl_Row{k}', label))
            for j, (cond, step) in enumerate(conds):
                t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                        [('INCREMENT_COUNTER', step, f'CNV_FWColl_Row{k}')], once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
        return t


    MISSION = {'engine_fwcollide': mission}
    CHECKS = {'engine_fwcollide': {'a': collide_test}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_fwupdate():
    """Engine unit test: FireWeaponUpdate (E218) -- the Tesla trooper's (SovietHeavyAntiVehicleInfantry) short circuit.

    Of retail's 23 templates with the module the 27 missions reach two: this trooper (all 27) and A09_IronCurtainEffect
    (a09, the Iron Curtain's look-alike). Retail data: ModuleTag_FireWeaponUpdate, FireInterval 0.13 s, AliveOnly,
    ActiveWhenDisabled HELD, FireWeaponNugget SovietHeavyAntiVehicleInfantryShortCircuit (OneShot false),
    ObjectStatusValidation RequiredStatus GENERIC_TOGGLE_STATE (Command_ToggleShortCircuit; on from the press for good,
    engine_toggle f). The weapon: two ParalyzeNuggets EMP, radius 50, 1.1 s, ENEMIES NEUTRAL -- the first Rule NONE with
    no Include (ExcludeThing the trooper), the second Rule ANY Include VEHICLE (+ SovietScoutVehicle), Exclude INFANTRY
    AIRCRAFT STRUCTURE, StatusBitFlagsExclude UNATTACKABLE UNDER_IRON_CURTAIN.

    On the probe range, everyone NO_ATTACK. Lane 1 (base gun): the player's trooper, an enemy Hammer 30 north and one 80
    north, an enemy conscript 30 south, the player's own Hammer 30 east. Lane 2 (switch gun, the control): the same
    trooper and an enemy Hammer 30 north, no press. At PRESS lane 1's trooper presses the toggle; MOVE_AT after it every
    other unit is sent 300 further out (its own direction); KILL after the press lane 1's trooper is killed (AliveOnly).

    Counters (four lines), frames added from the press on:
      近车  +1 a frame lane 1's Hammer 30 stands in its 30 home square, +1000 the Hammer 80 does
      旁人  +1 the conscript, +1000 the own Hammer
      对照  +1 lane 2's Hammer 30, +1000 a frame lane 1's Hammer 30 is below 100 % (NO_ATTACK holds)

    Predicted from the data (15 frames a second): a pulse every 2 frames from the press (0.13 s), each holding a taken
    unit 17 frames (1.1 s) past it; the trooper's last pulse at the kill (frame 75), so the Hammer 30 stays till ~92 and
    then walks its 30 like the control -- 近车 % 1000 = 对照 % 1000 + ~87; the Hammer 80 (outside 50) = the control;
    the own Hammer = the control (ENEMIES NEUTRAL); the conscript: the first nugget's Rule NONE with an empty Include
    read as taking nothing (INFERRED; it would hold him as the Hammer 30 if NONE takes all) -- = the control. 对照 // 1000
    = 0.
    """
    from maps import probe_range
    from parts import Mission, Script, Test, square

    PRESS, MOVE_AT, KILL, RUN = 2.0, 0.3, 5.0, 14.0
    TESLA, HAMMER, CONSCRIPT = 'SovietHeavyAntiVehicleInfantry', 'SovietAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry'
    TOGGLE = 'Command_ToggleShortCircuit'
    N = 'UNIT - CNV FWU '
    # name: (template, side, lane site, dx, dy) -- each sent 300 further out along (dx, dy)
    VICTIMS = {'H30': (HAMMER, 's1', 'base gun', 0, 30), 'H80': (HAMMER, 's1', 'base gun', 0, 80),
               'C30': (CONSCRIPT, 's1', 'base gun', 0, -30), 'Own': (HAMMER, 'p1', 'base gun', 30, 0),
               'Ctl': (HAMMER, 's1', 'switch gun', 0, 30)}


    def mission():
        m = Mission(name='CampFWUpd', map=probe_range, units=[], facts={})
        m.put(TESLA, 'base gun', side='p1', name=N + 'Tesla')
        m.put(TESLA, 'switch gun', side='p1', name=N + 'Tesla Ctl')
        for k, (tpl, side, site, dx, dy) in VICTIMS.items():
            m.put(tpl, site, dx, dy, side=side, name=N + k)
            f = 300.0 / (dx * dx + dy * dy) ** 0.5
            m.waypoint(f'{k} away', f'Test FWU {k} Away', site, dx * (1 + f), dy * (1 + f))
        return m


    def surge(m):
        t = Test()
        p1 = m.player('p1')
        names = [N + 'Tesla', N + 'Tesla Ctl'] + [N + k for k in VICTIMS]
        for k, (_, _, site, dx, dy) in VICTIMS.items():
            t.areas[f'Test FWU {k} Home'] = square(*m.site(site, dx, dy), 30.0)
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)] +
                                [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in names] +
                                [('SET_MILLISECOND_TIMER', 'Test Press', PRESS),
                                 ('SET_MILLISECOND_TIMER', 'Test Move', PRESS + MOVE_AT),
                                 ('SET_MILLISECOND_TIMER', 'Test Kill', PRESS + KILL)]))
        t.scripts.append(Script('Test - press', [('TIMER_EXPIRED', 'Test Press')], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', N + 'Tesla', TOGGLE), ('SET_FLAG', 'Test Going', 1)]))
        t.scripts.append(Script('Test - move', [('TIMER_EXPIRED', 'Test Move')],
                                [('MOVE_NAMED_UNIT_TO', N + k, m.mark(f'{k} away')) for k in VICTIMS]))
        t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill')], [('NAMED_KILL', N + 'Tesla')]))
        going = ('FLAG', 'Test Going', 1)
        home = lambda k: ('NAMED_INSIDE_AREA', N + k, f'Test FWU {k} Home')  # noqa: E731
        rows = {'近车': [(home('H30'), 1), (home('H80'), 1000)],
                '旁人': [(home('C30'), 1), (home('Own'), 1000)],
                '对照': [(home('Ctl'), 1), (('UNIT_HEALTH', N + 'H30', 0, 100), 1000)]}
        t.counters.append(('CNV_FWU_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_FWU_Frames')], once=False))
        for j, (label, conds) in enumerate(rows.items()):
            counter = f'CNV_FWU_Row{j}'
            t.counters.append((counter, label))
            t.scripts.extend(Script(f'Test - {counter} {i}', [going, cond], [('INCREMENT_COUNTER', step, counter)],
                                    once=False) for i, (cond, step) in enumerate(conds))
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
        return t


    MISSION = {'engine_fwupdate': mission}
    CHECKS = {'engine_fwupdate': {'a': surge}}      # mod CampFWUpdA: 10 characters
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_grapple():
    """GrapplingHookUpdate -- the Apocalypse's harpoon (SovietAntiVehicleVehicleTech3, 24 of the 27 levels).

    Retail: Command_ToggleHarpoonSpecialPower steps its ToggleStatusSpecialAbilityUpdate to GENERIC_TOGGLE_STATE; the weapon
    set then forbids the cannon and arms SovietAntiVehicleVehicleTech3Harpoon (300 range, FiringDuration 1 s, clip 1 /
    reload 2 s; GrapplingHookNugget Damage 1 CANNON on VEHICLE / STRUCTURE / TIME_BOMB not AIRCRAFT / bridge). The
    GrapplingHookUpdate (RequiredStatus GENERIC_TOGGLE_STATE) pulls the hooked thing at PullRate 40; at the hooker it
    fires SingleFireWeapon SovietHarpoonCrushWeapon (999999 CRUSH on VEHICLE / TIME_BOMB, 1 s delay) and then
    ContinuousFireWeapon SovietHarpoonGrindWeapon (25 EXPLOSIVE every 0.24 s, 0.25 s after) -- BouncePercentage 5 %.

    Two lanes, each a p1 Apocalypse facing north and an s1 Hammer (NO_ATTACK) DIST north of it (260 / 160: two distances
    part the pull's speed from its fixed delays). Both Apocalypses pressed at PRESS, held NO_ATTACK until SHOOT, then
    ordered at their Hammer. Counters: each Hammer's health and its ring -- how many of the squares of half-side 25 .. 225
    (step 25) round its Apocalypse it stands in (9 far .. 0 beyond 225; it walks the line, so a ring is a 25 band).
    Prediction: the ring climbs about 40 a second (1.6 a second), the Hammer dies a second after it is at the tank.
    b (A365): pressed the same, never ordered: Far's Apocalypse keeps NO_ATTACK all along, Near's loses it at the press -- does
    the harpoon fire at the press on its own (a's hook came at the press, a second before the order)?
    The older synthetic probe here (a gun with a GrapplingHookNugget, no toggle) never pulled anything (1099 x 4).
    """
    from maps import probe_range
    from parts import Mission, Script, Test, counted, square

    APOC, HAMMER = 'SovietAntiVehicleVehicleTech3', 'SovietAntiVehicleVehicleTech1'
    TOGGLE = 'Command_ToggleHarpoonSpecialPower'
    LANES = {'Far': ('base', 260.0), 'Near': ('high', 160.0)}
    RINGS = range(25, 250, 25)
    PRESS, SHOOT, END = 15 * 16, 15 * 17, 15 * 32      # the counters are read from s15


    def mission():
        m = Mission(name='CampGrapple', map=probe_range, units=[])
        for arm, (lane, dist) in LANES.items():
            m.put(APOC, f'{lane} gun', side='p1', role=f'apoc {arm}', name=f'E226 Apoc {arm}', angle=1.5708)
            m.put(HAMMER, f'{lane} gun', 0, dist, side='s1', role=f'victim {arm}', name=f'E226 Hammer {arm}', angle=4.7124)
        return m


    def check(m, b=False):
        t = Test()
        for arm, (lane, _) in LANES.items():
            counted(f'E226Hp{arm}', '血' + arm, t, health=m.role(f'victim {arm}').name)
        for arm, (lane, _) in LANES.items():
            c, v, (x, y) = f'E226Ring{arm}', m.role(f'victim {arm}').name, m.site(f'{lane} gun', 0, 0)
            t.counters.append((c, '圈' + arm))
            t.scripts.append(Script(f'Test - ring {arm} zero', [], [('SET_COUNTER', c, 0)], once=False))
            for r in RINGS:
                t.areas[f'E226 {arm} {r}'] = square(x, y, r)
                t.scripts.append(Script(f'Test - ring {arm} {r}', [('NAMED_INSIDE_AREA', v, f'E226 {arm} {r}')],
                                        [('INCREMENT_COUNTER', 1, c)], once=False))
        apocs = [m.role(f'apoc {arm}').name for arm in LANES]
        t.scripts += [Script('Test - clock', [('COUNTER', 'E226Frame', 0, END)],
                             [('INCREMENT_COUNTER', 1, 'E226Frame')], once=False),
                      Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] +
                             [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in apocs] +
                             [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'victim {arm}').name, 'NO_ATTACK', 1) for arm in LANES]),
                      Script('Test - press', [('COUNTER', 'E226Frame', 2, PRESS)],
                             [('NAMED_USE_COMMANDBUTTON_ABILITY', n, TOGGLE) for n in apocs] +
                             ([('UNIT_CHANGE_OBJECT_STATUS', apocs[1], 'NO_ATTACK', 0)] if b else []))]
        t.scripts += [] if b else [Script('Test - shoot', [('COUNTER', 'E226Frame', 2, SHOOT)],
                             [a for arm in LANES for a in (('UNIT_CHANGE_OBJECT_STATUS', m.role(f'apoc {arm}').name,
                                                            'NO_ATTACK', 0),
                                                           ('NAMED_ATTACK_NAMED', m.role(f'apoc {arm}').name,
                                                            m.role(f'victim {arm}').name))])]
        t.expect = [('血Far', 0, '==', 100)]
        t.bench = [('bench_camera', dict(x=m.site('base gun', 0, 0)[0], y=m.site('base gun', 0, 0)[1], look=False)),
                   ('bench_watch', dict(seconds=END // 15 + 3, every=.5, sheet=False, lines=4))]
        return t


    MISSION = {'engine_grapple': mission}
    CHECKS = {'engine_grapple': {'a': check, 'b': lambda m: check(m, True)}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


@cache
def engine_laser():
    """Bench PASS2/90/2/90 (new run); PREDICT before bench. Two1000HP Hammers each receive one100 EXPLOSIVE
    (100% tank armor); high gun additionally activates LaserId201 for2s.
    Both shooters carry retail Mirage's matching LaserDraw/LaserState201;
    so this is not an absent-renderer no-op. Laser nugget's schema fields
    Lifetime/LaserId/HitGroundFX/OverShootDistance contain no damage field;
    independent DamageNugget accounts for all100 damage. First script hit2
    frames, no HP change after laser expires. Finite clip loads1s, fire6s,
    stop6+4/15. Only HP/timing isolated here, draw declarations matched statically; rendered pixels are not asserted.
    """
    import re
    from pathlib import Path
    from maps import probe_range
    from parts import Mission,Script,Test
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun
    missile = engine_missile()["shared"]
    SAGE = missile.SAGE
    target = missile.target
    TARGET_ID = missile.TARGET_ID

    def mission():
        m=Mission(name='CampLaser',map=probe_range,units=[target(health=1000)],facts={})
        xml=Path(SAGE,'Allied','Units','AlliedAntiVehicleVehicleTech3.xml').read_text(encoding='utf8')
        draw=re.search(r'<LaserDraw\b.*?</LaserDraw>',xml,re.S).group(0)
        state=re.search(r'<LaserState\b.*?</LaserState>',xml,re.S).group(0)
        for lane in ('base','high'):
            extra='<ActivateLaserNugget LaserId="201" Lifetime="2s"/>' if lane=='high' else ''
            u=gun('CNV_Laser'+lane.title(),100,extra)
            u.xml=u.xml.replace('</Draws>',draw+'</Draws>').replace('</Behaviors>',state+'</Behaviors>')
            m.units.append(u)
            m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='Laser '+lane+' gun')
            m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name='Laser '+lane+' target')
        return m

    def check(m):
        t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','Laser Fire',6.0),('SET_MILLISECOND_TIMER','Laser Stop',6+4/15)]
        fire=[];stop=[]
        for lane in ('base','high'):
            g='Laser '+lane+' gun';v='Laser '+lane+' target';c='CNV_Laser_'+lane
            start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
            fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
            t.counters.extend([(c,lane+' hit'),(c+'HP',lane+' HP')])
            t.scripts += [Script('Test - hit '+lane,[('FLAG','Laser Ordered',1),('UNIT_HEALTH',v,2,100)],[('INCREMENT_COUNTER',1,c)],once=False),
                          Script('Test - hp '+lane,[],[('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c+'HP')],once=False)]
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','Laser Fire')],fire+[('SET_FLAG','Laser Ordered',1)]))
        t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','Laser Stop')],stop))
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(2,90,2,90))]
        t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
        return t
    MISSION={'engine_laser':mission}
    CHECKS={'engine_laser':{'pair':check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        check=check, mission=mission))


def engine_leechhealth():
    """New bench PASS1001095045/1001090050/1001090045/1001090040; initial prediction.
    Four1000HP casters start40%=400HP; each1000HP target starts full.
    base: LeechHealthDamageNugget Damage100 GUN, tank armor50% ->target95%;
    GUESSED healing after armor:100% of50 ->caster45%.
    high:100UNRESISTABLE bypasses armor ->target90%, heal100 ->caster50%.
    order: same UNRESISTABLE, PercentDamageToHeal50% ->caster45%, target90%.
    removed: plain100UNRESISTABLE ->caster40%, target90%.
    Packed=1e9*targetAlive+1e6*casterAlive+1000*targetHP%+casterHP%.
    If healing is before armor, base instead reads1001095050; the other lanes
    separate heal percentage from ordinary damage/autoheal. No health cap reached.
    Core unfiltered, ungated direct nugget; death/upgrade/beam weapon theft not
    asserted. Empty clips load1s; order6s, NO_ATTACK6+4/15; four lines.
    """
    import re
    from maps import probe_range
    from parts import Mission,Script,Test
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun
    missile = engine_missile()["shared"]
    target = missile.target
    TARGET_ID = missile.TARGET_ID
    CASES=(('base','GUN',100),('high','UNRESISTABLE',100),('order','UNRESISTABLE',50),('removed','UNRESISTABLE',None))

    def mission():
        m=Mission(name='CampLH',map=probe_range,units=[target(health=1000)],facts={})
        for lane,kind,pct in CASES:
            u=gun('CNV_LHealth'+lane.title(),100)
            u.xml=u.xml.replace('DamageType="EXPLOSIVE"',f'DamageType="{kind}"')
            u.xml,n=re.subn(r'\bMaxHealth="[^"]+"','MaxHealth="1000"',u.xml);assert n==1
            if pct is not None:u.xml=u.xml.replace('<DamageNugget ',f'<LeechHealthDamageNugget PercentDamageToHeal="{pct}%" ')
            m.units.append(u)
            m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='LH '+lane+' gun')
            m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name='LH '+lane+' target')
        return m

    def check(m):
        t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','LH Fire',6.0),('SET_MILLISECOND_TIMER','LH Stop',6+4/15)]
        fire=[];stop=[]
        for lane,kind,pct in CASES:
            g='LH '+lane+' gun';v='LH '+lane+' target';c='CNV_LH_'+lane;tmp=c+'VictimHP'
            start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
            start.append(('UNIT_SET_HEALTH',g,40.0))
            fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
            t.counters.append((c,lane+' packed'))
            t.scripts += [Script('Test - hp '+lane,[],[('SET_COUNTER',c,0),('SET_COUNTER',tmp,0),
                ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',g,c),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,tmp),
                ('COUNTER_MATH_VALUE',tmp,2,1000),('COUNTER_MATH_COUNTER',c,0,tmp)],once=False),
                Script('Test - caster '+lane,[('NAMED_NOT_DESTROYED',g)],[('INCREMENT_COUNTER',1000000,c)],once=False),
                Script('Test - victim '+lane,[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000000000,c)],once=False)]
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','LH Fire')],fire))
        t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','LH Stop')],stop))
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(1001095045,1001090050,1001090045,1001090040))]
        t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
        return t
    MISSION={'engine_leechhealth':mission}
    CHECKS={'engine_leechhealth':{'a':check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_leechpct():
    """New bench PASS1000025/1000025/1000030/1000020; PREDICT before bench.
    Four10000HP shooters start20%=2000HP. Three sole, ungated
    LeechPercentMaxHealthDamageNugget shots Damage999999UNRESISTABLE,
    PercentMaxHealthToTake50%; one plain DamageNugget control. Victims:
    base1000full, high1000half, order2000full, removed1000full control.
    GUESSED healing source from field name: half VICTIM MAX health500/500/1000,
    so caster25/25/30%; plain damage leaves20%. All victims die, shooters live.
    Packed per lane=HP% +1000*victimAlive +1000000*shooterAlive, cleared each
    frame before health read to defeat death-counter freeze. This separates
    max-vs-current victim HP and victim-vs-caster maximum, with no cap saturation.
    No retail RequiredUpgrade or filter in this core-field isolation; upgrade,
    CRUSH-specific delivery and nonlethal healing are outside the first probe.
    Empty clips load1s, order6s, NO_ATTACK6+4/15; four lines.
    """
    import re
    from maps import probe_range
    from parts import Mission,Script,Test
    from benches.weapon.target_effects.checks import engine_weaponfx
    gun = engine_weaponfx()["shared"].gun
    target = engine_missile()["shared"].target
    CASES=(('base',1000,100.0,True),('high',1000,50.0,True),('order',2000,100.0,True),('removed',1000,100.0,False))

    def mission():
        m=Mission(name='CampLPct',map=probe_range,units=[target('CNV_LPctT1',1000),target('CNV_LPctT2',2000)],facts={})
        for lane,hp,start,leech in CASES:
            u=gun('CNV_LPct'+lane.title(),999999)
            u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
            u.xml,n=re.subn(r'\bMaxHealth="[^"]+"','MaxHealth="10000"',u.xml);assert n==1
            if leech:
                u.xml=u.xml.replace('<DamageNugget ','<LeechPercentMaxHealthDamageNugget PercentMaxHealthToTake="50%" ')
            m.units.append(u)
            m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='LPct '+lane+' gun')
            m.put('CNV_LPctT2' if hp==2000 else 'CNV_LPctT1',lane+' gun',0,450,side='s1',angle=4.7124,name='LPct '+lane+' target')
        return m

    def check(m):
        t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','LPct Fire',6.0),('SET_MILLISECOND_TIMER','LPct Stop',6+4/15)]
        fire=[];stop=[]
        for lane,hp,health,leech in CASES:
            g='LPct '+lane+' gun';v='LPct '+lane+' target';c='CNV_LPct_'+lane
            start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
            start += [('UNIT_SET_HEALTH',g,20.0),('UNIT_SET_HEALTH',v,float(health))]
            fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
            t.counters.append((c,lane+' packed'))
            t.scripts += [Script('Test - hp '+lane,[],[('SET_COUNTER',c,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',g,c)],once=False),
                          Script('Test - caster '+lane,[('NAMED_NOT_DESTROYED',g)],[('INCREMENT_COUNTER',1000000,c)],once=False),
                          Script('Test - victim '+lane,[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,c)],once=False)]
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','LPct Fire')],fire))
        t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','LPct Stop')],stop))
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(1000025,1000025,1000030,1000020))]
        t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
        return t
    MISSION={'engine_leechpct':mission}
    CHECKS={'engine_leechpct':{'a':check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


@cache
def engine_missile():
    """Engine unit test: a homing missile (ADR 0019 layer 2, wish list item 2, batch "homing"; docs/engine/missile.md) --
    how long retail's V4 rocket (BezierProjectile) takes to land at two distances, what one hit takes off, and whether
    FlightPathAdjustDistPerSecond makes it follow a target that jumps aside while it flies.

    On the range probe map (maps/probe_range.py, flat) four lanes 1500 apart, each one shooter of the player's (p1, facing
    north, so no turning) and one enemy target (s1, target(): a Hammer with TARGET_HP health, held with NO_ATTACK, so a
    500 hit is a few percent) straight north of it:

      near   retail V4 (SovietAntiStructureVehicle)   target at NEAR
      far    retail V4                                target at FAR
      dodge  retail V4 (homing 10 / s)                target at FAR, teleported DODGE east at ORDER + JUMP
      home   CNV_MslHome: the V4 with its rocket's FlightPathAdjustDistPerSecond raised to HOME_ADJUST
                                                      target at FAR, teleported the same way

    The shooters hold fire (NO_ATTACK) until ORDER, when each is freed and told to attack its target. Each lane's
    counter (four lines, the bench reads all): frames from the order until its target's health first drops below
    100 % (one a frame), plus 1000 for every percent it has started to lose (health < 100, < 99, ...) -- so 5073 =
    first hit 73 frames (4.9 s at 15 fps) after the order, 4-5 % lost.
    A counter still climbing past the far lane's frames means the first rocket missed. The script engine counts, so the
    reading does not depend on the bench's clock (the bench's seconds run 1-2 s ahead of the timers).

    Read (测, 2026-11-05, docs/engine/missile.md 1):
      miss   run CampMslMiss_mcp_1105_074535: near 5108, far 5108 (first hit 108 frames after the order at 250 and at 450
             alike, 5 % a hit), dodge 5117, home 5116 (the jump at +30 frames came before the launch: both hit); later
             hits about every 6.5 s. (Runs 1-2 that morning set the targets' health by script and read 60000 from s1:
             the max passed as a REAL where the action takes an INT, so it did nothing -- hence target(); the action
             itself: benches/body_death/state/checks.py#engine_maxhealth.)
      flight run CampMslFlight_mcp_1105_074901: near / far never saw their rocket (the type-in-area count does not count
             it); dodge 5210, home 5212: jumped at +90 frames (JUMP_LATE), the first rocket of both missed -- homing 300
             did not follow a 150 jump ~1.2 s before impact.
    The builds engine_missile_sweep / _ns / _adj (further down) found why: the V4 weapon's scatter.
    """
    import os
    import re

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, square

    SAGE = os.path.join(labpaths.SDK3, 'SageXML')
    V4, TARGET = 'SovietAntiStructureVehicle', 'SovietAntiVehicleVehicleTech1'
    V4_WEAPON, V4_ROCKET = 'SovietAntiStructureVehicleV4Rocket', 'SovietAntiStructureVehicleV4RocketProjectile'
    HOME, HOME_WEAPON, HOME_ROCKET = 'CNV_MslHome', 'CNV_MslHomeRocket', 'CNV_MslHomeProjectile'
    HOME_ADJUST = 300.0
    NEAR, FAR, DODGE = 250.0, 450.0, 150.0
    TARGET_HP, TARGET_ID = 10000.0, 'CNV_MslTarget'
    ORDER, JUMP, RUN = 3.0, 2.0, 30.0
    LANES = {'near': ('base gun', V4, NEAR, False), 'far': ('high gun', V4, FAR, False),
             'dodge': ('order gun', V4, FAR, True), 'home': ('removed gun', HOME, FAR, True)}
    LABELS = {'near': '近靶', 'far': '远靶', 'dodge': '躲靶', 'home': '追靶'}
    LOST_MAX = 60                       # percent steps counted (a hit of 500 on 10 000 is 5 % before armor)


    def _sub1(x, old, new):
        assert x.count(old) == 1, (old[:60], x.count(old))
        return x.replace(old, new, 1)


    def home_v4(id=HOME, adjust=HOME_ADJUST, scatter=True, lock=True, times=None):
        """Retail's V4 under `id`, its rocket weapon swapped for a copy (`id`Rocket) whose projectile (`id`Projectile)
        is retail's V4 rocket with FlightPathAdjustDistPerSecond = adjust (retail 10). scatter=False also drops the
        weapon's own ScatterRadiusVsType 0.1 vs INFANTRY VEHICLE (with a scatter Generals launches at a position, not at
        the victim, so nothing homes); lock=False its WeaponAiHintInfo UseLongLockOnTimeCode; times = {'PreAttackDelay' /
        'FiringDuration': seconds} sets those (Min = Max). Nothing else differs (ADR 0016 G5: the probe builds it)."""
        HOME_WEAPON, HOME_ROCKET = id + 'Rocket', id + 'Projectile'
        x = open(os.path.join(SAGE, 'Soviet', 'Units', V4 + '.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{V4}"', f'id="{id}"')
        x = re.sub(rf'EditorName="{V4}"', f'EditorName="{id}"', x)
        x = _sub1(x, f'Template="{V4_WEAPON}"', f'Template="{HOME_WEAPON}"')
        w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
        s = re.search(rf'\t*<WeaponTemplate\s+id="{V4_WEAPON}".*?</WeaponTemplate>\n', w, re.S).group(0)
        s = _sub1(s, f'id="{V4_WEAPON}"', f'id="{HOME_WEAPON}"')
        # its parent ScatterableWeapon (Weapon.xml) is not in our stream; it only adds a scatter while SHRINK_EFFECT
        s = _sub1(s, 'inheritFrom="ScatterableWeapon"', '')
        s = _sub1(s, f'ProjectileTemplate="{V4_ROCKET}"', f'ProjectileTemplate="{HOME_ROCKET}"')
        if not scatter:
            s, k = re.subn(r'\s*<ScatterRadiusVsType\s+Radius="0\.1">.*?</ScatterRadiusVsType>', '', s, flags=re.S)
            assert k == 1, k
        if not lock:
            s, k = re.subn(r'\s*<WeaponAiHintInfo\s+UseLongLockOnTimeCode="true"\s*/>', '', s)
            assert k == 1, k
        for tag, sec in (times or {}).items():
            s, k = re.subn(rf'<{tag}\s+MinSeconds="[^"]*"\s+MaxSeconds="[^"]*"',
                           f'<{tag} MinSeconds="{sec:g}s" MaxSeconds="{sec:g}s"', s)
            assert k == 1, (tag, k)
        x = _sub1(x, '</AssetDeclaration>', s + '</AssetDeclaration>')
        p = open(os.path.join(SAGE, 'Soviet', 'Props', V4_ROCKET + '.xml'), encoding='utf-8').read()
        # the file's second GameObject is retail's heroic variant (inherits the rocket): not ours, dropped
        p, k = re.subn(rf'\s*<GameObject\s+inheritFrom="{V4_ROCKET}".*?</GameObject>', '', p, flags=re.S)
        assert k == 1, k
        p = _sub1(p, f'id="{V4_ROCKET}"', f'id="{HOME_ROCKET}"')
        p = _sub1(p, f'EditorName="{V4_ROCKET}"', f'EditorName="{HOME_ROCKET}"')
        p = _sub1(p, 'FlightPathAdjustDistPerSecond="10.0"', f'FlightPathAdjustDistPerSecond="{adjust:.1f}"')
        fname = HOME_ROCKET + '.xml'
        return Unit(id, x, files={fname: p}, also=[fname], link=[f'WeaponTemplate:{HOME_WEAPON}'],
                    names=dict(unit=id, weapon=HOME_WEAPON, rocket=HOME_ROCKET),
                    what=f'追踪加强的 V4（探针）：导弹每秒修正 {adjust:g}（原版 10）'
                         f'{"" if scatter else "，去掉对车辆步兵的 0.1 散布"}{"" if lock else "，去掉 UseLongLockOnTimeCode"}'
                         + ''.join(f'，{t} {v:g} 秒' for t, v in (times or {}).items()) + '，其余同原版',
                    params=dict(adjust=adjust, scatter=scatter) | ({} if lock else {'lock': False})
                    | ({'times': times} if times else {}))


    def target(id=TARGET_ID, health=TARGET_HP):
        """Retail's Hammer under `id` with MaxHealth = health (retail 550): a 500 hit is a few percent. Built in the XML:
        by script it did not work (run 2, 11-05: NAMED_SET_MAX_HEALTH(.., 10000.0, 1) -- a REAL in the INT slot -- left the
        Hammer below 41 % from the start)."""
        x = open(os.path.join(SAGE, 'Soviet', 'Units', TARGET + '.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{TARGET}"', f'id="{id}"')
        x = _sub1(x, f'EditorName="{TARGET}"', f'EditorName="{id}"')
        x = _sub1(x, 'MaxHealth="550"', f'MaxHealth="{health:.1f}"')
        return Unit(id, x, names=dict(unit=id), what=f'{health:g} 血的锤子坦克（探针靶子），其余同原版',
                    params=dict(health=health))


    def mission():
        m = Mission(name='CampMsl', map=probe_range, units=[home_v4(), target()], facts={})
        for lane, (site, tpl, d, jumps) in LANES.items():
            L = lane.title()
            m.put(tpl, site, side='p1', role=f'{lane} shooter', name=f'UNIT - CNV Msl {L} Shooter')
            m.put(TARGET_ID, site, 0, d, side='s1', role=f'{lane} target', name=f'UNIT - CNV Msl {L} Target')
            if jumps:
                m.waypoint(f'{lane} jump', f'CNV Msl {L} Jump', site, DODGE, d)
        m.spawns |= {V4_ROCKET, HOME_ROCKET}          # the shooters make them: the flight check counts them
        return m


    def missile_test(m):
        t = Test()

        def n(part):
            return m.role(part).name

        targets = [n(f'{lane} target') for lane in LANES]
        shooters = [n(f'{lane} shooter') for lane in LANES]
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('UNIT_CHANGE_OBJECT_STATUS', tg, 'NO_ATTACK', 1) for tg in targets]
        # the shooters hold fire until the order (a V4 picks an enemy in reach by itself)
        start += [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 1) for s in shooters]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER), ('SET_MILLISECOND_TIMER', 'Test Jump', ORDER + JUMP)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s in shooters]
                                + [('NAMED_ATTACK_NAMED', n(f'{lane} shooter'), n(f'{lane} target')) for lane in LANES]
                                + [('SET_FLAG', 'Test Ordered', 1)]))
        t.scripts.append(Script('Test - jump', [('TIMER_EXPIRED', 'Test Jump')],
                                [('UNIT_TELEPORT_TO_WAYPOINT', n(f'{lane} target'), m.mark(f'{lane} jump'))
                                 for lane, (_, _, _, jumps) in LANES.items() if jumps]))
        for lane in LANES:
            c, tg = f'CNV_Msl_{lane.title()}', n(f'{lane} target')
            t.counters.append((c, LABELS[lane]))
            t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
            t.scripts += [Script(f'Test - {c} lost {k}', [('UNIT_HEALTH', tg, 0, 100 - k + 1)],
                                 [('INCREMENT_COUNTER', 1000, c)]) for k in range(1, LOST_MAX + 1)]
        # a measurement: the readings are written up in docs/engine/missile.md; the expectation only says the run went
        t.expect = [(LABELS['near'], 0, 'ever>=', 1000, RUN - 2)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
        return t


    # --- flight: when does the rocket leave, how long does it fly, does it follow? ----------------------------------
    # miss (run 3) hit near and far alike 108 frames after the order and the jump (2 s) came before the launch. Here the
    # rocket itself is watched: the player's objects of the rocket's template in the lane's trigger area (FLY_R around
    # the shooter-target midpoint, on the ground: INFERRED 2D) -- from the order until one shows up ("launch"), then
    # while it is there ("flight", the first rocket only: a lane is done once it is gone).
    #   near / far  launch frames + 1000 x flight frames
    #   dodge / home  the jump happens JUMP_AFTER s after that lane's rocket shows up (or at ORDER + JUMP_LATE without
    #               one); counter as in miss: frames to the first hit + 1000 per percent lost
    FLY_R, JUMP_AFTER, JUMP_LATE, FLIGHT_RUN = 500.0, 0.5, 6.0, 20.0
    FLIGHT_LABELS = {'near': '近发飞', 'far': '远发飞', 'dodge': '躲靶', 'home': '追靶'}


    def _rocket(lane):
        return HOME_ROCKET if LANES[lane][1] == HOME else V4_ROCKET


    def flight_test(m):
        t = Test()

        def n(part):
            return m.role(part).name

        p1 = m.player('p1')
        targets = [n(f'{lane} target') for lane in LANES]
        shooters = [n(f'{lane} shooter') for lane in LANES]
        start = [('MAP_REVEAL_ALL_PERM', p1)]
        start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in targets + shooters]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s in shooters]
                                + [('NAMED_ATTACK_NAMED', n(f'{lane} shooter'), n(f'{lane} target')) for lane in LANES]
                                + [('SET_FLAG', 'Test Ordered', 1), ('SET_MILLISECOND_TIMER', 'Test Late', JUMP_LATE)]))
        for lane, (site, _, d, jumps) in LANES.items():
            L, c = lane.title(), f'CNV_MslF_{lane.title()}'
            area, seen, done = f'Test Fly {L}', f'Test Seen {L}', f'Test Done {L}'
            x, y = m.site(site, 0, d / 2)
            t.areas[area] = square(x, y, FLY_R)
            there = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, _rocket(lane), area)
            gone = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 2, 0, _rocket(lane), area)
            t.counters.append((c, FLIGHT_LABELS[lane]))
            t.scripts.append(Script(f'Test - {c} seen', [('FLAG', 'Test Ordered', 1), there],
                                    [('SET_FLAG', seen, 1)] +
                                    ([('SET_MILLISECOND_TIMER', f'Test Jump {L}', JUMP_AFTER)] if jumps else [])))
            if jumps:
                jump = [('UNIT_TELEPORT_TO_WAYPOINT', n(f'{lane} target'), m.mark(f'{lane} jump'))]
                t.scripts.append(Script(f'Test - jump {L}', [('TIMER_EXPIRED', f'Test Jump {L}')], jump))
                t.scripts.append(Script(f'Test - jump {L} late', [('TIMER_EXPIRED', 'Test Late'), ('FLAG', seen, 0)],
                                        jump))
                tg = n(f'{lane} target')
                t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                        [('INCREMENT_COUNTER', 1, c)], once=False))
                t.scripts += [Script(f'Test - {c} lost {k}', [('UNIT_HEALTH', tg, 0, 100 - k + 1)],
                                     [('INCREMENT_COUNTER', 1000, c)]) for k in range(1, LOST_MAX + 1)]
                continue
            t.scripts.append(Script(f'Test - {c} launch', [('FLAG', 'Test Ordered', 1), ('FLAG', seen, 0)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
            t.scripts.append(Script(f'Test - {c} flight', [('FLAG', seen, 1), ('FLAG', done, 0), there],
                                    [('INCREMENT_COUNTER', 1000, c)], once=False))
            t.scripts.append(Script(f'Test - {c} done', [('FLAG', seen, 1), gone], [('SET_FLAG', done, 1)]))
        t.expect = [(FLIGHT_LABELS['near'], 0, 'ever>=', 1, FLIGHT_RUN - 2)]
        t.bench = [('bench_watch', dict(seconds=FLIGHT_RUN, every=1, sheet=False, lines=4))]
        return t


    # --- sweep / drive: when does the rocket leave, and does homing follow at all? ---------------------------------
    # A second build, four lanes of the probe map at FAR (only four counter lines fit): base / high shoot with retail's
    # V4 (homing 10 / s), removed / switch with CNV_MslHome (300 / s). A frame tick counts from the order; each lane's
    # target is moved at its own tick -- teleported SWEEP_DODGE east (sweep*) or sent driving DRIVE_TO east (drive). A
    # jump before the launch is aimed at (the first rocket hits, maybe late); after it only homing can save the shot.
    # Counters as in miss: frames from the order to the first hit + 1000 per percent lost (a first-rocket miss reads
    # ~210: the second rocket).
    # The third build (engine_missile_ns) asks why: the V4 weapon has its own ScatterRadiusVsType 0.1 vs INFANTRY
    # VEHICLE, and Generals launches a scattering weapon at a position (Weapon.cpp: "With a scatter radius, don't follow
    # the victim"). Its lanes: CNV_MslCopy (retail's V4 renamed, homing 10, scatter kept: does the copy alone fire
    # later?), CNV_MslHomeNS (homing 300 without the scatter, two lanes), CNV_MslV4NS (homing 10 without the scatter).
    # The fourth (engine_missile_adj): no scatter, FlightPathAdjustDistPerSecond 2 / 5 / 10 / 20, 150 jump at +60.
    #
    # Read (测, 2026-11-05, docs/engine/missile.md 3; frames to the first hit, ~210 = the first rocket missed):
    #   sweep   CampMslSSweep_mcp_1105_120848   V4 jump +40 5209, +60 5203; Home +40 5117, +60 5212
    #   sweep2  CampMslSSweep2_mcp_1105_121148  V4 +34 5109, +40 5203; Home +40 5117, +50 5212
    #   drive   CampMslSDrive_mcp_1105_121412   V4 drive 0 6218, 40 6258; Home 0 6220, 40 6257 (all missed)
    #   small   CampMslSSmall_mcp_1105_121632   V4 +75 east 50 2109 (graze), east 80 5203; Home +75/80 5210, +60/80 5212
    #   still   CampMslSStill_mcp_1105_122110   none moved: 5109 5108 (base, high) 5117 5116 (removed, switch)
    #   nsjump  CampMslNNsjump_mcp_1105_122534  Copy still 5109; HomeNS +60 5109, +75/80 5117; V4NS +60 4114 (graze)
    #   nsdrive CampMslNNsdrive_mcp_1105_122913 Copy drive 40 6257 (missed); HomeNS 0 6109, 40 6117; V4NS 40 6257
    #   adj     CampMslAAdj_mcp_1105_123121     adjust 2 5214, 5 5211 (missed); 10 5116, 20 5115 (hit)
    # So: the V4 launches 35-40 frames after the order; with the scatter nothing homes; without it 300 follows jumps
    # and a driving Hammer, 10 follows a jump but not a drive. The removed / switch / order lanes run ~8 frames later
    # than base / high every run, whatever the shooter (not read why).
    SWEEP_DODGE, DRIVE_TO, SWEEP_RUN = 150.0, 600.0, 24.0
    COPY, HOME_NS, V4_NS, NO_LOCK = 'CNV_MslCopy', 'CNV_MslHomeNS', 'CNV_MslV4NS', 'CNV_MslNoLock'
    WHO = {V4: 'V4', HOME: '追300', COPY: '复制V4', HOME_NS: '追300无散', V4_NS: 'V4无散'}
    BUILDS = {   # build: (mission name, units, {lane: shooter})
        'engine_missile_sweep': ('CampMslS', lambda: [home_v4(), target()],
                                 {'base': V4, 'high': V4, 'removed': HOME, 'switch': HOME}),
        'engine_missile_ns': ('CampMslN', lambda: [home_v4(COPY, 10.0), home_v4(HOME_NS, HOME_ADJUST, scatter=False),
                                                   home_v4(V4_NS, 10.0, scatter=False), target()],
                              {'base': COPY, 'high': HOME_NS, 'removed': HOME_NS, 'switch': V4_NS}),
        # how strong is FlightPathAdjustDistPerSecond? no scatter, 2 / 5 / 10 / 20, three lanes of the south row
        'engine_missile_adj': ('CampMslA', lambda: [home_v4('CNV_MslA2', 2.0, scatter=False),
                                                    home_v4('CNV_MslA5', 5.0, scatter=False),
                                                    home_v4(V4_NS, 10.0, scatter=False),
                                                    home_v4('CNV_MslA20', 20.0, scatter=False), target()],
                               {'base': 'CNV_MslA2', 'high': 'CNV_MslA5', 'order': V4_NS, 'switch': 'CNV_MslA20'}),
        # what holds the launch to 35-40 frames after the order (the sim: the 8-frame PreAttackDelay)? the copy against
        # the copy without UseLongLockOnTimeCode, each on an early lane (base / high) and a late one (removed / switch)
        'engine_missile_lock': ('CampMslL', lambda: [home_v4(COPY, 10.0), home_v4(NO_LOCK, 10.0, lock=False), target()],
                                {'base': COPY, 'high': NO_LOCK, 'removed': NO_LOCK, 'switch': COPY}),
        # lock (CampMslLLock_mcp_1124) 5109 / 5108 / 5117 / 5116: not the lock. Does the rocket leave at the end of its
        # FiringDuration (1 s)? the copy; FiringDuration 0.1 (early lane); FiringDuration 2 and PreAttackDelay 1.5 (late)
        'engine_missile_time': ('CampMslT', lambda: [home_v4(COPY, 10.0), *(home_v4(i, 10.0, times=t) for i, t in TIMED),
                                                     target()],
                                {'base': COPY, 'high': 'CNV_MslF01', 'removed': 'CNV_MslF2', 'switch': 'CNV_MslP15'}),
    }
    TIMED = (('CNV_MslF01', {'FiringDuration': 0.1}), ('CNV_MslF2', {'FiringDuration': 2.0}),
             ('CNV_MslP15', {'PreAttackDelay': 1.5}))
    WHO |= {'CNV_MslA2': '修2', 'CNV_MslA5': '修5', 'CNV_MslA20': '修20', NO_LOCK: 'V4无锁',
            'CNV_MslF01': '射0.1', 'CNV_MslF2': '射2', 'CNV_MslP15': '瞄1.5'}
    JUMPS = (50.0, 80.0, SWEEP_DODGE)                     # the jump waypoints east of each target
    MOVES = {     # build: {check: (how, per lane frames after the order or (frames, jump east); None stays)}
        'engine_missile_sweep': {
            'sweep': ('jump', {'base': 40, 'high': 60, 'removed': 40, 'switch': 60}),
            'sweep2': ('jump', {'base': 34, 'high': 40, 'removed': 40, 'switch': 50}),
            'drive': ('drive', {'base': 0, 'high': 40, 'removed': 0, 'switch': 40}),
            'small': ('jump', {'base': (75, 50.0), 'high': (75, 80.0), 'removed': (75, 80.0), 'switch': (60, 80.0)}),
            'still': ('jump', {'base': None, 'high': None, 'removed': None, 'switch': None})},
        'engine_missile_ns': {
            'nsjump': ('jump', {'base': None, 'high': 60, 'removed': (75, 80.0), 'switch': 60}),
            'nsdrive': ('drive', {'base': 40, 'high': 0, 'removed': 40, 'switch': 40})},
        'engine_missile_adj': {
            'adj': ('jump', {'base': 60, 'high': 60, 'order': 60, 'switch': 60})},
        'engine_missile_lock': {
            # the late lanes' targets jump only after the first hit (their labels differ from the early lanes')
            'lock': ('jump', {'base': None, 'high': None, 'removed': (200, 50.0), 'switch': (200, 50.0)})},
        'engine_missile_time': {
            'time': ('jump', {'base': None, 'high': None, 'removed': None, 'switch': None})},
    }


    def _sweep_label(who, at, how):
        k, dx = at if isinstance(at, tuple) else (at, SWEEP_DODGE)
        far = '' if dx == SWEEP_DODGE else f'东{dx:g}'
        return f'{WHO[who]}{how}{"不动" if k is None else k}{far}'


    def sweep_mission(build='engine_missile_sweep'):
        name, units, lanes = BUILDS[build]
        m = Mission(name=name, map=probe_range, units=units(), facts={})
        for lane, tpl in lanes.items():
            L, site = lane.title(), f'{lane} gun'
            m.put(tpl, site, side='p1', role=f'{lane} shooter', name=f'UNIT - CNV MslS {L} Shooter')
            m.put(TARGET_ID, site, 0, FAR, side='s1', role=f'{lane} target', name=f'UNIT - CNV MslS {L} Target')
            for dx in JUMPS:
                m.waypoint(f'{lane} jump {dx:g}', f'CNV MslS {L} Jump {dx:g}', site, dx, FAR)
            m.waypoint(f'{lane} drive', f'CNV MslS {L} Drive', site, DRIVE_TO, FAR)
        return m


    def _moved_test(m, lanes, at, how):
        """The targets are moved at `at[lane]` frames after the order: how = 'jump' (teleport) or 'drive' (move)."""
        t = Test()

        def n(part):
            return m.role(part).name

        targets = [n(f'{lane} target') for lane in lanes]
        shooters = [n(f'{lane} shooter') for lane in lanes]
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in targets + shooters]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s in shooters]
                                + [('NAMED_ATTACK_NAMED', n(f'{lane} shooter'), n(f'{lane} target')) for lane in lanes]
                                + [('SET_FLAG', 'Test Ordered', 1)]))
        t.scripts.append(Script('Test - tick', [('FLAG', 'Test Ordered', 1)], [('INCREMENT_COUNTER', 1, 'Test_Tick')],
                                once=False))
        for lane in lanes:
            L, tg, k = lane.title(), n(f'{lane} target'), at[lane]
            k, dx = k if isinstance(k, tuple) else (k, SWEEP_DODGE)      # (frames after the order, jump east)
            if k is not None:
                act = (('UNIT_TELEPORT_TO_WAYPOINT', tg, m.mark(f'{lane} jump {dx:g}')) if how == 'jump' else
                       ('MOVE_NAMED_UNIT_TO', tg, m.mark(f'{lane} drive')))
                t.scripts.append(Script(f'Test - move {L}', [('FLAG', 'Test Ordered', 1), ('COUNTER', 'Test_Tick', 3, k)],
                                        [act]))
            c = f'CNV_MslS_{L}'
            t.counters.append((c, _sweep_label(lanes[lane], at[lane], '跳' if how == 'jump' else '开')))
            t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
            t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                 [('INCREMENT_COUNTER', 1000, c)]) for j in range(1, LOST_MAX + 1)]
        first = next(iter(lanes))
        t.expect = [(_sweep_label(lanes[first], at[first], '跳' if how == 'jump' else '开'), 0, 'ever>=', 1,
                     SWEEP_RUN - 2)]
        t.bench = [('bench_watch', dict(seconds=SWEEP_RUN, every=1, sheet=False, lines=6))]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_missile': mission} | {b: (lambda b=b: sweep_mission(b)) for b in BUILDS}
    CHECKS = {'engine_missile': {'miss': missile_test, 'flight': flight_test}} | {
        b: {k: (lambda m, b=b, k=k: _moved_test(m, BUILDS[b][2], MOVES[b][k][1], MOVES[b][k][0])) for k in MOVES[b]}
        for b in BUILDS}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        FAR=FAR, LOST_MAX=LOST_MAX, ORDER=ORDER, SAGE=SAGE, TARGET_ID=TARGET_ID, V4=V4,
        V4_ROCKET=V4_ROCKET, V4_WEAPON=V4_WEAPON, _sub1=_sub1, home_v4=home_v4, target=target))


def engine_ocl():
    """Engine unit test: the Athena cannon's real damage (OCL strike: AlliedAntiStructureVehicle -> OCL_AthenaCannon ->
    a CannonEffect object that fires AthenaCannonWeapon after 0.1 s and again when it dies at 2 s).

    Niagara map, 'west field': a player Athena and an enemy (s1) Soviet advanced power plant (MaxHealth 4000,
    SovietAdvancedPowerPlantArmor -> BaseFactionStructureArmor: EXPLOSIVE 125 %), 300 apart (weapon range 200-500). One
    second in the Athena is ordered to attack it. Counters: 帧数 frames since Go, 血量 the building's health in percent
    (1 % = 40 hp).

    Read 2026-11-08 (`a`, PASS): first loss at frame 49; each round takes ~19 % (750 hp = ~600 raw) over ~30 frames (the
    effect's 2 s, a hit every frame), rounds start at frames 49 / 125 / 207 / 284 / 360 (~80 frames = ~5.3 s = pre-attack 2
    + firing 2 + reload 1.1). simunits.ocl_round gives 620 a round, the fight 121.6 raw/s (bench ~113).
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test

    ATHENA, BARRACKS = 'AlliedAntiStructureVehicle', 'SovietPowerPlantAdvanced'
    RUN = 40.0
    SITE = ('west field', -120.0, 260.0)


    def _n(p):
        return f'UNIT - CNV Ocl {p}'


    def mission():
        m = Mission(name='CampOcl', map=resources.measured(niagara), units=[], facts={})
        m.put(ATHENA, SITE[0], SITE[1], SITE[2], angle=0.0, role='athena', name=_n('Athena'))
        m.put(BARRACKS, SITE[0], SITE[1], SITE[2] + 300.0, side='s1', angle=0.0, role='barracks', name=_n('Barracks'))
        return m


    def ocl_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                                     ('UNIT_CHANGE_OBJECT_STATUS', _n('Barracks'), 'NO_ATTACK', 1),
                                                     ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                                [('NAMED_ATTACK_NAMED', _n('Athena'), _n('Barracks')), ('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)
        t.counters.append(('CNV_Ocl_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Ocl_Frames')], once=False))
        t.counters.append(('CNV_Ocl_Health', '血量'))
        t.scripts.append(Script('Test - health', [going], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', _n('Barracks'),
                                                            'CNV_Ocl_Health')], once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
        return t


    MISSION = {'engine_ocl': mission}
    CHECKS = {'engine_ocl': {'a': lambda m: ocl_test(m, 'a')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_oclone():
    """New bench PASS99/1/40/1; PREDICT before bench. Control1000HP Hammer takes10EXPLOSIVE.
    High gun has ONLY WeaponOCLNugget OCL_AthenaCannon, no markerDamageNugget.
    Retail OCL creates CannonEffect at target; Lifetime2s=30frames;
    FireWeaponNugget FireDelay0.1s ->ceil1.5=2frames; AthenaCannonWeapon20.
    GUESSED endpoint convention: loop fires frames2..30 inclusive=29 hits,
    FireWeaponWhenDead adds1, total600EXPLOSIVE. BaseTankArmor100% ->40%HP.
    Current simulator ignores FireDelay, predicts30 loop+1death=620 ->38%.
    Probe isolates the lifetime TOTAL, not effect per-frame timing or area geometry.
    Finite one clip loads1s, fire6s, NO_ATTACK6+4/15; four lines with alive.
    """
    import re
    from parts import Script
    laser = engine_laser()["shared"]
    laser_mission = laser.mission
    laser_check = laser.check

    def mission():
        m=laser_mission();m.name='CampOclOne'
        for u in m.units:
            if u.id=='CNV_LaserBase':
                u.xml=u.xml.replace('Damage="100"','Damage="10"')
            if u.id=='CNV_LaserHigh':
                u.xml=re.sub(r'<DamageNugget\b[^>]*/>','',u.xml)
                u.xml=re.sub(r'<ActivateLaserNugget\b[^>]*/>','<WeaponOCLNugget WeaponOCL="OCL_AthenaCannon"/>',u.xml)
        return m

    def check(m):
        t=laser_check(m)
        t.counters=[]
        for lane in ('base','high'):
            hp='CNV_Laser_'+lane+'HP';alive='CNV_OclOne_'+lane+'Alive';v='Laser '+lane+' target'
            t.counters.extend([(hp,lane+' HP'),(alive,lane+' alive')])
            t.scripts.extend([Script('Test - alive '+lane,[],[('SET_COUNTER',alive,1)],once=False),
                              Script('Test - dead '+lane,[('NAMED_DESTROYED',v)],[('SET_COUNTER',alive,0)],once=False)])
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(99,1,40,1))]
        return t
    MISSION={'engine_oclone':mission}
    CHECKS={'engine_oclone':{'a':check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_prism():
    """Engine unit test: why does the mirage tank fire ONE shot and stop (engine line C round 12; docs/engine/weaponset.md 4).
    Bench 11-09: a mirage tank told to attack a held Tsunami tank (380 hp, NO_ATTACK) hit it once (200 -> 47 % left) and never
    fired again for 40 s, though its cannon is a single shot (1.5 s firing, 0.1 s reload, auto) that should repeat every 1.6 s.
    The simulator fires on. Candidates: the cannon's OCL nugget makes a prism node object at the target that blocks the
    line of sight; the one attack order is spent by a clip (ReAcquireDetailType PER_CLIP); a Tsunami target in particular.

    On the range probe map, four lanes (the lane names are the map's; the counter bar holds four lines), each an attacker of
    the player's at '<lane> gun' and a Tsunami tank 100 north (the enemy's, NO_ATTACK, never answers):
      base     mirage    one attack order at ORDER        (the control: one shot expected)
      high     mirage    no order at all (auto-acquire)
      removed  guardian  one attack order                 (a plain cannon: keeps firing)
      low      mirage    the order given again every 3 s from ORDER (is a fresh order a fresh clip?)
    Counters: 基准血 / 自动血 / 守护血 / 重令血 -- the Tsunami's health in percent, every second.

    Bench 2026-11-09: 基准 / 自动 / 守护 / 重令 = s1 47 47 84 47, s2-3 47 47 68 47, s4-5 .. 52, s6-7 .. 36, s8-9 .. 21, s10-31
    47 47 5 47. The mirage tank fires once however it is aimed (an order, auto-acquire, a fresh order every 3 s), the guardian's
    plain cannon keeps firing at the same tank: the cause is in the prism cannon itself (docs/engine/weaponset.md 4).
    """
    from maps import probe_range
    from parts import Mission, Script, Test, counted

    CONSCRIPT, MIRAGE, GUARD, TANK = ('SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech3',
                                      'AlliedAntiVehicleVehicleTech1', 'JapanAntiVehicleVehicleTech1')
    LANES = {'base': (MIRAGE, TANK), 'high': (MIRAGE, TANK), 'removed': (GUARD, TANK), 'low': (MIRAGE, TANK)}
    ORDERED = ('base', 'removed')                   # one attack order; low: repeated; high: none
    ORDER, AGAIN, RUN = 3.0, 3.0, 30.0
    LABELS = (('Base', '基准血'), ('High', '自动血'), ('Removed', '守护血'), ('Low', '重令血'))


    def _n(lane, part):
        return f'UNIT - CNV Prism {lane.title()} {part}'


    def mission():
        m = Mission(name='CampPrism', map=probe_range, units=[], facts={})
        for lane, (gun, target) in LANES.items():
            m.put(gun, f'{lane} gun', side='p1', role=f'{lane} attacker', name=_n(lane, 'Man'))
            m.put(target, f'{lane} gun', 0.0, 100.0, side='s1', role=f'{lane} target', name=_n(lane, 'Tank'))
        return m


    def prism_test(m):
        t = Test()
        p1 = m.player('p1')
        targets = [_n(lane, 'Tank') for lane in LANES]
        t.scripts.append(Script('Test - start', [], [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1) for u in targets] + [
            ('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]))
        hit = lambda lane: ('NAMED_ATTACK_NAMED', _n(lane, 'Man'), _n(lane, 'Tank'))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [hit(lane) for lane in ORDERED] + [hit('low'), ('SET_MILLISECOND_TIMER', 'Test Again', AGAIN)]))
        t.scripts.append(Script('Test - again', [('TIMER_EXPIRED', 'Test Again')],
                                [hit('low'), ('SET_MILLISECOND_TIMER', 'Test Again', AGAIN)], once=False))
        for key, label in LABELS:
            counted(f'CNV_Prism_{key}Hp', label, t, health=_n(key, 'Tank'))
        t.expect = [('基准血', 0, 'ever<=', 99, RUN)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_prism': mission}
    CHECKS = {'engine_prism': {'a': prism_test}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_prismx():
    """Engine unit test: which part of the mirage tank's cannon stops it after one shot (engine line C round 13;
    docs/engine/weaponset.md 4; follows engine_prism). Bench 11-09: the mirage tank fires ONE shot at a held Tsunami tank
    and never again, however it is aimed; a guardian's plain cannon keeps firing. The cause is in the cannon's own data:
    the cannon (id ...Tech3PrismCannon in GlobalData/Weapon.xml) is a single shot, firing 1.5 s, reload 0.1 s, auto reload,
    ReAcquireDetailType PER_CLIP, flag ATTACK_NEEDS_LINE_OF_SIGHT, and its nuggets are: a laser (ActivateLaser, 1.5 s), an OCL
    (the prism node object at the target), the 200 damage (PRISM, delay 0.1 s) and a suppression (radius 20).

    Each lane is a CLONE of the mirage tank (CNV_PrismX<Variant>: its unit file with the id changed and its own copy of the
    cannon, id <unit>Weapon, swapped in the weapon slot) with ONE thing taken away (VARIANTS). Same lane rig as engine_prism:
    one attack order at ORDER on a held Tsunami tank 100 north (the enemy's, NO_ATTACK); counter = the tank's health in
    percent every second. Two runs, four variants each (idle variants are deleted at the start):
      a: ctrl (the clone unchanged: must repeat the one-shot or the clone is not faithful), ocl (no OCL nugget), los (no
         ATTACK_NEEDS_LINE_OF_SIGHT), fx (no laser nugget, no suppression nugget)
      b: dis (the unit's AI state machine is the plain UnitAIStateMachine, not the disguise-when-idle one), bare (ocl + los +
         fx all gone: damage only), reacq (ReAcquireDetailType PRE_FIRE), all (bare + dis + reacq)
    A lane that keeps firing drops the tank's health step by step (a Tsunami tank 380 hp, 200 a shot); the one-shot lanes stop
    at 47 %.

    Readings (bench 2026-11-09): runs a and b -- every lane, the control included, stops at 47 %: taking away the OCL nugget,
    the line-of-sight flag, the laser and suppression nuggets, ReAcquire PER_CLIP or the disguise-when-idle state machine (and
    all of them together) does not make the mirage tank fire again. Runs c, d (same day), health in % at s1-s34:
      tgt (Soviet Tech1 tank, 550 hp, the clone unchanged) 27; nodel / dtype / nofd (no 0.1 s damage delay / damage type EXPLOSIVE /
      firing duration 0) 47 47 47; clip3 / noaim / range 47 47 47; nomv (CanFireWhileMoving false) '?' (the counter unreadable
      from about s3 -- probably the Tsunami was KILLED; not yet confirmed).
    CASE CLOSED (run e, same day, health + alive counters on the ctrl and tgt lanes): s1 73 1 27 0, s2-s31 73 0 27 0 -- both
    targets are DEAD (alive 0) and their health counters stay at the last value read before death. There is no one-shot
    mystery: a health counter freezes when its object dies (engine line A r130 found the same). The mirage tank, the
    guardian and the rest fire on until the target is dead; nothing in the cannon stops it. The reading below is the
    first guess, kept for the record.
    First guess: Tsunami (380 hp) stops at 47 % = ~179 hp left = ONE 200 shot taken; the Soviet tank (550 hp) stops at 27 % = ~148 hp
    = TWO shots taken. Both stop with less health left than one shot deals (200), as engine_prism's guardian lane did (stopped at
    5 %, a shot of 16 %). So it looks like "no shot that would kill a held target" (or CanFireWhileMoving true holds the last
    shot), not a flaw of the prism cannon. Next: a high-hp target (does it fire on until < 200 left?), nomv over time, the
    guardian with CanFireWhileMoving toggled, a target not held (no NO_ATTACK).
    """
    import os
    import re

    from maps import probe_range
    from parts import Mission, Script, Test, Unit, counted
    missile = engine_missile()["shared"]
    SAGE = missile.SAGE
    _sub1 = missile._sub1

    MIRAGE, CANNON, TANK = 'AlliedAntiVehicleVehicleTech3', 'AlliedAntiVehicleVehicleTech3PrismCannon', 'JapanAntiVehicleVehicleTech1'
    ORDER, RUN = 3.0, 30.0
    LANES = ('base', 'high', 'removed', 'low')          # the range map's four lane sites
    # variant: (what is taken away from the weapon, whether from the unit (disguise machine) too, one line)
    VARIANTS = {
        'ctrl':  ((), False, '克隆原样（对照）'),
        'ocl':   (('ocl',), False, '去掉生棱镜节点的 OCL'),
        'los':   (('los',), False, '去掉需要直线视线'),
        'fx':    (('laser', 'supp'), False, '去掉激光和压制'),
        'dis':   ((), True, '单位 AI 状态机换成普通的（不伪装）'),
        'bare':  (('ocl', 'los', 'laser', 'supp'), False, '只剩伤害'),
        'reacq': (('reacq',), False, 'ReAcquire 改 PRE_FIRE'),
        'all':   (('ocl', 'los', 'laser', 'supp', 'reacq'), True, '全去掉 + 普通状态机'),
        # second pass: runs a and b all read 47 (the one shot), so the cause is not in those parts
        'tgt':   ((), False, '克隆原样，目标换成苏联 Tech1 坦克（480 血）'),
        'nodel': (('delay',), False, '伤害去掉 0.1 秒延迟'),
        'dtype': (('dtype',), False, '伤害类型 PRISM 改 EXPLOSIVE'),
        'nofd':  (('firing',), False, '开火持续 1.5 秒改 0'),
        'clip3': (('clip3',), False, '弹夹 3 发'),
        'noaim': (('aim',), False, '去掉 AcceptableAimDelta'),
        'nomv':  (('nomove',), False, 'CanFireWhileMoving 改 false'),
        'range': (('range',), False, '射程 125 改 300'),
    }
    RUNS = {'a': ('ctrl', 'ocl', 'los', 'fx'), 'b': ('dis', 'bare', 'reacq', 'all'),
            'c': ('tgt', 'nodel', 'dtype', 'nofd'), 'd': ('clip3', 'noaim', 'nomv', 'range'),
            'e': ('ctrl', 'tgt')}
    ALIVE = ('e',)              # runs that also count whether the target is still alive (health + alive per lane)
    TARGETS = {'tgt': 'SovietAntiVehicleVehicleTech1'}


    def _uid(k):
        return 'CNV_PrismX' + k.title()


    def _n(k, part):
        return f'UNIT - CNV PrismX {k.title()} {part}'


    def _strip(s, what):
        for w in what:
            if w == 'ocl':
                s, n = re.subn(r'\s*<WeaponOCLNugget\b[^>]*/>', '', s)
            elif w == 'laser':
                s, n = re.subn(r'\s*<ActivateLaserNugget\b[^>]*/>', '', s)
            elif w == 'supp':
                s, n = re.subn(r'\s*<SuppressionNugget\b[^>]*/>', '', s)
            elif w == 'los':
                s, n = s.replace('ATTACK_NEEDS_LINE_OF_SIGHT ', ''), 1
                assert 'ATTACK_NEEDS_LINE_OF_SIGHT' not in s
            elif w == 'delay':
                s, n = re.subn(r'\s*DelayTimeSeconds="0\.1s"', '', s)
            elif w == 'dtype':
                s, n = s.replace('DamageType="PRISM"', 'DamageType="EXPLOSIVE"'), 1
            elif w == 'firing':
                s, n = re.subn(r'(<FiringDuration\s+MinSeconds=")1\.5s("\s+MaxSeconds=")1\.5s"', r'\g<1>0s\g<2>0s"', s)
            elif w == 'clip3':
                s, n = re.subn(r'ClipSize="1"', 'ClipSize="3"', s)
            elif w == 'aim':
                s, n = re.subn(r'\s*AcceptableAimDelta="10d"', '', s)
            elif w == 'nomove':
                s, n = re.subn(r'CanFireWhileMoving="true"', 'CanFireWhileMoving="false"', s)
            elif w == 'range':
                s, n = re.subn(r'AttackRange="125\.0"', 'AttackRange="300.0"', s)
            elif w == 'reacq':
                s, n = s.replace('ReAcquireDetailType="PER_CLIP"', 'ReAcquireDetailType="PRE_FIRE"'), 1
            assert n == 1, (w, n)
        return s


    def prism_clone(k):
        what, plain_ai, line = VARIANTS[k]
        id, wid = _uid(k), _uid(k) + 'Weapon'
        x = open(os.path.join(SAGE, 'Allied', 'Units', MIRAGE + '.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{MIRAGE}"', f'id="{id}"')
        x = re.sub(rf'EditorName="{MIRAGE}"', f'EditorName="{id}"', x)
        x = _sub1(x, f'Template="{CANNON}"', f'Template="{wid}"')
        if plain_ai:
            x = _sub1(x, 'StateMachine="DisguiseWhenIdleAIStateMachine"', 'StateMachine="UnitAIStateMachine"')
        w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
        s = re.search(rf'\t*<WeaponTemplate\s+id="{CANNON}".*?</WeaponTemplate>\n', w, re.S).group(0)
        s = _sub1(s, f'id="{CANNON}"', f'id="{wid}"')
        s = _strip(s, what)
        x = _sub1(x, '</AssetDeclaration>', s + '</AssetDeclaration>')
        return Unit(id, x, link=[f'WeaponTemplate:{wid}'], names=dict(unit=id, weapon=wid),
                    what=f'幻影坦克克隆（探针）：{line}', params=dict(away=list(what), plain_ai=plain_ai))


    def mission():
        m = Mission(name='CampPrismX', map=probe_range, units=[prism_clone(k) for k in VARIANTS], facts={})
        placed = set()
        for run, ks in RUNS.items():
            for lane, k in zip(LANES, ks):
                if k in placed:                     # run e reuses ctrl and tgt: placed once
                    continue
                placed.add(k)
                m.put(_uid(k), f'{lane} gun', side='p1', role=f'prismx {k}', name=_n(k, 'Man'))
                m.put(TARGETS.get(k, TANK), f'{lane} gun', 0.0, 100.0, side='s1', role=f'prismx {k} target', name=_n(k, 'Tank'))
        return m


    def prismx_test(m, run):
        t = Test()
        p1 = m.player('p1')
        ks = RUNS[run]
        idle = [k for k in VARIANTS if k not in ks]
        start = [('NAMED_DELETE', _n(k, part)) for k in idle for part in ('Man', 'Tank')]
        start += [('UNIT_CHANGE_OBJECT_STATUS', _n(k, 'Tank'), 'NO_ATTACK', 1) for k in ks]
        start += [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('NAMED_ATTACK_NAMED', _n(k, 'Man'), _n(k, 'Tank')) for k in ks]))
        for k in ks:
            counted(f'CNV_PrismX_{k.title()}Hp', k, t, health=_n(k, 'Tank'))
            if run in ALIVE:                        # a dead target's health counter freezes at its last reading (engine line A r130)
                c = f'CNV_PrismX_{k.title()}Alive'
                t.counters.append((c, k + ' 活'))
                t.scripts += [Script(f'Test - {c} one', [], [('SET_COUNTER', c, 1)], once=False),
                              Script(f'Test - {c} dead', [('NAMED_DESTROYED', _n(k, 'Tank'))], [('SET_COUNTER', c, 0)], once=False)]
        t.expect = [(ks[0], 0, 'ever<=', 99, RUN)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_prismx': mission}
    CHECKS = {'engine_prismx': {run: (lambda m, run=run: prismx_test(m, run)) for run in RUNS}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_projectile():
    """Bench PASS7/95/11/95 (new finite burst, 11-10); PREDICT before bench: retail Hammer straight projectile MuzzleVelocity50
    units/frame at250/450 distance. ProjectileNugget resolves500 EXPLOSIVE
    warhead on10000HP Hammer (100% armor), 95% after one hit. Object fires
    atF1, script observes atF2; flight adds floor(distance/50)=5/9 frames.
    Collision/launch phase formula is INFERRED from prior engine_shot evidence;
    this new finite-burst probe rechecks it. Current sim has no flight:2/95/2/95.
    Only stationary targets, no splash, no scatter. Empty clip loads1s;
    order6s, NO_ATTACK6+4/15 stops before second clip. Four counters.
    """
    from maps import probe_range
    from parts import Mission,Script,Test
    from benches.weapon.target_effects.checks import engine_shot
    shot = engine_shot()["shared"]
    shell_v4 = shot.shell_v4
    SHELL = shot.SHELL
    missile = engine_missile()["shared"]
    target = missile.target
    TARGET_ID = missile.TARGET_ID

    def mission():
        u=shell_v4('CNV_Proj',reload=1.0)
        u.xml=u.xml.replace('ProjectileTemplate="CNV_ProjProjectile"',f'ProjectileTemplate="{SHELL}"')
        u.files={};u.also=[]
        m=Mission(name='CampProj',map=probe_range,units=[u,target()],facts={})
        for lane,d in (('base',250),('high',450)):
            m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='Proj '+lane+' gun')
            m.put(TARGET_ID,lane+' gun',0,d,side='s1',angle=4.7124,name='Proj '+lane+' target')
        return m

    def check(m):
        t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','Proj Fire',6.0),('SET_MILLISECOND_TIMER','Proj Stop',6.0+4/15)]
        fire=[];stop=[]
        for lane in ('base','high'):
            g='Proj '+lane+' gun';v='Proj '+lane+' target';c='CNV_Proj_'+lane
            start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
            fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
            t.counters.extend([(c,lane+' hit'),(c+'HP',lane+' HP')])
            t.scripts += [Script('Test - frame '+lane,[('FLAG','Proj Ordered',1),('UNIT_HEALTH',v,2,100)],[('INCREMENT_COUNTER',1,c)],once=False),
                          Script('Test - hp '+lane,[],[('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c+'HP')],once=False)]
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','Proj Fire')],fire+[('SET_FLAG','Proj Ordered',1)]))
        t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','Proj Stop')],stop))
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(7,95,11,95))]
        t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
        return t
    MISSION={'engine_projectile':mission}
    CHECKS={'engine_projectile':{'flight':check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_projupd():
    """E250: ProjectileUpdate (StraightLineProjectile) owns the shell's flight. engine_projectile's V4, one shell each
    at a Hammer 450 north: On the retail Hammer shell (copied), Off the copy without its ProjectileUpdate, Slow the copy
    at MuzzleVelocity 25. Counters: frames from the order while each target is untouched (hit), Slow's target health %.
    PREDICT: first hit 2 + floor(450 / v) frames after the order -- On 11, Slow 20 (95 %) -- and Off never lands
    (engine_bezier_e's rocket without BezierProjectile never did; host.straight_speed's NO_FLIGHT): still counting.
    Bench 11-25: 11 / never / 19 / 95 -- the shell hits at the target's edge (engine/combat/projectile.py REACH)."""
    import re
    from maps import probe_range
    from parts import Mission, Script, Test
    from benches.weapon.target_effects.checks import engine_shot
    shell_v4 = engine_shot()["shared"].shell_v4
    missile = engine_missile()["shared"]
    LANES = (('On', 'base'), ('Off', 'high'), ('Slow', 'order'))

    def gun(tag):
        u = shell_v4('CNVPU1' + tag, reload=1.0)
        f = u.names['projectile'] + '.xml'
        cut = {'Off': (r'\s*<ProjectileUpdate\b.*?</ProjectileUpdate>', ''), 'Slow': ('"50.0"', '"25.0"')}
        if tag in cut:
            u.files[f], k = re.subn(*cut[tag], u.files[f], flags=re.S)
            assert k == 1, (tag, k)
        return u

    def mission():
        m = Mission(name='CampProjUpd', map=probe_range, units=[gun(t) for t, _ in LANES] + [missile.target()])
        for tag, lane in LANES:
            m.put('CNVPU1' + tag, lane + ' gun', side='p1', angle=1.5708, name='PU1 ' + tag + ' gun')
            m.put(missile.TARGET_ID, lane + ' gun', 0, 450, side='s1', angle=4.7124, name='PU1 ' + tag + ' target')
        return m

    def check(m):
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'PU1 Fire', 6.0),
                 ('SET_MILLISECOND_TIMER', 'PU1 Stop', 6.0 + 4 / 15)]
        fire, stop = [], []
        for tag, _ in LANES:
            g, v = 'PU1 ' + tag + ' gun', 'PU1 ' + tag + ' target'
            start += [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in (g, v)]
            fire += [('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', g, v)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 1)]
            t.counters.append(('PU1' + tag, tag + ' hit'))
            t.scripts.append(Script('Test - frame ' + tag, [('FLAG', 'PU1 Ordered', 1), ('UNIT_HEALTH', v, 2, 100)],
                                    [('INCREMENT_COUNTER', 1, 'PU1' + tag)], once=False))
        t.counters.append(('PU1SlowHP', 'Slow HP'))
        t.scripts = [Script('Test - start', [], start),
                     Script('Test - fire', [('TIMER_EXPIRED', 'PU1 Fire')], fire + [('SET_FLAG', 'PU1 Ordered', 1)]),
                     *t.scripts, Script('Test - stop', [('TIMER_EXPIRED', 'PU1 Stop')], stop),
                     Script('Test - hp', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', 'PU1 Slow target', 'PU1SlowHP')],
                            once=False)]
        t.expect = [('On hit', 14, '==', 11, 16), ('Off hit', 14, '>', 100, 16), ('Slow hit', 14, '==', 19, 16),
                    ('Slow HP', 14, '==', 95, 16)]
        t.bench = [('bench_watch', dict(seconds=16.0, every=.5, sheet=False, lines=4))]
        return t
    MISSION = {'engine_projupd': mission}
    CHECKS = {'engine_projupd': {'a': check}}
    CONTROL_ARMS = {'engine_projupd': ('On', 'Off')}
    return dict(MISSION=MISSION, CHECKS=CHECKS, CONTROL_ARMS=CONTROL_ARMS)


@cache
def engine_range():
    """Engine unit tests: what an upgrade's RANGE attribute modifier does to a turret (docs/engine/upgrades.md; A8's swell,
    what A8's tide_gun relies on). On the probe map (maps/probe_range.py) six turrets of the probe's own (gun(): retail's
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
    import os

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit

    RETAIL_GUN = 'SovietBaseDefenseGround'
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


    def gun(id, high=2.0, low=0.6, vision=None):
        """The probe's own turret (ADR 0016 G5: an engine probe builds its units itself, not from units/): retail's
        sentry gun (SovietBaseDefenseGround) under `id`, its power-plant dependency dropped, with two OBJECT upgrades,
        names on / off: High = RANGE x`high` (and VISION x`vision` if given), Low = RANGE x`low`."""
        up_on, up_off = f'Upgrade_{id}_High', f'Upgrade_{id}_Low'
        mod_on, mod_off = f'AttributeModifier_{id}_High', f'AttributeModifier_{id}_Low'
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Structures', 'SovietBaseDefenseGround.xml'),
                 encoding='utf-8').read()
        sight = f'\n\t\t<Modifier Type="VISION" Value="{round(vision * 100)}%"/>' if vision else ''
        for old, new in ((f'id="{RETAIL_GUN}"', f'id="{id}"'), (f'EditorName="{RETAIL_GUN}"', f'EditorName="{id}"'),
                         ('<GameDependency>\n\t\t\t<RequiredObject>SovietPowerPlant</RequiredObject>\n\t\t</GameDependency>', ''),
                         ('<Behaviors>', (
                             f'<Behaviors>\n'
                             f'\t\t\t<AttributeModifierUpgrade id="ModuleTag_CNV_High" AttributeModifier="{mod_on}">\n'
                             f'\t\t\t\t<TriggeredBy>{up_on}</TriggeredBy>\n'
                             f'\t\t\t</AttributeModifierUpgrade>\n'
                             f'\t\t\t<AttributeModifierUpgrade id="ModuleTag_CNV_Low" AttributeModifier="{mod_off}">\n'
                             f'\t\t\t\t<TriggeredBy>{up_off}</TriggeredBy>\n'
                             f'\t\t\t</AttributeModifierUpgrade>'
                         )),
                         ('</AssetDeclaration>', (
                             f'\t<UpgradeTemplate id="{up_on}" Type="OBJECT"/>\n'
                             f'\t<UpgradeTemplate id="{up_off}" Type="OBJECT"/>\n'
                             f'\t<AttributeModifier id="{mod_on}" Category="NONE">\n'
                             f'\t\t<Modifier Type="RANGE" Value="{round(high * 100)}%"/>{sight}\n'
                             f'\t</AttributeModifier>\n'
                             f'\t<AttributeModifier id="{mod_off}" Category="NONE">\n'
                             f'\t\t<Modifier Type="RANGE" Value="{round(low * 100)}%"/>\n'
                             f'\t</AttributeModifier>\n'
                             f'</AssetDeclaration>'
                         ))):
            assert x.count(old) == 1, (old[:60], x.count(old))
            x = x.replace(old, new, 1)
        # two copies of one retail file in one mod would define its <Define> twice (BinaryAssetBuilder: Critical)
        x = x.replace('SOVIET_BASE_DEFENSE_GROUND_LOCAL_UNPACK_TIME', f'{id.upper()}_UNPACK_TIME')
        return Unit(id, x, link=[f'UpgradeTemplate:{up_on}', f'UpgradeTemplate:{up_off}', f'AttributeModifier:{mod_on}',
                                 f'AttributeModifier:{mod_off}'],
                    names={'on': up_on, 'off': up_off}, what='引擎探针：原版哨戒炮，两个升级各带射程修正',
                    params=dict(high=high, low=low, vision=vision))


    def mission(seen=False):
        units = [gun(GUN)]                                  # the control: RANGE alone
        if seen:
            units.append(gun(SEEN, vision=2.0))
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
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        gun=gun))


def engine_reorder():
    """Engine probe: does a unit walk when a script gives it the same order again every frame
    (benches/weapon/firing/scenes.py#engine_reorder; A4's Ghost King, devices/horn.py ghost_scripts).

    An enemy (s1) Athena-type tank is made at 1 s on the s1 crew 'Reo' at S; the player's named ice wall W stands 900
    north (out of range), the player's named NO_ATTACK tank T beside it, move point M 600 from S. Orders from 2 s:
      once   one m.order('attack', wall)                       (control)
      every  the whole m.order (UNIT_SET_TEAM + TEAM_ATTACK_NAMED) every frame
      bare   only TEAM_ATTACK_NAMED every frame
      tank   m.order('attack', tank) every frame
      move   m.order('move', M) every frame
      alt    attack the wall, then attack the tank, two scripts, every frame
      late   once at 2 s, from 6 s every frame again
    Counters: 起点 (within 100 of S), 中途 (within 150 of (0,0)), 近墙 (in the square of half-side 170 round (0,330)),
    墙血 (the wall's health; tank: 坦克血). bench_watch 25 s, every 1 s.
    RESULTS (bench 2026-11-07; bench s; counters 起点 中途 近墙 墙血; the check logs 2-s rows):
      S first tried at (0, -500): on the water's edge, the unit did not move for ANY order (even move), 起点 1 all 26 s:
        a blocked spot, not an order effect; S moved to (0, -400).
      once   起点 0 from s2; 中途 1 s4-s7; 近墙 1 from s8; 墙血 100 to s9, 96 at s10, -4 per 2 s, 64 at s26.
      every  (full order each frame): identical to once.
      bare   (TEAM_ATTACK_NAMED only each frame): identical to once.
      tank   起点 0 s2; 中途 s4-s7; 近墙 1 only at s8 (passes it), then 0 (the tank is outside the box, x 250);
             坦克血 100 to s9, 86 s10, -14 per 2 s, 3 at s22-s26. It walked and fired.
      move   起点 0 s2; 中途 s4-s7; 近墙 1 from s8 to the end (stops at M): it walked and stayed.
      alt    wall then tank each frame: 起点 0 s2; 中途 s4-s7; 近墙 1 only s8, then 0; 墙血 100 to the end: it walked
             (the last order of the frame, the tank, rules; the wall was never shot). Tank health not read in this run.
      late   once at 2 s, every frame from 6 s: identical to once (no stop at 6 s; 墙血 96 at s10, 64 at s26).
      Reading: re-giving the SAME order (or a different one) every frame does not stop a unit here: it walks and fires
      in all seven variants. So A4's King standing still is not caused by the every-frame re-order itself.

    Second round (bench 2026-11-07), A4's King on the bench: attacker = JapanAntiVehicleVehicleTech3 (KING), the 'g'
    variants the Athena tank. Offsets are from 'west field'; the mod names are CampRo + D1/De/Dg/U1/Ue/Ug (+ Frames).
     A. Detour (dt*): a row of 11 unnamed ice-wall blocks CNV_ReoBar (80 wide, step 70, x -420..250, one at 250, y 50,
        role 'bar'): the gap only east of x 290. Attack W (0, 500) from 2 s. Counters 起点 (100 round S), 绕口 (square
        120 round (380, 50)), 近墙 (Test Near), 墙血. bench_watch 45 s.
       dt1   once at 2 s       起点 1 s1-s2, 0 from s3; 绕口 1 s7-s10; 近墙 1 from s13; 墙血 100 to s15, 88 at s16, -12
                               per ~2 s, 6 from s30 to s46.
       dtev  every frame       起点 1 s1-s2; 绕口 1 s7-s10; 近墙 1 from s14; 墙血 100 to s15, 88 at s16, 6 from s31.
       dtevg every frame, Athena  起点 1 s1; 绕口 1 s6-s9; 近墙 1 from s11; 墙血 100 to s12, 96 at s13, -4 per ~2 s,
                               32 at s50 (the Athena is the weak shooter).
       All three went round the gap (绕口 1 for 3-4 s), stopped near the wall and fired; no difference between once and
       every frame.
     B. Turn (tu*): at 2 s a move order S to P; from 14 s the attack order on a new named wall W2 (CNV_ReoWall,
        'UNIT - CNV Reo Wall2'). Counters 起点, 在P (square 80 round P), 墙2血. bench_watch 35 s.
        First tried P (-300, -400), W2 (-300, -250), west as asked: both in the water west of the coast (preview), the
        unit never moved (起点 1 until s13), W2 not shot: a blocked spot, not an order effect. Moved EAST:
        P (200, -400), W2 (200, -250) (due north of P, the unit stands facing east, a 90 degree turn).
       tu1   once at 14 s      起点 0 from s2; 在P 1 from s3 to the end; 墙2血 100 to s13, 88 at s14, -12 per ~2 s,
                               6 from s26.
       tuev  every frame from 14 s   起点 0 from s2; 在P 1 from s3; 墙2血 100 to s13, 88 at s14, 6 from s29.
       tuevg every frame, Athena     起点 0 from s2; 在P 1 from s2; 墙2血 100 to s12, 96 at s13, -4 per ~2 s, 52 at s35.
       Reading: with the every-frame attack order, in these runs the unit (King and Athena) detoured round the barrier,
       or turned 90 degrees on the spot, and fired at the same time as with a single order (first damage within ~1-2 s
       of the target being in reach / the order); the wall health fell at the same rate once and every frame. This
       bench did not reproduce the A4 stand-still (bridge detour); the difference to A4 is not located here.
    """
    from parts import Script, Test, counted, square

    # same order as benches/weapon/firing/scenes.py#engine_reorder (architecture test G5: a check does not import missions)
    OLD = ('once', 'every', 'bare', 'tank', 'move', 'alt', 'late')
    DT = ('dt1', 'dtev', 'dtevg')
    TU = ('tu1', 'tuev', 'tuevg')
    VARIANTS = OLD + DT + TU
    WALL2 = 'UNIT - CNV Reo Wall2'
    KING, ATHENA = 'JapanAntiVehicleVehicleTech3', 'AlliedAntiVehicleVehicleTech1'
    ATK, WALL, TANK = 'UNIT - CNV Reo Atk', 'UNIT - CNV Reo Wall', 'UNIT - CNV Reo Tank'
    RUN = 25.0


    def frames_new(m, v):
        """dt* / tu* variants: the attacker is the Ghost King (g suffix: Athena tank)."""
        t = Test()
        p1 = m.player('p1')
        team = m.teams['Reo']
        kind = ATHENA if v.endswith('g') else KING
        every = v.endswith('ev') or v.endswith('evg')
        t.areas['Test Start'] = square(*m.point('s'), 100.0)
        t.areas['Test Near'] = square(*m.point('near'), 170.0)
        tgt = WALL2 if v in TU else WALL
        order = lambda kind_, target: m.order(kind_, [ATK], target, 's1', crew='Reo')
        attack_o = order('attack', tgt)
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)]
                                + [('SET_MILLISECOND_TIMER', 'Test Make', 1.0),
                                   ('SET_MILLISECOND_TIMER', 'Test Go', 14.0 if v in TU else 2.0)]
                                + ([('SET_MILLISECOND_TIMER', 'Test Walk', 2.0)] if v in TU else [])))
        t.scripts.append(Script('Test - make', [('TIMER_EXPIRED', 'Test Make')],
                                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ATK, kind, m.team('s1'), m.mark('s')),
                                 ('UNIT_SET_TEAM', ATK, team)]))
        if v in TU:
            t.scripts.append(Script('Test - walk', [('TIMER_EXPIRED', 'Test Walk')], order('move', m.mark('p'))))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Go')], attack_o, once=not every))
        counted('CNV_Reo_S', '起点', t, named=ATK, area='Test Start')
        if v in DT:
            t.areas['Test Gap'] = square(*m.point('gap'), 120.0)
            counted('CNV_Reo_G', '绕口', t, named=ATK, area='Test Gap')
            counted('CNV_Reo_N', '近墙', t, named=ATK, area='Test Near')
            counted('CNV_Reo_H', '墙血', t, health=WALL)
            run = 45.0
        else:
            t.areas['Test P'] = square(*m.point('p'), 80.0)
            counted('CNV_Reo_P', '在P', t, named=ATK, area='Test P')
            counted('CNV_Reo_H', '墙2血', t, health=WALL2)
            run = 35.0
        t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def frames(m):
        v = VARIANTS[m.facts['variant']]
        if v in DT or v in TU:
            return frames_new(m, v)
        t = Test()
        p1 = m.player('p1')
        team = m.teams['Reo']
        t.areas['Test Start'] = square(*m.point('s'), 100.0)
        t.areas['Test Mid'] = square(*m.point('mid'), 150.0)
        t.areas['Test Near'] = square(*m.point('near'), 170.0)
        full = lambda kind, target: m.order(kind, [ATK], target, 's1', crew='Reo')
        tgt = TANK if v == 'tank' else WALL
        wall_o, tank_o = full('attack', WALL), full('attack', TANK)
        timers = [('SET_MILLISECOND_TIMER', 'Test Make', 1.0), ('SET_MILLISECOND_TIMER', 'Test Go', 2.0)]
        if v == 'late':
            timers.append(('SET_MILLISECOND_TIMER', 'Test Late', 6.0))
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                                     ('UNIT_CHANGE_OBJECT_STATUS', TANK, 'NO_ATTACK', 1)] + timers))
        t.scripts.append(Script('Test - make', [('TIMER_EXPIRED', 'Test Make')],
                                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ATK, 'AlliedAntiVehicleVehicleTech1',
                                  m.team('s1'), m.mark('s')), ('UNIT_SET_TEAM', ATK, team)]))
        go = ('TIMER_EXPIRED', 'Test Go')
        if v == 'once':
            t.scripts.append(Script('Test - order', [go], wall_o))
        elif v == 'every':
            t.scripts.append(Script('Test - order', [go], wall_o, once=False))
        elif v == 'bare':
            t.scripts.append(Script('Test - order', [go], [wall_o[-1]], once=False))
        elif v == 'tank':
            t.scripts.append(Script('Test - order', [go], tank_o, once=False))
        elif v == 'move':
            t.scripts.append(Script('Test - order', [go], full('move', m.mark('m')), once=False))
        elif v == 'alt':
            t.scripts += [Script('Test - order wall', [go], wall_o, once=False),
                          Script('Test - order tank', [go], tank_o, once=False)]
        elif v == 'late':
            t.scripts += [Script('Test - order', [go], wall_o),
                          Script('Test - order again', [('TIMER_EXPIRED', 'Test Late')], wall_o, once=False)]
        counted('CNV_Reo_S', '起点', t, named=ATK, area='Test Start')
        counted('CNV_Reo_M', '中途', t, named=ATK, area='Test Mid')
        counted('CNV_Reo_N', '近墙', t, named=ATK, area='Test Near')
        counted('CNV_Reo_H', '坦克血' if v == 'tank' else '墙血', t, health=tgt)
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {f'reorder_{v}': {'frames': frames} for v in VARIANTS}
    return dict(CHECKS=CHECKS)


def engine_wfire():
    """Engine unit test: WeaponFireSpecialAbilityUpdate -- a unit's button fires its SpecialWeapon once (after UnpackTime,
    within StartAbilityRange of its target), then packs (PackTime). The three of our 9 levels' templates that are not ships
    or aircraft, one lane each on the probe range, every unit NO_ATTACK (no ordinary fire), all pressed at PRESS:
      yuri   (base lane)  Yuriko (JapanCommandoTech1), Command_PsyonicBlastSpecialPower (TargetType NONE): weapon
             JapanCommandoTech1PsyonicBlast, DamageNugget 500 SNIPER radius 250, DelayTimeSeconds 1 s, ENEMIES NEUTRALS;
             UnpackTime 0, PackTime 2 s, BUSY_DURING_PACK. Enemy conscripts 100 / 200 / 300 north of her. MOVE_AT after
             the press she is sent 300 south (again at AGAIN).
      snipe  (high / order lanes) Natasha (SovietCommandoTech1), Command_ActivatePilotSnipeSpecialPower on a named enemy
             Hammer (TargetType OBJECT): SovietCommandoPilotSnipeWeapon, ParalyzeNugget UNMANNED on an enemy VEHICLE;
             UnpackTime 2 s, StartAbilityRange 500. The high lane's Hammer 400 north (in range), the order lane's 700 north
             (she must walk 200 first).
      bark   (switch lane) a dog (AlliedScoutInfantry), Command_ActivateBarkSpecialPower: AlliedScoutInfantryBark,
             ParalyzeNugget EMP radius 100, 10 s, enemy INFANTRY; FreezeAfterTriggerDuration 2 s. Enemy conscripts 60 and
             150 north of it, both sent 300 further north MOVE_AT after the press; the dog sent 300 south then too.
    Counters, frames added from the press on (four lines):
      尤活   +1 a frame the 100 conscript lives, +1000 the 200 one, +1000000 the 300 one
      走帧   +1 a frame Yuriko stands within 30 of her start, +1000 a frame the dog does
      狙     +1 a frame s1 owns the near Hammer, +1000 the far one, +1000000 a frame Natasha (order lane) is in her start
      吠     +1 a frame the 60 conscript stands within 30 of its start, +1000 a frame the 150 one does

    Predictions from the data (15 logic frames a second): Yuriko's blast at the press + 1 s: the 100 / 200 conscripts die
    ~15 (尤活 15 / 15000 + run), the 300 one lives; she stands till ~45 (1 s firing + 2 s pack, BUSY_DURING_PACK). Natasha
    near: the Hammer s1's ~30 frames (UnpackTime 2 s) then neutral; far: she walks 200 (~?), then 30 more. Bark: the 60
    conscript stays ~150 frames (10 s EMP), the 150 one leaves at once; the dog stays ~30 (2 s freeze).

    Bench 11-11 (round 160, work/logs/a160_wfire_bench.log, PASS), 尤活 走帧 狙 吠 at the last reading:
      310016016 36039 8074031 15160 -- the 100 / 200 conscripts die at frame 16, the 300 one lives (as predicted, +1);
      Yuriko out of her square at 39, the dog at 36: both stand 30 (PackTime under BUSY_DURING_PACK / the freeze) and
      walk 30 in 6-9 frames; the near Hammer neutral at 31, the far one at 74 -- Natasha leaves at 8 and walks ~44
      frames at 60: till the Hammer's edge, not its centre, is 500 off (INFERRED); the bark holds the 60 conscript 160
      (10 s + its walk), the 150 one walks at 15. Simulator (frame clock): 331016016 35037 8075031 14159.
    """
    from maps import probe_range
    from parts import Mission, Script, Test, square

    PRESS, MOVE_AT, AGAIN, RUN = 2.0, 0.3, 5.0, 20.0
    YURI, NATASHA, DOG = 'JapanCommandoTech1', 'SovietCommandoTech1', 'AlliedScoutInfantry'
    CONSCRIPT, HAMMER = 'SovietAntiInfantryInfantry', 'SovietAntiVehicleVehicleTech1'
    BLAST, SNIPE, BARK = ('Command_PsyonicBlastSpecialPower', 'Command_ActivatePilotSnipeSpecialPower',
                          'Command_ActivateBarkSpecialPower')
    N = 'UNIT - CNV WF '


    def mission():
        m = Mission(name='CampWFire', map=probe_range, units=[], facts={})
        m.put(YURI, 'base gun', side='p1', name=N + 'Yuri')
        for d in (100, 200, 300):
            m.put(CONSCRIPT, 'base gun', 0, d, side='s1', name=N + f'Yc{d}')
        m.waypoint('yuri away', 'Test WF Yuri Away', 'base gun', 0, -300)
        m.put(NATASHA, 'high gun', side='p1', name=N + 'Nat near')
        m.put(HAMMER, 'high gun', 0, 400, side='s1', name=N + 'Ham near')
        m.put(NATASHA, 'order gun', side='p1', name=N + 'Nat far')
        m.put(HAMMER, 'order gun', 0, 700, side='s1', name=N + 'Ham far')
        m.put(DOG, 'switch gun', side='p1', name=N + 'Dog')
        for d in (60, 150):
            m.put(CONSCRIPT, 'switch gun', 0, d, side='s1', name=N + f'Dc{d}')
            m.waypoint(f'dog c{d} away', f'Test WF Dc{d} Away', 'switch gun', 0, d + 300)
        m.waypoint('dog away', 'Test WF Dog Away', 'switch gun', 0, -300)
        return m


    def frames(m):
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        names = [N + k for k in ('Yuri', 'Yc100', 'Yc200', 'Yc300', 'Nat near', 'Ham near', 'Nat far', 'Ham far', 'Dog',
                                 'Dc60', 'Dc150')]
        for k, key in (('Yuri', 'base gun'), ('Nat far', 'order gun'), ('Dog', 'switch gun')):
            t.areas[f'Test WF {k} Home'] = square(*m.site(key), 30.0)
        for d in (60, 150):
            t.areas[f'Test WF Dc{d} Home'] = square(*m.site('switch gun', 0, d), 30.0)
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)] +
                                [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in names] +
                                [('SET_MILLISECOND_TIMER', 'Test Press', PRESS),
                                 ('SET_MILLISECOND_TIMER', 'Test Move', PRESS + MOVE_AT),
                                 ('SET_MILLISECOND_TIMER', 'Test Again', PRESS + AGAIN)]))
        t.scripts.append(Script('Test - press', [('TIMER_EXPIRED', 'Test Press')], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', N + 'Yuri', BLAST),
            ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', N + 'Nat near', SNIPE, N + 'Ham near'),
            ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', N + 'Nat far', SNIPE, N + 'Ham far'),
            ('NAMED_USE_COMMANDBUTTON_ABILITY', N + 'Dog', BARK),
            ('SET_FLAG', 'Test Going', 1)]))
        moves = [('MOVE_NAMED_UNIT_TO', N + 'Yuri', m.mark('yuri away')), ('MOVE_NAMED_UNIT_TO', N + 'Dog', m.mark('dog away'))]
        t.scripts.append(Script('Test - move', [('TIMER_EXPIRED', 'Test Move')], moves + [
            ('MOVE_NAMED_UNIT_TO', N + f'Dc{d}', m.mark(f'dog c{d} away')) for d in (60, 150)]))
        t.scripts.append(Script('Test - again', [('TIMER_EXPIRED', 'Test Again')], moves))
        going = ('FLAG', 'Test Going', 1)

        def per_frame(counter, label, rows):
            t.counters.append((counter, label))
            t.scripts.extend(Script(f'Test - {counter} {k}', [going, cond], [('INCREMENT_COUNTER', step, counter)],
                                    once=False) for k, (cond, step) in enumerate(rows))

        per_frame('CNV_WF_Yuri', '尤活', [(('NAMED_NOT_DESTROYED', N + f'Yc{d}'), step)
                                         for d, step in ((100, 1), (200, 1000), (300, 1000000))])
        per_frame('CNV_WF_Stand', '走帧', [(('NAMED_INSIDE_AREA', N + 'Yuri', 'Test WF Yuri Home'), 1),
                                          (('NAMED_INSIDE_AREA', N + 'Dog', 'Test WF Dog Home'), 1000)])
        per_frame('CNV_WF_Snipe', '狙', [(('NAMED_OWNED_BY_PLAYER', s1, N + 'Ham near'), 1),
                                        (('NAMED_OWNED_BY_PLAYER', s1, N + 'Ham far'), 1000),
                                        (('NAMED_INSIDE_AREA', N + 'Nat far', 'Test WF Nat far Home'), 1000000)])
        per_frame('CNV_WF_Bark', '吠', [(('NAMED_INSIDE_AREA', N + f'Dc{d}', f'Test WF Dc{d} Home'), step)
                                       for d, step in ((60, 1), (150, 1000))])
        t.expect = [('尤活', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_wfire': mission}
    CHECKS = {'engine_wfire': {'all': frames}}      # mod CampWFireAll: 13 characters
    return dict(MISSION=MISSION, CHECKS=CHECKS)


BENCHES = (
    engine_acquire, engine_bezier_e, engine_charge_e, engine_circular,
    engine_clip, engine_cosmetic_e, engine_discharge_e, engine_dot,
    engine_emp, engine_empfire, engine_fire, engine_fireobjects,
    engine_fwcollide, engine_fwupdate, engine_grapple, engine_laser,
    engine_leechhealth, engine_leechpct, engine_missile, engine_ocl,
    engine_oclone, engine_prism, engine_prismx, engine_projectile, engine_projupd,
    engine_range, engine_reorder, engine_wfire,
)
