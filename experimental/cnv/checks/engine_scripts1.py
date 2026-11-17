"""Engine probe, inventory batch 1 (docs/engine/inventory.md; the program read in work/re/l2_scripts1.md): mission
missions/scripts1_bench.py. What the notes predict is in brackets; the readings go below.

  cond    条件位 = the sum, every frame, of 1 PLAYER_IS_HUMAN_OR_AI_PERSONALITY(Player_1, Human) [1], 2 (Soviet_1,
          Human) [2: "Human" = the player has no AI] until UNIT_AI_TRANSFER_ALL(Soviet_1, 1) at AI_AT [then 0],
          4 (Soviet_1, AIP_A01_Coop_AlliedSpecialForces) [0], 8 HAS_FINISHED_AUDIO of a line never played [8: true],
          16 HAS_FINISHED_VIDEO of a clip never played [?: false if unregistered reads false].
          状态 = 1 UNIT_HAS_OBJECT_STATUS(idle 1, NO_ATTACK), set at 2 s and cleared at 5 s [1 between]
          + 2 the same of idle 2, set at the start and killed at KILL_AT [2 until then; 0 once it is gone]
  xfer    crew Go sent to `far` (650 east) at 1 s, TEAM_TRANSFER_TO_PLAYER(Go, Soviet_2) at XFER_AT. 易主 = go 1
          owned by Soviet_2 [1 from XFER_AT]; 到终点 = how many of go 1-2 in `far` [0: the move is cleared];
          离家 = how many left `home` (150) [2: they had started]; 队里几个 = crew Go's members [0: on Soviet_2's team]
  idle    idle 1 and 2 sent to `far2` at 1 s; UNIT_IDLE_FOR_SECONDS(idle 1, 3) at IDLE_AT. 一到 / 二到 = 1 while
          idle k is in `far2` [二到 at ~1 + 900 / speed; 一到 never: the move is cleared; or 3 s late]
  hunt    TEAM_HUNT(Hunt) and NAMED_HUNT(lone) at 2 s, (s1 has no AI); TEAM_HUNT(Go) the player's. 敌队离家 /
          孤狼离家 / 我队离家 = how many left their marks (250) [the notes: a flag bit and the unit's AI woken, nobody
          reads it outside an AI player's HuntTactic: 0 0 0?]
  button  TEAM_USE_COMMANDBUTTON_ABILITY(Pk, Command_ToggleRiotShieldSpecialPower) at 2 s. 举盾 = the player's
          objects with GENERIC_TOGGLE_STATE [2 from 2 s]

读数
Bench 2026-11-08 (one run each; the bench's seconds run ~2 s behind the game's; sim pairs in tests/test_simbench.py
test_scripts1_* / test_video_* / test_audio_*):
  cond    条件位 9 all run: Player_1 Human (1), a line never played reads done (8); Soviet_1 NOT Human from the start
          and after the wake (a campaign computer player has its AI object), the personality 0, a clip never played
          not done. 状态 3 -> 1 (idle 2 killed: false at once) -> 0 (idle 1 cleared).
  xfer    易主 1 from s3; 到终点 0 all 40 s (both had left home: 离家 2 before the hand-over) -- the move dropped;
          队里几个 2 -> 0 at the hand-over. (A first run had the tanks in the sea at -300: nobody moved.)
  idle    二到 1 from s7; 一到 0 all 45 s: UNIT_IDLE_FOR_SECONDS drops the order, it does not pause it.
  hunt    敌队离家 孤狼离家 我队离家 0 0 0 all 60 s: hunting without an AI player's tactic moves nobody.
  button  举盾 2 from s1 (the first reading): every member pressed. The simulator has no toggle (strict xfail).
"""
from parts import Script, Test, counted, square, status

AI_AT, KILL_AT, XFER_AT, IDLE_AT = 8.0, 4.0, 4.0, 3.0
RUN = {'cond': 12.0, 'xfer': 40.0, 'idle': 45.0, 'hunt': 60.0, 'button': 10.0}
LINE, CLIP = 'MA01_AlliedIntel24', 'CNVTEST01'
SHIELD, BUTTON = 'GENERIC_TOGGLE_STATE', 'Command_ToggleRiotShieldSpecialPower'


def _at(t, key, secs, actions):
    """actions at `secs` s from the start (a timer of its own)."""
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def _sum(t, counter, label, parts):
    """counter = the sum of the weights whose condition holds, recounted every frame. parts: [(weight, condition)]."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', w, counter)], once=False)
                  for k, (w, c) in enumerate(parts)]


def _away(t, counter, label, names, mark_point, r):
    """counter = how many of `names` are outside a square of half-side r around mark_point."""
    area = f'Test {counter} Home'
    t.areas[area] = square(*mark_point, r)
    _sum(t, counter, label, [(1, ('NAMED_OUTSIDE_AREA', n, area)) for n in names])


def _watch(t, run, every=1.0):
    t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]


def cond(m):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    i1, i2 = m.role('idle 1').name, m.role('idle 2').name
    na = status('NO_ATTACK')
    t.scripts.append(Script('Test - start', [], [('UNIT_CHANGE_OBJECT_STATUS', i2, na, 1)]))
    _at(t, 'set', 2.0, [('UNIT_CHANGE_OBJECT_STATUS', i1, na, 1)])
    _at(t, 'clear', 5.0, [('UNIT_CHANGE_OBJECT_STATUS', i1, na, 0)])
    _at(t, 'kill', KILL_AT, [('NAMED_KILL', i2)])
    _at(t, 'ai', AI_AT, [('UNIT_AI_TRANSFER_ALL', s1, 1)])
    _sum(t, 'CNV_S1_Cond', '条件位', [(1, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', p1, 'Human')),
                                      (2, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, 'Human')),
                                      (4, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, 'AIP_A01_Coop_AlliedSpecialForces')),
                                      (8, ('HAS_FINISHED_AUDIO', LINE)), (16, ('HAS_FINISHED_VIDEO', CLIP))])
    _sum(t, 'CNV_S1_Status', '状态', [(1, ('UNIT_HAS_OBJECT_STATUS', i1, na)), (2, ('UNIT_HAS_OBJECT_STATUS', i2, na))])
    _watch(t, RUN['cond'], 0.5)
    return t


def xfer(m):
    t = Test()
    go = m.teams['Go']
    names = [m.role(f'go {k}').name for k in (1, 2)]
    _at(t, 'go', 1.0, [('MOVE_TEAM_TO', go, m.mark('far'))])
    _at(t, 'xfer', XFER_AT, [('TEAM_TRANSFER_TO_PLAYER', go, m.player('s2'))])
    counted('CNV_S1_Owner', '易主', t, owner=names[0], player=m.player('s2'))
    t.areas['Test S1 Far'] = square(*m.point('far'), 80.0)
    _sum(t, 'CNV_S1_Far', '到终点', [(1, ('NAMED_INSIDE_AREA', n, 'Test S1 Far')) for n in names])
    _away(t, 'CNV_S1_Left', '离家', names, m.point('home'), 150.0)
    t.counters.append(('CNV_S1_Members', '队里几个'))
    t.scripts += [Script(f'Test - members {n}', [('TEAM_COMPARE_NUM_MEMBERS', go, 2, n)],
                         [('SET_COUNTER', 'CNV_S1_Members', n)], once=False) for n in range(3)]
    _watch(t, RUN['xfer'])
    return t


def idle(m):
    t = Test()
    names = [m.role(f'idle {k}').name for k in (1, 2)]
    _at(t, 'go', 1.0, [('MOVE_NAMED_UNIT_TO', n, m.mark('far2')) for n in names])
    _at(t, 'idle', IDLE_AT, [('UNIT_IDLE_FOR_SECONDS', names[0], 3)])
    t.areas['Test S1 Far2'] = square(*m.point('far2'), 80.0)
    for k, n in enumerate(names, 1):
        counted(f'CNV_S1_At{k}', '一到' if k == 1 else '二到', t, named=n, area='Test S1 Far2')
    _watch(t, RUN['idle'])
    return t


def hunt(m):
    t = Test()
    _at(t, 'hunt', 2.0, [('TEAM_HUNT', m.teams['Hunt']), ('NAMED_HUNT', m.role('lone').name),
                         ('TEAM_HUNT', m.teams['Go'])])
    _away(t, 'CNV_S1_EAway', '敌队离家', [m.role(f'hunt {k}').name for k in (1, 2)], m.point('ehome'), 250.0)
    _away(t, 'CNV_S1_LAway', '孤狼离家', [m.role('lone').name], m.point('lhome'), 250.0)
    _away(t, 'CNV_S1_GAway', '我队离家', [m.role(f'go {k}').name for k in (1, 2)], m.point('home'), 250.0)
    _watch(t, RUN['hunt'], 2.0)
    return t


def button(m):
    t = Test()
    _at(t, 'press', 2.0, [('TEAM_USE_COMMANDBUTTON_ABILITY', m.teams['Pk'], BUTTON)])
    counted('CNV_S1_Shield', '举盾', t, status=status(SHIELD), most=3)
    _watch(t, RUN['button'], 0.5)
    return t


CHECKS = {'engine_scripts1': {'cond': cond, 'xfer': xfer, 'idle': idle, 'hunt': hunt, 'button': button}}
