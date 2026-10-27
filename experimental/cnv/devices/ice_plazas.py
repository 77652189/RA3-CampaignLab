"""冰雕广场: A4's plazas (maps/festival.py: raised ground, one ramp each) with troops hidden in ice sculptures, and
the ice engineer who can shut a plaza's gate (units/icewall.py), as a plan device -- the A4 mechanics that were
missions/a4.py.

  机关: {冰雕广场: {类型: 冰雕广场, 车队: <a 车队 device>, 每座兵: [坦克杀手, 帝国武士, 坦克杀手], 每座几个: 1/2/3,
                   遇伏: 停下, 广场 2: {无敌: 是, 补兵: 0:20/0:15/0:10}}}

Each plaza holds two sculptures; a sculpture's troops are the first 每座几个 of 每座兵 (by difficulty), created
where it stood when it breaks. A truck on a plaza's approach breaks that plaza's sculptures (one the player breaks
earlier lets its own out then). Out, they go for the leading truck still on the road -- unless ice stands in their
gate: then they guard their plaza (a rule of the mission: a wall built in play does not bar infantry's way as its
shape says, bench 2026-10-23). The wall melts after its lifetime; while one stands its time left shows on screen.
遇伏: 停下 -- retail Iga's escort: while a truck is on a plaza's approach and the plaza's troops are out, alive and
their gate open, the convoy stops under their fire and goes on once they are all down or the gate is iced (so ice
is what keeps it rolling).
广场 <k>: that plaza's own 每座兵 / 每座几个, and two more -- retail Iga's freeze, the one way through being the new
unit: 无敌 是, its sculptures nothing can aim at (they let their troops out when a truck gets there); 补兵 <time>,
while a truck is on its approach a troop of its that is down comes back every so often -- with 遇伏 停下 it holds the
convoy however many the player kills, until the gate is iced.

Units: 冰幕工兵 (the engineer), 冰雕. Cast sculpture k-i, troop k-i-n (the enemy's); marks seal k (where ice in
plaza k's gate stands), pass 1-2 (plaza 2's / 3's approach: the road past plaza 1 / 2).
"""
import re

from devices import Device
from missions import festival_parts as fp
from parts import Role, Script, square
from units import festival as fest
from units import icewall as iw

GATE_AREA = 90.0                                # half-side of the area a wall must stand in to hold a gate
CLEAR_MARGIN = 5.0                              # an engineer this near the gate's block counts as shut in it
WALL_SIDE = 160.0                               # the block spans the head of the gate's ramp (120 wide)
OWN = ('每座兵', '每座几个', '无敌', '补兵')     # what 广场 <k> may set for its plaza


class IcePlazas(Device):
    WHAT = '三个广场的冰雕里藏着兵，车队靠近冰雕就碎；冰幕工兵能在出口冻冰把兵关住，冰会化'
    PARAMS = {'车队': '哪个车队机关', '每座兵': '冰雕里依次藏的兵', '每座几个': '每座冰雕藏几个（简单/普通/困难）',
              '遇伏': '停下：车在广场路口、伏兵出来、出口没封时车队停在原地挨打，伏兵清光或出口冻上才走（原版伊贺）；不写就不停',
              '广场 <k>': 'k 号广场自己的参数：每座兵、每座几个，和 无敌: 是（冰雕谁都瞄不了，车到才放兵）、'
                         '补兵: <时间>（车在路口时，倒下的兵每隔这么久补回来；配 遇伏: 停下 就只能封口才过得去，原版伊贺"冻住"）'}
    EVENTS = {'封住 <k>': 'k 号广场出口现在有冰', '全部封住': '三个出口都冻过冰（每个算一次）',
              '封过 <n>': '已有 n 个出口冻过冰（每个算一次，冰化了也算）',
              '伏兵出来 <k>': 'k 号广场的冰雕碎了，兵出来了',
              '拦住 <k>': 'k 号广场的伏兵现在拦着车队（遇伏: 停下 时；车队停着）'}
    ACTIONS = {}

    def __init__(self, c, name, spec):
        super().__init__(c, name, spec)
        # the engineer builds a small core that leaves a square block of ice across the gate's ramp
        # (units/icewall.py seed: a bar comes out at 45 degrees whatever is asked, and the gates stayed open)
        self.wall = iw.wall(f'CNV_{c.tag}IceWall', length=WALL_SIDE, shape='square')
        self.core = iw.seed(f'CNV_{c.tag}IceSeed', self.wall.id)
        self.eng = iw.engineer(wall_id=self.core.id, stand=iw.clear_of(self.wall))   # not shut in his own block
        self.sculpt = fest.sculpture()
        self.units = [self.eng, self.core, self.wall, self.sculpt]
        self.names = {'冰幕工兵': self.eng, '冰雕': self.sculpt}
        self.sealed = f'CNV_{c.tag}_Sealed'
        stop = spec.get('遇伏')
        assert stop in (None, '停下'), f'{name}: 遇伏 {stop!r} -- only 停下 (or leave it out)'
        self.stops = stop == '停下'
        self.own = {}                               # plaza -> its own settings (广场 <k>)
        for key, v in spec.items():
            mm = re.fullmatch(r'广场\s*(\d+)', str(key))
            if mm:
                bad = sorted(set(v or {}) - set(OWN))
                assert isinstance(v, dict) and not bad, f'{name}: {key} sets {bad or v!r} -- only {OWN}'
                self.own[int(mm.group(1))] = v
        self.base = self.troops_of(spec, name)

    def troops_of(self, spec, what):
        """(kinds, how many by difficulty) a sculpture holds by `spec`."""
        import plan
        kinds = [self.c.unit(u, 's1') for u in spec.get('每座兵', ['坦克杀手', '帝国武士'])]
        many = plan.counts(spec.get('每座几个', len(kinds)))
        assert min(many) >= 1 and max(many) <= len(kinds), \
            f'{what}: 每座几个 {many} must be 1 .. {len(kinds)} (每座兵 lists {len(kinds)})'
        return kinds, many

    def setting(self, k):
        """Plaza k's (kinds, many, unattackable, refill times or None)."""
        import plan
        own = self.own.get(k, {})
        kinds, many = self.base
        if '每座兵' in own or '每座几个' in own:
            kinds, many = self.troops_of({'每座兵': own.get('每座兵', self.spec.get('每座兵', ['坦克杀手', '帝国武士'])),
                                          '每座几个': own.get('每座几个', self.spec.get('每座几个', len(kinds)))},
                                         f'{self.name}: 广场 {k}')
        tough = own.get('无敌') in (True, '是')
        assert own.get('无敌') in (None, True, False, '是', '否'), f'{self.name}: 广场 {k} 无敌 {own["无敌"]!r}: 是 / 否'
        refill = plan.times(own['补兵']) if own.get('补兵') is not None else None
        return kinds, many, tough, refill

    def troop(self, k, i, n):
        return f'UNIT - CNV {self.c.tag} Troop {k}-{i}-{n}'

    def place(self):
        m, c, tag = self.m, self.c, self.c.tag
        self.cdev = self.c.devices[self.spec['车队']]
        self.convoy = self.cdev.cv
        for k, site in ((1, 'approach 2'), (2, 'approach 3')):
            m.waypoint(f'pass {k}', f'CNV {tag} Pass {k}', site)
        self.plazas = fp.plazas(m, tag, at='inside')
        stray = sorted(set(self.own) - set(self.plazas))
        assert not stray, f'{self.name}: 广场 {stray} -- the map has plazas {self.plazas}'
        self.walls = {}
        for k in self.plazas:
            kinds, many, _, _ = self.setting(k)
            s = fp.north(m, k)
            for i, dx in enumerate((-45, 45), 1):
                m.put(self.sculpt.id, f'plaza {k}', dx, s * 30, side='s1', name=f'UNIT - CNV {tag} Sculpture {k}-{i}',
                      role=f'sculpture {k}-{i}')
                m.waypoints[f'CNV {tag} Hide {k}-{i}'] = m.site(f'plaza {k}', dx, -s * 30)
                for n in range(1, max(many) + 1):  # created when the sculpture breaks (contract: by that script)
                    m.cast[f'troop {k}-{i}-{n}'] = Role(kinds[n - 1], self.troop(k, i, n), 's1', [f'plaza {k}'])
            gate = f'CNV {tag} Gate {k}'
            m.areas[gate] = square(*m.point(f'seal {k}'), GATE_AREA)
            # an engineer the gate's block comes out round (he stood closer than `stand` when told): put outside it,
            # away from the plaza (bench 2026-10-26, ice_turns clear: shut in, he could not walk out)
            (sx, sy), (px, py) = m.point(f'seal {k}'), m.site(f'plaza {k}')
            far = iw.clear_of(self.wall) / max(1.0, ((sx - px) ** 2 + (sy - py) ** 2) ** 0.5)
            m.areas[f'CNV {tag} Block {k}'] = square(sx, sy, WALL_SIDE / 2 + CLEAR_MARGIN)
            m.waypoints[f'CNV {tag} Clear {k}'] = (sx + (sx - px) * far, sy + (sy - py) * far)
            m.areas[f'CNV {tag} Plaza {k}'] = square(*m.site(f'plaza {k}'), m.where(f'plaza {k}').r)
            p1 = m.player('p1')
            self.walls[k] = (('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, self.wall.id, gate),
                             ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 2, 0, self.wall.id, gate))

    def cond(self, event, args):
        if event == '封住':
            return [[self.walls[int(args[0])][0]]]
        if event == '全部封住':
            return [[('COUNTER', self.sealed, 3, len(self.plazas))]]
        if event == '封过':
            return [[('COUNTER', self.sealed, 3, int(args[0]))]]
        if event == '伏兵出来':
            return [[('FLAG', f'CNV_{self.c.tag}_Out_{int(args[0])}', 1)]]
        if event == '拦住':
            assert self.stops, f'{self.name}.拦住: the plazas stop the convoy only with 遇伏: 停下'
            return [[('FLAG', self.blocking(int(args[0])), 1)]]
        return super().cond(event, args)

    def blocking(self, k):
        return f'CNV_{self.c.tag}_Blocking_{k}'

    def scripts(self):
        import plan
        m, tag, cv = self.m, self.c.tag, self.convoy
        life = self.wall.params['lifetime']
        out = []
        for k in self.plazas:
            kinds, many, tough, refill = self.setting(k)
            names = [f'UNIT - CNV {tag} Sculpture {k}-{i}' for i in (1, 2)]
            approach = self.c.area(f'approach {k}')
            near = f'CNV_{tag}_Near_{k}'            # a truck got to this plaza (latched)
            here = f'CNV_{tag}_Here_{k}'            # a truck is on its approach now: 0 each frame, then 1 if so
            left = f'CNV_{tag}_Left_{k}'            # the plaza's troops out and alive (遇伏: 停下)
            counts = self.stops or refill is not None
            if counts:                              # read by what holds the convoy or brings troops back
                out += [Script(f'CNV {tag} - Here {k} none', [], [('SET_FLAG', here, 0)], once=False)]
                out += [Script(f'CNV {tag} - Here {k} by {j + 1}', [('NAMED_INSIDE_AREA', t, approach)],
                               [('SET_FLAG', here, 1)], once=False) for j, t in enumerate(cv.trucks)]
            if tough:                               # retail: UNATTACKABLE, nothing can aim at it (a script can kill it)
                out.append(Script(f'CNV {tag} - Tough {k}', [],
                                  [('UNIT_CHANGE_OBJECT_STATUS', n, 'UNATTACKABLE', 1) for n in names]))
            for i, sname in enumerate(names, 1):
                for levels, much in plan.by_level(many):
                    lv = '' if levels == plan.ALL else f' {plan.TAGS[levels.index(True)]}'
                    made = range(1, much + 1)
                    alive = [('SET_FLAG', self.alive(k, i, n), 1) for n in made] if refill is not None else []
                    out.append(Script(f'CNV {tag} - Out {k}-{i}{lv}',
                                      [('FLAG', near, 1)] if tough else [('NAMED_DESTROYED', sname)],
                                      [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', self.troop(k, i, n), kinds[n - 1],
                                        m.team('s1'), f'CNV {tag} Hide {k}-{i}') for n in made] + alive +
                                      [('SET_FLAG', f'CNV_{tag}_Out_{k}', 1), ('SET_FLAG', f'CNV_{tag}_Out_{k}_{i}', 1)]
                                      + ([('INCREMENT_COUNTER', much, left)] if counts else []), levels=levels))
                    if refill is not None:          # down, and back while a truck is there (once made: the convoy tail)
                        out += [Script(f'CNV {tag} - Down {k}-{i}-{n}{lv}',
                                       [('FLAG', self.alive(k, i, n), 1), ('NAMED_DESTROYED', self.troop(k, i, n))],
                                       [('DECREMENT_COUNTER', 1, left), ('SET_FLAG', self.alive(k, i, n), 0)],
                                       once=False, levels=levels) for n in made]
                        out += [Script(f'CNV {tag} - Back {k}-{i}-{n}{lv}',
                                       [('FLAG', f'CNV_{tag}_Out_{k}_{i}', 1), ('FLAG', self.alive(k, i, n), 0),
                                        ('FLAG', here, 1), ('TIMER_EXPIRED', self.refill(k))],
                                       [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', self.troop(k, i, n), kinds[n - 1],
                                         m.team('s1'), f'CNV {tag} Hide {k}-{i}'),
                                        ('SET_FLAG', self.alive(k, i, n), 1), ('INCREMENT_COUNTER', 1, left)],
                                       once=False, levels=levels) for n in made]
                    elif self.stops:
                        # only the troops made, once made: a name not yet on the map may read as destroyed (convoy tail)
                        out += [Script(f'CNV {tag} - Down {k}-{i}-{n}{lv}',
                                       [('FLAG', f'CNV_{tag}_Out_{k}_{i}', 1), ('NAMED_DESTROYED', self.troop(k, i, n))],
                                       [('DECREMENT_COUNTER', 1, left)], levels=levels) for n in made]
            if refill is not None:                  # the clock runs while a truck is there; the backs above come first
                out.append(Script(f'CNV {tag} - Refill {k} clock', [], [('SET_MILLISECOND_TIMER', self.refill(k), 0.0)]))
                for levels, gap in plan.by_level(refill):
                    lv = '' if levels == plan.ALL else f' {plan.TAGS[levels.index(True)]}'
                    out.append(Script(f'CNV {tag} - Refill {k} again{lv}',
                                      [('FLAG', here, 1), ('TIMER_EXPIRED', self.refill(k))],
                                      [('SET_MILLISECOND_TIMER', self.refill(k), gap)], once=False, levels=levels))
            out += [Script(f'CNV {tag} - Ambush {k} by {j + 1}', [('NAMED_INSIDE_AREA', t, approach)],
                           ([] if tough else [('NAMED_KILL', n) for n in names]) + [('SET_FLAG', near, 1)])
                    for j, t in enumerate(cv.trucks)]
            walled, open_ = self.walls[k]
            them = [self.troop(k, i, n) for i in (1, 2) for n in range(1, max(many) + 1)]
            # out, they go for the leading truck still on the road; held while ice stands in their gate
            out += [Script(f'CNV {tag} - Chase {k} at {j + 1}',
                           [('FLAG', f'CNV_{tag}_Out_{k}', 1), ('TIMER_EXPIRED', cv.timer), open_] + cv.chase(j),
                           [('NAMED_ATTACK_NAMED', t, target) for t in them], once=False)
                    for j, target in enumerate(cv.trucks)]
            out.append(Script(f'CNV {tag} - Held {k}', [('FLAG', f'CNV_{tag}_Out_{k}', 1), ('TIMER_EXPIRED', cv.timer),
                                                        walled],
                              [('UNIT_GUARD_AREA', t, f'CNV {tag} Plaza {k}') for t in them], once=False))
            if self.stops:                          # a truck there, troops out, gate open: the convoy waits under fire
                block = self.blocking(k)
                stop = self.cdev.hold(block)
                # troops that keep coming hold it however many fall: only ice lets it through (retail Iga's freeze)
                many_left = [('FLAG', f'CNV_{tag}_Out_{k}', 1)] if refill is not None else [('COUNTER', left, 3, 1)]
                out += [Script(f'CNV {tag} - Blocked {k}', [('FLAG', here, 1), ('FLAG', block, 0)] + many_left + [open_],
                               [('SET_FLAG', block, 1)] + stop, once=False),
                        Script(f'CNV {tag} - Iced past {k}', [('FLAG', block, 1), walled],
                               [('SET_FLAG', block, 0)], once=False),
                        # the truck that was there gone (the rest behind it, off the approach): they come up
                        Script(f'CNV {tag} - Nobody at {k}', [('FLAG', block, 1), ('FLAG', here, 0)],
                               [('SET_FLAG', block, 0)], once=False)]
                if refill is None:
                    out.append(Script(f'CNV {tag} - Cleared {k}', [('FLAG', block, 1), ('COUNTER', left, 1, 0)],
                                      [('SET_FLAG', block, 0)], once=False))
            # each gate counts once the first time it is walled; while a wall stands its time left shows
            out.append(Script(f'CNV {tag} - Sealed {k}', [walled], [('INCREMENT_COUNTER', 1, self.sealed)]))
            out += [Script(f'CNV {tag} - Clear {k} of {j + 1}', [walled, ('NAMED_INSIDE_AREA', e, f'CNV {tag} Block {k}')],
                           [('UNIT_TELEPORT_TO_WAYPOINT', e, f'CNV {tag} Clear {k}')], once=False)
                    for j, e in enumerate(self.engineers())]
            timer, up = f'CNV {tag} Ice {k}', f'CNV_{tag}_Ice_{k}'
            label = f'SCRIPT:CNV{tag}_ICE{k}'
            m.strings[label] = f'{k} 号冰墙'
            out += [Script(f'CNV {tag} - Ice {k} up', [walled, ('FLAG', up, 0)],
                           [('SET_FLAG', up, 1), ('SET_MILLISECOND_TIMER', timer, float(life)),
                            ('DISPLAY_COUNTDOWN_TIMER', timer, label)], once=False),
                    Script(f'CNV {tag} - Ice {k} gone', [open_, ('FLAG', up, 1)],
                           [('SET_FLAG', up, 0), ('HIDE_COUNTDOWN_TIMER', timer)], once=False)]
            m.countdowns.append(timer)
        return out

    def engineers(self):
        """Every engineer of the mission by name: the cast's, and those the plan's scripts create (给; scripts() runs
        after the plan's own are compiled)."""
        names = [r.name for r in self.m.cast.values() if r.template == self.eng.id]
        return list(dict.fromkeys(names + [a[1] for s in self.m.scripts for a in s.do
                                           if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT' and a[2] == self.eng.id]))

    def alive(self, k, i, n):
        return f'CNV_{self.c.tag}_Alive_{k}_{i}_{n}'

    def refill(self, k):
        return f'CNV {self.c.tag} Refill {k}'
