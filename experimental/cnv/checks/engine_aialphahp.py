"""AlphaStrike health contrast: target damage and surviving return, not internal state.

Prediction: the named target's guards cause retreat in the low lane;
the high lane gives priority to finishing the 70% target. No exact boundary
or exact order frame is claimed. See missions/aialphahp_bench.py.

Bench 2026-11-11, corrected float health script: low PASS / high FAIL.
Both target HP70 s1-85, far2 s15-16, home4 s26-41, all four live to s85.
The high-lane finishing hypothesis below is retained as a diagnostic FAIL,
not retuned to the observation. This pair does not isolate AlphaStrike.
Only first-cycle arrival/return/unchanged HP replay is tested; no field
promotion. Missing target applicability evidence: work/re/handoff-c.md.
The first pair used integer70 (empty float slot, target dead s1); invalid,
not an AlphaStrike negative. The corrected pair changes only 70 -> 70.0.
"""
from checks import engine_airetreat as ar
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
