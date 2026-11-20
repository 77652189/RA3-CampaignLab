"""The simulator's ordered living-body views, shared by Sim and the skirmish AI."""
from engine.kernel import interfaces


class Alive:
    """Keep the dataclass field in vars(body) for snapshots and invalidate at the write."""

    def __get__(self, body, owner=None):
        return True if body is None else body.__dict__.get('alive', True)

    def __set__(self, body, value):
        body.__dict__['alive'] = value
        health = body.find(interfaces.Body)
        if health is not None and health.world is not None:
            health.world.invalidate_living()


class _LivingViews:
    _registry = _live = _unspawned = None
    _size = 0

    def invalidate(self):
        self._registry = self._live = self._unspawned = None

    def living(self, bodies, unspawned):
        if self._registry is not bodies or self._size != len(bodies):
            live = [body for body in bodies.values() if body.alive]
            self._registry, self._size, self._live, self._unspawned = bodies, len(bodies), live, None
        if unspawned and self._unspawned is None:
            self._unspawned = [body for body in self._live if body.spawn_parent is None]
        return (self._unspawned if unspawned else self._live).copy()


def refuse_living(bodies, name):
    """Sim.add's rule for a name (coord ruling 11-19 17:15, the same-name sweep): one a living thing holds is refused
    (ValueError) before anything is made. The game makes no second object to a name (CREATE_NAMED_ON_TEAM_AT_WAYPOINT,
    simact_world), and whatever keeps a thing by identity (a walk-in, a queue, a mine) must not be left holding one
    that silently left the world. A dead or deleted one's name may be taken again.
    The one exception is the map load (Sim.add shadow=True): a map naming two objects alike (15 of the 27 retail
    maps, e.g. a01 'UNIT - Bench 01' three times) -- the later takes the name in the earlier's place in bodies, the
    earlier leaves the world before anything holds it, as before this rule. The game keeping both, the name the
    first's, is INFERRED and an intended change of its own (work/re/handoff-r.md)."""
    held = bodies.get(name)
    if held is not None and held.alive:
        raise ValueError(f'Sim.add: {name!r} is held by a living {held.template}; kill or delete it first')


def living(world, bodies, unspawned):
    views = world._living_views
    if views is None:
        views = world._living_views = _LivingViews()
    return views.living(bodies, unspawned)
