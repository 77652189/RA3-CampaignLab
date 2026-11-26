"""Injured vehicles returning to an enterable repair facility.

Finite evidence: engine_aipullpct low .2 / high .5 at 30% health. Tactics
owns the threshold and nearest-place decision. This adapter supplies live
health, faction repair places and the return order: the ArmyDefinition's
VehicleRepairFacility for a ground mover, NavalRepairFacility for a water one,
both for an amphibian (the game's pull-back, bench aipullsnx / sny; a mission's
AIDataPack over the SDK's), AircraftRepairFacility for a flyer (aipullavp / axp). Recycling, repair and landing are not implemented. Arrival geometry is INFERRED from the
existing garrison approach; exact return seconds are not claimed.

L8 (the skirmish AI's tactics adapter: it orders units, it is not an object module). It is given the world
(simworld.WORLD_API only); its host's other parts come in as `peers` (`Peers`, the names in PEERS only, read when
used): the command port (R3 13f-1: the return is the AI's move order, given through it).
"""
from pathlib import Path
import xml.etree.ElementTree as ET

import engine.objects.garrison as simgarrison
import engine.data.units as simunits
from engine.kernel import interfaces
from engine.ports.command import Command

PEERS = frozenset({'commands'})
# the ArmyDefinition repair facilities a mover of this surface looks for (work/re b1126_armydef, the game's pull-back)
FACILITIES = {'ground': ('VehicleRepairFacility',), 'water': ('NavalRepairFacility',),
              'both': ('VehicleRepairFacility', 'NavalRepairFacility'), 'air': ('AircraftRepairFacility',)}


class Peers:
    """What the pullbacks may reach on their host (the Sim) beyond the world: the names in PEERS, read when used."""
    __slots__ = ('host',)

    def __init__(self, host):
        self.host = host

    def __getattr__(self, name):
        if name not in PEERS:
            raise AttributeError(f'simpullback.Peers: {name} is not lent (PEERS)')
        return getattr(self.host, name)


class Pullbacks:
    def __init__(self, world, peers):
        self.world, self.peers = world, peers
        # unit serial -> (facility, destination, owner, path object): by serial, not name (same-name review 1119b
        # O60 / N05: a unit made again under a dead returner's name, walking the very list, was taken for it)
        self.returning = {}
        self.log = []                   # seconds, unit name, facility name
        self.armies = None              # Side -> {field: template}, read on the first query
        self.filters = {}

    def _armies(self, settings):
        """The ArmyDefinitions: the SDK's, a mission's AIDataPack (missions/aiskirm_bench, Mission.statics) over them."""
        if self.armies is None:
            texts = [path.read_text(encoding='utf-8-sig')
                     for path in Path(simunits.SAGEXML, 'SkirmishAI').glob('ArmyDef*.xml')]
            texts += [p.xml().lstrip('﻿') for p in settings.statics if getattr(p, 'army', None)]
            self.armies = {}
            for text in texts:
                for el in ET.fromstring(text).iter():
                    if el.tag.rsplit('}', 1)[-1] == 'ArmyDefinition':
                        self.armies[el.get('Side')] = dict(el.attrib)
        return self.armies

    def _filter(self, template):
        if template not in self.filters:
            def read(xml):
                for _, inner in simunits._blocks(xml, 'SlaughterHordeContain'):
                    for head, body in simunits._blocks(inner, 'CanAlwaysEnterObjectFilter'):
                        return head, body
                return None
            world = self.world
            self.filters[template] = simunits._inherited(template, world.own, read, None)
        return self.filters[template]

    def accepts(self, u, g):
        world = self.world
        if (not u.alive or not g.alive or u.surface not in FACILITIES
                or 'STRUCTURE' not in g.kinds or world.relation(u.owner, g.owner) != 'ALLIES'):
            return False
        if u.surface == 'air':          # INFERRED: the game's "can it land there" is a parking place (aipullavp)
            return bool(g.find(interfaces.Parking))
        flt = self._filter(g.template)
        if flt is None:
            return False
        head, body = flt
        # Only the measured allied vehicle entry filter is supported here.
        if simunits._attr(head, 'Relationship') != 'ALLIES':
            return False
        kinds = set(u.kinds)
        include = set((simunits._attr(head, 'Include') or '').split())
        exclude = set((simunits._attr(head, 'Exclude') or '').split())
        status = set(u.status) | u.script_status
        no_status = set((simunits._attr(head, 'StatusBitFlagsExclude') or '').split())
        yes_status = set((simunits._attr(head, 'StatusBitFlags') or '').split())
        rule = simunits._attr(head, 'Rule') or 'ANY'
        if rule != 'ANY' or yes_status:
            return False               # other filters have not been measured
        named = f'<IncludeThing>{u.template}</IncludeThing>' in body
        return (bool(include & kinds) or named) and not (exclude & kinds or no_status & status)

    def reach(self, g):
        world = self.world
        shape = world.blocks(g)
        return (shape[2] if shape and len(shape) == 3 else 40.0) + simgarrison.ENTER_REACH

    def query(self, brain, member):
        """Tactics' pullback hook: health ratio and reachable, enterable repair places."""
        u, world = member.body, self.world
        if not u.alive or u.max_hp <= 0 or u.surface not in FACILITIES:
            return None
        side = next((side for side, owner in world.players.items() if owner == brain.player), '')
        faction = (brain.settings.sides.get(side) or {}).get('playerFaction')
        army = self._armies(brain.settings).get(faction) or {}
        templates = {army.get(k) for k in FACILITIES[u.surface]} - {None}
        places, ground = [], world.ground
        for g in world.living():
            if g.template not in templates or not self.accepts(u, g):
                continue
            # a flyer's facility is not path-checked (the game's flyer branch: work/re b1126_armydef)
            if u.surface == 'air' or ground.within(ground.walks(u), (u.x, u.y), (g.x, g.y), self.reach(g)) is not None:
                places.append((brain.tid(g), (g.x, g.y), True))
        return u.hp / u.max_hp, places

    def send(self, u, g):
        if not self.accepts(u, g):
            return False
        world, peers = self.world, self.peers
        # INFERRED: in the game the unit enters the repair facility; here it walks there, its target dropped first
        peers.commands.do(Command('move', f'ai:{u.owner}', units=(u.serial,), pos=(g.x, g.y),
                                  args=(('objects', 'serial'), ('drop_target', True))))
        self.returning[u.serial] = (g, u.move_to, u.owner, u.path)
        self.log.append((world.t, u.name, g.name))
        return True

    def busy(self, u):
        """Detached returners stay out of team recruitment, until cancelled or invalid."""
        entry = self.returning.get(u.serial)
        if entry is None:
            return False
        g, destination, owner, path = entry
        if (not self.accepts(u, g) or u.owner != owner or u.move_to != destination
                or u.goal is not None or u.path is not path):
            self.returning.pop(u.serial, None)
            return False
        return True
