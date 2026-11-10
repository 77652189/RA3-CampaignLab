r"""The skirmish AI on the plan simulator: the engine line's layer-4 model (RA3-EngineModel ra3model/ai, AIPlayer and
its blocks) plays an enemy of sim.Sim -- it builds its base, makes units, puts them in teams and sends them out.

This file only calls the simulator (Sim.advance, Sim.factories / order_build / queues, Sim.add, Sim.order_move,
Sim.money, Sim.ai); it changes none of sim.py's rules (sim.py / simunits.py are the engine line A's). Where the model
is not on this computer nothing here runs: available() is False and the tests skip (as simproxy).

  python -I -X utf8 experimental/cnv/simai.py [build] [--until <seconds>] [--check <check>]

When a player is handed to the AI (the mission's UNIT_AI_TRANSFER_ALL / SKIRMISH_AI_MAKE_BASE: Sim.ai, the second it
ran) an AIPlayer is made for it with the side's aiPersonality (mission.sides) and told 'make base' that frame. Then
every frame (the simulator moves in DT ticks; the AI is ticked for each frame of a tick right after it):
  structures  the simulator builds none (a yard's CommandSet has no UNIT_BUILD), so this file is the yard: one queue a
              yard, the float32 progress of Sim.produce_due paid frame by frame from Sim.money, owned PLACE_DELAY (1)
              frame after full, the next started the frame after (bench aiopen f1-f3); put down on rings round the
              yard (INFERRED: the first free spot, from the side away from the map's middle). A refinery brings its
              miner its UnpackTime later (bench aiopen: 667 = refinery + 60).
  units       Sim.order_build, one at a time a factory: the next is queued once the last has left the door (bench
              aiopen: 161 frames a Riptide = 151 + door 10), none before the factory has unpacked (UnpackTime).
  offers      the unit builder's candidates (Sim.offers) with their state (0 an idle factory, 1 all busy), standard
              combat flag and cost; it orders for no team, beside the opening, on the AI's PRODUCTION account.
  money       the player's money now (Sim.money) = ai.money: an account spends its Deposits + its budget share of it.
  teams      ai.units = the AI's own movers (not HARVESTER, not IGNORES_SELECT_ALL) as stable Unit wrappers;
              team_point = the closest enemy structure to the AI's yard.
  states      ctx: the mission's flags (ScriptedFlagHeuristic), 'has' (its templates; 'has enemy' / 'has ally' /
              'has neutral' by owner for ObjectOfTypeExists' Relationship), 'building' (the kinds queued),
              'enemy nearby' (enemy value within the distance of its yard), 'path to target' (PathToTargetHeuristic:
              the last enemy with a structure, both base objects by states.base_object, spots by states.spot on
              the simulator's grids, a route for the test template's surface; cached PATH_EVERY), 'harvesters',
              'money', 'opponent funds' (the first enemy's), 'income' (each side's harvesters while a refinery
              stands -- INFERRED), 'beacons' (none), 'power advantage' (tactics'
              rule over the whole armies -- INFERRED); the other strategic facts stay unmodelled (states.strategic).
  blocks      A's TargetsBlock + TacticsBlock (orders: 'move' / 'attack-move' -> Sim.order_move, 'enter' -> Garrisons;
              houses / defenses = Brain.garrisons, full ones listed too), DefenseBlock (one
              MAIN_BASE round the first yard; hurt = the body's hp fell; aesthetics = a circle round the point),
              MicroBlock (unit powers from the CommandSet; a use is only recorded: the simulator gives the AI's units
              no abilities), PlayerPowers (none yet: the simulator has no superweapon charge). The AI sees the whole
              map (INFERRED; the view's things are every living body that is not scenery).

HOOKS (what this file would rather have from sim.py; for A through the coordinator, not urgent):
  1. a per-frame callback inside Sim.step: here the AI is ticked after a whole DT tick, so a unit queued once the last
     left the door starts up to 7 frames late (Riptides 165 apart, bench 161), and the yard is paid after the tick's
     unit production;
  2. a structure queue (yard production) and a placement rule in Sim, so a human player's yard works the same;
  3. Sim.produce_due starts a factory's next job the frame after the last is full; the AI bench (aiopen) shows the
     next starting when the last has left the door -- which holds for a human's queue is not measured;
  4. a factory's UnpackTime in Sim (no unit before it has unpacked);
  5. unit abilities and superweapon charge for an AI player (micro / PlayerPowers only record what they would fire);
  6. simunits' table misses the second GameObject of a file (AlliedAntiInfantryVehicle_Ground, the Riptide the war
     factory makes: speed 0, no KindOf, no weapons); fill() patches the AI's own such units from the model's library.
  8. garrisons in Sim: Garrisons (below) walks the AI's men into houses / turrets and parks them there, wraps Sim.act
     for NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY, and sim.py does not count PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS
     (ENCLOSED), so the tests read Garrisons.log; no fire from inside.
"""
import argparse
import importlib
import math
import os
import random
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import labpaths  # noqa: E402
import sim  # noqa: E402
import simproxy  # noqa: E402
import simunits  # noqa: E402

FPS = 15
PLACE_DELAY = 1                     # bench aiopen f1-f3 (opening.PLACE_DELAY): owned 1 frame after the head is full
RING = (260.0, 400.0, 540.0, 680.0)     # INFERRED: the rings a yard puts its structures on
GAP = 20.0                          # INFERRED: room left between two structures' rounds
DIFFICULTY = {'easy': 'EASY', 'normal': 'MEDIUM', 'hard': 'HARD', 'brutal': 'BRUTAL'}
BLOCKS = ('targets', 'defense', 'micro', 'specials')
PATH_EVERY = 10 * FPS               # INFERRED: a PathToTargetHeuristic answer is kept 10 s (the engine asks every
                                    # evaluation; here a route costs a whole-grid search)
SCRIPT_SCOPE = 'the list owner'     # the scope of a bare flag name (the script list's player; INFERRED: its name)
MODULES = ('data','player', 'opening', 'states', 'teams', 'targets', 'tactics', 'defense', 'micro', 'specials')
_AI = {}


def model():
    """The engine model's ra3model.ai modules as a dict, or None (simproxy._package loads the package by file)."""
    if 'got' not in _AI:
        root = labpaths.ENGINE_MODEL
        got = None
        if os.path.isfile(os.path.join(root, 'ra3model', 'ai', 'player.py')):
            try:
                simproxy._package(os.path.join(root, 'ra3model'))
                got = {k: importlib.import_module(f'ra3model.ai.{k}') for k in MODULES}
                got['xmldata'] = importlib.import_module('ra3model.objects.xmldata')
            except ImportError:
                got = None
        _AI['got'] = got
    return _AI['got']


def available():
    return model() is not None


def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]


def side_index(side):
    try:
        return int(side.lstrip('ps'))
    except ValueError:
        return 0


GARRISON_TAGS = ('GarrisonContain', 'ContestableGarrisonContain')
ENTER_REACH = 20.0          # INFERRED: in at the building's side (its round + this; as Sim.capture_due's CAPTURE_REACH)
INSIDE_STATUS = {'IMMOBILE', 'UNATTACKABLE'}    # INFERRED: a passenger neither walks nor is shot at by itself
                                                # (the building takes the hits); its own ObjectStatusOfContained too


class Garrisons:
    """Garrisons for the AI's teams (HOOKS 8): sim.py has none, so the TacticsBlock's EnterGarrisons /
    EnterBaseDefenses orders ('enter' a building) and the script's NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY are
    carried out here, on the retail GarrisonContain / ContestableGarrisonContain data (the model's library):
      who         PassengerFilter INFANTRY (every retail garrison); the relation of the unit to the building (no owner =
                  neutral): AllowEnemiesInside / AllowNeutralInside / AllowAlliesInside, own player with
                  AllowOwnPlayerInsideOverride (the engine model's objects/contain.py, l2 garrison)
      going in    the unit walks to the building; at its side (round + ENTER_REACH, or stopped within twice that) it is
                  in if fewer than ContainMax are; else it stays there, out (bench aibdpre: a full turret is walked up
                  to and not entered)
      inside      the body stays alive at the building's spot with its ObjectStatusOfContained (ENCLOSED ...: what the
                  checks count) + INSIDE_STATUS; a neutral building turns the first passenger's player's (garrison.md 2)
                  and back to its owner when empty
      the end     the building dies: KillPassengersOnDeath kills them (the Multigunner turret; bench aibdpre 'the
                  sitter with it'), else they come out where it stood
    Not modelled: fire from inside (a house's passengers keep their own weapons, CAN_ATTACK; a turret's weapon set by
    its passenger), DamagePercentToUnits, contesting, leaving by order."""

    def __init__(self, sim_, lib):
        self.sim, self.lib = sim_, lib
        self.inside = {}            # building name -> [passenger bodies]
        self.where = {}             # passenger name -> building body
        self.going = {}             # body name -> building body it was sent into
        self.home = {}              # building name -> its owner before the first passenger
        self.log = []               # (sim seconds, passenger name, building name, script)
        self._spec = {}

    def spec(self, template):
        """The template's garrison: {'max', 'allow', 'own', 'kill', 'status', 'kinds'} or None."""
        if template not in self._spec:
            tpl = self.lib.template(template)
            m = next((m for t in GARRISON_TAGS for m in (tpl.find(t) if tpl is not None else ())), None)
            if m is None:
                self._spec[template] = None
            else:
                a = m.attrs
                yes = lambda k, d: a.get(k, d).lower() == 'true'                         # noqa: E731
                f = next((c for c in m.children if c.tag == 'PassengerFilter'), None)
                self._spec[template] = {
                    'max': int(float(a.get('ContainMax', '0'))),
                    'allow': {'ENEMIES': yes('AllowEnemiesInside', 'true'), 'NEUTRAL': yes('AllowNeutralInside', 'true'),
                              'ALLIES': yes('AllowAlliesInside', 'true')},
                    'own': yes('AllowOwnPlayerInsideOverride', 'false'),
                    'kill': yes('KillPassengersOnDeath', 'false'),
                    'status': set(a.get('ObjectStatusOfContained', '').split()),
                    'kinds': set(f.attrs.get('Include', '').split()) if f is not None else set()}
        return self._spec[template]

    def may(self, u, g):
        """u may go into g by the filter and the relation (not the room: the AI's pass does not look at it, aibdpre)."""
        sp = self.spec(g.template) if g.alive and 'STRUCTURE' in g.kinds else None
        if sp is None or u.name in self.where or (sp['kinds'] and not sp['kinds'] & set(u.kinds)):
            return False
        if g.owner == sim.CIV:
            return sp['allow']['NEUTRAL']
        if self.sim.enemy(u.owner, g.owner):
            return sp['allow']['ENEMIES']
        return (sp['own'] and u.owner == g.owner) or sp['allow']['ALLIES']

    def places(self, u, own_defenses):
        """The buildings u could be sent into, in the world's order (sim.living: made first, first): own_defenses ->
        u's player's base defenses (category 0x2e: FS_BASE_DEFENSE, INFERRED), else the other garrisons (aibd0: with
        EnterGarrisons on by default nobody went into the own turrets -- they are not on that list)."""
        out = []
        for g in self.sim.living():
            if 'STRUCTURE' not in g.kinds or self.spec(g.template) is None:
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

    def put(self, u, g, script=False):
        """u in g now if it may and there is room (script: the script's ..._INSTANTLY skips the relation and the
        room, the filter kept; objects/contain.py)."""
        sp = self.spec(g.template) if g and g.alive else None
        if sp is None or not u or not u.alive or u.name in self.where:
            return False
        held = self.inside.setdefault(g.name, [])
        if not script and (not self.may(u, g) or len(held) >= sp['max']):
            return False
        if script and sp['kinds'] and not sp['kinds'] & set(u.kinds):
            return False
        if not held and g.owner == sim.CIV:
            self.home[g.name] = g.owner
            g.owner = u.owner
        held.append(u)
        self.where[u.name] = g
        self.log.append((self.sim.t, u.name, g.name, script))
        u.x, u.y, u.path, u.goal = g.x, g.y, [], None
        u.script_status |= sp['status'] | INSIDE_STATUS
        self.sim.modify(u)
        self.sim.note('AI', f'{self.sim.label(u)} 进 {self.sim.label(g)}')
        self.sim.change()
        return True

    def due(self):
        """Once a DT tick: the ones sent in that have got there; the buildings that died."""
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
            if g is not None and g.alive:
                continue
            sp = self.spec(g.template) if g is not None else None
            for u in held:
                self.where.pop(u.name, None)
                if not u.alive:
                    continue
                if sp and sp['kill']:
                    s.destroy(u, '楼毁乘员同死')
                else:
                    u.script_status -= (sp['status'] if sp else set()) | INSIDE_STATUS
                    s.modify(u)
            del self.inside[gname]
        for gname, held in self.inside.items():         # the dead inside (none shoots them: a script's kill)
            held[:] = [u for u in held if u.alive]
            g = s.bodies.get(gname)
            if not held and gname in self.home and g is not None:
                g.owner = self.home.pop(gname)
        for name in [n for n, g in self.where.items() if not (s.bodies.get(n) and s.bodies[n].alive)]:
            del self.where[name]


class Unit:
    """One of the AI's movers as teams.py wants it: template, kindof, surface, pos, team (TeamMaker writes it).
    One object a body for the whole run (teams test membership by identity)."""

    def __init__(self, body):
        self.body = body
        self.template = body.template
        self.kindof = set(body.kinds)
        self.surface = 'AIR' if 'AIRCRAFT' in body.kinds else 'AMPHIBIOUS' if 'AMPHIBIOUS' in body.kinds else \
            'WATER' if 'SHIP' in body.kinds else 'LAND'
        self.team = None

    @property
    def pos(self):
        return (self.body.x, self.body.y)

    @pos.setter
    def pos(self, p):                   # a block that "walks" a unit itself: the simulator moves it, not this
        pass

    def __repr__(self):
        return f'Unit({self.template} {self.body.name})'


class Brain:
    """One AI player of the simulator's: the AIPlayer and the world it is given (yard, factories, units, the view)."""

    def __init__(self, host, player, side, personality, frame):
        self.host, self.sim, self.player = host, host.sim, player
        m = host.mod
        self.ai = m['player'].AIPlayer(host.data, personality, DIFFICULTY.get(host.level, 'MEDIUM'),
                                       ctx={'path to target': self.path_to_target}, rng=random.Random(host.seed),
                                       index=side_index(side))
        self.paths = {}                 # (surface, template, condition) -> (frame asked, answer)
        self.path_rng = random.Random(host.seed)    # the spot's start angles (the engine: the logic random)
        self.ai.builder = self.build
        self.ai.units = self.units
        self.ai.team_point = self.team_point
        self.ai.offers = self.offers
        self.yard_q = {}                # yard name -> [job]
        self.yard_rest = {}             # yard name -> the last frame it starts nothing (the one after a put)
        self.unit_q = []                # [template] waiting for a free, unpacked factory that makes it
        self.made = {}                  # body name -> frame it came (structures: unpack; units: the trace)
        self.wrappers = {}              # body name -> Unit
        self.later = []                 # (frame, template, (x, y), team): a refinery's miner
        self.trace = []                 # (frame, 'own' | 'out', template): what came when
        self.woke = self.frame = frame
        self.ids, self.hp, self.hurt_at = {}, {}, {}     # body name -> Thing id; last hp; id -> frame last hurt
        self.seen_t = None              # the sim time the view was last built at
        self.fired = []                 # (frame, team key, unit, command): unit powers the micro wanted
        yards = self.yards()
        self.home = (yards[0].x, yards[0].y) if yards else (0.0, 0.0)
        tg = m['targets']
        foes = frozenset(p for p in self.sim.players.values() if p != player and self.sim.enemy(player, p))
        self.view = tg.View(player, [], enemies=foes, waypoints=self.sim.waypoints)   # Waypoint targets
        self.base = self.powers = None
        self.attach(host.blocks)
        self.ai.tell(m['player'].Command('make base'))

    # ---- A's blocks (targets, tactics, defence, micro; the player's superweapons beside them)
    def attach(self, which):
        h, m = self.host, self.host.mod
        tg, tc, df, mc = m['targets'], m['tactics'], m['defense'], m['micro']
        if 'targets' not in which:
            return
        self.tactics = tc.TacticsBlock(None, lambda ai, f: self.view, self.order, lambda ai: self.home,
                                       micro=h.data_of('tactics micro'), fight=self.fight,
                                       houses=lambda ai, u: self.garrisons(u, False),
                                       defenses=lambda ai, u: self.garrisons(u, True))
        self.targets = tg.TargetsBlock(h.data_of('targets'), self.active, lambda ai, f: self.view,
                                       lambda ai, st: self.home, home=self.home, base_of=self.base_of,
                                       held=self.tactics.held)
        self.tactics.targets = self.targets
        self.ai.blocks += [self.targets, self.tactics]
        # a slot's team is made once the slot has a target (l4_states.md 1/7); the teams tick before the blocks,
        # so they see the slots of the last think (INFERRED one-think lag)
        self.ai.teams.has_target = lambda ai, key, n: self.targets.slot_target(
            self.tactics.state_of(ai, key), n) is not None
        # a gathering team whose slot's target is gone ends (teams.TeamMaker._slots, 0x8c6d10 / 0x8c7020)
        self.ai.teams.target_of = lambda ai, key, n: self.targets.slot_target(self.tactics.state_of(ai, key), n)
        self.ai.teams.alive = lambda ai, i: i in self.targets.points or any(t.id == i for t in self.view.things)
        if 'defense' in which:
            self.base = df.Base(1, self.home, (), frozenset({'MAIN_BASE'}))
            self.defense = df.DefenseBlock(self.tactics, lambda ai, f: self.view, bases=lambda ai, f: [self.base],
                                           busy=self.busy, aesthetics=self.stand, radius=self.radius_of,
                                           attrs=h.data_of('tactic attrs'), rng=random.Random(h.seed),
                                           last_hurt=lambda ai, i: self.hurt_at.get(i))
            self.ai.blocks.append(self.defense)
        if 'micro' in which:
            self.micro = mc.MicroBlock(self.micro_team, fire=self.fire_unit, data=h.data_of('micro'),
                                       rng=random.Random(h.seed).uniform)      # MicroManager's rng(lo, hi)
            self.ai.blocks.append(self.micro)
        if 'specials' in which:
            self.powers = m['specials'].PlayerPowers([], DIFFICULTY.get(h.level, 'MEDIUM'))

    def active(self, ai, frame):
        """The states whose target slots are picked this think. INFERRED from 0x8c7020 (a slot with a busy team does
        not re-pick; targets.TargetsBlock keeps what a team holds through tactics.held): a state whose team runs
        with a target picks no more. Without it the AlliedScout state (MaxTargets 2, unique targets) took two more
        of the player's three structures every think while its dog walked to the third, and BalancedAttackGround
        had none to go for (work/re/simai.md round 43). A state holds one slot per copy (MaxTargets slots, round 44),
        so it picks while one of its slots has no busy team. Belongs in the targets block (A's); wired here meanwhile."""
        on = list(ai.states.on)
        busy = {}
        for r in self.tactics.runs.values():
            if r.phase != 'done' and r.target is not None:
                busy[r.team.state] = busy.get(r.team.state, 0) + 1
        return [c.target for c in ai.states.choices if on.count(c.key) > busy.get(c.key, 0)]

    def switches(self):
        """The mission's SKIRMISH_AI_* switches (sim.AI_SWITCHES, kept by Sim.act) told to the AI as they change
        (work/re l4_aiswitches.md): enemy priorities over the enemies now, repairs, rebuild with a snapshot of the
        own structures."""
        got = self.sim.ai_switches.get(self.player, {})
        seen = getattr(self, '_switched', {})
        Command = self.host.mod['player'].Command
        for name, v in got.items():
            if seen.get(name) == v:
                continue
            if name == 'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES':
                self.ai.tell(Command('enemy priorities', {'n': v, 'enemies': sorted(self.view.enemies)}))
            elif name == 'SKIRMISH_AI_USE_REPAIRS':
                self.ai.tell(Command('use repairs', {'on': v}))
            elif name == 'SKIRMISH_AI_USE_REBUILD_SYSTEM':
                own = [(b.template, b.x, b.y) for b in self.sim.living()
                       if b.owner == self.player and 'STRUCTURE' in b.kinds and not b.scenery]
                self.ai.tell(Command('use rebuild', {'on': v, 'structures': own}))
        self._switched = dict(got)

    def base_of(self, player):
        ys = [b for b in self.sim.living() if b.owner == player and 'STRUCTURE' in b.kinds and not b.scenery]
        y = next((b for b in ys if 'CONSTRUCTION_YARD' in b.kinds), ys[0] if ys else None)
        return (y.x, y.y) if y else None

    def base_object(self, player):
        """states.base_object over a player's living, unpacked structures: preferred = CONSTRUCTION_YARD, rank = cost
        (INFERRED: which template bit / value the engine reads is not known)."""
        st, now = self.host.mod['states'], self.sim.frame_now()
        ys = [b for b in self.sim.living() if b.owner == player and 'STRUCTURE' in b.kinds and not b.scenery
              and (getattr(b, 'unpack_end', None) or 0) <= now]
        return st.base_object(ys, lambda b: 'CONSTRUCTION_YARD' in b.kinds, lambda b: self.host.cost(b.template))

    def path_to_target(self, surface, template, cond):
        """ctx 'path to target' (read 0x8c56b0, l4_states.md 3): None when it cannot judge (no base of ours, no enemy
        with one); False when a spot is not found; True when the template has no locomotor (bench aiopath1 /
        aiopathr, checks/engine_aiopath.py: AlliedPowerPlant as the tester picks the PathExists="true" opening in
        either order -- the program read "no locomotor -> no way" is wrong or misread); else whether the simulator's
        grid of the template's surface joins the two spots. cond: the simulator knows only NORMAL (INFERRED: same)."""
        key = (surface, template, cond)
        got = self.paths.get(key)
        if got is not None and self.frame - got[0] < PATH_EVERY:
            return got[1]
        st, s = self.host.mod['states'], self.sim
        mine = self.base_object(self.player)
        foes = [p for p in s.players.values() if p != self.player and s.enemy(self.player, p)]
        them = st.target_player(foes, self.base_object)
        if mine is None or them is None:
            answer = None
        else:
            stats = simunits.stats(template, s.own) if template else {'speed': None}
            if not stats.get('speed'):
                answer = True                                    # bench aiopath1 / aiopathr: no locomotor -> a way
            else:
                grid = 'water' if surface == 'Water' else 'ground'   # read: cell type Water 7 / Land 0
                ok = lambda p: s.ground.open(grid, *p)           # noqa: E731
                theirs = self.base_object(them)
                a = st.spot((mine.x, mine.y), ok, self.path_rng)
                b = st.spot((theirs.x, theirs.y), ok, self.path_rng)
                answer = a is not None and b is not None and s.ground.route(stats['surface'], a, b) is not None
        self.paths[key] = (self.frame, answer)
        return answer

    def tid(self, b):
        if b.name not in self.ids:
            self.ids[b.name] = len(self.ids) + 1
        return self.ids[b.name]

    def body_of(self, tid):
        name = next((k for k, v in self.ids.items() if v == tid), None)
        return self.sim.bodies.get(name) if name else None

    def look(self, frame):
        """The view's things (every living body but scenery: the AI sees the whole map, INFERRED) and who got hurt.
        Rebuilt once a DT tick (bodies move and fight once a tick)."""
        s, tg = self.sim, self.host.mod['targets']
        if self.seen_t == s.t:
            return
        self.seen_t = s.t
        things = []
        for b in s.living():
            if b.scenery:
                continue
            i = self.tid(b)
            if b.hp < self.hp.get(b.name, b.hp):
                self.hurt_at[i] = frame
            self.hp[b.name] = b.hp
            owner = b.owner if b.owner != sim.CIV else ''
            things.append(tg.Thing(i, owner, b.template, frozenset(b.kinds), frozenset(b.status), b.x, b.y,
                                   water=b.surface == 'water', value=float(self.host.cost(b.template)),
                                   hits=simproxy._hits(b.weapons) if b.weapons else frozenset(),
                                   under_attack=frame - self.hurt_at.get(i, -10 ** 9) <= 2 * FPS,
                                   name=b.name))                    # script name (NamedObject)
        self.view.things = things
        if self.base is not None:
            self.base.buildings = tuple(t.id for t in things if t.owner == self.player and 'STRUCTURE' in t.kindof)

    def facts(self):
        """The ctx the strategic states read, from the world."""
        mine = [b for b in self.sim.living() if b.owner == self.player]
        building = set()
        for t in [j['template'] for q in self.yard_q.values() for j in q] + self.unit_q:
            building |= self.host.kinds(t)
        hx, hy = self.home

        def near(distance, min_value, things=()):
            v = sum(t.value for t in self.view.things if t.owner in self.view.enemies
                    and math.hypot(t.x - hx, t.y - hy) <= distance and (not things or t.template in things))
            return v > 0 and v >= min_value
        foes = sorted(self.view.enemies)
        out = {'flags': self.host.flags(self.player), 'has': {b.template for b in mine}, 'building': building,
               'enemy nearby': near,
               # ObjectOfTypeExists by the filter's Relationship (bench aihoe*): the enemies' / allies' / neutral's
               'has enemy': {t.template for t in self.view.things if t.owner in self.view.enemies},
               'has ally': {t.template for t in self.view.things
                            if t.owner and t.owner != self.player and t.owner not in self.view.enemies},
               'has neutral': {t.template for t in self.view.things if not t.owner},
               'harvesters': sum('HARVESTER' in b.kinds for b in mine),               # INFERRED category 0x14
               'money': lambda account: self.sim.money.get(self.player, 0),          # one account in the simulator
               'beacons': set(),                                                     # no beacons in the simulator
               'power advantage': self.power_advantage,
               'attacked': self.attacked, 'energy': self.energy}
        if foes:                                     # INFERRED: 0x8b3a00's enemy = the first of the enemies here
            out['opponent funds'] = self.sim.money.get(foes[0], 0)
            out['income'] = (self.income(self.player), self.income(foes[0]))
        if 'targets' in self.host.blocks:
            out['target'] = self.has_target
        return out

    def income(self, owner):
        """ctx 'income' (IncomeAdvantageHeuristic, 0x8c5100, read: player +0x38 -> [0] +0x34 of each side x 1/90; both
        0 -> 1, the enemy's <= 0 -> 9999): what +0x34 holds is not read -- INFERRED a rate that grows with the miners
        at work, so here the owner's harvesters while it has a refinery (only the ratio of the two sides counts)."""
        mine = [b for b in self.sim.living() if b.owner == owner]
        if not any('REFINERY' in b.kinds for b in mine):
            return 0
        return sum('HARVESTER' in b.kinds for b in mine)

    def power_advantage(self, own_kindof, enemy_kindof, own_defenses, enemy_defenses):
        """ctx 'power advantage' (PowerAdvantageHeuristic, 0x8c4910, read): (the enemy's time to kill all of ours,
        ours to kill all of theirs), tactics.army_time -- template health, not what is left. A side = its units of
        the KindOf (category 0xd: INFERRED every unit, armed or not) and, if asked, its defences (category 0x2e,
        no KindOf: INFERRED structures with a weapon). The enemy is one player: INFERRED the first of the enemies,
        as 'opponent funds' (0x8b39b0's list order not read)."""
        foes = sorted(self.view.enemies)
        if not foes:
            return None
        tc = self.host.mod['tactics']

        def side(owner, kinds, defenses):
            kinds = set(kinds.split())
            return [b for b in self.sim.living() if not b.scenery and b.owner == owner
                    and (b.weapons and defenses if 'STRUCTURE' in b.kinds else not kinds or kinds & set(b.kinds))]
        mine = self.fighters(side(self.player, own_kindof, own_defenses))
        theirs = self.fighters(side(foes[0], enemy_kindof, enemy_defenses))
        return tc.army_time(theirs, mine), tc.army_time(mine, theirs)

    def attacked(self, seconds):
        """ctx 'attacked' (StructureOrHarvesterUnderAttackHeuristic, 0x8e0c50 -> 0x8da000 / 0x8da170 -> 0x741b70,
        read): one of our structures (category 0xb) or harvesters (0x14) last hurt no longer than 15 x seconds
        frames ago. The program also wants the one who hurt it still there (not modelled: the simulator keeps no
        attacker)."""
        due = self.frame - FPS * seconds
        return any(t.owner == self.player and ('STRUCTURE' in t.kindof or 'HARVESTER' in t.kindof)
                   and self.hurt_at.get(t.id, -10 ** 9) >= due for t in self.view.things)

    def energy(self, relationship):
        """ctx 'energy' (EnergyHeuristic, 0x8c52a0, read): produced - used of us (Relationship SAME_PLAYER) or else
        of the enemy (the first, as 'opponent funds'); None = no enemy. Sim.power (EnergyProduction)."""
        if relationship == 'SAME_PLAYER':
            who = self.player
        else:
            foes = sorted(self.view.enemies)
            if not foes:
                return None
            who = foes[0]
        sup, dem = self.sim.power(who)
        return sup - dem

    def has_target(self, st):
        """ctx 'target' (states._draw): one of the state's target heuristics finds a Thing now (claims count)."""
        tg, td = self.host.mod['targets'], self.host.data_of('targets')
        table = self.ai.enemy_table             # fixed by script: one tier ([[]] = no enemy), as TargetsBlock
        tiers = None if table is None else [[p for p in table if p in self.view.enemies]]
        return any(tg.find(td.heuristic(hid), self.view, self.home, tiers, None, self.home) is not None
                   for hid, _ in st.targets)

    # ---- the blocks' outlets
    def order(self, u, kind, arg):
        """TacticsBlock / DefenseBlock: 'move' or 'attack-move' to a point -> Sim.order_move."""
        b = u.body
        if not b.alive:
            return
        if kind == 'attack':                    # the team state's 0 / 6: attack the current enemy (a Thing id)
            t = self.body_of(arg)
            if t is not None:
                self.sim.order_attack(b, t.name)
            return
        if kind == 'enter':                     # EnterGarrisons / EnterBaseDefenses: into a building (a Thing id)
            t = self.body_of(arg)
            if t is not None:
                self.host.garrison.send(b, t)
            return
        b.goal = None
        self.sim.order_move(b, (float(arg[0]), float(arg[1])), kind == 'attack-move')

    def fight(self, ai, team):
        """TacticsBlock's fight hook (the team state, 0x8cdb70): the members and every living enemy body as
        Fighters; rate = the sum of the dps of the weapons that can hit the other, times its armour (Sim.can_hit /
        the firing rule); vision = its VisionRange alone (Body.sight, 0x725c80; not the shroud clearing range)."""
        foes = [b for b in self.sim.living()
                if not b.scenery and b.owner != self.player and b.owner in self.view.enemies]
        return self.fighters([u.body for u in team.members if u.body.alive]), self.fighters(foes)

    def fighters(self, bodies):
        """Bodies as tactics.Fighter (fight's rule: rate by Sim.can_hit and the armour, vision = VisionRange)."""
        tc, s = self.host.mod['tactics'], self.sim

        def rate_of(b):
            def rate(o):
                t = o.body
                return sum(w['dps'] * sim.simunits.percent(t.armor, w['type']) / 100.0
                           for w in b.weapons if s.can_hit(w, t))
            return rate

        def fighter(b, i):
            f = tc.Fighter(i, (b.x, b.y), b.hp, b.max_hp, b.speed,
                           max((w.get('range') or 0.0 for w in b.weapons), default=0.0), b.sight or b.vision,
                           'STRUCTURE' in b.kinds, rate_of(b))
            f.body = b
            return f
        return [fighter(b, self.tid(b)) for b in bodies]

    def garrisons(self, u, own_defenses):
        """TacticsBlock's houses / defenses hooks: [(id, (x, y))] u could be sent into, the list's order; [] when it
        cannot garrison (INFANTRY, not SKIRMISH_AI_DONT_GARRISON: template +0xc0 bit 10 / +0xdc bit 12). Full ones
        are listed too (bench aibdpre)."""
        b = u.body
        if not b.alive or 'INFANTRY' not in b.kinds or 'SKIRMISH_AI_DONT_GARRISON' in b.kinds:
            return []
        return [(self.tid(g), (g.x, g.y)) for g in self.host.garrison.places(b, own_defenses)]

    def busy(self, team):
        return any(u.body.engaged or isinstance(u.body.goal, sim.Body) for u in team.members)

    def stand(self, team, p, r, outer):
        """The aesthetics manager: the team stands round p (INFERRED: evenly on a circle of r)."""
        n = max(1, len(team.members))
        for k, u in enumerate(team.members):
            a = 2 * math.pi * k / n
            self.order(u, 'move', (p[0] + r * math.cos(a), p[1] + r * math.sin(a)))

    def radius_of(self, tid):
        b = self.body_of(tid)
        sh = self.sim.blocks(b) if b else None
        return sh[2] if sh and len(sh) == 3 else 40.0

    def micro_team(self, ai, frame, team):
        mc, sp = self.host.mod['micro'], self.host.mod['specials']
        powers = self.host.data_of('unit powers')
        units = []
        for u in team.members:
            b = u.body
            reach = max((w.get('range') or 0.0 for w in b.weapons), default=0.0)
            units.append(mc.Unit(b.name, (b.x, b.y), b.hp, b.max_hp,
                                 [powers[c] for c in self.host.command_set(b.template) if c in powers],
                                 weapon_range=reach, cost=self.host.cost(b.template)))
        enemies = [sp.Thing((t.x, t.y), t.kindof, int(t.value), name=str(t.id)) for t in self.view.things
                   if t.owner in self.view.enemies]
        return mc.Team(units, enemies=enemies)

    def fire_unit(self, ai, key, u, info):
        """A unit power the micro wants used: recorded only (HOOKS 5)."""
        self.fired.append((self.frame, key, u.name, info.command))
        self.sim.note('AI', f'{self.sim.who(self.player)} 微操想用 {info.command}（{u.name}；模拟器未接技能）')

    # ---- what the AI asks of the world
    def is_structure(self, t):
        return 'STRUCTURE' in self.host.kinds(t)

    def factories(self):
        """Sim.factories with the menus cached (simunits.menu parses the XML on each call)."""
        return [b for b in self.sim.living() if b.owner == self.player and 'STRUCTURE' in b.kinds and not b.scenery
                and self.host.menu(b.template)]

    def yards(self):
        return [b for b in self.sim.living() if b.owner == self.player and 'CONSTRUCTION_YARD' in b.kinds]

    def build(self, template):
        """AIPlayer.builder: True once the order is taken (queued), False when nothing of the AI's can make it now."""
        s = self.sim
        if self.is_structure(template):
            ys = self.yards()
            if not ys or not s.can_build(self.player, template):
                return False
            y = min(ys, key=lambda y: len(self.yard_q.get(y.name, [])))
            cost, secs = simunits.production(template, s.own)
            self.yard_q.setdefault(y.name, []).append(
                {'template': template, 'cost': cost, 'frames': max(1, int(round(secs * FPS))), 'progress': 0.0,
                 'paid': 0, 'full': None})
            s.note('AI', f'{s.who(self.player)} 建造场排 {template}（{cost}，{secs:g} 秒）')
            return True
        if not s.can_build(self.player, template) or \
                not any(template in self.host.menu(f.template) for f in self.factories()):
            return False
        self.unit_q.append(template)
        return True

    def offers(self, ai, frame):
        """AIPlayer.offers: the units the AI's live factories can build now (Sim.offers), as teams.Offer with the unit
        builder's candidate state (0x8c7910): 0 = an unpacked factory that makes it has an empty queue and nothing of
        unit_q it would take, 1 = all such factories are busy; a unit only unpacking factories make is left out
        (state 2, cannot build now)."""
        tm = self.host.mod['teams']
        s, frame = self.sim, self.frame
        ready = [f for f in self.factories() if frame >= self.made.get(f.name, -10 ** 9) + self.host.unpack(f.template)]
        out = []
        for t, _, _ in s.offers(self.player):
            fs = [f for f in ready if t in self.host.menu(f.template)]
            if not fs:
                continue
            idle = any(not s.queues.get(f.name) and not any(q in self.host.menu(f.template) for q in self.unit_q)
                       for f in fs)
            kinds = self.host.kinds(t)
            surface = 'AIR' if 'AIRCRAFT' in kinds else 'AMPHIBIOUS' if 'AMPHIBIOUS' in kinds else \
                'WATER' if 'SHIP' in kinds else 'LAND'
            out.append(tm.Offer(t, frozenset(kinds), surface, state=0 if idle else 1,
                                standard=self.host.standard(t), cost=self.host.cost(t)))
        return out

    def units(self, ai, frame):
        out = []
        for b in self.sim.living():
            if b.owner != self.player or 'STRUCTURE' in b.kinds or b.speed <= 0:
                continue
            if 'HARVESTER' in b.kinds or 'IGNORES_SELECT_ALL' in b.kinds:
                continue
            if self.host.garrison.busy(b):  # inside or on its way in (INFERRED: not taken into a team again)
                continue
            if b.name not in self.wrappers:
                self.wrappers[b.name] = Unit(b)
            out.append(self.wrappers[b.name])
        return out

    def team_point(self, ai, frame):
        hx, hy = self.home
        foes = [b for b in self.sim.living() if 'STRUCTURE' in b.kinds and not b.scenery
                and self.sim.enemy(self.player, b.owner)]
        if not foes:
            return None
        f = min(foes, key=lambda b: math.hypot(b.x - hx, b.y - hy))
        return (f.x, f.y)

    # ---- the yard (Sim.produce_due's rule, for structures)
    def spot(self, yard, template):
        """Where a structure goes: the first free point on the rings round the yard (INFERRED)."""
        import platprops
        s = self.sim
        r = platprops.radius(template) if template in platprops.CATALOG else 40.0
        xs = [b.x for b in s.living()] or [yard.x]
        ys = [b.y for b in s.living()] or [yard.y]
        away = math.atan2(yard.y - (min(ys) + max(ys)) / 2, yard.x - (min(xs) + max(xs)) / 2)
        taken = [t for t in (s.blocks(b) for b in s.living() if 'STRUCTURE' in b.kinds) if t and len(t) == 3]
        for ring in RING:
            n = max(8, int(2 * math.pi * ring / (2 * r + GAP)))
            for k in range(n):
                a = away + 2 * math.pi * k / n
                x, y = yard.x + ring * math.cos(a), yard.y + ring * math.sin(a)
                if all(math.hypot(x - tx, y - ty) >= r + tr + GAP for tx, ty, tr in taken):
                    return x, y
        return yard.x + RING[-1], yard.y

    def yard_due(self, frame):
        s = self.sim
        for name in list(self.yard_q):
            y, q = s.bodies.get(name), self.yard_q[name]
            if y is None or not y.alive or not q:
                del self.yard_q[name]
                continue
            job = q[0]
            if job['full'] is not None:
                if frame >= job['full'] + PLACE_DELAY:
                    q.pop(0)
                    self.put(y, job['template'], frame)
                    self.yard_rest[name] = frame + 1
                continue
            if frame <= self.yard_rest.get(name, -1):    # the yard takes up the next the frame after (bench: 153
                continue                                # frames between two 10 s structures = 1 + 151 + 1)
            step = f32(100.0 / job['frames'])
            nxt = f32(job['progress'] + step)
            owe = min(job['cost'], math.ceil(round(job['cost'] * nxt / 100.0, 9))) - job['paid']
            have = s.money.get(self.player, 0)
            if owe > have:
                continue
            s.money[self.player] = have - owe
            job['paid'] += owe
            job['progress'] = nxt
            if nxt >= 100.0:
                job['full'] = frame

    def put(self, yard, template, frame):
        s = self.sim
        x, y = self.spot(yard, template)
        b = s.add(f'#ai {len(s.bodies)} {template}', template, self.player, x, y, by='skirmish AI', at=s.t)
        b.team = yard.team
        self.made[b.name] = frame
        self.trace.append((frame, 'own', template))
        s.note('AI', f'{s.who(self.player)} 放下 {template}')
        if s.blocks(b):
            s.reblock()
        miner = self.host.free_unit(template)
        if miner:
            self.later.append((frame + self.host.unpack(template), miner, (x, y), yard.team))
        s.change()

    def later_due(self, frame):
        s = self.sim
        for job in [j for j in self.later if j[0] <= frame]:
            self.later.remove(job)
            _, t, (x, y), team = job
            b = s.add(f'#ai {len(s.bodies)} {t}', t, self.player, x, y + 60.0, by='skirmish AI', at=s.t)
            b.team = team
            self.made[b.name] = frame
            self.trace.append((frame, 'out', t))

    # ---- units, one at a time a factory
    def unit_due(self, frame):
        s = self.sim
        for b in s.living():                    # what came out of a factory since: the trace
            if b.owner == self.player and b.name.startswith('#made') and b.name not in self.made:
                self.made[b.name] = frame
                self.trace.append((frame, 'out', b.template))
                self.host.fill(b)
        for t in list(self.unit_q):
            free = [f for f in self.factories() if t in self.host.menu(f.template)
                    and frame >= self.made.get(f.name, -10 ** 9) + self.host.unpack(f.template)
                    and not s.queues.get(f.name)]
            if free and s.order_build(self.player, t):
                self.unit_q.remove(t)

    @property
    def started(self):
        """The frame 'make base' ran (the AI's start; the bench's 'from the wake' frames count from it)."""
        return self.ai.start if self.ai.start is not None else self.woke

    def earn(self):
        """AIPlayer.money: the player's money now (AIPlayer.available: an account spends its Deposits + its budget
        share of the money -- INFERRED, bench engine_aiskirm d / f; the income is in it, Sim.mine_due, HOOKS 7)."""
        self.ai.money = self.sim.money.get(self.player, 0)

    def tick(self, frame):
        self.frame = frame
        self.earn()
        self.later_due(frame)
        self.yard_due(frame)
        self.unit_due(frame)
        if self.seen_t != self.sim.t:           # the world changes once a DT tick: look and facts then
            self.look(frame)
            self.ai.ctx.update(self.facts())
        self.ai.tick(frame)


class SimAI:
    """sim.Sim with every player the mission hands to the skirmish AI played by the layer-4 model."""

    def __init__(self, s, level='normal', seed=1, lib=None, data=None, blocks=BLOCKS):
        mod = model()
        if mod is None:
            raise RuntimeError(f'ra3model.ai not found under {labpaths.ENGINE_MODEL}')
        self.sim, self.mod, self.level, self.seed = s, mod, level, seed
        self.lib = lib if lib is not None else mod['xmldata'].Library()
        self.data = data if data is not None else mod['data'].AIData()
        self.blocks = tuple(blocks)     # which of A's blocks the brains get (() = opening, states and teams only)
        self.brains = {}                # player -> Brain
        self.done_to = None             # the last frame the AI ran
        self._data, self._cost, self._menu, self._cs, self._kinds, self._std = {}, {}, {}, {}, {}, {}
        self.garrison = Garrisons(s, self.lib)
        act = s.act

        def act_with_garrisons(name, a, script):     # HOOKS 8: the script's instant garrison, which sim.act lacks
            if name == 'NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY':
                self.garrison.put(s.body(a[0]), s.body(a[1]), script=True)
                return
            act(name, a, script)
        s.act = act_with_garrisons

    @property
    def frame(self):
        s = self.sim
        return s.eng.frame if s.eng is not None else int(round(s.t * FPS))

    def flags(self, player):
        """The mission's flags as states.py keys them: cnv's scripts run in a player's script list, so a bare SET_FLAG
        name is that list owner's and 'scope/name' sets the scope by hand ('/name' the empty one, which
        ScriptedFlagHeuristic reads -- l4_states.md 7; bench aistateplain: bare names unseen, aistateslash: seen)."""
        st = self.mod['states']
        return {st.flag_key(k, SCRIPT_SCOPE): bool(v) for k, v in (self.sim.flags or {}).items()}

    def data_of(self, what):
        """The blocks' SDK data, read once a run."""
        if what not in self._data:
            m = self.mod
            self._data[what] = {'targets': lambda: m['targets'].TargetData(),
                                'tactics micro': lambda: m['tactics'].MicroData(),
                                'tactic attrs': lambda: m['defense'].TacticAttrs(),
                                'micro': lambda: m['micro'].load_micro(),
                                'unit powers': lambda: m['micro'].load_unit_powers()}[what]()
        return self._data[what]

    def cost(self, template):
        if template not in self._cost:
            self._cost[template] = int(simunits.production(template, self.sim.own)[0] or 0) if template else 0
        return self._cost[template]

    def menu(self, template):
        if template not in self._menu:
            self._menu[template] = simunits.menu(template, self.sim.own)
        return self._menu[template]

    def command_set(self, template):
        """The template's CommandSet's commands (simunits' reading of the SDK's GlobalData), cached."""
        if template not in self._cs:
            cs = simunits._inherited(template, self.sim.own,
                                     lambda xml: (re.findall(r'\bCommandSet="([^"]+)"', xml) or [''])[0], '')
            self._cs[template] = simunits._commands(self.sim.own)[0].get(cs, [])
        return self._cs[template]

    def standard(self, template):
        """UnitBuilderStandardCombatUnit of a template (the unit builder's candidates, INFERRED), cached."""
        if template not in self._std:
            self._std[template] = simunits._inherited(
                template, self.sim.own,
                lambda xml: (re.findall(r'\bUnitBuilderStandardCombatUnit="(\w+)"', xml) or [''])[0], '') == 'true'
        return self._std[template]

    def unpack(self, template):
        """round(UnpackTime x 15) (tools/aiopen.unpack_frames); 0 without the module."""
        tpl = self.lib.template(template)
        m = tpl.first('StructureUnpackUpdate') if tpl is not None else None
        s = (m.attrs.get('UnpackTime') or '0s') if m is not None else '0s'
        return round(float(s.rstrip('s')) * FPS)

    def kinds(self, template):
        """KindOf of a template: simunits', else the model's library's (HOOKS 6)."""
        if template not in self._kinds:
            st = simunits.stats(template, self.sim.own)
            tpl = None if st['kinds'] else self.lib.template(template)
            self._kinds[template] = set(st['kinds']) if st['kinds'] else set(tpl.kinds) if tpl is not None else set()
        return self._kinds[template]

    def fill(self, b):
        """A body simunits knows nothing of (its table misses the second GameObject of a file, such as the Riptide's
        AlliedAntiInfantryVehicle_Ground the war factory's button makes: speed 0, no KindOf -- HOOKS 6): KindOf and
        speed from the model's library, health / armour / weapons from the template of the name without its last
        '_' part when simunits knows that one (INFERRED: the same unit)."""
        if 'all' not in (b.guessed or []):
            return
        tpl = self.lib.template(b.template)
        if tpl is None:
            return
        ro = importlib.import_module('ra3model.objects.runoffmap')
        b.kinds = frozenset(tpl.kinds)
        b.speed = float(ro.normal_speed(self.lib, tpl) or 0.0)
        b.surface = 'both' if 'AMPHIBIOUS' in tpl.kinds else 'air' if 'AIRCRAFT' in tpl.kinds else b.surface
        base = b.template.rsplit('_', 1)[0]
        if base != b.template:
            st, f = simunits.stats(base, self.sim.own), simunits.fight(base, self.sim.own)
            if f['hp']:
                b.max_hp = b.hp = f['hp']
                b.armor, b.weapons = f['armor'], f['weapons']
            b.surface, b.sight = st['surface'], st['vision'] or b.sight
        b.guessed = ['all: simai.fill']

    def free_unit(self, template):
        """The unit a structure brings along (a refinery's miner; INFERRED by name, bench aiopen 采矿车)."""
        if 'REFINERY' in simunits.stats(template, self.sim.own)['kinds']:
            miner = template.replace('Refinery', 'Miner')
            return miner if simunits.table().get(miner.lower()) else None
        return None

    def own_personalities(self):
        """The AI personalities the mission writes into its mod (Mission.assets, AIPersonalityDefinition:...) added to
        the AI's data once, so a probe's own personality (missions/aistate_bench.py) is the one the brain runs."""
        if getattr(self, '_own_done', False):
            return
        self._own_done = True
        for a in getattr(self.sim.m, 'assets', None) or []:
            if len(a) >= 3 and str(a[2]).startswith('AIPersonalityDefinition:'):
                self.data.add_text(a[1])
                if 'AITargetingHeuristic' in a[1] and 'targets' in self.blocks:    # a probe's own heuristic
                    self.data_of('targets').add_text(a[1])                        # (missions/ainamed_bench.py)
                if 'AIMicroManagerData' in a[1] and 'targets' in self.blocks:      # a probe's own micro manager
                    self.data_of('tactics micro').add_text(a[1])                  # (missions/airetreat_bench.py)

    def attach(self):
        """Brains for the players the mission has handed to the AI since the last call."""
        s = self.sim
        sides = {v: k for k, v in s.players.items()}
        for player in s.ai:
            if player in self.brains:
                continue
            side = sides.get(player, '')
            pid = (s.m.sides.get(side) or {}).get('aiPersonality', '').split(':')[-1] or '1AlliedBalanced'
            self.own_personalities()
            self.brains[player] = Brain(self, player, side, pid, int(round(s.ai[player] * FPS)))

    def advance(self, frames):
        """The mission `frames` frames on (Sim.advance a DT tick at a time), the AI ticked for each frame after."""
        target = self.frame + frames
        while self.frame < target and self.sim.ending is None:
            self.sim.advance(1)
            self.garrison.due()
            self.attach()
            for b in self.brains.values():
                b.switches()
            now = self.frame
            for f in range(now if self.done_to is None else self.done_to + 1, now + 1):
                for b in self.brains.values():
                    if f >= b.woke:
                        b.tick(f)
            self.done_to = now
        return self

    def thoughts(self):
        return {self.sim.who(p): b.ai.thoughts() for p, b in self.brains.items()}


def run(build, check='', until=200.0, level='normal', seed=1, lib=None, data=None, blocks=BLOCKS):
    """Build `build` (a cnv build name), run it with the AI `until` seconds: the SimAI."""
    import build as bld
    m, t, _ = bld.resolve(build, check)
    w = SimAI(sim.Sim(m, t, level), level, seed, lib, data, blocks)
    w.advance(int(until * FPS))
    return w


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('build', nargs='?', default='aiopen')
    ap.add_argument('--check', default='')
    ap.add_argument('--until', type=float, default=200.0)
    a = ap.parse_args()
    if not available():
        print('ra3model.ai not on this computer')
        return 1
    w = run(a.build, a.check, a.until)
    for p, b in w.brains.items():
        print(f'{w.sim.who(p)}（第 {b.started} 帧开局；下面是开局后的帧）')
        for f, what, t in b.trace:
            print(f'  {f - b.started:5d} 帧 {(f - b.started) / FPS:6.1f} s  {what:4s} {t}')
        for e in [e for e in b.ai.teams.log if e[1] in ('go', 'disband', 'ended')][-10:]:
            print('  team', e[0] - b.started, e[1:])
    return 0


if __name__ == '__main__':
    sys.exit(main())
