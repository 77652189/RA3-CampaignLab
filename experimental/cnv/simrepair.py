"""Measured AI-funded quarter/half/three-quarter-health power-plant repair.

The economy latch, dispatch phase and accumulator arithmetic follow D's
observations; general AI economy, player input and other repair configurations
remain unmeasured. No mission names or final counter offsets are used here.
L2 (ADR 0029, docs/engine/sim-layers.md): the world only through simworld.WORLD_API; the money through simmoney.Money
(held / charge); the AI switches and the difficulty handed in by the host.
Step M13 (ADR 0029): a structure's rules, its repair under way and its refusal are its RepairUpdate module's
(engine/modules/repair.py, found by interface); this keeps the players' gates and the loop.
"""
import struct
import xml.etree.ElementTree as ET

import simunits
from engine.kernel import interfaces


def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]


class Repairs:
    def __init__(self, world, wallet, ai_switches, level):
        """world: simworld.WORLD_API only; wallet: the players' money (simmoney.Money, L4); ai_switches: player ->
        {AI_SWITCHES name: value} (the scripts' / AI's dict, read when due); level: the difficulty (0 easy .. 3 brutal)."""
        self.world, self.wallet, self.ai_switches = world, wallet, ai_switches
        self.blocked = set()            # players the no-economy money latch stopped
        self.players = {}
        # Only explicit mission personalities with a measured difficulty gate.
        # Inherited personality/economy evaluation belongs to the AI line.
        for side, attrs in getattr(world.m, 'sides', {}).items():
            if world.players.get(side, side) == world.human:
                continue
            pid = attrs.get('aiPersonality', '').split(':')[-1]
            for asset in getattr(world.m, 'assets', ()):
                if len(asset) < 3 or asset[2] != 'AIPersonalityDefinition:' + pid:
                    continue
                root = ET.fromstring(asset[1])
                for el in root.iter():
                    if el.tag.split('}')[-1] == 'AIPersonalityDefinition' and el.get('id') == pid:
                        allowed = el.get('RepairBuildingsAtDifficulty', '').split()
                        if ('EASY', 'MEDIUM', 'HARD', 'BRUTAL')[level] in allowed:
                            self.players[world.players.get(side, side)] = True

    def due(self, frame):
        world = self.world
        if not self.players or frame < 5:  # D42: default AI dispatch before the scripted wake.
            return
        for b in world.bodies.values():
            mods = b.find(interfaces.Repair)
            m = mods[0] if mods else None       # several blocks: never the measured shape, never repaired
            state = m.job() if m else None
            if m is not None and m.refused():
                continue
            if state and (state['owner'] != b.owner or abs(b.hp - state['last_hp']) > 1e-6):
                world.gap('物体模块', 'RepairUpdate interrupted', '维修中血量或归属被外部改变的分支未测')
                m.refuse()
                continue
            if not b.alive or b.hp >= b.max_hp:
                if m is not None:
                    m.set_job(None)
                continue
            if not state:
                if b.owner not in self.players:
                    continue
                if any(x.alive and x.owner == b.owner and {'REFINERY', 'HARVESTER'} & x.kinds
                       for x in world.bodies.values()):
                    world.gap('物体模块', 'RepairUpdate economy', '有矿场/矿车时的AI经济门禁未测')
                    continue
                if not self.ai_switches.get(b.owner, {}).get('SKIRMISH_AI_USE_REPAIRS', 1):
                    continue
                if b.owner in self.blocked:
                    continue
                if self.wallet.held(b.owner) < 5000:
                    # Measured no-economy latch; clearing it via mining is unmeasured.
                    self.blocked.add(b.owner)
                    world.gap('物体模块', 'RepairUpdate economy', '无经济低资金门禁；矿场清除此门禁未测')
                    continue
                if m is None:
                    continue
                rule, measured = m.rules(), len(mods) == 1 and m.measured()
                cost = simunits.production(b.template, world.own)[0]
                if (not measured or rule != {'rate': 10, 'toggleable': True, 'dead': False, 'cost': (.5,) * 4}
                        or b.max_hp != 1000 or cost != 800
                        or not any(abs(b.hp / b.max_hp - fraction) <= 1e-6 for fraction in (.25, .5, .75))):
                    world.gap('物体模块', 'RepairUpdate', '仅测1000血800造价25%/50%/75%初始血量默认维修；其他配置/受损档未测')
                    continue
                m.set_job(dict(owner=b.owner, cost=int((1 - b.hp / b.max_hp) * cost * .5),
                               r=f32(rule['rate'] / b.max_hp / 15), money=0., hp=0., last_hp=b.hp))
                world.gap('物体模块', 'RepairUpdate boundaries', '玩家入口、废墟、受伤/停修、非默认配置未测；启动相位INFERRED')
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
                if self.wallet.held(b.owner) < n:
                    world.gap('物体模块', 'RepairUpdate insufficient funds', '激活后资金耗尽未上台')
                    m.refuse()
                    continue
                self.wallet.charge(b.owner, n)
                b.mend(heal)
            elif new >= 1:
                b.mend(float('inf'))
            state['last_hp'] = b.hp
            world.used.add('repair')
