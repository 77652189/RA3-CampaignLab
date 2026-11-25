"""Weapon target effects checks and inline scenes."""
from functools import cache
from types import SimpleNamespace


def engine_inform():
    """InformTargetNugget (69 uses), next by usage: bounded damage isolation.
    PREDICT99/99 after100 marker,89/89 after1000,79/79 after second1000;
    both alive. Clone the already-benched attribute two-lane check, replacing
    ONLY the high lane modifier with retail's empty InformTargetNugget.
    The nugget schema has no damage amount. Simulator currently ignores it.
    This check ONLY isolates additional HP effects. Incoming-projectile AI
    response is NOT tested; do not promote whole-item coverage from this check.
    Empty initial clips load1s, order6s, each burst stopped byNO_ATTACK.
    """
    weaponfx = engine_weaponfx()["shared"]
    mission = weaponfx.mission
    check = weaponfx.check

    def damage_check(m):
        t=check(m,'attribute')
        for u in m.units:
            u.xml=u.xml.replace('<AttributeModifierNugget AttributeModifierName="AttributeMod_TargetPainted"/>','<InformTargetNugget/>')
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(79,1,79,1))]
        return t

    def make():
        m=mission();m.name='CampInfo';return m
    MISSION={'engine_inform':make}
    CHECKS={'engine_inform':{'damage':damage_check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


@cache
def engine_inform_ai():
    """InformTarget black box: second run PASS for the qualitative response.

    Observed automatic packed:1187051068/87135068/101003068/87135089.
    First damage frames87/87/1/87; first shield51/none/3/none.
    Actual health68/68/68/89: the side-facing miners take the native105% flank
    scalar (raw150/50, 500HP), rather than the nominal70/90 percent.
    The51->87 advance is2.4s, not exactly the original2s-window prediction;
    arrival estimation and micro phase remain unmodeled. PASS only means the
    broad before/after-hit controls below, not the original exact-window claim.
    Check ``off`` is the matched third-run ablation: only base's launching
    InformTargetNugget is removed; all other lanes and scripts stay unchanged.
    Original prediction: base loses its before-damage shield but can still
    react after damage (100M <= packed < 200M). Observed third run:
    87135068/87135068/101003068/87135089; base hit87, no shield through freeze.
    The no-advance prediction holds, but the extra post-hit prediction FAILS.
    Keep that failed expectation as evidence; do not silently tune it to PASS.
    This supports necessity in this recipe, not the exact arrival formula or
    the cause of the absent post-hit response. Do not promote whole coverage.

    PREDICTION before the first run:

    Retail SovietMiner: MaxHealth500, TrackIncomingWeaponFireBehavior,
    Toggle DEFENSE_SELF_ONLY, look-ahead/behind2s, damage fraction0.2.
    Create named retail miners at11s, AFTER the standard10s skirmish wake;
    transfer their AI at12s. The unit's TOGGLE command is MICRO_MANAGER too; the instant lane is the
    positive control for reaching its self-defense evaluator.
    Stationary miners (IMMOBILE, not NO_ATTACK) at450 distance; order20s,
    finite single shot, Hammer shell MuzzleVelocity5 units/frame => ~90frames.
    UNRESISTABLE150/500=30%, low50/500=10%. InformTarget is on the launching
    weapon, beside ProjectileNugget, as the retail Hammer cannon.

    Predict: AI high shields BEFORE damage within the last2s of flight;
    player high never auto-shields; AI instant can shield only AFTER damage;
    AI low never auto-shields. Instant's post-hit response is an AI positive
    control, not evidence of advance notification. A scripted press at40s
    checks the status detector separately, after automatic measurements end.

    Four counters: 1e9*shieldSeenBeforeDamage +1e8*shieldSeenAutomatically
    +1e6*framesUntilFirstDamage +1000*framesUntilFirstShield +HPpercent.
    After40s player/low manual-control sightings add1e9 as a separate bit.
    Frame counts start at the order and freeze at29s (never-seen sentinel).
    Damage/shield frame ordering uses script samples, not internal timings.
    Round2: WeaponSpeed75 matches MuzzleVelocity5*15, unlike round1
    WeaponSpeed999999. Fix the hit latch to UNIT_HEALTH comparison0 (<),
    not2 (==); delay manual controls beyond the automatic assertion window.
    Do not register InformTarget from a no-response or HP-only result.
    """
    import re

    from maps import probe_range
    from parts import Mission, Script, Test, status
    shot = engine_shot()["shared"]
    shell_v4 = shot.shell_v4
    shot_v4 = shot.shot_v4
    _nuggets = shot._nuggets

    MINER = 'SovietMiner'
    ARMOR = 'SPECIAL_ARMOR_ACTIVE'
    COMMAND = 'Command_ToggleArmorUp'
    LANES = ('base', 'high', 'order', 'removed')


    def mission():
        units = []
        for lane in LANES:
            damage = 50 if lane == 'removed' else 150
            uid = 'CNV_Info_' + lane
            if lane == 'order':
                u = shot_v4(uid, _nuggets(f'<DamageNugget Damage="{damage}" DamageType="UNRESISTABLE" DeathType="NORMAL"/>',
                                          '<InformTargetNugget/>'), reload=1)
            else:
                u = shell_v4(uid, damage=damage, reload=1)
                u.xml = u.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
                # Only the launch weapon gains InformTarget, never the warhead.
                u.xml = re.sub(r'(<ProjectileNugget[^>]*/>)', r'\1<InformTargetNugget/>', u.xml)
                u.files = {k: v.replace('MuzzleVelocity="50.0"', 'MuzzleVelocity="5.0"') for k, v in u.files.items()}
            units.append(u)
            if lane != 'order':
                u.xml = u.xml.replace('WeaponSpeed="999999"', 'WeaponSpeed="75"')
        m = Mission(name='CampInfoAI', map=probe_range, units=units,
                    facts={'wake at': 10.0, 'make at': 11.0, 'order at': 20.0, 'freeze at': 29.0})
        # Use B's proven wake actions; the miner's own toggle evaluator needs no Hunt team.
        m.put('AlliedConstructionYard', 'power 1', side='s1', name='Info AI Yard')
        m.waypoint('ai base', 'Info AI Base', 'power 1')
        for lane, u in zip(LANES, units):
            m.put(u.id, lane + ' gun', side='s1' if lane == 'high' else 'p1',
                  angle=1.5708, name='Info gun ' + lane)
            m.waypoint(lane + ' target', 'Info Target ' + lane, lane + ' gun', 0, 450)
        m.spawns.add(MINER)
        return m


    def check(m):
        t = Test()
        p, enemy = m.player('p1'), m.player('s1')
        start = [('MAP_REVEAL_ALL_PERM', p), ('PLAYER_SET_MONEY', enemy, 0)]
        start += [('SET_MILLISECOND_TIMER', 'Info ' + k, v) for k, v in
                  (('wake', 10.0), ('make', 11.0), ('transfer', 12.0), ('fire', 20.0),
                   ('stop', 20 + 4/15), ('freeze', 29.0), ('control', 40.0))]
        start += [('UNIT_CHANGE_OBJECT_STATUS', 'Info gun ' + lane, 'NO_ATTACK', 1) for lane in LANES]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - wake', [('TIMER_EXPIRED', 'Info wake')],
                               [('UNIT_AI_TRANSFER_ALL', enemy, 1), ('SKIRMISH_AI_MAKE_BASE', enemy, m.mark('ai base')),
                                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', enemy, 20),
                                ('SKIRMISH_AI_USE_REPAIRS', enemy, 0), ('SKIRMISH_AI_USE_REBUILD_SYSTEM', enemy, 0),
                                ('PLAYER_SET_MONEY', enemy, 0)]))
        make, fire, stop = [], [], []
        for lane in LANES:
            victim, gun = 'Info miner ' + lane, 'Info gun ' + lane
            c = 'CNV_Info_' + lane
            make += [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', victim, MINER, m.team('p1' if lane == 'high' else 's1'),
                      m.mark(lane + ' target')), ('UNIT_CHANGE_OBJECT_STATUS', victim, 'IMMOBILE', 1)]
            fire += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', gun, victim)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS', gun, 'NO_ATTACK', 1)]
            t.counters.append((c, lane + ' info'))
            active = [('FLAG', 'Info Ordered', 1), ('FLAG', 'Info Frozen', 0)]
            shield = ('UNIT_HAS_OBJECT_STATUS', victim, status(ARMOR))
            # Latch before incrementing first-observation clocks.
            t.scripts += [
                Script('Test - hit ' + lane, active + [('UNIT_HEALTH', victim, 0, 100)],
                       [('SET_FLAG', c + ' hit', 1)]),
                Script('Test - early shield ' + lane, active + [shield, ('FLAG', c + ' hit', 0)],
                       [('INCREMENT_COUNTER', 1000000000, c + ' state')]),
                Script('Test - shield ' + lane, active + [shield],
                       [('SET_FLAG', c + ' shield', 1), ('INCREMENT_COUNTER', 100000000, c + ' state')]),
                Script('Test - hit clock ' + lane, active + [('FLAG', c + ' hit', 0)],
                       [('INCREMENT_COUNTER', 1000000, c + ' state')], once=False),
                Script('Test - shield clock ' + lane, active + [('FLAG', c + ' shield', 0)],
                       [('INCREMENT_COUNTER', 1000, c + ' state')], once=False),
                Script('Test - display ' + lane, [], [('SET_COUNTER', c, 0),
                       ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, c),
                       ('COUNTER_MATH_COUNTER', c, 0, c + ' state')], once=False)]
        t.scripts += [Script('Test - make', [('TIMER_EXPIRED', 'Info make')], make),
                      Script('Test - transfer', [('TIMER_EXPIRED', 'Info transfer')], [('UNIT_AI_TRANSFER_ALL', enemy, 1)]),
                      Script('Test - fire', [('TIMER_EXPIRED', 'Info fire')], fire + [('SET_FLAG', 'Info Ordered', 1)]),
                      Script('Test - stop', [('TIMER_EXPIRED', 'Info stop')], stop),
                      Script('Test - freeze', [('TIMER_EXPIRED', 'Info freeze')], [('SET_FLAG', 'Info Frozen', 1)])]
        for lane in ('high', 'removed'):
            victim = 'Info miner ' + lane
            c = 'CNV_Info_' + lane
            t.scripts += [Script('Test - control press ' + lane, [('TIMER_EXPIRED', 'Info control')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', victim, COMMAND)]),
                          Script('Test - control seen ' + lane, [('FLAG', 'Info Frozen', 1),
                                 ('TIMER_EXPIRED', 'Info control'), ('FLAG', c + ' shield', 0),
                                 ('UNIT_HAS_OBJECT_STATUS', victim, status(ARMOR))],
                                 [('INCREMENT_COUNTER', 1000000000, c + ' state')])]
        # Early response is the distinguishing prediction; no exact first-shield phase presumed.
        t.expect = [('base info', 31.0, '>=', 1100000000, 34.0),
                    ('high info', 31.0, '<', 100000000, 34.0),
                    ('order info', 31.0, '>=', 100000000, 34.0),
                    ('order info', 31.0, '<', 110000000, 34.0),
                    ('removed info', 31.0, '<', 100000000, 34.0),
                    ('high info', 43, '>=', 1000000000), ('removed info', 43, '>=', 1000000000)]
        t.bench = [('bench_watch', dict(seconds=44, every=1, sheet=False, lines=4))]
        return t


    def check_without_inform(m):
        """Matched ablation; preserve the second run's three control lanes."""
        unit = m.units[LANES.index('base')]
        assert unit.xml.count('<InformTargetNugget/>') == 1
        unit.xml = unit.xml.replace('<InformTargetNugget/>', '', 1)
        t = check(m)
        t.expect = [('base info', 31.0, '>=', 100000000, 34.0),
                    ('base info', 31.0, '<', 200000000, 34.0)] + t.expect[1:]
        return t


    MISSION = {'engine_inform_ai': mission}
    CHECKS = {'engine_inform_ai': {'a': check, 'off': check_without_inform}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        COMMAND=COMMAND, LANES=LANES, MINER=MINER, check=check, check_without_inform=check_without_inform,
        mission=mission))


def engine_inform_expiry():
    """InformTarget natural expiry, independent of actual projectile arrival.

    Before bench: preserve engine_inform_probe's shell velocity, positions and
    scripts. Change only WeaponSpeed75 ->750 (base) /7500 (low damage lane).
    At the previous launch302, predict (hit, expiry)=(309,313)/(302,304),
    versus default player control (377,404). Actual shells still hit389.
    INFERRED before measurement: retain through expiry, remove strictly after;
    the read-only incoming log decides cleanup timing, counters only check HP.
    Full placement/flight/AI replay and damage history remain outside this slice.

    Measured a: deadlines313/304, physical removals336/312; b: deadlines303/317,
    physical removals336/320. Shared periodic sweep prediction was falsified.
    Only launch tuples replay green; autonomous cleanup remains strict xfail.
    The first wall-clock HP window failed before logical fire; kept unchanged.
    Two-run budget exhausted; see work/re/c_inform_expiry_report.md.
    """
    inform = engine_inform_ai()["shared"]
    probe = engine_inform_probe()["shared"]


    def mission():
        m = probe.mission()
        m.name = 'CampIExp'
        return m


    def check(m):
        for lane, speed in (('base', 750), ('removed', 7500)):
            unit = m.units[inform.LANES.index(lane)]
            assert unit.xml.count('WeaponSpeed="75"') == 1
            unit.xml = unit.xml.replace('WeaponSpeed="75"', f'WeaponSpeed="{speed}"', 1)
        t = probe._probed(m, inform.check(m))
        # Keep the original firing/control actions. Display raw HP rather than
        # the automatic-shield latches, whose timing is not this experiment.
        for script in t.scripts:
            if script.name.startswith('Test - display '):
                script.do = script.do[:2]
        t.expect = [(lane + ' info', 31, '==', hp, 34)
                    for lane, hp in zip(inform.LANES, (68, 68, 68, 89))]
        return t


    def crossed_deadlines(m):
        """Second discriminator: move deadlines across the observed cleanup frames.

        Prediction: base hit302/expiry303, low hit302/expiry317. If cleanup
        is a shared periodic sweep (INFERRED), removals swap to312/336.
        No wall-clock HP assertion: first a's s31 window preceded logical fire
        under load; preserve that failed prediction, judge the frame log instead.
        """
        t = check(m)
        for lane, factors in (('base', 'MinTimeToImpactFudgeFactor=".01" MaxTimeToImpactFudgeFactor=".1"'),
                              ('removed', 'MaxTimeToImpactFudgeFactor="16"')):
            unit = m.units[inform.LANES.index(lane)]
            assert unit.xml.count('<InformTargetNugget/>') == 1
            unit.xml = unit.xml.replace('<InformTargetNugget/>', f'<InformTargetNugget {factors}/>')
        t.expect = []
        return t


    MISSION = {'engine_inform_expiry': mission}
    CHECKS = {'engine_inform_expiry': {'a': check, 'b': crossed_deadlines}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_inform_max():
    """C line: change only base's InformTarget Max factor from 1.15 to 1.6.

    Prediction before running: same slow shell, damage150, launch302, hit377,
    actual damage/removal389 and automatic shield before damage. Default high/low
    controls keep expiry404; base expiry becomes444 (launch +142).
    The previous hit377/expiry404 constrain t to [75/.85, 102/1.15),
    so int(t*1.6+.99) is142 throughout that interval. No fitted distance needed.
    Expiry is the entry's recorded deadline; damage removes it before that time,
    so this check does not measure the exact automatic expiry-cleanup boundary.
    Reuse D's read-only probe without changing injection or the AI recipe.

    First run: incoming frames exactly matched; automatic controls all passed.
    Inherited manual assertions at43s failed at the first sample, then passed
    from44s onward. Preserve that FAIL in work/logs/c_inform_max_first_result.json;
    only the manual observation window moves to45s, with game scripts unchanged.
    """
    inform = engine_inform_ai()["shared"]
    probe = engine_inform_probe()["shared"]


    def mission():
        m = probe.mission()
        m.name = 'CampIMax'
        return m


    def check(m):
        unit = m.units[inform.LANES.index('base')]
        assert unit.xml.count('<InformTargetNugget/>') == 1
        unit.xml = unit.xml.replace('<InformTargetNugget/>',
                                    '<InformTargetNugget MaxTimeToImpactFudgeFactor="1.6"/>', 1)
        t = probe._probed(m, inform.check(m))
        t.expect = [(row[0], 45, *row[2:]) if row[1] == 43 else row for row in t.expect]
        return t


    MISSION = {'engine_inform_max': mission}
    CHECKS = {'engine_inform_max': {'a': check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


@cache
def engine_inform_probe():
    """Engine line D, round 35 (ADR 0027/0028): C line's InformTarget AI recipe with ra3ext's read-only probe on the miners.

    benches/weapon/target_effects/checks.py#engine_inform_ai (C line's check, not changed here) fires slow single shells with InformTargetNugget at AI miners
    (SovietMiner: TrackIncomingWeaponFireBehavior, self-defence look-ahead 2 s, fraction 0.2) and sees only when the
    armour goes up. This mission is the same one -- its mission() and check() are called as they are -- with two changes:
    the miners the scripts create are a copy CNV_InfoProbeMiner with one more module,
    `<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames=EVERY MaxFrames=LINES/>`, and the mission is built with ext=True.
    ra3ext's CNVProbe then logs, besides its usual probe line, an `incoming` line every time the miner's
    TrackIncomingWeaponFireBehavior list changes: each entry's source id, predicted damage, predicted impact frame and
    expiry frame (handoff-d round 35). The probe only reads, so C line's expectations are kept: the counters must equal
    C line's readings. The impact frame is read off ra3ext.log, not asserted.
    """
    import os

    import labpaths
    from parts import Unit
    inform = engine_inform_ai()["shared"]

    MINER, PROBE = inform.MINER, 'CNV_InfoProbeMiner'
    EVERY, LINES = 150, 3000


    def probe_miner():
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', MINER + '.xml'), encoding='utf-8') as f:
            x = f.read()
        assert x.count(f'id="{MINER}"') == 1 and x.count('<Behaviors>') == 1
        # the retail file also holds SovietMiner_Naval (inherits SovietMiner): drop it, the copy keeps only the miner
        first = x.index('</GameObject>') + len('</GameObject>')
        x = x[:first] + '\n' + x[x.index('</AssetDeclaration>'):]
        assert 'SovietMiner_Naval' not in x
        x = x.replace(f'id="{MINER}"', f'id="{PROBE}"', 1).replace(f'EditorName="{MINER}"', f'EditorName="{PROBE}"')
        x = x.replace('<Behaviors>', (
            f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'
        ), 1)
        return Unit(PROBE, x, names=dict(unit=PROBE),
                    what='原版矿车的复制（探针）：多一个 ra3ext 的 CNVProbe 模块，记 TrackIncomingWeaponFire 的来弹表',
                    params=dict(of=MINER, every=EVERY, lines=LINES))


    def mission():
        m = inform.mission()
        m.name, m.ext = 'CampIP', True     # + the check's name stays <= 15 (CampIPA, CampIPOff)
        m.spawns.discard(MINER)
        m.spawns.add(PROBE)
        return m


    def _probed(m, t):
        m.units.append(probe_miner())
        for s in t.scripts:
            s.do = [tuple(PROBE if v == MINER else v for v in a) for a in s.do]
        return t


    def check(m):
        return _probed(m, inform.check(m))


    def check_off(m):
        return _probed(m, inform.check_without_inform(m))


    MISSION = {'engine_inform_probe': mission}
    CHECKS = {'engine_inform_probe': {'a': check, 'off': check_off}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        PROBE=PROBE, _probed=_probed, mission=mission))


def engine_inform_radius():
    """InformTarget radius discriminator using the existing read-only incoming probe.

    Before bench: radius200 (base, instant order) should notify the primary and
    the neighbour80 away, not the neighbour320 away (INFERRED). Default radius0
    (high) should notify only its primary; removed has no launch notification.
    Only InformTarget changes; projectile/warhead damage remains single-target.
    Read incoming rows at launch, not HP or shield as a proxy for notification.
    No wall-clock expectations: retain all logical-frame observations privately.
    """
    inform = engine_inform_ai()["shared"]
    probe = engine_inform_probe()["shared"]


    def mission():
        m = probe.mission()
        m.name = 'CampIRad'
        for lane in inform.LANES:
            for label, offset in (('near', 80), ('far', 320)):
                m.waypoint(lane + ' ' + label, 'Info ' + lane + ' ' + label,
                           lane + ' gun', offset, 450)
        return m


    def check(m):
        for lane in ('base', 'order', 'removed'):
            unit = m.units[inform.LANES.index(lane)]
            assert unit.xml.count('<InformTargetNugget/>') == 1
            nugget = '' if lane == 'removed' else '<InformTargetNugget Radius="200"/>'
            unit.xml = unit.xml.replace('<InformTargetNugget/>', nugget, 1)
        t = probe._probed(m, inform.check(m))
        make = next(s for s in t.scripts if s.name == 'Test - make')
        for lane in inform.LANES:
            for label in ('near', 'far'):
                name = 'Info ' + lane + ' ' + label
                make.do += [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', name, probe.PROBE,
                             m.team('p1' if lane == 'high' else 's1'), m.mark(lane + ' ' + label)),
                            ('UNIT_CHANGE_OBJECT_STATUS', name, 'IMMOBILE', 1)]
        # Counter remains a health control, independent of notification assertions.
        for script in t.scripts:
            if script.name.startswith('Test - display '):
                script.do = script.do[:2]
        t.expect = []
        return t


    def swapped(m):
        """Second run: move radius200 from base/order to the player high lane.

        Predict launch302: base/order primary only; high primary+near, far none;
        removed remains empty. Timing/damage still follows the primary shot.
        """
        t = check(m)
        for lane in ('base', 'order'):
            unit = m.units[inform.LANES.index(lane)]
            unit.xml = unit.xml.replace('<InformTargetNugget Radius="200"/>', '<InformTargetNugget/>')
        unit = m.units[inform.LANES.index('high')]
        unit.xml = unit.xml.replace('<InformTargetNugget/>', '<InformTargetNugget Radius="200"/>', 1)
        return t


    MISSION = {'engine_inform_radius': mission}
    CHECKS = {'engine_inform_radius': {'a': check, 'b': swapped}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_scatter():
    """Engine unit test: the scatter (ADR 0019 layer 3, queue 3; docs/engine/weapons.md) -- how often a scattering shot
    still hits its victim, by ScatterRadius.

    Four of engine_shot's shell V4s (retail's Hammer shell, its warhead one radius-0 DamageNugget of HIT: 1 % of
    engine_missile's 10 000-health Hammer, from the front), each with its own ScatterRadius (RADII) and a reload of
    RELOAD s instead of 4.5-5.5, each at its own Hammer AT north (the Hammer faces south, the map's default for s1).
    Ordered at ORDER (every clip loaded), they fire for RUN - ORDER s. Counter per lane: percent lost (one per hit, the
    step counted once begun). Lane 0 (no scatter) hits every shot, so it counts the shots for all four (same timers).

    What it tells apart (the shot aims at a point within R of the Hammer's centre):
      the radius uniform in [0, R] (Generals Weapon.cpp 1004-1010)  hit share falls like 1 / R
      uniform over the disc                                         like 1 / R^2
      the shell detonating on the Hammer on its way to a point beyond it (collision) raises the share on every lane.

    Bench 11-05 (round 34, CampScatterHits_mcp_1105_170642): 51 shots in the run; R 0 / 30 / 60 / 120 hit 51 / 34 / 19 /
    4, and CampScatterHits_mcp_1105_171950 the same to the second (the game's draws are fixed). The counter is one more
    than the hits (the first step is true at full health): 50 shots, 66 / 36 / 6 %. Held against the model (round 35,
    RA3-EngineModel tests/test_scatter.py): the radius uniform in [0, R] on the shooter's half, the point inside the
    Hammer's 20 x 14 box -- expected 62 / 31 / 16 %, within 3 sigma of all three.
    """
    from maps import probe_range
    from parts import Mission, Script, Test
    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    LOST_MAX = missile.LOST_MAX
    TARGET_ID = missile.TARGET_ID
    target = missile.target
    shell_v4 = engine_shot()["shared"].shell_v4

    ORDER, RUN = 6.0, 30.0
    RADII = (0.0, 30.0, 60.0, 120.0)
    HIT, RELOAD, AT = 100.0, 0.5, 250.0
    LANES = ('base', 'high', 'removed', 'switch')


    def _id(r):
        return f'CNV_Scat{r:g}'


    def units():
        return [shell_v4(_id(r), damage=HIT, scatter=r, reload=RELOAD,
                         what=f'散布 V4（探针）：锤子炮弹、弹头半径 0、{HIT:g} 伤害，ScatterRadius {r:g}，'
                              f'装填 {RELOAD:g} 秒，无预瞄、无开火持续')
                for r in RADII] + [target()]


    def mission():
        m = Mission(name='CampScatter', map=probe_range, units=units(), facts={})
        for r, lane in zip(RADII, LANES):
            m.put(_id(r), f'{lane} gun', side='p1', role=f'scatter {r:g} shooter', name=f'UNIT - CNV Scat {r:g} Shooter')
            m.put(TARGET_ID, f'{lane} gun', 0, AT, side='s1', role=f'scatter {r:g} target',
                  name=f'UNIT - CNV Scat {r:g} Target')
        m.spawns |= {_id(r) + 'Projectile' for r in RADII}
        return m


    def scatter_test(m):
        t = Test()
        pairs = [(m.role(f'scatter {r:g} shooter').name, m.role(f'scatter {r:g} target').name) for r in RADII]
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for p in pairs for x in p]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s, _ in pairs]
                                + [('NAMED_ATTACK_NAMED', s, tg) for s, tg in pairs]))
        for k, (r, (_, tg)) in enumerate(zip(RADII, pairs)):
            c = f'CNV_Scat_{k}'
            t.counters.append((c, f'r{r:g}'))
            t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                 [('INCREMENT_COUNTER', 1, c)]) for j in range(1, LOST_MAX + 1)]
        t.expect = [('r0', 0, 'ever>=', 10, RUN - 1)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=6))]
        return t


    CYCLES = 40


    def cycle_test(m):
        """The 0.5 s reload's shot-to-shot cycle, by the game's own frames (the watch's seconds are wall clock x rate,
        so a count at 's30' is not at the mission's 30 s): R 0's target loses 1 % a hit, and 帧数 counts the frames
        from the first hit (health below 100 %) to the (CYCLES + 1)th (below 100 - CYCLES %) = CYCLES cycles."""
        t = Test()
        s, tg = m.role('scatter 0 shooter').name, m.role('scatter 0 target').name
        others = [m.role(f'scatter {r:g} shooter').name for r in RADII[1:]]
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in [s, tg] + others]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', s, tg)]))
        t.counters.append(('CNV_Scat_0', 'r0'))
        t.scripts += [Script(f'Test - CNV_Scat_0 lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                             [('INCREMENT_COUNTER', 1, 'CNV_Scat_0')]) for j in range(1, LOST_MAX + 1)]
        t.counters.append(('CNV_Scat_F', '帧数'))
        t.scripts.append(Script('Test - CNV_Scat_F', [('UNIT_HEALTH', tg, 0, 100), ('UNIT_HEALTH', tg, 3, 100 - CYCLES)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Scat_F')], once=False))
        t.expect = [('帧数', 0, 'ever>=', CYCLES * 6, RUN - 1)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=2))]
        return t


    SPANS = ((1, 5), (5, 11), (11, 21), (21, 41))


    def spans_test(m):
        """cycle_test's frames cut into SPANS: counter k counts the frames from hit a to hit b (health in
        [100 - b + 1, 100 - a] %), i.e. b - a cycles -- where the shorter cycles fall.

        Read (11-05): cyc CampScatterCyc_mcp_1105_205319 帧数 316 (hits 1 -> 41); span CampScatterSpan_mcp_1105_205644
        28 / 48 / 80 / 160: from hit 5 on every cycle is 8 frames (0.5 s -> ceil 7.5), the first four after the attack
        starts 7. Round 35's '50 shots in 24 s' read the watch's seconds (wall clock x rate) as mission time."""
        t = cycle_test(m)
        t.counters, t.scripts = [], [x for x in t.scripts if not x.name.startswith('Test - CNV_Scat_')]
        tg = m.role('scatter 0 target').name
        for k, (a, b) in enumerate(SPANS):
            c = f'CNV_Scat_S{k}'
            t.counters.append((c, f'{a}-{b}'))
            t.scripts.append(Script(f'Test - {c}', [('UNIT_HEALTH', tg, 0, 100 - a + 1), ('UNIT_HEALTH', tg, 3, 100 - b + 1)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
        t.expect = [(f'{a}-{b}', 0, 'ever>=', (b - a) * 6, RUN - 1) for a, b in SPANS]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(SPANS)))]
        return t


    MISSION = {'engine_scatter': mission}
    CHECKS = {'engine_scatter': {'hits': scatter_test, 'cyc': cycle_test, 'span': spans_test}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_secondary():
    """New bench PASS1099/0/1099/1; PREDICT before bench: packedHP+alive then frozen, control and high.
    Two1000HP Hammer targets each take one10UNRESISTABLE marker. Only high
    gets SecondaryDamageNugget Amount2000=MAX_SECONDARY_DAMAGE_SCALER200%
    of1000. BaseVehicle fraction1.0 freezes; DissipateAmount25/UpdateDuration1s.
    Even10s later cold>=2000-10*25=1750>1000, so frozen through final14..16s.
    Marker UNRESISTABLE bypasses frozen armor, so both HP99 and alive1.
    Single2000 dose deliberately exposes wrong continuous-DPS delivery: pre-fix
    sim averaged2000 over17/15s clip, applies about0.5s before NO_ATTACK,
    less than1000 cold, predicts1099/0/1099/0. Do not raise dose to hide this.
    This validates secondary-vs-HP channel and single-hit delivery, NOT first
    freeze phase, melt/recovery frames, splash or upgrades. Existing per-frame
    melt approximation remains GUESSED. Empty clip loads1s, fire6s, stop6+4/15.
    """
    from maps import probe_range
    from model import status
    from parts import Mission,Script,Test
    gun = engine_weaponfx()["shared"].gun
    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    target = missile.target
    TARGET_ID = missile.TARGET_ID

    def mission():
        m=Mission(name='CampSD',map=probe_range,units=[target(health=1000)],facts={})
        for lane in ('base','high'):
            effect='<SecondaryDamageNugget Amount="2000"/>' if lane=='high' else ''
            u=gun('CNV_SD'+lane.title(),10,effect)
            u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
            m.units.append(u)
            m.put(u.id,lane+' gun',side='p1',angle=1.5708,name='SD '+lane+' gun')
            m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name='SD '+lane+' tank')
        return m

    def check(m):
        t=Test();start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','SD Fire',6.0),('SET_MILLISECOND_TIMER','SD Stop',6.0+4/15)]
        fire=[];stop=[]
        for lane in ('base','high'):
            g='SD '+lane+' gun';v='SD '+lane+' tank';hp='CNV_SD_'+lane+'HP';cold='CNV_SD_'+lane+'Frozen'
            start += [('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)]
            fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
            t.counters.extend([(hp,lane+' aliveHP'),(cold,lane+' frozen')])
            t.scripts += [Script('Test - hp '+lane,[],[('SET_COUNTER',hp,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,hp),('SET_COUNTER',cold,0)],once=False),
                          Script('Test - alive '+lane,[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,hp)],once=False),
                          Script('Test - frozen '+lane,[('UNIT_HAS_OBJECT_STATUS',v,status('UNDER_FROZEN'))],[('SET_COUNTER',cold,1)],once=False)]
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts.insert(1,Script('Test - fire',[('TIMER_EXPIRED','SD Fire')],fire))
        t.scripts.append(Script('Test - stop',[('TIMER_EXPIRED','SD Stop')],stop))
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(1099,0,1099,1))]
        t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
        return t
    MISSION={'engine_secondary':mission}
    CHECKS={'engine_secondary':{'single':check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


@cache
def engine_shot():
    """Engine unit test: how the shot reaches the target (ADR 0019 layer 3, batch two; docs/engine/weapons.md) -- an
    instant weapon's WeaponSpeed, a straight-line shell (ProjectileUpdate StateMachine="StraightLineProjectile", the
    tanks'), a laser (ActivateLaserNugget beside a DamageNugget) -- and the splash taper (DamageTaperOff).

    Every shooter is engine_fire's V4 with both timers 0 (pre-attack and FiringDuration: copy I00) and no scatter; only
    the nuggets and WeaponSpeed differ. The order comes at ORDER = 6 s, when every clip is loaded (the first clip is
    reloaded from the frame the unit is made, at most 83 frames: docs/engine/weapons.md 0), so the first hit's frame
    is one constant C plus the way to the target, the same on every lane:

      base     instant, WeaponSpeed 999999            C (engine_fire late's cells without a pre-attack)
      high     instant, WeaponSpeed SLOW              C + the 3D distance / (SLOW / 15)
      removed  retail's Hammer shell (MuzzleVelocity 50), its warhead one radius-0 DamageNugget of 500
      switch   a laser (retail's LockDown laser nugget) and a DamageNugget of 500, WeaponSpeed 999999

    The target is engine_missile's 10 000-health Hammer FAR north (a hit is 5 %); counters as there: frames from the
    order to the first hit + 1000 per percent lost.

    splash (lane low, check splash; the lanes above are check way): one more I00 V4 whose nugget is Damage SPLASH_DAMAGE, Radius 100, DamageTaperOff 20; its target
    NEAR north, three more of the same Hammers SPLASH_AT east of it (the last outside the radius). Counter per Hammer:
    percent lost (1 per percent).

    Bench 11-05 (round 30, docs/engine/weapons.md 2):

      way     instant 2, slow 2, shell 11, laser 2 frames after the order; every lane 5 % a hit. WeaponSpeed does not
              delay an instant weapon; the laser neither delays nor deals damage; the radius-0 shell hits its victim and
              lands 9 frames after the instant shot (the model: 11). C = 2 (engine_fire late agrees; the model: 1).
      splash  first shot: 0 / 40 / 80 / 120 east lose 20 / 17 / 9 / 0 %. The taper goes by the distance less the
              Hammer's bounding circle (40 and 80 fit it; by the bare distance 40 would lose 12 %), but the Hammer at
              120 -- beyond Radius by its centre, within it less the circle -- is spared (the model gives it 2 %).
              From the fourth shot on splash0 stops gaining and the others gain 9 each: not read (the Hammers pushed
              apart?); only the first shot is used.

    shells (round 32; the order lane): four CNV_ShotReach -- the shell V4 with AttackRange SHELLS_REACH -- each at its
    own Hammer SHELLS_AT north; counters as in way. Bench 11-05: 250 / 350 / 450 / 550 read 7 / 9 / 11 / 13 = 2 +
    floor(d / 50): the distance alone, 1 / MuzzleVelocity a unit, no launch offset (the model before read 9 / 11 / 13 /
    15; now Idle leaves at the launch and the move ending in the victim detonates, INFERRED collision).

    The splash 120 Hammer (round 33): the radius takes by the shape (the default PartitionFilterTestType EXTENTS_3D: the
    ball against the box), the taper by the circle; the Hammer faces south, its box 14 wide east, the edge 106 away.

    Round 33 (counters: percent lost, a step counted once begun, so 6.25 shows as 7; only the first hit is read):

      armor   instant V4s of 2000 GUN / AUTO_CANNON / IMPACT / RADIATION at Hammers 250 north (front hits): 10 / 5 /
              15 / 1 = BaseTankArmor's 50 / 25 / 75 / 5 %.
      flank   4000 EXPLOSIVE from 0 / 40 / 90 / 180 degrees off the Hammer's facing (it faces south): 40 / 40 / 42 /
              44 -- Side 105 beyond 45 degrees, Rear 110 beyond 135, by the attacker's position.
      vet     retail V4s given 0 / 3600 / 7200 / 10800 points (ranks 1-4): 5 / 7 / 7 / 7 -- the veteran's DAMAGE_MULT
              125 stays at elite and heroic; the heroic's second rocket came sooner (RATE_OF_FIRE 120 %). A copy of the
              V4 with its own ExperienceLevelTemplates (linked) read 20 % at every level: copies do not get ranks so.
    """
    import math
    import os
    import re

    from maps import probe_range
    from parts import Mission, Script, Test, Unit
    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    FAR = missile.FAR
    LOST_MAX = missile.LOST_MAX
    SAGE = missile.SAGE
    TARGET_ID = missile.TARGET_ID
    V4 = missile.V4
    V4_WEAPON = missile.V4_WEAPON
    _sub1 = missile._sub1
    target = missile.target

    ORDER, RUN = 6.0, 20.0
    SLOW = 60.0                         # 4 a frame: FAR's ~450 takes ~113 frames
    SPLASH_DAMAGE, SPLASH_RADIUS, SPLASH_TAPER = 2000.0, 100.0, 20.0
    SPLASH_NEAR = 250.0
    SPLASH_AT = (40.0, 80.0, 120.0)
    SHELL = 'SovietAntiVehicleVehicleTech1TankProjectile'
    SHELLS_AT = (250.0, 350.0, 450.0, 550.0)   # check shells: each shell's target this far north of its shooter
    SHELLS_DX = (-600.0, -200.0, 200.0, 600.0)  # the shooters along the order lane, 400 apart (the lanes 1 500)
    SHELLS_REACH = 800.0                       # past 550 (retail's 500 would drive the V4 nearer first)
    DAMAGE = '<DamageNugget Damage="{d:.1f}" DamageType="EXPLOSIVE" DeathType="EXPLODED" Radius="{r:g}"{extra} />'
    # check armor (round 33): one instant V4 per DamageType, ARMOR_DAMAGE a hit, each at its own Hammer ARMOR_AT north
    # (the Hammer faces south, the map's default for s1: a front hit); retail's BaseTankArmor gives these percents
    ARMOR_KINDS = (('GUN', 50), ('AUTO_CANNON', 25), ('IMPACT', 75), ('RADIATION', 5))
    ARMOR_DAMAGE, ARMOR_AT, ARMOR_DX = 2000.0, 250.0, -500.0
    # check flank: four EXPLOSIVE V4s of FLANK_DAMAGE, each at its own Hammer (at lane + FLANK_AT, facing south) from
    # FLANK_REACH away at this many degrees off the Hammer's facing (BaseTankArmor Side 105, Rear 110)
    FLANK_OFF = (0.0, 40.0, 90.0, 180.0)
    FLANK_DAMAGE, FLANK_AT, FLANK_REACH = 4000.0, (500.0, 300.0), 250.0
    SHORT = ORDER + 3.0                  # armor / flank: only the first hit (the next is >= 4.5 s later)
    # check vet: four retail V4s (SovietAntiStructureVehicle: retail's ranks name it as their Target; a copy given its
    # own ExperienceLevelTemplates read 20 % at every point level, round 33 -- the copy's levels did not take or the
    # points did nothing, not told apart), given these points at the start (ranks 1-4 at 1 / 3600 / 7200 / 10800), each
    # at its own Hammer; the first rocket lands ~108 frames after the order (engine_missile miss), 5 % at rank 1
    VET, VET_DX, VET_POINTS, VET_RUN = 'SovietAntiStructureVehicle', 250.0, (0, 3600, 7200, 10800), ORDER + 9.0
    LASER = ('<ActivateLaserNugget id="DefaultLaserNugget" Lifetime="0.1s" LaserId="1" />')


    def _nuggets(*items):
        return '<Nuggets>\n\t\t\t' + '\n\t\t\t'.join(items) + '\n\t\t</Nuggets>'


    def shot_v4(id, nuggets, speed=999999.0, files=None, extra='', what='', reach=None, scatter=0.0, reload=None):
        """Retail's V4 under `id`, its rocket weapon swapped for `id`Weapon: `nuggets`, WeaponSpeed `speed`, no scatter,
        pre-attack 0, FiringDuration 0; nothing else differs (ADR 0016 G5: the probe builds it). `extra`: more assets
        laid into the unit's file, `files`: {name: xml} of its own; `reach`: AttackRange instead of retail's 500;
        `scatter`: a ScatterRadius (engine_scatter); `reload`: ClipReloadTime seconds instead of retail's 4.5-5.5."""
        wid = id + 'Weapon'
        x = open(os.path.join(SAGE, 'Soviet', 'Units', V4 + '.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{V4}"', f'id="{id}"')
        x = re.sub(rf'EditorName="{V4}"', f'EditorName="{id}"', x)
        x = _sub1(x, f'Template="{V4_WEAPON}"', f'Template="{wid}"')
        w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
        s = re.search(rf'\t*<WeaponTemplate\s+id="{V4_WEAPON}".*?</WeaponTemplate>\n', w, re.S).group(0)
        s = _sub1(s, f'id="{V4_WEAPON}"', f'id="{wid}"')
        s = _sub1(s, 'inheritFrom="ScatterableWeapon"', '')
        s = _sub1(s, 'WeaponSpeed="200"', f'WeaponSpeed="{speed:g}"')
        if reach is not None:
            s = _sub1(s, 'AttackRange="500.0"', f'AttackRange="{reach:g}"')
        if scatter:
            s = _sub1(s, 'MinimumAttackRange=', f'ScatterRadius="{scatter:g}" MinimumAttackRange=')
        if reload is not None:
            s, k = re.subn(r'(<ClipReloadTime\s+MinSeconds=")4\.5s("\s+MaxSeconds=")5\.5s"', rf'\g<1>{reload:g}s\g<2>{reload:g}s"', s)
            assert k == 1, k
        s, k = re.subn(r'<Nuggets>.*?</Nuggets>', nuggets, s, flags=re.S)
        assert k == 1, k
        s, k = re.subn(r'\s*<ScatterRadiusVsType\s+Radius="0\.1">.*?</ScatterRadiusVsType>', '', s, flags=re.S)
        assert k == 1, k
        s = _sub1(s, 'MinSeconds=".5s"\n\t\t  MaxSeconds=".5s"', 'MinSeconds="0s"\n\t\t  MaxSeconds="0s"')
        s = _sub1(s, '<FiringDuration\n\t\t\tMinSeconds="1.0s"\n\t\t\tMaxSeconds="1.0s"',
                  '<FiringDuration\n\t\t\tMinSeconds="0s"\n\t\t\tMaxSeconds="0s"')
        x = _sub1(x, '</AssetDeclaration>', s + extra + '</AssetDeclaration>')
        files = files or {}
        return Unit(id, x, files=files, also=list(files), link=[f'WeaponTemplate:{wid}'],
                    names=dict(unit=id, weapon=wid), what=what, params=dict(speed=speed))


    def shell_v4(id='CNV_ShotShell', reach=None, damage=500.0, what=None, **kw):
        """The V4 firing retail's Hammer shell (copied as `id`Projectile) with a warhead (`id`Warhead) of one radius-0
        DamageNugget of `damage` (500); `reach`: its AttackRange (retail 500); `kw`: shot_v4's scatter / reload."""
        proj, wh = id + 'Projectile', id + 'Warhead'
        p = open(os.path.join(SAGE, 'Soviet', 'Props', SHELL + '.xml'), encoding='utf-8').read()
        p = _sub1(p, f'id="{SHELL}"', f'id="{proj}"')
        p = _sub1(p, f'EditorName="{SHELL}"', f'EditorName="{proj}"')
        warhead = (f'\t<WeaponTemplate id="{wh}" ProjectileCollidesWith="ALLIES ENEMIES NEUTRAL STRUCTURES WALLS"\n'
                   f'\t\tRadiusDamageAffects="ENEMIES" RequiredAntiMask="ANTI_WATER ANTI_GROUND ANTI_STRUCTURE">\n'
                   f'\t\t{_nuggets(DAMAGE.format(d=damage, r=0, extra=""))}\n\t</WeaponTemplate>\n')
        nug = f'<ProjectileNugget WarheadTemplate="{wh}" ProjectileTemplate="{proj}" />'
        far = '' if reach is None else f'，射程 {reach:g}'
        u = shot_v4(id, _nuggets(nug), files={proj + '.xml': p}, extra=warhead, reach=reach, **kw,
                    what=what or f'打锤子炮弹的 V4（探针）：直射弹（原版锤子炮弹），弹头半径 0、500 伤害，无预瞄、无开火持续、无散布{far}')
        u.names.update(projectile=proj, warhead=wh)
        return u


    def units():
        one = DAMAGE.format(d=500.0, r=0, extra='')
        splash = DAMAGE.format(d=SPLASH_DAMAGE, r=SPLASH_RADIUS, extra=f' DamageTaperOff="{SPLASH_TAPER:g}"')
        return [
            shot_v4('CNV_ShotInstant', _nuggets(one), what='瞬发 V4（探针）：WeaponSpeed 999999，500 伤害，无预瞄、无开火持续、无散布'),
            shot_v4('CNV_ShotSlow', _nuggets(one), SLOW,
                    what=f'慢速瞬发 V4（探针）：WeaponSpeed {SLOW:g}，500 伤害，无预瞄、无开火持续、无散布'),
            shell_v4(),
            shell_v4('CNV_ShotReach', SHELLS_REACH),
            shot_v4('CNV_ShotLaser', _nuggets(LASER, one),
                    what='激光 V4（探针）：开激光光束 + 500 伤害，WeaponSpeed 999999，无预瞄、无开火持续、无散布'),
            shot_v4('CNV_ShotSplash', _nuggets(splash),
                    what=f'溅射 V4（探针）：{SPLASH_DAMAGE:g} 伤害、半径 {SPLASH_RADIUS:g}、边缘衰减到 {SPLASH_TAPER:g}，'
                         '无预瞄、无开火持续、无散布'),
            *[shot_v4(_kind_id(k), _nuggets(_kind_nugget(k, ARMOR_DAMAGE)),
                      what=f'{k} 瞬发 V4（探针）：{ARMOR_DAMAGE:g} 伤害、伤害类型 {k}，无预瞄、无开火持续、无散布')
              for k, _ in ARMOR_KINDS],
            shot_v4('CNV_ShotFlank', _nuggets(DAMAGE.format(d=FLANK_DAMAGE, r=0, extra='')),
                    what=f'侧击 V4（探针）：{FLANK_DAMAGE:g} 伤害（EXPLOSIVE），无预瞄、无开火持续、无散布'),
            target(),
        ]


    def _kind_id(kind):
        return 'CNV_ShotKind' + ''.join(p.title() for p in kind.split('_'))


    def _kind_nugget(kind, d):
        return f'<DamageNugget Damage="{d:.1f}" DamageType="{kind}" DeathType="EXPLODED" Radius="0" />'


    LANES = {'base': 'CNV_ShotInstant', 'high': 'CNV_ShotSlow', 'removed': 'CNV_ShotShell', 'switch': 'CNV_ShotLaser'}
    LABELS = {'base': 'instant', 'high': 'slow', 'removed': 'shell', 'switch': 'laser'}


    def mission():
        m = Mission(name='CampShot', map=probe_range, units=units(), facts={})
        for lane, tpl in LANES.items():
            L, site = lane.title(), f'{lane} gun'
            m.put(tpl, site, side='p1', role=f'{lane} shooter', name=f'UNIT - CNV Shot {L} Shooter')
            m.put(TARGET_ID, site, 0, FAR, side='s1', role=f'{lane} target', name=f'UNIT - CNV Shot {L} Target')
        m.put('CNV_ShotSplash', 'low gun', side='p1', role='splash shooter', name='UNIT - CNV Shot Splash Shooter')
        for k, dx in enumerate((0.0,) + SPLASH_AT):
            m.put(TARGET_ID, 'low gun', dx, SPLASH_NEAR, side='s1', role=f'splash {dx:g}',
                  name=f'UNIT - CNV Shot Splash {k}')
        for k, (dx, d) in enumerate(zip(SHELLS_DX, SHELLS_AT)):
            m.put('CNV_ShotReach', 'order gun', dx, 0, side='p1', role=f'shells {d:g} shooter',
                  name=f'UNIT - CNV Shot Shells {k} Shooter')
            m.put(TARGET_ID, 'order gun', dx, d, side='s1', role=f'shells {d:g} target',
                  name=f'UNIT - CNV Shot Shells {k} Target')
        for (kind, _), lane in zip(ARMOR_KINDS, LANES):
            m.put(_kind_id(kind), f'{lane} gun', ARMOR_DX, 0, side='p1', role=f'armor {kind} shooter',
                  name=f'UNIT - CNV Shot Armor {kind} Shooter')
            m.put(TARGET_ID, f'{lane} gun', ARMOR_DX, ARMOR_AT, side='s1', role=f'armor {kind} target',
                  name=f'UNIT - CNV Shot Armor {kind} Target')
        fx, fy = FLANK_AT
        for off, lane in zip(FLANK_OFF, LANES):
            a = math.radians(off)                       # the Hammer faces south: front is (0, -1)
            m.put('CNV_ShotFlank', f'{lane} gun', fx + FLANK_REACH * math.sin(a), fy - FLANK_REACH * math.cos(a),
                  side='p1', role=f'flank {off:g} shooter', name=f'UNIT - CNV Shot Flank {off:g} Shooter',
                  angle=math.atan2(math.cos(a), -math.sin(a)))  # facing its Hammer: no turn before the shot
            m.put(TARGET_ID, f'{lane} gun', fx, fy, side='s1', role=f'flank {off:g} target',
                  name=f'UNIT - CNV Shot Flank {off:g} Target')
        for pts, lane in zip(VET_POINTS, LANES):
            m.put(VET, f'{lane} gun', VET_DX, 0, side='p1', role=f'vet {pts} shooter',
                  name=f'UNIT - CNV Shot Vet {pts} Shooter')
            m.put(TARGET_ID, f'{lane} gun', VET_DX, ARMOR_AT, side='s1', role=f'vet {pts} target',
                  name=f'UNIT - CNV Shot Vet {pts} Target')
        m.spawns |= {'CNV_ShotShellProjectile', 'CNV_ShotReachProjectile'}
        return m




    def shot_test(m, group):
        """group 'way': the four lanes (counter: frames to the first hit + 1000 per percent); 'splash': the four splash
        Hammers (counter: percent lost). The other group's shooters keep NO_ATTACK."""
        t = Test()

        def n(part):
            return m.role(part).name

        lanes = [(LABELS[lane], n(f'{lane} shooter'), n(f'{lane} target')) for lane in LANES]
        splash = [(f'splash{dx:g}', n(f'splash {dx:g}')) for dx in (0.0,) + SPLASH_AT]
        shells = [(f'shell{d:g}', n(f'shells {d:g} shooter'), n(f'shells {d:g} target')) for d in SHELLS_AT]
        kinds = [(k.lower(), n(f'armor {k} shooter'), n(f'armor {k} target')) for k, _ in ARMOR_KINDS]
        flank = [(f'flank{off:g}', n(f'flank {off:g} shooter'), n(f'flank {off:g} target')) for off in FLANK_OFF]
        vet = [(f'vet{p}', n(f'vet {p} shooter'), n(f'vet {p} target')) for p in VET_POINTS]
        rows = {'armor': kinds, 'flank': flank, 'vet': vet}
        if group == 'way':
            pairs = [(s, tg) for _, s, tg in lanes]
        elif group == 'shells':
            pairs = [(s, tg) for _, s, tg in shells]
        elif group in rows:
            pairs = [(s, tg) for _, s, tg in rows[group]]
        else:
            pairs = [(n('splash shooter'), splash[0][1])]
        held = [s for _, s, _ in lanes] + [tg for _, _, tg in lanes] + [n('splash shooter')] + [tg for _, tg in splash]
        held += [x for _, s, tg in shells + kinds + flank + vet for x in (s, tg)]
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        if group == 'vet':
            start += [('UNIT_GIVE_EXPERIENCE_POINTS', s, p) for (_, s, _), p in zip(vet, VET_POINTS) if p]
        start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in held]
        start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0) for s, _ in pairs]
                                + [('NAMED_ATTACK_NAMED', s, tg) for s, tg in pairs]
                                + [('SET_FLAG', 'Test Ordered', 1)]))
        if group in ('way', 'shells'):
            for k, (label, _, tg) in enumerate(lanes if group == 'way' else shells):
                c = f'CNV_Shot_{"W" if group == "way" else "D"}{k}'
                t.counters.append((c, label))
                t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                        [('INCREMENT_COUNTER', 1, c)], once=False))
                t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                     [('INCREMENT_COUNTER', 1000, c)]) for j in range(1, LOST_MAX + 1)]
            t.expect = [(lanes[0][0] if group == 'way' else shells[0][0], 0, 'ever>=', 1000, RUN - 2)]
        elif group in rows:
            for k, (label, _, tg) in enumerate(rows[group]):
                c = f'CNV_Shot_{group[0].upper()}{k}'
                t.counters.append((c, label))
                t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                     [('INCREMENT_COUNTER', 1, c)]) for j in range(1, LOST_MAX + 1)]
            run = VET_RUN if group == 'vet' else SHORT
            t.expect = [(rows[group][0][0], 0, 'ever>=', 1, run - 1)]
            t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=6))]
            return t
        else:
            for k, (label, tg) in enumerate(splash):
                c = f'CNV_Shot_S{k}'
                t.counters.append((c, label))
                t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                     [('INCREMENT_COUNTER', 1, c)]) for j in range(1, LOST_MAX + 1)]
            t.expect = [('splash0', 0, 'ever>=', 1, RUN - 2)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=6))]
        return t


    MISSION = {'engine_shot': mission}
    CHECKS = {'engine_shot': {'way': lambda m: shot_test(m, 'way'), 'splash': lambda m: shot_test(m, 'splash'),
                              'shells': lambda m: shot_test(m, 'shells'), 'armor': lambda m: shot_test(m, 'armor'),
                              'flank': lambda m: shot_test(m, 'flank'), 'vet': lambda m: shot_test(m, 'vet')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        DAMAGE=DAMAGE, FLANK_DAMAGE=FLANK_DAMAGE, SHELL=SHELL, _nuggets=_nuggets, shell_v4=shell_v4,
        shot_v4=shot_v4))


def engine_strip():
    """Bench exact PASS95/45/74 ->100095/100045/100074, alive3 (11-10).
    PREDICT before bench: AmountToStrip acts on MAX health, not current.
    10000HP Hammer, one1 UNRESISTABLE marker plus4%/4%/25% strip;
    second lane starts at50%. UNRESISTABLE isolates armor. Predicted rounded
    health96/46/75, all alive. Formula(10000*start -1 -10000*Amount)/100.
    First bench maxhp read95/45/74: floor(95.99/45.99/74.99) is a
    GUESSED counter-conversion explanation, not a new damage formula.
    Second exact check changes marker1->100 (exactly1% of max10000),
    predicts95/45/74 with integer health percentages, packed100095/100045/100074.
    This removes floor-vs-round ambiguity without changing strip amounts.
    GUESSED before bench: the percent amount is damage rather than reducing maxHP.
    At10s SET_UNIT_HEALTH100% checks recovery ->100/100/100. This
    is not an independent absolute-maxHP measurement; maxHP preservation
    remains INFERRED from the damage-like percentage response.
    Each displayed row HPbefore +1000*HPafter; fourth row alive count3.
    Order6s after1s initial EMPTY clip load, NO_ATTACK stops6+4/15.
    """
    from maps import probe_range
    from parts import Mission,Script,Test
    gun = engine_weaponfx()["shared"].gun
    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    target = missile.target
    TARGET_ID = missile.TARGET_ID

    def mission():
        return Mission(name='CampStrip',map=probe_range,units=[target()],facts={})

    def check(m, exact=False):
        t=Test(); start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),
            ('SET_MILLISECOND_TIMER','Strip Fire',6.0),('SET_MILLISECOND_TIMER','Strip Stop',6.0+4/15),
            ('SET_MILLISECOND_TIMER','Strip Reset',10.0)]
        fire=[];stop=[];reset=[]
        for lane,amount,health in (('base',4,100.0),('high',4,50.0),('order',25,100.0)):
            u=gun('CNV_Strip'+lane.title(),100 if exact else 1,f'<StripMaxHealthPercentNugget AmountToStrip="{amount}%" DamageType="UNRESISTABLE"/>')
            u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"');m.units.append(u)
            g='Strip '+lane+' gun'; v='Strip '+lane+' target'; c='CNV_Strip_'+lane
            m.put(u.id,lane+' gun',side='p1',angle=1.5708,name=g)
            m.put(TARGET_ID,lane+' gun',0,450,side='s1',angle=4.7124,name=v)
            start.extend([('UNIT_CHANGE_OBJECT_STATUS',name,'NO_ATTACK',1) for name in (g,v)])
            start.append(('UNIT_SET_HEALTH',v,health))
            fire += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',g,v)]
            stop += [('UNIT_CHANGE_OBJECT_STATUS',g,'NO_ATTACK',1)]
            reset += [('UNIT_SET_HEALTH',v,100.0)]
            t.counters.append((c,lane+' HP packed'))
            temp='Strip HP '+lane
            t.scripts += [Script('Test - before '+lane,[('FLAG','Strip Reset Done',0)],[('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c)],once=False),
              Script('Test - after '+lane,[('FLAG','Strip Reset Done',1)],[('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,temp),('COUNTER_MATH_VALUE',temp,2,1000),('COUNTER_MATH_COUNTER',c,0,temp)])]
        # Snapshot before reset, then add1000*restored health once on the following frame.
        t.counters.append(('CNV_Strip_Alive','alive'))
        t.scripts.append(Script('Test - alive',[('NAMED_NOT_DESTROYED','Strip '+lane+' target') for lane in ('base','high','order')],[('SET_COUNTER','CNV_Strip_Alive',3)],once=False))
        t.scripts.insert(0,Script('Test - start',[],start))
        t.scripts += [Script('Test - fire',[('TIMER_EXPIRED','Strip Fire')],fire),
            Script('Test - stop',[('TIMER_EXPIRED','Strip Stop')],stop),
            Script('Test - reset',[('TIMER_EXPIRED','Strip Reset')],reset+[('SET_FLAG','Strip Reset Done',1)])]
        t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(100095,100045,100074,3) if exact else (100096,100046,100075,3))]
        t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
        return t
    MISSION={'engine_strip':mission}
    CHECKS={'engine_strip':{'maxhp':check,'exact':lambda m:check(m,True)}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


@cache
def engine_suppress_probe():
    """Engine line D, round 21 (ADR 0027/0028): C line's suppression closure with ra3ext's read-only probe on the target.

    benches/weapon/target_effects/checks.py#engine_suppression (C line's check, not changed here) times how long a suppressed man takes through a gate; the
    bench shows only the result. This mission is the same one -- its mission() and check() are called as they are --
    with two changes: the ordinary men (AlliedAntiInfantryInfantry, every lane but 'low') are a copy CNV_SuppProbeMan
    with one more module, `<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames=EVERY MaxFrames=LINES/>`, and the mission is
    built with ext=True (ra3ext.allow: the bench starts the game through ra3ext_launch). ra3ext's create sees the tag and
    builds CNVProbe instead of a DeletionUpdate: each frame it reads the man's SuppressionUpdate (end frame, state,
    threshold), the suppression value the game's own query returns for him and the raw manager entries covering him, and
    writes a line to the run folder's ra3ext.log when one of them changed (or every EVERY frames), LINES lines at most.

    The probe only reads, so the counters must equal C line's readings (its expectations are kept): that is the check
    that the probe does not change the game. The timing rules are read off ra3ext.log (handoff-d round 21), not asserted.
    'fast' (replaces the man's template itself) and the armour lanes (no walk) are left out.
    """
    import os

    import labpaths
    from parts import Unit
    supp = engine_suppression()["shared"]

    MAN, PROBE = 'AlliedAntiInfantryInfantry', 'CNV_SuppProbeMan'
    EVERY, LINES = 15, 3000
    WHICH = ('threshold', 'expiry', 'phasea', 'lifetime', 'fraction', 'tail', 'duration', 'speed')


    def probe_man():
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', MAN + '.xml'), encoding='utf-8') as f:
            x = f.read()
        assert x.count(f'id="{MAN}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{MAN}"', f'id="{PROBE}"', 1).replace(f'EditorName="{MAN}"', f'EditorName="{PROBE}"')
        x = x.replace('<Behaviors>', (
            f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'
        ), 1)
        return Unit(PROBE, x, names=dict(unit=PROBE),
                    what=f'维和步兵的复制（探针）：多一个 ra3ext 的 CNVProbe 模块（载体 DeletionUpdate），逐帧记压制读数',
                    params=dict(of=MAN, every=EVERY, lines=LINES))


    def _probed(m):
        for o in m.objects:
            if o.template == MAN:
                o.template = PROBE
        for lane in supp.CASES:
            if m.role(lane).template == MAN:
                m.role(lane).template = PROBE
        return m


    def mission():
        m = supp.mission()
        m.name, m.ext = 'CampSP', True     # + the check's name stays <= 15 (CampSPThreshold); longer crashes the game
        return _probed(m)


    def check(m, which):
        t = supp.check(m, which)       # rebuilds m.units from C line's guns
        m.units.append(probe_man())
        _probed(m)
        return t


    MISSION = {'engine_suppress_probe': mission}
    CHECKS = {'engine_suppress_probe': {k: (lambda m, k=k: check(m, k)) for k in WHICH}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        EVERY=EVERY, LINES=LINES, PROBE=PROBE, probe_man=probe_man))


@cache
def engine_suppression():
    """Suppression closure, rounds 11-13 (RA3 bench).

    SETTLED checks (strict == over the final two seconds):
      threshold: 24x2/3s ->44, 25x2/3s ->59, 5x10/3s ->59,
        6x10/3s ->59. Suppressability=50 is inclusive (48 fails, 50 works).
      speed: zero contribution ->44; 6x10/3s ->59. The data's modifier
        SPEED 75% means 50*.75=37.5; fast independently reads37 at80*.75=60.
        59 is the observed arrival counter; continuous 145/37.5*15 gives58.
        Sub-frame movement/entry is not explained: do not truncate speed to fit59.
      armor / armored: control has zero contribution; high has26x2/3s.
        MaxHealth150, one40 hit: UNRESISTABLE bypasses ARMOR (native0x785370),
        round(110/150*100)=73 on both lanes. EXPLOSIVE base scalar100%,
        ARMOR75% gives round((150-40*.75)/150*100)=80 on the high lane.
        Each health counter is followed by ALIVE=1.
      immune: zero-contribution ordinary control44; Tanya6x10/3s40.
        Speed50/55 explains ceil(145*15/speed)=44/40; Tanya removes the behavior.
      fast: long25/26x2 lanes37/37, from ceil(145/(80*.75/15)).

    Further bench counters (unchanged):
      expiry44/44/59/59 (48 long,52 short,50 long,60 long);
      phasea44/44, phaseb44/44 (1s, shots shifted1/3 or2/3s);
      lifetime44/59 (1.1s/2s), fraction59/59 (1.95s);
      duration44/45/44/45 (1s, early/late legs);
      tail56/56 (3s, move at12s; rejected predictions48/51/52).
    The read-only engine_suppress_probe tail/lifetime/duration/expiry runs
    (2026-11-10) resolve the common timing rule: born-phase samples, enter
    without setting the end, refresh only when already suppressed, low sample
    clears strictly after the end. The simulator replays the measured module
    state/end frames in all four checks. Duration counters also match exactly.
    Other suppressed arrival legs can remain one frame short: the bench's
    position trace has lateral walking drift (tail ends x806.7 from x800),
    while Sim walks a straight segment. Do not add a fitted frame to suppression.
    Fractional lifetime ceil vs nearest beyond the observed1.1s remains INFERRED.

    Probe contract: finite burst ordered at6s, guns initially load in1s and
    NO_ATTACK stops each before its next clip. Two guns split25/26 hits within
    3s. Pressure hits each deal1.5 UNRESISTABLE damage (1% of150HP), so the
    pre-move health platform verifies the burst. Armor resets health at9s and
    fires one separate40 hit at11s. Walk at9s (duration10s/17s; tail12s),
    through a gate145 units away with the destination75 beyond the goal.
    SUPPRESSED is a model condition, not a script object status. ForceMove and
    Cover are out of scope. Timers/health parameters must be Python floats.

    SuppressionUpdate and SuppressionNugget are registered to the four measured
    state/end replays, together with the earlier threshold/modifier controls.
    Arrival counters do not claim that generic walking drift has been modeled.
    """
    import os
    import re

    from maps import probe_range
    from parts import Mission, Script, Test, Unit, square
    from benches.weapon.firing.checks import engine_clip
    clip = engine_clip()["shared"]
    ORDER = clip.ORDER
    SAGE = clip.SAGE
    clip_v4 = clip.clip_v4

    CASES = {'base': (25, 2, 3), 'high': (26, 2, 3),
             'order': (5, 10, 1), 'removed': (6, 10, 1), 'low': (6, 10, 1)}
    # Copy clip's 6 s order; shift the round 7 schedule by the same 5 s.
    SHIFT = ORDER - 1.0
    RUN = 18 + SHIFT


    def cases_for(which):
        cases = dict(CASES)
        if which == 'threshold':
            cases.update(base=(24, 2, 3), high=(25, 2, 3),
                         order=(5, 10, 3), removed=(6, 10, 3))
        if which in ('speed', 'armor', 'armored', 'immune'):
            cases.update(order=(5, 0, 3), removed=(6, 10, 3), low=(6, 10, 3))
        if which == 'expiry':
            cases.update(base=(24, 2, 3), high=(26, 2, 1),
                         order=(5, 10, 3), removed=(6, 10, 3))
        if which == 'lifetime':
            cases.update(order=(5, 10, 1.1), removed=(6, 10, 2))
        if which == 'fraction':
            cases.update(order=(5, 10, 1.95), removed=(6, 10, 1.95))
        return cases


    def name(lane, part):
        return f'UNIT - CNV Supp {lane} {part}'


    def gun(lane, armor=False, second=False, cases=None):
        hits, value, duration = (cases or CASES)[lane]
        if lane in ('base', 'high') and not armor:
            hits = hits // 2 if second else (hits + 1) // 2
        uid = 'CNV_Supp' + lane.title() + ('Armor' if armor else 'Second' if second else '')
        u = clip_v4('bare', hit=40 if armor else 1.5, uid=uid,
                    spec=(0, 1 / 15, 1.0, 1 if armor else hits, 'PRE_FIRE', (), RUN, 'pressure'))
        effect = '' if armor else f'<SuppressionNugget Radius="20" Suppression="{value}" DurationSeconds="{duration}s"/>'
        u.xml, n = re.subn(r'<Nuggets>.*?</Nuggets>',
                           f'<Nuggets><DamageNugget Damage="{40 if armor else 1.5}" DamageType="UNRESISTABLE" '
                           f'DeathType="NORMAL" Radius="0"/>{effect}</Nuggets>', u.xml, flags=re.S)
        assert n == 1
        return u


    def mission():
        units = [gun(k, a) for k in CASES for a in (False, True)] + [gun(k, second=True) for k in ('base', 'high')]
        m = Mission(name='CampSu', map=probe_range, units=units, facts={})
        for lane in CASES:
            for armor in (False, True):
                m.put('CNV_Supp' + lane.title() + ('Armor' if armor else ''), f'{lane} gun',
                      100 if armor else 0, 0, side='p1', angle=1.5708,
                      name=name(lane, 'armor' if armor else 'gun'))
            if lane in ('base', 'high'):
                m.put('CNV_Supp' + lane.title() + 'Second', f'{lane} gun', -100, 0,
                      side='p1', angle=1.5708, name=name(lane, 'second'))
            # Stasis' benched s1 theirs/chaser follow MOVE_NAMED_UNIT_TO + m.mark().
            # Clip's target is 450 from its V4: retain the inherited 200..500 range.
            m.put('AlliedCommandoTech1' if lane == 'low' else 'AlliedAntiInfantryInfantry',
                  f'{lane} gun', 0, 450, side='s1', role=lane, name=name(lane, 'man'))
            m.waypoint(lane + ' goal', 'Supp ' + lane + ' goal', f'{lane} gun', 0, 600)
            m.waypoint(lane + ' late', 'Supp ' + lane + ' late', f'{lane} gun', 0, 750)
            # Walk THROUGH the timing gate, rather than stopping short of a tiny destination square.
            for leg, dy in (('goal', 675), ('late', 825)):
                m.waypoint(lane + ' ' + leg + ' runout', 'Supp ' + lane + ' ' + leg + ' runout',
                           f'{lane} gun', 0, dy)
        return m


    def check(m, which):
        cases = cases_for(which)
        m.units = [gun(k, a, cases=cases) for k in cases for a in (False, True)] + [
            gun(k, second=True, cases=cases) for k in ('base', 'high')]
        if which == 'armored':
            for u in m.units:
                if u.id.endswith('Armor'):
                    u.xml = u.xml.replace('DamageType="UNRESISTABLE"', 'DamageType="EXPLOSIVE"')
        if which == 'fast':
            with open(os.path.join(SAGE, 'Allied', 'Units', 'AlliedAntiInfantryInfantry.xml'), encoding='utf-8') as f:
                xml = f.read()
            xml = xml.replace('id="AlliedAntiInfantryInfantry"', 'id="CNV_SuppFastMan"', 1)
            xml, n = re.subn(r'(Locomotor="TestReactiveLocomotorHUMAN"\s+Condition="NORMAL"\s+Speed=")50"',
                            r'\g<1>80"', xml)
            assert n == 1
            m.units.append(Unit('CNV_SuppFastMan', xml))
            for k in ('base', 'high'):
                m.role(k).template = 'CNV_SuppFastMan'
                next(o for o in m.objects if o.name == name(k, 'man')).template = 'CNV_SuppFastMan'
        armor_check = which in ('armor', 'armored')
        fire_at = ORDER + {'phasea': 1 / 3, 'phaseb': 2 / 3}.get(which, 0)
        t = Test()
        lanes = (tuple(CASES)[:4] if which in ('threshold', 'expiry') else
                 ('order', 'high') if armor_check else
                 ('base', 'high') if which in ('edge', 'fast', 'tail') else
                 ('order', 'low') if which == 'immune' else ('order', 'removed'))
        # Match benched clip: reveal p1, hold both sides, then release only the gun.
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, part), 'NO_ATTACK', 1)
                  for k in CASES for part in ('gun', 'armor', 'man')]
        start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'second'), 'NO_ATTACK', 1) for k in ('base', 'high')]
        start += [('SET_MILLISECOND_TIMER', 'Supp Fire', float(fire_at)),
                  ('SET_MILLISECOND_TIMER', 'Supp Move', 12.0 if which == 'tail' else SHIFT + (5.0 if which == 'duration' else 4.0)),
                  ('SET_MILLISECOND_TIMER', 'Supp Late', SHIFT + 12.0),
                  ('SET_MILLISECOND_TIMER', 'Supp Armor', SHIFT + 6.0)]
        t.scripts.append(Script('Test - start', [], start))
        fire = []
        for k in lanes:
            fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 0),
                     ('NAMED_ATTACK_NAMED', name(k, 'gun'), name(k, 'man'))]
            if k in ('base', 'high'):
                fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'second'), 'NO_ATTACK', 0),
                         ('NAMED_ATTACK_NAMED', name(k, 'second'), name(k, 'man'))]
        # Initial clips load in 1 s, before ORDER. Stop inside the reload gap:
        # first shot +2 frames, then 2 frames per shot; next clip is 15 frames away.
        for k in lanes:
            for part in ('gun', 'second') if k in ('base', 'high') else ('gun',):
                hits = cases[k][0]
                if k in ('base', 'high'):
                    hits = hits // 2 if part == 'second' else (hits + 1) // 2
                timer = 'Supp Stop ' + k + part
                start.append(('SET_MILLISECOND_TIMER', timer, fire_at + (2 * hits + 2) / 15))
                t.scripts.append(Script('Test - stop ' + k + part, [('TIMER_EXPIRED', timer)],
                                        [('UNIT_CHANGE_OBJECT_STATUS', name(k, part), 'NO_ATTACK', 1)]))
        fire.append(('SET_FLAG', 'Supp Ordered', 1))
        t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'Supp Fire')], fire))
        for k in lanes:
            man = m.role(k).name
            if armor_check:
                t.scripts.append(Script('Test - reset ' + k, [('TIMER_EXPIRED', 'Supp Move')], [('UNIT_SET_HEALTH', man, 100.0)]))
                t.scripts.append(Script('Test - armor ' + k, [('TIMER_EXPIRED', 'Supp Armor')], [
                    ('UNIT_CHANGE_OBJECT_STATUS', name(k, 'armor'), 'NO_ATTACK', 0),
                    ('NAMED_ATTACK_NAMED', name(k, 'armor'), man)]))
                timer = 'Supp Stop armor ' + k
                start.append(('SET_MILLISECOND_TIMER', timer, SHIFT + 6.0 + 4 / 15))
                t.scripts.append(Script('Test - stop armor ' + k, [('TIMER_EXPIRED', timer)],
                                        [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'armor'), 'NO_ATTACK', 1)]))
                hp, alive = 'CNV_Supp_' + k + '_HP', 'CNV_Supp_' + k + '_ALIVE'
                t.counters += [(hp, k + ' 血'), (alive, k + ' 活')]
                t.scripts += [Script('Test - health ' + k, [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', man, hp)], once=False),
                              Script('Test - alive ' + k, [], [('SET_COUNTER', alive, 1)], once=False),
                              Script('Test - dead ' + k, [('NAMED_DESTROYED', man)], [('SET_COUNTER', alive, 0)], once=False)]
                continue
            for leg, timer in [('goal', 'Supp Move')] + ([('late', 'Supp Late')] if which == 'duration' else []):
                wp, c, flag = m.mark(k + ' ' + leg + ' runout'), 'CNV_Supp_' + k + '_' + leg, 'Supp moving ' + k + leg
                x, y = m.point(k + ' ' + leg)
                area = 'Supp area ' + k + leg
                # Crush uses square(..., 40); keep the existing y-5 entry line,
                # but allow lateral pathing drift rather than a ten-unit-wide slit.
                t.areas[area] = square(x, y + 35 - (1 if which == 'edge' else 0), 40)
                t.counters.append((c, k + ' ' + leg))
                # Before walking, reuse the goal line for health: 1.5 damage is
                # one percent of the ordinary man's 150 HP, making finite bursts visible.
                # The permanent started flag prevents arrival from overwriting frame counts.
                started = 'Supp started ' + k + leg
                if leg == 'goal':
                    t.scripts.append(Script('Test - burst health ' + k,
                                            [('FLAG', started, 0)],
                                            [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', man, c)], once=False))
                t.scripts.append(Script('Test - move ' + k + leg, [('TIMER_EXPIRED', timer)],
                                        [('SET_COUNTER', c, 0), ('SET_FLAG', started, 1),
                                         ('MOVE_NAMED_UNIT_TO', man, wp), ('SET_FLAG', flag, 1)]))
                t.scripts.append(Script('Test - arrived ' + k + leg, [('NAMED_INSIDE_AREA', man, area)], [('NAMED_STOP', man), ('SET_FLAG', flag, 0)]))
                t.scripts.append(Script('Test - frames ' + k + leg, [('FLAG', flag, 1)], [('INCREMENT_COUNTER', 1, c)], once=False))
        readings = {'threshold': (44, 59, 59, 59), 'expiry': (44, 44, 59, 59), 'speed': (44, 59),
                     'armor': (73, 1, 73, 1), 'armored': (73, 1, 80, 1),
                     'phasea': (44, 44), 'phaseb': (44, 44), 'lifetime': (44, 59), 'edge': (59, 59),
                     'fraction': (59, 59), 'fast': (37, 37), 'tail': (56, 56),
                     'duration': (44, 45, 44, 45), 'immune': (44, 40)}
        # judge has no 'at end' operator: require equality throughout the final 2 s.
        t.expect = [(label, RUN - 2, '==', value, RUN)
                    for (_, label), value in zip(t.counters, readings[which])]
        # Keep every lane visible for the entire observation; no gun-digit takeover.
        t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_suppression': mission}
    CHECKS = {'engine_suppression': {k: (lambda m, k=k: check(m, k))
                                   for k in ('threshold', 'expiry', 'phasea', 'phaseb', 'lifetime', 'fraction', 'edge', 'fast', 'tail',
                                             'speed', 'armor', 'armored', 'duration', 'immune')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        CASES=CASES, RUN=RUN, cases_for=cases_for, check=check, mission=mission))


@cache
def engine_sweep():
    """Engine line D, round 10 (ADR 0027/0028): the vertical sweep's carrier, with ra3ext injected and without. Retail's
    LinearDamageUpdate (the dolphin's sonar wave) is a damage line that walks away from the shooter: ActivateLinearDamageNugget
    starts it toward the weapon's target (flat, z dropped), from StartDistanceOffset out to StartDistanceOffset + Length at
    Speed, one SweepWeapon hit every 2 x Radius. What retail lacks is a laser beam that follows the walking point; the
    ra3ext module tagged ModuleTag_CNVSweep is to write the point into the LaserState's end each frame (handoff-d round 9).

    The shooter is engine_shot's V4 (no scatter, no pre-attack) under its own id, its weapon: a DamageNugget of AIM_DAMAGE on the
    aimed Hammer (counted: did it fire), ActivateLinearDamageNugget (Lifetime LIFE) and ActivateLaserNugget (LaserId 1,
    Lifetime LIFE); the clip loads RELOAD after birth, the order comes after it, the next clip after the far row's hit. Behaviors: LinearDamageUpdate id=ModuleTag_CNVSweep (StartDistanceOffset START, Radius RADIUS,
    Length LENGTH, Speed SPEED, SweepWeapon CNV_SweepHit = 500 damage in RADIUS, FollowTerrain), LaserState LaserId 1;
    Draws: the prism tower's LaserDraw (LaserStateID 1).

    Two lanes, a shooter at '<lane> gun' each, aimed (at ORDER) at a Hammer AIM north; three more Hammers (10 000 health,
    engine_missile's) between, at ROW north -- counted, never aimed at:

      base   CNV_Sweep       FiringDuration 0 (engine_shot's)
      high   CNV_SweepHold   FiringDuration LIFE (the update sleeps once the weapon slot says it stopped: does it?)

    Counter per row Hammer: frames from the order until its first hit (stops counting at the hit). Near < mid < far =
    the line walks outward; the gaps say the speed. Speed is a Velocity: BinaryAssetBuilder stores XML / 5 as units a
    logic frame (retail dolphin 170 -> 34, ours 60 -> 12), the logic runs 15 frames a second (a fixed rate, work/re/l2_scripts1.md), so the line
    walks SPEED x 3 a second: 100 apart = 100 x 5 / SPEED frames (60: ~8; bench 11-10 03:50: 9 / 18 / 26 frames to near / mid / far). It stops at
    min(Lifetime x 15, ceil(LENGTH / (SPEED / 5))) frames (work/re/handoff-archive.md, the sweep rounds), one hit every 2 x RADIUS.

      engine_sweep     Mission(ext=True)   the dll's sweep module: the laser's end follows the line's node; ra3ext.log
                                           has one 'sweep ... node=N at=x,y,z' line per new node (60 at most)
      engine_sweepoff  Mission(ext=False)  plain retail: the damage line alone, the beam stays on the aimed Hammer

    Checks: a the base lane's sweep; b the shooter stopped STOP s after the order; c deletion (delete_test): killed mid-sweep,
    a second one made, swept and deleted (bench 11-10 12:46 / 12:48 / 12:50: 9 / 158 / 167 with and without ra3ext -- the
    killed one's line stops with it, the rest is the second one's; ra3ext.log has no line of a module after its object went).
    """
    from maps import probe_range
    from parts import Mission, Script, Test, counted
    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    TARGET_ID = missile.TARGET_ID
    _sub1 = missile._sub1
    target = missile.target
    shot = engine_shot()["shared"]
    _nuggets = shot._nuggets
    shot_v4 = shot.shot_v4

    # the V4's clip is empty at birth and loads ClipReloadTime later (fire_state.md round 27): round 10's reload of 60 s
    # never let it fire in a 20 s run (bench 11-10 03:39, no row Hammer hit). Loaded at RELOAD, ordered at ORDER after it;
    # the next clip comes RELOAD after the first shot, past the far row's hit (ORDER + (350 - START) / (3 x SPEED))
    ORDER, RUN, RELOAD = 8.0, 22.0, 6.0
    START, RADIUS, LENGTH, SPEED = 50.0, 10.0, 450.0, 60.0     # covers 50 .. 500 north in 38 frames (2.5 s), 12 a frame
    LIFE = 8.0
    ROW, AIM = (150.0, 250.0, 350.0), 450.0
    TAG, HIT = 'ModuleTag_CNVSweep', 'CNV_SweepHit'
    LANES = {'base': ('CNV_Sweep', 0.0), 'high': ('CNV_SweepHold', LIFE)}
    LABELS = ('近', '中', '远')
    AIM_LABEL, AIM_DAMAGE = '瞄', 200.0      # the shot's own hit on the aimed Hammer: did the V4 fire at all

    # check c's second probe: ra3ext's CNVLog (engine_ext's carrier) on the base shooter, ext only -- without the dll the
    # carrier is a real DeletionUpdate and would delete the shooter
    CNV_LOG = (
        '\n'
        '\t\t\t<DeletionUpdate id="ModuleTag_CNVLog" MinFrames="30" MaxFrames="40"/>'
    )
    LASER_DRAW = (
        '\n'
        '\t\t\t<LaserDraw id="ModuleTag_CNVSweepLaserDraw" Texture1_UTile="1" Texture1_VTile="1" Texture1_UScrollRate="0"\n'
        '\t\t\t\tTexture1_VScrollRate=".2" Texture1_NumFrames="1" Texture1_FrameRate="30" Texture2_UTile="1"\n'
        '\t\t\t\tTexture2_VTile=".3" Texture2_UScrollRate="0" Texture2_VScrollRate="1.4" Texture2_NumFrames="1"\n'
        '\t\t\t\tTexture2_FrameRate="30" LaserWidth="8" LaserStateID="1">\n'
        '\t\t\t\t<FXShader ShaderName="Laser.fx" TechniqueIndex="0">\n'
        '\t\t\t\t\t<Constants>\n'
        '\t\t\t\t\t\t<Texture Name="Texture1"><Value>FXObeliskLaser</Value></Texture>\n'
        '\t\t\t\t\t\t<Texture Name="Texture2"><Value>FXLaserOverlay</Value></Texture>\n'
        '\t\t\t\t\t\t<Float Name="ColorEmissive"><Value>5.000000</Value><Value>5.000000</Value><Value>2.000000</Value></Float>\n'
        '\t\t\t\t\t</Constants>\n'
        '\t\t\t\t</FXShader>\n'
        '\t\t\t</LaserDraw>\n'
        '\t\t'
    )


    def hit_weapon():
        return (f'\t<WeaponTemplate id="{HIT}" RadiusDamageAffects="ENEMIES">\n\t\t'
                + _nuggets(f'<DamageNugget Damage="500.0" Radius="{RADIUS:g}" DamageType="EXPLOSIVE" DeathType="NORMAL" />')
                + '\n\t</WeaponTemplate>\n')


    def sweeper(id, firing, log=False):
        nug = _nuggets(f'<DamageNugget Damage="{AIM_DAMAGE:g}" Radius="1.0" DamageType="MAGIC" DeathType="NORMAL" />',
                       f'<ActivateLinearDamageNugget id="CNVSweepActivate" Lifetime="{LIFE:g}s" />',
                       f'<ActivateLaserNugget id="CNVSweepLaser" Lifetime="{LIFE:g}s" LaserId="1" />')
        hold = f'，开火持续 {firing:g} s' if firing else ''
        u = shot_v4(id, nug, extra=hit_weapon(), reload=RELOAD,
                    what=f'竖扫载体 V4（探针）：武器开伤害线 + 激光，LinearDamageUpdate（{TAG}）由近 {START:g} 到远 '
                         f'{START + LENGTH:g}、速度 {SPEED:g}{hold}')
        if firing:
            u.xml = _sub1(u.xml, '<FiringDuration\n\t\t\tMinSeconds="0s"\n\t\t\tMaxSeconds="0s"',
                          f'<FiringDuration\n\t\t\tMinSeconds="{firing:g}s"\n\t\t\tMaxSeconds="{firing:g}s"')
        u.xml = _sub1(u.xml, '<Behaviors>', (
            f'<Behaviors>\n'
            f'\t\t\t<LinearDamageUpdate id="{TAG}" StartDistanceOffset="{START:g}" Radius="{RADIUS:g}" Length="{LENGTH:g}"\n'
            f'\t\t\t\tSweepWeapon="{HIT}" Speed="{SPEED:g}" FollowTerrain="true" />\n'
            f'\t\t\t<LaserState id="ModuleTag_CNVSweepLaser" LaserId="1" />'
        ) + (CNV_LOG if log else ''))
        u.xml = _sub1(u.xml, '</Draws>', LASER_DRAW + '</Draws>')
        u.link.append(f'WeaponTemplate:{HIT}')
        u.names.update(hit=HIT, tag=TAG)
        u.params.update(start=START, radius=RADIUS, sweep_length=LENGTH, sweep_speed=SPEED, life=LIFE, firing=firing)
        return u


    def _n(lane, part):
        return f'UNIT - CNV Sweep {lane.title()} {part}'


    def mission(ext=True):
        m = Mission(name='CampSweep' if ext else 'CampSweepOff', map=probe_range,
                    units=[sweeper(tpl, firing, log=ext and lane == 'base') for lane, (tpl, firing) in LANES.items()]
                    + [target()], facts={}, ext=ext)
        m.waypoint('sweep spare', SPARE_WP, 'base gun', 0.0, -40.0)     # check c's second shooter
        for lane, (tpl, _) in LANES.items():
            site = f'{lane} gun'
            m.put(tpl, site, side='p1', role=f'{lane} sweeper', name=_n(lane, 'Shooter'))
            m.put(TARGET_ID, site, 0.0, AIM, side='s1', role=f'{lane} aim', name=_n(lane, 'Aim'))
            for k, d in enumerate(ROW):
                m.put(TARGET_ID, site, 0.0, d, side='s1', role=f'{lane} row {d:g}', name=_n(lane, f'Row{k}'))
        return m


    def sweep_test(m, lane='base', stop=None, then=(), run=RUN):
        """Check a: the base lane; b: the same, the shooter told NAMED_STOP `stop` s after the order (the near row is hit
        at ~9 frames, mid / far at ~18 / 26): does the damage line stop with the fire (mid / far never hit), and with
        ra3ext does the beam go out with it (ra3ext.log 'sweep ... end' line). Four counter lines at most; the other lane
        stays NO_ATTACK."""
        t = Test()
        held = [_n(x, p) for x in LANES for p in ['Shooter', 'Aim'] + [f'Row{k}' for k in range(len(ROW))]]
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
                                + [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in held]
                                + [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]))
        shooter = _n(lane, 'Shooter')
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('UNIT_CHANGE_OBJECT_STATUS', shooter, 'NO_ATTACK', 0),
                                 ('NAMED_ATTACK_NAMED', shooter, _n(lane, 'Aim')), ('SET_FLAG', 'Test Ordered', 1)]
                                + ([('SET_MILLISECOND_TIMER', 'Test Stop', stop)] if stop else [])
                                + [('SET_MILLISECOND_TIMER', f'Test Then {k}', secs) for k, (secs, _) in enumerate(then)]))
        t.scripts += [Script(f'Test - then {k}', [('TIMER_EXPIRED', f'Test Then {k}')], do) for k, (_, do) in enumerate(then)]
        if stop:
            t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'Test Stop')],
                                    [('UNIT_CHANGE_OBJECT_STATUS', shooter, 'NO_ATTACK', 1), ('NAMED_STOP', shooter)]))
        for k, label in list(enumerate(LABELS)) + [(len(LABELS), AIM_LABEL)]:
            c, tg = f'CNV_Sweep_{k}', _n(lane, f'Row{k}' if k < len(LABELS) else 'Aim')
            t.counters.append((c, label))
            t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
        # check a: every row Hammer is hit before the end (a counter that never stops reads ~15 a second); b only reads
        never = (run - ORDER - 2.0) * 15
        t.expect = ([(label, run - 1, '<', never) for label in LABELS + (AIM_LABEL,)] if not stop
                    else [(x, RUN - 1, '<', never) for x in (LABELS[0], AIM_LABEL)])
        t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=len(t.counters)))]
        return t


    # check c (deletion): the shooter killed KILL s after the order (the line walking, the beam on ours), a second one made
    # at SPARE_WP SPARE s after it (loaded RELOAD later), ordered at ORDER2 and deleted at DELETE (s after the first order)
    KILL, SPARE, ORDER2, DELETE, RUN_C, LAG = 0.9, 2.0, 9.0, 13.0, 26.0, 2.0
    SPARE_WP, ALIVE = 'Test Sweep Spare', '射手'


    def delete_test(m):
        """Check c: an object holding our modules (the sweep's damage line and laser, the CNVLog) killed mid-sweep, a new
        one made, swept once and deleted: the run ends, the counters read, and ra3ext.log has no line of a module after its
        object went (split by the create lines: heap addresses come back). The rows mid / far are hit by the second shooter
        (~ORDER2 x 15 frames) unless the killed one's line walks on (18 / 26). 射手: the base shooters alive."""
        first, spare, tpl = _n('base', 'Shooter'), _n('base', 'Spare'), LANES['base'][0]
        t = sweep_test(m, run=RUN_C, then=[
            (KILL, [('NAMED_KILL', first)]),
            (SPARE, [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', spare, tpl, m.team('p1'), m.mark('sweep spare')),
                     ('UNIT_CHANGE_OBJECT_STATUS', spare, 'NO_ATTACK', 1)]),
            (ORDER2, [('UNIT_CHANGE_OBJECT_STATUS', spare, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', spare, _n('base', 'Aim'))]),
            (DELETE, [('NAMED_DELETE', spare)])])
        aim = f'CNV_Sweep_{len(LABELS)}'            # four counter lines at most: 射手 takes 瞄's (the rows say it fired)
        t.counters = [c for c in t.counters if c[0] != aim]
        t.scripts = [s for s in t.scripts if s.name != f'Test - {aim} frames']
        t.expect = [e for e in t.expect if e[0] != AIM_LABEL]
        counted('CNV_Sweep_Alive', ALIVE, t, template=tpl)
        # the watch's seconds run LAG behind the mission's (bench 11-10 12:46: the kill at mission 8.9 read at s7, the make
        # at 10 at s9, the delete at 21 at s19)
        t.expect += [(ALIVE, 2, '==', 1, ORDER + KILL - LAG), (ALIVE, ORDER + SPARE - LAG + 1, '==', 1, ORDER + DELETE - LAG),
                     (ALIVE, ORDER + DELETE - LAG + 1, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=RUN_C, every=1, sheet=False, lines=len(t.counters)))]
        return t


    STOP = 0.9
    _CHECKS = {'a': sweep_test, 'b': lambda m: sweep_test(m, stop=STOP), 'c': delete_test}
    MISSION = {'engine_sweep': mission, 'engine_sweepoff': lambda: mission(False)}
    CHECKS = {'engine_sweep': _CHECKS, 'engine_sweepoff': _CHECKS}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        TAG=TAG))


def engine_tint():
    """New bench PASS2/90/2/90; PREDICT before bench: TintObjectsNugget changes color only.
    Use Laser probe's two1000HP Hammer lanes and100EXPLOSIVE one-shot guns;
    replace only high's ActivateLaserNugget with retail-style tint fields:
    PreColorTime0.5s, SustainedColorTime2s, PostColorTime0s, Frequency1,
    Amplitude0, ColorR2/G0/B0. Schema fields are color/animation parameters,
    no damage/movement/armor field. HP and hit timing should match control
    through tint expiry. Pixel rendering is not judged by this numeric probe.
    Initially empty clips load1s; fire6s; NO_ATTACK6+4/15; four counters.
    """
    from benches.weapon.firing.checks import engine_laser
    laser = engine_laser()["shared"]
    laser_mission = laser.mission
    check = laser.check

    def mission():
        m=laser_mission();m.name='CampTint'
        for u in m.units:
            u.xml=u.xml.replace('<ActivateLaserNugget LaserId="201" Lifetime="2s"/>',
                '<TintObjectsNugget PreColorTime="0.5s" SustainedColorTime="2s" PostColorTime="0s" Frequency="1" Amplitude="0"><Color R="2" G="0" B="0"/></TintObjectsNugget>')
        return m
    MISSION={'engine_tint':mission}
    CHECKS={'engine_tint':{'pair':check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


@cache
def engine_weaponfx():
    """Weapon round 1: PREDICTED before bench (2026-11-10).

    attribute: two 10000HP Hammer lanes. At6s each takes100 EXPLOSIVE;
    only high receives retail AttributeMod_TargetPainted (ARMOR150%,Duration1.1s).
    At6.5s a1000 hit: base89%, high84%; at9s after expiry another1000:
    base79%, high74%, both alive1. No fitted constants: the separate damage
    weapon has EXPLOSIVE100% on BaseTankArmor, both guns face the target front.
    Current simulator ignores the modifier nugget: predicts79/1/79/1.

    line:1000 EXPLOSIVE, LineWidth5, UseDynamicLineLength true, Overshoot200.
    10000HP Hammers at y450(target),350(before),550(after),x100/y450(outside).
    PREDICTED health90/90/90/100. Current simulator only damages the named
    victim:90/100/100/100. Geometry inclusion of full extents is INFERRED;
    these centres are deliberately far from the boundaries. Bench first round: attribute PASS79/1/74/1 (early89/1/84/1),
    line PASS90/90/90/100.
    No broad promotion
    from a limited probe; only explained fields may be registered.

    All clones load their initially EMPTY clip in1s; order>=6s, stop each
    one-shot burst after4/15s with NO_ATTACK. Float timers; at most4 lines.
    """
    import re
    from maps import probe_range
    from parts import Mission, Script, Test, square
    from benches.weapon.firing.checks import engine_clip
    clip_v4 = engine_clip()["shared"].clip_v4
    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    target = missile.target
    TARGET_ID = missile.TARGET_ID

    RUN = 16.0

    def gun(uid, damage, extra=''):
        u = clip_v4('bare', uid=uid, hit=damage,
                    spec=(0, 1/15, 1.0, 1, 'PRE_FIRE', (), RUN, 'weapon effect'))
        if extra:
            u.xml = u.xml.replace('</Nuggets>', extra + '</Nuggets>')
        return u


    def mission():
        return Mission(name='CampWx', map=probe_range, units=[], facts={})


    def check(m, which):
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        def put(template, lane, x, y, side, name):
            m.put(template, lane+' gun', x, y, side=side, angle=1.5708 if side=='p1' else 4.7124, name=name)
            start.append(('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1))
        def shoot(shooter, victim, at, suffix):
            fire, stop = 'Wfx Fire '+suffix, 'Wfx Stop '+suffix
            start.extend([('SET_MILLISECOND_TIMER', fire, float(at)),
                          ('SET_MILLISECOND_TIMER', stop, float(at+4/15))])
            t.scripts.extend([
                Script('Test - fire '+suffix, [('TIMER_EXPIRED',fire)],
                       [('UNIT_CHANGE_OBJECT_STATUS',shooter,'NO_ATTACK',0),('NAMED_ATTACK_NAMED',shooter,victim)]),
                Script('Test - stop '+suffix, [('TIMER_EXPIRED',stop)],
                       [('UNIT_CHANGE_OBJECT_STATUS',shooter,'NO_ATTACK',1)])])
        def hp(name, label):
            c='CNV_Wfx_'+label
            t.counters.append((c,label))
            t.scripts.append(Script('Test - hp '+label, [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',name,c)], once=False))
        def alive(name, label):
            c='CNV_Wfx_'+label
            t.counters.append((c,label))
            t.scripts.extend([Script('Test - alive '+label, [], [('SET_COUNTER',c,1)],once=False),
                              Script('Test - dead '+label,[('NAMED_DESTROYED',name)],[('SET_COUNTER',c,0)],once=False)])
        if which == 'line':
            u=gun('CNV_WfxLine',1000)
            u.xml=u.xml.replace('<DamageNugget ', '<LineDamageNugget LineWidth="5" UseDynamicLineLength="true" OverShootDistance="200" ')
            m.units=[u,target()]
            put(u.id,'base',0,0,'p1','Wfx Gun')
            for i,(x,y) in enumerate(((0,450),(0,350),(0,550),(100,450))):
                name='Wfx Target '+str(i)
                put(TARGET_ID,'base',x,y,'s1',name)
                hp(name,'HP'+str(i))
            shoot('Wfx Gun','Wfx Target 0',6.0,'line')
            values=(90,90,90,100)
        else:
            m.units=[target()]
            for lane in ('base','high'):
                extra = '<AttributeModifierNugget AttributeModifierName="AttributeMod_TargetPainted"/>' if lane=='high' else ''
                mark=gun('CNV_Wfx'+lane.title(),100,extra)
                m.units.append(mark)
                victim='Wfx '+lane+' target'
                shooter='Wfx '+lane+' marker'
                put(mark.id,lane,0,0,'p1',shooter)
                put(TARGET_ID,lane,0,450,'s1',victim)
                shoot(shooter,victim,6.0,lane+' mark')
                hit=gun('CNV_WfxHit'+lane.title(),1000)
                m.units.append(hit)
                hitter='Wfx '+lane+' hit'
                put(hit.id,lane,100,0,'p1',hitter)
                shoot(hitter,victim,6.5,lane+' early')
                shoot(hitter,victim,9.0,lane+' late')
                hp(victim,lane+'HP'); alive(victim,lane+'Alive')
            values=(79,1,74,1)
        t.scripts.insert(0,Script('Test - start',[],start))
        t.expect=[(label,RUN-2,'==',value,RUN) for (_,label),value in zip(t.counters,values)]
        t.bench=[('bench_watch',dict(seconds=RUN,every=.5,sheet=False,lines=len(t.counters)))]
        return t

    MISSION={'engine_weaponfx':mission}
    CHECKS={'engine_weaponfx':{k:(lambda m,k=k:check(m,k)) for k in ('attribute','line')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, shared=SimpleNamespace(
        check=check, gun=gun, mission=mission))


def engine_weaponset():
    """Engine unit test: weapon-set module -- which weapon a unit fires when the weapon's ObjectStatus / ForbiddenObjectStatus
    say so (engine line C round 9; docs/engine/weaponset.md). Retail writes the choice into the module: a Conscript's AK47
    is forbidden under GENERIC_TOGGLE_STATE and its Molotov needs it; a Guardian's cannon is forbidden under the toggle and
    its target painter (no damage) needs it; a mirage tank's cannon is replaced by the _Veteran one under WEAPON_UPGRADED_01.
    The simulator read the first PRIMARY_WEAPON of each slot whatever the status.

    On the range probe map, one lane each, an attacker of the player's at '<lane> gun' and a Tsunami tank of the enemy's
    (JapanAntiVehicleVehicleTech1, held NO_ATTACK so it never answers) 100 north. At ORDER the attacker is told to attack it:

      base     conscript   plain (AK47)
      high     conscript   GENERIC_TOGGLE_STATE from the start (Molotov)
      order    conscript   plain; GENERIC_TOGGLE_STATE given at TOGGLE (the weapon changes in the middle of the fight)
      removed  mirage      plain (the prism cannon)
      switch   mirage      WEAPON_UPGRADED_01 from the start (the Veteran cannon)
      low      guardian    GENERIC_TOGGLE_STATE from the start (the cannon is forbidden, the target painter does no damage)

    Counters: a: 基准血 / 毒瓶血 / 中途血 (the Tsunami's health in percent of the base / high / order lane); b: 棱镜血 /
    老兵血 / 涂靶血 (removed / switch / low lane). Every second.

    Bench 2026-11-09 (docs/engine/weaponset.md; WeaponSetUpdate registered): a at s41 基准 / 毒瓶 / 中途 = 42 / 9 / 21 (the Molotov
    lane loses ~2.2 %/s, the AK47 ~1.4 %/s; the order lane follows the base until the toggle at 12 s); b = 47 / 34 / 100: the
    mirage tank fires ONE shot (200 / veteran 250 of 380 hp) and then no more for 40 s (unexplained), the target painter
    does no harm. The simulator now picks the gun by status (simunits.weapon_sets); its mirage lanes still fire on.
    """
    from maps import probe_range
    from parts import Mission, Script, Test, counted

    CONSCRIPT, MIRAGE, GUARD, TANK = ('SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech3',
                                      'AlliedAntiVehicleVehicleTech1', 'JapanAntiVehicleVehicleTech1')
    LANES = {'base': CONSCRIPT, 'high': CONSCRIPT, 'order': CONSCRIPT, 'removed': MIRAGE, 'switch': MIRAGE, 'low': GUARD}
    START_STATUS = {'high': 'GENERIC_TOGGLE_STATE', 'switch': 'WEAPON_UPGRADED_01', 'low': 'GENERIC_TOGGLE_STATE'}
    ORDER, TOGGLE, RUN = 3.0, 12.0, 40.0


    def _n(lane, part):
        return f'UNIT - CNV Wset {lane.title()} {part}'


    def mission():
        m = Mission(name='CampWset', map=probe_range, units=[], facts={})
        for lane, tpl in LANES.items():
            m.put(tpl, f'{lane} gun', side='p1', role=f'{lane} attacker', name=_n(lane, 'Man'))
            m.put(TANK, f'{lane} gun', 0.0, 100.0, side='s1', role=f'{lane} tank', name=_n(lane, 'Tank'))
        return m


    def weaponset_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        tanks = [_n(lane, 'Tank') for lane in LANES]
        t.scripts.append(Script('Test - start', [], [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1) for u in tanks] + [
            ('UNIT_CHANGE_OBJECT_STATUS', _n(lane, 'Man'), st, 1) for lane, st in START_STATUS.items()] + [
            ('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER),
            ('SET_MILLISECOND_TIMER', 'Test Toggle', TOGGLE)]))
        t.scripts += [
            Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                   [('NAMED_ATTACK_NAMED', _n(lane, 'Man'), _n(lane, 'Tank')) for lane in LANES]),
            Script('Test - toggle', [('TIMER_EXPIRED', 'Test Toggle')],
                   [('UNIT_CHANGE_OBJECT_STATUS', _n('order', 'Man'), 'GENERIC_TOGGLE_STATE', 1)])]
        lines = ((('Base', '基准血'), ('High', '毒瓶血'), ('Order', '中途血')) if which == 'a' else
                 (('Removed', '棱镜血'), ('Switch', '老兵血'), ('Low', '涂靶血')))
        for key, label in lines:
            counted(f'CNV_Wset_{key}Hp', label, t, health=_n(key, 'Tank'))
        t.expect = [(lines[0][1], 0, 'ever<=', 99, RUN)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_weaponset': mission}
    CHECKS = {'engine_weaponset': {'a': weaponset_test, 'b': lambda m: weaponset_test(m, 'b')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


BENCHES = (
    engine_inform, engine_inform_ai, engine_inform_expiry, engine_inform_max,
    engine_inform_probe, engine_inform_radius, engine_scatter, engine_secondary,
    engine_shot, engine_strip, engine_suppress_probe, engine_suppression,
    engine_sweep, engine_tint, engine_weaponfx, engine_weaponset,
)
