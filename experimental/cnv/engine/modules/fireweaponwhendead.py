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
import math

from engine.kernel import factory, interfaces, module
from engine.ports import templates

AIRBORNE = module.AIRBORNE      # the status bit of a thing in the air (as CreateObjectDie's)


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
                   templates.words(mux, 'DeathTypes', 'ALL'), templates.words(mux, 'DeathTypesForbidden'),
                   templates.words(mux, 'RequiredStatus'), templates.words(mux, 'ExemptStatus'))

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


class FireWeaponCollideData(module.ModuleData):
    def __init__(self, weapon='', flags=frozenset(), required=frozenset()):
        self.weapon, self.flags, self.required = weapon, flags, required    # CollideWeapon, Flags, RequiredStatus

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'CollideWeapon', ''), templates.words(head, 'Flags'),
                   templates.words(head, 'RequiredStatus'))


@factory.module('FireWeaponCollide')
class FireWeaponCollide(module.Module, interfaces.Die):
    """FireWeaponCollide (E217, benches/weapon/firing/readings.toml#engine_fwcollide), WHEN_BEING_CRUSHED only: its thing crushed
    (death CRUSHED) under its RequiredStatus -- its toggles' ObjectStatus now counted (the Flak trooper's armed mine)
    -- fires its CollideWeapon at the crusher (its last damage's object; World.fire `at`: Generals fires it at the
    other). Bench: a Hammer crushing an armed trooper at frame 43 is below 70 % from 44, one crushing an unarmed
    trooper whole (the trooper's own spot is 10.3 behind the Hammer that frame: radius 10 would miss). Not modelled:
    the other Flags (a collision with a thing: the retail ones are projectiles, which the simulator does not make);
    FireOnce holds (a crush is once)."""
    DATA = FireWeaponCollideData
    STATE = ()

    def on_die(self, info):
        d, b = self.data, self.thing
        if info.death == 'CRUSHED' and 'WHEN_BEING_CRUSHED' in d.flags and d.required <= _toggled(b):
            body = b.find(interfaces.Body)
            by = body.last_attacker() if body is not None else None
            self.world.fire(b, d.weapon, (by.x, by.y) if by is not None else None)


def _toggled(b):
    """Its status now (module.status_now) and its toggles' ObjectStatus in their state now."""
    return module.status_now(b).union(*(t.rules()['states'][t.state()]['status'] for t in b.find(interfaces.Toggle)))


class FireWeaponUpdateData(module.ModuleData):
    def __init__(self, weapons=(), frames=1, required=frozenset()):
        self.weapons = weapons      # each FireWeaponNugget's WeaponName
        self.frames = frames        # FireInterval, whole frames rounded up (at least 1)
        self.required = required    # ObjectStatusValidation RequiredStatus: every bit

    @classmethod
    def parse(cls, head, inner):
        return cls(tuple(templates.attr(h, 'WeaponName', '') for h, _ in templates.blocks(inner, 'FireWeaponNugget')),
                   max(1, math.ceil(templates.secs(templates.attr(head, 'FireInterval')) * 15 - 1e-6)),
                   templates.words(templates.child(inner, 'ObjectStatusValidation'), 'RequiredStatus'))


@factory.module('FireWeaponUpdate')
class FireWeaponUpdate(module.Module, interfaces.Update):
    """FireWeaponUpdate (E218, benches/weapon/firing/readings.toml#engine_fwupdate): while its thing holds the RequiredStatus (its
    toggles' counted: the Tesla trooper's short circuit), fires each weapon where it stands (World.fire) every
    FireInterval, from the frame the status is first seen. Not modelled: OneShot, ActiveWhenDisabled (the trooper's
    HELD), a dead thing's (no retail AliveOnly false among the 27 missions' templates); the Athena cannon's effect is
    no thing (simunits.ocl_round folds its weapon into the strike)."""
    DATA = FireWeaponUpdateData
    PHASE = 'toggles'
    ORDER = 1                   # after the toggles' own cell runs: a press's state is seen the same frame
    STATE = ()

    def update(self, frame):
        b, d = self.thing, self.data
        if not b.alive:
            return interfaces.SLEEP
        if not d.required <= _toggled(b):
            return 1
        for w in d.weapons:
            self.world.fire(b, w)
        return d.frames
