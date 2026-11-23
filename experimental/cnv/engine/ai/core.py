r"""The skirmish AI on the plan simulator: the engine line's layer-4 model (RA3-EngineModel ra3model/ai, AIPlayer and
its blocks) plays an enemy of sim.Sim -- it builds its base, makes units, puts them in teams and sends them out.

This file only calls the simulator (Sim.advance, Sim.factories / order_build / queues, Sim.add, Sim.order_move,
Sim.money, Sim.ai); it changes none of sim.py's rules (sim.py / simunits.py are the engine line A's). Where the model
is not on this computer available() is False and the SimAI plays no one: a mission that hands no player to the AI
runs as the plain Sim (the conformance runner's AI-free scenes run there too); one that does raises NoModel (as soon as
a side with an aiPersonality is met, or the frame the mission hands a player over), which the tests take as a skip.

  python -I -X utf8 experimental/cnv/simai_run.py [build] [--until <seconds>] [--check <check>]
(R3 13f-2d: the run -- build, make the Sim, play it -- is simai_run.py; this file is the layered AI, L8, and
never names the Sim: a target that is an object, not a point, is a kernel Thing.)

A side with an aiPersonality (mission.sides) has an AIPlayer from the first frame -- its states and teams run before
the wake (bench aialobsw) -- and a side handed over without one gets the default personality then; either is told
'make base' the frame the mission hands it to the AI (UNIT_AI_TRANSFER_ALL / SKIRMISH_AI_MAKE_BASE: Sim.ai). Then
every frame (the simulator moves in DT ticks; the AI is ticked for each frame of a tick right after it):
  structures  the simulator builds none (a yard's CommandSet has no UNIT_BUILD), so this file is the yard: one queue a
              yard, the float32 progress of Sim.production.due paid frame by frame from Sim.money, owned PLACE_DELAY (1)
              frame after full, the next started the frame after (bench aiopen f1-f3); put down on rings round the
              yard (INFERRED: the first free spot, from the side away from the map's middle). A refinery brings its
              miner its UnpackTime later (bench aiopen: 667 = refinery + 60).
  units       Sim.order_build, one at a time a factory: the next is queued once the last has left the door (bench
              aiopen: 161 frames a Riptide = 151 + door 10), none before the factory has unpacked (UnpackTime).
  offers      the unit builder's candidates (Sim.offers) with their state (0 an idle factory, 1 all busy), standard
              combat flag and cost; it orders for no team, beside the opening, on the AI's PRODUCTION account.
  money       the player's money now (Sim.money) = ai.money: an account spends its Deposits + its budget share of it.
  teams      ai.units = the AI's own movers (not HARVESTER; the IGNORES_SELECT_ALL ones only a CreateUnits slot
              naming them takes, teams.recruit) as stable Unit wrappers;
              team_point = the closest enemy structure to the AI's yard.
  states      ctx: the mission's flags (ScriptedFlagHeuristic), 'has' (its templates; 'has enemy' / 'has ally' /
              'has neutral' by owner for ObjectOfTypeExists' Relationship), 'building' (the kinds queued),
              'enemy nearby' (enemy value within the distance of its yard), 'path to target' (PathToTargetHeuristic:
              the last enemy with a structure, both base objects by states.base_object, spots by states.spot on
              the simulator's grids, a route for the test template's surface; cached PATH_EVERY), 'harvesters',
              'money', 'opponent funds' (the first enemy's), 'income' (each side's harvesters while a refinery
              stands -- INFERRED), 'beacons' (none), 'tech buildings' (SimAI.tech_buildings), 'nodes full' (Brain.open_nodes empty), 'power advantage' (tactics'
              rule over the whole armies -- INFERRED); the other strategic facts stay unmodelled (states.strategic).
  blocks      A's TargetsBlock + TacticsBlock (orders: 'move' / 'attack-move' -> Sim.order_move, 'enter' -> Garrisons;
              houses / defenses = Brain.garrisons, full ones listed too), DefenseBlock (one
              MAIN_BASE round the first yard; hurt = the body's hp fell; aesthetics = a circle round the point),
              MicroBlock (unit powers from the CommandSet; the retail miner armor toggle executes; other uses
              are only recorded), PlayerPowers (none yet: the simulator has no superweapon charge). The AI sees the whole
              map (INFERRED; the view's things are every living body that is not scenery).

HOOKS (what this file would rather have from sim.py; for A through the coordinator, not urgent):
  1. a per-frame callback inside Sim.step: here the AI is ticked after a whole DT tick, so a unit queued once the last
     left the door starts up to 7 frames late (Riptides 165 apart, bench 161), and the yard is paid after the tick's
     unit production;
  2. a structure queue (yard production) and a placement rule in Sim, so a human player's yard works the same;
  3. Sim.production.due starts a factory's next job the frame after the last is full; the AI bench (aiopen) shows the
     next starting when the last has left the door -- which holds for a human's queue is not measured;
  4. a factory's UnpackTime in Sim (no unit before it has unpacked);
  5. AI unit powers: toggles and the bounded Bonzai bridge execute; other unit powers / player powers record intent;
  6. simunits' table misses the second GameObject of a file (AlliedAntiInfantryVehicle_Ground, the Riptide the war
     factory makes: speed 0, no KindOf, no weapons); fill() patches the AI's own such units from the model's library.
  9. RECORD (read only, off by default): SimAI(record=True) / run(..., record=True) fills each Brain.rec with a
     frame-by-frame trail of its teams for the other lines to read (Brain.snap, after each AI frame): rec['frames'],
     rec['orders'], rec['deaths']. It reads what the AI already holds and asks nothing new of the world (no Thing
     id is handed out, no random drawn), so a run is bit-for-bit the same on or off (tests/test_simai_record.py).
  8. garrisons: the simulator's (sim.Sim.garrison, simgarrison.Garrisons) -- the AI's 'enter' orders walk its men
     into houses / turrets through it; the older tests read Garrisons.log (sim.py counts
     PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS, ENCLOSED among them, since A round 164); no fire from inside.
"""
from collections import Counter
import functools
import importlib
import math
import os
import random
import re
import struct
import xml.etree.ElementTree as ET
import sys

HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import labpaths  # noqa: E402
import modelpin  # noqa: E402
import engine.data.units as simunits  # noqa: E402
import engine.orders.micro as simmicro  # noqa: E402
import engine.world.handle as simworld  # noqa: E402
from engine.ports.command import Command  # noqa: E402
from engine.ports import ai as ai_port, templates  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
import engine.combat.range as simrange  # noqa: E402

# The skirmish AI borrows nothing on its host (the Sim) beyond the world (simworld.WORLD_API) and the ports: its
# orders, its micro's charge too (`power` via 'micro', B3), through the command port (`commands`, R3 13f-1); the
# mission's AI settings and the players' systems (power, production, the wallet) through the AI port's Settings and
# PlayerSystems, the frame loop its runner's (13f-2a / 13f-2c, engine/ports/ai.py); money, flags and the fight through
# the observation port, the weapon reach rules off L3 simrange (13f-2b). It sets nothing there (⑨d-1).
# ADR 0037 phase 1: the names of the world API the AI reaches (16, under half; the mission and the garrisons through the
# settings and observation ports); it adds no body (a refinery's free miner is the production rules': systems.bring)
AI_WORLD = frozenset({'bodies', 'blocks', 'enemy', 'frame_now', 'ground', 'human', 'living', 'note', 'own',
                      'players', 'relation', 'relations', 't', 'waypoints', 'who', 'xml_of'})


FPS = 15
# the engine's word for a tactic type in its team names where it is not the type itself (C's team log
# tests/fixtures/c_release_teams/aiskirm_m.txt: Tactic="Engineer" -> AlliedCaptureTech_MEDIUM_EngineerTactic_0_0)
TACTIC_NAME_WORDS = {'Engineer': 'EngineerTactic'}
PLACE_DELAY = 1                     # bench aiopen f1-f3 (opening.PLACE_DELAY): owned 1 frame after the head is full
RING = (260.0, 400.0, 540.0, 680.0)     # INFERRED: the rings a yard puts its structures on
GAP = 20.0                          # INFERRED: room left between two structures' rounds
# the refinery placement search (work/re d125_refinery_units.md 1 / d121 3): the personality's fields and
# their XSD defaults; ResourceNodeSearchRadius orders the ore nodes, RefineryPlacement* sizes the rings round one
REFINERY_FIELDS = (('ResourceNodeSearchRadius', 500.0), ('RefineryPlacementStartDistanceDelta', 0.0),
                   ('RefineryPlacementIncreaseTickAmount', 60.0),
                   ('RefineryPlacementNumberOfIncreaseTicksBeforeGivingUp', 3))
REFINERY_NEAR = 200.0               # an own refinery within this of a node: the node's "has a refinery" key
# the search's pre-check (D138, work/re d138_refinery_answers.md 1, read): every ore node has a default spot S (its
# AssistedPlacementInfoBehavior SuggestedOffset ahead, facing the node); a spot c fails when (a) it is within the two
# rounds of S and the refinery's shape at c (facing its node) meets the one at S (facing S's node), or (b) it is within
# PASSAGE_CLEAR of the passage point P = S + (R + PASSAGE_GAP) toward the node (R the refinery's round). Every node's
# S is in the table, its own too, so a node's default spot always fails (read). 300 instead of 150 under an unread
# condition; bench rpx's ring 5 at k -3 (~183 from P) stands, so the AI's is 150.
PASSAGE_GAP = 20.0
PASSAGE_CLEAR = 150.0
# SimpleExpansion's go is one formation move (0x22c) to the node itself, faced at the nearest enemy object a member
# can hit (D167/D168: bench aiexpb50/200/400 f473 facing -2.248 = node -> the player's barracks, -128.9 deg, 754
# away); the game splits it one destination a member: the escorts one row through the node, EXPANSION_ROW apart,
# the miner a row behind (bench: four Guardians at side +-33 / +-100, the miner 67 straight back). INFERRED: the row
# step for other templates (other benches: Guardians 67, infantry 35, the formation shape a random pick -- line,
# column, box, wedge; the line is the common one), the search radius (>= 754), no enemy -> facing the way walked.
EXPANSION_ROW = 67.0
# when the AI wants a refinery (D138 2, read): some node not yet served has, R + its own radius ahead of it, a point
# within an own build-radius structure's ProjectedBuildabilityInfo Radius + R. Served (INFERRED: the node wrapper's
# state is unread): an own refinery within SERVED of the node, the node its nearest. aiskirm: both east nodes served
# -> no third; aiskin0 / aiskin1: the yard-placed ones stand 366+ from the west east node -> more keep coming;
# aiskind: the far fields (>= ~1280 from the yard) are beyond 600 + 75 of it -> never wanted.
SERVED = 300.0
NODE_REACH = 75.0                   # D138 2 / B208 (read): the constant both terms of that scan add
NODE_MINERS = 3                     # B210 (bench ainf2 / ainf4 / ainf3: 1 / 2 / 3 own collectors a refinery, its own
                                    # included -> full only at 3): INFERRED the node wrapper's capacity, unread
ALLY_OVERLAP_OK = True              # B213 allied_ok: an own radius over a friend's lets the spot through (H2, INFERRED:
                                    # the cell passes if any of its records does, read); bench acbr0 = acbr1 refutes H1
DIFFICULTY = {'easy': 'EASY', 'normal': 'MEDIUM', 'hard': 'HARD', 'brutal': 'BRUTAL'}
BLOCKS = ('targets', 'defense', 'micro', 'specials')
PATH_EVERY = 10 * FPS               # INFERRED: a PathToTargetHeuristic answer is kept 10 s (the engine asks every
                                    # evaluation; here a route costs a whole-grid search)
SCRIPT_SCOPE = 'the list owner'     # the scope of a bare flag name (the script list's player; INFERRED: its name)
MODULES = ('data','player', 'opening', 'states', 'teams', 'targets', 'tactics', 'defense', 'micro', 'specials')
_AI = {}


def _walks(b):                      # a unit that can walk: speed, not IMMOBILE (UseTransports' riders, review ww #2)
    return b.speed > 0 and 'IMMOBILE' not in b.status


def model():
    """The engine model's ra3model.ai modules as a dict, or None (modelpin.package loads the package by file)."""
    if 'got' not in _AI:
        root = labpaths.ENGINE_MODEL
        got = None
        if os.path.isfile(os.path.join(root, 'ra3model', 'ai', 'player.py')):
            try:
                modelpin.package(os.path.join(root, 'ra3model'))
                got = {k: importlib.import_module(f'ra3model.ai.{k}') for k in MODULES}
                got['xmldata'] = importlib.import_module('ra3model.objects.xmldata')
            except ImportError:
                got = None
        _AI['got'] = got
    return _AI['got']


def available():
    return model() is not None


class NoModel(RuntimeError):
    """The mission hands a player to the skirmish AI and ra3model.ai is not on this computer (a test's skip)."""


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

    def __init__(self, body, observe=None, hunted=None):
        self.body, self.observe = body, observe     # the observation port, for in_combat's firing / volleys
        self.hunted = hunted                        # serial -> the AI's recorded unit target (Brain.hunt_target)
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

    @property
    def facing(self):                   # radians; the aesthetics form-up faces the lead member's heading
        return getattr(self.body, 'angle', None)

    @property
    def moving(self):                   # still on a path, or turning to the facing it was sent with (locomotion.turn; the
        b = self.body                   # form-up waits for every member to stop: bench airev1t, A round 227)
        return bool(b.alive and (getattr(b, 'path', None) or getattr(b, 'face', None) is not None))

    @property
    def in_combat(self):
        """What TeamTemplate.AllowRecruitUnitsInCombat false keeps out (teams.recruit, work/re b220): the unit's own
        attack target, alive, that one of its weapons can hit and reaches (simrange.in_range) at the recruiting
        frame. Its own target: the order's (body.goal) or the one it went after by itself (body.chase); else the one
        it aimed at this tick (firing / volleys: the simulator keeps no auto-acquired target between ticks,
        INFERRED); else the AI's recorded target for it (the hunt state's). A dead target is no target (the K2 cut:
        a stale fire entry on a dead foe kept the Hammers out past the swap); firing, reloading or a pre-attack wait
        decide nothing (bench k2gate0 / k2gate1: a Guardian 60 s in pre-attack at a live foe in range is refused
        with the switch off, taken with it on). The range edge, weapon switching and the team fallback are not
        benched (work/re/k2_recruit_gate_1119.md)."""
        b, observe = self.body, self.observe
        if observe is None or not b.alive:
            return False
        t = next((g for g in (getattr(b, 'goal', None), getattr(b, 'chase', None)) if getattr(g, 'alive', False)),
                 None)
        if t is None:
            t = next((pick for pick, _, a in observe.firing() + observe.volleys() if a is b and pick.alive), None)
        if t is None and self.hunted is not None:
            t = self.hunted(b.serial)
            t = t if getattr(t, 'alive', False) else None
        return t is not None and any(observe.can_hit(w, t) and simrange.in_range(b, t, w) for w in b.weapons)

    def __repr__(self):
        return f'Unit({self.template} {self.body.name})'


# The engine model's callbacks a brain answers (ADR 0037 core step 5): model part -> (attribute, the brain's method
# of that name, or a maker of the answer for one brain). Bound only where the model has the attribute (a model
# without the structure build states has no power, one without REFINERY no refinery_spot): 'ai' when the brain is
# made, 'tactics' and 'teams' when the targets block attaches.
MODEL_HOOKS = {
    'ai': (('structure_of', 'is_structure'), ('builder', 'build'), ('units', 'units'), ('owned', 'owned'),
           ('army', 'army'), ('team_point', 'team_point'), ('offers', 'offers'), ('build_offers', 'build_offers'),
           ('power', 'power_now'), ('energy_of', lambda b: lambda t: simunits.energy(t, b.world.own)),
           ('near_factory', 'near_factory'), ('upgrade_offers', 'upgrade_offers'), ('upgrader', 'upgrade'),
           ('refinery_spot', lambda b: lambda ai, frame, template: b.refinery_spot(template)),
           # BEST_UNIT_* scores with host.efficiency (SimAI.efficiency): the build states then take the idle
           # barracks every second and the unit builder (every 10 s) finds it busy -- the bench (engine_aiskirm z)
           # builds only the counter (B handoff 131); off = the unit builder alone, as before round 129
           ('expected', lambda b: b.expected if getattr(b.host, 'efficiency', False) else None)),
    # PathfindingCheckType's kick (D152); SimpleExpansion unpacks within Distance on the way (D157); AlphaStrike (a)
    'tactics': (('reach', 'reach'), ('approach', 'approach'), ('allied', 'allied'), ('carry', 'carry'),
                ('board', 'board'), ('riding', 'riding'), ('unload', 'unload')),
    # a slot's team is made once the slot has a target (l4_states.md 1/7; the teams tick before the blocks: INFERRED
    # one-think lag); a gathering team whose slot's target is gone ends (TeamMaker._slots); PathfindingCheckType at
    # recruiting (D152): the slot's target as a point
    'teams': (('has_target', lambda b: lambda ai, key, n: b.slot_target(ai, key, n) is not None),
              ('target_of', 'slot_target'), ('reach', 'reach_target'), ('carry', 'carry'),
              ('alive', lambda b: lambda ai, i: i in b.targets.points or any(t.id == i for t in b.view.things))),
}


class Brain:
    """One AI player of the simulator's: the AIPlayer and the world it is given (yard, factories, units, the view)."""

    def __init__(self, host, player, side, personality, frame):
        self.host, self.world, self.player = host, host.world, player
        self.commands = host.commands   # the command port its orders go through (13f-1)
        self.commands.library(player, lambda: host.lib)     # its fill_body's library (B3), the host's when used
        self.systems = host.systems     # the players' systems it asks (power, production, the wallet; 13f-2c)
        self.settings = host.settings   # the mission's AI settings (the AI port)
        self.observe = host.observe     # the observation port (its reads of the fight, money, flags: 13f-2b)
        self.made_as = (side, personality)      # how SimAI.attach made it (a snapshot's brain is made again so)
        m = host.mod
        import engine.players.tech as simtech
        # the player's faction (the map's playerFaction, else by name) for the openings' Side (d66_b_fields.md:
        # an opening of another faction is skipped; none left = the opening is complete at once)
        faction = simtech.faction_of(player, self.settings.sides.get(side))
        self.ai = m['player'].AIPlayer(host.data, personality, DIFFICULTY.get(host.level, 'MEDIUM'),
                                       ctx={'path to target': self.path_to_target}, rng=random.Random(host.seed),
                                       index=side_index(side), side=faction and f'PlayerTemplate:{faction}')
        # the short-opening rule (opening.kept_orders) covers structure Builds only: a unit Build is kept (D157,
        # INFERRED -- bench aiexpb*: Time 0s Deposit, Build AlliedMiner, Time 5s made its miner): structure_of
        self.hook('ai', self.ai)
        # ResourceMultiplierCheat: the AI's deposits x the line for its difficulty (Mining.mine_due; data.resource_multiplier)
        mult = getattr(host.data, 'resource_multiplier', lambda *a: 1.0)(personality, self.ai.difficulty)
        if mult != 1.0:
            self.systems.multiply_income(player, mult)              # the AI port's PlayerSystems (shortcut)
        self.paths = {}                 # (surface, template, condition) -> (frame asked, answer)
        self.path_rng = random.Random(host.seed)    # the spot's start angles (the engine: the logic random)
        self.tower_rng = random.Random(host.seed)   # a base defence's angle and radius jitter (its own: no other draw moves)
        self.place_rng = random.Random(host.seed + 7)   # the general placement's angle and radius draws (its own too)
        self._protos = {}               # template -> a Body never placed (expected: the candidate)
        self.yard_q = {}                # yard serial, or (serial, 'defense') -> [job]
        self.yard_rest = {}             # the same key -> the last frame it starts nothing (the one after a put)
        self.unit_q = []                # [template] waiting for a free, unpacked factory that makes it
        self.made = {}                  # body serial -> frame it came (same-name sweep 11-19b O63: not by name) (structures: unpack; units: the trace)
        self.wrappers = {}              # body serial -> Unit (by serial: review 11-19 q P2 #1)
        self.trace = []                 # (frame, 'own' | 'out', template): what came when
        self.born = self.frame = frame  # the brain thinks from here (its states and teams: before the wake)
        self.last_expansion = 0         # the frame its newest outpost came (facts' 'last expansion')
        self.woke = None                # the frame 'make base' was told (the mission's wake): wake()
        self.ids, self.hp, self.hurt_at = {}, {}, {}     # body name -> Thing id; last hp; id -> frame last hurt
        self.seen_t = None              # the sim time the view was last built at
        self.fired = []                 # (frame, team key, unit, command): unit powers the micro wanted
        self.rec = {'frames': [], 'orders': [], 'deaths': {}}   # HOOKS 9: filled only with SimAI(record=True)
        # the runs the trail saw, first seen first (a run's number is its place + 1; a Run is the plugin's dataclass,
        # equal by value, so found by identity, never by id()); run number -> the Run.mem seen last; name -> body
        self._rec_runs, self._rec_mem, self._rec_bodies = [], {}, {}
        self._team_names = None         # engine team name -> the model's team key (state, tactic id, template index)
        self.settings.add_team_lookup(self.team_named)
        self.home = (0.0, 0.0)
        tg = m['targets']
        self.view = tg.View(player, [], enemies=self.foes(), waypoints=self.world.waypoints,
                            # E81/E87: Location uses terrain, including stationary water structures.
                            # INFERRED at shorelines, bridges and for airborne targets.
                            water_at=lambda x, y: self.world.ground.z(x, y) < self.world.ground.water,
                            expansion_candidates=(self.expansion_candidates
                                                  if (self.settings.facts.get('dual bases')
                                                      or self.settings.facts.get('expansion')) else None))
        self.base = self.powers = None
        self.attach(host.blocks)
        self._set_initial_yards(self.yards())

    def _set_initial_yards(self, yards):
        self._has_initial_yards = bool(yards)
        if yards:
            self.home = (yards[0].x, yards[0].y)
        # Dual-yard probe: the initial AI base exists before the scripted yard.
        # INFERRED bootstrap for this single-initial-yard fixture only. Later
        # yards do not register AI bases merely by being physical structures.
        self.expansion_anchor = yards[0] if len(yards) == 1 else None
        # Initial-yard registration order is INFERRED from the two-base probe;
        # retain stable ids when a yard disappears, never enumerate live yards.
        self.expansion_initial_yards = tuple(yards) if self.settings.facts.get('initial dual bases') else ()
        if 'targets' in self.host.blocks:
            self.targets.home = self.home
        if self.defense is not None:
            df = self.host.mod['defense']
            self.base = df.Base(1, self.home, (), frozenset({'MAIN_BASE'}))
            self.bases = [self.base]
            if len(self.expansion_initial_yards) >= 2:      # two initial yards: two MAIN_BASEs, ids in placement
                a, b = self.expansion_initial_yards[:2]     # order (C's aibs3 / aibn2 base ids; INFERRED adapter)
                self.base = df.Base(0, (a.x, a.y), (), frozenset({'MAIN_BASE', 'OLDEST_OF_TYPE'}))
                self.bases = [self.base, df.Base(1, (b.x, b.y), (), frozenset({'MAIN_BASE', 'MOST_RECENT_OF_TYPE'}))]

    def wake(self, frame):
        """The mission handed the player to the AI (Sim.ai): 'make base' that frame -- the opening and the building
        start from it; the states and teams have run since the brain was made (bench aialobsw, B round 161)."""
        if self.woke is None:
            self.woke = frame
            self.ai.tell(self.host.mod['player'].Command('make base'))

    # ---- A's blocks (targets, tactics, defence, micro; the player's superweapons beside them)
    def attach(self, which):
        import engine.objects.crush as simcrush

        h, m = self.host, self.host.mod
        tg, tc, df, mc = m['targets'], m['tactics'], m['defense'], m['micro']
        self.defense = None             # no defense block (blocks=()): general_spot / node_side_spot make their own
        if 'targets' not in which:
            return
        self.tactics = tc.TacticsBlock(None, lambda ai, f: self.view, self.order, lambda ai: self.home,
                                       act=self.act, micro=h.data_of('tactics micro'), fight=self.fight,
                                       houses=lambda ai, u: self.garrisons(u, False),
                                       defenses=lambda ai, u: self.garrisons(u, True),
                                       crush=self._crush_hook(simcrush),
                                       pullback=lambda ai, u: h.pullback.query(self, u),
                                       # GatherWaypoint: the map's waypoint by name, None when absent (D148)
                                       gather_point=lambda ai, tac: self.world.waypoints.get(getattr(tac, 'gather', '')
                                                                                           or None))
        self.tactics.rng = random.Random(h.seed)    # state 2's RandomTargetScoreModifier / TimeToKeepTarget
        self.hook('tactics', self.tactics)
        self.targets = tg.TargetsBlock(h.data_of('targets'), self.active, lambda ai, f: self.view,
                                       lambda ai, st: self.home, home=self.home, base_of=self.base_of,
                                       held=self.tactics.held)
        self.tactics.targets = self.targets
        self.ai.blocks += [self.targets, self.tactics]
        self.hook('teams', self.ai.teams)
        if 'defense' in which:
            self.defense = df.DefenseBlock(self.tactics, lambda ai, f: self.view, bases=lambda ai, f: self.bases,
                                           busy=self.busy, aesthetics=self.stand, radius=self.radius_of,
                                           attrs=h.data_of('tactic attrs'), rng=random.Random(h.seed),
                                           last_hurt=lambda ai, i: self.hurt_at.get(i))
            self.ai.blocks.append(self.defense)
        if 'micro' in which:
            self.micro = mc.MicroBlock(self.micro_team, fire=self.fire_unit, data=h.data_of('micro'),
                                       rng=random.Random(h.seed).uniform, move=self.dodge_move)      # MicroManager's rng(lo, hi)
            self.ai.blocks.append(self.micro)
        if 'specials' in which:
            self.powers = m['specials'].PlayerPowers([], DIFFICULTY.get(h.level, 'MEDIUM'))

    def hook(self, part, model):
        """Bind MODEL_HOOKS[part] on that part of the brain's own engine model: each callback the model has."""
        for name, answer in MODEL_HOOKS[part]:
            if hasattr(model, name):
                setattr(model, name, getattr(self, answer) if isinstance(answer, str) else answer(self))

    def allied(self, ai):
        """AlphaStrike (a)'s own / allied objects: not the enemies', the civilians' or a Neutral player's."""
        return self.fighters([
            b for b in self.living() if not b.scenery and b.owner and b.owner != simworld.CIV
            and b.owner not in self.view.enemies and self.world.relations.get((self.player, b.owner)) != 'Neutral'])

    def slot_target(self, ai, key, n):
        """The target of slot n of the team template `key`'s state, None when it has none."""
        return self.targets.slot_target(self.tactics.state_of(ai, key), n)

    def active(self, ai, frame):
        """The states whose target slots are picked this think. INFERRED from the slot-pick rule, work/re/l4_states.md (a slot with a busy team does
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
        got = self.settings.ai_switches.get(self.player, {})
        seen = getattr(self, '_switched', {})
        Command = self.host.mod['player'].Command
        for name, v in got.items():
            if seen.get(name) == v:
                continue
            if name == 'SKIRMISH_AI_USE_REPAIRS':
                self.ai.tell(Command('use repairs', {'on': v}))
            elif name == 'SKIRMISH_AI_USE_REBUILD_SYSTEM':
                own = [(b.template, b.x, b.y) for b in self.world.living()
                       if b.owner == self.player and 'STRUCTURE' in b.kinds and not b.scenery]
                self.ai.tell(Command('use rebuild', {'on': v, 'structures': own}))
        self._switched = dict(got)
        # the enemy-priority calls, each once in script order (bench 11-10 checks/engine_aiprio.py; review 1122ss #2)
        calls = self.settings.ai_priorities.get(self.player, [])
        for enemy, n, *foes in calls[getattr(self, '_prio_seen', 0):]:
            if enemy is None:       # SET_FAVORED_ENEMY's clear (sim.py, A 220 bench engine_aifav: the table emptied)
                self.ai.tell(Command('enemy priorities', {'n': 0}))
                continue
            if enemy == '*':        # SET_ALL (act_player): the enemies when the action ran (review vv)
                self.ai.tell(Command('enemy priorities', {'n': n, 'enemies': list(foes[0])}))
                continue
            self.ai.tell(Command('enemy priority', {'player': enemy, 'n': n}))
        self._prio_seen = len(calls)

    def base_of(self, player):
        ys = [b for b in self.world.living() if b.owner == player and 'STRUCTURE' in b.kinds and not b.scenery]
        y = next((b for b in ys if 'CONSTRUCTION_YARD' in b.kinds), ys[0] if ys else None)
        return (y.x, y.y) if y else None

    def expansion_candidates(self, heuristic, origin):
        """D104: select a base before choosing its nearest eligible ore.

        INFERRED adapter: initial yards supply base centres, map OreNodes are
        state-2 entries (observed only for the aiexp fixtures). Dynamic table
        registration, occupancy/flags and death/capture remain gaps.
        """
        selection = heuristic.base_selection
        if (selection is None or selection.preferred - {'MAIN_BASE', 'OLDEST_OF_TYPE',
                                                       'MOST_RECENT_OF_TYPE'}
                or selection.preferred_not - {'CAPTURED', 'MAIN_BASE', 'OLDEST_OF_TYPE',
                                               'MOST_RECENT_OF_TYPE'}
                or selection.sort_order not in ('PREFER_OLDEST', 'PREFER_NEWEST')):
            return []
        # CAPTURED cannot be resolved from current ownership. Do not claim this
        # provider tests that flag; this hypothesis covers ordinary own yards.
        tg = self.host.mod['targets']
        nodes = [b for b in self.world.living() if b.template == 'OreNode']
        anchor = self.expansion_anchor
        registered = self.expansion_initial_yards or ((anchor,) if anchor is not None else ())
        yards = [(bid, yard) for bid, yard in enumerate(registered)
                 if (yard in self.yards()
                     and not yard.scenery
                     and (getattr(yard, 'unpack_end', None) or 0) <= self.world.frame_now())]
        candidates = []
        for bid, yard in yards:
            base_types = {'MAIN_BASE'}
            # Intact initial-dual table: first/last MAIN_BASE carries its age
            # flag. Registration and reassignment after death remain INFERRED.
            # See work/re/c_bn2_report.md for the same-frame preference contrast.
            if bid == min(i for i, _ in yards):
                base_types.add('OLDEST_OF_TYPE')
            if bid == max(i for i, _ in yards):
                base_types.add('MOST_RECENT_OF_TYPE')
            candidates.append(tg.ExpansionCandidate(
                ('base', bid), yard.x, yard.y, base_id=bid,
                base_types=frozenset(base_types)))
        selected = tg.select_expansion_base(selection, candidates)
        base = next((c for c in candidates if c.base_id == selected), None)
        if base is None:
            return []
        ores = [tg.ExpansionOre(('ore', n.name), n.x, n.y, state=2,
                               occupied=False, blocked=False,
                               water=self.view.water_at(n.x, n.y)) for n in nodes]
        node = tg.select_expansion_ore(heuristic, self.view, (base.x, base.y), ores)
        return ([tg.ExpansionCandidate(node.id, node.x, node.y, base_id=selected,
                                       base_types=base.base_types, water=node.water)]
                if node is not None else [])

    def base_object(self, player):
        """states.base_object over a player's living, unpacked structures: preferred = CONSTRUCTION_YARD, rank = cost
        (INFERRED: which template bit / value the engine reads is not known)."""
        st, now = self.host.mod['states'], self.world.frame_now()
        ys = [b for b in self.world.living() if b.owner == player and 'STRUCTURE' in b.kinds and not b.scenery
              and (getattr(b, 'unpack_end', None) or 0) <= now]
        return st.base_object(ys, lambda b: 'CONSTRUCTION_YARD' in b.kinds, lambda b: self.host.cost(b.template))

    def reach(self, ai, u, point, check):
        """TacticsBlock's reach hook (PathfindingCheckType, work/re d62_b_fields.md 1): aircraft always; else
        QuickDoesPathExist = the simulator's grid of the member's surface joins it to the point (its nearest open
        cell, Ground.snap); QuickDoesAttackPathExist = to some open spot within its longest weapon's range of the
        point (INFERRED: sixteen bearings at half and nine tenths of the range stand for the engine's search)."""
        b, g = u.body, self.world.ground
        if b.surface == 'air' or not b.alive:
            return True
        here = (b.x, b.y)
        if g.can_route(b.surface, here, point):
            return True
        if check != 'QuickDoesAttackPathExist':
            return False
        r = max((w['range'] for w in b.weapons if w.get('range')), default=0.0)
        for f in (0.5, 0.9):
            for k in range(16):
                a = 2 * math.pi * k / 16
                q = (point[0] + f * r * math.cos(a), point[1] + f * r * math.sin(a))
                if g.open(b.surface, *q) and g.can_route(b.surface, here, q):
                    return True
        return False

    def carry(self, ai, t, u):
        """TeamMaker's carry hook: t's free slots if its TransportContain's PassengerFilter takes u, else 0
        (INFERRED: one slot a passenger, the relation not asked; the engine's own test is not read)."""
        return self.observe.room(t.body, u.body)

    def board(self, ai, u, t):
        """TacticsBlock's boarding order (UseTransports): u walks into the carrier t as into a house; one that cannot
        walk is not sent -- the engine's can-enter test before it sends a rider again (INFERRED, review ww #2)."""
        return _walks(u.body) and self.give('enter', u.body, target=t.body, args=(('via', 'garrison'),))[0]

    def unload(self, ai, t, at):
        """TacticsBlock's unload (UseTransports, INFERRED): the carrier t lets every rider out where it is; an aircraft
        only at the target (bench aitranst1: the Twinblade keeps its four in while it shoots the plant)."""
        return (at or 'AIRCRAFT' not in t.body.kinds) and self.give('exit', t.body)[0]

    def riding(self, ai, u, t=None):
        """TacticsBlock: 'in' when u is inside t (None: any), 'going' when sent into it and walking there (one standing
        is idle: the engine asks again whether it can get in, b1122_boarding), else None."""
        o, b = self.observe, u.body
        for state, g in (('in', o.inside(b)), ('going', o.heading(b) if _walks(b) and b.path else None)):
            if g is not None and (t is None or g is t.body):
                return state
        return None

    def reach_target(self, ai, u, target, check):
        """TeamMaker's reach hook: reach() to the target id's point (a thing in view or a Waypoint target's point);
        a target not found is not judged (True)."""
        p = self.targets.points.get(target)
        if p is not None and hasattr(p, 'x'):       # an Expansion candidate's point is a Thing (aiexpse)
            p = (p.x, p.y)
        if p is None:
            t = next((t for t in self.view.things if t.id == target), None)
            p = None if t is None else (t.x, t.y)
        return True if p is None else self.reach(ai, u, (float(p[0]), float(p[1])), check)

    def path_to_target(self, surface, template, cond):
        """ctx 'path to target' (read, work/re/l4_states.md 3): None when it cannot judge (no base of ours, no enemy
        with one); False when a spot is not found or the template has no locomotor for the condition (read, D175
        why=noloco; bench aiopath1 / aiopathr picked the PathExists="true" opening only because that draw is the
        early one below); else whether the simulator's grid of the template's surface joins the two spots.
        cond: the simulator knows only NORMAL (INFERRED: same).
        The opening draw ('make base', the AI's start not set yet) always gets None: on the bench the engine draws
        it at f4 before any base is registered and the heuristic returns "cannot judge" before it looks at the
        tester (D108 / D175 ptt rows why=early:nobase on aipathx, aipclandy; aiopwater and aiopath1 the same
        bench kind; INFERRED that every opening draw is that early). The later states do route (D108 f158)."""
        if self.ai.start is None:
            return None
        key = (surface, template, cond)
        got = self.paths.get(key)
        if got is not None and self.frame - got[0] < PATH_EVERY:
            return got[1]
        st, world = self.host.mod['states'], self.world
        mine = self.base_object(self.player)
        foes = [p for p in world.players.values() if p != self.player and world.enemy(self.player, p)]
        them = st.target_player(foes, self.base_object)
        if mine is None or them is None:
            answer = None
        else:
            stats = simunits.stats(template, world.own) if template else {'speed': None}
            if not stats.get('speed'):
                answer = False                                   # read (D175 why=noloco): no locomotor -> no way
            else:
                grid = 'water' if surface == 'Water' else 'ground'   # read: cell type Water 7 / Land 0
                ok = lambda p: world.ground.open(grid, *p)           # noqa: E731
                theirs = self.base_object(them)
                a = st.spot((mine.x, mine.y), ok, self.path_rng)
                b = st.spot((theirs.x, theirs.y), ok, self.path_rng)
                answer = a is not None and b is not None and world.ground.route(stats['surface'], a, b) is not None
        self.paths[key] = (self.frame, answer)
        return answer

    def tid(self, b):
        """The model's Thing id of b: one an object, by its serial (11-19 same-name sweep S6: by name, a building made
        again under the name of one the AI saw took the old one's id, and its attacks, captures and garrisons)."""
        if b.serial not in self.ids:
            self.ids[b.serial] = len(self.ids) + 1
        return self.ids[b.serial]

    def body_of(self, tid):
        """The object the AI gave Thing id `tid`, while the world still has it (under its name, dead or not, as
        before); None once it is gone or another object holds its name."""
        serial = next((k for k, v in self.ids.items() if v == tid), None)
        b = self.observe.by_serial(serial) if serial is not None else None
        return b if b is not None and self.world.bodies.get(b.name) is b else None

    def hunt_target(self, serial):
        """The target the AI recorded for its unit `serial` (the hunt state's, set by a team's attack order), or None:
        Unit.in_combat's last resort when the unit holds no target of its own."""
        state = self.__dict__.get('_hunt_goals', {}).get(serial)
        return state.target if state is not None else None

    def engine_team_names(self):
        """{engine name: model team key}: the name table the engine builds once when the AI is made -- every strategic
        state x every tactic (index a) x every TeamTemplate of it (index b) is '<state>_<Tactic=>_<a>_<b>' (read, A
        round 96 / 99 in work/re: the tactic's TYPE, never its id; bench 11-07..11-11 checks/engine_aiskirm.py g:
        LandDefense_MEDIUM_StaticDefense_0_0 answers, ..._Defense_0_0 never does). The slot (MaxTargets copy) is not in
        the name. INFERRED: a counts every tactic of the state, whatever its Difficulty; the state's name is its
        definition id (the same as the personality's id in every SDK personality the benches run)."""
        if self._team_names is None:
            self._team_names = {}
            for c in self.ai.states.choices:
                st = self.host.data.states[c.target]
                for a, tac in enumerate(st.tactics):
                    for b in range(len(tac.teams)):
                        word = TACTIC_NAME_WORDS.get(tac.kind, tac.kind)
                        self._team_names.setdefault(f'{st.id}_{word}_{a}_{b}', (c.key, tac.id, b))
        return self._team_names

    def team_named(self, team):
        """Sim.team_names for this AI player: (exists, living members) of a team the scripts name, None when the name
        is not this AI's. The pool 'defaultSkirmishTeam<player>' (read, A round 96) is always there and holds the
        player's movers on no model team (INFERRED: harvesters and units in a garrison too -- the bench reads the
        pool's CAN_ATTACK members only). A strategic-state name is there while the model has a team of that key; of
        several (the state's slots share the name) the OLDEST answers, the lowest copy of those made together
        (INFERRED, as Sim.members' reinforcement instances; bench 11-11 aiskirm:m: LandDefense_MEDIUM _0_0 reads a
        steady 8 s125-128 while the model's two other slots' gathering teams expire and are made again every 5 s
        around the started one). Any other '<...>_<a>_<b>' name of this player no body is on (a
        tactic id, an index the table lacks) the engine never finds: absent."""
        owner, _, bare = team.rpartition('/')
        if owner and owner != self.player:
            return None
        if bare == f'defaultSkirmishTeam{self.player}':
            held = {id(u) for t in self.ai.teams.teams.values() for u in t.members}
            return True, [b for b in self.living() if b.owner == self.player and 'STRUCTURE' not in b.kinds
                          and b.speed > 0 and id(self.wrappers.get(b.serial)) not in held]
        key = self.engine_team_names().get(bare)
        if key is None:
            parts = bare.rsplit('_', 2)
            if not (owner and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit()) or \
                    any(simworld.same_team(b.team, team) for b in self.world.living()):
                return None
            return False, []
        teams = [t for k, t in self.ai.teams.teams.items() if k[:3] == key]
        if not teams:
            return False, []
        first = min(teams, key=lambda t: (-1 if t.made is None else t.made, t.copy))
        return True, [u.body for u in first.members if u.body.alive]

    def living(self):
        """What the AI perceives: the world's living bodies but SpawnBehavior's slaves (a war factory's repair drones,
        AIRCRAFT NOT_AUTOACQUIRABLE SUMMONED). INFERRED from the bench: aiskirm (a/c/i-p) and aiskvinf z were read
        with the player's map-placed war factory and its 3 drones up, and the AI built, ranked and attacked as if
        they were not there; since sim.py spawns them (Codex E 7b9bb57) counting them turned the Peacekeeper's
        expected efficiency against conscripts 0.033 -> 1e-5 (nothing it has hits them) and moved the Cleanup
        attack. Whether the engine's unit category and the target scan skip slaves (work/re/l4_efficiency.md) is NOT READ."""
        return self.world.living(unspawned=True)

    def foes(self):
        """The players this one takes as enemies now (Sim.enemy)."""
        w = self.world
        return frozenset(p for p in w.players.values() if p != self.player and w.enemy(self.player, p))

    def look(self, frame):
        """The view's things (living bodies, including garrisonable scenery, but not other scenery or slaves; the whole map,
        INFERRED) and who got hurt. Rebuilt once a DT tick (bodies move and fight once a tick)."""
        world, tg = self.world, self.host.mod['targets']
        if self.seen_t == world.t:
            return
        self.seen_t = world.t
        # the enemies follow the relations as they change, no action needed: bench A274 aiallflip, the build picks
        # count s5 from the first pass after PLAYER_RELATES_PLAYER turns it enemy (engine_aiflip)
        self.view.enemies = self.foes()
        things = []
        for b in self.living():
            # NeutralGarrison's native candidate scan includes retail map houses
            # (aigarron/off); scenery is a placement category, not ineligibility.
            # Other scenery stays outside the target view. Full occupancy and
            # containment eligibility remain gaps; see work/re/c_garrison_report.md.
            if b.scenery and 'GARRISON' not in b.kinds:
                continue
            i = self.tid(b)
            if b.hp < self.hp.get(i, b.hp):
                self.hurt_at[i] = frame
            self.hp[i] = b.hp
            owner = b.owner if b.owner != simworld.CIV else ''
            things.append(tg.Thing(i, owner, b.template, frozenset(b.kinds), frozenset(b.status), b.x, b.y,
                                   water=b.surface == 'water', value=float(self.host.cost(b.template)),
                                   hits=simrange.hits(b.weapons) if b.weapons else frozenset(),
                                   under_attack=frame - self.hurt_at.get(i, -10 ** 9) <= 2 * FPS,
                                   name=b.name))                    # script name (NamedObject)
        self.view.things = things
        if 'targets' in self.host.blocks:
            # the read target types measure from the AI base centre, which the engine re-averages every few frames over
            # the player's living units, structures not counted (none: a point the brain keeps, INFERRED the yard);
            # work/re/b1121_mindist.md
            units = [t for t in things if t.owner == self.player and 'STRUCTURE' not in t.kindof]
            us = [(t.x, t.y) for t in units]
            self.targets.home = (sum(p[0] for p in us) / len(us), sum(p[1] for p in us) / len(us)) if us else self.home
            # ThreatToWater's samples are the units of mine afloat now (or submerged, INFERRED); with none every
            # water threat is 0 and the first candidate wins (work/re/b1121_water.md; bench aiwaterthreat: near)
            wet = any(t.water or 'SUBMERGED' in t.status for t in units)
            self.view.own_domains = frozenset({'ground', 'air', 'water'} if wet else {'ground', 'air'})
        if self.base is not None:
            self.base.buildings = tuple(t.id for t in things if t.owner == self.player and 'STRUCTURE' in t.kindof)

    def facts(self):
        """The ctx the strategic states read, from the world."""
        mine = [b for b in self.living() if b.owner == self.player]
        building = set()
        for t in [j['template'] for q in self.yard_q.values() for j in q] + self.unit_q:
            building |= self.host.kinds(t)
        near = functools.partial(self.enemy_near, tuple(self.home))     # a partial, not a closure: the AI's
        foes = sorted(self.view.enemies)                                # snapshot keeps it (simaisnap)
        # TimeSinceLastExpansion's clock restarts as an outpost of its own comes and keeps that frame (bench ailastx200:
        # the miner's unpack f1061, the base f1070, the Time=150s team at f3326 = ailastx50's f2261 + 1065; which of
        # the two frames, and an outpost lost, INFERRED)
        self.last_expansion = max([self.last_expansion] + [round(b.made_at * FPS) for b in mine if 'OUTPOST' in b.kinds])
        out = {'flags': self.host.flags(self.player), 'has': {b.template for b in mine}, 'building': building,
               'last expansion': self.last_expansion,
               'enemy nearby': near,
               # ObjectOfTypeExists by the filter's Relationship (bench aihoe*): the enemies' / allies' / neutral's
               'has enemy': {t.template for t in self.view.things if t.owner in self.view.enemies},
               'has ally': {t.template for t in self.view.things
                            if t.owner and t.owner != self.player and t.owner not in self.view.enemies},
               'has neutral': {t.template for t in self.view.things if not t.owner},
               'kindof': self.host.kinds,                # an ObjectFilter's KindOf Include / Exclude (D61 3)
               'harvesters': sum('HARVESTER' in b.kinds for b in mine),               # INFERRED category 0x14
               'money': self.money_in,          # one account in the simulator
               'beacons': set(),                                                     # no beacons in the simulator
               'power advantage': self.power_advantage,
               'tech buildings': self.tech_buildings(),
               'nodes full': not self.open_nodes(miners=True),            # AllNearbyNodesFull (B208 / B210)
               'attacked': self.attacked, 'energy': self.energy,
               # the private AIPlayer.available: no income -> the budget share pays nothing (bench engine_aitower e).
               # A refinery counts: the retail one brings its own miner (SpawnBehavior SpawnOnUnpack), which the
               # simulator's skirmish runs (aiskirm) do not show -- B handoff 137
               'own income': int(any('REFINERY' in b.kinds for b in mine)) or self.income(self.player)}
        if foes:                                     # INFERRED (work/re/l4_states.md): the engine's enemy = the first of the enemies here
            out['opponent funds'] = self.observe.money().get(foes[0], 0)
            out['income'] = (self.income(self.player), self.income(foes[0]))
        if 'targets' in self.host.blocks:
            out['target'] = self.has_target
        return out

    def income(self, owner):
        """ctx 'income' (IncomeAdvantageHeuristic, read, work/re/l4_states.md: a per-player value of each side x 1/90; both
        0 -> 1, the enemy's <= 0 -> 9999): what that per-player value holds is not read -- INFERRED a rate that grows with the miners
        at work, so here the owner's harvesters while it has a refinery (only the ratio of the two sides counts)."""
        mine = [b for b in self.living() if b.owner == owner]
        if not any('REFINERY' in b.kinds for b in mine):
            return 0
        return sum('HARVESTER' in b.kinds for b in mine)

    def tech_buildings(self):
        """ctx 'tech buildings' (TechBuildingShareHeuristic, work/re/l4_states.md): (own, all, players).
        own = the player's registered set 0xc, all = the global set 2; by the SetId enum order (SDK xsd
        RegisteredObjectSetId: 0xa STRUCTURES, 0xd UNITS, 0x14 HARVESTERS as read elsewhere) those are
        PLAYER_NEUTRAL_TECH and NEUTRAL_TECH, both KindOf CAPTUREFLAG or NEUTRAL_TECH (GlobalData
        RegisteredObjectSets.xml; the player's one SAME_PLAYER). players: the game's count is not read: INFERRED the
        players owning something alive, the civilians not counted (it only matters once the player owns one)."""
        tech = [b for b in self.living() if {'CAPTUREFLAG', 'NEUTRAL_TECH'} & set(b.kinds)]
        players = {b.owner for b in self.living() if b.owner != simworld.CIV and not b.scenery}
        return sum(b.owner == self.player for b in tech), len(tech), len(players)

    def _related(self, owner, relationship):
        # an ObjectFilter's Relationship (D59 2: the ally bit takes the player itself, SAME_PLAYER only it);
        # none written: the enemies (INFERRED, EnemyNearby before its EnemyFilter was read)
        enemy, mine_ = owner in self.view.enemies, owner == self.player
        return any((r == 'ENEMIES' and enemy) or (r == 'SAME_PLAYER' and mine_) or (r == 'NEUTRAL' and not owner)
                   or (r == 'ALLIES' and owner and not enemy) for r in relationship) if relationship else enemy

    def enemy_near(self, home, distance, min_value, things=(), relationship=(), passes=None):
        """facts' 'enemy nearby' (home: the yard's point when the facts were read). passes: the EnemyFilter's
        template test (the private model's), None = every template."""
        hx, hy = home
        v = sum(t.value for t in self.view.things if self._related(t.owner, relationship)
                and math.hypot(t.x - hx, t.y - hy) <= distance and (not things or t.template in things)
                and (passes is None or passes(t.template)))
        return v > 0 and v >= min_value

    def money_in(self, account):
        """facts' 'money': the player's money, whatever the account (one account in the simulator). A method, not a
        closure, so the AI's snapshot keeps it (simaisnap)."""
        return self.observe.money().get(self.player, 0)

    def power_advantage(self, own_kindof, enemy_kindof, own_defenses, enemy_defenses):
        """ctx 'power advantage' (PowerAdvantageHeuristic, read, work/re/l4_states.md): (the enemy's time to kill all of ours,
        ours to kill all of theirs), tactics.army_time -- template health, not what is left. A side = its units of
        the KindOf (category 0xd: INFERRED every unit, armed or not) and, if asked, its defences (category 0x2e,
        no KindOf: INFERRED structures with a weapon). The enemy is one player: INFERRED the first of the enemies,
        as 'opponent funds' (the engine's list order not read, work/re/l4_states.md)."""
        foes = sorted(self.view.enemies)
        if not foes:
            return None
        tc = self.host.mod['tactics']

        def side(owner, kinds, defenses):
            kinds = set(kinds.split())
            return [b for b in self.living() if not b.scenery and b.owner == owner
                    and (b.weapons and defenses if 'STRUCTURE' in b.kinds else not kinds or kinds & set(b.kinds))]
        mine = self.fighters(side(self.player, own_kindof, own_defenses), True)
        theirs = self.fighters(side(foes[0], enemy_kindof, enemy_defenses), True)
        return tc.army_time(theirs, mine), tc.army_time(mine, theirs)

    def attacked(self, seconds):
        """ctx 'attacked' (StructureOrHarvesterUnderAttackHeuristic, work/re/l4_states.md,
        read): one of our structures (category 0xb) or harvesters (0x14) last hurt no longer than 15 x seconds
        frames ago. The program also wants the one who hurt it still there (not modelled: the simulator keeps no
        attacker)."""
        due = self.frame - FPS * seconds
        return any(t.owner == self.player and ('STRUCTURE' in t.kindof or 'HARVESTER' in t.kindof)
                   and self.hurt_at.get(t.id, -10 ** 9) >= due for t in self.view.things)

    def energy(self, relationship):
        """ctx 'energy' (EnergyHeuristic, read, work/re/l4_states.md): produced - used of us (Relationship SAME_PLAYER) or else
        of the enemy (the first, as 'opponent funds'); None = no enemy. Sim.power (EnergyProduction)."""
        if relationship == 'SAME_PLAYER':
            who = self.player
        else:
            foes = sorted(self.view.enemies)
            if not foes:
                return None
            who = foes[0]
        sup, dem = self.systems.power(who)
        return sup - dem

    def has_target(self, st):
        """ctx 'target' (states._draw): one of the state's target heuristics finds a Thing now (claims count)."""
        tg, td = self.host.mod['targets'], self.host.data_of('targets')
        table = self.ai.enemy_table             # fixed by script: tiers by score ([[]] = no enemy), as TargetsBlock
        tiers = None if table is None else tg.table_tiers(table, self.view.enemies)
        return any(tg.find(td.heuristic(hid), self.view, self.home, tiers, None, self.home) is not None
                   for hid, _ in st.targets)

    # ---- the blocks' outlets
    def hunt_arrived(self, b, state):
        """INFERRED arrival radius; D113 establishes arrival, not its tolerance."""
        t = state.pursuit
        return t is not None and math.hypot(b.x - t.x, b.y - t.y) <= b.radius

    def _crush_hook(self, simcrush):
        """TacticsBlock's crush(ai, member, foe): it can crush him; the point a crush move would go to is kept for
        the member's next order (order: a 'move' to it is that crush move, its goal not moved off the mates' spots)."""
        def crush(ai, f, foe):
            ok = simcrush.eligible(self.world, f, foe, self.observe.attachments())
            if ok:
                self.__dict__.setdefault('_crush_to', {})[f.body.serial] = tuple(map(float, foe.pos[:2]))
            return ok
        return crush

    def order(self, u, kind, arg):
        """TacticsBlock / DefenseBlock: 'move' or 'attack-move' to a point -> Sim.order_move; the point may carry a
        facing, (x, y, radians): the unit turns to it once there (the form-up slots)."""
        b = u.body
        if kind == 'hunt':
            state = self.__dict__.setdefault('_hunt_goals', {}).setdefault(
                b.serial, self.host.mod['micro'].HuntGoal())     # per object: same-name sweep S6b
            state.expire(lambda t: t is not None and t.alive,
                         arrived=self.hunt_arrived(b, state))
            if state.state != 16 or not b.alive:
                return
            t = self.body_of(arg)
            if t is None:
                return
        if self.host.record:                    # HOOKS 9: every order the blocks give, as given
            by_id = kind in ('attack', 'enter', 'hunt')
            t = self.body_of(arg) if by_id else None
            self.rec['orders'].append({'frame': self.frame, 'member': b.name, 'alive': b.alive, 'kind': kind,
                                       'target': t.name if t is not None else None,
                                       'target_id': arg if by_id else None,
                                       'point': None if by_id else (float(arg[0]), float(arg[1]))})
        if not b.alive:
            return
        if kind == 'hunt':
            state.command(t)
            self.give('attack_move', b, pos=(t.x, t.y), args=(('drop_target', True),))
            return
        if kind == 'attack':                    # the team state's 0 / 6: attack the current enemy (a Thing id)
            if getattr(b, 'unpack_here', False) and b.building is not None:
                return      # a SimpleExpansion miner armed to unpack walks on (bench aiexpb*, D157; INFERRED)
            t = self.body_of(arg)
            if t is not None:
                state = self.__dict__.get('_hunt_goals', {}).get(b.serial)
                if state is not None:
                    state.state, state.target = 26, t
                if t.owner == self.player and t in self.observe.garrisons(b, True):
                    # "attacking" one's own base defense = entering it (d133_airevk2.md 1: the team state 6's 0x210
                    # at the AI's own turret, bench aibdi0 / aibdi2)
                    self.give('enter', b, target=t, args=(('via', 'garrison'),))
                    return
                self.give('attack', b, target=t)
            return
        if kind == 'enter':                     # EnterGarrisons / EnterBaseDefenses: into a building (a Thing id)
            t = self.body_of(arg)
            if t is not None:
                if not self.host.pullback.send(b, t):   # the pullbacks (L8) give their return through the port
                    self.give('enter', b, target=t, args=(('via', 'garrison'),))
            return
        face = float(arg[2]) if len(arg) > 2 and arg[2] is not None else None
        crush = self.__dict__.get('_crush_to', {}).pop(b.serial, None)
        if kind == 'move' and crush == (float(arg[0]), float(arg[1])):     # the crush move: onto the man as he
            self.give('move', b, pos=crush, args=(('drop_target', True), ('exact', True)))  # stands (order_move)
            return
        slot = self.__dict__.get('_exp_slots', {}).get(b.name)
        if kind == 'move' and slot is not None and math.hypot(float(arg[0]) - slot[0][0],
                                                              float(arg[1]) - slot[0][1]) < 1.0:
            _, arg, face = slot                 # SimpleExpansion's formation move: this member's slot (D168)
        self.give('attack_move' if kind == 'attack-move' else 'move', b, pos=(float(arg[0]), float(arg[1])),
                  args=(('drop_target', True),) + ((('face', face),) if face is not None else ()))

    def give(self, kind, b, **kw):
        """One order of the AI's to its unit b through the command port (R3 13f-1): by serial, as the AI picked it
        (a script reference of the same name cannot take its place, as the proxy's: review 11-19 h #1). (ok, why)."""
        args = (('objects', 'serial'),) + kw.pop('args', ())
        t = kw.get('target')
        if t is not None and not isinstance(t, str):    # an object the AI picked: by serial, its name for the record
            kw['target'], args = t.name, args + (('target_serial', t.serial),)
        return self.commands.do(Command(kind, f'ai:{self.player}', units=(b.serial,), args=args, **kw))

    def expansion_slots(self, team, p):
        """SimpleExpansion's formation move to node p (EXPANSION_ROW): {member name: (p, slot, facing)}, every living
        member ordered to its slot once."""
        live = [u.body for u in team.members if u.body.alive]
        if not live:
            return {}
        foes = [t for t in self.living() if not t.scenery and t.owner != self.player and t.owner in self.view.enemies
                and any(self.observe.can_hit(w, t) for b in live for w in b.weapons)]
        o = min(foes, key=lambda t: math.hypot(t.x - p[0], t.y - p[1]), default=None)
        if o is not None:
            a = math.atan2(o.y - p[1], o.x - p[0])
        else:
            cx, cy = sum(b.x for b in live) / len(live), sum(b.y for b in live) / len(live)
            a = math.atan2(p[1] - cy, p[0] - cx)
        fx, fy = math.cos(a), math.sin(a)
        back = [b for b in live if not b.weapons]           # the miner: the row behind
        row = [b for b in live if b.weapons] or back
        back = [b for b in back if b not in row]
        slots = {}
        for i, b in enumerate(row):
            s = (i - (len(row) - 1) / 2) * EXPANSION_ROW
            slots[b.name] = (p, (p[0] - s * fy, p[1] + s * fx), a)
        for i, b in enumerate(back):
            s = (i - (len(back) - 1) / 2) * EXPANSION_ROW
            slots[b.name] = (p, (p[0] - EXPANSION_ROW * fx - s * fy, p[1] - EXPANSION_ROW * fy + s * fx), a)
        return slots

    def fight(self, ai, team):
        """TacticsBlock's fight hook (the team state, work/re/l4_gather.md): the members and every living enemy body as
        Fighters; rate = the sum of the dps of the weapons that can hit the other, times its armour (Sim.can_hit /
        the firing rule); vision = its VisionRange alone (Body.sight, work/re/l2_vision.md; not the shroud clearing range)."""
        foes = [b for b in self.living()
                if not b.scenery and b.owner != self.player and b.owner in self.view.enemies]
        live = [u for u in team.members if u.body.alive]
        mem = self.fighters([u.body for u in live])
        for f, u in zip(mem, live):
            f.unit = u                          # the member it stands for (state 2's pick, Crush, ReverseMove)
            t = self.ordered_aim(u.body)
            f.aim = None if t is None else (t.x, t.y)
        return mem, self.fighters(foes)

    def act(self, team, kind, thing):
        """TacticsBlock's act hook (go-and-act family): True once the tactic's thing is done. Engineer: every living
        member the target's EngineerContain admits is sent to capture it (Sim.order_capture; the capture itself is
        Sim.capture_due, the engineer consumed); done once the target is the AI's, or once it is gone or no member
        is left to take it (INFERRED: what the engine does then not read). Bench aiskirm:et 2026-11-13: the engineer
        at the derrick s216, the derrick s1's and the team gone s222 (line A round 204). The other act kinds keep
        the block's default (done on arrival).
        SimpleExpansion is approach's (TacticsBlock.EN_ROUTE); a model without that hook falls back to it here with
        no Distance (driven to the node and unpacked there, the script's path)."""
        if kind == 'SimpleExpansion':
            return self.approach(team, kind, thing, None)
        if kind not in ('Engineer', 'GarrisonBuilding'):
            return True
        t = self.body_of(thing.id) if thing is not None else None
        if t is None or not t.alive or t.owner == self.player:
            return True
        if kind == 'GarrisonBuilding':          # every living member into the house (INFERRED: bench aigarrbld,
            live = [u for u in team.members if u.body.alive]    # the shop the AI's at s56.7 with both alive)
            for u in live:
                if u.body.goal is not t:
                    self.order(u, 'enter', thing.id)
            return not live
        live = [u.body for u in team.members if u.body.alive and self.systems.engineer_entry(u.body, t)]
        for b in live:
            if b.mode != 'capture' or b.goal is not t:
                self.give('capture', b, target=t)
        return not live

    def approach(self, team, kind, thing, distance):
        """TacticsBlock's approach hook (EN_ROUTE kinds, every think from the go order on). SimpleExpansion: each
        living member with an unpack button (the AlliedMiner, the state's CreateUnits) is armed once to unpack where
        it stands the first frame it is within `distance` (Tactic.Distance) of the Expansion node, while the team's
        move order walks it on (Sim.order_unpack here=True, send=False); a walk that never brings it that close
        never unpacks. Done once an armed member is no longer armed (unpacked or dead) and none is left armed, or
        when no member can unpack. Bench D round 156 (missions/aisimpleexp_bench.py aiexpb*): 400 -> unpack f995 at
        397 from the node, 200 -> f1061 at 194, 50 -> the walk ends 98 away, no unpack to f1936. INFERRED: the done
        rule (the team is empty from f1070 on the bench, the miner replaced itself)."""
        if kind != 'SimpleExpansion' or thing is None:
            return True
        p = (float(thing.x), float(thing.y))
        made = self.__dict__.setdefault('_exp_teams', [])   # [(team, node)], found by identity (a Team is not
        k = next((k for k, (t, _) in enumerate(made) if t is team), None)   # hashable; the snapshot keeps it by
        if k is None or made[k][1] != p:        # its snapshot_key); the go order's formation split, once a node (D168)
            if k is None:
                made.append((team, p))
            else:
                made[k] = (team, p)
            slots = self.expansion_slots(team, p)
            self.__dict__.setdefault('_exp_slots', {}).update(slots)
            for u in team.members:
                if u.body.alive and u.body.name in slots:
                    self.order(u, 'move', p)
        armed = was = False
        ordered = self.__dict__.setdefault('_unpack_ordered', set())  # the serials of the members armed once
        for u in team.members:
            b = u.body
            if b.serial in ordered:
                was = True
            if not b.alive:
                continue
            if b.building is not None and b.serial in ordered:
                armed = True
            elif b.serial not in ordered and \
                    self.give('unpack', b, pos=p, args=(('stand', distance), ('here', distance is not None),
                                                        ('send', distance is None)))[0]:
                ordered.add(b.serial)
                was = True
                armed = b.building is not None or armed
        return not armed if was else True

    def fighters(self, bodies, template=False):
        """Bodies as tactics.Fighter (fight's rule: rate by Sim.can_hit and the armour, vision = VisionRange).
        template: the rate counts the weapons the AI's template-against-template rate takes (simunits.template_weapons:
        one per slot, none that needs an upgrade or an ObjectStatus; engine line B round 227, read), not the ones
        the body holds -- the expected efficiency's."""
        tc, world, observe = self.host.mod['tactics'], self.world, self.observe
        memo = self.__dict__.setdefault('_template_guns', {})

        def guns_of(b):
            if not template:
                return b.weapons
            if b.template not in memo:
                memo[b.template] = simunits.template_weapons(b.template, world.own)
            return b.weapons if memo[b.template] is None else memo[b.template]

        def rate_of(b):
            guns = guns_of(b)

            def rate(o):
                t = o.body
                # each damage part its own armour percent (simunits ai_parts: the AI sums a weapon's nuggets and
                # its warhead's, l4_efficiency.md 3, read); a weapon without parts as fight does
                return sum(sum(d * simunits.percent(t.armor, ty) / 100.0 for d, ty in w['ai_parts'])
                           if w.get('ai_parts') else w['dps'] * simunits.percent(t.armor, w['type']) / 100.0
                           for w in guns if observe.can_hit(w, t))
            return rate

        def fighter(b, i):
            # reach = the engine's longest-range read: the weapon's AttackRange less 5 (sim.Sim.reach_of), no radii
            # (work/re/d131_triggers.md 1, read; its height and range-bonus terms not modelled); a member with no weapon 0
            f = tc.Fighter(i, (b.x, b.y), b.hp, b.max_hp, b.speed,
                           max((simrange.reach_of(w) for w in b.weapons if w.get('range')), default=0.0),
                           b.sight or b.vision,
                           'STRUCTURE' in b.kinds, rate_of(b))
            f.body = b
            f.template, f.kinds = b.template, frozenset(b.kinds)
            f.radius = b.radius                     # the search circle reaches its edge (work/re d149, bench airett)
            f.can_fire = lambda other: any(observe.can_hit(w, other.body) and simrange.in_range(b, other.body, w)
                                           for w in b.weapons)
            return f
        return [fighter(b, self.tid(b)) for b in bodies]

    def garrisons(self, u, own_defenses):
        """TacticsBlock's houses / defenses hooks: [(id, (x, y))] u could be sent into, the list's order; [] when it
        cannot garrison (INFANTRY, not SKIRMISH_AI_DONT_GARRISON: template flag bits, work/re/l4_gather.md). Full ones
        are listed too (bench aibdpre)."""
        b = u.body
        if not b.alive or 'INFANTRY' not in b.kinds or 'SKIRMISH_AI_DONT_GARRISON' in b.kinds:
            return []
        return [(self.tid(g), (g.x, g.y)) for g in self.observe.garrisons(b, own_defenses)]

    def busy(self, team):
        return any(self.observe.fighting(u.body) for u in team.members)

    def stand(self, team, p, r, outer):
        """Consume the model's aesthetics gates; formation member destinations remain a gap.
        INFERRED (D round 137): no aesthetics before 'make base' -- its idle clock starts at the AI's start. A
        FriendlyStructure team forms before the wake (bench aibdi*, f21), yet aidist2000's guardian (wake s10, 10 s
        PatrolIdleTime) is still in the 900 circle at s20 on the bench."""
        if self.ai.start is None:
            return
        # EngineModel is optional and versioned separately from this repository.
        if not hasattr(self.tactics, 'stand'):
            n = max(1, len(team.members))
            for k, u in enumerate(team.members):
                a = 2 * math.pi * k / n
                self.order(u, 'move', (p[0] + r * math.cos(a), p[1] + r * math.sin(a)))
            return
        members, foes = self.fight(self.ai, team)
        harvesters = [(b.x, b.y) for b in self.living()
                      if b.owner == self.player and 'HARVESTER' in b.kinds]
        run_of = getattr(self.tactics, 'run_of', None)      # a model before 11b-4c keyed its runs by id(team)
        run = run_of(team) if run_of is not None else self.tactics.runs.get(id(team))
        if run is None:
            return
        state = self.tactics.state_of(self.ai, team.state)
        attrs = self.defense.attrs
        self.tactics.stand(team, p, r, outer, self.frame, members, foes, harvesters,
                           round(float(attrs.get(state, run.tactic.id, 'PatrolIdleTime', '10')) * 15),
                           float(attrs.get(state, run.tactic.id, 'MinDistanceFromHarvester', '300')))

    def radius_of(self, tid):
        b = self.body_of(tid)
        sh = self.world.blocks(b) if b else None
        return sh[2] if sh and len(sh) == 3 else 40.0

    def ordered_aim(self, b):
        """Fighter.aim (ReverseMove's gate 3: the target the member is really attacking, work/re/d131 1):
        its ordered or chased living enemy, else None -- no nearest-in-range fallback (bench airevt1: members
        standing in a turret's range with no target of their own never backed off)."""
        if not b.alive:
            return None
        state = self.__dict__.get('_hunt_goals', {}).get(b.serial)
        if state is not None:
            return state.target if state.target is not None and state.target.alive else None
        return next((t for t in (b.goal, getattr(b, 'chase', None))
                     if self.observe.is_thing(t) and t.alive and t.owner in self.view.enemies), None)

    def aim_of(self, b, reach):
        """The unit's current target for the micro (work/re/l4_micro_heur.md; RUSH_ATTACK reads it): its ordered or
        chased enemy, else the nearest living enemy within its longest weapon range
        (INFERRED legacy proxy). Hunt members instead keep a persistent object goal."""
        state = self.__dict__.get('_hunt_goals', {}).get(b.serial)
        if state is not None:
            return state.target if state.target is not None and state.target.alive else None
        for t in (b.goal, getattr(b, 'chase', None)):
            if self.observe.is_thing(t) and t.alive and t.owner in self.view.enemies:
                return t
        near = [(math.hypot(t.x - b.x, t.y - b.y), k, t) for k, t in enumerate(self.living())
                if not t.scenery and t.owner in self.view.enemies]
        near = [n for n in near if n[0] - n[2].radius <= reach]
        return min(near)[2] if near else None

    def micro_team(self, ai, frame, team):
        mc, sp = self.host.mod['micro'], self.host.mod['specials']
        powers = self.host.data_of('unit powers')
        units = []
        # the view's units -> the objects they were made of: the manager fires / moves this same batch right after
        # (MicroBlock.tick), so the outlets take the object, not a lookup of its name (same-name sweep S6b)
        self._micro_units = seen = []
        # the model keys its plans / dodges by name: two members of one name are told apart by serial (review 11-19
        # q P3 #3); a name alone in the team stays as it is -- unless an earlier object of this brain's view held it
        # (same-name sweep 11-19b N01: the model keeps a dodge job by (unit name, threat name), so a member or a
        # beacon made again under the old one's name got the old one's flight point)
        names = Counter(u.body.name for u in team.members)
        view = lambda b: self.view_name(b, names[b.name] > 1)  # noqa: E731
        for u in team.members:
            b = u.body
            reach = max((w.get('range') or 0.0 for w in b.weapons), default=0.0)
            t = self.aim_of(b, reach)
            toggles = []
            if 'Command_ToggleArmorUp' in self.host.command_set(b.template):
                cache = self.__dict__.setdefault('_miner_toggles', {})
                if b.template not in cache:
                    inner = next((inner for h, inner in simunits._blocks(self.world.xml_of(b.template),
                                  'ToggleStatusSpecialAbilityUpdate') if simunits._attr(h, 'SpecialPowerTemplate') ==
                                  'SpecialPower_ToggleArmorUp'), '')
                    cache[b.template] = mc.parse_toggle(ET.fromstring('<update>' + inner + '</update>'))
                toggles = cache[b.template]
            units.append(mu := mc.Unit(view(b), (b.x, b.y), b.hp, b.max_hp,
                                 [powers[c] for c in self.host.command_set(b.template)
                                  if c in powers and simmicro.ready(self.world, b, c)],
                                 target=None if t is None else sp.Thing((t.x, t.y), t.kinds, 0, name=t.name),
                                 weapon_range=reach, cost=self.host.cost(b.template),
                                 damage=lambda behind, ahead, b=b: self.observe.expected_damage(b, behind, ahead, now=frame),
                                 toggles=toggles, toggle_index=int(b.armor_up)))
            seen.append((mu, b))
        enemies = [sp.Thing((t.x, t.y), t.kindof, int(t.value), name=str(t.id)) for t in self.view.things
                   if t.owner in self.view.enemies]
        threats = []
        for b in self.living():
            if 'SKIRMISH_AI_ATTEMPT_TO_DODGE' not in b.kinds or b.owner not in self.view.enemies:
                continue
            # Bounded native-beacon contract: reject unsupported filters rather than
            # treating all enemies as threats. Multi-threat selection remains a gap.
            root = ET.fromstring(self.world.xml_of(b.template))
            info = next((e for e in root.iter() if e.tag.endswith('}SkirmishAIInformation')
                         or e.tag == 'SkirmishAIInformation'), None)
            if info is None or 'DodgeSafetyDistance' not in info.attrib:
                continue
            filt = next((e for e in info if e.tag.endswith('DodgeWithUnits')), None)
            if filt is None or dict(filt.attrib) != {'Rule': 'ALL', 'StatusBitFlagsExclude': 'AIRBORNE_TARGET'}:
                continue
            if b.life_end is None:
                life = next((e for e in root.iter() if e.tag.endswith('LifetimeUpdate')), None)
                if life is None or life.get('MinLifetime') != life.get('MaxLifetime'):
                    continue
                # Retail fixed lifetime was not loaded by simunits' bounded reader.
                # INFERRED first-seen birth frame; Sim owns expiry/deletion thereafter.
                die = frame + mc.frames(mc.seconds(life.get('MinLifetime')))
                self.give('set_lifetime', b, args=(('die_frame', die),))
            eligible = frozenset(view(u.body) for u in team.members if u.body.alive
                                 and 'AIRCRAFT' not in u.body.kinds
                                 and not (getattr(u.body, 'z', None) or 0) > 0)
            threats.append(mc.DodgeThreat(self.view_name(b), (b.x, b.y),
                                          float(info.get('DodgeSafetyDistance')),
                                          b.owner, b.life_end - frame, eligible))
        return mc.Team(units, enemies=enemies, threats=threats)

    def first_of(self, b):
        """Whether b is the first object the micro view met under its name (`_view_names` name -> that serial)."""
        return self.__dict__.setdefault('_view_names', {}).setdefault(b.name, b.serial) == b.serial

    def view_name(self, b, twins=False):
        """b's name in the micro view: `name#serial` for one of twins, one not first_of its name, or a name with a #
        in it (so a thing named `lead#1` never reads as lead's serial 1: review 11-19 w #6), else the name."""
        first = self.first_of(b)            # asked every time: it marks the name's first holder
        return f'{b.name}#{b.serial}' if twins or not first or '#' in b.name else b.name

    def micro_body(self, u):
        """The object micro_team made the view's unit u of (None for a unit of no view of this brain's)."""
        return next((b for mu, b in self.__dict__.get('_micro_units', ()) if mu is u), None)

    def dodge_move(self, ai, key, unit, point):
        """E micro threat outlet (coordinator authorization); ordinary movement path."""
        b = self.micro_body(unit)
        member = next((u for u in ai.teams.teams[key].members if u.body is b), None) if b else None
        if member is not None:
            self.order(member, 'move', point)

    def fire_unit(self, ai, key, u, info):
        """Execute toggles and C's bounded self-power bridge; otherwise record intent."""
        self.fired.append((self.frame, key, u.name, info.command))
        b = self.micro_body(u)
        if b and b.owner == self.player and self.give('toggle', b, args=(('button', info.command),))[0]:
            self.world.note('AI', f'{u.name} 执行 {info.command}')
            return
        if b and b.owner == self.player and self.give('power', b, power=info.command, args=(('via', 'micro'),))[0]:
            state = self.__dict__.get('_hunt_goals', {}).get(b.serial)
            if (state is not None and state.state == 33
                    and info.command == simmicro.COMMAND):
                state.charge_finished()
                if state.pursuit is not None and state.pursuit.alive:
                    self.give('attack_move', b, pos=(state.pursuit.x, state.pursuit.y), args=(('drop_target', True),))
                else:                           # the charge's target dropped, no order after it
                    self.give('attack', b, target='', args=(('goal_only', True),))
            return
        self.world.note('AI', f'{self.world.who(self.player)} 微操想用 {info.command}（{u.name}；模拟器未接技能）')

    # ---- what the AI asks of the world
    def is_structure(self, t):
        return 'STRUCTURE' in self.host.kinds(t)

    def factories(self):
        """Sim.factories with the menus cached (simunits.menu parses the XML on each call)."""
        return [b for b in self.world.living() if b.owner == self.player and 'STRUCTURE' in b.kinds and not b.scenery
                and self.host.menu(b.template)]

    def yards(self):
        """The player's yards handed to the AI: on no map team (bench aistart:a, no library, woken by SKIRMISH_AI_START
        alone: the yard left on teamSoviet_1 builds nothing in 60 s; aistartx:a, the yard handed by UNIT_AI_TRANSFER
        first, opens as aiskirm)."""
        return [b for b in self.world.living() if b.owner == self.player and 'CONSTRUCTION_YARD' in b.kinds
                and not b.team]

    def queue_of(self, template):
        """fn(yard) -> the yard_q key a structure goes in: a base defence (FS_BASE_DEFENSE) in the yard's own
        defence queue beside the structures' (bench 2026-11-10 engine_aiskirm v: aiskacd's two towers, s49 / s69,
        leave the opening's structures on aiskacp's timeline, 4th s50 -> s49, 5th s71 -> s69 -- INFERRED a second
        queue, the sidebar's defence tab); anything else in the yard's own. Keyed by the yard object's serial, not
        its name (review 11-19 q P2 #2: by name, a yard made again under a dead one's name took over its orders).
        INFERRED, no bench reading: a yard packed and unpacked is a new object under the old name, so its queue
        ends with the packing."""
        if 'FS_BASE_DEFENSE' in self.host.kinds(template):
            return lambda y: (y.serial, 'defense')
        return lambda y: y.serial

    def put_yard_jobs(self, yard, rows):
        """SimAI.put_yard_jobs for a yard of this brain's: its two queues made the rows' (as build queues a job, at the
        row's progress, paid and full); a why for each row left out (not a structure), None for one placed."""
        out = []
        for key in (yard.serial, (yard.serial, 'defense')):
            self.yard_q.pop(key, None)
        for row in rows:
            t = row['template']
            if not self.is_structure(t):
                out.append(f'a yard builds no {t} (not a structure)')
                continue
            cost, secs = simunits.production(t, self.world.own)
            self.yard_q.setdefault(self.queue_of(t)(yard), []).append(
                {'template': t, 'cost': cost, 'frames': max(1, int(round(secs * FPS))), 'progress': row['progress'],
                 'paid': row['paid'], 'full': row['full']})
            out.append(None)
        return out

    def present(self, serial):
        """The object of `serial` while it is alive and still the one the world holds under its name; None once it
        is gone, dead, or another object took its name (Sim.add over a living one)."""
        b = self.observe.by_serial(serial)
        return b if b is not None and b.alive and self.world.bodies.get(b.name) is b else None

    def build_offers(self, ai, frame, templates):
        """AIPlayer.build_offers: of `templates`, the structures the AI could order now -- a yard, can_build, and
        nothing waiting in that template's queue (one order a queue at a time, INFERRED) -- as (template, cost,
        kinds)."""
        world, systems, ys = self.world, self.systems, self.yards()
        if not ys or self.player in self.settings.base_construction_disabled:   # bench aibgate:a (A269)
            return []
        out = []
        for t in templates:
            if not self.is_structure(t) or not systems.can_build(self.player, t):
                continue
            q = self.queue_of(t)
            if all(self.yard_q.get(q(y)) for y in ys):
                continue
            out.append((t, simunits.production(t, world.own)[0], frozenset(self.host.kinds(t))))
        return out

    def power_now(self, ai, frame):
        """AIPlayer.power: (supply, demand) as Sim.power (a structure still unpacking on neither side), the energy of
        everything in the AI's yard queues (built or not, till it is placed), and the structure templates it owns."""
        world, systems = self.world, self.systems
        sup, dem = systems.power(self.player)
        queued = sum(simunits.energy(j['template'], world.own) for q in self.yard_q.values() for j in q)
        owned = {b.template for b in world.living() if b.owner == self.player and 'STRUCTURE' in b.kinds}
        return sup, dem, queued, owned

    def build(self, template):
        """AIPlayer.builder: True once the order is taken (queued), False when nothing of the AI's can make it now."""
        world, systems = self.world, self.systems
        if self.is_structure(template):
            ys = self.yards()
            if not ys or self.player in self.settings.base_construction_disabled \
                    or not systems.can_build(self.player, template):
                return False        # base-disabled: bench aibgate:a (A269), no structure order taken till enabled
            q = self.queue_of(template)
            y = min(ys, key=lambda y: len(self.yard_q.get(q(y), [])))
            cost, secs = simunits.production(template, world.own)
            self.yard_q.setdefault(q(y), []).append(
                {'template': template, 'cost': cost, 'frames': max(1, int(round(secs * FPS))), 'progress': 0.0,
                 'paid': 0, 'full': None})
            world.note('AI', f'{world.who(self.player)} 建造场排 {template}（{cost}，{secs:g} 秒）')
            return True
        if not systems.can_build(self.player, template) or \
                not any(template in self.host.menu(f.template) for f in self.factories()):
            return False
        self.unit_q.append(template)
        return True

    def upgrade_offers(self, ai, frame, upgrades):
        """AIPlayer.upgrade_offers: {upgrade: cost} of `upgrades` a structure of the AI's buys now (Sim.upgrade_sellers:
        its GameDependency met, not held, not in a queue)."""
        systems = self.systems
        return {u: simunits.upgrade_cost(u)[0] for u in upgrades if systems.upgrade_sellers(self.player, u)}

    def upgrade(self, upgrade):
        """AIPlayer.upgrader: queue the upgrade at the structure that buys it (Sim.order_build; paid as it builds)."""
        return bool(self.systems.upgrade_sellers(self.player, upgrade)) and \
            self.commands.do(Command('build', f'ai:{self.player}', player=self.player, template=upgrade))[0]

    def offers(self, ai, frame):
        """AIPlayer.offers: the units the AI's live factories can build now (Sim.offers), as teams.Offer with the unit
        builder's candidate state (work/re/l4_unitbuilder.md): 0 = an unpacked factory that makes it has an empty queue and nothing of
        unit_q it would take, 1 = all such factories are busy; a unit only unpacking factories make is left out
        (state 2, cannot build now)."""
        tm = self.host.mod['teams']
        systems, frame = self.systems, self.frame
        ready = [f for f in self.factories() if frame >= self.made.get(f.serial, -10 ** 9) + self.host.unpack(f.template)]
        out = []
        for t, _, _ in systems.offers(self.player):
            fs = [f for f in ready if t in self.host.menu(f.template)]
            if not fs:
                continue
            idles = tuple(f.name for f in fs if not systems.busy(f)
                          and not any(q in self.host.menu(f.template) for q in self.unit_q))
            idle = bool(idles)
            kinds = self.host.kinds(t)
            surface = 'AIR' if 'AIRCRAFT' in kinds else 'AMPHIBIOUS' if 'AMPHIBIOUS' in kinds else \
                'WATER' if 'SHIP' in kinds else 'LAND'
            out.append(tm.Offer(t, frozenset(kinds), surface, state=0 if idle else 1,
                                standard=self.host.standard(t), cost=self.host.cost(t),
                                **({'facilities': idles} if 'facilities' in tm.Offer.__dataclass_fields__ else {})))
        return out

    def near_factory(self, ai, frame, template, distance):
        """AIPlayer.near_factory (BuildEntry.BlockIfThingNearFactory, work/re/d59_b_fields.md 2): for each ready,
        idle factory of the player that builds `template` (as offers' state 0), the living things (the factory
        itself too, scenery not) whose 2D distance to its centre <= distance + their radius, each with its
        relationship to the player: SAME_PLAYER, NEUTRAL (the civilian player or a Neutral relation), ENEMIES,
        else ALLIES. bench 2026-11-12 engine_aiskirm y aiskblkn / aiskblkf / aiskblkr."""
        world, systems = self.world, self.systems
        ready = [f for f in self.factories() if self.frame >= self.made.get(f.serial, -10 ** 9)
                 + self.host.unpack(f.template) and template in self.host.menu(f.template)
                 and not systems.busy(f) and not any(q in self.host.menu(f.template) for q in self.unit_q)]
        if not ready:
            return []
        live = [b for b in self.living() if not b.scenery]

        def rel(owner):
            if owner == self.player:
                return 'SAME_PLAYER'
            if owner == simworld.CIV or world.relations.get((self.player, owner)) == 'Neutral':
                return 'NEUTRAL'
            return 'ENEMIES' if owner in self.view.enemies else 'ALLIES'
        return [[(b.template, rel(b.owner)) for b in live
                 if math.hypot(b.x - f.x, b.y - f.y) <= distance + (b.radius or 0.0)] for f in ready]

    def expected(self, ai, frame, templates):
        """AIPlayer.expected: {template: tactics.expected_efficiency} (work/re/l4_efficiency.md). Mine =
        the AI's living units (category 0xd: INFERRED every non-structure, harvesters too); foes = every enemy
        player's units, weight UnitBuilderEnemyNearbyMultiplier within UnitBuilderEnemyNearbyDistance of the AI's
        home (the engine's "in my base area" test NOT READ, work/re/l4_efficiency.md -- INFERRED), else 1; defences = their armed
        structures (category 0x2e: INFERRED); the candidate = a Body of the template never placed. Every enemy, seen
        or not (no vision test read). UnitModifier from the unit builder's rules (work/re/l4_unitbuilder.md)."""
        tc, pl = self.host.mod['tactics'], self.host.mod['player']
        p = pl.efficiency_params(ai.personality)
        near, mult = p['UnitBuilderEnemyNearbyDistance'], p['UnitBuilderEnemyNearbyMultiplier']
        live = [b for b in self.living() if not b.scenery]
        hx, hy = self.home
        mine = self.fighters([b for b in live if b.owner == self.player and 'STRUCTURE' not in b.kinds], True)
        foe_units = [b for b in live if b.owner in self.view.enemies and 'STRUCTURE' not in b.kinds]
        foes = [(f, mult if math.hypot(b.x - hx, b.y - hy) < near else 1.0)
                for f, b in zip(self.fighters(foe_units, True), foe_units)]
        defences = self.fighters([b for b in live if b.owner in self.view.enemies and 'STRUCTURE' in b.kinds
                                  and b.weapons], True)
        ub = getattr(ai, 'unit_builder', None)
        mods = ub.rules.get('modifiers', {}) if ub else {}
        out = {}
        for t in templates:
            if t not in self._protos:
                self._protos[t] = self._proto(t)
            cand = self.fighters([self._protos[t]], True)[0]
            cost, secs = simunits.production(t, self.world.own)
            off, dfn = mods.get(t, (1.0, 1.0))
            out[t] = tc.expected_efficiency(cand, mine, foes, defences, p, cost, secs, off, dfn)
        return out

    def _proto(self, template):
        """A Body of the template that is not in the world (Sim.add, then taken out again)."""
        return self.systems.proto(template, self.player)

    def units(self, ai, frame):
        out = []
        for b in self.living():
            if b.owner != self.player or 'STRUCTURE' in b.kinds or b.speed <= 0:
                continue
            # IGNORES_SELECT_ALL units are offered too: only a CreateUnits slot naming the template takes them
            # (teams.recruit; retail aiskirm_m team log, A round 191)
            # a HARVESTER only if the AI's own production made it (a factory's '#made' body): bench aiexpb* (D
            # round 156) -- the opener's AlliedMiner is taken by the SimpleExpansion team (CreateUnits AlliedMiner)
            # at f465 with its escorts; a placed miner (aiexpse, D154) and a refinery's free miner (aiexph*, D155)
            # never are, and the team holds its escorts back meanwhile. INFERRED: the rule's mechanism (what marks
            # the free and placed ones as not the AI's to take) is not read, only these three fit it
            if 'HARVESTER' in b.kinds and not b.name.startswith('#made'):
                continue
            if self.observe.boarding(b) or self.host.pullback.busy(b):
                continue
            # by serial, not name (review 11-19 q P2 #1: a unit made again under a dead one's name got the dead
            # one's wrapper, and the orders the AI gave it went to the dead body). The dead ones' stay: a model team
            # may still hold their Unit, and the snapshot builds its `$unit` table from here
            if b.serial not in self.wrappers:
                self.wrappers[b.serial] = Unit(b, self.observe, self.hunt_target)
            out.append(self.wrappers[b.serial])
        return out

    def owned(self, ai, frame):
        """{template: count} the AI owns now, minus those inside a garrison or transport -- what SpecificUnitCap
        counts (D round 89: boarding takes one off, getting out puts it back; walking to a garrison or pulled back
        it still counts)."""
        out = {}
        for b in self.living():
            if b.owner != self.player or 'STRUCTURE' in b.kinds or b.speed <= 0:
                continue
            if self.observe.inside(b) is not None:
                continue
            out[b.template] = out.get(b.template, 0) + 1
        return out

    def army(self, ai, frame):
        """The AI's unit count UnitCap holds (work/re d124_unitcap.md 2): the UNITS registered set -- every SELECTABLE
        non-STRUCTURE object it owns, harvesters, garrisoned, carried and pulled-back units included (those inside a
        garrison or transport stay in the set: d125_refinery_units.md 3, read)."""
        return sum(1 for b in self.living()
                   if b.owner == self.player and 'SELECTABLE' in b.kinds and 'STRUCTURE' not in b.kinds)

    def team_point(self, ai, frame):
        hx, hy = self.home
        foes = [b for b in self.world.living() if 'STRUCTURE' in b.kinds and not b.scenery
                and self.world.enemy(self.player, b.owner)]
        if not foes:
            return None
        f = min(foes, key=lambda b: math.hypot(b.x - hx, b.y - hy))
        return (f.x, f.y)

    # ---- the yard (Sim.production.due's rule, for structures)
    def spot(self, yard, template):
        """Where a structure goes: the first free point on the rings round the yard (INFERRED)."""
        import platprops
        world = self.world
        r = platprops.radius(template) if template in platprops.CATALOG else 40.0
        xs = [b.x for b in world.living()] or [yard.x]
        ys = [b.y for b in world.living()] or [yard.y]
        away = math.atan2(yard.y - (min(ys) + max(ys)) / 2, yard.x - (min(xs) + max(xs)) / 2)
        taken = [t for t in (world.blocks(b, place=True) for b in world.living() if 'STRUCTURE' in b.kinds) if t and len(t) == 3]
        for ring in RING:
            n = max(8, int(2 * math.pi * ring / (2 * r + GAP)))
            for k in range(n):
                a = away + 2 * math.pi * k / n
                x, y = yard.x + ring * math.cos(a), yard.y + ring * math.sin(a)
                if all(math.hypot(x - tx, y - ty) >= r + tr + GAP for tx, ty, tr in taken) and self.allied_ok(x, y):
                    return x, y
        return yard.x + RING[-1], yard.y

    def placer(self, df):
        """The defence block whose tower_spots place a structure: the brain's own, or (blocks without 'defense', the
        opening tests' blocks=()) a bare one -- its tactics a placeholder, since the block registers itself there."""
        if self.defense is not None:
            return self.defense
        import types
        return df.DefenseBlock(types.SimpleNamespace(kinds={}), lambda ai, f: None)

    def general_spot(self, yard, template):
        """Where a structure with a SkirmishAIInformation BaseBuildingLocation FRONT / SIDE / BACK / SPREAD / CENTER
        goes (the build slot's general placement, work/re l4_queue.md 2, l4_defense.md 3, l4_defense2.md 2.2, read):
        the angle by the location -- FRONT the base's facing A, SIDE A + 90 deg + {0, 180}, BACK A + 180, SPREAD /
        CENTER A + 0..9 x 36 deg -- round the own structure nearest the yard (try i = 0: the yard) by the model's
        tower_spots (angles +0, +36, -36, +72, -72; r = (BaseCompactness + rand(-0.05, 0.05)) x R, x 0.5 for CENTER);
        tries i = 1..4 move the probe out along the angle (as tower_centre). A (INFERRED, the unread point taken as the
        map's middle): the yard towards the centre of the whole map. R INFERRED: the towers' TOWER_LIST_R (600).
        bench 2026-11-14 engine_aiskirm rpb (aiskin0 / aiskin0r, B190): the barracks (FRONT) at strips x11 y17 in both
        = A ~213.7 deg, r ~285; the war factory (FRONT) A + 36 (aiskin0) / A - 36 (aiskin0r, where A + 36 had a
        plant); every plant (SPREAD) at A + k x 36. None = no such location (refinery, tower, a modded template) or
        nothing placeable: the yard's rings (spot)."""
        df = (model() or {}).get('defense')
        t = self.host.lib.template(template)
        info = t.first('SkirmishAIInformation') if t is not None else None
        where = (info.attrs.get('BaseBuildingLocation') or '').upper() if info is not None else ''
        if df is None or where not in ('FRONT', 'SIDE', 'BACK', 'SPREAD', 'CENTER'):
            return None
        import platprops
        world = self.world
        rects = self.settings.borders
        if rects:
            x0, y0, x1, y1 = max(rects, key=lambda q: (q[2] - q[0]) * (q[3] - q[1]))
        else:
            xs, ys = [b.x for b in world.living()] or [yard.x], [b.y for b in world.living()] or [yard.y]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        facing = math.atan2((y0 + y1) / 2 - yard.y, (x0 + x1) / 2 - yard.x)
        r = platprops.radius(template) if template in platprops.CATALOG else 40.0
        mine = [b for b in world.living() if b.owner == self.player and 'STRUCTURE' in b.kinds]
        taken = [q for q in (world.blocks(b, place=True) for b in world.living() if 'STRUCTURE' in b.kinds) if q and len(q) == 3]
        block = self.placer(df)
        rng = self.place_rng
        comp = float(df.personality_attr(self.ai, 'BaseCompactness', df.COMPACTNESS))
        for i in range(df.TOWER_TRIES):
            if where == 'FRONT':
                angle = facing
            elif where == 'SIDE':
                angle = facing + math.pi / 2 + math.pi * rng.randint(0, 1)
            elif where == 'BACK':
                angle = facing + math.pi
            else:
                angle = facing + df.SPREAD_STEP * rng.randint(0, 9)
            cx, cy = yard.x, yard.y
            if i > 0:
                far = df.PROBE_FAR if i >= df.TOWER_TRIES - 1 else comp * df.PROBE_STEP * i
                cx, cy = cx + far * math.cos(angle), cy + far * math.sin(angle)
            c = min(mine, key=lambda b: math.hypot(b.x - cx, b.y - cy), default=yard)
            for x, y in block.tower_spots(self.ai, (c.x, c.y), angle, centre_location=where == 'CENTER', rng=rng):
                if all(math.hypot(x - tx, y - ty) >= r + tr + GAP for tx, ty, tr in taken) and self.allied_ok(x, y):
                    return x, y
        return None

    def tower_spot(self, yard, template):
        """Where a base defence (KindOf FS_BASE_DEFENSE) goes: the model's tower_spots (BaseCompactness x ~600 with a
        +-0.05 jitter, five tries 36 deg apart) round the own structure nearest the yard (the yard itself), the
        first angle k x 36 deg (bench engine_aitower 11-07: round the yard, not toward the enemy -- the model's
        "no enemy found" branch); the first try clear of every structure, None = the yard's rings."""
        import platprops
        world = self.world
        df = (model() or {}).get('defense')
        if df is None:
            return None
        r = platprops.radius(template) if template in platprops.CATALOG else 40.0
        taken = [t for t in (world.blocks(b, place=True) for b in world.living() if 'STRUCTURE' in b.kinds) if t and len(t) == 3]
        angle = df.SPREAD_STEP * self.tower_rng.randint(0, 9)
        block = self.placer(df)
        for x, y in block.tower_spots(self.ai, (yard.x, yard.y), angle, rng=self.tower_rng):
            if all(math.hypot(x - tx, y - ty) >= r + tr + GAP for tx, ty, tr in taken) and self.allied_ok(x, y):
                return x, y
        return None

    def refinery_spot(self, template):
        """Where the AI's next refinery goes, None = it wants none now. Wanted (D138 2, read; 'served' INFERRED): a node
        no own refinery serves has its point R + its radius ahead within an own structure's build radius + R. The
        search (d125 1 + D136 5 + D138, read): the nodes in order -- within ResourceNodeSearchRadius of the nearest own
        yard first, a node's default spot before any ring, no own refinery within REFINERY_NEAR first, nearer first. A
        node's default spot: SuggestedOffset ahead (read; always fails the pre-check); its rings: ring i < Ticks
        (Ticks <= 0: none) at StartDistanceDelta + i x IncreaseTickAmount + the node's + the refinery's radius R
        (R INFERRED: the first shape's round, 75), in the node's facing + k x pi/16, k 0, -1, +1, -2, +2, -3, +3
        (read). A spot: open ground, clear of every structure (spot()'s rounds) and passing the pre-check (PASSAGE_*,
        read). Every node fails: the general placement by the yard (D138 4 read that it falls through to it; the
        simulator's yard rings are INFERRED, F1: aiskin0 / aiskin1's stand 430-630 from the yard).
        bench 2026-11-14 CampaignLab engine_aiskirm rpx (B188, work/bench_results/<build>__rpx.json): aiskirm's two at
        strips x26 y9 / x28 y11 (k -3, r ~250 of the east nodes 4173,2987 / 4279,3093, facing 0), no third; aiskin0
        (Ticks 0) = aiskin1 (StartDistanceDelta 1000): x27 y18, x16 y8, x27 y25, then two more by the yard."""
        import platprops
        world = self.world
        a = self.ai.personality.attrs
        near, start, inc, ticks = (float(a.get(k)) if a.get(k) is not None else d for k, d in REFINERY_FIELDS)
        r = platprops.radius(template) if template in platprops.CATALOG else 40.0
        yards = self.yards()
        if not yards:
            return None
        g = self.host.lib.template(template)
        g = g.first('Geometry') if g is not None else None
        shape = next((c.attrs for c in (g.children if g else ()) if c.tag == 'Shape'), None)
        # the ring's template term (D136 5): INFERRED the first shape's bounding circle (AlliedRefinery 60 x 45: 75)
        reach = (math.hypot(float(shape.get('MajorRadius', 0)), float(shape.get('MinorRadius', 0)))
                 if shape and shape.get('Type', '').upper() == 'BOX' else float(shape.get('MajorRadius', r)) if shape
                 else r)
        bodies = world.living()
        nodes = [b for b in bodies if 'orenode' in b.template.lower()]
        mine = [b for b in bodies if b.owner == self.player and 'REFINERY' in b.kinds]
        if not self.open_nodes(reach, bodies):
            return None
        taken = [t for t in (world.blocks(b, place=True) for b in bodies if 'STRUCTURE' in b.kinds and b not in nodes)
                 if t and len(t) == 3]
        memo = self.__dict__.setdefault('_refinery_spots', {})
        mk = (template, tuple(taken), tuple((y.x, y.y) for y in yards))
        if mk not in memo:
            memo.clear()
            yard = min(yards, key=lambda y: min((math.hypot(n.x - y.x, n.y - y.y) for n in nodes), default=0.0))
            memo[mk] = (self._refinery_search(world, r, reach, near, start, inc, int(ticks), yards, nodes, mine, taken,
                                              shape, [n for n in nodes if self._near_builder(n, reach, bodies)])
                        or self.node_side_spot(yard, template, nodes)
                        or self.spot(yard, template))
        return memo[mk]

    def node_side_spot(self, yard, template, nodes):
        """Where a refinery goes when the node search finds nothing: the general placement's NEAR_RESOURCE_NODE
        branch (work/re l4_defense2.md 2.2, l4_defense.md 3, read): round the base's anchor (the yard), the angle A
        toward a resource node (the pick unread; INFERRED the node nearest the yard), r = R x (N - n) / N with no
        BaseCompactness and no draw, five tries A, +36, -36, +72, -72 deg (read). R INFERRED the towers' TOWER_LIST_R
        (600) and N = 1 (the radius list unread); a try must be open ground clear of every structure and ore node
        (GAP as spot). bench 2026-11-14 engine_aiskirm rpx aiskin0 / aiskin1 / aiskinp (B188, the search fails every
        node): x27 y18 / x16 y8 / x27 y25 = 588 at -12 / 625 at -88 / 617 at +21 deg from the yard; the nearest
        node is -52 deg (its try stands on the node) -- the tries A + 36, A - 36, A + 72 (B204; the first one strip
        off, A ~ -50 would fit). None = all five fail (the engine's nudges and area scan not modelled: the yard's
        rings)."""
        df = (model() or {}).get('defense')
        if df is None or not nodes:
            return None
        import platprops
        world = self.world
        r = platprops.radius(template) if template in platprops.CATALOG else 40.0
        taken = [q for q in (world.blocks(b, place=True) for b in world.living() if 'STRUCTURE' in b.kinds or b in nodes)
                 if q and len(q) == 3]
        n = min(nodes, key=lambda n: math.hypot(n.x - yard.x, n.y - yard.y))
        a, step = math.atan2(n.y - yard.y, n.x - yard.x), df.SPREAD_STEP
        rr = df.TOWER_LIST_R
        for k in (0, 1, -1, 2, -2):
            x, y = yard.x + rr * math.cos(a + k * step), yard.y + rr * math.sin(a + k * step)
            if world.ground.open('ground', x, y, place=True) and all(math.hypot(x - tx, y - ty) >= r + tr + GAP
                                                     for tx, ty, tr in taken):
                return x, y
        return None

    def _near_builder(self, n, reach, bodies):
        """D138 2 (read): the point (the node's radius + reach) ahead of the node is within an own build-radius
        structure's radius + reach."""
        qx = n.x + ((n.radius or 0.0) + reach) * math.cos(n.angle)
        qy = n.y + ((n.radius or 0.0) + reach) * math.sin(n.angle)
        return any(math.hypot(b.x - qx, b.y - qy) < br + reach for b, br in
                   ((b, self._build_radius(b.template)) for b in bodies
                    if b.owner == self.player and 'STRUCTURE' in b.kinds) if br > 0)

    def open_nodes(self, reach=None, bodies=None, miners=False):
        """The ore nodes the AI could still use (D138 2 / B208, read): not served, and near one of its build-radius
        structures (_near_builder; reach: the scan's constant NODE_REACH, read). Served (INFERRED: the engine skips
        a node whose wrapper's taken count reached its capacity, the wrapper unread): an own refinery within SERVED
        of it, the node that refinery's nearest. Empty = AllNearbyNodesFull true (the same scan answers 'wants a
        refinery' and the heuristic). miners (the heuristic, B210): a served node is taken only while the AI's own
        collectors cover NODE_MINERS for it, pooled over the served nodes (INFERRED: ainf3's placed collectors stand
        nearer the other refinery; which node a collector counts at is unread). The refinery search keeps miners
        off: its 'no third' runs (aiskirm) are benched with one collector a refinery. B214 (bench aiskuc7 / aiskuc
        uc: the AI's collectors stay 2 from s73 to s218 with aiskirm's build times; aiskirm rp no third refinery to
        s252, while aiskin* order one at s148): counted at NODE_MINERS the refinery decision would want a third from
        s73 -- forced on, the simulator builds aiskirm's third at s152 and aiskuc7's collectors reach 4 with 14
        structures (bench 2 / 11; off: 2 / 11) -- so it does not count collectors (INFERRED: the wrapper's state 2 =
        'a refinery registered' skips it)."""
        reach = NODE_REACH if reach is None else reach
        bodies = self.world.living() if bodies is None else bodies
        nodes = [b for b in bodies if 'orenode' in b.template.lower()]
        served = set()
        for b in bodies:
            if b.owner == self.player and 'REFINERY' in b.kinds:
                n = min(nodes, key=lambda n: math.hypot(n.x - b.x, n.y - b.y), default=None)
                if n is not None and math.hypot(n.x - b.x, n.y - b.y) <= SERVED:
                    served.add(n.name)
        if miners:
            have = sum(b.owner == self.player and 'HARVESTER' in b.kinds for b in bodies)
            served = set(sorted(served)[:have // NODE_MINERS])
        return [n for n in nodes if n.name not in served and self._near_builder(n, reach, bodies)]

    def allied_ok(self, x, y):
        """CanBuildInAlliedBuildRadii (B212 read, work/re l4_allied_radii.md): unless the personality says true, the
        AI's placement search carries a flag that makes the cell check refuse a friend's buildable-area record. So
        false (the default; every retail personality) = a spot inside the build radius of another player whom the AI
        calls Friend is not buildable, unless an own build-radius structure covers it too and ALLY_OVERLAP_OK. True =
        any spot (the simulator before B213)."""
        memo = self.__dict__.setdefault('_allied_radii', {})
        if 'on' not in memo:
            df = (model() or {}).get('defense')
            v = df.personality_attr(self.ai, 'CanBuildInAlliedBuildRadii', 'false') if df is not None else 'true'
            memo['on'] = str(v).lower() != 'true'
        if not memo['on']:
            return True
        world = self.world
        near = [(b, self._build_radius(b.template)) for b in world.living() if 'STRUCTURE' in b.kinds]
        near = [(b, br) for b, br in near if br > 0 and math.hypot(b.x - x, b.y - y) < br]
        if not any(b.owner != self.player and world.relations.get((self.player, b.owner)) == 'Friend' for b, _ in near):
            return True
        return ALLY_OVERLAP_OK and any(b.owner == self.player for b, _ in near)

    def _build_radius(self, template):
        """A structure's build radius: its ProjectedBuildabilityInfo Radius (the largest), 0 = none (retail Allied:
        the yard and the outpost, 600; D138 2 reads the AI's 'wants a refinery' scan over these)."""
        memo = self.__dict__.setdefault('_build_radii', {})
        if template not in memo:
            t = self.host.lib.template(template)
            memo[template] = max((float(m.attrs.get('Radius', 0)) for m in (t.find('ProjectedBuildabilityInfo')
                                                                           if t is not None else ())), default=0.0)
        return memo[template]

    def _node_offset(self, n):
        """The node's default refinery spot distance: its AssistedPlacementInfoBehavior SuggestedOffset x (OreNode 180)."""
        memo = self.__dict__.setdefault('_node_offsets', {})
        if n.template not in memo:
            t = self.host.lib.template(n.template)
            m = t.first('AssistedPlacementInfoBehavior') if t is not None else None
            off = next((c.attrs for c in (m.children if m else ()) if c.tag == 'SuggestedOffset'), {})
            memo[n.template] = float(off.get('x', 180.0))
        return memo[n.template]

    def _refinery_search(self, world, r, reach, near, start, inc, ticks, yards, nodes, mine, taken, shape, tried):
        rects = self.settings.borders
        x0, y0, x1, y1 = rects[self.settings.border] if self.settings.border < len(rects) else (-1e9, -1e9, 1e9, 1e9)
        hx, hy = ((float(shape.get('MajorRadius', reach)), float(shape.get('MinorRadius', reach)))
                  if shape else (reach, reach))
        # every node's default spot S, facing its node, and its passage point P (D138 1, read)
        table = []
        for n in nodes:
            off, c, d = self._node_offset(n), math.cos(n.angle), math.sin(n.angle)
            sx, sy = n.x + off * c, n.y + off * d
            table.append((sx, sy, n.angle + math.pi, sx - (reach + PASSAGE_GAP) * c, sy - (reach + PASSAGE_GAP) * d))

        def meet(ax, ay, aa, bx, by, ba):          # two hx x hy boxes overlap (separating axes)
            dx, dy = bx - ax, by - ay
            for t in (aa, aa + math.pi / 2, ba, ba + math.pi / 2):
                span = sum(hx * abs(math.cos(t - q)) + hy * abs(math.sin(t - q)) for q in (aa, ba))
                if abs(dx * math.cos(t) + dy * math.sin(t)) >= span:
                    return False
            return True

        def fits(x, y, n):                          # the footprint inside the active border (INFERRED)
            if not (x0 + reach <= x <= x1 - reach and y0 + reach <= y <= y1 - reach
                    and world.ground.open('ground', x, y, place=True)
                    and all(math.hypot(x - tx, y - ty) >= r + tr + GAP for tx, ty, tr in taken)
                    and self.allied_ok(x, y)):
                return False
            face = math.atan2(n.y - y, n.x - x)     # the candidate faces its node (FACING_TOWARDS; INFERRED)
            for sx, sy, sa, px, py in table:        # the pre-check (D138 1, read; the shape test INFERRED)
                if math.hypot(x - sx, y - sy) < 2 * reach and meet(x, y, face, sx, sy, sa):
                    return False
                if math.hypot(x - px, y - py) < PASSAGE_CLEAR:
                    return False
            return True

        def key(n):
            d = min(math.hypot(n.x - y.x, n.y - y.y) for y in yards)
            has = any(math.hypot(n.x - b.x, n.y - b.y) < REFINERY_NEAR for b in mine)
            return d >= near, has, d
        # D138 2 reads no distance gate in the sort; INFERRED: only the nodes the 'wants a refinery' scan passes are
        # tried (aiskin1 = aiskin0 on the bench: without a limit its 1100+ rings round far nodes would stand far off)
        order = sorted(tried, key=key)
        for outside in (False, True):
            group = [n for n in order if key(n)[0] == outside]
            for n in group:                         # the default spots (tried first; the pre-check always fails them)
                off = self._node_offset(n)
                x, y = n.x + off * math.cos(n.angle), n.y + off * math.sin(n.angle)
                if fits(x, y, n):
                    return x, y
            for n in group:                         # the rings (after every default spot)
                for i in range(max(0, ticks)):
                    ring = start + i * inc + (n.radius or 0.0) + reach
                    for k in (0, -1, 1, -2, 2, -3, 3):   # D138 3, read: 0 (twice), -1, +1, -2, +2, -3, +3
                        t = n.angle + k * math.pi / 16
                        x, y = n.x + ring * math.cos(t), n.y + ring * math.sin(t)
                        if fits(x, y, n):
                            return x, y
        return None

    def yard_due(self, frame):
        world, systems = self.world, self.systems
        for name in list(self.yard_q):
            y, q = self.present(name[0] if isinstance(name, tuple) else name), self.yard_q[name]
            if y is None or not q:
                del self.yard_q[name]
                continue
            job = q[0]
            if job['full'] is not None:
                # a paused AI (PLAYER_TOGGLE_SKIRMISH_AI 0) places nothing: aipause:a's third structure, done while
                # paused, came down at f1280, just after the 85 s resume
                if frame >= job['full'] + PLACE_DELAY and self.player not in self.settings.ai_paused and \
                        systems.instal(self.player, job, 100.0):     # a file's full job not paid up waits for its rest
                    q.pop(0)
                    self.put(y, job['template'], frame)
                    self.yard_rest[name] = frame + 1
                continue
            if frame <= self.yard_rest.get(name, -1):    # the yard takes up the next the frame after (bench: 153
                continue                                # frames between two 10 s structures = 1 + 151 + 1)
            step = f32(100.0 / job['frames'])
            nxt = f32(job['progress'] + step)
            if not systems.instal(self.player, job, nxt):           # the AI port's PlayerSystems
                continue
            job['progress'] = nxt
            if nxt >= 100.0:
                job['full'] = frame

    def put(self, yard, template, frame):
        world = self.world
        spot = None
        if 'REFINERY' in self.host.kinds(template) and hasattr(self.ai, 'refinery_spot'):
            spot = self.refinery_spot(template)     # the search's spot, or the yard's (F1)
        elif 'FS_BASE_DEFENSE' in self.host.kinds(template):
            spot = self.tower_spot(yard, template)
        else:
            spot = self.general_spot(yard, template)
        x, y = spot or self.spot(yard, template)
        name = simworld.free_name(world, '#ai', template)
        self.commands.do(Command('place', f'ai:{self.player}', player=self.player, template=template,
                                       pos=(float(x), float(y)), args=(('name', name), ('team', yard.team))))
        placed = world.bodies.get(name)         # set down whole by the command, now (CommandPort._place)
        if placed is not None:
            self.made[placed.serial] = frame
        self.trace.append((frame, 'own', template))
        world.note('AI', f'{world.who(self.player)} 放下 {template}')
        self.systems.bring(frame + self.host.unpack(template), template, self.player, x, y, yard.team)

    def later_due(self, frame):
        for b in self.systems.brought(self.player, frame):     # a refinery's free miner (the production rules')
            self.made[b.serial] = frame
            self.trace.append((frame, 'out', b.template))

    # ---- units, one at a time a factory
    def unit_due(self, frame):
        world, systems = self.world, self.systems
        for b in world.living():                    # what came out of a factory since: the trace
            if b.owner == self.player and b.name.startswith('#made') and b.serial not in self.made:
                self.made[b.serial] = frame
                self.trace.append((frame, 'out', b.template))
                self.give('fill_body', b)       # a body simunits does not know (HOOKS 6)
        for t in list(self.unit_q):
            free = [f for f in self.factories() if t in self.host.menu(f.template)
                    and frame >= self.made.get(f.serial, -10 ** 9) + self.host.unpack(f.template)
                    and not systems.busy(f)
                    and systems.can_build(self.player, t, f)]   # its tier there (review 1120aa: order_build's own test)
            if free and self.commands.do(Command(          # at the free one it picked, by serial (same-name 11-19b
                    'build', f'ai:{self.player}', player=self.player, template=t,   # N03: not the shortest queue,
                    target=free[0].name, args=(('target_serial', free[0].serial),)))[0]:   # one still unpacking)
                self.unit_q.remove(t)

    @property
    def started(self):
        """The frame 'make base' ran (the AI's start; the bench's 'from the wake' frames count from it)."""
        return self.ai.start if self.ai.start is not None else self.woke if self.woke is not None else self.born

    def earn(self):
        """AIPlayer.money: the player's money now (AIPlayer.available: an account spends its Deposits + its budget
        share of the money -- INFERRED, bench engine_aiskirm d / f; the income is in it, Mining.mine_due, HOOKS 7)."""
        self.ai.money = self.observe.money().get(self.player, 0)

    def tick(self, frame):
        self.frame = frame
        # aiexpc, aibs3old and aieng hand over the starting yards after the brain is attached.
        if not self._has_initial_yards and (yards := self.yards()):
            self._set_initial_yards(yards)
        self.earn()
        self.later_due(frame)
        self.yard_due(frame)
        self.unit_due(frame)
        if self.player in self.settings.ai_paused:   # PLAYER_TOGGLE_SKIRMISH_AI(p, 0): the brain's update skips the
            return                              # whole frame (program, work/re a270_skirmish_start.md; aipause:a)
        if self.seen_t != self.world.t:           # the world changes once a DT tick: look and facts then
            self.look(frame)
            self.ai.ctx.update(self.facts())
        self.ai.tick(frame)
        self.hunt_threats(frame)
        if self.host.record:
            self.snap(frame)

    def hunt_threats(self, frame):
        """D110/D112 bounded Hunt bridge. No observed frames or IDs drive it.

        INFERRED: inclusive grid boundary, stable world order within cells,
        health-based death exclusion and current weapon grid reach. These are
        provisional until the named natural replay agrees; see work/re/e135_engage_host.md.
        """
        states = self.__dict__.get('_hunt_goals', {})
        cells = self.__dict__.setdefault('_hunt_cells', {})
        cell = lambda b: (int(b.x * .05), int(b.y * .05))
        for serial, state in states.items():
            # the member the state is of, by serial: a reference of its name or an object made again under it is
            # not that member (same-name sweep S6b), nor is it once another object holds its name (s P3)
            b = self.present(serial)
            if b is None:
                continue
            arrived = self.hunt_arrived(b, state)
            state.expire(lambda t: t is not None and t.alive, arrived=arrived)
            if (state.state == 33 and state.pursuit is not None
                    and not state.pursuit.alive and not arrived and not b.path):
                # INFERRED bridge: a dead combat goal can have cancelled the path.
                # Continue toward the pursuit's last position, without a new
                # team command or a fabricated current target.
                self.give('attack_move', b, pos=(state.pursuit.x, state.pursuit.y), args=(('drop_target', True),))
            here = cell(b)
            previous = cells.get(serial)
            cells[serial] = here
            if state.state != 33 or here == previous or frame <= 3:
                continue
            reach = max((w.get('range') or 0. for w in b.weapons), default=0.)
            radius = b.radius * 2
            if 20 < radius < 40:
                radius = 40
            span = max(1, int(radius * .05 + .3))
            weapon_cells = max(1, int(reach * .05 + .1))
            candidates = []
            for t in self.living():
                if t.scenery or t.owner not in self.view.enemies:
                    continue
                offset = max(abs(a - c) for a, c in zip(cell(t), here))
                if offset > span:
                    continue
                candidates.append(self.host.mod['micro'].ThreatCandidate(
                    t, True, requires_current_target='STRUCTURE' in t.kinds,
                    in_range=offset <= weapon_cells))
            selected = self.host.mod['micro'].select_threat([], candidates, state.pursuit)
            if selected is not None:
                state.target = selected
                # Direct object-goal write, not a fresh team attack order.
                self.give('attack', b, target=selected, args=(('goal_only', True),))

    # ---- HOOKS 9: the read-only trail (SimAI(record=True)); nothing below changes the run
    def _name(self, tid):
        b = self.body_of(tid) if tid is not None else None
        return b.name if b is not None else None

    def _places(self, b, own_defenses):
        """garrisons() without handing out Thing ids: [(name, x, y)] in the list's order."""
        if not b.alive or 'INFANTRY' not in b.kinds or 'SKIRMISH_AI_DONT_GARRISON' in b.kinds:
            return []
        return [(g.name, g.x, g.y) for g in self.observe.garrisons(b, own_defenses)]

    def snap(self, frame):
        """One row a team run a frame into rec['frames'] (a finished run once, the frame it ended):
          run (this brain's run number, first seen first), state_key / tactic / copy (the team), phase, state and
          prev_state (the team state now / at the micro update before: Run.state / Run.was), updated (a micro update
          ran this frame: state, foe, power, hostiles and cond are from it), target / target_id (the tactical
          target), foe / foe_id (the team's current enemy, Run.foe), power, hostiles (the hostile list's names);
          members: name, id (None while it has no Thing id), pos, hp, alive, goal (a body's name or a point), chase,
          aim (the micro's current target, aim_of), keep (the frame its keep record runs out, None: none / a crush's),
          going / inside (the garrison it walks to / is in);
          cond (only when updated): the terms of the team state's tests as that micro update saw them -- alpha
          (AlphaStrike), retreat (the retreat test), engage (able, the flags), garrisons (EnterBaseDefenses / EnterGarrisons:
          each member's places with distance and alive, the reach).
        rec['deaths'][name] = the first frame a body once in a team was seen dead. Bodies move once a DT tick, so
        positions and deaths step by a tick while the frames go one by one."""
        tactics = getattr(self, 'tactics', None)
        if tactics is None:
            return
        tc = self.host.mod['tactics']
        for r in list(tactics.runs.values()):
            n = next((i for i, x in enumerate(self._rec_runs, 1) if x is r), 0)
            if not n:
                self._rec_runs.append(r)
                n = len(self._rec_runs)
            if r.phase == 'done' and r.since < frame:
                continue
            for u in r.team.members:
                self._rec_bodies.setdefault(u.body.name, u.body)
            last = self._rec_mem.get(n)
            updated = r.was is not None and last is not None and r.mem is not last
            self._rec_mem[n] = r.mem
            mem = []
            keep = getattr(r, 'keep', {})
            for u in r.team.members:
                b = u.body
                reach = max((w.get('range') or 0.0 for w in b.weapons), default=0.0)
                aim = self.aim_of(b, reach) if b.alive else None
                goal, chase = b.goal, getattr(b, 'chase', None)
                hunt = self.__dict__.get('_hunt_goals', {}).get(b.serial)
                going, inside = self.observe.heading(b), self.observe.inside(b)
                mem.append({'name': b.name, 'id': self.ids.get(b.serial), 'pos': (b.x, b.y), 'hp': b.hp,
                            'alive': b.alive, 'goal': goal.name if self.observe.is_thing(goal) else goal,
                            'chase': chase.name if self.observe.is_thing(chase) else chase,
                            'aim': aim.name if aim is not None else None,
                            'keep': keep[u] if math.isfinite(keep.get(u, math.inf)) else None,
                            'unit_state': hunt.state if hunt is not None else None,
                            'pursuit': getattr(hunt.pursuit, 'name', None) if hunt is not None else None,
                            'going': getattr(going, 'name', going), 'inside': getattr(inside, 'name', inside)})
            foe = r.foe
            self.rec['frames'].append({
                'frame': frame, 'run': n, 'state_key': r.team.state, 'tactic': r.team.tactic,
                'copy': getattr(r.team, 'copy', 0), 'phase': r.phase, 'state': r.state, 'prev_state': r.was,
                'updated': updated, 'target': self._name(r.target), 'target_id': r.target,
                'foe': self._name(foe.id) if foe is not None else None, 'foe_id': foe.id if foe is not None else None,
                'power': r.power, 'hostiles': [self._name(h.id) for h in r.hostile], 'members': mem,
                'cond': self._conds(tc, r) if updated else None})
        for name, b in self._rec_bodies.items():
            if not b.alive and name not in self.rec['deaths']:
                self.rec['deaths'][name] = frame

    def _conds(self, tc, r):
        """The terms of tactics._team_state / _retreat / the garrison pass over the Fighters of the micro update just
        run (Run.mem / hostile / foe): the model's own tests, recomputed for reading, no new rule."""
        md, name, mem, hostile, foe = self.tactics.micro, r.team.template.micro, r.mem, r.hostile, r.foe
        if not mem:
            return {}
        c = tc.centre(mem)
        army = [m for m in mem if tc._dist(m.pos, c) < md.num(name, 'MaxDistanceFromTeamToIncludeInArmy')]
        if foe is not None and foe.id == r.target and md.flag(name, 'EngageTacticalTarget'):
            army = list(mem)

        def hurts(f):
            return any(m.dps(f) > 0 for m in mem)
        out = {'centre': c, 'army': [self._name(m.id) for m in army],
               'engage': {'able': any(hurts(h) and self.tactics._ignore_allows(self.ai, name, h)
                                      for h in hostile),
                          'EngageHostileTargets': md.flag(name, 'EngageHostileTargets'),
                          'EngageTacticalTarget': md.flag(name, 'EngageTacticalTarget'),
                          'EngagePassiveTargets': md.flag(name, 'EngagePassiveTargets'),
                          'UseGatherState': md.flag(name, 'UseGatherState'),
                          'CleanupPowerAdvantage': md.num(name, 'CleanupPowerAdvantage')}}
        out['alpha'] = None
        if foe is not None and foe.max_hp:
            ratio, kill = foe.hp / foe.max_hp, tc.kill_time(army, foe)
            past = min(tc._dist(m.pos, foe.pos) - max(m.reach, 100) for m in mem)
            a = {'ratio': ratio, 'kill_time': kill, 'ratio_x_kill': ratio * kill,
                 'AlphaStrikeTargetHealthPct': md.num(name, 'AlphaStrikeTargetHealthPct'),
                 'AlphaStrikeTargetTimeToKill': md.num(name, 'AlphaStrikeTargetTimeToKill'),
                 'nearest_past_reach': past, 'in_reach': tc.alpha_in_reach(mem, foe)}
            a['pass'] = (ratio <= a['AlphaStrikeTargetHealthPct'] and a['in_reach']
                         and a['ratio_x_kill'] < a['AlphaStrikeTargetTimeToKill'])
            out['alpha'] = a
        base = self.tactics.home(self.ai)
        far = math.inf if base is None else tc._dist(c, base)
        back = r.retreat_from
        rt = {'from_fallback': None if back is None else tc._dist(c, back),
              'RetreatMinDistanceToFallback': md.num(name, 'RetreatMinDistanceToFallback'),
              'mine_speed': sum(m.speed for m in mem) / len(mem),
              'their_speed': sum(h.speed for h in hostile) / len(hostile) if hostile else None,
              'RetreatSpeedBuffer': md.num(name, 'RetreatSpeedBuffer'), 'from_base': far,
              'RetreatMinDistanceFromBase': md.num(name, 'RetreatMinDistanceFromBase'), 'power': r.power,
              'RetreatPowerAdvantage': md.num(name, 'RetreatPowerAdvantage')}
        rt['falling_back'] = (r.was == 1 and back is not None
                              and rt['from_fallback'] < rt['RetreatMinDistanceToFallback'])
        rt['pass'] = rt['falling_back'] or (bool(hostile) and rt['RetreatSpeedBuffer'] * rt['their_speed']
                                            <= rt['mine_speed'] and far >= rt['RetreatMinDistanceFromBase']
                                            and r.power < rt['RetreatPowerAdvantage'])
        out['retreat'] = rt
        gar = {'EnterBaseDefenses': md.flag(name, 'EnterBaseDefenses'),
               'EnterBaseDefensesWhenIdle': md.flag(name, 'EnterBaseDefensesWhenIdle'),
               'EnterGarrisons': md.flag(name, 'EnterGarrisons'),
               'reach': md.num(name, 'EnterGarrisonableStructureDistance'), 'members': {}}
        for m in mem:
            b = m.unit.body if m.unit is not None else getattr(m, 'body', None)
            if b is None:
                continue
            gar['members'][b.name] = {kind: [(gn, math.hypot(gx - b.x, gy - b.y), self.world.bodies[gn].hp)
                                             for gn, gx, gy in self._places(b, own)]
                                      for kind, own in (('defenses', True), ('houses', False))}
        out['garrisons'] = gar
        return out


class SimAI:
    """sim.Sim with every player the mission hands to the skirmish AI played by the layer-4 model."""

    # Brain: the build states' BEST_UNIT_* entries scored by the expected efficiency. On by default since B round 131:
    # the 8 simai tests it once turned red (B handoff 131) were the player's war factory drones in the AI's count
    # (SimAI.living, round 130); with them out every simai test passes on (work/logs/b133_on.log). False = the unit
    # builder alone, as before round 129.
    efficiency = True

    def __init__(self, s, level='normal', seed=1, lib=None, data=None, blocks=BLOCKS, record=False):
        mod = model()                   # None: no brain is ever made (NoModel where one would be)
        self.sim, self.mod, self.level, self.seed = s, mod, level, seed   # sim: for the callers (main, tests)
        self.world = s                  # the world API: all the AI reads of its host beyond the ports
        self.commands = s.commands      # the command port (R3 13f-1)
        self.systems = ai_port.PlayerSystems(s)     # and the players' systems (the AI port, R3 13f-2c)
        self.settings = ai_port.Settings(s)     # and the mission's AI settings (the AI port)
        self.observe = Observe(s)       # and the observation port (R3 13f-2b)
        self.lib = lib if lib is not None or mod is None else mod['xmldata'].Library()
        self.data = data if data is not None or mod is None else mod['data'].AIData()
        self.blocks = tuple(blocks)     # which of A's blocks the brains get (() = opening, states and teams only)
        self.brains = {}                # player -> Brain
        self.done_to = None             # the last frame the AI ran
        self._data, self._cost, self._menu, self._cs, self._kinds, self._std = {}, {}, {}, {}, {}, {}
        import engine.ai.pullback as simpullback
        self.pullback = simpullback.Pullbacks(s, simpullback.Peers(s))
        self.record = record            # HOOKS 9: each Brain.rec gets the read-only trail (Brain.snap); off: none
        self._assigned = {}             # player -> its personality, settled before the first frame (the engine does
        for side, info in self.settings.sides.items():   # it as it makes the player; bench aisksd2
            player, pid = s.players.get(side), ((info or {}).get('aiPersonality') or '').split(':')[-1]   # 136 at s1)
            if pid and player is not None and player != s.human:
                self.no_model(side)
                self.own_personalities()
                self._assigned[player] = self.assigned(player, side, pid)

    @property
    def frame(self):
        return self.world.frame_now()

    def no_model(self, side):
        """NoModel where the AI would play `side` and the model is not on this computer."""
        if self.mod is None:
            raise NoModel(f'{side} is the skirmish AI\'s and ra3model.ai is not under {labpaths.ENGINE_MODEL}')

    def flags(self, player):
        """The mission's flags as states.py keys them: cnv's scripts run in a player's script list, so a bare SET_FLAG
        name is that list owner's and 'scope/name' sets the scope by hand ('/name' the empty one, which
        ScriptedFlagHeuristic reads -- l4_states.md 7; bench aistateplain: bare names unseen, aistateslash: seen)."""
        st = self.mod['states']
        return {st.flag_key(k, SCRIPT_SCOPE): bool(v) for k, v in (self.observe.flags() or {}).items()}

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
            self._cost[template] = int(simunits.production(template, self.world.own)[0] or 0) if template else 0
        return self._cost[template]

    def menu(self, template):
        if template not in self._menu:
            self._menu[template] = simunits.menu(template, self.world.own)
        return self._menu[template]

    def command_set(self, template):
        """The template's CommandSet's commands (simunits' reading of the SDK's GlobalData), cached."""
        if template not in self._cs:
            cs = simunits._inherited(template, self.world.own,
                                     lambda xml: (re.findall(r'\bCommandSet="([^"]+)"', xml) or [''])[0], '')
            self._cs[template] = simunits._commands(self.world.own)[0].get(cs, [])
        return self._cs[template]

    def standard(self, template):
        """UnitBuilderStandardCombatUnit of a template (the unit builder's candidates, INFERRED), cached."""
        if template not in self._std:
            self._std[template] = simunits._inherited(
                template, self.world.own,
                lambda xml: (re.findall(r'\bUnitBuilderStandardCombatUnit="(\w+)"', xml) or [''])[0], '') == 'true'
        return self._std[template]

    def unpack(self, template):
        """round(UnpackTime x 15) (tools/aiopen.unpack_frames); 0 without the module."""
        tpl = self.lib.template(template)
        m = tpl.first('StructureUnpackUpdate') if tpl is not None else None
        return round(templates.secs(m.attrs.get('UnpackTime')) * FPS) if m is not None else 0

    def kinds(self, template):
        """KindOf of a template: simunits', else the model's library's (HOOKS 6)."""
        if template not in self._kinds:
            st = simunits.stats(template, self.world.own)
            tpl = None if st['kinds'] else self.lib.template(template)
            self._kinds[template] = set(st['kinds']) if st['kinds'] else set(tpl.kinds) if tpl is not None else set()
        return self._kinds[template]

    def own_personalities(self):
        """The AI personalities the mission writes into its mod (Mission.assets, AIPersonalityDefinition:...) added to
        the AI's data once, so a probe's own personality (missions/aistate_bench.py) is the one the brain runs."""
        if getattr(self, '_own_done', False):
            return
        self._own_done = True
        for a in self.settings.assets:
            if len(a) >= 3 and str(a[2]).startswith('AIPersonalityDefinition:'):
                self.data.add_text(a[1])
                if 'defense' in self.blocks:
                    self.data_of('tactic attrs').add_text(a[1])
                if 'AITargetingHeuristic' in a[1] and 'targets' in self.blocks:    # a probe's own heuristic
                    self.data_of('targets').add_text(a[1])                        # (missions/ainamed_bench.py)
                if 'AIMicroManagerData' in a[1] and 'targets' in self.blocks:      # a probe's own micro manager
                    self.data_of('tactics micro').add_text(a[1])                  # (missions/airetreat_bench.py)
                    self.data_of('micro').update(self.mod['micro'].load_micro(texts=[a[1]]))   # its unit powers'
                    #                                                              rounds too (aimicro_bench _spow_xml)

    def assigned(self, player, side, pid):
        """The personality a side the map names `pid` ends up with (the model's AIData.assigned_personality, work/re
        d123_side.md 1.2): kept unless its SkirmishPersonality gate is open and its Side lacks the player's faction
        (bench aisksd2: a random Japanese skirmish one). The sim's PLAYER_IS_HUMAN_OR_AI_PERSONALITY reads the
        result (Sim.personality_of). None from the model (no library personality of the faction) keeps pid."""
        pick = getattr(self.data, 'assigned_personality', None)
        if pick is None:
            return pid
        import engine.players.tech as simtech
        faction = simtech.faction_of(player, self.settings.sides.get(side))
        got = pick(pid, faction and f'PlayerTemplate:{faction}', random.Random(self.seed + 11)) or pid
        if got != pid:
            self.settings.take_personality(player, got)
        return got

    def attach(self):
        """Brains for the AI's players, each told 'make base' the frame the mission handed it to the AI (Sim.ai). A
        side with an aiPersonality has its brain from the first frame: its states and teams run before the wake
        (bench aialobsw, B round 161: the wake held to ~s28, its team still 4 at f21 as with the wake at s10); a side
        handed over without one gets the default personality then."""
        world, settings = self.world, self.settings
        sides = {v: k for k, v in world.players.items()}
        for side, info in self.settings.sides.items():
            player = world.players.get(side)
            pid = ((info or {}).get('aiPersonality') or '').split(':')[-1]
            if pid and player is not None and player != world.human and player not in self.brains:
                self.no_model(side)
                self.own_personalities()
                pid = self._assigned.get(player) or self.assigned(player, side, pid)
                # INFERRED (D round 137): a side in the map with its personality thinks from frame 0, though the
                # first DT tick lands at frame 8 (bench aibdi0 / aibdi2: the team's rounds at f50 / f80 = mission
                # s2 / s4, the man inside from s4)
                self.brains[player] = Brain(self, player, side, pid, 0 if self.done_to is None else self.frame)
        for player in settings.ai:
            if player not in self.brains:
                side = sides.get(player, '')
                self.no_model(side or player)
                pid = (self.settings.sides.get(side) or {}).get('aiPersonality', '').split(':')[-1] or '1AlliedBalanced'
                self.own_personalities()
                self.brains[player] = Brain(self, player, side, pid, int(round(settings.ai[player] * FPS)))
            self.brains[player].wake(int(round(settings.ai[player] * FPS)))

    def advance(self, frames):
        """The mission `frames` frames on (the AI port's runner: Sim.advance a DT tick at a time), the AI ticked for
        each frame after."""
        return ai_port.drive(self.world, self, frames)

    def tick(self, now):
        """The plug-in's turn after the world reached frame `now`: the brains the mission handed over made, their
        switches read, and each ticked for every frame since the last turn (a brain from its birth)."""
        self.attach()
        for b in self.brains.values():
            b.switches()
        for f in range(min([now] + [b.born for b in self.brains.values()]) if self.done_to is None
                       else self.done_to + 1, now + 1):
            for b in self.brains.values():
                if f >= b.born:
                    b.tick(f)
        self.done_to = now

    def thoughts(self):
        return {self.world.who(p): b.ai.thoughts() for p, b in self.brains.items()}

    # ---- a yard's queue as plain rows (a Battlefield file's, S 11d: experimental/cnv/engine/state/battlefield.py). The yard's
    # structures are the AI's own queue (Brain.yard_q: the simulator's yards build none), so a file reads and places
    # them here, not in the world's queues.
    def yard_jobs(self, yard):
        """The jobs the AI of `yard`'s owner has queued at it, its structures' then its defences' (Brain.queue_of),
        each in order: [(template, progress 0..1, paid, the frame it filled or None)]; [] where no brain runs it."""
        brain = self.brains.get(yard.owner)
        if brain is None:
            return []
        return [(j['template'], min(1.0, j['progress'] / 100), j['paid'], j['full'])
                for key in (yard.serial, (yard.serial, 'defense')) for j in brain.yard_q.get(key, ())]

    def put_yard_jobs(self, yard, rows):
        """`rows` ({template, progress: per cent float32, paid, full: a frame of the host's or None} each, in order)
        into the queues of `yard` as Brain.build queues them -- the brains made first (attach: as the next tick would),
        nothing paid now (yard_due pays the rest frame by frame); a row the AI cannot take is left out. A why for each
        row left out, None for one placed. An AI that has not run yet starts from the placing's frame (its done_to:
        the source's AI had run the cut's frame, so the frames before it are not run again -- a brain born at 0 would
        step the yard once for each)."""
        if self.done_to is None:
            self.done_to = self.frame
        self.attach()
        brain = self.brains.get(yard.owner)
        if brain is None:
            return [f'no skirmish AI runs {yard.owner} on the host'] * len(rows)
        if yard not in brain.yards():
            return [f'not a yard of the AI of {yard.owner} (one on a map team builds nothing)'] * len(rows)
        return brain.put_yard_jobs(yard, rows)

