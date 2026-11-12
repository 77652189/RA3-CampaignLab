"""Prediction: only the host bound to Iron Curtain protects against enemy fire.

Identical retail clones keep the module, remove it, or bind it to Vacuum Bomb.
All cast Iron Curtain by script at frame 75. The existing j probe supplies the
two tanks and enemy fire; NAMED_DAMAGE is deliberately absent because it bypasses
protection. This measures the module dispatch boundary, not general OCL behavior.

E63: a matching module bound to a legal empty OCL should still dispatch one
cast event, but create no protection. The retail reference is the positive
control; enemy fire and the bounded observation window stay identical.

E64: a new local reference with the identical retail CreateObject payload
should protect both tanks and dispatch once, just like the positive control.
This measures protection, not a count of generated objects.
"""
from checks.engine_super import super_test


def check(m, valid, casts=None):
    t = super_test(m, 'j')
    # Five-element expectations bound the protection window: it ends normally
    # around s28, so an unbounded "from s12" would falsely require immortality.
    t.expect = [(label, 12, '==' if valid else '<', 100, 20)
                for label in ('血0', '血150')]
    if valid:
        t.expect += [(label, 30, '<', 100) for label in ('血0', '血150')]
    t.expect.append(('施放数', 12, '==', int(valid) if casts is None else casts))
    return t


CHECKS = {'engine_oclcurtain': {'a': lambda m: check(m, True)},
          'engine_oclcopy': {'a': lambda m: check(m, True)},
          'engine_oclempty': {'a': lambda m: check(m, False, casts=1)},
          'engine_oclnone': {'a': lambda m: check(m, False)},
          'engine_oclwrong': {'a': lambda m: check(m, False)}}
