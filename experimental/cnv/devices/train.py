"""列车: a scripted train (units/train.py: the armoured train, retail's campaign train under our id with a Tesla gun)
as a plan device. Once a second the mission sends it to the next stop on its route it has not reached (a move
order of anyone else's -- the player's -- lasts a second at most: missions/train_bench.py, bench 2026-10-22); a
stop's area reached makes the next one the goal. It may wait at each stop (停靠: the enemy's train in S2 stops at
every station, so the player's can catch it), and be held (停下 / 继续).

  机关: {装甲列车: {类型: 列车, 角色: train, 起点: <site>, 路线: [<site>, ...], 出发: <condition>, 阵营: 我,
                    停靠: 0, 血量: 3000, 射程: 250}}

Published: cast <角色> (the train, named); events 出发, 到站 <site>, 到终点; actions 停下, 继续; a wave may 打 it.
"""
import re

from devices import Device
from parts import Script
from units import train as tr

TICK = 1.0


class Train(Device):
    WHAT = '一辆列车沿着一串车站开：任务脚本每秒送它去下一站，玩家只能瞄准和刹车，不能开到别处；可以每站停靠'
    PARAMS = {'角色': '它在开局部队里的角色名（英文，默认 train）', '起点': '地点：列车摆在这里',
              '路线': '一串地点：按顺序开过去，最后一个是终点', '出发': '条件：什么时候开（默认 开局）',
              '阵营': '我 / 敌（默认 我）', '停靠': '秒：每到一站停多久（默认 0，终点不停）',
              '血量': '默认 3000', '射程': '磁暴炮射程（默认 250）', '朝向': '弧度（默认 0）'}
    EVENTS = {'出发': '列车开动了', '到站 <地点>': '列车到了路线上的这一站（之后一直算数）', '到终点': '列车到了路线的最后一站'}
    ACTIONS = {'停下': '列车停在原地', '继续': '列车接着开'}
    TARGET = '这辆列车'

    def __init__(self, c, name, spec):
        super().__init__(c, name, spec)
        from plan import PlanError
        self.role = str(spec.get('角色', 'train'))
        self.route = list(spec.get('路线') or [])
        if not self.route or '起点' not in spec:
            raise PlanError(f'{name}: 列车 needs 起点 and 路线 (a list of sites)')
        key = re.sub(r'[^A-Za-z0-9]', '', self.role.title())
        tag = c.tag
        self.unit = tr.train(id=f'CNV_{tag}{key}Train', health=int(spec.get('血量', 3000)),
                             reach=int(spec.get('射程', 250)))
        self.units = [self.unit]
        self.names = {name: self.unit}
        self.side = c.side[spec.get('阵营', '我')]
        self.obj = f'UNIT - CNV {tag} {self.role}'
        base = f'CNV_{tag}_{key}'
        self.rolling, self.halted, self.docked = f'{base}_Rolling', f'{base}_Halted', f'{base}_Docked'
        self.stop, self.timer, self.dock = f'{base} Stop', f'{base} Tick', f'{base} Dock'
        self.attacks = 0

    def place(self):
        self.m.put(self.unit.id, self.spec['起点'], side=self.side, name=self.obj, role=self.role,
                   angle=self.spec.get('朝向', 0.0))

    def index(self, site):
        from plan import PlanError
        if site not in self.route:
            raise PlanError(f'{self.name}: {site!r} is not on its route {self.route}')
        return self.route.index(site)

    def cond(self, event, args):
        if event == '出发':
            return [[('FLAG', self.rolling, 1)]]
        if event == '到站':
            return [[('COUNTER', self.stop, 3, self.index(' '.join(args)) + 1)]]
        if event == '到终点':
            return [[('COUNTER', self.stop, 3, len(self.route))]]
        return super().cond(event, args)

    def action(self, what, args):
        if what == '停下':
            return [('SET_FLAG', self.halted, 1), ('NAMED_STOP', self.obj)]
        if what == '继续':
            return [('SET_FLAG', self.halted, 0)]
        return super().action(what, args)

    def attack(self, names):
        self.attacks += 1
        return [Script(f'CNV {self.c.tag} - {self.role} target {self.attacks}', [('TIMER_EXPIRED', self.timer)],
                       [('NAMED_ATTACK_NAMED', n, self.obj) for n in names], once=False)]

    def scripts(self):
        import plan
        tag, train = self.c.tag, self.obj
        waits = plan.times(self.spec.get('停靠', 0) or 0)       # by difficulty (25/20/15)
        wait = max(waits)
        self.c.when(f'{self.role} go', self.spec.get('出发', '开局'), [('SET_FLAG', self.rolling, 1)])
        out = [Script(f'CNV {tag} - {self.role} tick', [], [('SET_MILLISECOND_TIMER', self.timer, TICK)])]
        for k, site in enumerate(self.route):
            wp = self.c.mark(site)
            out.append(Script(f'CNV {tag} - {self.role} to {k + 1}',
                              [('FLAG', self.rolling, 1), ('FLAG', self.halted, 0), ('FLAG', self.docked, 0),
                               ('TIMER_EXPIRED', self.timer), ('COUNTER', self.stop, 2, k)],
                              [('MOVE_NAMED_UNIT_TO', train, wp)], once=False))
            docks = wait and k + 1 < len(self.route)
            for levels, w in (plan.by_level(waits) if docks else [(plan.ALL, 0)]):
                out.append(Script(f'CNV {tag} - {self.role} at {k + 1}' +
                                  ('' if levels == plan.ALL else f' {plan.TAGS[levels.index(True)]}'),
                                  [('FLAG', self.rolling, 1), ('COUNTER', self.stop, 2, k),
                                   ('NAMED_INSIDE_AREA', train, self.c.area(site))],
                                  [('SET_COUNTER', self.stop, k + 1)] +
                                  ([('SET_FLAG', self.docked, 1), ('NAMED_STOP', train),
                                    ('SET_MILLISECOND_TIMER', self.dock, w)] if docks else []),
                                  once=False, levels=levels))
        if wait:
            out.append(Script(f'CNV {tag} - {self.role} leaves', [('FLAG', self.docked, 1),
                                                                    ('TIMER_EXPIRED', self.dock)],
                              [('SET_FLAG', self.docked, 0)], once=False))
        return out

    def last(self):
        """The tick, after everything that waits on it (it sets the timer again)."""
        return [Script(f'CNV {self.c.tag} - {self.role} tick again', [('TIMER_EXPIRED', self.timer)],
                       [('SET_MILLISECOND_TIMER', self.timer, TICK)], once=False)]
