"""自由号: the enemy's Liberty carrier (units/liberty.py: drones, a deck factory, the deck jump) as a plan device --
A7's boss. While its power station is the enemy's (standing, not captured), the device jumps it from home to the
landing point the player defends least, a warning first (a countdown, a caption), and back home after a while; the
station hurt, it jumps back to defend it once. Grounded, the plan can send it flying round a route until the
level's deadline (飞走): the countdown, not the route, decides the deadline (its speed would).

  机关: {自由号: {类型: 自由号, 电站: station, 开始: <condition>, 落点: [site, ...], 空虚: 3, 每隔: 1:30, 停留: 30,
                  预警: 15, 家: carrier home, 航线: [site, ...], 血量: 70/100/100,
                  加快: [{当: 摧毁 a、b、c 1 个, 每隔: 1:00}, ...]}}

落点: in order, the first with fewer than 空虚 of the player's armed units in it; none: the last. Cast carrier (the
enemy's); marks: carrier home, the landing points, the route's; facts: first jump (when 开始 is a time), jump every.
"""
from devices import Device
from parts import Script, kindof
from units import liberty as lib

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'      # what the deck factory builds
FAR = 99999.0


class Carrier(Device):
    WHAT = '敌方的自由号：电站在，就跳到玩家防守最空的地方放无人机、卸兵，过一会儿跳回去；电站受伤就跳回去救；断电后可以让它绕航线飞'
    PARAMS = {'电站': '角色：给它供电的建筑（被毁或被玩家占领就断电）', '开始': '条件：什么时候开始跳',
              '落点': '一串地点：按顺序选玩家武装单位少于"空虚"个的那一个', '空虚': '少于几个算空虚（默认 3）',
              '每隔': '时间：跳回家后多久再跳', '停留': '秒：在落点停多久', '预警': '秒：跳之前提前多久报警',
              '家': '地点', '航线': '一串地点：飞走时绕着飞', '血量': '百分比（简单/普通/困难）',
              '加快': '一串 {当: 条件, 每隔: 时间}：条件成立过以后跳得更勤，后面的一档优先（原版宫古岛：龙剩的关键建筑越少，充能越快）'}
    EVENTS = {'跃迁': '第一次跳过来了', '断电': '电站被毁或被玩家占领', '回防': '为了救电站跳回去了',
              '击落': '自由号被击落', '预警 <n>': '第 n 次跳之前报警了（报警那一刻起一直算数；地面进攻配合跃迁用）'}
    ACTIONS = {'回防': '马上跳到电站边上（电站还是敌人的、没在飞走时；不然不跳）', '飞走': '不再跳，绕航线飞'}

    def __init__(self, c, name, spec):
        super().__init__(c, name, spec)
        self.unit = lib.liberty('CNV_Liberty', reload='0s', factory=GUARDIAN)  # the scripts pace the jumps
        self.units = [self.unit]
        self.names = {'自由号': self.unit}
        self.jump = self.unit.abilities['jump']
        t = c.tag
        self.obj = f'UNIT - CNV {t} Liberty'
        self.timer, self.state, self.target = f'CNV {t} Jump', f'CNV_{t}_Jump_State', f'CNV_{t}_Jump_To'
        self.choosing, self.on, self.flying = f'CNV_{t}_Jump_Choose', f'CNV_{t}_Jump_On', f'CNV_{t}_Flying'
        self.jumped, self.defended, self.asked = f'CNV_{t}_Jumped', f'CNV_{t}_Defended', f'CNV_{t}_Defend_Asked'
        self.warned = f'CNV_{t}_Jump_Warned'      # how many warnings so far (预警 <n>)
        self.faster = list(spec.get('加快') or [])
        for s in self.faster:
            if not isinstance(s, dict) or set(s) != {'当', '每隔'}:
                from plan import PlanError
                raise PlanError(f'{name}: 加快 {s!r} -- each {{当: <condition>, 每隔: <time>}}')

    def place(self):
        m, c = self.m, self.c
        m.put(self.unit.id, self.spec['家'], side='s1', name=self.obj, role='carrier', angle=3.1416)
        self.home = c.mark(self.spec['家'])
        self.lands = [c.mark(s) for s in self.spec['落点']]
        self.route = [c.mark(s) for s in self.spec.get('航线') or []]
        self.station = c.part_names(self.spec['电站'])[0]
        self.near_station = c.mark(m.cast[self.spec['电站']].site)

    def powered(self):
        return ('NAMED_OWNED_BY_PLAYER', self.m.player('s1'), self.station)

    def cond(self, event, args):
        p1 = self.m.player('p1')
        if event == '跃迁':
            return [[('FLAG', self.jumped, 1)]]
        if event == '断电':
            return [[('NAMED_DESTROYED', self.station)], [('NAMED_OWNED_BY_PLAYER', p1, self.station)]]
        if event == '回防':
            return [[('FLAG', self.defended, 1)]]
        if event == '击落':
            return [[('NAMED_DESTROYED', self.obj)]]
        if event == '预警':
            n = int(args[0]) if args else 1
            return [[('COUNTER', self.warned, 3, n)]]
        return super().cond(event, args)

    def action(self, what, args):
        if what == '回防':                       # a request: done while there is a station to defend (scripts)
            return [('SET_FLAG', self.asked, 1)]
        if what == '飞走':
            if not self.route:
                from plan import PlanError
                raise PlanError(f'{self.name}.飞走: no 航线')
            return [('SET_FLAG', self.flying, 1), ('MOVE_NAMED_UNIT_TO', self.obj, self.route[0])]
        return super().action(what, args)

    def scripts(self):
        import plan
        m, c, t = self.m, self.c, self.c.tag
        s1, p1 = m.player('s1'), m.player('p1')
        stay = float(self.spec.get('停留', 30))
        warn = float(self.spec.get('预警', 15))
        few = int(self.spec.get('空虚', 3))
        out = []
        for levels, hp in plan.by_level(plan.counts(self.spec.get('血量', 100))):
            if hp < 100:
                out.append(Script(f'CNV {t} - Carrier health' + ('' if levels == plan.ALL else
                                                                f' {plan.TAGS[levels.index(True)]}'),
                                  [], [('UNIT_SET_HEALTH', self.obj, float(hp))], levels=levels))
        c.when('Carrier on', self.spec['开始'], [('SET_FLAG', self.on, 1), ('SET_COUNTER', self.state, 0),
                                                 ('SET_MILLISECOND_TIMER', self.timer, 0.0)])
        warn_key = c.text('SCRIPT', '自由号正在充能，准备跃迁！')
        count_key = c.text('SCRIPT', '自由号跃迁')
        ready = [('FLAG', self.on, 1), ('FLAG', self.flying, 0), ('TIMER_EXPIRED', self.timer), self.powered()]
        # 0: at home, waiting -> warn, pick where to land
        out.append(Script(f'CNV {t} - Carrier warn', ready + [('COUNTER', self.state, 2, 0)],
                          [('SET_COUNTER', self.state, 1), ('SET_FLAG', self.choosing, 1),
                           ('INCREMENT_COUNTER', 1, self.warned),
                           ('SET_MILLISECOND_TIMER', self.timer, warn), ('SHOW_MILITARY_CAPTION', warn_key, 5.0),
                           ('DISPLAY_COUNTDOWN_TIMER', self.timer, count_key), lib.charging(self.obj, warn)],
                          once=False))
        armed = kindof('CAN_ATTACK')
        for k, site in enumerate(self.spec['落点']):
            out.append(Script(f'CNV {t} - Carrier picks {k + 1}',
                              [('FLAG', self.choosing, 1),
                               ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 0, few, armed, c.area(site))],
                              [('SET_COUNTER', self.target, k + 1), ('SET_FLAG', self.choosing, 0)], once=False))
        out.append(Script(f'CNV {t} - Carrier picks the last', [('FLAG', self.choosing, 1)],
                          [('SET_COUNTER', self.target, len(self.lands)), ('SET_FLAG', self.choosing, 0)], once=False))
        # 1: warned -> jump there; 2: out -> jump home, wait for the next
        for k, wp in enumerate(self.lands):
            out.append(Script(f'CNV {t} - Carrier jumps to {k + 1}', ready + [('COUNTER', self.state, 2, 1),
                                                                            ('COUNTER', self.target, 2, k + 1)],
                              [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', self.obj, self.jump, wp),
                               ('SET_COUNTER', self.state, 2), ('SET_MILLISECOND_TIMER', self.timer, stay),
                               ('HIDE_COUNTDOWN_TIMER', self.timer), ('SET_FLAG', self.jumped, 1)], once=False))
        # 加快: the later a step that holds, the sooner it jumps again (retail Miyako: the fewer of Tatsu's key
        # buildings left, the faster the recharge, 90 -> 45 s); each step latched the first time it holds
        steps = [plan.times(self.spec.get('每隔', 90))] + [plan.times(s['每隔']) for s in self.faster]
        flags = [None] + [f'CNV_{t}_Faster_{k}' for k in range(1, len(steps))]
        for k, s in enumerate(self.faster, 1):
            c.when(f'Carrier faster {k}', s['当'], [('SET_FLAG', flags[k], 1)])
        for k, gaps in enumerate(steps):
            step = ([('FLAG', flags[k], 1)] if k else []) + [('FLAG', f, 0) for f in flags[k + 1:]]
            for levels, gap in plan.by_level(gaps):
                out.append(Script(f'CNV {t} - Carrier home' + (f' {k}' if k else '') +
                                  ('' if levels == plan.ALL else f' {plan.TAGS[levels.index(True)]}'),
                                  ready + [('COUNTER', self.state, 2, 2)] + step,
                                  [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', self.obj, self.jump, self.home),
                                   ('SET_COUNTER', self.state, 0), ('SET_MILLISECOND_TIMER', self.timer, gap)],
                                  once=False, levels=levels))
        # defending: only for a station still the enemy's, and not once flying off (review 2026-10-24: a station the
        # player took, hurt by the island's guard, called it back there); a warning under way is called off
        out.append(Script(f'CNV {t} - Carrier defends', [('FLAG', self.asked, 1), ('FLAG', self.flying, 0),
                                                         self.powered()],
                          [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', self.obj, self.jump, self.near_station),
                           ('SET_FLAG', self.asked, 0), ('SET_FLAG', self.defended, 1), ('SET_FLAG', self.choosing, 0),
                           ('SET_COUNTER', self.state, 2), ('SET_MILLISECOND_TIMER', self.timer, stay),
                           ('HIDE_COUNTDOWN_TIMER', self.timer)], once=False))
        for k, alt in enumerate(self.cond('断电', [])):         # a warning under way is called off
            out.append(Script(f'CNV {t} - Carrier grounded {k + 1}', [('FLAG', self.on, 1)] + alt,
                              [('HIDE_COUNTDOWN_TIMER', self.timer)]))
        m.countdowns.append(self.timer)
        # flying off: round the route, point after point
        for k, wp in enumerate(self.route):
            nxt = self.route[(k + 1) % len(self.route)]
            out.append(Script(f'CNV {t} - Carrier flies on {k + 1}',
                              [('FLAG', self.flying, 1), ('NAMED_INSIDE_AREA', self.obj, c.area(self.spec['航线'][k]))],
                              [('MOVE_NAMED_UNIT_TO', self.obj, nxt)], once=False))
        return out

    def facts(self):
        """jump every, warning, stay (seconds, normal difficulty); jump delay: from what 开始 waits on to the jumps'
        start (its `+ t`); first jump: from the mission's start, when a time decides it."""
        import re
        import plancheck
        import plan
        out = {'jump every': plan.times(self.spec.get('每隔', 90))[1], 'warning': float(self.spec.get('预警', 15)),
               'stay': float(self.spec.get('停留', 30))}
        for k, s in enumerate(self.faster, 1):      # 加快's steps, normal difficulty
            out[f'jump every {k}'] = plan.times(s['每隔'])[1]
        mm = re.match(r'^.*?\+\s*([^+]+)$', str(self.spec['开始']).strip())
        out['jump delay'] = plan.times(mm.group(1))[1] if mm else 0.0
        first = plancheck.times_of(self.spec['开始'], plancheck.phase_starts(self.c.d))
        if first is not None:
            out['first jump'] = first + out['warning']
        return out
