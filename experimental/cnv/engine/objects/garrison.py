"""Garrisons in the simulator: GarrisonContain / ContestableGarrisonContain (sim.Sim.garrison; simai's AI walks its men
in through the same object). The rules are the XML's (GarrisonContain's fields) and the bench's readings
(checks/engine_garrison.py in / hp, bench 11-05, del 11-17; docs/engine/garrison.md):

  who          the PassengerFilter (Include kinds by its Rule, ExcludeThing templates) -- kept for every entry; then the
               relation of the unit to the building (world.relation: no owner = NEUTRAL): AllowEnemiesInside /
               AllowNeutralInside / AllowAlliesInside, own player with AllowOwnPlayerInsideOverride; then fewer than
               ContainMax inside. The script's NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY skips the relation and the
               room (garrison.md 1: six into a five-place house; an enemy into the player's, the player's into the
               enemy's), and so does a unit carrying every RequiredClearingObjectStatus bit of a contestable one
  contest      such a unit coming into a ContestableGarrisonContain: the first passenger of another team and not allied
               is pushed out and the newcomer stays out (garrison.md 5: one of the player's two came out, the contesting
               conscript never in; a plain enemy put in stays beside them)
  inside       the passenger stands at the building's spot carrying ObjectStatusOfContained (UNSELECTABLE ENCLOSED
               CAN_ATTACK for a house: ENCLOSED is what the checks count) + INSIDE_STATUS; the building's owner is the
               first passenger's, empty again the owner it had before (garrison.md 1 / 2: 16 / 15 / 0)
  out          NAMED_EXIT_BUILDING (the unit); a sale, all out in the sale's frame (bench 11-17 engine_sell g, a
               SovietBunker; a house without StructureSellUpdate is not sold at all, engine_garrison del);
               REALLYDAMAGED -- the health at
               or under ActiveBody's MaxHealthReallyDamagedPercentage (default 33.333333 %) without KindOf
               GARRISONABLE_UNTIL_DESTROYED -- orders all out (garrison.md 3: out at 13 %)
  the end      the building killed (a hit or a script's kill, garrison.md 4): KillPassengersOnDeath kills them (the
               Multigunner turret), else they come out alive (DamagePercentToUnits: none of the retail houses writes
               it, not modelled); a deleted building takes them with it (bench 11-17 engine_garrison del: NAMED_DELETE
               on a house with three in, none of them left)
Transports (TransportContain: the Bullfrog, the Riptide, the bomber; bench 11-10 checks/engine_transport.py load):
  in           the script's TEAM_ / NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY as into a house -- no room, no relation
               (six into the five-place Bullfrog, Soviet_4's two into the player's); the AI never picks one (places)
  walk in      the script's TEAM_GARRISON_SPECIFIC_BUILDING (not instantly): walks to it and goes in as into a house,
               the room asked (bench 11-13 engine_acts_tel: five of six into the five-place Bullfrog, one a second);
               the relation as a house's (INFERRED). The NAMED_ one still only walks to a transport (sim.py: s01)
  ride         a passenger stands where its transport is, every frame (inside an area with it, ENCLOSED all along)
  eject        a button whose power an EjectPassengersSpecialAbilityUpdate serves, at a waypoint: one out every
               TimePerPassenger from the moment it is pressed (within StartAbilityRange; farther, the transport drives
               in first -- INFERRED), each landing on the spot EJECT_FLIGHT later (out of ENCLOSED at once)
  the end      KillPassengersOnDeath (every retail transport): a killed transport kills them (NAMED_KILL too)
  not          the REALLYDAMAGED walk-out (a house's only), the passengers' fire, the parachute (untargeted) eject
Not modelled: fire from inside (the passengers keep their own weapons; a turret's weapon set by its passenger), the
garrison aura, clearing weapons, the exit point (they come out where the building stands), EjectSpeed.
L2 (ADR 0029, docs/engine/sim-layers.md): the world is reached only through simworld.WORLD_API (`world`), the host's
other parts through `peers` (Peers: the names in PEERS, read when used). This module never imports sim."""
import math
import re

import engine.data.units as simunits
import engine.modules.locomotor as locomotor
from engine.kernel import interfaces

TAGS = ('GarrisonContain', 'ContestableGarrisonContain')
TRANSPORT = ('TransportContain',)
EVACUATE_DELAY = 1.5            # INFERRED from engine_acts_btn EV (round 221): all in 1 s after the press, all out at 2 s
EJECT_FLIGHT = 2.0             # INFERRED from bench 11-10 engine_transport load 跳 (ENCLOSED 3 1 0 at s2-s4, inside
                                # the far square 0 2 3 at s4-s6: out 0.5 s apart, down ~2 s later, 500 away)
REALLY_DAMAGED = 33.333333      # ActiveBody.xsd MaxHealthReallyDamagedPercentage's default (percent)
ENTER_REACH = 20.0              # INFERRED: in at the building's side (its round + this; as Sim.capture_due's)
ARRIVE = 10.0                   # INFERRED: StartAbilityRange 0's "there" (a frame of the bomber's flight, 150 / 15)
INSIDE_STATUS = frozenset({'IMMOBILE', 'UNATTACKABLE'})     # INFERRED: a passenger neither walks nor is shot at
                                                            # by itself (the building takes the hits)
CIV = 'PlyrCivilian'


_memo = {}


def really(template, own=None):
    """The REALLYDAMAGED line in percent: the nearest ActiveBody up the chain writing MaxHealthReallyDamagedPercentage,
    else the default (step M14: what simgarrison.spec read beside the garrison block, which is the contain module's)."""
    key = (template, (own or {}).get(template))
    if key not in _memo:
        bodies = []

        def walk(xml):
            bodies.extend(h for h, _ in simunits._blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S),
                                                         'ActiveBody'))
        try:
            simunits._chain(template, own, walk)
        except (OSError, ValueError):
            pass
        v = next((simunits._attr(h, 'MaxHealthReallyDamagedPercentage') for h in bodies
                  if simunits._attr(h, 'MaxHealthReallyDamagedPercentage')), None)
        _memo[key] = float(v.rstrip('%')) if v else REALLY_DAMAGED
    return _memo[key]


def contain(b, tags=TAGS):
    """b's contain module of the nearest of `tags` (GarrisonContain / ContestableGarrisonContain, or TransportContain),
    None without one. A thing has at most one of a tag (the port gathers the chain's into one block) and no template
    has both garrison tags (step M14 census: 3448 retail + 520 own)."""
    for m in b.find(interfaces.Contain) if b is not None and b.modules else ():
        if m.data.TAG in tags:
            return m
    return None


def ejects(command, own=None):
    """The button fires an eject-the-passengers power (SpecialPower_EjectPassengers*: the man cannon, the paradrop)."""
    return str(simunits.command_power(command, own) or '').startswith('SpecialPower_EjectPassengers')


PEERS = frozenset({'_upgrade', 'delete', 'destroy', 'modify', 'send'})


class Peers:
    """What the garrisons may reach on their host (the Sim) beyond the world: the names in PEERS, read when used --
    L2 upgrades (_upgrade), the body's end (destroy / delete), modifiers (modify) and its walk (send). L5's order_move
    is handed in as `move` (the enter order's walk: mode, move_to, its spot; a bare go_to lets an idle walker turn to fight,
    unbenched -- the enter order moves up into order.py at the move family's close)."""
    __slots__ = ('host',)

    def __init__(self, host):
        object.__setattr__(self, 'host', host)

    def __getattr__(self, name):
        if name not in PEERS:
            raise AttributeError(f'simgarrison.Peers: {name} is not lent (PEERS)')
        return getattr(self.host, name)


class Garrisons:
    def __init__(self, world, peers, move):
        self.world, self.peers, self.move = world, peers, move    # WORLD_API only; the host's other parts (Peers); L5's move
        self.boxes = {}             # host serial (Thing.serial) -> its contain module (interfaces.Contain: the
                                    # passengers, the owner before, the listener's upgrades), in the order first put
                                    # into (the cell's order); by the thing, not its name: a thing made under a taken
                                    # name has none of the old one's passengers (step B4c-3, INFERRED)
        self.where = {}             # passenger serial -> building body
        self.going = {}             # serial -> (the body, the building body it was sent into) (the AI's walk); both
                                    # by the thing picked, not its name (11-19 same-name sweep: a thing made under the
                                    # name since is neither inside nor on its way, INFERRED)
        self.log = []               # (sim seconds, passenger name, building name, script)
        self.ejecting = {}          # host serial -> [the spot, seconds between, reach, next out at]: by the thing, as
                                    # boxes (B5 review g #1: a thing made under its name since neither drops nor takes
                                    # the job)
        self.flying = []            # [lands at, passenger body, the spot]
        self.leaving = []           # emptied hosts whose eject runs them off (RunOffMapWhenDone): L5's flee_due's

    def _box(self, b):
        """b's contain module a script may put a unit into: a building's garrison, else a TransportContain."""
        if b is None:
            return None
        return ('STRUCTURE' in b.kinds and contain(b)) or contain(b, TRANSPORT)

    def spec(self, b):
        """A building's garrison (what the AI and the walk-in look at): its module's rules, None without one."""
        m = contain(b) if b is not None and 'STRUCTURE' in b.kinds else None
        return m.rules() if m is not None else None

    def box(self, b):
        """Anything a script may put a unit into: a building's garrison, else a TransportContain (its rules)."""
        m = self._box(b)
        return m.rules() if m is not None else None

    def held(self, g):
        """The passengers of the building or transport g (the thing, not its name), in the order they came in."""
        m = self.boxes.get(getattr(g, 'serial', None)) if g is not None else None    # unbuilt: no box
        return m.passengers() if m is not None else []

    def home(self, g):
        """The owner the garrisoned building g goes back to when its last passenger is out (the owner it had before
        its first), None when it holds none or is a transport (which keeps its owner): put keeps it with the first
        passenger, out gives it back with the last."""
        m = self.boxes.get(getattr(g, 'serial', None)) if g is not None else None
        return m.home()[0] if m is not None and m.home() else None

    def set_home(self, g, owner):
        """The garrisoned building g, holding passengers, to go back to `owner` when emptied (a placed file's, S 11d:
        the owner before its first passenger); False when g holds none or is a transport (nothing kept)."""
        m = self.boxes.get(getattr(g, 'serial', None)) if g is not None else None
        if m is None or not m.home():
            return False
        m.give_home()
        m.keep_home(owner)
        return True

    # ---- who
    def fits(self, u, sp):
        """The PassengerFilter."""
        if u.template.lower() in sp['exclude'] or sp['unkinds'] & set(u.kinds):
            return False
        if not sp['kinds']:
            return True
        return sp['kinds'] <= set(u.kinds) if sp['rule'] == 'ALL' else bool(sp['kinds'] & set(u.kinds))

    def clears(self, u, sp):
        return bool(sp['clearing']) and sp['clearing'] <= set(u.status) | u.script_status

    def may(self, u, g):
        """u may go into g by the filter and the relation (not the room: the AI's pass does not look at it, aibdpre)."""
        world = self.world
        sp = self.box(g) if g is not None and g.alive else None
        if sp is None or u.serial in self.where or not self.fits(u, sp):
            return False
        if self.clears(u, sp):
            return True
        rel = world.relation(u.owner, g.owner)
        if rel == 'ALLIES':
            return (sp['own'] and u.owner == g.owner) or sp['allow']['ALLIES']
        return sp['allow'].get(rel, False)

    def places(self, u, own_defenses):
        """The buildings u could be sent into, in the world's order (world.living: made first, first): own_defenses ->
        u's player's base defenses (FS_BASE_DEFENSE, INFERRED), else the other garrisons (aibd0: with EnterGarrisons on
        by default nobody went into the own turrets -- they are not on that list)."""
        world = self.world
        out = []
        for g in world.living():
            if self.spec(g) is None:
                continue
            d = 'FS_BASE_DEFENSE' in g.kinds
            if (d and own_defenses and g.owner == u.owner or not d and not own_defenses) and self.may(u, g):
                out.append(g)
        return out

    def send(self, u, g):
        if u.alive and g.alive:
            self.going[u.serial] = (u, g)
            if u.goal is not None:
                u.aiupdate.command('goal')
            self.move(u, (g.x, g.y), False)
            return True
        return False                        # one of them dead: not sent (the port answers so: review 11-19 k #4)

    def busy(self, u):
        return u.serial in self.going or u.serial in self.where

    def room(self, t, u):
        """The free slots of t's TransportContain if its PassengerFilter takes u, else 0 (also for t without one)."""
        m = contain(t, ('TransportContain',))
        return m.rules()['max'] - len(self.held(t)) if m is not None and self.fits(u, m.rules()) else 0

    # ---- in and out
    def secondary(self, g):
        """E174: one contained secondary grants matching explicit-template upgrades.

        Bench engine_secondon_e/off_e:a measures AlliedEngineer in a multigunner
        turret, then its exit. Immediate notification is INFERRED; weapon/visual
        dispatch, SelfValidation, kind filters and multiple secondaries remain gaps.
        Keep upgrades that were already present before the listener granted them.
        """
        world, peers = self.world, self.peers
        box = self.boxes.get(g.serial)
        if box is None:
            return
        for up in box.granted():
            peers._upgrade(g, up, False)
        box.set_granted(())
        held = box.passengers()
        if len(held) != 1:
            return

        def read(xml):
            text = re.sub(r'<!--.*?-->', '', simunits._with_includes(xml or ''), flags=re.S)
            modules = list(simunits._blocks(text, 'SecondaryObjectListenerModule'))
            if not modules:
                return None
            upgrades = set()
            for head, inner in modules:
                if simunits._attr(head, 'Flags') != 'NOTIFY_WEAPON_SET_UPDATE' or '<SelfValidation' in inner:
                    continue
                for _, effect in simunits._blocks(inner, 'ObjectEffectTuple'):
                    filt = next(simunits._blocks(effect, 'ObjectFilter'), None)
                    if not filt or dict(re.findall(r'(\w+)="([^"]*)"', filt[0])) != {'Rule': 'NONE'}:
                        continue
                    names = re.findall(r'<IncludeThing>\s*([^<]+?)\s*</IncludeThing>', filt[1])
                    # Only the explicit allowlist form; do not guess mixed filters.
                    rest = re.sub(r'<IncludeThing>.*?</IncludeThing>', '', filt[1], flags=re.S).strip()
                    if rest or held[0].template.lower() not in {n.lower() for n in names}:
                        continue
                    upgrades.update(re.findall(r'<UpgradeSelf>\s*([^<]+?)\s*</UpgradeSelf>', effect))
            return upgrades

        upgrades = simunits._chain(g.template, world.own, read) or set()
        added = upgrades - g.upgrades
        for up in added:
            peers._upgrade(g, up, True)
        if added:
            box.set_granted(added)

    def put(self, u, g, script=False):
        """u into g now; True when it is inside. script: the script's ..._INSTANTLY (no relation, no room)."""
        world, peers = self.world, self.peers
        sp = self.box(g) if g is not None and g.alive else None     # walked in: a transport asks the room too
        if sp is None or u is None or not u.alive or u is g or u.serial in self.where or not self.fits(u, sp):
            return False
        box = self.boxes.setdefault(g.serial, self._box(g))
        held = box.passengers()
        clears = self.clears(u, sp)
        if not script and not clears and (not self.may(u, g) or len(held) >= sp['max']):
            return False
        if clears:                      # the contest: the first of another team, not allied, and the newcomer, out
            for p in held:
                if p.team != u.team and world.relation(p.owner, u.owner) != 'ALLIES':
                    self.out(p)
                    world.note('驻军', f'{world.label(u)} 把 {world.label(p)} 挤出 {world.label(g)}，自己也没进去')
                    return False
        house = sp['tag'] in TAGS                       # a transport keeps its owner
        if not held and house:
            box.keep_home(g.owner)
        bits = (sp['status'] | INSIDE_STATUS) - u.script_status
        box.let_in(u, bits)
        self.where[u.serial] = g
        self.going.pop(u.serial, None)
        self.log.append((world.t, u.name, g.name, script))
        self._set_down(u, g.x, g.y)
        u.script_status |= bits
        if house:
            g.owner = held[0].owner
        self.secondary(g)
        peers.modify(u)
        world.note('驻军', f'{world.label(u)} 进 {world.label(g)}')
        world.change()
        return True

    def _set_down(self, u, x, y):
        """u put at (x, y) with no way left (its Locomotor's) and no goal (its AIUpdate's: dropped alone)."""
        u.x, u.y = x, y
        locomotor.write(None, u, path=[])
        if u.goal is not None:
            u.aiupdate.command('goal')

    def out(self, u):
        """u out of the building it is in (where the building stands, INFERRED)."""
        world, peers = self.world, self.peers
        g = self.where.pop(u.serial, None) if u is not None else None
        if g is None:
            return False
        box = self.boxes.get(g.serial)
        u.script_status -= box.let_out(u) if box is not None else frozenset()
        held = box.passengers() if box is not None else []
        u.x, u.y = g.x, g.y
        if u.alive:
            peers.modify(u)
        if held:
            g.owner = held[0].owner
        elif box is not None and box.home():
            g.owner = box.give_home()
        self.secondary(g)
        world.change()
        return True

    def empty(self, g):
        for u in list(self.held(g)):
            self.out(u)

    def died(self, g, delete=False):
        """Sim.destroy / delete: the building is gone. Killed: KillPassengersOnDeath kills them, else they come out
        alive; deleted: they go with it."""
        held = list(self.held(g))
        if not held:
            return
        sp = self.box(g) or {}
        peers = self.peers
        self.ejecting.pop(g.serial, None)
        for u in held:
            self.out(u)
            if u.alive and (delete or sp.get('kill')):
                (peers.delete if delete else peers.destroy)(u, '随楼删掉' if delete else '楼毁乘员同死')
        self.boxes.pop(g.serial, None)

    def eject(self, g, command, where, power=None):
        """The button `command` pressed on g at the spot `where` (or the power itself fired: an OCL's
        FIRE_SPECIAL_POWER): True when an EjectPassengersSpecialAbilityUpdate of g serves its power (then the
        passengers go out one by one in due()). StartAbilityRange 0 with a spot away: it goes there first, out on
        arrival (engine_acts_drop air: the bomber drop's load rides its bombers from the store to the spot)."""
        world, peers = self.world, self.peers
        power = power or simunits.command_power(command, world.own)
        found = []

        def walk(xml):
            for head, _ in simunits._blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S),
                                            'EjectPassengersSpecialAbilityUpdate'):
                if power and simunits._attr(head, 'SpecialPowerTemplate') == power:
                    found.append(head)
        try:
            simunits._chain(g.template, world.own, walk)
        except (OSError, ValueError):
            pass
        if not found or g is None or not g.alive:
            return False
        h = found[0]
        per = simunits._secs(simunits._attr(h, 'TimePerPassenger') or '0.5s')
        reach = simunits._num(simunits._attr(h, 'StartAbilityRange'), 0.0) or \
            (ARRIVE if math.hypot(where[0] - g.x, where[1] - g.y) > ARRIVE else 0.0)
        self.ejecting[g.serial] = [where, per, reach, None, simunits._attr(h, 'RunOffMapWhenDone') == 'true']
        if reach and math.hypot(where[0] - g.x, where[1] - g.y) > reach:
            peers.send(g, where)                     # INFERRED: drives in, then throws
        world.note('驻军', f'{world.label(g)} 往外弹乘员')
        return True

    def run_off(self):
        """The living emptied hosts to run off (an eject's RunOffMapWhenDone), handed over once."""
        out, self.leaving = [g for g in self.leaving if g.alive], []
        return out

    def evacuate(self, g):
        """An EVACUATE button (LogicCommand Type EVACUATE: the Twinblade's): every passenger out where g is, together,
        EVACUATE_DELAY after the press (engine_acts_btn EV: all three in a second after the press, all out the next;
        INFERRED: the landing's time, 1-2 s, taken as 1.5). False when g carries nobody."""
        world = self.world
        if g is None or not g.alive or not [u for u in self.held(g) if u.alive]:
            return False
        # only an aircraft lands first: the Sudden transport's DisguisedEvacuate and a civilian building's evacuate
        # had all out within a second of the press (engine_acts_tgl DE / CV, round 223)
        delay = EVACUATE_DELAY if 'AIRCRAFT' in g.kinds else 0.0
        self.ejecting[g.serial] = [(g.x, g.y), 0.0, 0.0, world.t + delay]
        world.note('驻军', f'{world.label(g)} 落地放下乘员')
        return True

    def _throw(self):
        world, peers = self.world, self.peers
        for serial, job in list(self.ejecting.items()):
            box = self.boxes.get(serial)                # the host itself, by its serial (never its name: g #1)
            g = box.thing if box is not None else None
            held = [u for u in (box.passengers() if box else ()) if u.alive]
            where, per, reach, at, *off = job
            if g is None or not g.alive or not held:
                del self.ejecting[serial]
                if off and off[0] and g is not None and g.alive:
                    self.leaving.append(g)              # RunOffMapWhenDone: its RunOffMapBehavior takes it off
                continue
            if at is None:
                if reach and math.hypot(where[0] - g.x, where[1] - g.y) > reach:
                    continue
                at = job[3] = world.t
            if world.t + 1e-9 >= at:
                u = held[0]
                self.out(u)
                self.flying.append([world.t + EJECT_FLIGHT, u, where])
                job[3] = at + per
        for f in list(self.flying):
            if world.t + 1e-9 >= f[0]:
                self.flying.remove(f)
                u = f[1]
                if u.alive:
                    self._set_down(u, f[2][0], f[2][1])
                    peers.modify(u)
                    world.change()

    def due(self):
        """Once a frame: the ones sent in that have got there; a building at or under its REALLYDAMAGED line empties;
        the dead inside are let go of."""
        world = self.world
        for key, (u, g) in list(self.going.items()):
            if not u.alive or not g.alive or world.bodies.get(u.name) is not u:     # dead, or out of the world
                del self.going[key]
                continue
            sh = world.blocks(g)
            r = (sh[2] if sh and len(sh) == 3 else 40.0) + ENTER_REACH
            d = math.hypot(g.x - u.x, g.y - u.y)
            if d > r and (u.path or d > 2 * r):
                if not u.path and u.goal is None:
                    self.move(u, (g.x, g.y), False)          # stopped short (a fight): on its way again
                continue
            del self.going[key]
            self.put(u, g)
        for box in list(self.boxes.values()):
            g, held = box.thing, box.passengers()       # the host itself (a thing made under its name since: not it)
            for u in [u for u in held if not u.alive]:
                self.out(u)
            if not held:
                continue
            if not g.alive:
                self.died(g, g.deleted)
                continue
            for u in held:                              # riding: where the transport is
                u.x, u.y = g.x, g.y
            self.hurt(g)
        self._throw()

    def hurt(self, g):
        """At or under the REALLYDAMAGED line (and not GARRISONABLE_UNTIL_DESTROYED): everyone out. A script's damage
        calls it at once; due() catches the fight's hits the frame after (INFERRED: the game's is in the damage)."""
        world = self.world
        sp = self.spec(g) if self.held(g) else None
        if sp and g.alive and g.max_hp and g.hp > 0 and 100.0 * g.hp <= g.max_hp * really(g.template, world.own) + 1e-9 \
                and 'GARRISONABLE_UNTIL_DESTROYED' not in g.kinds:
            world.note('驻军', f'{world.label(g)} 残血，乘员全出来')
            self.empty(g)


def ocl_transports(ocl, own=None):
    """The OCL's FIRE_SPECIAL_POWER nuggets (the campaign bomber drop's: transports made carrying their InitialPayload
    and casting their eject): [(template, dx, dy, the power fired)], [] for any other list. Looked for in the
    mission's texts and retail's ObjectCreationLists.xml (_ocl), then in any retail file (the drop's list is kept in
    the file of the bomber it makes, which the SageXML index does not name)."""
    got = simunits._ocl(ocl, own) or _ocl_anywhere(ocl)
    out = []
    for ch, cb in re.findall(r'<CreateObject\b(\s[^>]*)>(.*?</CreateObject>)\s*</CreateObject>', got[1] if got else '',
                             re.S):
        made, off = re.search(r'<CreateObject>\s*([^<\s]+)', cb), re.search(r'<Offset\b([^>]*)', cb)
        if made and 'FIRE_SPECIAL_POWER' in (simunits._attr(ch, 'Options') or ''):
            out.append((made.group(1), simunits._num(simunits._attr(off.group(1), 'x') if off else 0),
                        simunits._num(simunits._attr(off.group(1), 'y') if off else 0),
                        simunits._attr(ch, 'FireSpecialPowerTemplate')))
    return out


def _ocl_anywhere(ocl):
    if ('ocl anywhere', ocl) not in simunits._reads:
        simunits.retail_xml('')
        tag = f'id="{ocl}"'
        simunits._reads['ocl anywhere', ocl] = next(
            ((h, b) for p in simunits._retail_files.values() if tag in simunits._text(p)
             for h, b in simunits._blocks(re.sub(r'<!--.*?-->', '', simunits._text(p), flags=re.S),
                                           'ObjectCreationList')
             if simunits._attr(h, 'id') == ocl), None)
    return simunits._reads['ocl anywhere', ocl]


def initial_payload(template, own=None):
    """Its TransportContain's InitialPayload: [(template, count)], [] without one."""
    def read(xml):
        got = [(simunits._attr(h, 'Name'), int(simunits._num(simunits._attr(h, 'Count'), 1))) for _, tb in
               simunits._blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'TransportContain')
               for h, _ in simunits._blocks(tb, 'InitialPayload')]
        return got or None
    return simunits._chain(template, own, read) or []
