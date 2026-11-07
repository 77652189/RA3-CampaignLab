"""Engine probe: strategic states switched by map flags (missions/aistate_bench.py) -- which of the AI's units leave
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
    inf, tank = m.cnv_units                 # the mission says (missions/aistate_bench.py), the check asks
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


CHECKS = {'aistate': {'a': a}, 'aistatenear': {'a': a}, 'aistateconst': {'a': a}, 'aistatefar': {'a': a}, 'aistateplain': {'a': a},
          'aistateslash': {'a': a}, 'aistateoff': {'off': off}, 'aistateoffhome': {'off': off},
          'aistateoff1': {'off': off}, 'aistateoffh': {'off': off}, 'aihunt': {'hunt': hunt}, 'aihunt2': {'hunt': hunt}}
