"""GrapplingHookUpdate (E226, bench benches/weapon/firing/readings.toml#engine_grapple): the Apocalypse's harpoon. A
GrapplingHookNugget hit (engine/combat/grapple.py) hooks the target; while its thing holds the ObjectStatusValidation's
RequiredStatus (the toggle's GENERIC_TOGGLE_STATE) and the target is of a KeepAliveObjectFilter kind, it pulls the
target straight at its thing PullRate a second (the bench: 160 and 260 away, both about 40) until it is within its
thing's radius (INFERRED; the bench: 25-50 centre to centre, the two radii's 55 too far), then fires SingleFireWeapon (the crush, its 1 s delay) and, from
ContinuousFireWeaponDelay on, ContinuousFireWeapon every GRIND -- each at the target's spot (World.fire).
Not modelled: the bounce (BouncePercentage), a hooked structure, a hook let go and taken again."""
import math

from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15
GRIND = 4           # frames between grinds: SovietHarpoonGrindWeapon's FiringDuration + ClipReloadTime, 0.24 s (INFERRED)


class GrappleData(module.ModuleData):
    def __init__(self, rate=0.0, single='', grind='', delay=0.0, need=frozenset(), keep=frozenset()):
        self.rate, self.single, self.grind, self.delay, self.need, self.keep = rate, single, grind, delay, need, keep

    @classmethod
    def parse(cls, head, inner):
        need = {s for h, _ in templates.blocks(inner, 'ObjectStatusValidation')
                for s in (templates.attr(h, 'RequiredStatus') or '').split()}
        keep = {k for h, _ in templates.blocks(inner, 'KeepAliveObjectFilter')
                for k in (templates.attr(h, 'Include') or '').split()}
        return cls(templates.num(templates.attr(head, 'PullRate'), 0.0), templates.attr(head, 'SingleFireWeapon', ''),
                   templates.attr(head, 'ContinuousFireWeapon', ''),
                   templates.secs(templates.attr(head, 'ContinuousFireWeaponDelay') or '0s'), frozenset(need),
                   frozenset(keep))


@factory.module('GrapplingHookUpdate')
class Grapple(module.Module, interfaces.Update, interfaces.Grapple):
    """In the frame order's frame_movers cell while it holds a target: pulls it a frame's PullRate, or grinds it."""
    DATA = GrappleData
    PHASE = 'frame_movers'
    STATE = ('target', 'touched')
    RECORDED = ()
    target = None       # the hooked thing
    touched = False     # it reached the hooker (the crush is fired)

    def hook(self, target):
        if self.target is not target:
            self.target, self.touched = target, False
            self.world.wake(self)

    def update(self, frame):
        b, t, d = self.thing, self.target, self.data
        if (t is None or not (b.alive and t.alive) or not d.need <= module.status_now(b)
                or not d.keep & set(t.kinds)):
            self.target = None
            return interfaces.SLEEP
        if self.touched:
            self.world.fire(b, d.grind, at=(t.x, t.y))
            return GRIND
        dx, dy = b.x - t.x, b.y - t.y
        far = math.hypot(dx, dy)
        step = min(d.rate / FPS, max(0.0, far - b.radius))
        if far:
            t.x, t.y = t.x + dx / far * step, t.y + dy / far * step
        if step < d.rate / FPS:
            self.touched = True
            self.world.fire(b, d.single, at=(t.x, t.y))
            return max(1, round(d.delay * FPS))
        return 1
