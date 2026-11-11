"""Injured ground vehicles returning to an enterable repair facility.

Finite evidence: engine_aipullpct low .2 / high .5 at 30% health. Tactics
owns the threshold and nearest-place decision. This adapter supplies live
health, faction repair places and the return order. Recycling, repair and
air/naval entry are not implemented. Arrival geometry is INFERRED from the
existing garrison approach; exact return seconds are not claimed.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

import simgarrison
import simunits


class Pullbacks:
    def __init__(self, world):
        self.sim = world
        self.returning = {}             # unit name -> (facility, destination, owner, path object)
        self.log = []                   # seconds, unit name, facility name
        self.armies = {}
        for path in Path(simunits.SAGEXML, 'SkirmishAI').glob('ArmyDef*.xml'):
            for el in ET.parse(path).getroot().iter():
                if el.tag.rsplit('}', 1)[-1] == 'ArmyDefinition':
                    self.armies[el.get('Side')] = el.get('VehicleRepairFacility')
        self.filters = {}

    def _filter(self, template):
        if template not in self.filters:
            def read(xml):
                for _, inner in simunits._blocks(xml, 'SlaughterHordeContain'):
                    for head, body in simunits._blocks(inner, 'CanAlwaysEnterObjectFilter'):
                        return head, body
                return None
            self.filters[template] = simunits._inherited(template, self.sim.own, read, None)
        return self.filters[template]

    def accepts(self, u, g):
        s = self.sim
        if (not u.alive or not g.alive or u.surface != 'ground'
                or 'STRUCTURE' not in g.kinds or s.relation(u.owner, g.owner) != 'ALLIES'):
            return False
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
        shape = self.sim.blocks(g)
        return (shape[2] if shape and len(shape) == 3 else 40.0) + simgarrison.ENTER_REACH

    def query(self, brain, member):
        """Tactics' pullback hook: health ratio and reachable, enterable repair places."""
        u, s = member.body, self.sim
        if not u.alive or u.max_hp <= 0 or u.surface != 'ground':
            return None
        side = next((side for side, owner in s.players.items() if owner == brain.player), '')
        faction = (s.m.sides.get(side) or {}).get('playerFaction')
        template = self.armies.get(faction)
        places = []
        for g in s.living():
            if g.template != template or not self.accepts(u, g):
                continue
            route = s.ground.within(u.surface, (u.x, u.y), (g.x, g.y), self.reach(g))
            if route is not None:
                places.append((brain.tid(g), (g.x, g.y), True))
        return u.hp / u.max_hp, places

    def send(self, u, g):
        if not self.accepts(u, g):
            return False
        u.goal = None
        self.sim.order_move(u, (g.x, g.y), False)
        self.returning[u.name] = (g, u.move_to, u.owner, u.path)
        self.log.append((self.sim.t, u.name, g.name))
        return True

    def busy(self, u):
        """Detached returners stay out of team recruitment, until cancelled or invalid."""
        entry = self.returning.get(u.name)
        if entry is None:
            return False
        g, destination, owner, path = entry
        if (not self.accepts(u, g) or u.owner != owner or u.move_to != destination
                or u.goal is not None or u.path is not path):
            self.returning.pop(u.name, None)
            return False
        return True
