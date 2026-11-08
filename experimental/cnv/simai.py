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
  states      ctx: the mission's flags (ScriptedFlagHeuristic), 'has' (its templates), 'building' (the kinds queued),
              'enemy nearby' (enemy value within the distance of its yard).
  blocks      A's TargetsBlock + TacticsBlock (orders: 'move' / 'attack-move' -> Sim.order_move), DefenseBlock (one
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
                                       ctx={'land path': True}, rng=random.Random(host.seed), index=side_index(side))
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
        self.view = tg.View(player, [], enemies=foes)
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
                                       micro=h.data_of('tactics micro'))
        self.targets = tg.TargetsBlock(h.data_of('targets'), self.active, lambda ai, f: self.view,
                                       lambda ai, st: self.home, home=self.home, base_of=self.base_of,
                                       held=self.tactics.held)
        self.tactics.targets = self.targets
        self.ai.blocks += [self.targets, self.tactics]
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

    def base_of(self, player):
        ys = [b for b in self.sim.living() if b.owner == player and 'STRUCTURE' in b.kinds and not b.scenery]
        y = next((b for b in ys if 'CONSTRUCTION_YARD' in b.kinds), ys[0] if ys else None)
        return (y.x, y.y) if y else None

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
                                   under_attack=frame - self.hurt_at.get(i, -10 ** 9) <= 2 * FPS))
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
        out = {'flags': self.host.flags(self.player), 'has': {b.template for b in mine}, 'building': building,
               'enemy nearby': near}
        if 'targets' in self.host.blocks:
            out['target'] = self.has_target
        return out

    def has_target(self, st):
        """ctx 'target' (states._draw): one of the state's target heuristics finds a Thing now (claims count)."""
        tg, td = self.host.mod['targets'], self.host.data_of('targets')
        return any(tg.find(td.heuristic(hid), self.view, self.home, None, None, self.home) is not None
                   for hid, _ in st.targets)

    # ---- the blocks' outlets
    def order(self, u, kind, arg):
        """TacticsBlock / DefenseBlock: 'move' or 'attack-move' to a point -> Sim.order_move."""
        b = u.body
        if b.alive:
            b.goal = None
            self.sim.order_move(b, (float(arg[0]), float(arg[1])), kind == 'attack-move')

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
            self.attach()
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
