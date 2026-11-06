"""Engine probe: strategic states switched by map flags (missions/aistate_bench.py) -- which of the AI's units leave
its base, and how many frames after their state's flag went on.

  a  步兵在家 / 坦克在家   Peacekeepers / Guardians of s1 inside the base area (450 around the east base), once a second
     步兵等帧 / 坦克等帧   frames from the flag going on while all four are still home (stops at the first to leave)

Expected if ScriptedFlagHeuristic follows SET_FLAG and a team takes only what its filter names: the infantry go
after INF_AT and the tanks stay home till TANK_AT, then the tanks go. The waits are the reading (the model,
RA3-EngineModel ra3model/ai/states.py, re-weighs states every 15 frames).
Builds: aistate (target only the player's yard, ~2600 away), aistatenear (+ a player power plant ~750 away),
aistateconst (near, and both states always on: does a team go at all).

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


CHECKS = {'aistate': {'a': a}, 'aistatenear': {'a': a}, 'aistateconst': {'a': a}, 'aistateplain': {'a': a},
          'aistateslash': {'a': a}}
