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
enginefiles = _layers.enginefiles     # module name -> file (simX, or engine.<layer>.<part> after step 10)

# (module, forwarder) -> calls, 11-17 (R2). Who calls: the script actions (simact_*), the frame table (simloop), the
# Peers loans (simdamage, simorder, simpullback, simsweep, simgarrison, siminfiltrator: `peers.X` is the Sim's
# forwarder X today). Step B4b split destroy(delete=...) into destroy (a death) and delete (no death): the calls
# that picked by a flag name both now.
FORWARDER_CALLS = {
    # simact_ability: a special power's cast walking the ice engineer to his spot (its buttons go through the command
    # port, R3 13d-2)
    ('engine.script.act_ability', 'send'): 1,
    # simact_object: kill / sell / move / capture an object
    ('engine.script.act_object', 'delete'): 2, ('engine.script.act_object', 'destroy'): 5, ('engine.script.act_object', 'modify'): 1, ('engine.script.act_object', 'order_capture'): 1,
    ('engine.script.act_object', 'sell'): 2, ('engine.script.act_object', 'send'): 1, ('engine.script.act_object', 'stand'): 1,
    # simact_order: a teleport's and the AI hand-over's dropped order (its orders go through the command port, R3 13d-1)
    ('engine.script.act_order', 'stand'): 2,
    # the command port: the one caller of the order calls for the givers moved onto it (R3 13b-13d; the order family's
    # move into AIUpdate turns these into its module's command)
    ('engine.ports.command', 'flee_start'): 1, ('engine.ports.command', 'hunt_due'): 1,
    ('engine.ports.command', 'order_attack'): 2, ('engine.ports.command', 'order_capture'): 2,
    ('engine.ports.command', 'order_follow'): 1, ('engine.ports.command', 'order_group'): 2,
    ('engine.ports.command', 'order_guard'): 1, ('engine.ports.command', 'order_move'): 2,
    ('engine.ports.command', 'order_power'): 1, ('engine.ports.command', 'order_stop'): 1,
    ('engine.ports.command', 'player_power'): 1,
    ('engine.ports.command', 'stand'): 3,
    ('engine.ports.command', 'leap_press'): 1, ('engine.ports.command', 'movement_power_press'): 1,
    ('engine.ports.command', 'order_unpack'): 1, ('engine.ports.command', 'self_power_press'): 1,
    ('engine.ports.command', 'toggle_press'): 1, ('engine.ports.command', 'wfire_press'): 1,
    # simact_player / simact_world: upgrades and a team's stop
    ('engine.script.act_player', 'modify'): 1, ('engine.script.act_world', 'stand'): 1,
    # simdamage's Peers loan
    ('engine.combat.host', 'destroy'): 3, ('engine.combat.meta_impact', 'destroy'): 1, ('engine.combat.host', 'modify'): 2, ('engine.combat.host', 'projectile_detonate'): 2,
    ('engine.combat.host', 'queue_projectile_hit'): 1,
    # simgarrison's Peers loan (R3 ⑨c)
    ('engine.objects.garrison', 'delete'): 1, ('engine.objects.garrison', 'destroy'): 1, ('engine.objects.garrison', 'modify'): 3, ('engine.objects.garrison', 'order_move'): 2,
    ('engine.objects.garrison', 'send'): 1,
    # siminfiltrator's Peers loan (R3 ⑨c: the calls it made on the whole Sim before, counted once it was layered)
    ('engine.objects.infiltrator', 'delete'): 10, ('engine.objects.infiltrator', 'destroy'): 1, ('engine.objects.infiltrator', 'send'): 1,
    # simloop: the frame table's cells, each the Sim's forwarder of its block
    **dict.fromkeys([('engine.loop.frame', n) for n in (
        'aura_tick', 'blast_due', 'deal', 'death_blast_due', 'lose_health', 'self_power_due', 'suppression_tick',
        'wfire_due')], 1),     # S2 (ADR 0037): seq / flee / hunt / fight / follow / capture call engine.orders
    # simorder's Peers loan
    ('engine.orders.order', 'delete'): 2, ('engine.orders.order', 'send'): 11,
    ('engine.orders.ability', 'delete'): 1, ('engine.orders.ability', 'modify'): 1, ('engine.orders.ability', 'send'): 1, ('engine.orders.ability', 'toggle_press'): 1,
    # simsweep's Peers loan (simpullback's order_move went through the command port, R3 13f-1)
    ('engine.combat.sweeps', 'destroy'): 1,
    # simai's Peers loan (step 9d-2, R: the calls it made on self.sim before, counted since it joined the registry;
    # step 10 can call simorder / simmodifier / simdamage itself; its orders go through the command port since R3
    # 13f-1). Not the Sim's: self.tactics.stand (the tactics block, 1; the AI's hunt state's expire went off the count
    # with Sim.expire, step M10)
    ('engine.ai.core', 'expected_damage'): 1, ('engine.ai.core', 'modify'): 1,
    ('engine.ai.core', 'stand'): 1,
    # simproxy: none (its orders go through the command port since R3 13e)
    # living: a forwarder since the living cache (Sim.living -> simliving.living); these are the layers' calls the day
    # it became one, the rule's home being world.living(). The count only shrinks from here.
    ('engine.script.act_ability', 'living'): 2, ('engine.script.act_object', 'living'): 3, ('engine.script.act_order', 'living'): 3,
    ('engine.script.act_player', 'living'): 3, ('engine.script.act_world', 'living'): 1, ('engine.ai.core', 'living'): 23,
    ('engine.script.cond_object', 'living'): 8, ('engine.script.cond_player', 'living'): 1, ('engine.script.cond_vision', 'living'): 3,
    ('engine.combat.host', 'living'): 2, ('engine.combat.meta_impact', 'living'): 1, ('engine.objects.garrison', 'living'): 1,
    ('engine.objects.infiltrator', 'living'): 3, ('engine.objects.mine', 'living'): 4, ('engine.objects.modifier', 'living'): 1,
    ('engine.orders.order', 'living'): 3, ('engine.orders.ability', 'living'): 2, ('engine.orders.hunt', 'living'): 1, ('simproxy', 'living'): 3, ('engine.ai.pullback', 'living'): 1,
    ('engine.objects.special', 'living'): 2, ('engine.combat.sweeps', 'living'): 1,
    ('engine.objects.path', 'living'): 2,       # claims / goal_off_nodes, moved off the Sim (R3 M5 3a)
}

# ADR 0037 S0: how many of the Sim's names (methods and fields) each package reaches on the world it is handed --
# `<r>.name` with <r> one of RECEIVERS (`sim.t`, `world.order_move`, `self._w.stand`, `context.world.bodies`). Only
# shrinks: a name a package newly reaches is red (reach the part's own home instead), and so is a count above the
# code's -- lower it in the same commit. Packages are engine.<layer> and the top-level sim*.py files.
SIM_SURFACE = {'engine.ai': 21, 'engine.combat': 37, 'engine.kernel': 1, 'engine.loop': 38, 'engine.modules': 4,
               'engine.objects': 34, 'engine.orders': 48, 'engine.players': 19, 'engine.ports': 102,
               'engine.script': 139, 'engine.state': 27, 'engine.testing': 3, 'engine.world': 2, 'simai_run': 2, 'simbench': 2,
               'simbench_peak': 9, 'simproxy': 29, 'simrecord': 6, 'simshow': 1}
RECEIVERS = {'sim', 's', 'w', 'world', 'host', 'peers', '_w'}

_CONTAINER = set(dir(dict)) | set(dir(list)) | set(dir(set))   # self.players.get(...) is a lookup, not a forwarder


def _src(name):
    return Path(enginefiles.file_of(name)).read_text(encoding='utf-8')


def block_functions():
    """Names of the functions and methods defined in the moved blocks (every simulator file but sim.py)."""
    out = set()
    for p in map(Path, enginefiles.files()):
        if enginefiles.name_of(p) != 'sim':
            out |= {n.name for n in ast.walk(ast.parse(p.read_text(encoding='utf-8')))
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return out


def forwarders(source=None, modules=None, functions=None):
    """Sim method -> the call it forwards to (its body, the docstring aside, is one call into a moved block)."""
    functions = functions if functions is not None else block_functions()
    tree = ast.parse(source if source is not None else _src('sim'))
    if modules is None:          # the names sim.py holds the moved blocks by: simX, or `from engine.L import x as simX`
        engine = {enginefiles.name_of(p) for p in enginefiles.files()}
        modules = {m for m in engine if '.' not in m} | \
            {local for local, m in enginefiles.bindings(tree).items() if m in engine}
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
                                          'engine.players.tech': _src('engine.players.tech') + "\ndef z(world):\n    world.order_move(1)\n"})
    assert ('engine.players.tech', 'order_move', 1, 0) in ratchet_breaks(real)


def _package(module):
    parts = module.split('.')
    return '.'.join(parts[:2]) if parts[0] == 'engine' and len(parts) > 2 else module


def sim_surface(names=None, sources=None):
    """package -> the Sim names its files reach (see SIM_SURFACE); `sources`: {module: text} in place of the files."""
    names = names if names is not None else set().union(*_layers.sim_members())
    sources = sources if sources is not None else {enginefiles.name_of(p): Path(p).read_text(encoding='utf-8')
                                                   for p in enginefiles.files()}
    out = collections.defaultdict(set)
    for mod, text in sources.items():
        for n in ast.walk(ast.parse(text)) if mod != 'sim' else ():
            v = getattr(n, 'value', None)
            if isinstance(n, ast.Attribute) and n.attr in names and getattr(v, 'id', getattr(v, 'attr', None)) in RECEIVERS:
                out[_package(mod)].add(n.attr)
    return out


def surface_breaks(found, allowed=SIM_SURFACE):
    """(package, found, allowed, names) for each count that differs from the list."""
    return sorted((p, len(found.get(p, ())), allowed.get(p, 0), sorted(found.get(p, ())))
                  for p in set(found) | set(allowed) if len(found.get(p, ())) != allowed.get(p, 0))


def test_sim_surface_only_shrinks():
    assert not surface_breaks(sim_surface())


def test_sim_surface_guard_bites():
    """Mutation check: a package reaching one Sim name more is caught, by whichever receiver; a stale count too."""
    found = sim_surface({'order_move', 't'},
                        {'engine.players.x': 'def f(sim, a):\n    sim.t\n    a.order_move\n',
                         'engine.ports.y': 'class P:\n    def g(self):\n        self._w.order_move\n', 'sim': 'sim.t\n'})
    assert found == {'engine.players': {'t'}, 'engine.ports': {'order_move'}}
    real = sim_surface()
    unused = sorted(set().union(*_layers.sim_members()) - real['engine.players'])[0]
    real['engine.players'].add(unused)
    assert surface_breaks(real)[0][:3] == ('engine.players', SIM_SURFACE['engine.players'] + 1,
                                           SIM_SURFACE['engine.players'])
    assert surface_breaks({}, {'engine.players': 1}) == [('engine.players', 0, 1, [])]
