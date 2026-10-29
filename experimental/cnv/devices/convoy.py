"""车队: the escorted convoy (missions/festival_parts.Convoy: three unarmed trucks the player cannot drive, sent on
to the exit every tick) as a plan device. The plan says when it sets off (出发, a condition) and may stop it and
send it on again (停下 / 继续: retail's escorts wait for the player and time out, map-language.md 7).

  机关: {车队: {类型: 车队, 出发: <condition>, 每隔: 3, 血量: 700/500/350}}

Cast truck 1-3 (the 车 side's: the player's by default, or a side of 阵营 其他 allied to them), mark exit; facts: convoy leaves (when 出发 is a phase that starts at a time), tick.
Other devices may hold the convoy too (hold(flag): it rolls only while every such flag is 0 -- the plazas' ambush).
"""
import re

from devices import Device
from missions import festival_parts as fp
from parts import Script


class Convoy(Device):
    WHAT = '三辆车按时间表开向终点，玩家护送但指挥不了'
    PARAMS = {'出发': '条件：车队什么时候出发', '每隔': '秒：每隔多久重新给车下一次命令（默认 3）',
              '车': '谁的车：我、敌，或 阵营 其他 里的一方（写成盟友的，玩家点不了；默认 我）',
              '血量': '每辆车的血量，可按难度写（原版伊贺 7000/5000/3000；默认 500）',
              '分批': '每辆车在出发后多少秒才开，例如 [0, 50, 110]（默认一起开；原版敖德萨的船一艘接一艘）',
              '分批从': '出发（默认）或 继续：写 继续 时出发一起开，停下以后 继续 那一刻起才按 分批 一辆接一辆开'
                       '（A4 返工：一起开到 2 号广场，最后一程分批走）'}
    EVENTS = {'出发': '车队出发了', '到达 <地点>': '第一辆车开进这个地点', '到终点 <n>': '已有 n 辆车到达终点',
              '损失 <n>': '已有 n 辆车被毁', '继续了': '动作 继续 做过了（停下以后又开了）'}
    ACTIONS = {'停下': '车队停在原地', '继续': '车队接着开'}
    TARGET = '最前面那辆还在路上的车'

    def __init__(self, c, name, spec):
        super().__init__(c, name, spec)
        self.tick = float(spec.get('每隔', 3.0))
        from plan import PlanError
        who = spec.get('车', '我')
        if who not in c.side:
            raise PlanError(f'{name}: 车 {who!r} is none of {sorted(c.side)}')
        self.cv = fp.Convoy(self.m, c.tag, c.side[who], 0.0, self.tick)
        self.batches = [float(x) for x in spec.get('分批') or []]
        if self.batches and len(self.batches) != len(self.cv.trucks):
            raise PlanError(f'{name}: 分批 gives one time per truck ({len(self.cv.trucks)})')
        self.go = [f'CNV_{c.tag}_Go_{j}' for j in range(1, len(self.cv.trucks) + 1)]
        self.batch_from = spec.get('分批从', '出发')
        if self.batch_from not in ('出发', '继续'):
            raise PlanError(f'{name}: 分批从 {self.batch_from!r} is 出发 or 继续')
        if self.batch_from == '继续' and not self.batches:
            raise PlanError(f'{name}: 分批从 继续 without 分批')
        self.resumed = f'CNV_{c.tag}_Resumed'
        self.halted = f'CNV_{c.tag}_Halted'
        self.holds = [self.halted]                  # flags that keep it parked (停下; hold() adds more)
        self.attacks = 0
        code = self.cv.code
        self.m.strings.setdefault(f'SCRIPT:{code}_GO', '车队出发了。')
        self.m.strings.setdefault(f'SCRIPT:{code}_SAFE', '一辆车到达终点。')

    def cond(self, event, args):
        cv = self.cv
        if event == '出发':
            return [[('FLAG', cv.rolling, 1)]]
        if event == '到达':
            area = self.c.area(' '.join(args))
            return [[('NAMED_INSIDE_AREA', t, area)] for t in cv.trucks]
        if event == '到终点':
            return [[('COUNTER', cv.arrived, 3, int(args[0]))]]
        if event == '损失':
            return [[('COUNTER', cv.losses, 3, int(args[0]))]]
        if event == '继续了':
            return [[('FLAG', self.resumed, 1)]]
        return super().cond(event, args)

    def action(self, what, args):
        if what == '停下':
            # 分批从 继续: stopped, the trucks after the first wait for their time after the 继续
            late = [('SET_FLAG', g, 0) for g, after in zip(self.go, self.batches) if after] \
                if self.batch_from == '继续' else []
            return [('SET_FLAG', self.halted, 1)] + late + [('NAMED_STOP', t) for t in self.cv.trucks]
        if what == '继续':
            return [('SET_FLAG', self.halted, 0), ('SET_FLAG', self.resumed, 1)]
        return super().action(what, args)

    def hold(self, flag):
        """Keep the convoy parked while `flag` is 1 (as 停下 does); returns the actions that stop the trucks now."""
        self.holds.append(flag)
        return [('NAMED_STOP', t) for t in self.cv.trucks]

    def attack(self, names):
        """Every tick, at the leading truck still on the road (bench 2026-10-23: sent toward the exit they ran ahead of
        the convoy at its own speed and never fired on it)."""
        cv = self.cv
        self.attacks += 1                           # one set per wave (names cut short collided, review 2026-10-24)
        return [Script(f'CNV {self.c.tag} - Convoy target {self.attacks} at {j + 1}',
                       [('TIMER_EXPIRED', cv.timer)] + cv.chase(j), [('NAMED_ATTACK_NAMED', n, t) for n in names],
                       once=False) for j, t in enumerate(cv.trucks)]

    def scripts(self):
        import plan
        self.c.when('Convoy go', self.spec['出发'], self.cv.go()[0].do)
        for j, (after, g) in enumerate(zip(self.batches, self.go)):    # 分批: truck j once its time is up
            if self.batch_from == '继续':                 # all at the departure; in turn after the 继续
                self.c.when(f'Convoy go {j + 1}', f'{self.name}.出发', [('SET_FLAG', g, 1)])
                if after:
                    self.c.when(f'Convoy resume {j + 1}', f'{self.name}.继续了 + {after:g}', [('SET_FLAG', g, 1)])
                continue
            self.c.when(f'Convoy go {j + 1}', f'{self.name}.出发' + (f' + {after:g}' if after else ''),
                        [('SET_FLAG', g, 1)])
        # the tick runs before the convoy sets off too: what attacks it (a wave the player called early, troops out
        # of a broken sculpture) waits on the tick, and a timer never set never runs out
        out = [Script(f'CNV {self.c.tag} - Tick before', [], [('SET_MILLISECOND_TIMER', self.cv.timer, 0.0)])]
        if self.spec.get('血量') is not None:      # retail Iga: NAMED_SET_MAX_HEALTH by difficulty, full health too
            there = [('FLAG', self.cv.rolling, 1)] if self.cv.enter else []     # trucks made at the departure
            for levels, v in plan.by_level(plan.counts(self.spec['血量'])):
                out.append(Script(f'CNV {self.c.tag} - Truck health' + ('' if levels == plan.ALL else
                                                                       f' {plan.TAGS[levels.index(True)]}'),
                                  there, [('NAMED_SET_MAX_HEALTH', t, v, 1) for t in self.cv.trucks], levels=levels))
        return out

    def last(self):
        """The roll after everything else that waits on the tick timer (it sets the timer again). In batches (分批)
        each truck is sent on by a script of its own, once its time after the departure ran out."""
        roll = self.cv.roll()[0]
        roll.when = roll.when + [('FLAG', h, 0) for h in self.holds]
        if self.batches:
            sends = [Script(f'CNV {self.c.tag} - Roll {j + 1}', roll.when + [('FLAG', g, 1)],
                            [('MOVE_NAMED_UNIT_TO', t, self.cv.exit)], once=False)
                     for j, (t, g) in enumerate(zip(self.cv.trucks, self.go))]
            roll.do = [a for a in roll.do if a[0] != 'MOVE_NAMED_UNIT_TO']
            roll = sends + [roll]
        else:
            roll = [roll]
        # stopped, the tick still runs (scripts waiting on it would otherwise fire every frame): no moves
        wait = [Script(f'CNV {self.c.tag} - Roll held' + (f' {k}' if k else ''),
                       [('FLAG', self.cv.rolling, 1), ('TIMER_EXPIRED', self.cv.timer), ('FLAG', h, 1)],
                       [('SET_MILLISECOND_TIMER', self.cv.timer, self.tick)], once=False)
                for k, h in enumerate(self.holds)]
        parked = Script(f'CNV {self.c.tag} - Roll parked', [('FLAG', self.cv.rolling, 0), ('TIMER_EXPIRED', self.cv.timer)],
                        [('SET_MILLISECOND_TIMER', self.cv.timer, self.tick)], once=False)
        return roll + wait + [parked] + self.cv.tail()

    def facts(self):
        out = {'tick': self.tick}
        mm = re.match(r'^段\s+(.+?)(\s+开始)?$', str(self.spec.get('出发', '')).strip())
        if mm and f'段 {mm.group(1)}' in self.m.facts:
            out['convoy leaves'] = self.m.facts[f'段 {mm.group(1)}']
        return out
