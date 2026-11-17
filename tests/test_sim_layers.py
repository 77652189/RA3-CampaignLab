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

# module -> layer (0 world, 1 data, 2 object modules, 3 combat, 4 player systems, 5 unit orders, 6 scripts,
# 7 frame loop, 8 skirmish AI, 9 report)
LAYER_OF = {
    'simworld': 0,
    'simunits': 1,
    'simtopple': 2, 'simjet': 2, 'simcrush': 2, 'simheal': 2, 'simmine': 2, 'simstatus': 2, 'simpower': 2, 'simgarrison': 2,
    'simmodifier': 2, 'simlevel': 2, 'simlocomotion': 2,
    'simbody': 2,
    'simtoggle': 2,
    'simspecial': 2,
    'simorder': 5,
    'simdamage': 3,
    'simtech': 4, 'simmoney': 4,
    'simact': 6, 'simact_vision': 6, 'simact_player': 6, 'simact_order': 6, 'simact_object': 6, 'simact_ability': 6, 'simact_world': 6, 'simact_show': 6, 'simscript': 6,
    'simcond': 6, 'simcond_world': 6, 'simcond_object': 6, 'simcond_vision': 6, 'simcond_player': 6, 'simcond_show': 6,
    'simloop': 7,
    'simassign': 2,
}
# (simmicro, L5, waits for simai: reached only through simai, which still imports sim, so the inventory's
# simcoverage.sim_files does not count it yet -- test_simcoverage_files would be red. It is a WORLD_TAKER already.)

# modules that take the world as an argument (rule 2): they reach it only through WORLD_API
WORLD_TAKERS = {'simheal', 'simmine', 'simmoney', 'simmodifier', 'simlocomotion',
                'simbody',
                'simtoggle',
                'simspecial',
                'simorder',
                'simcrush', 'simjet', 'simmicro', 'simassign',
                'simdamage'}

# modules that reach their host beyond the world through a Peers loan: every `peers.X` they read is in their PEERS
PEER_TAKERS = {'simorder', 'simdamage'}

# field -> the one file that may assign it (rule 3), for the blocks moved so far. Not yet the money dicts (money,
# income, money_cap): scripts, selling, production, repairs, spies and simai still write them directly (simmoney.py)
FIELD_OWNER = {'heal_at': 'simheal', 'heal_seen': 'simheal',
               'mine': 'simmine', 'nodes': 'simmine', 'mined_to': 'simmine',
               'aura_cache': 'simmodifier', 'aura_beat': 'simmodifier', 'level_rate': 'simmodifier',
               'level_vision': 'simmodifier', 'shielded': 'simmodifier', 'taken': 'simmodifier', 'dealt': 'simmodifier',
               'stood_for': 'simlocomotion', 'set_off': 'simlocomotion', 'jet_motion': 'simlocomotion',
               'frame_move': 'simlocomotion',
               'deleted': 'simbody', 'died_at': 'simbody', 'sell_end': 'simbody', 'lose_of': 'simbody',
               'toggle_at': 'simtoggle', 'armor_up': 'simtoggle', 'toggler': 'sim',
               'wfires': 'simspecial', 'leaps_due': 'simspecial', 'leap_ground_hits': 'simspecial',
               'movement_due': 'simspecial', 'self_bits_due': 'simspecial',
               'flee': 'simorder', 'follow': 'simorder', 'move_to': 'simorder', 'unpack_here': 'simorder',
               **dict.fromkeys(('incoming', 'projectile_hits', 'projectile_speeds', 'impact_body', 'knock_drowns',
                                'dots', 'cold_on', 'lift_modules', 'nugget_powers', 'hit_reaction_of'), 'simdamage'),
               'spot': 'simorder'}
# (a body's `alive` is assigned only in simbody too, but simai's teams.alive callback shares the name)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, CNV / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tree(name):
    return ast.parse((CNV / f'{name}.py').read_text(encoding='utf-8'))


def _imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module.split('.')[0]


def import_breaks(layer_of=LAYER_OF):
    """(module, imported, why) for each import that breaks rule 1."""
    out = []
    for mod, layer in layer_of.items():
        for name in _imports(_tree(mod)):
            if not (CNV / f'{name}.py').exists() and not (CNV / name / '__init__.py').exists():
                continue                                   # the standard library, numpy, experimental/campaign
            if name not in layer_of:
                out.append((mod, name, 'not layered'))
            elif layer_of[name] > layer:
                out.append((mod, name, f'L{layer} imports L{layer_of[name]}'))
    return out


def world_breaks(takers=WORLD_TAKERS):
    api = _load('simworld').WORLD_API
    out = []
    for mod in takers:
        for node in ast.walk(_tree(mod)):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'world' \
                    and node.attr not in api:
                out.append((mod, node.attr))
            if isinstance(node, ast.Name) and node.id in ('sim', 'Sim'):
                out.append((mod, node.id))
    return out


def owner_breaks(owners=FIELD_OWNER):
    """(file, field) for each assignment `<x>.field = / += / [k] =` outside the field's owner."""
    out = []
    for path in sorted(CNV.glob('sim*.py')):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            targets = node.targets if isinstance(node, ast.Assign) else \
                [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
            for t in targets:
                while isinstance(t, ast.Subscript):
                    t = t.value
                if isinstance(t, ast.Attribute) and t.attr in owners and path.stem != owners[t.attr]:
                    out.append((path.stem, t.attr))
    return out


def test_layered_modules_import_downward_only():
    assert not import_breaks()


def test_import_guard_bites():
    """Mutation check: a layer that imported one above it, or sim, would be caught."""
    assert ('simtech', 'simunits', 'L4 imports L5') in import_breaks({**LAYER_OF, 'simunits': 5})
    assert any(b[0] == 'simjet' and b[1] == 'simtopple' for b in import_breaks({**LAYER_OF, 'simtopple': 3}))


def test_world_takers_reach_only_the_world_api():
    assert not world_breaks()


def test_field_owners():
    assert not owner_breaks()


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
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'peers':
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


def group_actions(hub='simact', var='ACTIONS'):
    """action (condition) file -> the names its ACTIONS (CONDITIONS) table has (read from the source: `'X': fn` and
    `**dict.fromkeys(CONST, fn)` with CONST a tuple in that file), for the files simact.GROUPS (simcond.GROUPS)
    lists."""
    groups = next(n.value for n in _tree(hub).body if isinstance(n, ast.Assign) and n.targets[0].id == 'GROUPS')
    out = {}
    for g in (e.id for e in groups.elts):
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
    groups = group_actions('simcond', 'CONDITIONS')
    assert len(groups) >= 2 and all(groups.values())
    assert not chain_names(method='cond')
    assert not home_breaks(groups, set())
    homed = set().union(*groups.values())
    assert {'FLAG', 'COUNTER', 'TEAM_HAS_UNITS', 'TEAM_OUTSIDE_AREA_ENTIRELY', 'SKIRMISH_SPECIAL_POWER_READY',
            'NAMED_DESTROYED', 'ENEMY_SIGHTED', 'HAS_FINISHED_VIDEO'} <= homed and len(homed) == 71


def test_condition_home_guard_bites():
    """Mutation check: a condition in two files, or a branch back in Sim.cond_retail, is caught."""
    groups = group_actions('simcond', 'CONDITIONS')
    first, second = list(groups)[:2]
    name = next(iter(groups[first]))
    assert home_breaks({**groups, second: groups[second] | {name}}, set())
    assert chain_names(f"class Sim:\n    def cond_retail9(self, name, a):\n"
                       f"        if name == '{name}':\n            return True\n", method='cond') == {name}


def _loop():
    """simloop's CELLS (names), its orders (every tuple of names assigned at module level) and its functions, read
    from the source: importing it needs simworld on sys.path."""
    out, orders, defs = {}, {}, set()
    for n in _tree('simloop').body:
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
    for path in sorted(CNV.glob('sim*.py')):
        if path.stem != 'simloop':
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
HOST_USERS = ('simai', 'simproxy')
MUTATORS = {'append', 'pop', 'update', 'add', 'setdefault', 'remove', 'discard', 'clear', 'extend', 'insert'}


def host_write_breaks(mods=HOST_USERS, source=None):
    """(module, field) for each write on the Sim a module holds (`self.sim`, or a name bound to it): an assignment,
    augmented assignment or item set on one of its fields, or a mutating call (append, pop, ...) on one."""
    out = []
    for mod in mods:
        tree = ast.parse(source) if source is not None else _tree(mod)
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.Lambda))]:
            def is_sim(e):
                return isinstance(e, ast.Attribute) and e.attr == 'sim'

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
                        if field(x) and not (isinstance(x, ast.Attribute) and x.attr == 'sim'):
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
    assert host_write_breaks(('simai',), src) == [('simai', f) for f in
                                                   ('bodies', 'income', 'money', 'seen', 't', 'team_names')]
