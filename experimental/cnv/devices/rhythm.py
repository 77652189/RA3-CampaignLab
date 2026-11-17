"""节律: groups of units that switch between two states on a beat, each group with its own phase (docs/design/draft-inventory.md
class 7, "按时无敌或区域效果": A8's platforms rising and falling with the swell; S2's ice armour, A9's charging balls, S8's vents,
A3's time zones are the same shape). A state is an upgrade of the unit's own (units/platform.py: `on` and `off`, each
applying an attribute modifier -- range, invulnerable, damage ...); the device grants the one and takes the other away,
for every unit of the group, at the group's beat. Nothing here knows what the states are.

  机关: {浪: {类型: 节律, 单位: 浪涌炮塔, 开始: 开局 + 0:20, 周期: 60, 开: 25,
              组: [{角色: gun 1, 相位: 0}, {角色: gun 2, 相位: 20}, {角色: gun 3, 相位: 40}]}}

单位: a roster name whose Unit publishes names {on, off} (the two upgrade ids). 开始: when the beat starts (default 开局).
周期: seconds for one round (on, then off). 开: seconds a round spends on (the rest is off). 相位: seconds after the
start a group first turns on (default 0, may exceed 周期's share: every group turns on once per 周期). 组 角色: the
units of the group, by role (a role with a count is all of them). All groups start off.

Published: events `开 <角色>` (that group is on now), `关 <角色>` (started, and that group is off now), `开始`;
action `停` (the beat stops where it is), `继续`.
"""
from devices import Device
from parts import Script


def key_of(name):
    """The ASCII key a plan name (Chinese) gives the device's scripts, flags and timers (the map stores Latin-1)."""
    import hashlib
    return 'Beat' + hashlib.sha1(name.encode('utf-8')).hexdigest()[:5]


def on_flag(tag, name, k):
    """The flag that is 1 while group k of device `name` is on (what a check reads)."""
    return f'CNV_{tag}_{key_of(name)}_On_{k}'


class Rhythm(Device):
    WHAT = '一批单位按节拍在两种状态之间切换（升级一开一关），每组有自己的相位：平台随浪、冰甲、充能的球、喷口都是它'
    PARAMS = {'单位': '名册里的单位名；它公开 on/off 两个升级', '开始': '条件：什么时候开始打拍子（默认 开局）',
              '周期': '秒：开一阵、关一阵合起来多长', '开': '秒：每个周期里开着多久',
              '组': '一串 {角色: <角色名>, 相位: <秒>}：这一组单位和它第一次开的时刻（开始后多少秒）'}
    EVENTS = {'开始': '节拍开始了', '开 <角色>': '这一组现在是开的', '关 <角色>': '节拍已经开始，这一组现在是关的'}
    ACTIONS = {'停': '节拍停在原地（各组状态不再变）', '继续': '节拍接着走'}

    def __init__(self, ctx, name, spec):
        super().__init__(ctx, name, spec)
        from plantime import PlanError
        from units import roster
        if '单位' not in spec or spec['单位'] not in roster.NAMES:
            raise PlanError(f'{name}: 节律 needs 单位, one of {sorted(roster.NAMES)}')
        made = roster.make(spec['单位'])[0]
        if set(made.names) < {'on', 'off'}:
            raise PlanError(f'{name}: the unit {spec["单位"]!r} publishes no on/off upgrades')
        self.on_up, self.off_up = made.names['on'], made.names['off']
        self.period, self.on_for = float(spec.get('周期', 60)), float(spec.get('开', 30))
        if not 0 < self.on_for < self.period:
            raise PlanError(f'{name}: 开 {self.on_for:g} must be between 0 and 周期 {self.period:g}')
        self.groups = []
        for g in spec.get('组') or []:
            if not isinstance(g, dict) or '角色' not in g:
                raise PlanError(f'{name}: 组 {g!r} -- each {{角色: <role>, 相位: <seconds>}}')
            self.groups.append((str(g['角色']), float(g.get('相位', 0))))
        if not self.groups:
            raise PlanError(f'{name}: 节律 needs 组')
        self.key = key_of(name)
        base = f'CNV_{ctx.tag}_{self.key}'
        self.started, self.held = f'{base}_Started', f'{base}_Held'
        self.state = {role: on_flag(ctx.tag, name, k) for k, (role, _) in enumerate(self.groups)}
        self.timer = {role: f'CNV {ctx.tag} {self.key} Timer {k}' for k, (role, _) in enumerate(self.groups)}

    def cond(self, event, args):
        if event == '开始':
            return [[('FLAG', self.started, 1)]]
        role = ' '.join(args)
        if event in ('开', '关'):
            if role not in self.state:
                from plantime import PlanError
                raise PlanError(f'{self.name}: no group {role!r}: {sorted(self.state)}')
            if event == '开':
                return [[('FLAG', self.state[role], 1)]]
            return [[('FLAG', self.started, 1), ('FLAG', self.state[role], 0)]]
        return super().cond(event, args)

    def action(self, what, args):
        if what == '停':
            return [('SET_FLAG', self.held, 1)]
        if what == '继续':
            return [('SET_FLAG', self.held, 0)]
        return super().action(what, args)

    def swap(self, role, up):
        """Actions turning every unit of the group on (up) or off: take the other upgrade away, grant this one."""
        give, take = (self.on_up, self.off_up) if up else (self.off_up, self.on_up)
        names = self.ctx.part_names(role)
        return ([('NAMED_REMOVE_UPGRADE', take, n) for n in names] + [('NAMED_RECEIVE_UPGRADE', give, n) for n in names])

    def scripts(self):
        ctx = self.ctx
        tag, off_for = ctx.tag, self.period - self.on_for
        ctx.when(f'{self.key} start', self.spec.get('开始', '开局'), [('SET_FLAG', self.started, 1)])
        out = []
        for k, (role, phase) in enumerate(self.groups):
            state, timer = self.state[role], self.timer[role]
            label = f'CNV {tag} - {self.key} {k}'
            running = [('FLAG', self.started, 1), ('FLAG', self.held, 0)]
            out += [
                # at the start: off, and the first turn-on after the phase (a hair after 0 when there is none)
                Script(f'{label} begin', [('FLAG', self.started, 1)],
                       self.swap(role, False) + [('SET_MILLISECOND_TIMER', timer, max(phase, 0.1))]),
                Script(f'{label} on', running + [('TIMER_EXPIRED', timer), ('FLAG', state, 0)],
                       self.swap(role, True) + [('SET_FLAG', state, 1), ('SET_MILLISECOND_TIMER', timer, self.on_for)],
                       once=False),
                Script(f'{label} off', running + [('TIMER_EXPIRED', timer), ('FLAG', state, 1)],
                       self.swap(role, False) + [('SET_FLAG', state, 0), ('SET_MILLISECOND_TIMER', timer, off_for)],
                       once=False)]
        return out
