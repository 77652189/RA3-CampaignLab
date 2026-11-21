"""The simulator's layers (ADR 0029, docs/engine/sim-layers.md): guards that hold each block moved out of sim.py.

- Import direction: a layered module imports only layered modules of its own layer or below (rule 1); `sim` itself
  (the old class, on top of everything) is never imported by a layered module.
- World handle: a module that takes the world reaches only simworld.WORLD_API on it, and never names a Sim (rule 2).
- Frame order in one place: the frame loop's two orders name cells of one roster, and only simloop runs the scripts'
  engine step (rule 5).
- Field owners: a field a moved block owns is assigned only in that block's file (rule 3).

LAYER_OF grows by one entry per block moved (work/re/handoff-r.md 进度)."""
import ast
import importlib.util
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CNV = ROOT / 'experimental' / 'cnv'
# module name -> file (bare simX or full engine.<layer>.<part>, ADR 0029 step 10-0): one place, loaded by file path
_ef_spec = importlib.util.spec_from_file_location('enginefiles', CNV / 'enginefiles.py')
enginefiles = importlib.util.module_from_spec(_ef_spec)
_ef_spec.loader.exec_module(enginefiles)

# module -> layer (0 world, 1 data, 2 object modules, 3 combat, 4 player systems, 5 unit orders, 6 scripts,
# 7 frame loop, 8 skirmish AI, 9 report)
LAYER_OF = {
    'engine.world.handle': 0,
    'engine': 0, 'engine.kernel': 0, 'engine.kernel.interfaces': 0, 'engine.kernel.module': 0,   # the kernel
    'engine.kernel.factory': 0, 'engine.kernel.schedule': 0, 'engine.kernel.world': 0,          # (tests/test_kernel.py)
    'engine.kernel.snap': 0,                                                                     # step S's values
    'engine.ports.templates': 0, 'engine.modules.weaponset': 0,     # W1: simunits' weapon readers read its data
    'engine.modules.locomotor': 0,                                  # M2: and its Locomotor readers
    'engine.state.snapshot': 9,                                                       # step S, the host's part (a whole run's)
    'engine.state.ai_snapshot': 9,                                                     # step S 11b-4, the SimAI's around it
    'engine.state.battlefield': 9,                                                # step S 11d, the exchange file's
    'engine.data.units': 1,
    'engine.objects.topple': 2, 'engine.objects.jet': 2, 'engine.objects.crush': 2, 'engine.objects.heal': 2, 'engine.objects.mine': 2, 'engine.objects.status': 2, 'engine.objects.power': 2, 'engine.objects.garrison': 2,
    'engine.players.production': 2,
    'engine.objects.modifier': 2, 'engine.objects.level': 2, 'engine.objects.locomotion': 2, 'engine.objects.path': 2,
    'engine.objects.body': 2,
    'engine.objects.toggle': 2,
    'engine.objects.special': 2,
    'engine.orders.order': 5, 'engine.orders.ability': 5, 'engine.orders.target': 5, 'engine.orders.hunt': 5, 'engine.orders.seq': 5,
    'engine.combat.host': 3,
    'engine.combat': 3, 'engine.combat.registry': 3, 'engine.combat.damage': 3,      # N1 the nugget handlers
    'engine.combat.line_damage': 3, 'engine.combat.projectile': 3,
    'engine.combat.leech': 3, 'engine.combat.strip': 3,     # N2a
    'engine.combat.lift': 3, 'engine.combat.attach': 3, 'engine.combat.special_power': 3,     # N3a, N3b
    'engine.combat.attribute_modifier': 3, 'engine.combat.sweep': 3, 'engine.combat.meta_impact': 3,     # N3c, N3d, N3e
    'engine.combat.dot': 3, 'engine.combat.contained': 3, 'engine.combat.secondary': 3,     # N2b
    'engine.combat.suppression': 3, 'engine.combat.paralyze': 3,
    'engine.combat.range': 3,          # the weapon reach rules (R3 13f-2b)
    'engine.players.tech': 4, 'engine.players.money': 4,
    'engine.script.act': 6, 'engine.script.act_vision': 6, 'engine.script.act_player': 6, 'engine.script.act_order': 6, 'engine.script.act_object': 6, 'engine.script.act_ability': 6, 'engine.script.act_world': 6, 'engine.script.act_show': 6, 'engine.script.common': 6,
    'engine.script.cond': 6, 'engine.script.cond_world': 6, 'engine.script.cond_object': 6, 'engine.script.cond_vision': 6, 'engine.script.cond_player': 6, 'engine.script.cond_show': 6,
    'engine.loop.frame': 7,
    'engine.objects.assign': 2,
    'engine.combat.sweeps': 3,
    'engine.objects.infiltrator': 2, 'engine.objects.repair': 2,
    'engine.orders.micro': 5, 'engine.ai.pullback': 8,
    'engine.ai.core': 8,             # the skirmish AI (R3 13f-2d: it names no Sim; its run is simai_run.py, an entry point)
    'engine.ports.scripts': 0, 'engine.ports.command': 0, 'engine.script': 6, 'engine.script.executor': 6, 'engine.script.lists': 6, 'engine.script.host': 6,   # P1 the script port, Z its lists
}
# the skirmish AI's side (step 9d): simai and the parts only it imports. The inventory counts the player's run
# (simcoverage.sim_files walks down from sim and simproxy, never into simai; inventory_ai counts the AI apart), so
# test_simcoverage_files leaves these out; no other simulator module imports them (test_nothing_else_imports_the_ai).
AI_SIDE = {'engine.ai.core', 'engine.orders.micro', 'engine.ai.pullback'}
# tools over a whole run (step S's snapshot): layered for the import rule (never import sim), not a part of the
# simulator, so the inventory does not count their strings (tests/test_simcoverage_files.py)
OVER_THE_RUN = {'engine.state.snapshot', 'engine.state.ai_snapshot', 'engine.state.battlefield'}
# what any layer may import though it is no layer of the simulator (R3 13f-2d): the ports the AI asks its host
# through (adapters over the Sim, not parts of the run -- the inventory does not count them, the forwarder guard
# does not hold them) and modelpin (the private model's pin and package loader). Each imports nothing above L0.
# engine.ports.readonly: the read-only views those ports hand out (review 1119z P2 #2); read by them and simrecord
# only, no part of the player's run (it was in LAYER_OF and the inventory guard counted its strings as uncounted).
BOUNDARY = {'engine.ports.ai', 'engine.ports.observe', 'engine.ports.readonly', 'modelpin'}


def ai_import_breaks(mods=None, source=None):
    """(module, imported) for each simulator module outside AI_SIDE that imports one inside it (lazily too)."""
    mods = sorted((set(LAYER_OF) | {'sim', 'simproxy'}) - AI_SIDE) if mods is None else mods
    return [(m, n) for m in mods for n in _imports(ast.parse(source) if source is not None else _tree(m))
            if n in AI_SIDE]


# modules that take the world as an argument (rule 2): they reach it only through WORLD_API
WORLD_TAKERS = {'engine.objects.heal', 'engine.objects.mine', 'engine.players.money', 'engine.objects.modifier', 'engine.objects.locomotion',
                'engine.objects.body',
                'engine.objects.toggle',
                'engine.objects.special',
                'engine.orders.order', 'engine.orders.ability', 'engine.orders.hunt', 'engine.orders.seq',
                'engine.objects.crush', 'engine.objects.jet', 'engine.orders.micro', 'engine.objects.assign',
                'engine.combat.host',
                'engine.objects.level', 'engine.ai.pullback', 'engine.combat.sweeps',
                'engine.objects.garrison', 'engine.objects.infiltrator', 'engine.objects.repair',
                'engine.ai.core',
                'simproxy', 'engine.players.production'}
# (simpullback, L8 -- the AI tactics' pullback adapter -- is not in LAYER_OF for simmicro's reason: only simai imports it)

# modules that reach their host beyond the world through a Peers loan: every `peers.X` they read is in their PEERS
PEER_TAKERS = {'engine.orders.order', 'engine.orders.ability', 'engine.orders.hunt', 'engine.orders.seq', 'engine.combat.host',
               'engine.ai.pullback', 'engine.combat.sweeps',
               'engine.objects.garrison', 'engine.objects.infiltrator',
               'engine.ai.core',
               'simproxy', 'engine.players.production'}
# (simai, step 9d-2: a world and peers taker holding them as self.world / self.peers; since R3 13f-2d it names no
# sim -- a target object is a kernel Thing, the run is simai_run.py)
SIM_NAMES_UNTIL_10 = {}
# (simproxy, step 9d: the same for SimWorld; it makes the Sim (sim.Sim, sim.LEVELS for main's --level) as an entry
# point, which stays after step 10 -- only its sim.Body goes then)
SIM_NAMES_UNTIL_10['simproxy'] = {'Body', 'Sim', 'LEVELS'}

# field -> the one file that may assign it (rule 3), for the blocks moved so far. Not yet the money dicts (money,
# income, money_cap): scripts, selling, production, repairs, spies and simai still write them directly (simmoney.py)
FIELD_OWNER = {'heal_at': 'engine.modules.autoheal', 'hurt': 'engine.modules.autoheal',
               'life_end': 'engine.modules.lifetime',
               'toppled': 'engine.modules.topple', 'topple_end': 'engine.modules.topple',
               'mine': 'engine.modules.oreminer', 'nodes': 'engine.objects.mine', 'mined_to': 'engine.objects.mine',
               'level_rate': 'engine.objects.modifier',
               'level_vision': 'engine.objects.modifier', 'shielded': 'engine.objects.modifier', 'taken': 'engine.objects.modifier', 'dealt': 'engine.objects.modifier',
               'stood_for': 'engine.objects.locomotion', 'set_off': 'engine.objects.locomotion', 'jet_motion': 'engine.objects.locomotion',
               'frame_move': 'engine.objects.locomotion',
               'deleted': 'engine.objects.body', 'died_at': 'engine.objects.body', 'sell_end': 'engine.modules.sell', 'unpack_end': 'engine.modules.unpack', 'lose_of': 'engine.objects.body',
               'toggle_at': 'engine.modules.toggle', 'armor_up': 'engine.modules.toggle',
               'wfires': 'engine.objects.special', 'leaps_due': 'engine.objects.special', 'leap_ground_hits': 'engine.objects.special',
               'movement_due': 'engine.objects.special', 'self_bits_due': 'engine.objects.special',
               'flee': 'engine.orders.ability', 'follow': 'engine.orders.order', 'move_to': 'engine.orders.order', 'unpack_here': 'engine.orders.ability',
               **dict.fromkeys(('incoming', 'projectile_hits', 'projectile_speeds', 'impact_body', 'knock_drowns',
                                'dots', 'cold_on', 'lift_modules', 'nugget_powers', 'hit_reaction_of'), 'engine.combat.host'),
               'spot': 'engine.orders.order',
               'level_rank': 'engine.objects.level',
               **dict.fromkeys(('queues', 'placing', 'pack_hold'), 'engine.players.production')}
# (a body's `alive` is assigned only in simbody too, but simai's teams.alive callback shares the name)
# the writes outside the owner that owner_breaks finds and that stay for now, one row per write: the guard asks
# for exactly these (a fixed one comes off, a new one is red)
OWNER_KNOWN = {('engine.combat.registry', 'hurt'): "the hit Context's own slot (self.hurt), not the body field",
               ('engine.combat.registry', 'dots'): "the hit Context's own slot (self.dots), not the host's table",
               ('engine.orders.ability', 'move_to'): "flee_start's clearing unpack (b.path, ..., b.move_to = ...); "
                                                     "to move behind an order.py call"}


def _load(name):
    spec = importlib.util.spec_from_file_location(name, enginefiles.file_of(name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tree(name):
    return enginefiles.parse(name)


def _imports(tree):
    """The modules of experimental/cnv a tree imports, by full name (enginefiles.imports: `import engine.a.b` and
    `from engine.a import b` are engine.a.b, not engine); the standard library, numpy, experimental/campaign are not."""
    yield from sorted(enginefiles.imports(tree))


def import_breaks(layer_of=LAYER_OF, boundary=BOUNDARY):
    """(module, imported, why) for each import that breaks rule 1 (a BOUNDARY module counts as L0 for what it
    imports, and may be imported by any layer)."""
    out = []
    for mod, layer in {**layer_of, **dict.fromkeys(boundary, 0)}.items():
        for name in _imports(_tree(mod)):
            if name in boundary:
                continue
            if name not in layer_of:
                out.append((mod, name, 'not layered'))
            elif layer_of[name] > layer:
                out.append((mod, name, f'L{layer} imports L{layer_of[name]}'))
    return out


def _held(e, name):
    """`name` or `self.name` (a handle passed in, or one an object keeps)."""
    return (isinstance(e, ast.Name) and e.id == name) or \
        (isinstance(e, ast.Attribute) and e.attr == name and isinstance(e.value, ast.Name) and e.value.id == 'self')


def world_breaks(takers=WORLD_TAKERS, source=None):
    api = _load('engine.world.handle').WORLD_API
    out = []
    for mod in takers:
        tree = ast.parse(source) if source is not None else _tree(mod)
        parent = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and _held(node.value, 'world') and node.attr not in api:
                out.append((mod, node.attr))
            if isinstance(node, ast.Name) and node.id in ('sim', 'Sim'):
                p = parent.get(node)
                if not (isinstance(p, ast.Attribute) and p.attr in SIM_NAMES_UNTIL_10.get(mod, ())):
                    out.append((mod, node.id))
    return out


def owner_breaks(owners=FIELD_OWNER, sources=None):
    """(file, field) for each assignment `<x>.field = / += / [k] =` outside the field's owner, also as one of
    several targets (`a.f = b.g = v`) or inside an unpacking (`a.f, *b.g = v`). `sources`: {module: text} in place
    of the engine files (the self-test)."""
    out = []
    for stem, text in (sources or {enginefiles.name_of(p): Path(p).read_text(encoding='utf-8')
                                   for p in enginefiles.files()}).items():
        for node in ast.walk(ast.parse(text)):
            targets = list(node.targets) if isinstance(node, ast.Assign) else \
                [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
            for t in targets:
                if isinstance(t, (ast.Tuple, ast.List, ast.Starred)):
                    targets += [t.value] if isinstance(t, ast.Starred) else t.elts
                    continue
                while isinstance(t, ast.Subscript):
                    t = t.value
                if isinstance(t, ast.Attribute) and t.attr in owners and stem != owners[t.attr]:
                    out.append((stem, t.attr))
    return out


def test_layered_modules_import_downward_only():
    assert not import_breaks()


def test_import_guard_bites():
    """Mutation check: a layer that imported one above it, or sim, would be caught."""
    assert ('engine.players.tech', 'engine.data.units', 'L4 imports L5') in import_breaks({**LAYER_OF, 'engine.data.units': 5})
    assert any(b[0] == 'engine.objects.jet' and b[1] == 'engine.objects.topple' for b in import_breaks({**LAYER_OF, 'engine.objects.topple': 3}))
    assert ('engine.ai.core', 'modelpin', 'not layered') in import_breaks(boundary=BOUNDARY - {'modelpin'})
    assert ('engine.ports.observe', 'engine.kernel.module', 'L0 imports L3') in \
        import_breaks({**LAYER_OF, 'engine.kernel.module': 3})


def test_world_takers_reach_only_the_world_api():
    assert not world_breaks()


def test_field_owners():
    assert sorted(owner_breaks()) == sorted(OWNER_KNOWN)


def test_owner_guard_bites():
    """Mutation check: a field written outside its owner is caught inside an unpacking and in a chained assignment."""
    src = "def f(b, u):\n    b.path, (b.move_to, *u.follow) = 1, (2, 3)\n    u.x = b.spot = 4\n    b.flee = 5\n"
    assert owner_breaks(sources={'engine.orders.ability': src}) == \
        [('engine.orders.ability', 'move_to'), ('engine.orders.ability', 'follow'), ('engine.orders.ability', 'spot')]


def peer_breaks(takers=PEER_TAKERS, source=None):
    """(module, name) for each `peers.X` a module reads that its PEERS does not lend, or sets that its WRITES (none
    where it has no WRITES) does not allow."""
    out = []
    for mod in takers:
        tree = ast.parse(source) if source is not None else _tree(mod)   # read from the source (no sys.path)
        table = {n.targets[0].id: ast.literal_eval(n.value.args[0]) for n in tree.body if isinstance(n, ast.Assign)
                 and getattr(n.targets[0], 'id', '') in ('PEERS', 'WRITES')}
        lent, writes = table['PEERS'], table.get('WRITES', set())
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and _held(n.value, 'peers'):
                if n.attr not in lent or (isinstance(n.ctx, ast.Store) and n.attr not in writes):
                    out.append((mod, n.attr))
    return out


def test_peer_takers_reach_only_their_loan():
    assert not peer_breaks()


def test_peer_guard_bites():
    src = ("PEERS = frozenset({'send', 'seen'})\nWRITES = frozenset({'seen'})\n"
           "def f(peers):\n    peers.seen = {}\n    peers.send(1)\n")
    assert not peer_breaks(['m'], src)
    assert peer_breaks(['m'], src + "    peers.send = None\n") == [('m', 'send')]      # lent to read, not to set
    assert peer_breaks(['m'], src + "    peers.aim()\n") == [('m', 'aim')]             # not lent


def chain_names(source=None, method='act'):
    """The names Sim.act's (or Sim.cond's and its old tail cond_retail*'s) own chain still tests for (`name == 'X'`,
    `name in (...)`)."""
    tree = ast.parse(source if source is not None else (CNV / 'sim.py').read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Sim')
    out = set()
    for node in (x for fn in cls.body if isinstance(fn, ast.FunctionDef)
                 and (fn.name == method or fn.name.startswith(method + '_retail')) for x in ast.walk(fn)):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == 'name':
            for c in node.comparators:
                out |= {e.value for e in ast.walk(c) if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    return out


def group_actions(hub='engine.script.act', var='ACTIONS'):
    """action (condition) file -> the names its ACTIONS (CONDITIONS) table has (read from the source: `'X': fn` and
    `**dict.fromkeys(CONST, fn)` with CONST a tuple in that file), for the files simact.GROUPS (simcond.GROUPS)
    lists."""
    groups = next(n.value for n in _tree(hub).body if isinstance(n, ast.Assign) and n.targets[0].id == 'GROUPS')
    out = {}
    bindings = enginefiles.bindings(_tree(hub))
    for g in (bindings[e.id] for e in groups.elts):
        tree = _tree(g)
        consts = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                  and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Tuple)}
        table = next(n.value for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') ==
                     var)
        names = set()
        for k, v in zip(table.keys, table.values):
            names |= {k.value} if k is not None else set(consts[v.args[0].id])
        out[g] = names
    return out


def home_breaks(groups, chain):
    """(name, where) for an action (condition) name in two files or still in Sim.act's (Sim.cond's) chain too."""
    out, seen = [], {}
    for g, names in groups.items():
        out += [(n, f'{seen[n]} and {g}') for n in names if n in seen]
        seen.update(dict.fromkeys(names, g))
    return out + [(n, f'{seen[n]} and the Sim chain') for n in sorted(chain & seen.keys())]


def test_each_action_has_one_home():
    """Step 3 (act as a table): a name moved to an action file is gone from Sim.act's chain, and no two action files
    have it (one owner: the old chain's order no longer decides which runs)."""
    groups = group_actions()
    assert len(groups) >= 2 and all(groups.values())
    assert not home_breaks(groups, chain_names())


def test_home_guard_bites():
    """Mutation check: a name in two action files, or still in Sim.act's chain, is caught."""
    groups = group_actions()
    first, second = list(groups)[:2]
    name = next(iter(groups[first]))
    assert home_breaks({**groups, second: groups[second] | {name}}, set())
    assert home_breaks(groups, chain_names(f"class Sim:\n    def act(self, name, a, s):\n"
                                           f"        if name == '{name}':\n            pass\n"))


def test_each_condition_has_one_home():
    """Step 3c (cond as a table): no two condition files have a name, Sim.cond keeps no chain of its own (the old
    cond_retail* tail gone), and every name the old chain answered has a home."""
    groups = group_actions('engine.script.cond', 'CONDITIONS')
    assert len(groups) >= 2 and all(groups.values())
    assert not chain_names(method='cond')
    assert not home_breaks(groups, set())
    homed = set().union(*groups.values())
    assert {'FLAG', 'COUNTER', 'TEAM_HAS_UNITS', 'TEAM_OUTSIDE_AREA_ENTIRELY', 'SKIRMISH_SPECIAL_POWER_READY',
            'NAMED_DESTROYED', 'ENEMY_SIGHTED', 'HAS_FINISHED_VIDEO'} <= homed and len(homed) == 70
    assert 'TIMER_EXPIRED' not in homed         # Z 2: the script executor's own (its timer table)


def test_condition_home_guard_bites():
    """Mutation check: a condition in two files, or a branch back in Sim.cond_retail, is caught."""
    groups = group_actions('engine.script.cond', 'CONDITIONS')
    first, second = list(groups)[:2]
    name = next(iter(groups[first]))
    assert home_breaks({**groups, second: groups[second] | {name}}, set())
    assert chain_names(f"class Sim:\n    def cond_retail9(self, name, a):\n"
                       f"        if name == '{name}':\n            return True\n", method='cond') == {name}


def _loop():
    """simloop's CELLS (names), its orders (every tuple of names assigned at module level) and its functions, read
    from the source: importing it needs simworld on sys.path."""
    out, orders, defs = {}, {}, set()
    for n in _tree('engine.loop.frame').body:
        if isinstance(n, ast.FunctionDef):
            defs.add(n.name)
        elif isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Tuple) \
                and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in n.value.elts):
            orders[n.targets[0].id] = ast.literal_eval(n.value)
        elif isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'CELLS':
            out['CELLS'] = {e.id for gen in n.value.generators for e in gen.iter.elts}
    return types.SimpleNamespace(FRAME=orders.get('FRAME'), orders=orders, defs=defs, **out)


def order_breaks(loop):
    """What breaks 'one frame order' (rule 5): an order beside FRAME (the old loop's OLD), a cell not in it, a step
    of its own for the run without the model."""
    out = [('order', name) for name in loop.orders if name != 'FRAME']
    out += [('unused cell', name) for name in sorted(set(loop.CELLS) - set(loop.FRAME))]
    out += [('step', name) for name in sorted(loop.defs) if name.startswith('step') and name != 'step']
    return out


def test_frame_orders_share_one_roster():
    loop = _loop()
    assert set(loop.FRAME) <= set(loop.CELLS) and len(set(loop.FRAME)) == len(loop.FRAME)
    assert loop.FRAME.index('tech') < loop.FRAME.index('scripts') < loop.FRAME.index('lose_health')
    assert loop.FRAME[-1] == 'deal'                    # damage last, after the frame's scripts (R6)
    for path in map(Path, enginefiles.files()):
        if enginefiles.name_of(path) != 'engine.loop.frame':
            assert 'eng.step()' not in path.read_text(encoding='utf-8'), path.name


def test_one_frame_order_with_or_without_the_model():
    """The run without the private engine model is FRAME minus nothing (its scripts cell runs the Python scripts):
    no second order, no cell outside FRAME, no step_old (merged 11-17)."""
    loop = _loop()
    assert not order_breaks(loop)
    assert 'step_old' not in (CNV / 'sim.py').read_text(encoding='utf-8')


def test_one_frame_order_guard_bites():
    """Mutation check: the old loop's order, an extra cell, or its own step put back is caught."""
    loop = _loop()
    old = types.SimpleNamespace(orders={**loop.orders, 'OLD': ('release', 'events_old')},
                                CELLS=set(loop.CELLS) | {'events_old'}, FRAME=loop.FRAME,
                                defs=loop.defs | {'step_old'})
    assert order_breaks(old) == [('order', 'OLD'), ('unused cell', 'events_old'), ('step', 'step_old')]


MOVE_TAIL = ('follow', 'capture', 'infiltrate', 'auto_kill')     # cells after a coarse move (step 8c)
MOVE_TAIL_CALLS = {'follow_due', 'capture_due', 'tick', 'auto_kill_due'}


def move_tail_breaks(frame, source=None):
    """What breaks 'a move is only a move': the tail cells right after the moving cells in the frame order, and
    Sim.move calling none of what they run."""
    out = []
    i = frame.index('shot_clock') + 1
    if tuple(frame[i:i + len(MOVE_TAIL)]) != MOVE_TAIL:
        out.append(('order', 'shot_clock'))
    tree = ast.parse(source if source is not None else (CNV / 'sim.py').read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Sim')
    move = next(fn for fn in cls.body if isinstance(fn, ast.FunctionDef) and fn.name == 'move')
    out += [('move calls', n.func.attr) for n in ast.walk(move) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr in MOVE_TAIL_CALLS]
    return out


def test_move_is_only_a_move():
    loop = _loop()
    assert not move_tail_breaks(loop.FRAME)


def test_move_tail_guard_bites():
    """Mutation check: a tail cell moved off its place, or the tail called from Sim.move again, is caught."""
    loop = _loop()
    frame = tuple(n for n in loop.FRAME if n != 'capture')
    assert move_tail_breaks(frame[:2] + ('capture',) + frame[2:]) == [('order', 'shot_clock')]
    src = ("class Sim:\n    def move(self, dt=1, precise=False):\n        self.attachment_tick()\n"
           "        self.infiltrators.tick()\n")
    assert move_tail_breaks(loop.FRAME, src) == [('move calls', 'tick')]


# the skirmish AI and the player proxy (L8, step 9d): they play the Sim through its methods; a field of it they
# changed would bypass the field's owner (simmoney's wallet, the team registry, the AI's personalities, the sight)
HOST_USERS = ('engine.ai.core', 'simproxy')
MUTATORS = {'append', 'pop', 'update', 'add', 'setdefault', 'remove', 'discard', 'clear', 'extend', 'insert'}
# what the two hold of the Sim: itself, the world API, the Peers loan, and the AI port's Settings (R3 13f-2a: the
# mission's AI settings, read through; its two writes are its methods) and PlayerSystems (13f-2c: the production
# queues read through; the wallet's writes are its methods)
HOST_HANDLES = ('sim', 'world', 'peers', 'settings', 'systems')


def host_write_breaks(mods=HOST_USERS, source=None):
    """(module, field) for each write on the Sim a module holds (`self.sim`, or a name bound to it): an assignment,
    augmented assignment or item set on one of its fields, or a mutating call (append, pop, ...) on one."""
    out = []
    for mod in mods:
        tree = ast.parse(source) if source is not None else _tree(mod)
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.Lambda))]:
            def is_sim(e):          # the Sim, or what simai holds of it since step 9d-2 (world, peers; settings: 13f-2a)
                return isinstance(e, ast.Attribute) and e.attr in HOST_HANDLES

            handles = {t.id for st in ast.walk(fn) if isinstance(st, ast.Assign)
                       for tgt, val in ([(st.targets[0], st.value)] if len(st.targets) == 1 else [])
                       for t, v in (zip(tgt.elts, val.elts) if isinstance(tgt, ast.Tuple) and isinstance(val, ast.Tuple)
                                    else [(tgt, val)])
                       if isinstance(t, ast.Name) and is_sim(v)}

            def field(e):
                while isinstance(e, ast.Subscript):
                    e = e.value
                if isinstance(e, ast.Attribute) and (is_sim(e.value) or
                                                     isinstance(e.value, ast.Name) and e.value.id in handles):
                    return e.attr
                return None
            for n in ast.walk(fn):
                targets = n.targets if isinstance(n, ast.Assign) else \
                    [n.target] if isinstance(n, (ast.AugAssign, ast.AnnAssign)) else []
                for t in targets:
                    for x in (t.elts if isinstance(t, ast.Tuple) else [t]):
                        if field(x) and not (isinstance(x, ast.Attribute) and x.attr in HOST_HANDLES):
                            out.append((mod, field(x)))
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in MUTATORS \
                        and field(n.func.value):
                    out.append((mod, field(n.func.value)))
    return sorted(set(out))


def test_the_ai_and_the_proxy_write_no_field_of_the_sim():
    assert not host_write_breaks()


def test_host_write_guard_bites():
    """Mutation check: the writes step 9d took out (income, money, the team registry, the proto's pop, the sight)."""
    src = ("class Brain:\n    def f(self):\n        s, x = self.sim, 1\n        s.money[p] = 3\n"
           "        self.sim.income[p] = (1, 0)\n        self.sim.team_names.append(g)\n"
           "        s.bodies.pop(n, None)\n        s.seen = {}\n        s.t += 1\n"
           "        s.wallet.charge(p, 3)\n        self.sim = s\n")
    assert host_write_breaks(('engine.ai.core',), src) == [('engine.ai.core', f) for f in
                                                   ('bodies', 'income', 'money', 'seen', 't', 'team_names')]
    assert host_write_breaks(('engine.ai.core',), "def f(self):\n    self.settings.ai_paused.add(p)\n") == \
        [('engine.ai.core', 'ai_paused')]


# R3 13f-2a: the mission's AI settings reach simai through the AI port (engine/ports/ai.py Settings), not the Peers
# loan: every `settings.X` it reads is a Settings name, and PEERS lends none of them (nor the frame loop, `advance`:
# the port's runner drives the world and calls SimAI.tick)
def _ai_port():
    spec = importlib.util.spec_from_file_location('ai_port_for_layers', CNV / 'engine' / 'ports' / 'ai.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def settings_breaks(source=None):
    """(line, name) for each `settings.X` in simai that the AI port's Settings does not have, and ('PEERS', name) for
    each Settings name (or `advance`) PEERS still lends."""
    names = {n for n in vars(_ai_port().Settings) if not n.startswith('_')}
    tree = ast.parse(source) if source is not None else _tree('engine.ai.core')
    out = [(n.lineno, n.attr) for n in ast.walk(tree) if isinstance(n, ast.Attribute) and _held(n.value, 'settings')
           and n.attr not in names]
    lent = next((ast.literal_eval(n.value.args[0]) for n in tree.body if isinstance(n, ast.Assign)
                 and getattr(n.targets[0], 'id', '') == 'PEERS'), set())
    return out + [('PEERS', n) for n in sorted(lent & (names | {'advance'}))]


def test_the_ai_reads_its_settings_through_the_ai_port():
    assert not settings_breaks()


def test_settings_guard_bites():
    """Mutation check on the real file: a Settings name lent by Peers again, a setting read that Settings lacks."""
    src = (CNV / 'engine/ai/core.py').read_text(encoding='utf-8')
    assert settings_breaks(src.replace("PEERS = frozenset({'modify'", "PEERS = frozenset({'ai_paused', "
                                       "'modify'")) == [('PEERS', 'ai_paused')]
    assert [n for _, n in settings_breaks(src.replace('self.settings.ai_switches.get(',
                                                      'self.settings.switches.get('))] == ['switches']


# R3 13f-2b: what simai reads of the fight, the money and the flags reaches it through the observation port
# (engine/ports/observe.py Observe, held as `observe`) and the weapon reach rules off L3 simrange: every `observe.X`
# it reads is an Observe name, and PEERS lends none of the Observe names it reads nor simrange's rules
def _defs(path, cls=None):
    """The public function names of a file (cls: of that class in it), read off its source."""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    body = tree.body if cls is None else next(n.body for n in tree.body if isinstance(n, ast.ClassDef)
                                              and n.name == cls)
    return {n.name for n in body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')}


def observe_breaks(source=None):
    """(line, name) for each `observe.X` in simai that Observe does not have, and ('PEERS', name) for each name
    PEERS lends that simai reads through Observe or off simrange."""
    names = _defs(CNV / 'engine' / 'ports' / 'observe.py', 'Observe')
    tree = ast.parse(source) if source is not None else _tree('engine.ai.core')
    read = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and _held(n.value, 'observe')]
    out = [(n.lineno, n.attr) for n in read if n.attr not in names]
    lent = next((ast.literal_eval(n.value.args[0]) for n in tree.body if isinstance(n, ast.Assign)
                 and getattr(n.targets[0], 'id', '') == 'PEERS'), set())
    moved = {n.attr for n in read} | _defs(CNV / 'engine/combat/range.py')
    return out + [('PEERS', n) for n in sorted(lent & moved)]


def test_the_ai_reads_the_fight_through_the_observation_port():
    assert not observe_breaks()


def test_observe_guard_bites():
    """Mutation check on the real file: a name read through Observe lent by Peers again, a simrange rule lent again,
    an observe read that Observe lacks."""
    src = (CNV / 'engine/ai/core.py').read_text(encoding='utf-8')
    assert observe_breaks(src.replace("PEERS = frozenset({'modify'", "PEERS = frozenset({'money', 'reach_of', "
                                      "'modify'")) == [('PEERS', 'money'), ('PEERS', 'reach_of')]
    assert [n for _, n in observe_breaks(src.replace('self.observe.attachments()',
                                                     'self.observe.attached()'))] == ['attached']


# R3 13f-2c: the players' systems (power, the build permissions, the upgrades for sale, the production queues, the
# wallet) reach simai through the AI port's PlayerSystems (held as `systems`) and its orders through the command port
# it holds (`commands`): every `systems.X` it reads is a PlayerSystems name, and PEERS lends nothing but AI_PEERS_LEFT
# -- `modify`, the micro's charge recomputing a body's attributes (an effect of the power: it goes with toggle / power
# into the command family)
AI_PEERS_LEFT = frozenset({'modify'})


def systems_breaks(source=None):
    """(line, name) for each `systems.X` in simai that PlayerSystems does not have, and ('PEERS', name) for each name
    PEERS lends beyond AI_PEERS_LEFT."""
    names = {n for n in vars(_ai_port().PlayerSystems) if not n.startswith('_')}
    tree = ast.parse(source) if source is not None else _tree('engine.ai.core')
    out = [(n.lineno, n.attr) for n in ast.walk(tree) if isinstance(n, ast.Attribute) and _held(n.value, 'systems')
           and n.attr not in names]
    lent = next((ast.literal_eval(n.value.args[0]) for n in tree.body if isinstance(n, ast.Assign)
                 and getattr(n.targets[0], 'id', '') == 'PEERS'), set())
    return out + [('PEERS', n) for n in sorted(lent - AI_PEERS_LEFT)]


def test_the_ai_asks_the_player_systems_through_the_ai_port():
    assert not systems_breaks()


def test_systems_guard_bites():
    """Mutation check on the real file: a player system or the command port lent by Peers again, a systems read that
    PlayerSystems lacks (the wallet itself, not its three methods)."""
    src = (CNV / 'engine/ai/core.py').read_text(encoding='utf-8')
    assert systems_breaks(src.replace("PEERS = frozenset({'modify'", "PEERS = frozenset({'queues', 'commands', "
                                      "'modify'")) == [('PEERS', 'commands'), ('PEERS', 'queues')]
    assert [n for _, n in systems_breaks(src.replace('systems.instal(self.player, job, nxt)',
                                                     'systems.wallet.instal(self.player, job, nxt)'))] == ['wallet']


# step 9d-2: simai reads its host only through the world API and its Peers loan; the raw Sim it is handed is kept as
# SimAI.sim for its callers (main, tests) and read nowhere else (SimAI.__init__ makes world and peers; run() makes it)
AI_RAW_SIM = {'SimAI.__init__', 'run', 'main'}
# step 9d (R3): simproxy the same way; SimWorld.__init__ makes the Sim and world / peers, play() reads the ending, the
# guessed set off w.sim (the run's report; simshow.problems reads w.show, the port's), main hands nothing on
PROXY_RAW_SIM = {'SimWorld.__init__', 'play', 'main'}


def ai_sim_breaks(source=None, mod='engine.ai.core', raw=AI_RAW_SIM):
    """(function, line) for each `<x>.sim` in simai (or `mod`) outside AI_RAW_SIM (or `raw`)."""
    tree = ast.parse(source) if source is not None else _tree(mod)
    out = []
    for top in tree.body:
        fns = [(top.name, top)] if isinstance(top, ast.FunctionDef) else \
            [(f'{top.name}.{f.name}', f) for f in top.body if isinstance(f, ast.FunctionDef)] \
            if isinstance(top, ast.ClassDef) else []
        for q, fn in fns:
            if q not in raw:
                out += [(q, n.lineno) for n in ast.walk(fn) if isinstance(n, ast.Attribute) and n.attr == 'sim']
    return out


def test_the_ai_reads_its_host_through_world_and_peers():
    assert not ai_sim_breaks()


def test_the_proxy_reads_its_sim_through_world_and_peers():
    assert not ai_sim_breaks(mod='simproxy', raw=PROXY_RAW_SIM)


def test_proxy_read_guard_bites():
    """Mutation check on the real file: a SimWorld method or goals() reading self.sim / w.sim again, a peers read not
    lent, a world read outside the API, and sim named beyond SIM_NAMES_UNTIL_10 are each caught."""
    src = (CNV / 'simproxy.py').read_text(encoding='utf-8')
    for old, new in (('return self.peers.input and', 'return self.sim.input and'),
                     ('    world = w.world\n', '    world = w.sim\n')):
        assert old in src
        assert ai_sim_breaks(src.replace(old, new), 'simproxy', PROXY_RAW_SIM)
    assert peer_breaks(['simproxy'], src.replace('self.peers.offers(', 'self.peers.order_move(')) == \
        [('simproxy', 'order_move')]
    assert world_breaks(['simproxy'], src.replace('self.world.point(block)', 'self.world.timers(block)')) == \
        [('simproxy', 'timers')]
    assert world_breaks(['simproxy'], src.replace('simworld.CIV', 'sim.CIV')) == [('simproxy', 'sim')] * 3


def test_ai_read_guard_bites():
    """Mutation check: the raw Sim read again, a world read outside the API, a peers read not lent, a write through
    world, and sim named beyond SIM_NAMES_UNTIL_10 are each caught."""
    assert ai_sim_breaks("class Brain:\n    def f(self):\n        return self.sim.money\n") == [('Brain.f', 3)]
    assert ai_sim_breaks("class SimAI:\n    def __init__(self, s):\n        self.sim = s\n") == []
    src = "PEERS = frozenset({'money'})\nclass Brain:\n    def f(self):\n        return self.peers.money\n"
    assert not peer_breaks(['engine.ai.core'], src)
    assert peer_breaks(['engine.ai.core'], src.replace('peers.money', 'peers.order_move')) == [('engine.ai.core', 'order_move')]
    assert world_breaks(['engine.ai.core'], "def f(self):\n    return self.world.order_move, sim.Body\n") == \
        [('engine.ai.core', 'order_move'), ('engine.ai.core', 'sim')]         # R3 13f-2d: simai names no sim, Body neither
    assert world_breaks(['simproxy'], "def f(self):\n    return sim.Body\n") == []
    assert world_breaks(['simproxy'], "def f(self):\n    return sim.Thing\n") == [('simproxy', 'sim')]
    assert host_write_breaks(('engine.ai.core',), "class B:\n    def f(self):\n        self.world.money[p] = 3\n") == \
        [('engine.ai.core', 'money')]


def test_nothing_else_imports_the_ai():
    assert not ai_import_breaks()


def test_ai_import_guard_bites():
    """Mutation check: a simulator module importing simmicro at its top or simai inside a function is caught."""
    assert ai_import_breaks(['sim'], "import engine.orders.micro as simmicro\ndef f():\n    import engine.ai.core as simai\n") == \
        [('sim', 'engine.ai.core'), ('sim', 'engine.orders.micro')]


# step 9d: the skirmish AI writes no field of a body either (rule "L8 changes no object field"): a goal, a team, a
# lifetime, the stats of a body simunits does not know go through their owners (the command port's goal_only,
# world.add(team=), simbody.last_until / fill); what it marks for itself it keeps (Brain._unpack_ordered). Its own
# records it may write: a tactics Fighter (`f`) and a hunt goal's state (`state`).
AI_RECORDS = {'f', 'state'}


def ai_object_write_breaks(source=None):
    """(function, line, target) for each write in simai on an attribute of anything but itself and AI_RECORDS: an
    assignment, augmented assignment or item set, a mutating call (append, add, ...) or a setattr."""
    tree = ast.parse(source) if source is not None else _tree('engine.ai.core')
    out = []

    def outside(e):
        while isinstance(e, (ast.Attribute, ast.Subscript)):
            e = e.value
        return not (isinstance(e, ast.Name) and e.id in AI_RECORDS | {'self'})

    def walk(node, q):
        for c in ast.iter_child_nodes(node):
            cq = f'{q}.{c.name}' if q and isinstance(c, (ast.FunctionDef, ast.ClassDef)) else \
                c.name if isinstance(c, (ast.FunctionDef, ast.ClassDef)) else q
            targets = c.targets if isinstance(c, ast.Assign) else \
                [c.target] if isinstance(c, (ast.AugAssign, ast.AnnAssign)) else []
            for t in targets:
                for x in (t.elts if isinstance(t, ast.Tuple) else [t]):
                    while isinstance(x, ast.Subscript):
                        x = x.value
                    if q and isinstance(x, ast.Attribute) and outside(x):
                        out.append((q, c.lineno, ast.unparse(x)))
            if q and isinstance(c, ast.Call):
                f = c.func
                if isinstance(f, ast.Name) and f.id == 'setattr' and c.args and outside(c.args[0]):
                    out.append((q, c.lineno, 'setattr ' + ast.unparse(c.args[0])))
                if isinstance(f, ast.Attribute) and f.attr in MUTATORS and isinstance(f.value, ast.Attribute) \
                        and outside(f.value):
                    out.append((q, c.lineno, ast.unparse(f.value)))
            walk(c, cq)
    walk(tree, '')
    return out


def test_the_ai_writes_no_field_of_a_body():
    assert not ai_object_write_breaks()


def test_ai_object_write_guard_bites():
    """Mutation check: the writes step 9d took out (a goal, a team, a lifetime, a fill, the unpack mark), a status
    set's add and a setattr are each caught; the AI's own records and itself are not."""
    src = ("class Brain:\n    def f(self, u, t):\n        b = u.body\n        b.goal = None\n        b.team = t\n"
           "        u.body.life_end = 9\n        b.max_hp = b.hp = 3\n        b.unpack_ordered = was = True\n"
           "        b.status.add('X')\n        setattr(b, 'speed', 1)\n"
           "        f.kinds, state.target = (), t\n        self.made[b.name] = 1\n")
    assert [w for _, _, w in ai_object_write_breaks(src)] == \
        ['b.goal', 'b.team', 'u.body.life_end', 'b.max_hp', 'b.hp', 'b.unpack_ordered', 'b.status',
         'setattr b']
