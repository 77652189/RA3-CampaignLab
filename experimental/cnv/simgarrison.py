"""Garrisons in the simulator: GarrisonContain / ContestableGarrisonContain (sim.Sim.garrison; simai's AI walks its men
in through the same object). The rules are the engine model's (RA3-EngineModel ra3model/objects/contain.py, read in
RA3 1.13), held to the bench (checks/engine_garrison.py in / hp, bench 11-05; docs/engine/garrison.md):

  who          the PassengerFilter (Include kinds by its Rule, ExcludeThing templates) -- kept for every entry; then the
               relation of the unit to the building (sim.relation: no owner = NEUTRAL): AllowEnemiesInside /
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
  out          NAMED_EXIT_BUILDING (the unit), a sale (INFERRED, Generals' onSelling); REALLYDAMAGED -- the health at
               or under ActiveBody's MaxHealthReallyDamagedPercentage (default 33.333333 %) without KindOf
               GARRISONABLE_UNTIL_DESTROYED -- orders all out (garrison.md 3: out at 13 %)
  the end      the building killed (a hit or a script's kill, garrison.md 4): KillPassengersOnDeath kills them (the
               Multigunner turret), else they come out alive (DamagePercentToUnits: none of the retail houses writes
               it, not modelled); a deleted building takes them with it (INFERRED, Generals' onDelete)
Not modelled: fire from inside (the passengers keep their own weapons; a turret's weapon set by its passenger), the
garrison aura, clearing weapons, the exit point (they come out where the building stands), EjectSpeed."""
import math
import re

import simunits

TAGS = ('GarrisonContain', 'ContestableGarrisonContain')
REALLY_DAMAGED = 33.333333      # ActiveBody.xsd MaxHealthReallyDamagedPercentage's default (percent)
ENTER_REACH = 20.0              # INFERRED: in at the building's side (its round + this; as Sim.capture_due's)
INSIDE_STATUS = frozenset({'IMMOBILE', 'UNATTACKABLE'})     # INFERRED: a passenger neither walks nor is shot at
                                                            # by itself (the building takes the hits)
CIV = 'PlyrCivilian'


def _yes(v, default):
    return default if v is None else v.strip().lower() == 'true'


_memo = {}


def spec(template, own=None):
    """The template's garrison, None without one: {'tag', 'max', 'allow' {ENEMIES, NEUTRAL, ALLIES}, 'own', 'kill',
    'status', 'clearing', 'rule', 'kinds', 'exclude', 'really'}. A module's attributes are merged down the inheritFrom
    chain by its id (BaseCivilianStructureMedium writes only ContainMax over BaseCivilianStructure's); the
    PassengerFilter is the nearest one written."""
    key = (template, (own or {}).get(template))
    if key in _memo:
        return _memo[key]
    found, bodies = [], []

    def walk(xml):
        text = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        for tag in TAGS:
            for head, inner in simunits._blocks(text, tag):
                found.append((tag, head, inner))
        for head, _ in simunits._blocks(text, 'ActiveBody'):
            bodies.append(head)
        return None
    try:
        simunits._chain(template, own, walk)
    except (OSError, ValueError):
        found = []
    if not found:
        _memo[key] = None
        return None
    tag = found[0][0]
    attrs, flt = {}, None
    for t, head, inner in reversed(found):              # farthest first: the nearer writes over it
        if t != tag:
            continue
        attrs.update(re.findall(r'(\w+)="([^"]*)"', head))
    for t, head, inner in found:
        f = next(simunits._blocks(inner, 'PassengerFilter'), None) if t == tag else None
        if f is not None:
            flt = f
            break
    really = next((simunits._attr(h, 'MaxHealthReallyDamagedPercentage') for h in bodies
                   if simunits._attr(h, 'MaxHealthReallyDamagedPercentage')), None)
    a = {k: simunits.expand(v) for k, v in attrs.items()}
    fh, fi = flt if flt is not None else ('', '')
    out = {
        'tag': tag,
        'max': int(float(a.get('ContainMax') or 0)),
        'allow': {'ENEMIES': _yes(a.get('AllowEnemiesInside'), True), 'NEUTRAL': _yes(a.get('AllowNeutralInside'), True),
                  'ALLIES': _yes(a.get('AllowAlliesInside'), True)},
        'own': _yes(a.get('AllowOwnPlayerInsideOverride'), False),
        'kill': _yes(a.get('KillPassengersOnDeath'), False),
        'status': frozenset(a.get('ObjectStatusOfContained', '').split()),
        'clearing': frozenset(a.get('RequiredClearingObjectStatus', '').split())
        if tag == 'ContestableGarrisonContain' else frozenset(),
        'rule': (simunits._attr(fh, 'Rule') or 'ANY').upper(),
        'kinds': frozenset((simunits._attr(fh, 'Include') or '').split()),
        'unkinds': frozenset((simunits._attr(fh, 'Exclude') or '').split()),
        'exclude': frozenset(t.strip().lower() for t in re.findall(r'<ExcludeThing>([^<]*)</ExcludeThing>', fi)),
        'really': float(really.rstrip('%')) if really else REALLY_DAMAGED,
    }
    _memo[key] = out
    return out


class Garrisons:
    def __init__(self, sim_):
        self.sim = sim_
        self.inside = {}            # building name -> [passenger bodies], in the order they came in
        self.where = {}             # passenger name -> building body
        self.added = {}             # passenger name -> the status bits the garrison gave it
        self.going = {}             # body name -> building body it was sent into (the AI's walk)
        self.home = {}              # building name -> its owner before the first passenger
        self.log = []               # (sim seconds, passenger name, building name, script)

    def spec(self, b):
        return spec(b.template, self.sim.own) if b is not None and 'STRUCTURE' in b.kinds else None

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
        sp = self.spec(g) if g is not None and g.alive else None
        if sp is None or u.name in self.where or not self.fits(u, sp):
            return False
        if self.clears(u, sp):
            return True
        rel = self.sim.relation(u.owner, g.owner)
        if rel == 'ALLIES':
            return (sp['own'] and u.owner == g.owner) or sp['allow']['ALLIES']
        return sp['allow'].get(rel, False)

    def places(self, u, own_defenses):
        """The buildings u could be sent into, in the world's order (sim.living: made first, first): own_defenses ->
        u's player's base defenses (FS_BASE_DEFENSE, INFERRED), else the other garrisons (aibd0: with EnterGarrisons on
        by default nobody went into the own turrets -- they are not on that list)."""
        out = []
        for g in self.sim.living():
            if self.spec(g) is None:
                continue
            d = 'FS_BASE_DEFENSE' in g.kinds
            if (d and own_defenses and g.owner == u.owner or not d and not own_defenses) and self.may(u, g):
                out.append(g)
        return out

    def send(self, u, g):
        if u.alive and g.alive:
            self.going[u.name] = g
            u.goal = None
            self.sim.order_move(u, (g.x, g.y), False)

    def busy(self, u):
        return u.name in self.going or u.name in self.where

    # ---- in and out
    def put(self, u, g, script=False):
        """u into g now; True when it is inside. script: the script's ..._INSTANTLY (no relation, no room)."""
        s = self.sim
        sp = self.spec(g) if g is not None and g.alive else None
        if sp is None or u is None or not u.alive or u is g or u.name in self.where or not self.fits(u, sp):
            return False
        held = self.inside.setdefault(g.name, [])
        clears = self.clears(u, sp)
        if not script and not clears and (not self.may(u, g) or len(held) >= sp['max']):
            return False
        if clears:                      # the contest: the first of another team, not allied, and the newcomer, out
            for p in held:
                if p.team != u.team and s.relation(p.owner, u.owner) != 'ALLIES':
                    self.out(p)
                    s.note('驻军', f'{s.label(u)} 把 {s.label(p)} 挤出 {s.label(g)}，自己也没进去')
                    return False
        if not held:
            self.home.setdefault(g.name, g.owner)
        held.append(u)
        self.where[u.name] = g
        self.going.pop(u.name, None)
        self.added[u.name] = (sp['status'] | INSIDE_STATUS) - u.script_status
        self.log.append((s.t, u.name, g.name, script))
        u.x, u.y, u.path, u.goal = g.x, g.y, [], None
        u.script_status |= self.added[u.name]
        g.owner = held[0].owner
        s.modify(u)
        s.note('驻军', f'{s.label(u)} 进 {s.label(g)}')
        s.change()
        return True

    def out(self, u):
        """u out of the building it is in (where the building stands, INFERRED)."""
        g = self.where.pop(u.name, None) if u is not None else None
        if g is None:
            return False
        held = self.inside.get(g.name, [])
        if u in held:
            held.remove(u)
        u.script_status -= self.added.pop(u.name, frozenset())
        u.x, u.y = g.x, g.y
        if u.alive:
            self.sim.modify(u)
        if held:
            g.owner = held[0].owner
        elif g.name in self.home:
            g.owner = self.home.pop(g.name)
        self.sim.change()
        return True

    def empty(self, g):
        for u in list(self.inside.get(g.name, [])):
            self.out(u)

    def died(self, g, delete=False):
        """Sim.destroy: the building is gone. Killed: KillPassengersOnDeath kills them, else they come out alive;
        deleted: they go with it."""
        held = list(self.inside.get(g.name, []))
        if not held:
            return
        sp = self.spec(g) or {}
        s = self.sim
        for u in held:
            self.out(u)
            if u.alive and (delete or sp.get('kill')):
                s.destroy(u, '随楼删掉' if delete else '楼毁乘员同死', delete=delete)
        self.inside.pop(g.name, None)

    def due(self):
        """Once a frame: the ones sent in that have got there; a building at or under its REALLYDAMAGED line empties;
        the dead inside are let go of."""
        s = self.sim
        for name, g in list(self.going.items()):
            u = s.bodies.get(name)
            if u is None or not u.alive or not g.alive:
                del self.going[name]
                continue
            sh = s.blocks(g)
            r = (sh[2] if sh and len(sh) == 3 else 40.0) + ENTER_REACH
            d = math.hypot(g.x - u.x, g.y - u.y)
            if d > r and (u.path or d > 2 * r):
                if not u.path and u.goal is None:
                    s.order_move(u, (g.x, g.y), False)          # stopped short (a fight): on its way again
                continue
            del self.going[name]
            self.put(u, g)
        for gname, held in list(self.inside.items()):
            g = s.bodies.get(gname)
            for u in [u for u in held if not u.alive]:
                self.out(u)
            if g is None or not held:
                continue
            if not g.alive:
                self.died(g, g.deleted)
                continue
            self.hurt(g)

    def hurt(self, g):
        """At or under the REALLYDAMAGED line (and not GARRISONABLE_UNTIL_DESTROYED): everyone out. A script's damage
        calls it at once; due() catches the fight's hits the frame after (INFERRED: the game's is in the damage)."""
        sp = self.spec(g) if self.inside.get(g.name) else None
        if sp and g.alive and g.max_hp and g.hp > 0 and 100.0 * g.hp <= g.max_hp * sp['really'] + 1e-9 \
                and 'GARRISONABLE_UNTIL_DESTROYED' not in g.kinds:
            self.sim.note('驻军', f'{self.sim.label(g)} 残血，乘员全出来')
            self.empty(g)
