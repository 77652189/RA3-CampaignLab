"""Engine probe, the inferred script items (docs/engine/inventory-levels-a.md): counter arithmetic and DISABLE_INPUT.
Mission: missions/scripts2_bench.py's island scene as build engine_scripts3. What the model / simulator predicts is
in brackets; the readings go below.

  math   SET_COUNTER at the start, then at OP_AT one COUNTER_MATH_COUNTER(counter, op, 'CNV_S3_Four' = 4) each:
         加 3 op 0 [7], 减 3 op 1 [-1: no floor at 0], 乘 3 op 2 [12], 除 13 op 3 [3]. The model
         (RA3-EngineModel ra3model/scripts.py) reads 0 / 1 off retail's use (a total of kills; what is left of the
         transports); 2 / 3 were its guess.
  input  DISABLE_INPUT at the start, ENABLE_INPUT at FREE_AT. At GO_AT MOVE_NAMED_UNIT_TO(tank 1, 'Test S3 Go', 300
         south of east 3) [走到 1 by ~GO_AT + 10: a script's order is not the player's input -- the simulator keeps
         DISABLE_INPUT a flag nothing reads]; B血 = the enemy MCV the player's Guardian shoots [falls from the start:
         the unit's own fire is not input]; 负数 = SET 2, DECREMENT_COUNTER 5 at GO_AT [-3]; 除负 = SET -13, op 3 by
         4 at GO_AT [-3: C's division truncates toward 0, -4 would be floor].

读数
Bench 2026-11-09 (one run each; sim pairs tests/test_simbench.py test_scripts3_*; docs/engine/script-semantics.md
3 and 8.13):
  math   CampScr3Math_mcp_1109_063100: 3 3 3 13 at s1, 7 -1 12 3 from s2 -- all four as the model. (-1 read "?"
         at first: the counter reader dropped the minus as a speck; experimental/testbench/counters.minus since.)
  input  CampScr3Input_mcp_1109_063847 (frames re-read with the fixed reader; the running bench server still had
         the old one): 走到 1 from bench s9 (the move, given at 7 while locked, done), B血 98 -> 96 then back to 100
         (the Guardian's ~4 s on the unarmed MCV, as in scripts2), 负数 -3 and 除负 -3 from s6. With DISABLE_INPUT
         at 1 s (and at the start) bench_start failed: Esc opened no mission menu -- the lock takes Esc too.
"""
from parts import Script, Test, counted, square

OP_AT, LOCK_AT, GO_AT, FREE_AT = 3.0, 5.0, 7.0, 20.0
RUN = {'math': 10.0, 'input': 24.0}
FOUR = 'CNV_S3_Four'


def _at(t, key, secs, actions):
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def _watch(t, run):
    t.bench = [('bench_watch', dict(seconds=run, every=0.5, sheet=False, lines=len(t.counters)))]


def math(m):
    t = Test()
    rows = [('CNV_S3_Add', '加', 3, 0), ('CNV_S3_Sub', '减', 3, 1), ('CNV_S3_Mul', '乘', 3, 2), ('CNV_S3_Div', '除', 13, 3)]
    t.counters += [(c, label) for c, label, _, _ in rows]
    t.scripts.append(Script('Test - start', [], [('SET_COUNTER', FOUR, 4)] + [('SET_COUNTER', c, v) for c, _, v, _ in rows]))
    _at(t, 'op', OP_AT, [('COUNTER_MATH_COUNTER', c, op, FOUR) for c, _, _, op in rows])
    t.expect += [('加', OP_AT + 3, '==', 7, RUN['math']), ('减', OP_AT + 3, '==', -1, RUN['math']),
                 ('乘', OP_AT + 3, '==', 12, RUN['math']), ('除', OP_AT + 3, '==', 3, RUN['math'])]
    _watch(t, RUN['math'])
    return t


def input_(m):
    t = Test()
    tank = m.role('tank 1').name
    t.waypoints['Test S3 Go'] = m.site('east 3', 0.0, -300.0)
    t.areas['Test S3 Go Area'] = square(*m.site('east 3', 0.0, -300.0), 80.0)
    counted('CNV_S3_At', '走到', t, named=tank, area='Test S3 Go Area')
    counted('CNV_S3_B', 'B血', t, health=m.role('mcv b').name)
    t.counters += [('CNV_S3_Neg', '负数'), ('CNV_S3_NegDiv', '除负')]
    t.scripts.append(Script('Test - start', [], [('SET_COUNTER', FOUR, 4), ('SET_COUNTER', 'CNV_S3_Neg', 2),
                                                ('SET_COUNTER', 'CNV_S3_NegDiv', -13)]))
    _at(t, 'lock', LOCK_AT, [('DISABLE_INPUT',)])   # after bench_start's Esc check: locked from the start, Esc
                                                    # opened no menu and the bench could not start (11-09)
    _at(t, 'go', GO_AT, [('MOVE_NAMED_UNIT_TO', tank, 'Test S3 Go'), ('DECREMENT_COUNTER', 5, 'CNV_S3_Neg'),
                         ('COUNTER_MATH_COUNTER', 'CNV_S3_NegDiv', 3, FOUR)])
    _at(t, 'free', FREE_AT, [('ENABLE_INPUT',)])
    t.expect += [('走到', GO_AT + 12, '==', 1, FREE_AT), ('负数', GO_AT + 3, '==', -3, RUN['input']),
                 ('除负', GO_AT + 3, '==', -3, RUN['input'])]
    _watch(t, RUN['input'])
    return t


CHECKS = {'engine_scripts3': {'math': math, 'input': input_}}
