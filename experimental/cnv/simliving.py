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


def living(world, bodies, unspawned):
    views = world._living_views
    if views is None:
        views = world._living_views = _LivingViews()
    return views.living(bodies, unspawned)
