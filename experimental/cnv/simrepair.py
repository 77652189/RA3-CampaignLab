"""Measured AI-funded quarter/half/three-quarter-health power-plant repair.

The economy latch, dispatch phase and accumulator arithmetic follow D's
observations; general AI economy, player input and other repair configurations
remain unmeasured. No mission names or final counter offsets are used here.
"""
import struct
import xml.etree.ElementTree as ET

import simunits


def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]


class Repairs:
    def __init__(self, sim):
        self.sim = sim
        self.rules, self.active, self.blocked = {}, {}, set()
        self.refused = set()
        self.players = {}
        # Only explicit mission personalities with a measured difficulty gate.
        # Inherited personality/economy evaluation belongs to the AI line.
        for side, attrs in getattr(sim.m, 'sides', {}).items():
            if sim.players.get(side, side) == sim.human:
                continue
            pid = attrs.get('aiPersonality', '').split(':')[-1]
            for asset in getattr(sim.m, 'assets', ()):
                if len(asset) < 3 or asset[2] != 'AIPersonalityDefinition:' + pid:
                    continue
                root = ET.fromstring(asset[1])
                for el in root.iter():
                    if el.tag.split('}')[-1] == 'AIPersonalityDefinition' and el.get('id') == pid:
                        allowed = el.get('RepairBuildingsAtDifficulty', '').split()
                        if ('EASY', 'MEDIUM', 'HARD', 'BRUTAL')[sim.level] in allowed:
                            self.players[sim.players.get(side, side)] = True

    def due(self, frame):
        s = self.sim
        if not self.players or frame < 5:  # D42: default AI dispatch before the scripted wake.
            return
        for b in s.bodies.values():
            state = self.active.get(b.name)
            if b.name in self.refused:
                continue
            if state and (state['owner'] != b.owner or abs(b.hp - state['last_hp']) > 1e-6):
                s.gap('物体模块', 'RepairUpdate interrupted', '维修中血量或归属被外部改变的分支未测')
                self.active.pop(b.name, None)
                self.refused.add(b.name)
                continue
            if not b.alive or b.hp >= b.max_hp:
                self.active.pop(b.name, None)
                continue
            if not state:
                if b.owner not in self.players:
                    continue
                if any(x.alive and x.owner == b.owner and {'REFINERY', 'HARVESTER'} & x.kinds
                       for x in s.bodies.values()):
                    s.gap('物体模块', 'RepairUpdate economy', '有矿场/矿车时的AI经济门禁未测')
                    continue
                if not s.ai_switches.get(b.owner, {}).get('SKIRMISH_AI_USE_REPAIRS', 1):
                    continue
                if b.owner in self.blocked:
                    continue
                if s.money.get(b.owner, 0) < 5000:
                    # Measured no-economy latch; clearing it via mining is unmeasured.
                    self.blocked.add(b.owner)
                    s.gap('物体模块', 'RepairUpdate economy', '无经济低资金门禁；矿场清除此门禁未测')
                    continue
                if b.template not in self.rules:
                    self.rules[b.template] = (simunits.repair_update(b.template, s.own),
                                              simunits.repair_measured_config(b.template, s.own))
                rule, measured = self.rules[b.template]
                if rule is None:
                    continue
                cost = simunits.production(b.template, s.own)[0]
                if (not measured or rule != {'rate': 10, 'toggleable': True, 'dead': False, 'cost': (.5,) * 4}
                        or b.max_hp != 1000 or cost != 800
                        or not any(abs(b.hp / b.max_hp - fraction) <= 1e-6 for fraction in (.25, .5, .75))):
                    s.gap('物体模块', 'RepairUpdate', '仅测1000血800造价25%/50%/75%初始血量默认维修；其他配置/受损档未测')
                    continue
                state = self.active[b.name] = dict(owner=b.owner, cost=int((1 - b.hp / b.max_hp) * cost * .5),
                                                  r=f32(rule['rate'] / b.max_hp / 15), money=0., hp=0., last_hp=b.hp)
                s.gap('物体模块', 'RepairUpdate boundaries', '玩家入口、废墟、受伤/停修、非默认配置未测；启动相位INFERRED')
                continue
            old = f32(b.hp / b.max_hp)
            new = min(1., f32(old + state['r']))
            delta = f32(new - old)
            state['money'] = f32(state['money'] + f32(state['cost'] * delta))
            state['hp'] = f32(state['hp'] + f32(delta * b.max_hp))
            if state['money'] >= 1:
                n = int(state['money'])
                heal = f32(state['hp'] * n / state['money'])
                state['money'] = f32(state['money'] - n)
                state['hp'] = f32(state['hp'] - heal)
                if s.money.get(b.owner, 0) < n:
                    s.gap('物体模块', 'RepairUpdate insufficient funds', '激活后资金耗尽未上台')
                    self.active.pop(b.name, None)
                    self.refused.add(b.name)
                    continue
                s.money[b.owner] -= n
                b.hp = min(b.max_hp, b.hp + heal)
            elif new >= 1:
                b.hp = b.max_hp
            state['last_hp'] = b.hp
            s.used.add('repair')
