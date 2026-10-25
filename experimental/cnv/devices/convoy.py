"""车队: the escorted convoy (missions/festival_parts.Convoy: three unarmed trucks the player cannot drive, sent on
to the exit every tick) as a plan device. The plan says when it sets off (出发, a condition) and may stop it and
send it on again (停下 / 继续: retail's escorts wait for the player and time out, map-language.md 7).

  机关: {车队: {类型: 车队, 出发: <condition>, 每隔: 3}}

Cast truck 1-3 (the player's), mark exit; facts: convoy leaves (when 出发 is a phase that starts at a time), tick.
"""
import re

from devices import Device
from missions import festival_parts as fp
from parts import Script


class Convoy(Device):
    WHAT = '三辆车按时间表开向终点，玩家护送但指挥不了'
    PARAMS = {'出发': '条件：车队什么时候出发', '每隔': '秒：每隔多久重新给车下一次命令（默认 3）',
              '车': '谁的车（默认 我）'}
    EVENTS = {'出发': '车队出发了', '到达 <地点>': '第一辆车开进这个地点', '到终点 <n>': '已有 n 辆车到达终点',
              '损失 <n>': '已有 n 辆车被毁'}
    ACTIONS = {'停下': '车队停在原地', '继续': '车队接着开'}
    TARGET = '最前面那辆还在路上的车'

    def __init__(self, c, name, spec):
        super().__init__(c, name, spec)
        self.tick = float(spec.get('每隔', 3.0))
        side = 'p1' if spec.get('车', '我') == '我' else 's1'
        self.cv = fp.Convoy(self.m, c.tag, side, 0.0, self.tick)
        self.halted = f'CNV_{c.tag}_Halted'
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
        return super().cond(event, args)

    def action(self, what, args):
        if what == '停下':
            return [('SET_FLAG', self.halted, 1)] + [('NAMED_STOP', t) for t in self.cv.trucks]
        if what == '继续':
            return [('SET_FLAG', self.halted, 0)]
        return super().action(what, args)

    def attack(self, names):
        """Every tick, at the leading truck still on the road (bench 2026-10-23: sent toward the exit they ran ahead of
        the convoy at its own speed and never fired on it)."""
        cv = self.cv
        self.attacks += 1                           # one set per wave (names cut short collided, review 2026-10-24)
        return [Script(f'CNV {self.c.tag} - Convoy target {self.attacks} at {j + 1}',
                       [('TIMER_EXPIRED', cv.timer)] + cv.chase(j), [('NAMED_ATTACK_NAMED', n, t) for n in names],
                       once=False) for j, t in enumerate(cv.trucks)]

    def scripts(self):
        self.c.when('Convoy go', self.spec['出发'], self.cv.go()[0].do)
        # the tick runs before the convoy sets off too: what attacks it (a wave the player called early, troops out
        # of a broken sculpture) waits on the tick, and a timer never set never runs out
        return [Script(f'CNV {self.c.tag} - Tick before', [], [('SET_MILLISECOND_TIMER', self.cv.timer, 0.0)])]

    def last(self):
        """The roll after everything else that waits on the tick timer (it sets the timer again)."""
        roll = self.cv.roll()[0]
        roll.when = roll.when + [('FLAG', self.halted, 0)]
        # stopped, the tick still runs (scripts waiting on it would otherwise fire every frame): no moves
        wait = Script(f'CNV {self.c.tag} - Roll held', [('FLAG', self.cv.rolling, 1), ('TIMER_EXPIRED', self.cv.timer),
                                                        ('FLAG', self.halted, 1)],
                      [('SET_MILLISECOND_TIMER', self.cv.timer, self.tick)], once=False)
        parked = Script(f'CNV {self.c.tag} - Roll parked', [('FLAG', self.cv.rolling, 0), ('TIMER_EXPIRED', self.cv.timer)],
                        [('SET_MILLISECOND_TIMER', self.cv.timer, self.tick)], once=False)
        return [roll, wait, parked] + self.cv.tail()

    def facts(self):
        out = {'tick': self.tick}
        mm = re.match(r'^段\s+(.+?)(\s+开始)?$', str(self.spec.get('出发', '')).strip())
        if mm and f'段 {mm.group(1)}' in self.m.facts:
            out['convoy leaves'] = self.m.facts[f'段 {mm.group(1)}']
        return out
