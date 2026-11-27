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
    # (S3 2, ADR 0037: a body's end is the kernel World's kill / remove, its walk simlocomotion.go_to, a sale and
    # LoseHealthUpdate simbody.Life's -- no layer calls Sim.destroy / delete / sell / send / lose_health)
    # the command port: the special powers' presses (S1, ADR 0037: its orders call the rules it is handed; these wait
    # for Specials as a part of its own, S3)
    ('engine.ports.command', 'leap_press'): 1, ('engine.ports.command', 'movement_power_press'): 1,
    ('engine.ports.command', 'self_power_press'): 1, ('engine.ports.command', 'wfire_press'): 1,
    # simdamage's Peers loan
    ('engine.combat.host', 'projectile_detonate'): 2,
    ('engine.combat.host', 'queue_projectile_hit'): 1,
    # simloop: the frame table's cells, each the Sim's forwarder of its block
    **dict.fromkeys([('engine.loop.frame', n) for n in (
        'blast_due', 'deal', 'death_blast_due', 'suppression_tick',
        'wfire_due')], 1),     # S2 (ADR 0037): seq / flee / hunt / fight / follow / capture call engine.orders
    # simai's Peers loan (step 9d-2, R: the calls it made on self.sim before, counted since it joined the registry;
    # step 10 can call simorder / simmodifier / simdamage itself; its orders go through the command port since R3
    # 13f-1). (The AI's hunt state's expire went off the count with Sim.expire, step M10; self.tactics.stand with
    # Sim.stand, S1)
    ('engine.ai.core', 'expected_damage'): 1,
    # simproxy: none (its orders go through the command port since R3 13e)
    # living: a forwarder since the living cache (Sim.living -> simliving.living); these are the layers' calls the day
    # it became one, the rule's home being world.living(). The count only shrinks from here.
    ('engine.script.act_ability', 'living'): 2, ('engine.script.act_object', 'living'): 3, ('engine.script.act_order', 'living'): 3,
    ('engine.script.act_player', 'living'): 3, ('engine.script.act_world', 'living'): 1, ('engine.ai.core', 'living'): 23,
    ('engine.script.cond_object', 'living'): 8, ('engine.script.cond_player', 'living'): 1, ('engine.script.cond_vision', 'living'): 3,
    ('engine.combat.host', 'living'): 3, ('engine.combat.meta_impact', 'living'): 1, ('engine.objects.garrison', 'living'): 1,
    ('engine.objects.infiltrator', 'living'): 3, ('engine.objects.mine', 'living'): 3, ('engine.objects.modifier', 'living'): 1,
    ('engine.orders.order', 'living'): 3, ('engine.orders.ability', 'living'): 2, ('engine.orders.hunt', 'living'): 1, ('simproxy', 'living'): 3, ('engine.ai.pullback', 'living'): 1,
    ('engine.objects.special', 'living'): 2, ('engine.combat.sweeps', 'living'): 1,
    ('engine.objects.path', 'living'): 2,       # claims / goal_off_nodes, moved off the Sim (R3 M5 3a)
}

# ADR 0037 S0: the Sim's names (methods and fields) each package reaches on the world it is handed, with how many
# access points (`name*3`; none = one) -- `<r>.name` with <r> one of RECEIVERS (`sim.t`, `world.order_move`,
# `self._w.stand`, `context.world.bodies`). Only shrinks: a name a package newly reaches, or one more point of a name
# it already does, is red (reach the part's own home instead), and so is a point the code no longer makes -- write
# the line the failure prints, in the same commit (review rr #8: a names-only count let a swap through). Packages are
# engine.<layer> and the top-level sim*.py files.
SIM_SURFACE = {
    'engine.ai': 'blocks*11 bodies*4 commands*3 enemy*2 flags frame_now*3 ground*8 human*2 level living*24 '
                 'note*4 own*15 players*6 relation relations*3 t*4 waypoints*2 who*4 world xml_of*2',
    'engine.combat': 'attachment_tick attachments*4 can_hit change*2 cold_of*3 death_blasts*2 emp_disabled*2 firing '
                     'first_death*4 frame_now*15 gap*5 garrison*2 ground*6 guessed has_model_condition hostile infiltrators '
                     'label*5 lift_timers*2 living*6 mark_first_death note own*7 player_ups projectile_detonate*2 '
                     'queue_projectile_hit relation*2 set_model_condition shots_due suppression_fields*3 sweeps t*4 used*7 '
                     'world*7 xml_of*2',
    'engine.kernel': 'seq*2',
    'engine.loop': '_life aim_due anchored*2 auto_kill_due blast_due clock combat*3 deal death_blast_due ending*4 events*5 '
                   'flags frame_movers garrison handed*3 happen heal hunts infiltrators mid_aims mining move*3 off_teams '
                   'production*2 repairs self_power_due seq series shot_clock*2 suppression_tick sweeps t*8 tech_due test*3 '
                   'toggles_of wallet wfire_due world*2',
    'engine.modules': 'pick',     # a module's self.world.gap / living / used are the kernel World's (world_names)
    'engine.objects': 'add*2 blocks*4 bodies*9 body change*21 cold_of enemy*2 frame_movers*2 frame_now*32 gap*60 ground*5 '
                      'guessed*5 human*11 kills*2 label*23 living*12 looks m*2 note*20 own*42 player_ups players*3 point '
                      'reblock*2 relation*6 relations*4 shot_clock t*7 toggles_of topples used*18 weapon_upgrades world*24 '
                      'xml_of*6',   # objects.bridge (A315): the ManagerBody gap / own / blocks_of moved out of Sim.add
    'engine.orders': '_field _fire_obstacles act acting*5 aim areas blocks body*3 can_hit*4 change*5 engineer_entry*2 fight_field fire_spot firing*3 frame_now*9 gap garrison*2 ground*2 hostile hunts*5 in_range label*10 living*6 members mid_aims mm*2 note*8 own*12 point*2 powers_off production reach*5 relation seen seq*7 short_of_power shot_blocked*4 side_sees*4 team_targets*3 toggles_of used*14 wallet waypoints*8 who world*4 xml_of*2',
    'engine.players': '_life add*3 banned blocks bodies*4 build_frames emp_book frame_now*3 label note own*4 '
                      'produce_out reblock relations script_disabled t*3 unit_construction_disabled upgrade_done wallet*2 world',
    'engine.ports': 'act*2 add*2 add_team_lookup advance ai ai_paused ai_priorities ai_switches anchored*3 areas '
                    'attachments banned base_construction_disabled blocks*2 bodies*6 body*2 books*2 border box_at '
                    'can_build can_hit change*2 countdowns counters death_blasts emp_disabled ending*2 ending_line enemy engineer_entry '
                    'events*4 expected_damage factories firing flags foe frame_now*9 garrison*8 ground*2 happen*2 '
                    'human*5 income input label*3 late_captions leap_press living log*2 looks m*7 markers mm*3 money '
                    'movement_power_press note*4 objectives offers*2 order_build*3 own panel_at pending pick*4 '
                    'player_ups players point*6 power*2 production*5 proto reblock relations sample*2 seen sees '
                    'self_power_press series short_of_power side_sees spellbook_ready step*2 t*2 take_personality team_targets text '
                    'timers unknown unmodeled*2 upgrade_sellers wallet waypoints wfire_press who world',
    'engine.script': '_life*2 _tier_held act*4 active*7 add*5 ai*4 ai_paused*2 ai_priorities ai_switches all_revealed areas*11 '
                     'asked*3 assignments attachment_known_status*2 attacked_by*2 audio_end banned*2 banned_ups*2 '
                     'base_construction_disabled*2 base_power blasts blocks*2 bodies*12 body*57 book_players books*2 '
                     'books_of*3 border*4 buildable camera*2 camera_been*2 can_hit casts*5 change*16 cloaked*3 clock*4 '
                     'commands*3 cond_memory*2 countdowns*3 counters*15 dying*3 end*2 enemy engineer_entry flags*4 frame_now*19 '
                     'gap*19 garrison*29 ground*2 handed*2 has_model_condition hidden_home*2 hidden_members hotspots*3 human*9 '
                     'infiltrators*3 input*2 kills*4 label*11 level*3 library_ai*2 living*24 looks lost_orders m*6 made_frame '
                     'markers members*31 mm*6 model_scripts*2 money*9 money_cap named_team nearest_ref*3 note*34 object_lists '
                     'objectives*2 of_types*12 off_teams*2 on_the_move own*33 peeks personality_of*2 player_team_rel '
                     'player_ups players*8 point*19 power power_at*2 powers_off present*16 production*3 ra3_only*3 reblock*2 '
                     'reinforce*2 relation relations reshroud*3 retail*5 reveal_all*2 reveal_all_until*2 reveal_areas*2 '
                     'revealed_to*2 reveals*3 scenes*4 script_disabled*2 sees*4 selected*2 seq*5 set_model_condition*3 '
                     'sharing*2 short_of_power show_caption show_subtitle spellbook_ready start_camera surfaces t*18 tactical '
                     'team_active*2 team_entered team_player_rel team_team_rel tech_read*2 text*4 timers*2 '
                     'unit_construction_disabled*2 unknown*6 up used*31 video_end wallet*2 waypoints*2 who*5 world*9',
    'engine.state': 'act*5 active add bodies*11 books*4 change*3 flags*4 frame_now garrison*3 ground level m*6 '
                    'money*2 objectives*3 own*8 player_ups*2 players power production*2 reblock refs*2 relations*2 '
                    'script t used*3 world*9',
    'engine.testing': 'add bodies*2 world',
    'engine.world': 'bodies*3 world',
    'simai_run': 'advance who',
    'simbench': 'run waypoints',
    'simbench_peak': 'advance*2 bodies*9 ending money move*2 order_build players step*2 t*4',
    'simproxy': 'advance bodies*5 commands countdowns end ending ending_line enemy*3 forget_sight frame_now*2 guessed '
                'human input label level*2 living*3 log*2 m*8 money note offers own players point*7 production '
                'side_sees t timers*2 world',
    'simrecord': 'advance*3 ending*2 report run*3 t*8 world*4',
    'simshow': 'run',
}
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
                                          'engine.players.tech': _src('engine.players.tech') + "\ndef z(world):\n    world.leap_press(1)\n"})
    assert ('engine.players.tech', 'leap_press', 1, 0) in ratchet_breaks(real)


def _package(module):
    parts = module.split('.')
    return '.'.join(parts[:2]) if parts[0] == 'engine' and len(parts) > 2 else module


def world_names():
    """The kernel World's own names (its methods and the fields it sets): a module's `self.world` is that World
    (Module.world), so `self.world.living()` in engine.modules is the World's service, not the Sim's same-named one."""
    tree = ast.parse(Path(enginefiles.file_of('engine.kernel.world')).read_text(encoding='utf-8'))
    world = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'World')
    return {n.name for n in world.body if isinstance(n, ast.FunctionDef)} | {
        t.attr for n in ast.walk(world) if isinstance(n, ast.Assign) for e in n.targets
        for t in (e.elts if isinstance(e, ast.Tuple) else [e])
        if isinstance(t, ast.Attribute) and getattr(t.value, 'id', None) == 'self'}


def _module_world(mod, v, kernel):
    return (mod.startswith('engine.modules.') and isinstance(v, ast.Attribute) and v.attr == 'world'
            and getattr(v.value, 'id', None) == 'self' and kernel)


def sim_surface(names=None, sources=None):
    """package -> Counter of the Sim names its files reach, one per access point (see SIM_SURFACE); `sources`:
    {module: text} in place of the files. A kernel World name on a module's `self.world` is not counted."""
    names = names if names is not None else set().union(*_layers.sim_members())
    sources = sources if sources is not None else {enginefiles.name_of(p): Path(p).read_text(encoding='utf-8')
                                                   for p in enginefiles.files()}
    kernel = world_names()
    out = collections.defaultdict(collections.Counter)
    for mod, text in sources.items():
        for n in ast.walk(ast.parse(text)) if mod != 'sim' else ():
            v = getattr(n, 'value', None)
            if isinstance(n, ast.Attribute) and n.attr in names and getattr(v, 'id', getattr(v, 'attr', None)) in RECEIVERS \
                    and not _module_world(mod, v, n.attr in kernel):
                out[_package(mod)][n.attr] += 1
    return out


def surface_text(points):
    """A Counter as SIM_SURFACE writes it: 'bodies*4 t' (no '*' = one point)."""
    return ' '.join(n + (f'*{k}' if k > 1 else '') for n, k in sorted(points.items()))


def surface_breaks(found, allowed=SIM_SURFACE):
    """(package, points beyond the list, points the list has that the code no longer makes, the line to write) for
    each package whose access points differ from the list."""
    out = []
    for p in sorted(set(found) | set(allowed)):
        may = collections.Counter({n: int(k or 1) for n, _, k in (w.partition('*') for w in allowed.get(p, '').split())})
        have = found.get(p, collections.Counter())
        if have != may:
            out.append((p, sorted((have - may).elements()), sorted((may - have).elements()), surface_text(have)))
    return out


def test_sim_surface_only_shrinks():
    assert not surface_breaks(sim_surface())


def test_sim_surface_guard_bites():
    """Mutation check: one more access point of a name a package already reaches, or one name swapped for another,
    is caught, by whichever receiver (review rr #8: counting names alone let both through); a stale list too."""
    found = sim_surface({'order_move', 't'},
                        {'engine.players.x': 'def f(sim, a):\n    sim.t\n    sim.t\n    a.order_move\n',
                         'engine.ports.y': 'class P:\n    def g(self):\n        self._w.order_move\n', 'sim': 'sim.t\n'})
    assert found == {'engine.players': {'t': 2}, 'engine.ports': {'order_move': 1}}
    # a module's self.world: the World's living / used are not the Sim's; a Sim-only name still is, so is world.living
    mod = 'class M:\n    def u(self, world):\n        self.world.living()\n        self.world.used\n' \
          '        self.world.order_move\n        world.living()\n'
    assert sim_surface({'living', 'used', 'order_move'}, {'engine.modules.m': mod}) == \
        {'engine.modules': {'order_move': 1, 'living': 1}}
    assert surface_breaks(found, {'engine.players': 't', 'engine.ports': 'order_move'}) == \
        [('engine.players', ['t'], [], 't*2')]
    real = sim_surface()
    old = sorted(real['engine.players'])[0]
    real['engine.players'][old] += 1
    assert surface_breaks(real) == [('engine.players', [old], [], surface_text(real['engine.players']))]
    real['engine.players'][old] -= 1
    new = sorted(set().union(*_layers.sim_members()) - set(real['engine.players']))[0]
    real['engine.players'][new] = real['engine.players'].pop(old)
    assert surface_breaks(real)[0][:3] == ('engine.players', [new] * real['engine.players'][new],
                                           [old] * real['engine.players'][new])
    assert surface_breaks({}, {'engine.players': 'x*2'}) == [('engine.players', [], ['x', 'x'], '')]
