"""敌方AI 分档 on the bench (plan.py compile_ai): ai_plan_bench's plan (Niagara, the Allied AI on a construction yard
at the east base, lots of money) with its IFVs held back -- let go STEP after it woke. Read back by checks/aistep.py.
The IFV, not the guardian tank: bench 2026-10-27, this AI built four IFVs (the first ~135 s after waking, the last
~180 s) and never a guardian, held back or not, even with a liking for them (aistep_free).

Facts: wake at, step (seconds after waking the IFVs are let go), watch.
"""
import plan
from missions import ai_plan_bench as ap

STEP, WATCH = 150.0, 300.0                      # let go after the control (aistep_free) had its first IFV
HELD = '多功能步兵车'


def mission(name='CampStep', held=True):
    """held=False: the control -- nothing held back."""
    d = dict(ap.PLAN, 关卡='as')
    d['敌方AI'] = dict(ap.PLAN['敌方AI'])
    if held:
        d['敌方AI']['分档'] = [{'当': f'敌方AI 醒来 + {STEP:g}', '放开': [HELD]}]
    m = plan.Compiler(d, name).compile()
    m.facts.update({'wake at': ap.WAKE_AT, 'step': STEP, 'watch': WATCH})
    return m
