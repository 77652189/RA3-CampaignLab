"""时停区: a time-stop zone that grows (A3 格林尼治时差, docs/engine/upgrades.md 5). The zone is made of rings; a ring is
a few circles (the unit units/stasis_zone.py, one object per circle, `半径` each) at named sites of the map, made at the
moment the ring's 开始 comes true and, if it has a 结束, taken away when that comes true. Every unit inside any circle,
of any side, stands still and can be neither hurt nor fire (the aura gives it retail's out-of-time status, a second at a
time); a unit that walks in later stops at the edge; a unit that leaves, or a zone that goes, is back within a second.
Nothing here knows who is where: the plan says when a ring grows and which sites it covers (circles may overlap; an
irregular area is several circles).

  机关: {时停区: {类型: 时停区, 半径: 450, 阵营: 敌,
                  圈: [{名: 一, 地点: [zone 1 a, zone 1 b], 开始: 开局},
                       {名: 二, 地点: [zone 2 a, zone 2 b], 开始: 段 天文台山 开始 + 2:00, 结束: 摧毁 generator}]}}

半径: each circle's reach (default 450). 阵营: whose the objects are (the zone stops everyone either way; default 敌).
圈: 名, 地点 (a list of map sites, the circle centres), 开始 (a condition, default 开局), 结束 (optional).

Published: events `圈 <名>` (that ring is on now); action `收圈 <名>` (take that ring away now).
"""
from devices import Device
from devices.rhythm import key_of
from parts import Script
from units import stasis_zone


def ring_flag(tag, name, k):
    """The flag that is 1 while ring k of device `name` is on (what a check reads)."""
    return f'CNV_{tag}_{key_of(name)}_Ring_{k}'


class Stasis(Device):
    WHAT = '一块会长大的时停区：一圈一圈地由几个圆拼成，到点在地图的几个地点上造出来，里面的敌我中立全停住；到点可以收'
    PARAMS = {'半径': '每个圆的半径（默认 450；多个圆可以重叠）', '阵营': '时停物体归谁（默认 敌；不分敌我都停）',
              '圈': '一串 {名, 地点: [地点, ...], 开始: 条件（默认 开局）, 结束: 条件（可选）}'}
    EVENTS = {'圈 <名>': '这一圈现在开着（造出来了、还没收）'}
    ACTIONS = {'收圈 <名>': '这一圈的时停物体全删掉，里面的单位一秒内恢复'}

    def __init__(self, ctx, name, spec):
        super().__init__(ctx, name, spec)
        from plantime import PlanError
        self.radius = float(spec.get('半径', 450))
        self.unit = stasis_zone.zone(id=f'CNV_{ctx.tag}StasisZone', radius=self.radius)
        self.units = [self.unit]
        self.owner = ctx.side(spec.get('阵营', '敌'))
        self.rings = []
        for r in spec.get('圈') or []:
            if not isinstance(r, dict) or not r.get('名') or not r.get('地点'):
                raise PlanError(f'{name}: 圈 {r!r} -- each {{名, 地点: [site, ...], 开始, 结束}}')
            self.rings.append(r)
        if not self.rings:
            raise PlanError(f'{name}: 时停区 needs 圈')
        names = [str(r['名']) for r in self.rings]
        if len(set(names)) != len(names):
            raise PlanError(f'{name}: 圈 names repeat: {names}')
        self.index = {n: k for k, n in enumerate(names)}
        self.flags = [ring_flag(ctx.tag, name, k) for k in range(len(self.rings))]
        ctx.spawns_add(self.unit.id)

    def objects(self, k):
        """The names of ring k's zone objects (one per site)."""
        key = key_of(self.name)
        return [f'UNIT - CNV {self.ctx.tag} {key} {k}-{j}' for j in range(len(self.rings[k]['地点']))]

    def ring(self, args):
        from plantime import PlanError
        n = ' '.join(args)
        if n not in self.index:
            raise PlanError(f'{self.name}: no ring {n!r}: {sorted(self.index)}')
        return self.index[n]

    def cond(self, event, args):
        if event == '圈':
            return [[('FLAG', self.flags[self.ring(args)], 1)]]
        return super().cond(event, args)

    def action(self, what, args):
        if what == '收圈':
            k = self.ring(args)
            return [('NAMED_DELETE', o) for o in self.objects(k)] + [('SET_FLAG', self.flags[k], 0)]
        return super().action(what, args)

    def scripts(self):
        ctx, key = self.ctx, key_of(self.name)
        team = ctx.team(self.owner)
        for k, r in enumerate(self.rings):
            make = [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', o, self.unit.id, team, ctx.mark(site))
                    for o, site in zip(self.objects(k), r['地点'])]
            ctx.when(f'{key} ring {k} on', r.get('开始', '开局'), make + [('SET_FLAG', self.flags[k], 1)])
            if r.get('结束'):
                ctx.when(f'{key} ring {k} off', r['结束'],
                         [('NAMED_DELETE', o) for o in self.objects(k)] + [('SET_FLAG', self.flags[k], 0)])
        return []
