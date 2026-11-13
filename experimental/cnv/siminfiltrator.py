"""InfiltratorContain ENERGY, ordinary VISION and measured PARALYZE movement slices.

One retail Allied plant: 20 seconds of zero supply, spy consumed, owner unchanged.
Travel/entry reach and Amount * eligible energy duration scaling are INFERRED;
only Amount=.2 and eligible energy=100 have been measured.
engine_infvis:a/b measure Allied/Soviet yards' local vision.
VISION activation delay of five seconds is INFERRED from second-spaced samples;
Soviet first discovery is later; only stable windows replay, exact timing is a gap.
mapping the whole local radius to yard XML and parent-death cleanup are INFERRED.
Observer lifetime, other templates/players/spies and repeated entry remain gaps.
"""
import math
import os
import re

import simunits


def spec(template, own=None):
    def read(xml):
        text = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        def include(m):
            path = os.path.join(simunits.SAGEXML, *m.group(1).split('/'))
            return open(path, encoding='utf-8').read() if os.path.isfile(path) else ''
        text = re.sub(r'<xi:include\b[^>]*href="DATA:([^"]+)"[^>]*/>', include, text)
        head = next(simunits._blocks(text, 'InfiltratorContain'), None)
        return dict(re.findall(r'(\w+)="([^"]*)"', head[0])) if head else None
    return simunits._chain(template, own, read)


def filter_spec(name):
    """Retail named NONE filters; complex filters remain unsupported."""
    text = simunits.retail_xml('InfiltratorContainFilters')
    for head, body in simunits._blocks(text, 'ObjectFilterAsset'):
        if simunits._attr(head, 'id') != name:
            continue
        fh, fi = next(simunits._blocks(body, 'Filter'), ('', ''))
        if (simunits._attr(fh, 'Rule') != 'NONE'
                or set(re.findall(r'(\w+)\s*=', fh)) - {'Rule', 'Relationship'}):
            return None
        things = frozenset(x.strip().lower() for x in re.findall(r'<IncludeThing>([^<]+)</IncludeThing>', fi))
        if re.sub(r'<IncludeThing>[^<]+</IncludeThing>', '', fi).strip():
            return None
        return things, frozenset(simunits._attr(fh, 'Relationship', '').split())
    return None


class Infiltrators:
    def __init__(self, sim):
        self.sim = sim
        self.rules = {}
        self.going = {}
        self.off_until = {}
        self.observers = []
        self.paralyzed_until = {}
        self.paralyzed_hosts = set()

    def vision_rule(self, target, rule):
        return (target.template in ('AlliedConstructionYard', 'SovietConstructionYard')
                and rule.get('Effect') == 'VISION' and rule.get('Duration') == '-1s'
                and rule.get('ObjectRef') == 'VisionObserver' and not rule.get('ReplaceWith'))

    def paralyze_rule(self, target, rule):
        """E128/E129/E133 retail hosts and complete explicit module configuration.

        Extra attributes remain gaps even on a measured host: matching the
        host name must not enable unmeasured entry/status/duration variants.
        """
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template in ('AlliedTechStructure', 'SovietTechStructure', 'JapanTechStructure')
                and config == {'Effect': 'PARALYZE', 'Duration': '30s',
                               'UnitFilter': 'InfiltrationParalyzeObjectFilter'})

    def movement_blocked(self, body):
        """E128 movement only; no PARALYZED model-condition bit was observed."""
        return self.sim.frame_now() < self.paralyzed_until.get(id(body), 0)

    def sees(self, side, x, y, air=False):
        """Measured local yard shroud. Parent-death cleanup is INFERRED."""
        return any(owner == side and target.alive and self.sim.frame_now() >= start
                   and self.sim.looks(target, x, y, air)
                   for owner, target, start in self.observers)

    def spec(self, target):
        if target.template not in self.rules:
            self.rules[target.template] = spec(target.template, self.sim.own)
        return self.rules[target.template]

    def send(self, spy, target):
        s, rule = self.sim, self.spec(target)
        if not rule or not spy.alive or not target.alive:
            return
        entry = filter_spec(rule.get('CanEnterFilter', 'InfiltrationCanEnterObjectFilter'))
        if entry is None:
            s.gap('InfiltratorContain', target.template, '复杂进入筛选未对拍')
            return
        things, relations = entry
        if spy.template.lower() not in things or (relations and s.relation(target.owner, spy.owner) not in relations):
            return
        energy = (rule.get('Effect') == 'ENERGY' and rule.get('ObjectRef') == 'EnergyDisabler'
                  and not rule.get('ReplaceWith'))
        if not energy and not self.vision_rule(target, rule) and not self.paralyze_rule(target, rule):
            s.gap('InfiltratorContain', target.template, '仅已测ENERGY、普通VISION及三国科技中心原版PARALYZE配置已实现')
            return
        if self.paralyze_rule(target, rule) and (
                spy.owner != s.human or spy.template != 'AlliedInfiltrationInfantry'
                or id(target) in self.paralyzed_hosts):
            s.gap('InfiltratorContain', target.template, 'PARALYZE其他间谍/玩家或重复进入未对拍')
            return
        if self.vision_rule(target, rule) and (
                spy.owner != s.human or spy.template != 'AlliedInfiltrationInfantry'
                or any(parent is target for _, parent, _ in self.observers)):
            s.gap('InfiltratorContain', target.template, 'VISION其他玩家/间谍或重复渗透未对拍')
            return
        if target.status & set(rule.get('InfiltratedStatusFilter', 'DESTROYED UNDER_CONSTRUCTION SOLD UNPACKING').split()):
            return
        self.going[spy.name] = target
        spy.goal, spy.mode = target, 'infiltrate'
        s.send(spy, (target.x, target.y))

    def tick(self):
        s = self.sim
        for name, target in list(self.going.items()):
            spy = s.body(name)
            if not spy or not spy.alive or not target.alive or spy.mode != 'infiltrate' or spy.goal is not target:
                self.going.pop(name)
                continue
            shape = s.blocks(target)
            reach = (shape[2] if shape and len(shape) == 3 else 40.0) + 20.0
            distance = math.hypot(spy.x - target.x, spy.y - target.y)
            if distance > reach and (spy.path or distance > 2 * reach):
                continue
            self.going.pop(name)
            rule = self.spec(target)
            entry = filter_spec(rule.get('CanEnterFilter', 'InfiltrationCanEnterObjectFilter'))
            if (not entry or spy.template.lower() not in entry[0]
                    or (entry[1] and s.relation(target.owner, spy.owner) not in entry[1])
                    or target.status & set(rule.get('InfiltratedStatusFilter',
                                                   'DESTROYED UNDER_CONSTRUCTION SOLD UNPACKING').split())):
                continue
            if self.vision_rule(target, rule):
                # INFERRED: sampled consumption at s11, first local discovery at s16.
                # No engine mechanism or exact first-frame claim follows from this fit.
                self.observers.append((spy.owner, target, s.frame_now() + 5 * simunits.LIFE_FPS))
                s.destroy(spy, '进楼渗透', delete=True)
                s.change()
                continue
            if self.paralyze_rule(target, rule):
                selected = filter_spec(rule['UnitFilter'])
                if selected is None:
                    s.gap('InfiltratorContain', target.template, 'PARALYZE复杂目标筛选未对拍')
                    continue
                # INFERRED: apply once to existing units at entry, for the XML duration.
                # E128 b/E129 a/E133 a support stable movement windows, not exact expiry or new units.
                end = s.frame_now() + simunits._frames(float(rule['Duration'][:-1]))
                self.paralyzed_hosts.add(id(target))
                for body in s.living():
                    if body.owner != target.owner or body.template.lower() not in selected[0]:
                        continue
                    if body.template != 'AlliedAntiVehicleVehicleTech3':
                        s.gap('InfiltratorContain', body.template, 'PARALYZE其他匹配模板未对拍')
                        continue
                    self.paralyzed_until[id(body)] = end
                s.destroy(spy, '进楼渗透', delete=True)
                s.change()
                continue
            structure = filter_spec(rule.get('StructureFilter', ''))
            if structure is None:
                s.gap('InfiltratorContain', target.template, '复杂电力建筑筛选未对拍')
                continue
            energy = sum(max(0, simunits.energy(b.template, s.own)) for b in s.living()
                         if b.owner == target.owner and b.template.lower() in structure[0])
            duration = float(rule.get('Amount', '0')) * energy
            if energy != 100 or float(rule.get('Amount', '0')) != .2:
                s.gap('InfiltratorContain', target.template, '停电时长缩放INFERRED，仅0.2乘100电量已对拍')
            if self.disabled(target.owner):
                s.gap('InfiltratorContain', target.template, '重复渗透续期INFERRED，未对拍')
            end = s.frame_now() + round(duration * simunits.LIFE_FPS)
            self.off_until[target.owner] = max(self.off_until.get(target.owner, 0), end)
            s.destroy(spy, '进楼渗透', delete=True)
            s.change()

    def disabled(self, owner):
        return self.sim.frame_now() < self.off_until.get(owner, 0)
