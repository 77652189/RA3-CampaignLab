"""冰雕广场: A4's plazas (maps/festival.py: raised ground, one ramp each) with troops hidden in ice sculptures, and
the ice engineer who can shut a plaza's gate (units/icewall.py), as a plan device -- the A4 mechanics that were
missions/a4.py.

  机关: {冰雕广场: {类型: 冰雕广场, 车队: <a 车队 device>, 每座兵: [坦克杀手, 帝国武士, 坦克杀手], 每座几个: 1/2/3}}

Each plaza holds two sculptures; a sculpture's troops are the first 每座几个 of 每座兵 (by difficulty), created
where it stood when it breaks. A truck on a plaza's approach breaks that plaza's sculptures (one the player breaks
earlier lets its own out then). Out, they go for the leading truck still on the road -- unless ice stands in their
gate: then they guard their plaza (a rule of the mission: a wall built in play does not bar infantry's way as its
shape says, bench 2026-10-23). The wall melts after its lifetime; while one stands its time left shows on screen.

Units: 冰幕工兵 (the engineer), 冰雕. Cast sculpture k-i, troop k-i-n (the enemy's); marks seal k (where ice in
plaza k's gate stands), pass 1-2 (plaza 2's / 3's approach: the road past plaza 1 / 2).
"""
from devices import Device
from missions import festival_parts as fp
from parts import Role, Script, square
from units import festival as fest
from units import icewall as iw

GATE_AREA = 90.0                                # half-side of the area a wall must stand in to hold a gate
WALL_SIDE = 160.0                               # the block spans the head of the gate's ramp (120 wide)


class IcePlazas(Device):
    WHAT = '三个广场的冰雕里藏着兵，车队靠近冰雕就碎；冰幕工兵能在出口冻冰把兵关住，冰会化'
    PARAMS = {'车队': '哪个车队机关', '每座兵': '冰雕里依次藏的兵', '每座几个': '每座冰雕藏几个（简单/普通/困难）'}
    EVENTS = {'封住 <k>': 'k 号广场出口现在有冰', '全部封住': '三个出口都冻过冰（每个算一次）',
              '伏兵出来 <k>': 'k 号广场的冰雕碎了，兵出来了'}
    ACTIONS = {}

    def __init__(self, c, name, spec):
        super().__init__(c, name, spec)
        # the engineer builds a small core that leaves a square block of ice across the gate's ramp
        # (units/icewall.py seed: a bar comes out at 45 degrees whatever is asked, and the gates stayed open)
        self.wall = iw.wall(f'CNV_{c.tag}IceWall', length=WALL_SIDE, shape='square')
        self.core = iw.seed(f'CNV_{c.tag}IceSeed', self.wall.id)
        self.eng = iw.engineer(wall_id=self.core.id)
        self.sculpt = fest.sculpture()
        self.units = [self.eng, self.core, self.wall, self.sculpt]
        self.names = {'冰幕工兵': self.eng, '冰雕': self.sculpt}
        import plan
        self.kinds = [c.unit(u, 's1') for u in spec.get('每座兵', ['坦克杀手', '帝国武士'])]
        self.many = plan.counts(spec.get('每座几个', len(self.kinds)))
        assert min(self.many) >= 1 and max(self.many) <= len(self.kinds), \
            f'{name}: 每座几个 {self.many} must be 1 .. {len(self.kinds)} (每座兵 lists {len(self.kinds)})'
        self.sealed = f'CNV_{c.tag}_Sealed'

    def troop(self, k, i, n):
        return f'UNIT - CNV {self.c.tag} Troop {k}-{i}-{n}'

    def place(self):
        m, c, tag = self.m, self.c, self.c.tag
        self.convoy = self.c.devices[self.spec['车队']].cv
        for k, site in ((1, 'approach 2'), (2, 'approach 3')):
            m.waypoint(f'pass {k}', f'CNV {tag} Pass {k}', site)
        self.plazas = fp.plazas(m, tag, at='inside')
        self.walls = {}
        for k in self.plazas:
            s = fp.north(m, k)
            for i, dx in enumerate((-45, 45), 1):
                m.put(self.sculpt.id, f'plaza {k}', dx, s * 30, side='s1', name=f'UNIT - CNV {tag} Sculpture {k}-{i}',
                      role=f'sculpture {k}-{i}')
                m.waypoints[f'CNV {tag} Hide {k}-{i}'] = m.site(f'plaza {k}', dx, -s * 30)
                for n in range(1, max(self.many) + 1):     # created when the sculpture breaks (contract: by that script)
                    m.cast[f'troop {k}-{i}-{n}'] = Role(self.kinds[n - 1], self.troop(k, i, n), 's1', [f'plaza {k}'])
            gate = f'CNV {tag} Gate {k}'
            m.areas[gate] = square(*m.point(f'seal {k}'), GATE_AREA)
            m.areas[f'CNV {tag} Plaza {k}'] = square(*m.site(f'plaza {k}'), m.where(f'plaza {k}').r)
            p1 = m.player('p1')
            self.walls[k] = (('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, self.wall.id, gate),
                             ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 2, 0, self.wall.id, gate))

    def cond(self, event, args):
        if event == '封住':
            return [[self.walls[int(args[0])][0]]]
        if event == '全部封住':
            return [[('COUNTER', self.sealed, 3, len(self.plazas))]]
        if event == '伏兵出来':
            return [[('FLAG', f'CNV_{self.c.tag}_Out_{int(args[0])}', 1)]]
        return super().cond(event, args)

    def scripts(self):
        import plan
        m, tag, cv = self.m, self.c.tag, self.convoy
        life = self.wall.params['lifetime']
        out = []
        for k in self.plazas:
            names = [f'UNIT - CNV {tag} Sculpture {k}-{i}' for i in (1, 2)]
            for i, sname in enumerate(names, 1):
                for levels, many in plan.by_level(self.many):
                    out.append(Script(f'CNV {tag} - Out {k}-{i}' + ('' if levels == plan.ALL else
                                                                    f' {plan.TAGS[levels.index(True)]}'),
                                      [('NAMED_DESTROYED', sname)],
                                      [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', self.troop(k, i, n), self.kinds[n - 1],
                                        m.team('s1'), f'CNV {tag} Hide {k}-{i}') for n in range(1, many + 1)] +
                                      [('SET_FLAG', f'CNV_{tag}_Out_{k}', 1)], levels=levels))
            approach = self.c.area(f'approach {k}')
            out += [Script(f'CNV {tag} - Ambush {k} by {j + 1}', [('NAMED_INSIDE_AREA', t, approach)],
                           [('NAMED_KILL', n) for n in names]) for j, t in enumerate(cv.trucks)]
            walled, open_ = self.walls[k]
            them = [self.troop(k, i, n) for i in (1, 2) for n in range(1, max(self.many) + 1)]
            # out, they go for the leading truck still on the road; held while ice stands in their gate
            out += [Script(f'CNV {tag} - Chase {k} at {j + 1}',
                           [('FLAG', f'CNV_{tag}_Out_{k}', 1), ('TIMER_EXPIRED', cv.timer), open_] + cv.chase(j),
                           [('NAMED_ATTACK_NAMED', t, target) for t in them], once=False)
                    for j, target in enumerate(cv.trucks)]
            out.append(Script(f'CNV {tag} - Held {k}', [('FLAG', f'CNV_{tag}_Out_{k}', 1), ('TIMER_EXPIRED', cv.timer),
                                                        walled],
                              [('UNIT_GUARD_AREA', t, f'CNV {tag} Plaza {k}') for t in them], once=False))
            # each gate counts once the first time it is walled; while a wall stands its time left shows
            out.append(Script(f'CNV {tag} - Sealed {k}', [walled], [('INCREMENT_COUNTER', 1, self.sealed)]))
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
