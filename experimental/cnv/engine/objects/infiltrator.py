"""InfiltratorContain ENERGY, VISION, PARALYZE, money, crane KILL and vehicle entry.

One retail Allied plant: 20 seconds of zero supply, spy consumed, owner unchanged.
Travel/entry reach is INFERRED; the blackout lasts Amount x the entered plant's EnergyProduction
seconds (engine_infilpow h / i / j, one plant on the grid).
VISION's observer sees the yard's own VisionRange (150 / Japan 100), not its 1000 shroud (A408 H6):
engine_infvis:a/b/c's s16-s19 discovery recurs with no entry (d), so it was never VISION;
engine_infvis3 a/b see nothing within 30 s of entry. A reveal inside VisionRange and
parent-death cleanup are INFERRED (no bench shows the observer seeing anything).
Observer lifetime, other templates/players/spies and repeated entry remain gaps.
E138/E205 KILL removes the hostile Allied spy and credits the crane owner;
fling distance, exact entry clock and death-module dispatch remain gaps.
VISION_UNITS (E199/E200, A411/A412 engine_infunit): any host whose UnitFilter is a KindOf include watches its owner's
units of those kinds at entry: each shows 0/1/1/1/1 for UnitDuration, then every pass for 10 s, nothing while walking;
units around it are seen every pass. Units made after entry and repeated entry are unmeasured.
E201 port VISION measures local same/third-owner sight and a blocked second spy.
Exact activation and the XML blocking expiry remain INFERRED.
E195 RESET only consumes the hostile spy at a Soviet Iron Curtain; readiness
and actual cooldown remain unresolved. Entry reach/clock remain INFERRED.
Entry reach/clock remain INFERRED; the discovery trace uses an entry-relative clock.
L2 (ADR 0029, docs/engine/sim-layers.md): the world is reached only through simworld.WORLD_API (`world`), the host's
other parts through `peers` (Peers: the names in PEERS, read when used; a body's end is the kernel World's), the money through simmoney.Money (`wallet`:
held / charge / credit). This module never imports sim.
"""
import math
import re

import engine.data.units as simunits
import engine.objects.locomotion as simlocomotion
from engine.kernel import factory, interfaces


TAG = 'InfiltratorContain'
# VISION_UNITS: how far around a watched unit others are seen. INFERRED between A412 engine_infunit b's bounds: a
# neighbour 300 off seen every pass, a walker about 450 off at entry never (UnitVisionObserver's own ranges are 0).
UNIT_NEAR = 400.0


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


def kind_filter(name):
    """A retail filter that is a plain KindOf include (Rule NONE, Include only, nothing inside): its kinds, else None."""
    for head, body in simunits._blocks(simunits.retail_xml('InfiltratorContainFilters'), 'ObjectFilterAsset'):
        if simunits._attr(head, 'id') == name:
            fh, fi = next(simunits._blocks(body, 'Filter'), ('', ''))
            plain = simunits._attr(fh, 'Rule') == 'NONE' and set(re.findall(r'(\w+)\s*=', fh)) == {'Rule', 'Include'}
            return frozenset(simunits._attr(fh, 'Include').split()) if plain and not fi.strip() else None
    return None


PEERS = frozenset({'looks'})


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
        self.going = {}         # the spy's serial -> (the spy, its target): the objects send picked, not names
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

    def units_rule(self, target, rule):
        """VISION_UNITS: the KindOfs its UnitFilter includes (any host carrying it: A411 a Japan war factory, a Soviet
        barracks; its StructureFilter unread), None for another effect / observer or a filter not a plain include."""
        if rule.get('Effect') != 'VISION_UNITS' or rule.get('ObjectRef') != 'UnitVisionObserver':
            return None
        return kind_filter(rule.get('UnitFilter', ''))

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
        """The entered host's VisionRange (sight; its shroud range sees nothing, A408). Parent-death cleanup INFERRED."""
        world, peers = self.world, self.peers
        now = world.frame_now()
        return any(owner == side and target.alive and now >= start
                   and math.hypot(target.x - x, target.y - y) <= target.sight and peers.looks(target, x, y, air)
                   for owner, target, start in self.observers) or any(
            owner == side and 0 < math.hypot(body.x - x, body.y - y) <= UNIT_NEAR
            and self.unit_age(body, start, end) is not None and peers.looks(body, x, y, air)
            for owner, body, start, end in self.unit_observers)

    def unit_age(self, body, start, end):
        """Passes since a watched unit's observer began, None when it shows nothing: before it, after its end, the unit
        dead or walking (A412 engine_infunit b: a walker unseen till it stopped, then on the same clock)."""
        age = self.world.frame_now() - start
        return age if 0 <= age < end - start and body.alive and not body.path else None

    def unit_discovered(self, side, body):
        """A watched unit itself (E199 / E200: 0/1/1/1/1 from the pass after the spy is gone, for UnitDuration; A412
        engine_infunit b: then every pass for the observer's 10 s LifetimeUpdate, all gone 40 s after entry). Units
        around it are seen every pass all 40 s (sees, within UNIT_NEAR)."""
        hold = simunits._frames(10.0)
        for owner, watched, start, end in self.unit_observers:
            age = self.unit_age(body, start, end) if owner == side and watched is body else None
            if age is not None and (age % 5 or age >= end - start - hold):
                return True
        return False

    def unit_vision(self, spy, target, rule, kinds):
        """Watch every living unit of the host's owner of the filter's kinds (A411: a Japan war factory, a Soviet
        barracks too) from the pass after entry for UnitDuration + 10 s. Units made later (the StructureFilter's
        part?) are not watched: unmeasured."""
        start = self.world.frame_now() + 1
        end = start + simunits._frames(simunits._secs(rule.get('UnitDuration', '30s')) + 10.0)
        self.unit_observers += [(spy.owner, body, start, end) for body in self.world.living()
                                if body.owner == target.owner and kinds & set(body.kinds)]

    def spec(self, target):
        """The target's rule (its module's data, shared by the template's things), None without the module."""
        found = target.find(interfaces.Infiltrate) if target.modules else ()
        return _rule(found[0].rules(), len(found)) if found else None

    def send(self, spy, target):
        world = self.world
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
                    self.units_rule(target, rule), self.reset_rule(target, rule),
                    self.port_rule(target, rule))):
            world.gap('InfiltratorContain', target.template, '仅已测ENERGY、普通VISION、原版PARALYZE、单次STEAL_MONEY、起重机KILL存活、VISION_UNITS及RESET入楼切片已实现')
            return
        if self.port_rule(target, rule):
            if not self.port_entry_measured(spy):
                world.gap('InfiltratorContain', target.template, '港口其他间谍/玩家未对拍')
                return
            if world.frame_now() < self.module(target).blocked_until():
                return  # E201 a: second remains alive; b checks the same order is legal.
        if self.units_rule(target, rule) and self.entered(target, 'units'):
            world.gap('InfiltratorContain', target.template, 'VISION_UNITS重复进入未对拍')
            return
        if self.reset_rule(target, rule) and not self.reset_entry_measured(spy, target):
            world.gap('InfiltratorContain', target.template, 'RESET其他间谍/玩家或重复进入未对拍')
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
        self.going[spy.serial] = (spy, target)
        spy.goal, spy.mode = target, 'infiltrate'
        simlocomotion.go_to(world, spy, (target.x, target.y))

    def tick(self):
        world = self.world
        for key, (spy, target) in list(self.going.items()):
            if not spy.alive or not target.alive or spy.mode != 'infiltrate' or spy.goal is not target:
                self.going.pop(key)
                continue
            shape = world.blocks(target)
            reach = (shape[2] if shape and len(shape) == 3 else 40.0) + 20.0
            distance = math.hypot(spy.x - target.x, spy.y - target.y)
            if distance > reach and (spy.path or distance > 2 * reach):
                continue
            self.going.pop(key)
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
                now = world.frame_now()
                if now < self.module(target).blocked_until():
                    continue
                # INFERRED: XML duration beyond the measured second-entry window;
                # E201 observes blocking through 41s, not its distant expiry.
                self.module(target).block(now + simunits._frames(simunits._secs(rule['BlockedDuration'])))
                # INFERRED: attach local sight at accepted entry; exact activation
                # phase/observer identity were not measured. Keep ordinary yards' delay.
                self.observers.append((spy.owner, target, world.frame_now()))
                world.gap('InfiltratorContain', target.template,
                      '港口精确入楼/观察者/死亡清理/阻断到期未对拍，见 work/re/e201_port.md')
                world.world.remove(spy, '进港渗透')
                world.change()
                continue
            kinds = self.units_rule(target, rule)
            if kinds:
                if self.entered(target, 'units'):
                    world.gap('InfiltratorContain', target.template, 'VISION_UNITS重复进入未对拍')
                    continue
                self.mark(target, 'units')
                self.unit_vision(spy, target, rule, kinds)
                world.world.remove(spy, '进楼渗透')
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
                world.world.remove(spy, '进楼渗透')
                world.change()
                continue
            if self.kill_rule(target, rule):
                # INFERRED: ordinary lethal cleanup; E138 only observes survival,
                # not the fling trajectory, death animation or death-module dispatch.
                self.mark(target, 'kill')
                world.gap('InfiltratorContain', target.template,
                      'KILL存活及玩家击杀归属已接，抛飞/死亡模块派发未对拍，见 work/re/e205_kill.md')
                prior_attacker = spy.last_by is not None
                world.world.kill(spy, '起重机拒绝渗透')
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
                world.world.remove(spy, '进楼渗透')
                world.change()
                continue
            if self.vision_rule(target, rule):
                self.observers.append((spy.owner, target, world.frame_now()))   # INFERRED: sees from entry
                world.world.remove(spy, '进楼渗透')
                world.change()
                continue
            if self.paralyze_rule(target, rule):
                selected = filter_spec(rule['UnitFilter'])
                if selected is None:
                    world.gap('InfiltratorContain', target.template, 'PARALYZE复杂目标筛选未对拍')
                    continue
                # INFERRED: apply once to existing units at entry, for the XML duration.
                # E128 b/E129 a/E133 a support stable movement windows, not exact expiry or new units.
                end = world.frame_now() + simunits._frames(simunits._secs(rule['Duration']))
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
                world.world.remove(spy, '进楼渗透')
                world.change()
                continue
            # Amount x the entered plant's own EnergyProduction (engine_infilpow h / i / j: .2 x 100, .1 x 100 and
            # .2 x 200, the copies unlisted in its StructureFilter); the filter's part and grids of several plants unmeasured
            duration = float(rule.get('Amount', '0')) * max(0, simunits.energy(target.template, world.own))
            if self.disabled(target.owner):
                world.gap('InfiltratorContain', target.template, '重复渗透续期INFERRED，未对拍')
            end = world.frame_now() + round(duration * simunits.LIFE_FPS)
            self.off_until[target.owner] = max(self.off_until.get(target.owner, 0), end)
            world.world.remove(spy, '进楼渗透')
            world.change()

    def disabled(self, owner):
        """Dark: a spy's blackout (off_until), or the owner holds a living thing with EnergyDisablingBehavior
        (engine_infilpow e / f: a script-made EnergyDisabler darkens its owner until NAMED_DELETE; read off the retail
        templates only, a mission's own copy unmodelled)."""
        world = self.world
        return world.frame_now() < self.off_until.get(owner, 0) or any(
            b.owner == owner and simunits.module_blocks(b.template, 'EnergyDisablingBehavior')
            for b in world.living())
