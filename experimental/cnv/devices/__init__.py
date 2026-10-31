"""A level's own mechanics, for its plan (plan.py): each device type is a class a plan names in 机关 ({name: {类型:
<type>, ...}}). A device publishes, under its plan name:

  units   -- names the plan may write for units of ours it makes (冰幕工兵, 冰雕 ...): `names`
  events  -- conditions `<name>.<event> [args]`: cond(event, args) -> alternatives (plan.Compiler.cond)
  actions -- `<name>.<action> [args]`: action(what, args) -> script actions
  target  -- a wave told to 打 <name>: attack(unit names) -> scripts that keep them on it
and EVENTS / ACTIONS / TARGET (what each means), for plan_vocab. The cast parts, marks and facts it makes are the
mission's (checks ask the mission for them, as always).
"""


class Device:
    WHAT = ''
    PARAMS = {}
    EVENTS = {}
    ACTIONS = {}
    TARGET = ''

    def __init__(self, c, name, spec):
        self.c, self.m, self.name, self.spec = c, c.m, name, spec
        self.units, self.names = [], {}

    def place(self):
        """Objects and marks, once the plan's own start forces are placed."""

    def cond(self, event, args):
        raise self.unknown('event', event, self.EVENTS)

    def action(self, what, args):
        raise self.unknown('action', what, self.ACTIONS)

    def attack(self, names):
        from plan import PlanError
        raise PlanError(f'{self.name}: not a target a wave can attack')

    def scripts(self):
        """Its scripts (it may also add some through the compiler, c.when)."""
        return []

    def last(self):
        """Scripts that must come after every other script (a timer they set again, others wait on)."""
        return []

    def facts(self):
        return {}

    def unknown(self, kind, what, known):
        from plan import PlanError
        return PlanError(f'{self.name}: no {kind} {what!r}: {sorted(known)}')


def registry():
    """{device type (the plan's 类型): class}."""
    from devices import carrier, convoy, horn, ice_plazas, train
    return {'车队': convoy.Convoy, '冰雕广场': ice_plazas.IcePlazas, '号角': horn.Horn, '自由号': carrier.Carrier,
            '列车': train.Train}
