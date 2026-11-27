"""Damage lines in the simulator: ActivateLinearDamageNugget + LinearDamageUpdate (the dolphin's sonar wave; engine line D's
vertical sweep, benches/weapon/target_effects/checks.py#engine_sweep, bench 11-10 rounds 12 / 16 / 17, work/re/handoff-d.md). The rules, from the
assembly (activate, update and total; work/re/handoff-archive.md) and held to the bench:

  start        a shot of a weapon with an ActivateLinearDamageNugget (its Lifetime) starts a line on the shooter's
               LinearDamageUpdate toward the target, flat (z dropped), from the shooter + StartDistanceOffset along it
  walk         Speed is a Velocity: BinaryAssetBuilder stores XML / 5 a logic frame (60 -> 12); total frames =
               min(Lifetime x 15, ceil(Length / (Speed / 5))); j frames after the shot the line holds
               floor(j x (Length / (2 x Radius)) / total) nodes (the module stops counting at ceil(Length / (2 x Radius)),
               one frame past total: the dll log's 23 nodes, 470 -> 910 in 37 frames, bench 11-10 04:22)
  node         node k at start + 2 x Radius x k fires the SweepWeapon there once: its DamageNuggets hit what of
               RadiusDamageAffects lies within the nugget's Radius of the node plus the body's own radius (edge to
               centre, FITTED: the Hammer 150 north is hit by node 4 at 130 -- 9 / 18 / 26 frames after the order to the
               rows at 150 / 250 / 350, the aimed one at 2)
  the end      walked out; the shooter dead or gone takes its line with it (round 17, check c: 9 / 158 / 167, the killed
               one's mid / far never hit); a stop does not cut a line already out (round 16, check b: 9 / 18 / 26)
Not modelled: FollowTerrain (flat maps), SweepFXList, ObjectStatusValidation, a second line while one walks (a new shot
starts another; retail has one per module -- INFERRED harmless at the bench's reload).

L3 (combat). It is given the world (simworld.WORLD_API only); its host's other parts come in as `peers` (`Peers`, the
names in PEERS only, read when used): the fight's first death (mark_first_death); a death is the kernel World's (kill)."""
import math
import re

import engine.data.units as simunits
from engine.combat.registry import standing

_memo, _weapon_blocks = {}, None

PEERS = frozenset({'mark_first_death'})


class Peers:
    """What the lines may reach on their host (the Sim) beyond the world: the names in PEERS, read when used."""
    __slots__ = ('host',)

    def __init__(self, host):
        self.host = host

    def __getattr__(self, name):
        if name not in PEERS:
            raise AttributeError(f'simsweep.Peers: {name} is not lent (PEERS)')
        return getattr(self.host, name)


def _weapon(wid, own):
    """(head, body) of WeaponTemplate `wid`: the mission's own XML first, then retail's."""
    global _weapon_blocks
    for text in (own or {}).values():
        for head, body in simunits._blocks(text or '', 'WeaponTemplate'):
            if simunits._attr(head, 'id') == wid:
                return head, body
    if _weapon_blocks is None:
        _weapon_blocks = {}
        for text in simunits._weapon_files():
            for head, body in simunits._blocks(re.sub(r'<!--.*?-->', '', text, flags=re.S), 'WeaponTemplate'):
                _weapon_blocks.setdefault(simunits._attr(head, 'id'), (head, body))
    return _weapon_blocks.get(wid, ('', ''))


def linear_damage(template, own=None):
    """The template's LinearDamageUpdate (nearest up the chain): {start, radius, length, speed (a frame), hits:
    [(damage, type, radius)], affects}; None without one."""
    key = (template, (own or {}).get(template))
    if key not in _memo:
        def read(xml):
            for head, _ in simunits._blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'LinearDamageUpdate'):
                return head
            return None
        try:
            head = simunits._chain(template, own, read)
        except (OSError, ValueError):
            head = None
        if head is None:
            _memo[key] = None
        else:
            whead, wbody = _weapon(simunits._attr(head, 'SweepWeapon'), own)
            hits = [(simunits._num(simunits._attr(h, 'Damage'), 0.0), simunits._attr(h, 'DamageType') or '',
                     simunits._num(simunits._attr(h, 'Radius'), 0.0))
                    for h, _ in simunits._blocks(re.sub(r'<!--.*?-->', '', wbody, flags=re.S), 'DamageNugget')]
            _memo[key] = dict(start=simunits._num(simunits._attr(head, 'StartDistanceOffset'), 0.0),
                              radius=simunits._num(simunits._attr(head, 'Radius'), 0.0),
                              length=simunits._num(simunits._attr(head, 'Length'), 0.0),
                              speed=simunits._num(simunits._attr(head, 'Speed'), 0.0) / 5.0,
                              hits=hits,
                              affects=frozenset((simunits._attr(whead, 'RadiusDamageAffects')
                                                 or 'ENEMIES NEUTRALS').split()))
    return _memo[key]


def circular_damage(template, own=None):
    """The template's CircularDamageUpdate (the Stingray's tesla nova): {max (MaxRadius), hits, relation, kinds, rule,
    water (ONLY_ON_WATER)} as linear_damage reads its line; None without one."""
    key = ('circle', template, (own or {}).get(template))
    if key not in _memo:
        def read(xml):
            return next(simunits._blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'CircularDamageUpdate'), None)
        try:
            block = simunits._chain(template, own, read)
        except (OSError, ValueError):
            block = None
        _memo[key] = None
        if block is not None:
            head, inner = block
            fh, _ = next(simunits._blocks(inner or '', 'ObjectFilter'), ('', ''))
            _, wbody = _weapon(simunits._attr(head, 'SweepWeapon'), own)
            _memo[key] = dict(max=simunits._num(simunits._attr(head, 'MaxRadius'), 100.0),
                              hits=[(simunits._num(simunits._attr(h, 'Damage'), 0.0), simunits._attr(h, 'DamageType') or '')
                                    for h, _ in simunits._blocks(re.sub(r'<!--.*?-->', '', wbody, flags=re.S), 'DamageNugget')],
                              relation={r.rstrip('S') for r in (simunits._attr(fh, 'Relationship') or '').split()},
                              kinds=frozenset((simunits._attr(fh, 'Include') or '').split()),
                              rule=simunits._attr(fh, 'Rule') or 'ANY',
                              water='ONLY_ON_WATER' in (simunits._attr(head, 'Flags') or ''))
    return _memo[key]


class Sweeps:
    """The lines walking and the rings spreading: started by Sim.deal on a shot, walked once a frame by due()."""

    def __init__(self, world, peers):
        self.world, self.peers, self.lines, self.rings = world, peers, [], []

    def fire(self, by, target, life, ring=False):
        """A shot of `by` at `target` whose weapon's ActivateLinearDamageNugget (ring: ActivateCircularDamageNugget)
        has Lifetime `life` s. A line walks from the shooter toward the target. A ring: the shooter's
        CircularDamageUpdate starts it at the weapon's point (the target's place then, not the shooter's -- the
        retail nova fires at its own feet), radius 0 the frame after, MaxRadius / (Lifetime x 15) more each frame up to
        MaxRadius; every object the ring reaches (its edge, FITTED as the line's nodes: the Hammers 50 / 100 / 150 off
        the centre first hit 6 / 10 / 14 frames after the order, the aimed one 2) that passes the module's ObjectFilter takes the
        SweepWeapon's DamageNuggets once. A new shot on the same module starts it again (one ring a module, the hit
        list cleared). work/re/a395_circular.md; bench engine_circular e / f."""
        world = self.world
        d = (circular_damage if ring else linear_damage)(by.template, world.own)
        lack = (('ActivateCircularDamageNugget', '射手没有 CircularDamageUpdate') if ring and d is None else
                ('CircularDamageUpdate', 'ONLY_ON_WATER 的水面筛选未建模（台上只测了陆地无旗）') if ring and d['water'] else
                ('ActivateLinearDamageNugget', '射手没有可用的 LinearDamageUpdate')
                if not ring and (d is None or d['speed'] <= 0 or d['radius'] <= 0) else None)
        if lack:
            world.gap('weapon', *lack)
        if d is None or lack and not ring:
            return
        now = world.frame_now()
        if ring:
            frames = max(round(life * simunits.LIFE_FPS), 1)
            self.rings[:] = [r for r in self.rings if r['by'] is not by]
            self.rings.append(dict(by=by, x=target.x, y=target.y, frame=now, step=d['max'] / frames,
                                   last=frames, hit=set(), d=d))
        else:
            dx, dy = target.x - by.x, target.y - by.y
            n = math.hypot(dx, dy)
            if not n:
                return
            ux, uy = dx / n, dy / n
            total = min(round(life * simunits.LIFE_FPS), math.ceil(d['length'] / d['speed']))
            self.lines.append(dict(by=by, x=by.x + ux * d['start'], y=by.y + uy * d['start'], ux=ux, uy=uy, frame=now,
                                   total=max(total, 1), nodes=math.ceil(d['length'] / (2 * d['radius'])), done=0, d=d))
        world.used.add('circular damage' if ring else 'linear damage')

    def spread(self, frame, living):
        world = self.world
        for ring in list(self.rings):
            by, d, k = ring['by'], ring['d'], frame - ring['frame'] - 1
            if not by.alive or k > ring['last']:
                self.rings.remove(ring)
                continue
            if k < 0:
                continue
            for t in living:
                if (t is by or not t.alive or t.serial in ring['hit'] or math.hypot(t.x - ring['x'], t.y - ring['y']) > k * ring['step'] + t.radius
                        or d['relation'] and standing(world, by.owner, t).rstrip('S') not in d['relation']
                        or not (t.kinds & d['kinds'] if d['rule'] == 'ANY' else d['kinds'] <= t.kinds)):
                    continue
                ring['hit'].add(t.serial)
                self.hit(by, t.x, t.y, dict(d, hits=[(dmg, typ, 0.0) for dmg, typ in d['hits']],
                                            affects=frozenset({standing(world, by.owner, t)})), frame, [t])

    def due(self, frame):
        living = self.world.living() if self.rings or self.lines else ()
        self.spread(frame, living)
        for line in list(self.lines):
            by, d = line['by'], line['d']
            if not by.alive:                                    # round 17: the killed one's line stops with it
                self.lines.remove(line)
                continue
            j = frame - line['frame']
            want = min(line['nodes'], j * (d['length'] / (2 * d['radius'])) // line['total'])
            while line['done'] < want:
                line['done'] += 1
                step = 2 * d['radius'] * line['done']
                self.hit(by, line['x'] + line['ux'] * step, line['y'] + line['uy'] * step, d, frame, living)
            if line['done'] >= line['nodes']:
                self.lines.remove(line)

    def hit(self, by, x, y, d, frame, among):
        world, peers = self.world, self.peers
        for t in among:
            if t is by or not t.alive or frame < t.immune_until or t.shielded or t.indestructible:
                continue
            if standing(world, by.owner, t) not in d['affects']:
                continue
            dist = math.hypot(t.x - x, t.y - y)
            for dmg, typ, reach in d['hits']:
                if dist > reach + t.radius:
                    continue
                armor = 1.0 if typ == 'UNRESISTABLE' else simunits.percent(t.armor, typ) / 100.0 * t.taken
                if dmg * armor * by.dealt <= 0:
                    continue
                t.damage(dmg * armor * by.dealt)
                t.set_last_damage(by.owner, by)
                if t.hp <= 0 and t.alive:
                    peers.mark_first_death(t, by)
                    world.world.kill(t, f'被 {world.label(by)} 的伤害线打掉')
