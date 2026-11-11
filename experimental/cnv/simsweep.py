"""Damage lines in the simulator: ActivateLinearDamageNugget + LinearDamageUpdate (the dolphin's sonar wave; engine line D's
vertical sweep, checks/engine_sweep.py, bench 11-10 rounds 12 / 16 / 17, work/re/handoff-d.md). The rules, from the
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
starts another; retail has one per module -- INFERRED harmless at the bench's reload)."""
import math
import re

import simunits

_memo, _weapon_blocks = {}, None


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


class Sweeps:
    """The lines walking: started by Sim.deal on a shot, walked once a frame by due()."""

    def __init__(self, sim):
        self.sim, self.lines = sim, []

    def fire(self, by, target, life):
        """A shot of `by` at `target` whose weapon's ActivateLinearDamageNugget has Lifetime `life` s."""
        d = linear_damage(by.template, self.sim.own)
        if d is None or d['speed'] <= 0 or d['radius'] <= 0:
            self.sim.gap('weapon', 'ActivateLinearDamageNugget', '射手没有可用的 LinearDamageUpdate')
            return
        dx, dy = target.x - by.x, target.y - by.y
        n = math.hypot(dx, dy)
        if not n:
            return
        ux, uy = dx / n, dy / n
        total = min(round(life * simunits.LIFE_FPS), math.ceil(d['length'] / d['speed']))
        nodes = math.ceil(d['length'] / (2 * d['radius']))
        self.lines.append(dict(by=by, x=by.x + ux * d['start'], y=by.y + uy * d['start'], ux=ux, uy=uy,
                               frame=self.sim.frame_now(), total=max(total, 1), nodes=nodes, done=0, d=d))
        self.sim.used.add('linear damage')

    def due(self, frame):
        sim = self.sim
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
                self.hit(by, line['x'] + line['ux'] * step, line['y'] + line['uy'] * step, d, frame)
            if line['done'] >= line['nodes']:
                self.lines.remove(line)

    def hit(self, by, x, y, d, frame):
        sim = self.sim
        for t in sim.living():
            if t is by or frame < t.immune_until or t.shielded or t.indestructible:
                continue
            rel = sim.relation(by.owner, t.owner)
            if (rel + 'S' if rel == 'NEUTRAL' else rel) not in d['affects']:
                continue
            dist = math.hypot(t.x - x, t.y - y)
            for dmg, typ, reach in d['hits']:
                if dist > reach + t.radius:
                    continue
                armor = 1.0 if typ == 'UNRESISTABLE' else simunits.percent(t.armor, typ) / 100.0 * t.taken
                if dmg * armor * by.dealt <= 0:
                    continue
                t.damage(dmg * armor * by.dealt)
                t.last_hit, t.last_by = by.owner, by.name
                if t.hp <= 0 and t.alive:
                    if sim.first_death is None:
                        sim.first_death = (sim.t, t, by)
                    sim.destroy(t, f'被 {sim.label(by)} 的伤害线打掉')
