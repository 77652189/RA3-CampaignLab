"""The compile context a plan device (devices/) or a hand-written level (missions/a8, j4) is given: what it may ask of
the compiler and the mission, and the three outlets everything a player sees or a unit is told goes through.

  say(key, secs)                 the one way to show a line: the action that puts `key` on the caption strip
  camera(a, secs, in, out)       the camera moves a plan's 镜头 step compiles to (needs the compiler)
  order(kind, names, target)     the one way to tell named units what to do: 'attack' a named target, 'guard' an area

This step the outlets only hand over what the call sites spelled out themselves (the same actions, in the same order:
the build fingerprint does not move); `say` does not queue yet, that is the next stage. The rest is the small set of
things a device used to take from `self.c` (the compiler) and `self.m` (the mission) by reaching in: each is one line
that forwards, so a device can no longer touch what is not listed. A Ctx made without a compiler (a hand-written
level has none) answers say / order / tag and the mission's own; a compiler's questions raise PlanError.
"""
from plantime import PlanError

CAPTION = 'SHOW_MILITARY_CAPTION'        # the caption action is spelled here and nowhere else (tests/test_architecture G3a)
ATTACK = 'NAMED_ATTACK_NAMED'
GUARD = 'UNIT_GUARD_AREA'


def caption(key, secs):
    """The action that shows the strip text `key` for `secs` seconds."""
    return (CAPTION, key, secs)


def orders(kind, names, target):
    """The actions that tell each of `names` to attack the named `target` ('attack') or to hold the area `target`
    ('guard')."""
    if kind == 'attack':
        return [(ATTACK, n, target) for n in names]
    if kind == 'guard':
        return [(GUARD, n, target) for n in names]
    raise PlanError(f'order: no kind {kind!r}: attack, guard')


class Ctx:
    def __init__(self, compiler=None, mission=None, tag=None):
        if compiler is None and mission is None:
            raise PlanError('Ctx: needs a compiler or a mission')
        self._c = compiler
        self._m = mission if mission is not None else compiler.m
        self.tag = tag if tag is not None else compiler.tag

    # ---- the three outlets
    def say(self, key, secs):
        return caption(key, secs)

    def camera(self, a, secs, ease_in, ease_out):
        return self._compiler('camera').camera(a, secs, ease_in, ease_out)

    def order(self, kind, names, target):
        return orders(kind, names, target)

    # ---- the compiler's
    def _compiler(self, what):
        if self._c is None:
            raise PlanError(f'{what}: this level is written by hand, there is no plan compiler behind it')
        return self._c

    def unit(self, name, side='p1'):
        return self._compiler('unit').unit(name, side)

    def when(self, label, c, actions, **kw):
        return self._compiler('when').when(label, c, actions, **kw)

    def area(self, site):
        return self._compiler('area').area(site)

    def mark(self, site):
        """A waypoint at a site (published as a mark under the site's name), its name."""
        return self._compiler('mark').mark(site)

    def text(self, kind, s):
        return self._compiler('text').text(kind, s)

    def part_names(self, part):
        return self._compiler('part_names').part_names(part)

    def side(self, who):
        return self._compiler('side').side[who]

    def device(self, name):
        return self._compiler('device').devices[name]

    def plan_start(self, value):
        """The plan's own start phase times of `value` (what carrier.facts asks of the compiler's data)."""
        import plancheck
        c = self._compiler('plan_start')
        return plancheck.times_of(value, plancheck.phase_starts(c.d))

    # ---- the mission's
    def put(self, *a, **kw):
        return self._m.put(*a, **kw)

    def player(self, who):
        return self._m.player(who)

    def team(self, who):
        return self._m.team(who)

    def waypoint(self, *a, **kw):
        return self._m.waypoint(*a, **kw)

    def point(self, key):
        return self._m.point(key)

    def site(self, name, dx=0.0, dy=0.0):
        return self._m.site(name, dx, dy)

    def where(self, site):
        return self._m.where(site)

    def mark_of(self, key):
        """The waypoint a mark key (`ice 3`, `sea`) names."""
        return self._m.mark(key)

    def has_mark(self, key):
        return key in self._m.marks

    def add_area(self, name, area):
        self._m.areas[name] = area

    def add_point(self, name, xy):
        self._m.waypoints[name] = xy

    def spawns_add(self, *templates):
        """Templates the scripts create (the contract: they must be published)."""
        self._m.spawns.update(templates)

    def string(self, key, text, keep=False):
        """A string of the mission's table; `keep` leaves one already there."""
        if keep:
            self._m.strings.setdefault(key, text)
        else:
            self._m.strings[key] = text

    def countdown(self, timer):
        self._m.countdowns.append(timer)

    def add_unit(self, unit):
        self._m.units.append(unit)

    def add_role(self, key, role, later=False):
        self._m.cast[key] = role
        if later:
            self._m.later.add(key)

    def made(self, keys):
        return self._m.made(keys)

    def role(self, key):
        return self._m.cast[key]

    def roles(self):
        return list(self._m.cast.values())

    def compiled_scripts(self):
        return list(self._m.scripts)

    def fact(self, key, default=None):
        return self._m.facts.get(key, default)

    def has_fact(self, key):
        return key in self._m.facts

    def voice_has(self, group):
        """Whether the mission's voice pack has the voice group (True when there is no pack: nothing to be missing)."""
        voice = self._m.voice
        return voice is None or group in getattr(voice, 'groups', {group})
