"""What a unit is good against, from the simulator's own unit data (engine.data.units: the fight model's health, armour
and weapons) instead of its name.

The proxy player counters by kind (world.KINDS); a world gives each Mine / Offer a good_against set. This is where that
set comes from for a retail template: roles_from_name (world.py) stays the stand-in for one outside the SDK's tables
(a part of ours, CNV_*).

Matchup().dps(shooter, victim): the damage per second the shooter's weapons do to one victim standing in reach:
  - weapons: Matchup.weapons (the <Weapon> lines no upgrade gates, both sides of a toggle); of those the one that
    does the most to this victim (INFERRED: one weapon fires at a time);
  - a weapon must take the victim (engine.combat.range.takes: its anti mask against the victim's surface and kinds;
    an aircraft as airborne);
  - its rate x the victim's armour percent for its damage type (simunits.percent), each damage part apart where the
    data splits it (ai_parts), as the skirmish AI's rate reads it.
value_rate(shooter, victim) = dps x victim cost / victim MaxHealth: the money's worth destroyed per second, so a unit
and a kind compare whatever their health. good_against(shooter, refs) = the kinds whose mean value rate over
refs[kind] (victim templates) is at least `share` of the shooter's best kind's. REFS is a default roster (the three
factions' first-tier units of each kind). All of it INFERRED: a human's reading of the unit cards, not a program's.
"""
import types

import engine.combat.range as simrange
import engine.data.units as simunits
from engine.modules import weaponset

from proxy import world as pw

SHARE = 0.5                     # INFERRED: "made for" = at least half of the shooter's best kind

REFS = {                        # retail multiplayer units, one per faction and kind where the faction has one
    'infantry': ('AlliedAntiInfantryInfantry', 'SovietAntiInfantryInfantry', 'JapanAntiInfantryInfantry',
                 'AlliedAntiVehicleInfantry', 'SovietAntiVehicleInfantry', 'JapanAntiVehicleInfantry'),
    'vehicle': ('AlliedAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech1', 'JapanAntiVehicleVehicleTech1',
                'AlliedAntiAirVehicleTech1', 'SovietAntiInfantryVehicle', 'JapanAntiInfantryVehicle'),
    'air': ('AlliedFighterAircraft', 'SovietFighterAircraft', 'SovietAntiGroundAircraft', 'AlliedAntiGroundAircraft'),
    'ship': ('AlliedAntiNavyShipTech1', 'SovietAntiNavyShipTech1', 'JapanAntiVehicleShip'),
    'structure': ('AlliedBarracks', 'SovietBarracks', 'JapanBarracks', 'AlliedPowerPlant', 'SovietPowerPlant'),
}


class Matchup:
    def __init__(self):
        self._dps = {}

    @staticmethod
    def known(template):
        """Is it a template of the SDK's unit table (else the world falls back to roles_from_name)?"""
        return template.lower() in simunits.table()

    @staticmethod
    def kinds(template):
        return frozenset(simunits.stats(template)['kinds']) if Matchup.known(template) else frozenset()

    @staticmethod
    def health(template):
        return float(simunits.fight(template).get('hp') or 0.0)

    @staticmethod
    def cost(template):
        return int(simunits.production(template)[0])

    @staticmethod
    def weapons(template):
        """The weapons a fresh unit can fire: every <Weapon> line that needs no upgrade (both sides of a toggle -- a
        player toggles to what fits; the IFV's rider guns not), else fight's where no line has a condition."""
        sets = simunits.weapon_sets(template)
        if sets is None:
            return simunits.fight(template).get('weapons') or []
        return [w for slot in sets for need, _, _, w in slot
                if w and weaponset.armed(w) and not any(n.startswith(weaponset.UPGRADE_BIT) for n in need)]

    def dps(self, shooter, victim):
        key = (shooter, victim)
        if key not in self._dps:
            best = 0.0
            if self.known(victim) and self.known(shooter):
                kinds = self.kinds(victim)
                v = types.SimpleNamespace(kinds=kinds, surface='air' if 'AIRCRAFT' in kinds else
                                          simunits.stats(victim)['surface'])
                armor = simunits.fight(victim).get('armor') or {}
                for w in self.weapons(shooter):
                    if simrange.takes(w, v):
                        parts = w.get('ai_parts') or ((w['dps'], w['type']),)
                        best = max(best, sum(d * simunits.percent(armor, ty) / 100.0 for d, ty in parts))
            self._dps[key] = best
        return self._dps[key]

    def value_rate(self, shooter, victim):
        hp = self.health(victim) if self.known(victim) else 0.0
        return self.dps(shooter, victim) * self.cost(victim) / hp if hp else 0.0

    def rates(self, shooter, refs=None):
        """{kind: mean value_rate over refs[kind]} (kinds without a known ref left out)."""
        out = {}
        for kind, victims in (refs or REFS).items():
            known = [v for v in victims if self.known(v)]
            if known:
                out[kind] = sum(self.value_rate(shooter, v) for v in known) / len(known)
        return out

    def good_against(self, shooter, refs=None, share=SHARE):
        return self._good(self.rates(shooter, refs), share)

    @staticmethod
    def _good(r, share=SHARE):
        top = max(r.values(), default=0.0)
        return frozenset(k for k, x in r.items() if top > 0 and x >= share * top)

    def offer(self, template, refs=None, seconds=10.0):
        """A world adapter's sidebar button for template, from the data: KindOf, BuildCost, good_against, rates."""
        r = self.rates(template, refs)
        return pw.Offer(template, self.kinds(template), self.cost(template), self._good(r), seconds, rates=r)
