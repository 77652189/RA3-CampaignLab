"""Guard (ADR 0029, docs/plan.md "搬完" check (b)): the layered modules do not call the Sim's forwarders.

A forwarder is a method of `Sim` whose whole body is one call into a moved block: a function of a sim* module
(`return simorder.order_move(self, ...)`) or a method of an object one lives in (`self._harm().deal(...)`,
`self.wallet.earn(...)`). New code in a layer reaches the rule's own home (the block's function, the world API, a
Peers loan of the real function), never the Sim's forwarder of it.

The calls the layers make today are FORWARDER_CALLS: (module, forwarder) -> how many times, each with who calls it.
The list only shrinks: a new call (or one more of an old one) is red, and so is a line the code no longer needs --
lower or delete it in the same commit. The forwarders nobody outside sim.py and the tests calls are listed in
work/re/handoff-r2.md for step ⑩ to delete.

A call is `<x>.<forwarder>` (called or passed on) in a layered module (test_sim_layers' LAYER_OF, WORLD_TAKERS,
PEER_TAKERS) where <x> is a plain local name (`world`, `sim`, `s`, `peers`; not `self`, not an imported module) or
`self.<name>` (`self.world`, `self.sim`). A same-named method of some other object reached that way counts too: list
it here with a note, or rename it."""
import ast
import collections
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CNV = ROOT / 'experimental' / 'cnv'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_layers = _load('test_sim_layers_registry', ROOT / 'tests' / 'test_sim_layers.py')
LAYERED = sorted(set(_layers.LAYER_OF) | _layers.WORLD_TAKERS | _layers.PEER_TAKERS)

# (module, forwarder) -> calls, 11-17 (R2). Who calls: the script actions (simact_*), the frame table (simloop), the
# Peers loans (simdamage, simorder, simpullback, simsweep, simgarrison, siminfiltrator: `peers.X` is the Sim's
# forwarder X today).
FORWARDER_CALLS = {
    # simact_ability: the ability buttons the scripts press
    ('simact_ability', 'leap_press'): 1, ('simact_ability', 'movement_power_press'): 1,
    ('simact_ability', 'order_capture'): 1, ('simact_ability', 'order_unpack'): 1,
    ('simact_ability', 'self_power_press'): 1, ('simact_ability', 'send'): 1, ('simact_ability', 'toggle_press'): 1,
    ('simact_ability', 'wfire_press'): 1,
    # simact_object: kill / sell / move / capture an object
    ('simact_object', 'destroy'): 5, ('simact_object', 'modify'): 1, ('simact_object', 'order_capture'): 1,
    ('simact_object', 'sell'): 2, ('simact_object', 'send'): 1, ('simact_object', 'stand'): 1,
    # simact_order: the unit and team orders
    ('simact_order', 'flee_start'): 1, ('simact_order', 'hunt_due'): 1, ('simact_order', 'order_attack'): 4,
    ('simact_order', 'order_capture'): 1, ('simact_order', 'order_follow'): 2, ('simact_order', 'order_group'): 4,
    ('simact_order', 'order_guard'): 2, ('simact_order', 'order_move'): 1, ('simact_order', 'order_stop'): 2,
    ('simact_order', 'stand'): 6,
    # simact_player / simact_world: upgrades and a team's stop
    ('simact_player', 'modify'): 1, ('simact_world', 'stand'): 1,
    # simdamage's Peers loan
    ('simdamage', 'destroy'): 4, ('simdamage', 'modify'): 5, ('simdamage', 'projectile_detonate'): 2,
    ('simdamage', 'queue_projectile_hit'): 1,
    # simgarrison's Peers loan (R3 ⑨c)
    ('simgarrison', 'destroy'): 1, ('simgarrison', 'modify'): 3, ('simgarrison', 'order_move'): 2,
    ('simgarrison', 'send'): 1,
    # siminfiltrator's Peers loan (R3 ⑨c: the calls it made on the whole Sim before, counted once it was layered)
    ('siminfiltrator', 'destroy'): 11, ('siminfiltrator', 'send'): 1,
    # simloop: the frame table's cells, each the Sim's forwarder of its block
    **dict.fromkeys([('simloop', n) for n in (
        'aura_tick', 'blast_due', 'capture_due', 'deal', 'death_blast_due', 'expire', 'fight', 'flee_due',
        'follow_due', 'hunt_due', 'lose_health', 'self_power_due', 'seq_due', 'suppression_tick', 'toggles_run',
        'wfire_due')], 1),
    # simorder's Peers loan
    ('simorder', 'destroy'): 3, ('simorder', 'modify'): 1, ('simorder', 'send'): 12, ('simorder', 'toggle_press'): 1,
    # simpullback / simsweep Peers loans
    ('simpullback', 'order_move'): 1, ('simsweep', 'destroy'): 1,
}

_CONTAINER = set(dir(dict)) | set(dir(list)) | set(dir(set))   # self.players.get(...) is a lookup, not a forwarder


def _src(name):
    return (CNV / f'{name}.py').read_text(encoding='utf-8')


def block_functions():
    """Names of the functions and methods defined in the moved blocks (every sim*.py but sim.py)."""
    out = set()
    for p in CNV.glob('sim*.py'):
        if p.stem != 'sim':
            out |= {n.name for n in ast.walk(ast.parse(p.read_text(encoding='utf-8')))
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return out


def forwarders(source=None, modules=None, functions=None):
    """Sim method -> the call it forwards to (its body, the docstring aside, is one call into a moved block)."""
    modules = modules if modules is not None else {p.stem for p in CNV.glob('sim*.py')}
    functions = functions if functions is not None else block_functions()
    tree = ast.parse(source if source is not None else _src('sim'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Sim')
    out = {}
    for fn in cls.body:
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
        if len(body) != 1 or not isinstance(body[0], (ast.Return, ast.Expr)) or not isinstance(body[0].value, ast.Call):
            continue
        f = body[0].value.func
        if not isinstance(f, ast.Attribute):
            continue
        v = f.value
        to_module = isinstance(v, ast.Name) and v.id in modules
        to_object = f.attr in functions and f.attr not in _CONTAINER and (
            isinstance(v, ast.Call) or (isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name)
                                        and v.value.id == 'self'))
        if to_module or to_object:
            out[fn.name] = ast.unparse(f)
    return out


def forwarder_calls(names, sources=None):
    """(module, forwarder) -> count of `<x>.<forwarder>` in each layered module's source (see the module doc)."""
    sources = sources if sources is not None else {m: _src(m) for m in LAYERED}
    out = collections.Counter()
    for mod, text in sources.items():
        tree = ast.parse(text)
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imported |= {a.asname or a.name.split('.')[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                imported |= {a.asname or a.name for a in n.names}
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr in names:
                v = n.value
                if (isinstance(v, ast.Name) and v.id != 'self' and v.id not in imported) or \
                        (isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id == 'self'):
                    out[(mod, n.attr)] += 1
    return out


def ratchet_breaks(found, allowed=FORWARDER_CALLS):
    """(module, forwarder, found, allowed) for each count that differs from the list: above it is a new call through
    a forwarder (call the block instead); below it is a line to lower or delete (the list only shrinks)."""
    return sorted((m, n, found.get((m, n), 0), allowed.get((m, n), 0))
                  for m, n in set(found) | set(allowed) if found.get((m, n), 0) != allowed.get((m, n), 0))


def test_layers_call_no_new_forwarder():
    assert not ratchet_breaks(forwarder_calls(forwarders()))


def test_forwarders_are_found():
    """The reading itself: today's Sim has the forwarders the list leans on, and a lookup is not one."""
    fw = forwarders()
    assert 'owner_of' not in fw and 'note' not in fw and 'give_upgrade' not in fw
    assert {n for _, n in FORWARDER_CALLS} <= set(fw)


def test_forwarder_guard_bites():
    """Mutation check: a forwarder new in Sim, a layer calling it or one more old one, and a stale line are caught."""
    sim_src = ("class Sim:\n"
               "    def hop(self, b):\n        '''doc'''\n        return simhop.hop(self, b)\n"
               "    def wallet_earn(self, o):\n        self.wallet.earn(self, o)\n"
               "    def owner(self, s):\n        return self.players.get(s)\n"
               "    def two(self, b):\n        x = 1\n        return simhop.hop(self, b)\n")
    fw = forwarders(sim_src, modules={'simhop'}, functions={'hop', 'earn', 'get'})
    assert set(fw) == {'hop', 'wallet_earn'}
    layer = ("import simhop\n"
             "def f(world, peers):\n    world.hop(1)\n    peers.hop(2)\n    simhop.hop(3)\n    self.x.hop\n"
             "class C:\n    def g(self):\n        self.world.hop(4)\n        self.hop(5)\n")
    found = forwarder_calls({'hop'}, {'simx': layer})
    assert found == {('simx', 'hop'): 4}                  # world., peers., self.x., self.world. -- not simhop., self.
    assert ratchet_breaks(found, {('simx', 'hop'): 3}) == [('simx', 'hop', 4, 3)]      # one more
    assert ratchet_breaks(found, {}) == [('simx', 'hop', 4, 0)]                        # a new one
    assert ratchet_breaks({}, {('simx', 'hop'): 4}) == [('simx', 'hop', 0, 4)]         # stale: delete the line
    real = forwarder_calls(forwarders(), {**{m: _src(m) for m in LAYERED},
                                          'simtech': _src('simtech') + "\ndef z(world):\n    world.order_move(1)\n"})
    assert ('simtech', 'order_move', 1, 0) in ratchet_breaks(real)
