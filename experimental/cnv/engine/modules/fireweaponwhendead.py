"""FireWeaponWhenDead (step B5c, ADR 0029, docs/engine/sim-modules.md 4; moved from simunits.death_weapons, which
simbody.Life.kill and the falling wreck's weapons of simunits.ocl_wrecks read): one module a FireWeaponWhenDead block.
Told of its thing's death, it fires its DeathWeapon where the thing died (World.fire: the host queues the weapon's
DamageNuggets as death blasts, simbody.Life.fire) when it is InitiallyActive and its DieMuxData's death types take the
death (module.DieMux.takes: a crush's CRUSHED, a lifetime's DeathType, else NORMAL) and its RequiredStatus /
ExemptStatus the thing's status (module.DieMux.holds: its status bits, AIRBORNE_TARGET in the air). Bench 11-05
engine_spawn_refill: S02_ExplodingMig (1000 GRENADE, radius 100, .3 s) killed by script takes the Guardian beside it
with it. A falling wreck, which the simulator does not make as a thing, fires its template's modules' weapons where it
rests through the same data (World.data_of, Life.air_crash: the Apollo's / MiG's NormalAircraftDeathWeapon).

Step B5c reads the template data port (the SDK's merge: a FireWeaponWhenDead inherited beside one of the template's
own is kept -- the old reader took the nearest template's only) and the status the old reader never read: the 47
Japanese templates' inherited EnhancedKamikazeDeathPlayerPowerWeapon (RequiredStatus PLAYER_POWER_1) fires only under
that bit, as before never; the time bomb's (alliedtimebomblvl2 / 3: its level's on the ground, the weaker in the
air) and the balloon's two weapons by whether it is in the air (the old reader fired both on the ground); a
SovietPowerPlantAdvanced's not while UNPACKING (a status bit the simulator does not set). The death's own type is read
where the old one asked NORMAL (no template's weapons differ for a crush or a lifetime's DeathType).
INFERRED, kept from the old reader: an upgrade-activated module (InitiallyActive false) never fires -- no upgrade
turns it on --; VeterancyLevels not read; a deletion fires nothing (Generals' destroyObject skips the die modules)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

AIRBORNE = module.AIRBORNE      # the status bit of a thing in the air (as CreateObjectDie's)


def _words(head, name, default=''):
    return frozenset((templates.attr(head, name) or default).split())


class FireWeaponWhenDeadData(module.ModuleData, module.DieMux):
    def __init__(self, weapon='', active=False, types=frozenset({'ALL'}), forbidden=frozenset(),
                 required=frozenset(), exempt=frozenset()):
        self.weapon = weapon        # DeathWeapon: the WeaponTemplate it fires
        self.active = active        # InitiallyActive (an upgrade would turn it on: not read)
        self.types = types          # DieMuxData DeathTypes (ALL, -X, +X, X)
        self.forbidden = forbidden  # DeathTypesForbidden
        self.required = required    # RequiredStatus: every bit
        self.exempt = exempt        # ExemptStatus: none of them

    @classmethod
    def parse(cls, head, inner):
        mux = templates.child(inner, 'DieMuxData')
        return cls(templates.attr(head, 'DeathWeapon', ''),
                   (templates.attr(head, 'InitiallyActive') or 'false').lower() == 'true',
                   _words(mux, 'DeathTypes', 'ALL'), _words(mux, 'DeathTypesForbidden'),
                   _words(mux, 'RequiredStatus'), _words(mux, 'ExemptStatus'))

    def fires(self, death, status=frozenset()):
        """A death of this type, of a thing with this status, sets its weapon off: active, its death types take it,
        the status holds its RequiredStatus and none of its ExemptStatus."""
        return self.active and self.takes(death) and self.holds(status)


@factory.module('FireWeaponWhenDead')
class FireWeaponWhenDead(module.Module, interfaces.Die, interfaces.DeathWeapon):
    """No update, no state of its own: told of its thing's death (on_die), it asks the host to fire its weapon."""
    DATA = FireWeaponWhenDeadData
    STATE = ()

    def on_die(self, info):
        if self.fires(info.death):
            self.world.fire(self.thing, self.data.weapon)

    def death_weapon(self):
        return self.data.weapon

    def fires(self, death):
        """By its thing's status now (module.status_now: its object status bits, AIRBORNE_TARGET while in the air --
        the same match as CreateObjectDie's, B5 review e #6)."""
        return self.data.fires(death, module.status_now(self.thing))
