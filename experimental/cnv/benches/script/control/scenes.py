"""Standalone script control scenes."""

from maps import island
from parts import Mission

TANK, PK = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'


def _n(part):
    return f'UNIT - CNV S1 {part}'


def scripts1_mission(name='CampScr1'):
    """Island scene for the batch 1 script probes.

    The player's Guardians on crew Go head east from the west field. Two idle Guardians
    and crew Pk stand apart from Go. Enemy crew Hunt and a lone Guardian start in the
    east field. The checks use marks far, far2, home, ehome and lhome.
    """
    m = Mission(name=name, map=island, units=[], facts={})
    m.spawns |= {TANK, PK}
    go, pk, hunt = m.crew('Go'), m.crew('Pk'), m.crew('Hunt', 's1')
    for k, dy in enumerate((-100.0, 0.0), 1):
        m.put(TANK, 'west field', -50.0, dy, angle=0.0, name=_n(f'Go {k}'), role=f'go {k}', props={'originalOwner': go})
    for k, dy in enumerate((150.0, 250.0), 1):
        m.put(TANK, 'west field', -50.0, dy, angle=0.0, name=_n(f'Idle {k}'), role=f'idle {k}')
    for k, dx in enumerate((-100.0, 0.0), 1):
        m.put(PK, 'west field', dx, -300.0, angle=0.0, name=_n(f'Pk {k}'), role=f'pk {k}', props={'originalOwner': pk})
    for k, dy in enumerate((-60.0, 60.0), 1):
        m.put(TANK, 'east field', 0.0, dy, side='s1', angle=3.1416, name=_n(f'Hunt {k}'), role=f'hunt {k}',
              props={'originalOwner': hunt})
    m.put(TANK, 'east 1', side='s1', angle=3.1416, name=_n('Lone'), role='lone')
    m.waypoint('far', 'CNV S1 Far', 'west field', 600.0, -50.0)
    m.waypoint('home', 'CNV S1 Home', 'west field', -50.0, -50.0)
    m.waypoint('far2', 'CNV S1 Far2', 'west field', 600.0, 200.0)
    m.waypoint('ehome', 'CNV S1 EHome', 'east field')
    m.waypoint('lhome', 'CNV S1 LHome', 'east 1')
    return m


def drive():
    """Engine probe for ADR 0010 (docs/adr/0010-question-first.md, the graybox): can the map's own scripts play the
    player's side, so a "playstyle script" runs a level unattended and the counters give the verdict (win, time, losses,
    money)? Read back by checks/drive.py.

    Niagara map: the player's yard, a power plant and a barracks (Allied, money MONEY) at the start, three Guardians by
    the base; the hawks (Soviet, s1) three Hammers at `front` (west end of the island bridge, the same bank).

      - commands: one script order each -- MOVE_NAMED_UNIT_TO, NAMED_ATTACK_NAMED, ATTACK_MOVE_TEAM_TO on the player's
        own default team (a8's assault already ran the last one, 2026-10-21);
      - production, how the player's barracks might be made to build: nothing (control), SKIRMISH_AI_START on the
        human player (what a retail mission does to wake an AI), PLAYER_ENABLE_UNIT_CONSTRUCTION;
      - run: the whole loop of a playstyle script -- every ORDER_EVERY s the team attack-moves at the enemy, every
        GIVE_EVERY s one more Guardian appears at the base (what the barracks would have made: "给兵" standing in for
        the economy), the run ends by itself (a flag stops the clock) and the readout is time, losses, the end state.

    Facts: money, give every, order every.
    """
    import resources
    from maps import niagara
    from parts import Mission

    GUARDIAN, HAMMER, BARRACKS = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech1', 'AlliedBarracks'
    MONEY, GIVE_EVERY, ORDER_EVERY = 6000, 20.0, 8.0


    def mission(name='CampDrive', hammers=3, who='drive'):
        m = Mission(name=name, map=resources.measured(niagara), facts={'money': MONEY, 'give every': GIVE_EVERY, 'order every': ORDER_EVERY})
        m.spawns |= {BARRACKS, GUARDIAN, 'AlliedPowerPlant'}        # what the AI may build, the checks count
        m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard')
        m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power')
        m.put(BARRACKS, 'base factory', angle=3.1416, role='barracks')
        for k, (dx, dy) in enumerate(((0, -60), (0, 0), (0, 60))):
            m.put(GUARDIAN, 'base edge', dx, dy, name=f'UNIT - CNV {who} Guardian {k + 1}', role=f'guardian {k + 1}')
        for k in range(hammers):
            m.put(HAMMER, 'front', 0, -80 + 80 * k, side='s1', name=f'UNIT - CNV {who} Hammer {k + 1}',
                  role=f'hammer {k + 1}')
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'drive_idle': lambda: mission('CampDrvI'),
        'drive_ai': lambda: mission('CampDrvA'),
        'drive_enable': lambda: mission('CampDrvE'),
        'drive_cmd': lambda: mission('CampDrvM', hammers=1),
        'drive_run': lambda: mission('CampDrvR'),
    }
    return dict(MISSION=MISSION)


def engine_aichange():
    """A: the AI's subsystem switches PLAYER_AI_CHANGE* (engine line A round 294; retail a06 presses four of them "on").

    C's aiallbuildoff (missions/aiallbuild_bench.py: s1 Allied AI woken at 10 s, its enemies the player and s5's twenty
    tanks) with the switch pressed in the wake script, right after the AI takes over:

      aiubon     no switch (the control)
      aiuboff    PLAYER_AI_CHANGEUNITBUILDER 0
      aiubback   ... 0, then 1 at 40 s
      aitboff    PLAYER_AI_CHANGETEAMBUILDER 0 and PLAYER_AI_CHANGE_ECONOMY_MANAGER 0

    Prediction (INFERRED, from the program; private work/re/a293_changebuilder.md): unit builder 0 turns off two of the
    AI's builders (both on by default) -- what they do is not read yet, so whether units stop is the question; team
    builder and economy manager do nothing whatever the value (their index falls through), so aitboff builds as aiubon.
    """
    from missions.aiallbuild_bench import mission as allbuild
    from parts import Script

    UNIT, TEAM, ECONOMY = ('PLAYER_AI_CHANGEUNITBUILDER', 'PLAYER_AI_CHANGETEAMBUILDER',
                           'PLAYER_AI_CHANGE_ECONOMY_MANAGER')
    BACK_AT = 40.


    def mission(name, off=(), back=False):
        m = allbuild(False)
        m.name = name
        for o in m.objects:     # s5's tanks 250 south: AllBuild's grid stands six on trees and fences (tests/test_maps.py)
            o.y -= 250. if o.name.startswith('CNV AllB tank') else 0.
        m.scripts = [s for s in m.scripts if not s.name.startswith('CNV AllB')]      # no 70 s friendship
        ai = m.player('s1')
        m.facts['switched off'] = ' '.join(off) or 'none'
        next(s for s in m.scripts if s.name == 'CNV AI - Wake').do += [(x, ai, 0) for x in off]
        if back:
            m.facts['back on at'] = BACK_AT
            m.scripts += [Script('CNV AISw back timer', [], [('SET_MILLISECOND_TIMER', 'CNV AISw Back', BACK_AT)]),
                          Script('CNV AISw back', [('TIMER_EXPIRED', 'CNV AISw Back')], [(x, ai, 1) for x in off])]
        return m


    MISSION = {'aiubon': lambda: mission('CampAISwOn'),
               'aiuboff': lambda: mission('CampAISwUOff', (UNIT,)),
               'aiubback': lambda: mission('CampAISwBack', (UNIT,), back=True),
               'aitboff': lambda: mission('CampAISwTOff', (TEAM, ECONOMY))}
    return dict(MISSION=MISSION)


def engine_aiflip():
    """A: the all-enemies building action after a relation change (engine line A round 274).

    C's aiallbuildon / aiallbuildoff (missions/aiallbuild_bench.py) set the secondary enemy s5 in the Start script and
    never changed it before the end of the run, so the action could not show anything. Here s5 (twenty Hammer tanks)
    starts as s1's friend and turns enemy both ways at 5 s; s1 wakes at 10 s as in C's.

      aiallflipon     the action at the wake (10 s, after the change)
      aiallflipoff    no action
      aiallfliplate   the action at 3 s (before the change)
      aiallflipnever  no action, s5 stays a friend (the control: s5 is not in the enemies whatever the action does)

    Prediction (INFERRED, from the program; notes in the private work/re/a273_consider_all.md): the AI's building
    enemies are a snapshot taken at the start and retaken by the action only, so off / late / never build alike and
    on differs (the twenty tanks count: more anti-vehicle). Read by teamlog.build_picks / build_orders, same frames.
    """
    from missions.aiallbuild_bench import mission as allbuild
    from missions.aiskirm_bench import FRIEND
    from parts import Script

    ACTION = 'SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING'
    ENEMY = (0, 0.0, 'Enemy')
    FLIP_AT, LATE_AT = 5., 3.
    AFTER_FLIP, AFTER_ACT = 15., 20.     # round 2: the change after the wake (10 s), the action after that


    def mission(name, when, flip=FLIP_AT, act=LATE_AT):
        """when: 'wake' / 'late' (the action at `act`) / None (no action) / 'never' (no action and no change)."""
        m = allbuild(when == 'wake')
        m.name = name
        m.facts['consider all'] = {'wake': 10, 'late': act}.get(when, 0)
        m.facts['enemy at'] = 0 if when == 'never' else flip
        ai, secondary = m.player('s1'), m.player('s5')
        # C's 70 s friendship is past the run's end (C's runs reached f598 at most); drop it, the change here is the flip
        m.scripts = [s for s in m.scripts if not s.name.startswith('CNV AllB') or 'friend' not in s.name]
        start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
        pair = ((ai, secondary), (secondary, ai))
        start.do = [d for d in start.do if not (d[0] == 'PLAYER_RELATES_PLAYER' and (d[1], d[2]) in pair)]
        start.do += [('PLAYER_RELATES_PLAYER', a, b, FRIEND) for a, b in pair]
        if when != 'never':
            start.do.append(('SET_MILLISECOND_TIMER', 'CNV AllF Flip', flip))
            m.scripts.append(Script('CNV AllF flip', [('TIMER_EXPIRED', 'CNV AllF Flip')],
                                    [('PLAYER_RELATES_PLAYER', a, b, ENEMY) for a, b in pair]))
        if when == 'late':
            start.do.append(('SET_MILLISECOND_TIMER', 'CNV AllF Late', act))
            m.scripts.append(Script('CNV AllF late', [('TIMER_EXPIRED', 'CNV AllF Late')], [(ACTION, ai)]))
        return m


    MISSION = {'aiallflipon': lambda: mission('CampAllFOn', 'wake'),
               'aiallflipoff': lambda: mission('CampAllFOff', None),
               'aiallfliplate': lambda: mission('CampAllFLate', 'late'),
               'aiallflipnever': lambda: mission('CampAllFNever', 'never'),
               # round 2: on / off / late all built like s5-enemy-from-the-start, never apart -- the change at 5 s
               # reached the building enemies with no action. These move the change past the wake (15 s): the wake
               # retaking the snapshot vs the enemies following the relation as it changes.
               'aiallflipwoff': lambda: mission('CampAllFWOff', None, flip=AFTER_FLIP),
               'aiallflipwon': lambda: mission('CampAllFWOn', 'late', flip=AFTER_FLIP, act=AFTER_ACT)}
    return dict(MISSION=MISSION)


def engine_aistart():
    # A270: compare the no-library wake modes and pause a library-enabled AI.
    from missions.aiskirm_bench import mission

    MISSION = {
        'aistart': lambda: mission('CampAIStart', lib=False, wake='start'),
        'ainowake': lambda: mission('CampAINoWake', lib=False, wake=None),
        'aistartx': lambda: mission('CampAIStartX', lib=False, wake='startx'),
        'aixfer': lambda: mission('CampAIXfer', lib=False, wake='team'),
        'aipause': lambda: mission('CampAIPause'),
    }
    return dict(MISSION=MISSION)


def engine_basegate():
    # A269: base construction gate on the skirmish AI.
    from missions.aiskirm_bench import mission

    MISSION = {
        'aibgate': lambda: mission('CampAIBGate'),
    }
    return dict(MISSION=MISSION)


def engine_killcount():
    """Throwaway native kill-credit scene for C's counter action probe."""
    from maps import probe_border
    from parts import Mission


    def mission():
        m = Mission(name='CampKillCount', map=probe_border, units=[], facts={})
        for side, dx in (('p1', 0.), ('s5', 1800.)):
            for i, template in enumerate(('SovietAntiInfantryInfantry',
                                          'SovietAntiInfantryInfantry',
                                          'AlliedAntiVehicleVehicleTech1')):
                for role, kind, owner, x in ((f'{side} gun {i}', 'AlliedAntiVehicleVehicleTech1', side, dx),
                                              (f'{side} victim {i}', template, 's4', dx+130.)):
                    m.put(kind, 'stop row', x, -2300.+i*650., side=owner,
                          angle=0., name='CNV Kill '+role, role=role)
        for i, role in enumerate(('script', 'alive')):
            m.put('SovietAntiInfantryInfantry', 'stop row', 3500., -2300.+i*650.,
                  side='s4', angle=0., name='CNV Kill '+role, role=role)
        return m


    MISSION = {'engine_killcount': mission}
    return dict(MISSION=MISSION)


def engine_scripts1():
    MISSION = {'engine_scripts1': scripts1_mission}
    return dict(MISSION=MISSION)


def engine_scripts2():
    """Engine probe mission (inventory: the inferred script items, checks/engine_scripts2.py): PLAYER_RELATES_PLAYER (one
    way? '<All Players>'?) and PLAYER_HAS_OBJECT_COMPARISON (are the dying counted?).

    Island map (+y is north):
      west field  `mcv a` the player's AlliedMCV (unarmed) at (-50, 0); `gun a` the enemy's (s1, Soviet_1, no AI)
                  Guardian 120 east of it, facing it -- only the enemy can shoot here
      east field  `mcv b` the enemy's AlliedMCV at (0, 0); `gun b` the player's Guardian 120 west of it, facing it --
                  only the player can shoot here (~1800 from the west pair)
      east 3      `tank 1`, `tank 2` the player's Guardians, 60 apart (~900 from east field): counted, one killed
    Published (the cast): mcv a, gun a, mcv b, gun b, tank 1, tank 2.
    """
    from maps import island
    from parts import Mission

    TANK, MCV = 'AlliedAntiVehicleVehicleTech1', 'AlliedMCV'


    def _n(part):
        return f'UNIT - CNV S2 {part}'


    def mission(name='CampScr2'):
        m = Mission(name=name, map=island, units=[], facts={})
        m.spawns |= {TANK, MCV}
        m.put(MCV, 'west field', -50.0, 0.0, angle=0.0, name=_n('Mcv A'), role='mcv a')
        m.put(TANK, 'west field', 70.0, 0.0, side='s1', angle=3.1416, name=_n('Gun A'), role='gun a')
        m.put(MCV, 'east field', 0.0, 0.0, side='s1', angle=3.1416, name=_n('Mcv B'), role='mcv b')
        m.put(TANK, 'east field', -120.0, 0.0, angle=0.0, name=_n('Gun B'), role='gun b')
        for k, dx in enumerate((-30.0, 30.0), 1):
            m.put(TANK, 'east 3', dx, 0.0, angle=0.0, name=_n(f'Tank {k}'), role=f'tank {k}')
        return m


    MISSION = {'engine_scripts2': mission,
               'engine_scripts3': lambda: mission('CampScr3')}     # checks/engine_scripts3.py: counter math, DISABLE_INPUT
    return dict(MISSION=MISSION)


def engine_scripts8b():
    from missions.super_bench import mission

    MISSION = {
        'engine_scripts8bs': lambda: mission('CampS8bS', True),
        'engine_scripts8bm': lambda: mission('CampS8bM', most=True),
    }
    return dict(MISSION=MISSION)


def team():
    """K6 engine probe (ADR 0016): what a map's own team does when a script orders it as one (checks/team.py).

    Three convoy trucks stand on the west field, placed on the team `Probe` (the map's Teams chunk, Mission.crew; the
    objects' originalOwner), 300 west of `far` (a mark and a trigger area): the questions are whether a placed unit joins
    the team, whether a whole-team order reaches a unit made on the team later, what the team's conditions read when its
    members die, and whether the survivors both move.

    Published (the cast): truck 1 .. 3; marks far, late (where a late member is made); the team (m.teams['Probe']).
    """
    from maps import island
    from parts import Mission
    from units import convoy

    SPEED = 25.0


    def mission(name='CampTeam', crewed=True):
        """crewed=False: the trucks on the player's default team (the control: does a truck move at all here)."""
        truck = convoy.truck(speed=SPEED)
        m = Mission(name=name, map=island, units=[truck])
        props = {'originalOwner': m.crew('Probe')} if crewed else {}
        for k, dy in enumerate((-60, 0, 60), 1):
            m.put(truck.id, 'west field', dy, -300, name=f'UNIT - CNV Probe Truck {k}', role=f'truck {k}',
                  angle=0.0, props=props)
        m.waypoint('far', 'CNV Probe Far', 'west field', 0, 300)      # the train bench's leg: land all the way (x -300
        m.waypoint('late', 'CNV Probe Late', 'west field', 150, -300)  # was cut by a band of water, bench 2026-11-04)
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'team': lambda: mission(),
        'team_plain': lambda: mission(name='CampTeamP', crewed=False),
    }
    return dict(MISSION=MISSION)


BENCHES = (
    drive, engine_aichange, engine_aiflip, engine_aistart,
    engine_basegate, engine_killcount, engine_scripts1, engine_scripts2,
    engine_scripts8b, team,
)
