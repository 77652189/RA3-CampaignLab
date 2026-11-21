"""engine.orders.target (command family C1): the picks on stand-ins -- the host's queries a plain reach rule."""
import itertools
import types

import numpy as np
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
from engine.orders import target  # noqa: E402

Q = types.SimpleNamespace(hostile=lambda a, t: a.owner != t.owner, can_hit=lambda w, t: True,
                          in_range=lambda a, t, w, d=None: np.hypot(t.x - a.x, t.y - a.y) - a.radius - t.radius <= 20,
                          side_sees=lambda s, t: True, shot_blocked=lambda a, t, w: False, reach_of=lambda w: 20,
                          unshot={'Ice'}, ai=())
SERIAL = itertools.count()


def body(x, owner='them', template='Tank', status=(), kinds=(), radius=0.0, **kw):
    kw = dict(mode='attack', acquire=(), ai_acquire=False, goal=None, weapons=[{}]) | kw
    return types.SimpleNamespace(x=x, y=0.0, owner=owner, template=template, status=set(status), kinds=set(kinds),
                                 radius=radius, alive=True, serial=next(SERIAL), **kw)


def pick(a, targets, aimable=None):
    got = target.picks(a, targets, {t.serial for t in targets} if aimable is None else aimable,
                       np.array([t.x for t in targets]), np.array([t.y for t in targets]), Q)
    return got and got[2][0]


def test_the_order_first_then_the_nearest_it_may_take():
    a, far = body(0, 'us'), body(15)
    skip = [body(5, template='Ice'), body(5, status={'NON_AUTOACQUIRABLE'}), body(5, kinds={'STRUCTURE'})]
    ties = [body(10) for _ in range(3)]                         # one point: the first in the list
    assert pick(a, skip + ties + [far]) is ties[0]
    a.goal = far
    assert pick(a, skip + ties + [far]) is far
    assert pick(a, skip + ties + [far], aimable=set()) is ties[0]        # the order's target out of the fight
    a.goal, a.mode = None, 'move'
    assert pick(a, ties) is None                                 # idle without AutoAcquireEnemiesWhenIdle YES
    assert pick(body(0, 'us', mode='move', acquire=('YES',)), ties) is ties[0]
    assert pick(a, [body(0, 'us')]) is None and target.picks(a, [], set(), np.array([]), np.array([]), Q) is None


def test_structures_and_the_reach_cut():
    hq, gun = body(5, kinds={'STRUCTURE'}), body(5, kinds={'STRUCTURE', 'FS_BASE_DEFENSE'})
    assert pick(body(0, 'us'), [hq, gun]) is gun
    assert pick(body(0, 'us', acquire=('ATTACK_BUILDINGS',)), [hq]) is hq
    assert target.takes_by_itself(body(0, 'us'), hq, types.SimpleNamespace(unshot=set(), ai={'us'}))
    near = body(3)                                              # review ll #4: a nearer tank, both rules still pick hq
    assert pick(body(0, 'us', ai_acquire=True), [hq]) is hq      # AI auto-acquire takes a plain structure
    assert pick(body(0, 'us', goal=hq), [near, hq]) is hq       # an order naming the structure beats the nearer foe
    big = body(60, radius=50.0)                                 # 60 by centre, 10 by edge: the biggest radius pads it
    assert pick(body(0, 'us'), [big]) is big
