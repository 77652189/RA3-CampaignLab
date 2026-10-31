"""号角: A4's festival horn (docs/design/flow/a4.md, cards/a4-layer3.md) as a plan device. A horn sounds every 间隔
(a table: one time per horn, each by difficulty); on every horn each open way out of the ground sends a wave at the
convoy -- first the festival's three streets, later the last leg's three mouths. The player's ice engineer freezes a
way shut (an ice wall standing in its area); the two sets treat a shut way differently:

  streets (街): a shut street's wave is made at an open street instead, 绕路 seconds later (the back streets); the
      table gives, per shut street, the delay at each other street, so two shut streets that go to the same open one
      arrive at least MIN_APART apart, and a lone shut street goes to the open street it is quickest to.
      A street that opens only from horn k (从: k) neither sends nor takes a wave before.
  mouths (口): a shut mouth's wave is not made but kept (it queues behind the ice); the moment the ice is gone it
      is made, all the kept ones of every horn together.

  机关: {号角: {类型: 号角, 车队: <a 车队 device>, 间隔: [45, 50, 45, 50, 45], 每街一波: {帝国武士: 2, 坦克杀手: 2},
                冷却: 40, 街: {<name>: {点: <site the ice goes>, 出: <site the wave is made at>, 偏移: [dx, dy], 从: 1}},
                绕路: {<shut>: {<open>: 0:10, ...}, ...}, 口: {<name>: {点, 出, 偏移}},
                鬼王: {从: 3, 数量: 1/1/2, 运输车: 突击运输车, 海: sea east, 岸: beach}}}

Waves go for the convoy (the convoy device's attack). 鬼王 (last leg, from the horn 从 on): a 运输车 comes from
海 to 岸, the Ghost King lands where it arrives; it smashes the ice wall nearest to it when there is one (bench
2026-10-31, checks/icewall.py ghost: it does not do it on its own, an attack order at the wall does it), else it goes
for the convoy.

Units: 冰幕工兵 (the engineer). Marks spawn <street or mouth> (where its wave is made), ice <name> (where the ice
goes); areas hold the ice (GATE_AREA round the ice mark). Events: 号角 <n> (the n-th horn of the streets sounded),
口号角 <n> (of the mouths), 冻住 <name> (ice stands there now). Actions: 开 街 / 开 口 (the horns start, counting from
the first), 停 (they stop; what is made or kept goes on).
"""
import itertools

from devices import Device, ice_plazas
from parts import Script, square
from units import icewall as iw

GATE_AREA = ice_plazas.GATE_AREA                # half-side of the area an ice wall must stand in to hold a way
CLEAR_MARGIN = ice_plazas.CLEAR_MARGIN
WALL_SIDE = ice_plazas.WALL_SIDE
RELOAD = ice_plazas.RELOAD
MIN_APART = 10.0                                # two waves shut streets send to one open street arrive this far apart
MODES = {'街': 'V', '口': 'L'}                  # the two sets, and the letter in their names


def route(delay, order, avail, shut, origin):
    """(street the wave of `origin` is made at, seconds late), or None when no street is open: its own when it is open,
    else the open one it is quickest to (a tie: the earlier in `order`). avail: the streets that take part now."""
    if origin not in shut:
        return origin, 0.0
    free = [o for o in order if o in avail and o not in shut]
    if not free:
        return None
    best = min(free, key=lambda o: (delay[origin][o], order.index(o)))
    return best, delay[origin][best]


def check_delays(delay, order):
    """The 绕路 table is whole, and the waves of two shut streets bound for the same open one arrive MIN_APART apart."""
    for s in order:
        for o in order:
            if o != s:
                assert o in delay.get(s, {}), f'绕路 {s} -> {o} is missing'
    for o in order:
        others = [s for s in order if s != o]
        for i, a in enumerate(others):
            for b in others[i + 1:]:
                gap = abs(delay[a][o] - delay[b][o])
                assert gap >= MIN_APART, f'绕路: {a} and {b} both shut arrive at {o} only {gap:g} s apart (< {MIN_APART:g})'


class Horn(Device):
    WHAT = '号角按间隔表一声声响，每响一声开着的地道口各出一波扑车；冰墙把出口封住：街口的兵绕路晚到，最后一程口子的兵攒在墙后'
    PARAMS = {'车队': '哪个车队机关（兵扑它）', '间隔': '每声号角的间隔（秒，可按难度写），一个数一声；开头那个是开始到第一声',
              '每街一波': '每个开着的口一声出多少兵，{兵种: 数量}（可按难度）', '冷却': '冰幕工兵放一次冰后多少秒才能再放（默认 40）',
              '街': '会场的街：{名: {点: 冰放的地方, 出: 兵出生的地方, 偏移: [dx, dy], 从: 第几声起开}}',
              '绕路': '冻住的街的兵去开着的街晚多少秒：{冻住的街: {开着的街: 时间}}，每两条街去同一条街的差 ≥ 10 秒',
              '口': '最后一程的口子：{名: {点, 出, 偏移}}，冻住的口子这一波攒着，冰没了一起出',
              '鬼王': '{从: 第几声起, 数量: 每声几台, 运输车: 单位, 海: 运输车出现的地方, 岸: 靠岸的地方}'}
    EVENTS = {'号角 <n>': '街的第 n 声号角响了', '口号角 <n>': '口的第 n 声号角响了', '冻住 <名>': '这个口子现在有冰',
              '鬼王上岸': '第一个鬼王上岸了', '放出': '口子后攒着的兵放出来过（冰化了或被砸开）'}
    ACTIONS = {'开 <街|口>': '号角从头开始响（先显示倒计时）', '停': '号角停（倒计时收起）；已经出的、攒着的照旧'}

    def __init__(self, c, name, spec):
        super().__init__(c, name, spec)
        import plan
        from plan import PlanError
        self.plan = plan
        tag = c.tag
        self.wall = iw.wall(f'CNV_{tag}IceWall', length=WALL_SIDE, shape='square')
        self.core = iw.seed(f'CNV_{tag}IceSeed', self.wall.id)
        self.eng = iw.engineer(wall_id=self.core.id, stand=iw.clear_of(self.wall),
                               reload=f'{float(spec.get("冷却", RELOAD)):g}s')
        self.units = [self.eng, self.core, self.wall]
        self.names = {'冰幕工兵': self.eng}
        self.gaps = [plan.times(g) for g in spec['间隔']]
        if not self.gaps:
            raise PlanError(f'{name}: 间隔 needs at least one time')
        self.troops = {u: plan.counts(n) for u, n in (spec.get('每街一波') or {}).items()}
        if not self.troops:
            raise PlanError(f'{name}: 每街一波 lists the troops of a wave')
        self.ways = {'V': dict(spec.get('街') or {}), 'L': dict(spec.get('口') or {})}
        for k, v in self.ways.items():
            if any(len(str(w)) == 0 for w in v):
                raise PlanError(f'{name}: empty way name')
        self.delay = {s: {o: plan.seconds(t) for o, t in row.items()} for s, row in (spec.get('绕路') or {}).items()}
        if self.ways['V']:
            check_delays(self.delay, list(self.ways['V']))
        self.ghost = spec.get('鬼王')
        if self.ghost and not self.ways['L']:
            raise PlanError(f'{name}: 鬼王 comes with 口')
        self.horns = len(self.gaps)
        self.timer = f'CNV {tag} Horn'
        self.on = {m: f'CNV_{tag}_Horn_{m}_On' for m in 'VL'}
        self.start = {m: f'CNV_{tag}_Horn_{m}_Start' for m in 'VL'}
        self.count = {m: f'CNV_{tag}_Horn_{m}_N' for m in 'VL'}
        self.label = f'SCRIPT:CNV{tag}_HORN_TIMER'
        self.alert = f'SCRIPT:CNV{tag}_HORN'
        self.c.m.strings[self.label] = '下一声号角'
        self.c.m.strings[self.alert] = '号角响了！'
        self.kings = f'CNV_{tag}_Kings'              # Ghost Kings landed so far
        self.released = f'CNV_{tag}_Released'        # a kept wave of a mouth was made (its ice went)

    # ---- names
    def ids(self, mode):
        """{way name: id} -- V1, V2 ... / L1, L2 ... in the order the plan lists them."""
        return {w: f'{mode}{k}' for k, w in enumerate(self.ways[mode], 1)}

    def frozen(self, wid):
        return f'CNV_{self.c.tag}_Frozen_{wid}'

    def blow(self, mode, n):
        return f'CNV_{self.c.tag}_Blow_{mode}{n}'

    def troop(self, mode, n, wid, u, j):
        return f'UNIT - CNV {self.c.tag} H{mode}{n} {wid} {u}-{j}'

    # ---- the plan's words
    def cond(self, event, args):
        if event == '号角':
            return [[('COUNTER', self.count['V'], 3, int(args[0]))]]
        if event == '口号角':
            return [[('COUNTER', self.count['L'], 3, int(args[0]))]]
        if event == '冻住':
            wid = self.ids_by_name(' '.join(args))
            return [[('FLAG', self.frozen(wid), 1)]]
        if event == '鬼王上岸':
            return [[('COUNTER', self.kings, 3, 1)]]
        if event == '放出':
            return [[('FLAG', self.released, 1)]]
        return super().cond(event, args)

    def ids_by_name(self, name):
        for mode in 'VL':
            if name in self.ids(mode):
                return self.ids(mode)[name]
        from plan import PlanError
        raise PlanError(f'{self.name}.冻住 {name!r}: no street or mouth of that name: '
                        f'{[*self.ids("V"), *self.ids("L")]}')

    def action(self, what, args):
        if what == '开':
            from plan import PlanError
            if len(args) != 1 or args[0] not in MODES:
                raise PlanError(f'{self.name}.开 {" ".join(args)!r}: 街 or 口')
            mode = MODES[args[0]]
            if not self.ways[mode]:
                raise PlanError(f'{self.name}.开 {args[0]}: the device has no {args[0]}')
            return [('SET_COUNTER', self.count[mode], 0), ('SET_FLAG', self.on[mode], 1),
                    ('SET_FLAG', self.start[mode], 1)]
        if what == '停':
            return [('SET_FLAG', self.on['V'], 0), ('SET_FLAG', self.on['L'], 0), ('HIDE_COUNTDOWN_TIMER', self.timer)]
        return super().action(what, args)

    # ---- the map side: marks and areas
    def place(self):
        m, tag = self.m, self.c.tag
        p1 = m.player('p1')
        self.walled = {}
        for mode in 'VL':
            for w, wid in self.ids(mode).items():
                way = self.ways[mode][w]
                dx, dy = way.get('偏移', (0, 0))
                m.waypoint(f'spawn {wid}', f'CNV {tag} Spawn {wid}', way['出'], dx, dy)
                m.waypoint(f'ice {wid}', f'CNV {tag} IceAt {wid}', way['点'])
                area = f'CNV {tag} Way {wid}'
                m.areas[area] = square(*m.point(f'ice {wid}'), GATE_AREA)
                sx, sy = m.point(f'ice {wid}')
                px, py = m.point(f'spawn {wid}')
                far = iw.clear_of(self.wall) / max(1.0, ((sx - px) ** 2 + (sy - py) ** 2) ** 0.5)
                m.areas[f'CNV {tag} Block {wid}'] = square(sx, sy, WALL_SIDE / 2 + CLEAR_MARGIN)
                m.waypoints[f'CNV {tag} Clear {wid}'] = (sx + (sx - px) * far, sy + (sy - py) * far)
                self.walled[wid] = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, self.wall.id, area)
        self.cdev = self.c.devices[self.spec['车队']]
        self.convoy = self.cdev.cv
        if self.ghost:
            g = self.ghost
            m.waypoint('sea', f'CNV {tag} Sea', g.get('海', 'sea east'))
            m.waypoint('shore', f'CNV {tag} Shore', g.get('岸', 'beach'))
            m.areas[f'CNV {tag} Shore'] = square(*m.point('shore'), max(60.0, m.where(g.get('岸', 'beach')).r))

    # ---- scripts
    def opens(self, mode, n):
        """The way ids of the set that take part in horn n (a street opens from its 从)."""
        return [wid for w, wid in self.ids(mode).items() if int(self.ways[mode][w].get('从', 1)) <= n]

    def variants(self, many=None):
        """[(levels, level index)]: one entry when the waves (or `many`, one number per difficulty) are the same on all
        difficulties, else one per level."""
        plan = self.plan
        keys = [tuple(n[lv] for n in self.troops.values()) for lv in range(3)] if many is None else list(many)
        if keys[0] == keys[1] == keys[2]:
            return [(plan.ALL, 0)]
        return [(plan.ONE[lv], lv) for lv in range(3)]

    def lvname(self, levels):
        return '' if levels == self.plan.ALL else f' {self.plan.TAGS[levels.index(True)]}'

    def make_at(self, mode, n, origin, target, lv):
        """Actions that make the wave of horn n of way `origin` (named after it) at the spawn mark of `target`."""
        m = self.m
        acts = []
        for u, ns in self.troops.items():
            tmpl = self.c.unit(u, 's1')
            m.spawns.add(tmpl)
            acts += [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', self.troop(mode, n, origin, tmpl, j), tmpl, m.team('s1'),
                      m.mark(f'spawn {target}')) for j in range(1, ns[lv] + 1)]
        return acts

    def names_of_waves(self):
        out = []
        for mode in 'VL':
            for wid in self.ids(mode).values():
                for n in range(1, self.horns + 1):
                    if wid not in self.opens(mode, n):
                        continue                    # a street not open yet makes no wave
                    for u, ns in self.troops.items():
                        out += [self.troop(mode, n, wid, self.c.unit(u, 's1'), j) for j in range(1, max(ns) + 1)]
        return out

    def scripts(self):
        m = self.m
        out = []
        # what the ice stands on now, read off every frame (zero, then one if a wall stands there), before the rest
        for mode in 'VL':
            for wid in self.ids(mode).values():
                f = self.frozen(wid)
                out += [Script(f'CNV {self.c.tag} - Frozen {wid} zero', [], [('SET_FLAG', f, 0)], once=False),
                        Script(f'CNV {self.c.tag} - Frozen {wid} holds', [self.walled[wid]], [('SET_FLAG', f, 1)],
                               once=False)]
        out += self.horn_scripts()
        for n in range(1, self.horns + 1):
            out += self.street_scripts(n) + self.mouth_scripts(n)
        out += self.ghost_scripts() + self.ice_scripts()
        names = self.names_of_waves()
        if names:
            out += self.cdev.attack(names)
        m.countdowns.append(self.timer)
        return out

    def horn_scripts(self):
        """The countdown and the horns: `开` sets a Start flag, the script of its set sets the first time; each horn
        counts, sets the next time (the table's next, by difficulty), and flags its blow for the scripts after."""
        plan, tag = self.plan, self.c.tag
        out = []
        for mode in 'VL':
            if not self.ways[mode]:
                continue
            for levels, gap in plan.by_level(self.gaps[0]):
                out.append(Script(f'CNV {tag} - Horn {mode} start{self.lvname(levels)}', [('FLAG', self.start[mode], 1)],
                                  [('SET_FLAG', self.start[mode], 0), ('SET_MILLISECOND_TIMER', self.timer, gap),
                                   ('DISPLAY_COUNTDOWN_TIMER', self.timer, self.label)], once=False, levels=levels))
            for n in range(1, self.horns + 1):
                base = [('SET_FLAG', self.blow(mode, n), 1), ('INCREMENT_COUNTER', 1, self.count[mode]),
                        ('SHOW_MILITARY_CAPTION', self.alert, 3.0)]
                when = [('FLAG', self.on[mode], 1), ('COUNTER', self.count[mode], 2, n - 1), ('TIMER_EXPIRED', self.timer)]
                if n == self.horns:
                    out.append(Script(f'CNV {tag} - Horn {mode}{n}', when, base + [('HIDE_COUNTDOWN_TIMER', self.timer)]))
                    continue
                for levels, gap in plan.by_level(self.gaps[n]):
                    out.append(Script(f'CNV {tag} - Horn {mode}{n}{self.lvname(levels)}', when,
                                      base + [('SET_MILLISECOND_TIMER', self.timer, gap),
                                              ('DISPLAY_COUNTDOWN_TIMER', self.timer, self.label)], levels=levels))
        return out

    def to(self, n, origin, target):
        return f'CNV_{self.c.tag}_To_V{n}_{origin}_{target}'

    def wait(self, n, origin):
        return f'CNV {self.c.tag} Wait V{n} {origin}'

    def send(self, n, origin, target, secs, conds, label):
        return Script(f'CNV {self.c.tag} - Route V{n} {label}', conds,
                      [('SET_FLAG', self.to(n, origin, target), 1), ('SET_MILLISECOND_TIMER', self.wait(n, origin), secs)])

    def street_scripts(self, n):
        """Horn n of the streets: the wave of each street that takes part goes to a street by `route`, made after its
        delay (a timer of its own for each wave). The Blow flag is read the frame it is set, then put away."""
        ids = self.ids('V')
        if not ids:
            return []
        order = list(ids.values())
        delay = {ids[s]: {ids[o]: t for o, t in row.items()} for s, row in self.delay.items()}
        avail = self.opens('V', n)
        out = []
        blow = ('FLAG', self.blow('V', n), 1)
        for origin in avail:
            others = [wid for wid in avail if wid != origin]
            # origin open: its own street, no wait; origin shut: one script per state (shut or open) of the others
            out.append(self.send(n, origin, origin, 0.0, [blow, ('FLAG', self.frozen(origin), 0)], f'{origin} open'))
            for bits in itertools.product((0, 1), repeat=len(others)):
                shut = {w for w, b in zip(others, bits) if b} | {origin}
                res = route(delay, order, avail, shut, origin)
                if res is None:
                    continue
                conds = [blow, ('FLAG', self.frozen(origin), 1)] + [('FLAG', self.frozen(w), b)
                                                                     for w, b in zip(others, bits)]
                out.append(self.send(n, origin, res[0], res[1], conds, f'{origin} shut {"".join(map(str, bits))}'))
        out.append(Script(f'CNV {self.c.tag} - Blow V{n} done', [blow], [('SET_FLAG', self.blow('V', n), 0)]))
        # made when the wait is over, wherever it was sent
        for origin in avail:
            for target in avail:
                flag, timer = self.to(n, origin, target), self.wait(n, origin)
                for levels, lv in self.variants():
                    out.append(Script(f'CNV {self.c.tag} - Out V{n} {origin} at {target}{self.lvname(levels)}',
                                      [('FLAG', flag, 1), ('TIMER_EXPIRED', timer)],
                                      self.make_at('V', n, origin, target, lv) + [('SET_FLAG', flag, 0)],
                                      levels=levels))
        return out

    def mouth_scripts(self, n):
        """Horn n of the mouths: an open mouth sends its wave now; a shut one keeps it (a flag), and it is made the
        moment the ice is gone -- every kept wave of every horn, each by a script of its own."""
        ids = self.ids('L')
        if not ids:
            return []
        tag = self.c.tag
        out = []
        blow = ('FLAG', self.blow('L', n), 1)
        for wid in ids.values():
            kept = f'CNV_{tag}_Kept_L{n}_{wid}'
            for levels, lv in self.variants():
                lvn = self.lvname(levels)
                out.append(Script(f'CNV {tag} - Out L{n} {wid}{lvn}', [blow, ('FLAG', self.frozen(wid), 0)],
                                  self.make_at('L', n, wid, wid, lv), levels=levels))
                out.append(Script(f'CNV {tag} - Release L{n} {wid}{lvn}',
                                  [('FLAG', kept, 1), ('FLAG', self.frozen(wid), 0)],
                                  self.make_at('L', n, wid, wid, lv) + [('SET_FLAG', kept, 0), ('SET_FLAG', self.released, 1)],
                                  levels=levels))
            out.append(Script(f'CNV {tag} - Keep L{n} {wid}', [blow, ('FLAG', self.frozen(wid), 1)],
                              [('SET_FLAG', kept, 1)]))
        out += self.boats(n)
        out.append(Script(f'CNV {tag} - Blow L{n} done', [blow], [('SET_FLAG', self.blow('L', n), 0)]))
        return out

    # ---- the Ghost King
    def boats(self, n):
        """Transports made at the sea on the blow of horn n (many by difficulty), sent to the shore."""
        g, m, tag = self.ghost, self.m, self.c.tag
        if not g or n < int(g.get('从', 3)):
            return []
        many = self.plan.counts(g.get('数量', 1))
        boat = self.c.unit(g.get('运输车', '突击运输车'), 's1')
        m.spawns.add(boat)
        out = []
        for levels, lv in self.variants(many):
            names = [f'UNIT - CNV {tag} Boat {n}-{j}' for j in range(1, many[lv] + 1)]
            out.append(Script(f'CNV {tag} - Boats {n}{self.lvname(levels)}', [('FLAG', self.blow('L', n), 1)],
                              [a for b in names for a in (
                                  ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', b, boat, m.team('s1'), m.mark('sea')),
                                  ('MOVE_NAMED_UNIT_TO', b, m.mark('shore')))], levels=levels))
        return out

    def ghost_scripts(self):
        """Where a transport gets to the shore the Ghost King lands. It smashes the nearest ice wall (a flag says the
        pointer points at one; it is picked again after that wall is gone), else it goes for the convoy."""
        g, m, tag, cv = self.ghost, self.m, self.c.tag, self.convoy
        if not g:
            return []
        many = self.plan.counts(g.get('数量', 1))
        king = self.c.unit('鬼王', 's1')
        m.spawns.add(king)
        p1, wall = m.player('p1'), self.wall.id
        ref = f'UNITRef - CNV {tag} Nearest Wall'
        walls, picked, kings = f'CNV_{tag}_Walls', f'CNV_{tag}_Picked', self.kings
        out = [Script(f'CNV {tag} - Walls counted', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', wall, p1, walls)],
                      once=False),
               Script(f'CNV {tag} - Ghost pick', [('COUNTER', kings, 3, 1), ('FLAG', picked, 0), ('COUNTER', walls, 3, 1)],
                      [('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', wall, p1, m.team('s1'), ref),
                       ('SET_FLAG', picked, 1)], once=False),
               Script(f'CNV {tag} - Ghost dropped', [('FLAG', picked, 1), ('NAMED_DESTROYED', ref)],
                      [('SET_FLAG', picked, 0)], once=False)]
        for n in range(int(g.get('从', 3)), self.horns + 1):
            for j in range(1, max(many) + 1):
                b, k = f'UNIT - CNV {tag} Boat {n}-{j}', f'UNIT - CNV {tag} King {n}-{j}'
                landed = f'CNV_{tag}_Landed_{n}_{j}'
                out.append(Script(f'CNV {tag} - King {n}-{j} lands',
                                  [('NAMED_INSIDE_AREA', b, f'CNV {tag} Shore'), ('FLAG', landed, 0)],
                                  [('SET_FLAG', landed, 1), ('INCREMENT_COUNTER', 1, kings),
                                   ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', k, king, m.team('s1'), m.mark('shore'))]))
                out.append(Script(f'CNV {tag} - King {n}-{j} smashes',
                                  [('FLAG', landed, 1), ('FLAG', picked, 1), ('NAMED_NOT_DESTROYED', ref),
                                   ('NAMED_NOT_DESTROYED', k)], [('NAMED_ATTACK_NAMED', k, ref)], once=False))
                out += [Script(f'CNV {tag} - King {n}-{j} hunts at {t + 1}',
                               [('FLAG', landed, 1), ('COUNTER', walls, 2, 0), ('NAMED_NOT_DESTROYED', k),
                                ('TIMER_EXPIRED', cv.timer)] + cv.chase(t), [('NAMED_ATTACK_NAMED', k, target)],
                               once=False) for t, target in enumerate(cv.trucks)]
        return out

    # ---- the ice: its time left on screen, an engineer shut in the block taken out
    def ice_scripts(self):
        m, tag = self.m, self.c.tag
        life = self.wall.params['lifetime']
        out = []
        for mode in 'VL':
            for w, wid in self.ids(mode).items():
                timer, up = f'CNV {tag} Ice {wid}', f'CNV_{tag}_Ice_{wid}'
                label = f'SCRIPT:CNV{tag}_ICE{wid}'
                m.strings[label] = f'{w}的冰墙'
                f = self.frozen(wid)
                out += [Script(f'CNV {tag} - Ice {wid} up', [('FLAG', f, 1), ('FLAG', up, 0)],
                               [('SET_FLAG', up, 1), ('SET_MILLISECOND_TIMER', timer, float(life)),
                                ('DISPLAY_COUNTDOWN_TIMER', timer, label)], once=False),
                        Script(f'CNV {tag} - Ice {wid} gone', [('FLAG', f, 0), ('FLAG', up, 1)],
                               [('SET_FLAG', up, 0), ('HIDE_COUNTDOWN_TIMER', timer)], once=False)]
                m.countdowns.append(timer)
                out += [Script(f'CNV {tag} - Clear {wid} of {j + 1}',
                               [('FLAG', f, 1), ('NAMED_INSIDE_AREA', e, f'CNV {tag} Block {wid}')],
                               [('UNIT_TELEPORT_TO_WAYPOINT', e, f'CNV {tag} Clear {wid}')], once=False)
                        for j, e in enumerate(self.engineers())]
        return out

    engineers = ice_plazas.IcePlazas.engineers
