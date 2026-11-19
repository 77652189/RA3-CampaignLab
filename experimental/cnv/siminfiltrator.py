"""InfiltratorContain ENERGY, VISION, PARALYZE, money, crane KILL and vehicle entry.

One retail Allied plant: 20 seconds of zero supply, spy consumed, owner unchanged.
Travel/entry reach and Amount * eligible energy duration scaling are INFERRED;
only Amount=.2 and eligible energy=100 have been measured.
engine_infvis:a/b/c measure Allied/Soviet/Japan yards' local vision.
VISION activation delay of five seconds is INFERRED from second-spaced samples;
Soviet/Japan first discovery is later; only stable windows replay, exact timing is a gap.
mapping the whole local radius to yard XML and parent-death cleanup are INFERRED.
Observer lifetime, other templates/players/spies and repeated entry remain gaps.
E138/E205 KILL removes the hostile Allied spy and credits the crane owner;
fling distance, exact entry clock and death-module dispatch remain gaps.
E199/E200 VISION_UNITS: existing measured vehicle/aircraft/infantry/ship markers have
a five-pass discovery cycle, 0/1/1/1/1 from first observed spy disappearance.
Only the first 300 passes and stationary measured templates are implemented;
expiry, new units, movement and observer internals remain explicit gaps.
E201 port VISION measures local same/third-owner sight and a blocked second spy.
Exact activation and the XML blocking expiry remain INFERRED.
E195 RESET only consumes the hostile spy at a Soviet Iron Curtain; readiness
and actual cooldown remain unresolved. Entry reach/clock remain INFERRED.
Entry reach/clock remain INFERRED; the discovery trace uses an entry-relative clock.
L2 (ADR 0029, docs/engine/sim-layers.md): the world is reached only through simworld.WORLD_API (`world`), the host's
other parts through `peers` (Peers: the names in PEERS, read when used), the money through simmoney.Money (`wallet`:
held / charge / credit). This module never imports sim.
"""
import math
import re

import simunits
from engine.kernel import factory, interfaces


TAG = 'InfiltratorContain'


def _rule(rule, modules):
    """The first module's rule; a KILL host with sibling InfiltratorContains is marked (E205 measured one alone), a
    copy so the shared data stays as parsed."""
    if rule.get('Effect') == 'KILL' and modules != 1:
        return dict(rule, _unmeasured_siblings=modules)
    return rule


def spec(template, own=None):
    """The rule a thing of the template gets (the port's blocks, simunits.INCLUDED, parsed as its module's data:
    engine/modules/infiltrate.py), None without the tag. Step M15 census: the reader it replaced, 3448 retail + 520
    own templates, no difference (work/logs/m15_census.log). The tag is registered once engine.modules is imported
    (sim does)."""
    blocks = simunits.module_blocks(template, TAG, own)
    return _rule(factory.TAGS[TAG].DATA.parse(*blocks[0]).rule, len(blocks)) if blocks else None


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


PEERS = frozenset({'delete', 'destroy', 'looks', 'send'})


class Peers:
    """What the spies may reach on their host (the Sim) beyond the world: the names in PEERS, read when used -- the
    body's end (destroy / delete, L2), its walk (send, L2) and sight (looks)."""
    __slots__ = ('host',)

    def __init__(self, host):
        object.__setattr__(self, 'host', host)

    def __getattr__(self, name):
        if name not in PEERS:
            raise AttributeError(f'siminfiltrator.Peers: {name} is not lent (PEERS)')
        return getattr(self.host, name)


class Infiltrators:
    def __init__(self, world, peers, wallet):
        # simworld.WORLD_API only; the host's other parts (Peers); the players' money (simmoney.Money, L4)
        self.world, self.peers, self.wallet = world, peers, wallet
        self.going = {}
        self.off_until = {}
        self.observers = []
        self.unit_observers = []
        self.paralyzed_until = {}
        self.attack_until = {}

    def module(self, target):
        """The target's first InfiltratorContain module (engine/modules/infiltrate.py, the one the rule is read
        from), None without one."""
        found = target.find(interfaces.Infiltrate) if target is not None and target.modules else ()
        return found[0] if found else None

    def entered(self, target, slice_):
        """A spy has entered the target for this measured slice (the module keeps it, step M15)."""
        return self.module(target).entered(slice_)

    def mark(self, target, slice_):
        self.module(target).mark(slice_)

    def aircraft_rule(self, target, rule):
        """E197 complete retail airfield configuration; no reveal assumption."""
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template == 'AlliedAirfield'
                and config == {'Effect': 'VISION_UNITS', 'Duration': '30s',
                               'UnitDuration': '30s', 'ObjectRef': 'UnitVisionObserver',
                               'UnitFilter': 'InfiltrationAircraftObjectFilter',
                               'StructureFilter': 'InfiltrationAircraftStructuresFilter'})

    def aircraft_entry_measured(self, spy, target):
        world = self.world
        return (spy.owner == world.human and spy.template == 'AlliedInfiltrationInfantry'
                and not self.entered(target, 'aircraft'))

    def infantry_rule(self, target, rule):
        """E198 complete retail barracks configuration; no reveal assumption."""
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template == 'AlliedBarracks'
                and config == {'Effect': 'VISION_UNITS', 'Duration': '30s',
                               'UnitDuration': '30s', 'ObjectRef': 'UnitVisionObserver',
                               'UnitFilter': 'InfiltrationInfantryObjectFilter',
                               'StructureFilter': 'InfiltrationInfantryStructuresFilter'})

    def infantry_entry_measured(self, spy, target):
        world = self.world
        return (spy.owner == world.human and spy.template == 'AlliedInfiltrationInfantry'
                and not self.entered(target, 'infantry'))

    def ship_rule(self, target, rule):
        """E200 complete retail naval yard configuration; no reveal assumption."""
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template == 'AlliedNavalYard'
                and config == {'Effect': 'VISION_UNITS', 'Duration': '30s',
                               'UnitDuration': '30s', 'ObjectRef': 'UnitVisionObserver',
                               'UnitFilter': 'InfiltrationShipObjectFilter',
                               'StructureFilter': 'InfiltrationShipStructuresFilter'})

    def ship_entry_measured(self, spy, target):
        world = self.world
        return (spy.owner == world.human and spy.template == 'AlliedInfiltrationInfantry'
                and not self.entered(target, 'ship'))

    def port_rule(self, target, rule):
        """E201 complete retail port signature, independent of ordinary yards."""
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template == 'CA_PortStructure'
                and config == {'Effect': 'VISION', 'Duration': '-1s',
                               'BlockedDuration': '9999999s', 'ObjectRef': 'VisionObserver'})

    def port_entry_measured(self, spy):
        world = self.world
        return (spy.owner == world.human
                and spy.template == 'AlliedInfiltrationInfantry')

    def reset_rule(self, target, rule):
        """E195 retail Iron Curtain entry only; cooldown/ready remain gaps."""
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return target.template == 'SovietSuperWeapon' and config == {'Effect': 'RESET'}

    def reset_entry_measured(self, spy, target):
        world = self.world
        return (spy.owner == world.human and spy.template == 'AlliedInfiltrationInfantry'
                and not self.entered(target, 'reset'))

    def vehicle_rule(self, target, rule):
        """E194: measured factory entry only; intermittent discovery stays a gap."""
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template == 'AlliedWarFactory'
                and config == {'Effect': 'VISION_UNITS', 'Duration': '30s',
                               'UnitDuration': '30s', 'ObjectRef': 'UnitVisionObserver',
                               'UnitFilter': 'InfiltrationVehicleObjectFilter',
                               'StructureFilter': 'InfiltrationVehicleStructuresFilter'})

    def vehicle_entry_measured(self, spy, target):
        world = self.world
        return (spy.owner == world.human and spy.template == 'AlliedInfiltrationInfantry'
                and not self.entered(target, 'vehicle'))

    def money_rule(self, target, rule):
        """E193: one retail Allied refinery transfer; income blocking is a gap."""
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template == 'AlliedRefinery'
                and config == {'Effect': 'STEAL_MONEY', 'Amount': '2000',
                               'BlockedDuration': '30s'})

    def money_entry_measured(self, spy, target):
        world = self.world
        return (spy.owner == world.human and spy.template == 'AlliedInfiltrationInfantry'
                and not self.entered(target, 'money')
                and self.wallet.held(target.owner) >= 2000)

    def vision_rule(self, target, rule):
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template in ('AlliedConstructionYard', 'SovietConstructionYard',
                                    'JapanConstructionYard')
                and config == {'Effect': 'VISION', 'Duration': '-1s',
                               'ObjectRef': 'VisionObserver'})

    def paralyze_rule(self, target, rule):
        """E128/E129/E133 retail hosts and complete explicit module configuration.

        Extra attributes remain gaps even on a measured host: matching the
        host name must not enable unmeasured entry/status/duration variants.
        """
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template in ('AlliedTechStructure', 'SovietTechStructure', 'JapanTechStructure')
                and config == {'Effect': 'PARALYZE', 'Duration': '30s',
                               'UnitFilter': 'InfiltrationParalyzeObjectFilter'})

    def kill_rule(self, target, rule):
        """E205 complete signature; survival/player credit, not fling/death dispatch."""
        config = {key: value for key, value in rule.items() if key not in ('xmlns', 'id')}
        return (target.template == 'SovietCrane'
                and config == {'Effect': 'KILL', 'Amount': '1.5',
                               'EvaEventForInfiltratedPlayer': ''})

    def movement_blocked(self, body):
        """E128 movement only; no PARALYZED model-condition bit was observed."""
        world = self.world
        return world.frame_now() < self.paralyzed_until.get(body.serial, 0)

    def attack_blocked(self, body):
        """E139/E140/E141: existing Mirage fire, three retail tech hosts.

        Exact application/expiry phase is INFERRED from the XML duration.
        Other templates' attack consumers and retained orders remain gaps.
        """
        world = self.world
        return world.frame_now() < self.attack_until.get(body.serial, 0)

    def sees(self, side, x, y, air=False):
        """Measured local yard shroud. Parent-death cleanup is INFERRED."""
        world, peers = self.world, self.peers
        return any(owner == side and target.alive and world.frame_now() >= start
                   and peers.looks(target, x, y, air)
                   for owner, target, start in self.observers)

    def unit_discovered(self, side, body):
        """E199 named-object readout, not a general fog or observer simulation.

        Three independent 300-pass traces share 0/1/1/1/1 starting at the
        first script pass observing spy disappearance. In the simulator the
        spy is consumed after scripts, hence that first pass is entry + 1.
        INFERRED: using that anchor outside the measured entry frames. The
        three entries differ by five, so a global modulo-five phase is not
        distinguished by E199. See work/re/e199_vision_clock.md.
        E200 independently adds the ship: entry 182 (different modulo five),
        with the same relative sequence. This supports the disappearance anchor,
        but accepted entry and observer lifetime remain unobserved.
        No observer birth/death rule follows from this measured readout.
        """
        world = self.world
        now = world.frame_now()
        for owner, target, start, position in self.unit_observers:
            if owner != side or target is not body:
                continue
            age = now - start
            if not body.alive or (body.x, body.y) != position or age >= 300:
                world.gap('InfiltratorContain', body.template,
                             'VISION_UNITS移动/死亡/300帧后到期未对拍，见 work/re/e199_vision_clock.md')
                continue
            if age >= 0 and age % 5 != 0:
                return True
        return False

    def unit_vision(self, spy, target, rule):
        """Select only the existing same-owner templates measured by E199/E200.

        Filtering beyond these templates and later production remain gaps;
        do not turn a complete retail filter into unmeasured reveal coverage.
        """
        world = self.world
        measured = {'AlliedWarFactory': 'AlliedAntiVehicleVehicleTech1',
                    'AlliedAirfield': 'AlliedSupportAircraft',
                    'AlliedBarracks': 'AlliedEngineer',
                    'AlliedNavalYard': 'AlliedAntiAirShip'}
        # These measured complete configurations use a KindOf Include, not the
        # IncludeThing-only helper above. Do not broaden that helper's contract.
        kind = {'AlliedWarFactory': 'VEHICLE', 'AlliedAirfield': 'AIRCRAFT',
                'AlliedBarracks': 'INFANTRY', 'AlliedNavalYard': 'SHIP'}[target.template]
        for body in world.living():
            if body.owner != target.owner:
                continue
            if kind not in body.kinds:
                continue
            if body.template != measured[target.template]:
                world.gap('InfiltratorContain', body.template,
                             'VISION_UNITS其他匹配模板未对拍，见 work/re/e199_vision_clock.md')
                continue
            self.unit_observers.append((spy.owner, body, world.frame_now() + 1,
                                        (body.x, body.y)))

    def spec(self, target):
        """The target's rule (its module's data, shared by the template's things), None without the module."""
        found = target.find(interfaces.Infiltrate) if target.modules else ()
        return _rule(found[0].rules(), len(found)) if found else None

    def send(self, spy, target):
        world, peers = self.world, self.peers
        rule = self.spec(target)
        if not rule or not spy.alive or not target.alive:
            return
        entry = filter_spec(rule.get('CanEnterFilter', 'InfiltrationCanEnterObjectFilter'))
        if entry is None:
            world.gap('InfiltratorContain', target.template, '复杂进入筛选未对拍')
            return
        things, relations = entry
        if spy.template.lower() not in things or (relations and world.relation(target.owner, spy.owner) not in relations):
            return
        energy = (rule.get('Effect') == 'ENERGY' and rule.get('ObjectRef') == 'EnergyDisabler'
                  and not rule.get('ReplaceWith'))
        if not any((energy, self.vision_rule(target, rule), self.paralyze_rule(target, rule),
                    self.kill_rule(target, rule), self.money_rule(target, rule),
                    self.vehicle_rule(target, rule), self.reset_rule(target, rule),
                    self.aircraft_rule(target, rule), self.infantry_rule(target, rule),
                    self.ship_rule(target, rule), self.port_rule(target, rule))):
            world.gap('InfiltratorContain', target.template, '仅已测ENERGY、普通VISION、原版PARALYZE、单次STEAL_MONEY、起重机KILL存活、车辆、飞机、步兵、舰船及RESET入楼切片已实现')
            return
        if self.port_rule(target, rule):
            if not self.port_entry_measured(spy):
                world.gap('InfiltratorContain', target.template, '港口其他间谍/玩家未对拍')
                return
            if world.frame_now() < self.module(target).blocked_until():
                return  # E201 a: second remains alive; b checks the same order is legal.
        if self.aircraft_rule(target, rule) and not self.aircraft_entry_measured(spy, target):
            world.gap('InfiltratorContain', target.template, '飞机VISION_UNITS其他间谍/玩家或重复进入未对拍')
            return
        if self.infantry_rule(target, rule) and not self.infantry_entry_measured(spy, target):
            world.gap('InfiltratorContain', target.template, '步兵VISION_UNITS其他间谍/玩家或重复进入未对拍')
            return
        if self.ship_rule(target, rule) and not self.ship_entry_measured(spy, target):
            world.gap('InfiltratorContain', target.template, '舰船VISION_UNITS其他间谍/玩家或重复进入未对拍')
            return
        if self.reset_rule(target, rule) and not self.reset_entry_measured(spy, target):
            world.gap('InfiltratorContain', target.template, 'RESET其他间谍/玩家或重复进入未对拍')
            return
        if self.vehicle_rule(target, rule) and not self.vehicle_entry_measured(spy, target):
            world.gap('InfiltratorContain', target.template, '车辆VISION_UNITS其他间谍/玩家或重复进入未对拍')
            return
        if self.money_rule(target, rule) and not self.money_entry_measured(spy, target):
            world.gap('InfiltratorContain', target.template, 'STEAL_MONEY其他间谍/玩家、重复进入及余额不足未对拍')
            return
        if self.kill_rule(target, rule) and (
                spy.owner != world.human or spy.template != 'AlliedInfiltrationInfantry'
                or self.entered(target, 'kill')):
            world.gap('InfiltratorContain', target.template, 'KILL其他间谍/玩家或重复进入未对拍')
            return
        if self.paralyze_rule(target, rule) and (
                spy.owner != world.human or spy.template != 'AlliedInfiltrationInfantry'
                or self.entered(target, 'paralyze')):
            world.gap('InfiltratorContain', target.template, 'PARALYZE其他间谍/玩家或重复进入未对拍')
            return
        if self.vision_rule(target, rule) and (
                spy.owner != world.human or spy.template != 'AlliedInfiltrationInfantry'
                or any(parent is target for _, parent, _ in self.observers)):
            world.gap('InfiltratorContain', target.template, 'VISION其他玩家/间谍或重复渗透未对拍')
            return
        if target.status & set(rule.get('InfiltratedStatusFilter', 'DESTROYED UNDER_CONSTRUCTION SOLD UNPACKING').split()):
            return
        self.going[spy.name] = target
        spy.goal, spy.mode = target, 'infiltrate'
        peers.send(spy, (target.x, target.y))

    def tick(self):
        world, peers = self.world, self.peers
        for name, target in list(self.going.items()):
            spy = world.body(name)
            if not spy or not spy.alive or not target.alive or spy.mode != 'infiltrate' or spy.goal is not target:
                self.going.pop(name)
                continue
            shape = world.blocks(target)
            reach = (shape[2] if shape and len(shape) == 3 else 40.0) + 20.0
            distance = math.hypot(spy.x - target.x, spy.y - target.y)
            if distance > reach and (spy.path or distance > 2 * reach):
                continue
            self.going.pop(name)
            rule = self.spec(target)
            entry = filter_spec(rule.get('CanEnterFilter', 'InfiltrationCanEnterObjectFilter'))
            if (not entry or spy.template.lower() not in entry[0]
                    or (entry[1] and world.relation(target.owner, spy.owner) not in entry[1])
                    or target.status & set(rule.get('InfiltratedStatusFilter',
                                                   'DESTROYED UNDER_CONSTRUCTION SOLD UNPACKING').split())):
                continue
            if self.port_rule(target, rule):
                if not self.port_entry_measured(spy):
                    world.gap('InfiltratorContain', target.template, '港口入楼时资格变化未对拍')
                    continue
                if world.frame_now() < self.module(target).blocked_until():
                    continue
                # INFERRED: XML duration beyond the measured second-entry window;
                # E201 observes blocking through 41s, not its distant expiry.
                self.module(target).block(world.frame_now()
                    + simunits._frames(float(rule['BlockedDuration'][:-1])))
                # INFERRED: attach local sight at accepted entry; exact activation
                # phase/observer identity were not measured. Keep ordinary yards' delay.
                self.observers.append((spy.owner, target, world.frame_now()))
                world.gap('InfiltratorContain', target.template,
                      '港口精确入楼/观察者/死亡清理/阻断到期未对拍，见 work/re/e201_port.md')
                peers.delete(spy, '进港渗透')
                world.change()
                continue
            if self.aircraft_rule(target, rule):
                if not self.aircraft_entry_measured(spy, target):
                    world.gap('InfiltratorContain', target.template, '飞机VISION_UNITS入楼时资格变化未对拍')
                    continue
                self.mark(target, 'aircraft')
                self.unit_vision(spy, target, rule)
                world.gap('InfiltratorContain', target.template,
                      '飞机VISION_UNITS观察者内部/完整筛选/到期未闭合，见 work/re/e199_vision_clock.md')
                peers.delete(spy, '进楼渗透')
                world.change()
                continue
            if self.infantry_rule(target, rule):
                if not self.infantry_entry_measured(spy, target):
                    world.gap('InfiltratorContain', target.template, '步兵VISION_UNITS入楼时资格变化未对拍')
                    continue
                self.mark(target, 'infantry')
                self.unit_vision(spy, target, rule)
                world.gap('InfiltratorContain', target.template,
                      '步兵VISION_UNITS观察者内部/完整筛选/到期未闭合，见 work/re/e199_vision_clock.md')
                peers.delete(spy, '进楼渗透')
                world.change()
                continue
            if self.ship_rule(target, rule):
                if not self.ship_entry_measured(spy, target):
                    world.gap('InfiltratorContain', target.template, '舰船VISION_UNITS入楼时资格变化未对拍')
                    continue
                self.mark(target, 'ship')
                self.unit_vision(spy, target, rule)
                world.gap('InfiltratorContain', target.template,
                      '舰船VISION_UNITS观察者内部/完整筛选/到期未闭合，见 work/re/e200_ship.md')
                peers.delete(spy, '进楼渗透')
                world.change()
                continue
            if self.reset_rule(target, rule):
                if not self.reset_entry_measured(spy, target):
                    world.gap('InfiltratorContain', target.template, 'RESET入楼时资格变化未对拍')
                    continue
                self.mark(target, 'reset')
                # E61 observes entry, not an independent remaining cooldown.
                # Never interpret the short ready interruption as a reload time.
                world.gap('InfiltratorContain', target.template,
                      'RESET真实冷却与就绪条件未闭环，见 work/re/e195_reset.md')
                peers.delete(spy, '进楼渗透')
                world.change()
                continue
            if self.vehicle_rule(target, rule):
                if not self.vehicle_entry_measured(spy, target):
                    world.gap('InfiltratorContain', target.template, '车辆VISION_UNITS入楼时资格变化未对拍')
                    continue
                self.mark(target, 'vehicle')
                self.unit_vision(spy, target, rule)
                world.gap('InfiltratorContain', target.template,
                      '车辆VISION_UNITS观察者内部/完整筛选/到期未闭合，见 work/re/e199_vision_clock.md')
                peers.delete(spy, '进楼渗透')
                world.change()
                continue
            if self.kill_rule(target, rule):
                # INFERRED: ordinary lethal cleanup; E138 only observes survival,
                # not the fling trajectory, death animation or death-module dispatch.
                self.mark(target, 'kill')
                world.gap('InfiltratorContain', target.template,
                      'KILL存活及玩家击杀归属已接，抛飞/死亡模块派发未对拍，见 work/re/e205_kill.md')
                prior_attacker = spy.last_by is not None
                peers.destroy(spy, '起重机拒绝渗透')
                if not spy.alive and not prior_attacker:
                    # E205 c measures the host player's named-victim credit.
                    # No named killer was measured: do not invent one here.
                    world.kills.append((target.owner, None, spy.template, spy.name))
                else:
                    world.gap('InfiltratorContain', target.template,
                          'KILL已有伤害来源/免死进入者的击杀归属未对拍')
                world.change()
                continue
            if self.money_rule(target, rule):
                if not self.money_entry_measured(spy, target):
                    world.gap('InfiltratorContain', target.template, 'STEAL_MONEY入楼时资格变化未对拍')
                    continue
                amount = int(rule['Amount'])
                self.wallet.charge(target.owner, amount)
                self.wallet.credit(spy.owner, amount)
                self.mark(target, 'money')
                # E60 observed subsequent miner income. Do not invent a 30s
                # income freeze from BlockedDuration; its consumer remains a gap.
                peers.delete(spy, '进楼渗透')
                world.change()
                continue
            if self.vision_rule(target, rule):
                # INFERRED: sampled consumption at s11, first local discovery at s16.
                # No engine mechanism or exact first-frame claim follows from this fit.
                self.observers.append((spy.owner, target, world.frame_now() + 5 * simunits.LIFE_FPS))
                peers.delete(spy, '进楼渗透')
                world.change()
                continue
            if self.paralyze_rule(target, rule):
                selected = filter_spec(rule['UnitFilter'])
                if selected is None:
                    world.gap('InfiltratorContain', target.template, 'PARALYZE复杂目标筛选未对拍')
                    continue
                # INFERRED: apply once to existing units at entry, for the XML duration.
                # E128 b/E129 a/E133 a support stable movement windows, not exact expiry or new units.
                end = world.frame_now() + simunits._frames(float(rule['Duration'][:-1]))
                self.mark(target, 'paralyze')
                for body in world.living():
                    if body.owner != target.owner or body.template.lower() not in selected[0]:
                        continue
                    if body.template != 'AlliedAntiVehicleVehicleTech3':
                        world.gap('InfiltratorContain', body.template, 'PARALYZE其他匹配模板未对拍')
                        continue
                    self.paralyzed_until[body.serial] = end
                    if target.template in ('AlliedTechStructure', 'SovietTechStructure', 'JapanTechStructure'):
                        self.attack_until[body.serial] = end
                peers.delete(spy, '进楼渗透')
                world.change()
                continue
            structure = filter_spec(rule.get('StructureFilter', ''))
            if structure is None:
                world.gap('InfiltratorContain', target.template, '复杂电力建筑筛选未对拍')
                continue
            energy = sum(max(0, simunits.energy(b.template, world.own)) for b in world.living()
                         if b.owner == target.owner and b.template.lower() in structure[0])
            duration = float(rule.get('Amount', '0')) * energy
            if energy != 100 or float(rule.get('Amount', '0')) != .2:
                world.gap('InfiltratorContain', target.template, '停电时长缩放INFERRED，仅0.2乘100电量已对拍')
            if self.disabled(target.owner):
                world.gap('InfiltratorContain', target.template, '重复渗透续期INFERRED，未对拍')
            end = world.frame_now() + round(duration * simunits.LIFE_FPS)
            self.off_until[target.owner] = max(self.off_until.get(target.owner, 0), end)
            peers.delete(spy, '进楼渗透')
            world.change()

    def disabled(self, owner):
        world = self.world
        return world.frame_now() < self.off_until.get(owner, 0)
