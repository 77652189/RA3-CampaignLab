"""Diagnostics bench scenes."""


def count_probes():
    """Two probes of the counters themselves (build.py digits --calibrate; build.py kinds), not levels."""
    import parts


    def digits():
        """A map that shows counters.CALIBRATION (every digit once), whose frame gives the counter reader's templates."""
        from maps import island
        values = [1234, 5678, 90]                   # experimental/testbench/counters.py CALIBRATION
        m = parts.Mission(name='CampDigits', map=island)
        t = parts.Test(counters=[(f'Digit {k}', '校准') for k in range(len(values))])
        t.scripts.append(parts.Script('Digits', [], [('SET_COUNTER', f'Digit {k}', v) for k, v in enumerate(values)]))
        t.bench = [('bench_watch', dict(seconds=3, every=3, sheet=False))]
        return m, t


    def kinds():
        """A probe of the counting itself: 3 Guardians and 2 buildings of ours, counted four ways at once -- by KindOf
        in an area (VEHICLE, STRUCTURE), by template in an area, by template owned. Should read 3 2 3 3 (the a8 assault's
        KindOf counts read 20 for 12 vehicles, 2026-10-21)."""
        from maps import island
        guardian = 'AlliedAntiVehicleVehicleTech1'
        m = parts.Mission(name='CampKinds', map=island)
        for dx in (-60, 0, 60):
            m.put(guardian, 'west field', dx, -60, role='guardian')
        m.put('AlliedWarFactory', 'base factory', angle=3.1416, role='factory')
        m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power')
        t = parts.Test()
        whole = m.where('island')
        t.areas['Test Whole Island'] = parts.square(whole.x, whole.y, whole.r + 300)
        parts.counted('Test Kind V', '类别车辆', t, kind=parts.kindof('VEHICLE'), area='Test Whole Island')
        parts.counted('Test Kind S', '类别建筑', t, kind=parts.kindof('STRUCTURE'), area='Test Whole Island')
        parts.counted('Test Type A', '型号区域', t, template=guardian, area='Test Whole Island')
        parts.counted('Test Type O', '型号拥有', t, template=guardian)
        t.expect += [('类别车辆', 3, '==', 3), ('类别建筑', 3, '==', 2), ('型号区域', 3, '==', 3), ('型号拥有', 3, '==', 3)]
        t.bench = [('bench_watch', dict(seconds=6, every=3, sheet=False))]
        return m, t


    PAIR_BUILDS = {'digits': digits, 'kinds': kinds}
    return dict(PAIR_BUILDS=PAIR_BUILDS)


def engine_kingref():
    """Level-line probe mission: why A4's Ghost King stood on the bridge and did not shoot the ice wall when the script
    re-gave its attack order every frame (devices/horn.py ghost_scripts before 11-07; checks/engine_kingref.py).

    A's engine_reorder probe (missions/reorder_bench.py) showed an Athena-type tank walks and fires under every-frame orders;
    A4's King is JapanAntiVehicleVehicleTech3 and its target was a SET_REF pick, so the probe here changes those two things:
    the attacker (King) and the way the wall is named (a name, or a SET_REF reference to an unnamed wall).

    The west field (island map), offsets from 'west field' (the same layout as the reorder probe):
      S (0, -400)  the attacker's birth point (an enemy s1 King, made at 1 s on the s1 crew 'Reo')
      W (0,  500)  the player's ice wall (no lifetime), 900 from S; named in the 'name' variants, unnamed in the 'ref' ones
    Published waypoints: s, mid (0, 0), near (0, 330).
    """
    from maps import island
    from parts import Mission
    from units import icewall as iw

    WALL = 'CNV_ReoWall'
    VARIANTS = ('kone', 'kevery', 'rone', 'revery', 'aref')
    S, W = (0.0, -400.0), (0.0, 500.0)


    def mission(name, variant):
        m = Mission(name=name, map=island, facts={'variant': VARIANTS.index(variant)})
        m.units += [iw.wall(WALL, length=60, shape='square', lifetime=None)]
        m.crew('Reo', 's1')
        named = variant in ('kone', 'kevery')
        m.put(WALL, 'west field', *W, role='wall', name='UNIT - CNV Reo Wall' if named else '')
        for part, label, at in (('s', 'S', S), ('mid', 'Mid', (0.0, 0.0)), ('near', 'Near', (0.0, 330.0))):
            m.waypoint(part, f'CNV Reo {label}', 'west field', *at)
        return m


    MISSION = {f'kingref_{v}': (lambda v=v: mission('CampKr' + v[:3].capitalize(), v)) for v in VARIANTS}
    return dict(MISSION=MISSION)


def music_bench():
    """Music jump timings, also used by experimental/music/timing.py."""
    def make():
        from missions.music_bench import mission
        return mission()

    return dict(MISSION={'music': make})



def _music_dyn_mission(**options):
    """The game's own dynamic music (its combat states: sdk SageXML/PathMusic) driving our A4 music
    (experimental/music/a4.py): the mission turns the system on and stages a fight the player first loses, then wins,
    then no more fighting. A recording of the game (experimental/music/bench_listen.py --nav) then says which section
    played when: listen.identify against a4.STREAMS (index.npz there).

      0 s        a4's start event (prep) and the dynamic system on (a4.DYNAMIC_SYSTEM)
      ENEMY_AT   enemy tanks and infantry attack-move onto the player's infantry, in the start camera's view: combat
                 (-> fierce); they kill many and lose few (-> SetAdvantageEnemy -> tense, after 20 s of combat)
      HELP_AT    a strong player force arrives and kills them (-> ResetAdvantage -> fierce)
      then quiet (-> Threat1_1 -> escort)

    Facts: enemy at, help at (mission seconds).
    """
    from maps import island
    from parts import Mission, Script

    from missions.music_bench import pack  # Initializes the shared music imports.
    from experimental.music import a4

    ENEMY_AT, HELP_AT = 5.0, 80.0
    ENEMY = {'JapanAntiVehicleVehicleTech1': 6, 'JapanAntiInfantryInfantry': 8}      # tsunami tanks, imperial warriors
    PLAYER = {'AlliedAntiInfantryInfantry': 16}                                       # peacekeepers
    # guardian tanks: 12 killed the enemy but never got the game to fire ResetAdvantage (bench 2026-10-26: it wants
    # twice as many kills as losses over 20 s, and 3 kills), so many more, to lose few
    HELP = {'AlliedAntiVehicleVehicleTech1': 24}


    SPY_VAR_CASES = ('UpYoursSoviet', 'UpYoursEmpire')     # spy: Threat1_1 plays the first's tracer if a4.PHASE_VAR
                                                           # holds 1, else the second's (what does the variable start at?)


    def _spy_pack():
        """Every event plays a tracer of its own, at once (ownmap.spy): the recording says which events the game's
        dynamic system fired when (bench_listen prints the tracer runs: stream = event index)."""
        from experimental.music import extract, ownmap
        b, lengths = ownmap.spy(extract.retail_map())
        secs = {e.name: s for e, s in zip(b.m.events, b.sections)}
        b.act(a4.EVENTS['calm'][0], ownmap.switch(a4.PHASE_VAR, {1: ownmap.goto(secs[SPY_VAR_CASES[0]], True)},
                                                  ownmap.goto(secs[SPY_VAR_CASES[1]], True)))
        return pack.make(b.m, pack.tracer_tracks(b.m, lengths))


    def _tracer_pack():
        """a4's own map, every stream a tracer (stream k plays tracer k): the recording says which stream the game
        played when, with no doubt between sections that sound alike."""
        from experimental.music import extract
        b, secs, lengths = a4.music_map(extract.retail_map())
        ours = lengths[:len(lengths) - len(b.kept)]                 # the shell's retail streams stay retail
        return pack.make(b.m, pack.tracer_tracks(b.m, ours, extract.retail_streams(b.kept)))


    def mission(name='CampMusDyn', spy=False, tracer=False, cue_at=None):
        """cue_at: a4's escort cue played then, before the fight (engine line: does a cue suspend the dynamic system?
        the program says it does, until it is turned on again)."""
        start, cue = a4.EVENTS['start'][0], a4.EVENTS['escort'][0]
        m = Mission(name=name, map=island, facts={'enemy at': ENEMY_AT, 'help at': HELP_AT},
                    music=pack.Later(_spy_pack if spy else _tracer_pack if tracer else a4.pack,
                                     {start} | ({cue} if cue_at is not None else set())))
        if cue_at is not None:
            m.scripts += [Script('CNV Music - Cue timer', [], [('SET_MILLISECOND_TIMER', 'CNV Music Cue', cue_at)]),
                          Script('CNV Music - Cue', [('TIMER_EXPIRED', 'CNV Music Cue')], [('PATH_MUSIC_PLAY_EVENT', cue)])]
        m.waypoint('fight', 'CNV Music Fight', 'west field')
        m.waypoint('help', 'CNV Music Help', 'west shore')
        k = 0
        for tmpl, n in PLAYER.items():
            for j in range(n):
                m.put(tmpl, 'west field', -60 + 40 * (j % 4), -60 + 40 * (j // 4))
        enemy = []
        for tmpl, n in ENEMY.items():
            for j in range(n):
                k += 1
                enemy.append(f'UNIT - CNV Music Enemy {k}')
                m.put(tmpl, 'east field', -100 + 50 * (j % 4), -60 + 60 * (j // 4), side='s1', name=enemy[-1],
                      role=f'enemy {k}')
        help_ = []
        for tmpl, n in HELP.items():
            m.spawns.add(tmpl)
            for j in range(n):
                help_.append((f'UNIT - CNV Music Help {j + 1}', tmpl))
        m.scripts += [
            Script('CNV Music - Start', [], [('PATH_MUSIC_PLAY_EVENT', start),
                                             ('PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM', a4.DYNAMIC_SYSTEM),
                                             ('SET_MILLISECOND_TIMER', 'CNV Music Enemy', ENEMY_AT),
                                             ('SET_MILLISECOND_TIMER', 'CNV Music Help', HELP_AT)]),
            Script('CNV Music - Enemy', [('TIMER_EXPIRED', 'CNV Music Enemy')],
                   m.order('attack_move', enemy, m.mark('fight'), 's1')),
            Script('CNV Music - Help', [('TIMER_EXPIRED', 'CNV Music Help')],
                   [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', n, t, m.team('p1'), m.mark('help')) for n, t in help_] +
                   m.order('attack_move', [n for n, _ in help_], m.mark('fight'), 'p1')),
        ]
        return m

    return mission(**options)


def music_dyn():
    MISSION = {
        'musicdyn': lambda: _music_dyn_mission(),
        'musicdynspy': lambda: _music_dyn_mission(name='CampMusDynS', spy=True),
        'musicdyntr': lambda: _music_dyn_mission(name='CampMusDynT', tracer=True),
        'musicdyncue': lambda: _music_dyn_mission(name='CampMusDynC', tracer=True, cue_at=20.0),
    }
    return dict(MISSION=MISSION)


def _music_route_mission(**options):
    """Router probe: what the engine does after a jump without PREP whose router has no pair for it (bench 2026-10-26,
    CampMusDynT: Combat took a4's prep, whose router knows only escort, to fierce; fierce played one segment and went
    on to final, with no event, past its own transition). Tracers: each segment its own stream (SECTIONS order).

      P1   router 1: [(T_P1E, E)]                   lacks F and G
      P2   router 2: [(T_P2F, F)]                   has F
      F    router 3: [(T_FE, E), (T_FX, X), (T_FY, Y)]
      G    router 4: [(T_GY, Y), (T_GE, E), (T_GX, X)]   F's targets in another order
      E X Y          loops, no router

    SCHEDULE fires, at known mission seconds: cuts (PREP) to P1 / P2 and plain jumps to F / G from them. Expected if a
    pending jump ends once taken: F (or G) then loops on itself. Facts: '<event key> <n>' = seconds.
    """
    from maps import island
    from parts import Mission, Script

    from missions.music_bench import ownmap, pack

    SEG_MS, T_MS = 4000, 1500
    LOOPS = ['P1', 'P2', 'F', 'G', 'E', 'X', 'Y']           # two segments each
    ROUTES = {'P1': [('E', 'T_P1E')], 'P2': [('F', 'T_P2F')],
              'F': [('E', 'T_FE'), ('X', 'T_FX'), ('Y', 'T_FY')], 'G': [('Y', 'T_GY'), ('E', 'T_GE'), ('X', 'T_GX')]}
    EVENTS = {'P1': ('S_A01BrightonThreat', True), 'P2': ('S_A02CannesBegin', True),
              'F': ('S_A01BrightonCombat', False), 'G': ('S_A01BrightonExplore', False)}
    SCHEDULE = [(2.0, 'P1'), (10.3, 'F'), (42.0, 'P2'), (50.3, 'F'), (82.0, 'P1'), (90.3, 'G'), (122.0, 'P2'),
                (130.3, 'G')]


    def streams():
        """[(section, ms)] in stream order: two segments per loop, then one per transition."""
        out = [(s, SEG_MS) for s in LOOPS for _ in range(2)]
        return out + [(t, T_MS) for routes in ROUTES.values() for _, t in routes]


    def events(swap=False):
        """swap: F and G trade events (bench 2026-10-26: G, jumped to from P1, kept replaying its first segment while F
        did not -- the event or the section?)."""
        if not swap:
            return EVENTS
        return {**EVENTS, 'F': EVENTS['G'], 'G': EVENTS['F']}


    def music_map(base, swap=False, cover=False):
        """cover: every router also gets a pair straight to each plain jump's target it lacks (b, b): no jump is left
        without a pair (does that cure G?)."""
        b = ownmap.Builder(base)
        secs, k = {}, 0
        route_of = {s: i + 1 for i, s in enumerate(ROUTES)}
        for s in LOOPS:
            secs[s] = b.section([k, k + 1], router=route_of.get(s, 0))
            b.loop(secs[s])
            k += 2
        for routes in ROUTES.values():
            for target, t in routes:
                secs[t] = b.section([k])
                k += 1
        for routes in ROUTES.values():
            for target, t in routes:
                b.link(secs[t], secs[target])
        b.m.routers = [[(secs[t].entry, secs[target].entry) for target, t in routes] for routes in ROUTES.values()]
        if cover:
            plain = [secs[key].entry for key, (_, prep) in EVENTS.items() if not prep]
            for pairs in b.m.routers:
                pairs += [(e, e) for e in plain if e not in {to for _, to in pairs}]
        for key, (event, prep) in events(swap).items():
            b.on(event, secs[key], prep=prep)
        for shell in ('MenuTrack', 'BriefingTrack'):
            b.on(shell, secs['E'], prep=True)
        return b, [ms for _, ms in streams()]


    def _pack(swap=False, cover=False):
        from experimental.music import extract
        b, lengths = music_map(extract.retail_map(), swap, cover)
        return pack.make(b.m, pack.tracer_tracks(b.m, lengths))


    def facts():
        seen, out = {}, {}
        for t, key in SCHEDULE:
            seen[key] = seen.get(key, 0) + 1
            out[f'{key} {seen[key]}'] = t
        return out


    def mission(name='CampMusRoute', swap=False, cover=False):
        ev = events(swap)
        m = Mission(name=name, map=island, facts=facts(),
                    music=pack.Later(lambda: _pack(swap, cover), {e for e, _ in ev.values()}))
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', 0, 0, name='UNIT - CNV Music Route Guardian', role='listener')
        m.scripts.append(Script('CNV Music Route - Start', [], [('SET_MILLISECOND_TIMER', f'CNV Music Route {k}', t)
                                                                for k, (t, _) in enumerate(SCHEDULE)]))
        m.scripts += [Script(f'CNV Music Route - {k} {key}', [('TIMER_EXPIRED', f'CNV Music Route {k}')],
                             [('PATH_MUSIC_PLAY_EVENT', ev[key][0])]) for k, (_, key) in enumerate(SCHEDULE)]
        return m

    return mission(**options)


def music_route():
    MISSION = {
        'musicroute': lambda: _music_route_mission(),
        'musicrouteswap': lambda: _music_route_mission(name='CampMusRouteW', swap=True),
        'musicroutecover': lambda: _music_route_mission(name='CampMusRouteC', cover=True),
    }
    return dict(MISSION=MISSION)


def probe():
    """Engine probe for plan-driven missions (docs/story/plans): what a level plan's standard operations rely on, each
    read back as a counter by checks/probe.py.

      - difficulty: three copies of a script, each with one difficulty bit (retail's only switch), set a counter to
        1 / 2 / 3 -- which one runs is the difficulty the game was started on;
      - money: PLAYER_SET_MONEY, read back with SET_PLAYER_MONEY_TO_COUNTER;
      - borders: the festival map's second border (west of the canal) at the start, back to the whole map (0) at
        `open at` -- checked by hand (checks/probe.py: the camera is held west of the canal until then);
      - autosave: CAMPAIGN_CREATE_AUTO_SAVE once a few seconds in (save=False: none -- the bench 2026-10-24 crashed
        ~4 s in, but every start that day failed alike: another game held the screen, see harness.DEVICE_HINT).

    Facts: open at, money.
    """
    from maps import festival
    from parts import Mission, Script

    OPEN_AT, MONEY = 25.0, 4321


    def mission(name='CampProbe', save=True):
        m = Mission(name=name, map=festival, facts={'open at': OPEN_AT, 'money': MONEY})
        west = list(festival.BORDERS).index('west of the canal')
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', 250, 30, name='UNIT - CNV Probe Guardian', role='guardian')
        m.strings['AUTOSAVE:CNVCAMPAIGN'] = '新战役（自动存档）'
        m.scripts += [
            Script('CNV Probe - Start', [], [('MAP_SWITCH_BORDER', west),('PLAYER_SET_MONEY', m.player('p1'), MONEY),
                                             ('SET_MILLISECOND_TIMER', 'CNV Probe Open', OPEN_AT),
                                             ('SET_MILLISECOND_TIMER', 'CNV Probe Save', 5.0)]),
            Script('CNV Probe - Open', [('TIMER_EXPIRED', 'CNV Probe Open')],
                   [('MAP_SWITCH_BORDER', 0)]),
            *([Script('CNV Probe - Save', [('TIMER_EXPIRED', 'CNV Probe Save')],
                      [('CAMPAIGN_CREATE_AUTO_SAVE', 'AUTOSAVE:CNVCAMPAIGN')])] if save else []),
            *[Script(f'CNV Probe - Difficulty {k}', [], [('SET_COUNTER', 'CNV_Probe_Difficulty', k)],
                     levels=tuple(j == k for j in (1, 2, 3))) for k in (1, 2, 3)],
            Script('CNV Probe - Money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('p1'), 'CNV_Probe_Money')],
                   once=False)]
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'probe': lambda: mission(),
        'probe_nosave': lambda: mission(name='CampPrbN', save=False),
    }
    return dict(MISSION=MISSION)


def render_war():
    """Render line probe (docs/research/rendering.md "第 0 步结果"): a big battle in the start camera's view that keeps going,
    to measure drawn frames (capture shim log) against logic frames (a script counter) under each renderer setup.

    The west field (island map), offsets from 'west field' (x east): the player's Allied army west of the centre, s1's Soviet
    army east of it, ROWS x COLS each, GAP apart, the fronts 2 x FRONT apart; each side's reinforcements come in at its
    rear waypoint (checks/render_war.py keeps them topped up and attacking the other side's rear).
    Published waypoints: west rear, east rear.
    """
    from maps import island
    from parts import Mission

    ALLIED = ('AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryVehicle', 'AlliedAntiStructureVehicle',
              'AlliedAntiInfantryInfantry')
    SOVIET = ('SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech3', 'SovietAntiStructureVehicle',
              'SovietAntiInfantryInfantry')
    ROWS, COLS, GAP, FRONT = 6, 8, 35.0, 150.0


    def mission(name):
        m = Mission(name=name, map=island, facts={})     # checks/render_war.py keeps its own copy of the kinds (G5)
        m.spawns |= set(ALLIED + SOVIET)
        for side, kinds, sign in (('p1', ALLIED, -1), ('s1', SOVIET, 1)):
            for r in range(ROWS):
                for c in range(COLS):
                    m.put(kinds[(r + c) % len(kinds)], 'west field', sign * (FRONT + r * GAP),
                          (c - (COLS - 1) / 2) * GAP, side=side)
        m.waypoint('west rear', 'CNV Rw West', 'west field', -(FRONT + ROWS * GAP + 60), 0.0)
        m.waypoint('east rear', 'CNV Rw East', 'west field', FRONT + ROWS * GAP + 60, 0.0)
        return m


    MISSION = {'render_war': lambda: mission('CampRndr')}
    return dict(MISSION=MISSION)


def shikigami():
    """The shikigami's bench scene on the west field: two groups 400 apart (A west, B east), each a VIP of ours (a
    Japanese engineer, standing in for Yuriko) with a shikigami 30 east of him, and two enemy conscripts 300 south.

    Published (the cast): vip A, vip B, guard A, guard B, shooter A 1 .. 2, shooter B 1 .. 2.
    """
    from maps import island
    from parts import Mission
    from units import shikigami as sk

    VIP = 'JapanEngineer'
    SHOOTER = 'SovietAntiInfantryInfantry'          # the conscript


    V4 = 'SovietAntiStructureVehicle'               # V4 rockets: 500 out, not flagged NOT_ATTRACTED_BY_MAGNETS


    def shells(name='CampShikiV', **unit):
        """Shells bending: two groups 400 apart, each a VIP with a shikigami 120 east of him (he stays within its 200;
        a rocket bent onto it bursts away from him) and an enemy V4 launcher 400 south of the VIP (outside the 200: it is
        not made to retarget, only its rockets can bend). Published (the cast): vip A / B, guard A / B, launcher A / B."""
        u = sk.shikigami(**unit)
        m = Mission(name=name, map=island, units=[u])
        for tag, dx in (('A', -100.0), ('B', 300.0)):
            m.put(VIP, 'west field', dx, 150, name=f'UNIT - CNV VIP {tag}', role=f'vip {tag}')
            m.put(u.id, 'west field', dx + 120, 150, name=f'UNIT - CNV Shikigami {tag}', role=f'guard {tag}')
            m.put(V4, 'west field', dx, -250, side='s1', name=f'UNIT - CNV Launcher {tag}', role=f'launcher {tag}')
        return m


    def mission(name='CampShiki', **unit):
        u = sk.shikigami(**unit)
        m = Mission(name=name, map=island, units=[u])
        for tag, dx in (('A', -50.0), ('B', 350.0)):
            m.put(VIP, 'west field', dx, 100, name=f'UNIT - CNV VIP {tag}', role=f'vip {tag}')
            m.put(u.id, 'west field', dx + 30, 100, name=f'UNIT - CNV Shikigami {tag}', role=f'guard {tag}')
            for k, sx in enumerate((-25, 25)):
                m.put(SHOOTER, 'west field', dx + sx, -200, side='s1', name=f'UNIT - CNV Shooter {tag}{k + 1}',
                      role=f'shooter {tag} {k + 1}')
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'shikigami': lambda: mission(),
        'shikigami_shells': lambda: shells(),
    }
    return dict(MISSION=MISSION)


BENCHES = (
    count_probes, engine_kingref, music_bench, music_dyn, music_route,
    probe, render_war, shikigami,
)
