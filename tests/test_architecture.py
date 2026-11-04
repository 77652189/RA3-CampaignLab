"""Architecture guards (ADR 0016, docs/reviews/architecture-2026-11-03.md section 5): ratchets that stop one class of
mess from growing back. Every whitelist below is the CURRENT state written out as a literal set and may only SHRINK.
When a guard fails because something was removed from the code, the fix is to remove it from the set here. Adding to a
set (or raising a ceiling) needs the coordinator.

Files are enumerated with `git ls-files`, so untracked work files, caches and environments never count."""
import ast
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent

# G1: no new experimental/campaign/make_campnewNN.py. The 14 that are still live (the packaging chain 2 3 4 6 7 18, and
# 23..29 + 35 which make_campchrono -> liberty_kit still import); shrink as they are archived.
CAMPNEW_FROZEN = {
    'make_campnew2', 'make_campnew3', 'make_campnew4', 'make_campnew6', 'make_campnew7', 'make_campnew18',
    'make_campnew23', 'make_campnew24', 'make_campnew25', 'make_campnew26', 'make_campnew27', 'make_campnew28',
    'make_campnew29', 'make_campnew35',
}

# G2: dead probes live in experimental/archive/ and nothing outside it may import them (ADR 0016).
ARCHIVE = 'experimental/archive'

# G3a: the only files under experimental/cnv that may spell out the caption action (one outlet for dialogue).
CAPTION_LITERAL = 'SHOW_MILITARY_CAPTION'
CAPTION_ALLOWED = {
    'experimental/cnv/checks/a8.py',
    'experimental/cnv/checks/liberty.py',
    'experimental/cnv/ctx.py',          # the outlet itself (Ctx.say)
    'experimental/cnv/model.py',
    'experimental/cnv/sim.py',
}

# G4: how many tracked .py files still edit sys.path. Only lower it.
SYS_PATH_CEILING = 129

# G5: checks may not reach into missions/maps/devices/units (a check asks the mission, not another module).
CHECK_IMPORT_ALLOWED = {
    'experimental/cnv/checks/a4_before.py',
    'experimental/cnv/checks/clone.py',
    'experimental/cnv/checks/combo.py',
    'experimental/cnv/checks/fence.py',
    'experimental/cnv/checks/liberty.py',
    'experimental/cnv/checks/mech.py',
    'experimental/cnv/checks/reroute.py',
    'experimental/cnv/checks/sight.py',
}

CNV = 'experimental/cnv'
CNV_LAYERS = ('missions', 'maps', 'devices', 'units')


def _tracked():
    out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout
    files = [f for f in out.decode('utf-8').split('\0') if f and (ROOT / f).is_file()]
    assert files, 'git ls-files returned nothing, the guards would pass vacuously'
    return files


def _read(rel):
    return (ROOT / rel).read_text(encoding='utf-8', errors='replace')


def _under(files, folder, suffix=None, deep=True):
    prefix = folder + '/'
    got = [f for f in files if f.startswith(prefix) and (suffix is None or f.endswith(suffix))
           and (deep or '/' not in f[len(prefix):])]
    assert got, f'no tracked files under {folder}: the scan found nothing and would pass vacuously'
    return got


def test_g1_no_new_make_campnew():
    stems = {PurePosixPath(f).stem for f in _under(_tracked(), 'experimental/campaign', '.py', deep=False)
             if PurePosixPath(f).name.startswith('make_campnew')}
    assert stems, 'no make_campnew*.py found, the guard would pass vacuously'
    assert stems <= CAMPNEW_FROZEN, f'new make_campnew files (do not add; use cnv): {sorted(stems - CAMPNEW_FROZEN)}'


def _import_names(source):
    """Every dotted segment and imported name of every import in the file, including imports inside functions."""
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for a in node.names:
                names |= set(a.name.split('.'))
        elif isinstance(node, ast.ImportFrom):
            names |= set((node.module or '').split('.')) | {a.name for a in node.names}
    return names


def test_g2_nothing_imports_the_archive():
    files = _tracked()
    archived = {PurePosixPath(f).stem for f in _under(files, ARCHIVE, '.py')}
    archived.discard('__init__')
    assert archived, 'the archive holds no modules, the guard would pass vacuously'
    bad = {f: sorted(_import_names(_read(f)) & archived) for f in files
           if f.endswith('.py') and not f.startswith(ARCHIVE + '/')}
    bad = {f: v for f, v in bad.items() if v}
    assert not bad, f'live files import archived modules: {bad}'


def test_g3a_caption_action_has_one_outlet():
    hits = {f for f in _under(_tracked(), CNV) if CAPTION_LITERAL in _read(f)}
    assert hits, 'literal not found anywhere, the guard would pass vacuously'
    assert hits <= CAPTION_ALLOWED, f'new files spell the caption action: {sorted(hits - CAPTION_ALLOWED)}'


def test_g4_sys_path_ratchet():
    needles = ('sys.path.' + 'insert', 'sys.path.' + 'append')    # split so this file does not count itself
    py = [f for f in _tracked() if f.endswith('.py') and not f.startswith('experimental/archive/')]   # live code only
    assert py
    count = sum(1 for f in py if any(n in _read(f) for n in needles))
    assert count > 0, 'no sys.path edits found, the guard would pass vacuously'
    assert count <= SYS_PATH_CEILING, f'{count} files edit sys.path, ceiling {SYS_PATH_CEILING}: only lower it'


def _layer_names(files):
    """missions / maps / devices / units, plus every module that is a file in those folders."""
    names = set(CNV_LAYERS)
    for layer in CNV_LAYERS:
        names |= {PurePosixPath(f).stem for f in _under(files, f'{CNV}/{layer}', '.py', deep=False)}
    names.discard('__init__')
    return names


def _strip(module):
    for prefix in ('experimental.cnv.', 'cnv.'):
        if module.startswith(prefix):
            return module[len(prefix):]
    return module


def _imported_tops(source):
    """Top-level name of every import in the file, including imports inside functions."""
    tops = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            tops |= {_strip(a.name).split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = _strip(node.module)
                tops.add(mod.split('.')[0])
                if mod in ('experimental.cnv', 'experimental', 'cnv'):    # from experimental.cnv import units
                    tops |= {a.name for a in node.names}
            else:                                                          # from . import units
                tops |= {a.name for a in node.names}
    return tops


def test_g5_checks_do_not_reach_into_content_layers():
    files = _tracked()
    names = _layer_names(files)
    checks = _under(files, f'{CNV}/checks', '.py', deep=False)
    hits = {f for f in checks if _imported_tops(_read(f)) & names}
    assert hits, 'no check imports a content layer, the guard would pass vacuously'
    assert hits <= CHECK_IMPORT_ALLOWED, f'checks now import content layers: {sorted(hits - CHECK_IMPORT_ALLOWED)}'


def test_g_units_do_not_import_make_campnew2():
    files = _tracked()
    units = _under(files, f'{CNV}/units', '.py', deep=False)
    bad = [f for f in units if any(t.startswith('make_campnew') for t in _imported_tops(_read(f)))]
    assert not bad, f'units import a make_campnew module (use labpaths): {bad}'


def test_g9_devices_do_not_import_the_compiler():
    """A device is an input of plan.py, not its client: the pure words (times, counts, PlanError ...) live in
    plantime.py and the rest comes through the Ctx a device is handed."""
    files = _tracked()
    devices = _under(files, f'{CNV}/devices', '.py', deep=False)
    bad = [f for f in devices if _imported_tops(_read(f)) & {'plan'}]
    assert not bad, f'devices import plan (take plantime or the Ctx): {bad}'


# G-layers (ADR 0016): parts.py was split by layer. model.py (L2, mission data) imports neither contract.py (L5, rule
# checks) nor package.py (L3, packaging); contract.py does not import package.py. The facade parts.py re-exports all
# three, so neither of them may import it back.
LAYER_FORBIDDEN = {
    f'{CNV}/model.py': {'contract', 'package', 'parts'},
    f'{CNV}/contract.py': {'package', 'parts'},
}


def test_g_layers_model_and_contract_do_not_import_upwards():
    files = _tracked()
    for rel, forbidden in LAYER_FORBIDDEN.items():
        assert rel in files, f'{rel} is not tracked, the guard would pass vacuously'
        bad = _imported_tops(_read(rel)) & forbidden
        assert not bad, f'{rel} imports {sorted(bad)}: the dependency direction is model <- contract <- package'


# G7 (ADR 0016): importing the packaging chain changes nothing. make_campnew4/6/7/18 used to point make_campnew2 at
# themselves (NAME, OUT ...) and swap each other's functions on import; that now happens only in their install(),
# which a build calls. Each module's state is taken right after its own import, before anything above it is imported,
# and must be the same once the whole chain and package.py are in. Run in a fresh interpreter: other tests may have
# imported the chain already.
CHAIN = ('make_campnew2', 'make_campnew3', 'make_campnew4', 'make_campnew6', 'make_campnew7', 'make_campnew18')
G7_PROBE = '''
import copy, importlib, sys, types
sys.path[:0] = [{campaign!r}, {cnv!r}]
def state(m):
    return {{k: (v, copy.copy(v) if isinstance(v, (dict, list, set)) else v) for k, v in vars(m).items()
            if not k.startswith('__') and not isinstance(v, types.ModuleType)}}
taken = {{}}
for name in {chain!r}:
    taken[name] = state(importlib.import_module(name))
import package
bad = []
for name, before in taken.items():
    now = vars(sys.modules[name])
    for k, (obj, held) in before.items():
        if now.get(k) is not obj or (isinstance(obj, (dict, list, set)) and obj != held):
            bad.append(name + '.' + k)
assert sys.modules['make_campnew2'].NAME == 'CampNew2', sys.modules['make_campnew2'].NAME
print('G7 BAD', bad)
'''


def test_g7_packaging_chain_has_no_import_side_effects():
    import sys
    probe = G7_PROBE.format(campaign=str(ROOT / 'experimental' / 'campaign'), cnv=str(ROOT / CNV), chain=CHAIN)
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', probe], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert 'G7 BAD []' in r.stdout, f'importing the chain changed: {r.stdout.strip()}'


# G11 (ADR 0016): an acceptance check only observes. contract.observes(mission, test) lists what a check does to the
# level beyond reading it; a check that acts is a device unit test, never evidence for the player's game. The rule
# is held on real checks (one that only counts, one that kills) and on each way a check can act.
G11_PROBE = '''
import sys
sys.path[:0] = [{cnv!r}, {root!r}]
import build, contract
from model import Script, Test, Obj
m, look, _ = build.resolve('sight', 'look')
assert contract.observes(m, look) == [], contract.observes(m, look)
m, win, _ = build.resolve('a4', 'win')
assert any('NAMED_KILL acts' in p for p in contract.observes(m, win)), contract.observes(m, win)
own = 'G11 own counter'
used = next(a for s in m.scripts for x in s.do if isinstance(x, tuple) and x[0] == 'SET_FLAG' for a in x[1:2])
cases = {{
    'reads': Test(scripts=[Script('t', [], [('SET_COUNTER', own, 0), ('INCREMENT_COUNTER', 1, own)])]),
    'acts': Test(scripts=[Script('t', [], [('UNIT_SET_HEALTH', 'x', 100)])]),
    'reveals': Test(scripts=[Script('t', [], [('MAP_REVEAL_ALL_PERM', 'p')])]),
    'overrides': Test(scripts=[Script('t', [], [('SET_FLAG', used, 0)])]),
    'adds': Test(objects=[Obj('AlliedEngineer', 0, 0)]),
}}
print('G11', sorted(k for k, t in cases.items() if contract.observes(m, t)))
'''


def test_g11_acceptance_checks_only_observe():
    import sys
    probe = G11_PROBE.format(cnv=str(ROOT / CNV), root=str(ROOT))
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', probe], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "G11 ['acts', 'adds', 'overrides', 'reveals']" in r.stdout, r.stdout.strip()


# G3b (ADR 0016 phase 3, K1 + K2): everything said in a built level comes from the one queue. contract.said_outside_the_outlet
# holds it on the product of every build (a level's own caption, announcer, voice line or talking head in a script
# that is not `Say k` / a scene's `Phase n line k` / an ending's own is a problem), contract.said_lines_kept that a line
# is lost only by a 闲话 line's own Drop and an ending waits for the floor, and the simulator's timetable of every level
# shows lines at least the strip's 5.4 s apart (the strip stacks lines and clears them together after the last).
# tests/test_talk_queue.py runs the queue itself (order, tiers, expiry, the ending).
G3B_PROBE = '''
import sys
sys.path[:0] = [{cnv!r}, {root!r}]
import build, contract, model, sim
from model import Script
bad = []
for n in sorted(build.MISSIONS):
    m, _, _ = build.resolve(n, '')
    bad += [(n, p) for p in contract.contract(model.merged(m))
            if 'dialogue outlet' in p or 'queued line' in p or 'not 闲话' in p or 'must wait for the floor' in p]
print('G3B builds', len(build.MISSIONS), 'outside', bad[:3])
m, _, _ = build.resolve('a4', '')
m.scripts.append(Script('CNV A4 - Own caption', [], [('SHOW_MILITARY_CAPTION', 'SCRIPT:X', 3.0)]))
print('G3B mutation', len([p for p in contract.contract(model.merged(m)) if 'dialogue outlet' in p]))
close = []
for lv in build.LEVELS:
    s = sim.simulate(lv, until={until})
    said = [t for t, kind, _ in s.log if kind in ('通报', '配音', '原版播报')]
    # a voiced line logs its voice and its caption together: one line
    starts = sorted(set(round(t, 2) for t in said))
    close += [(lv, a, b) for a, b in zip(starts, starts[1:]) if b - a < 5.4]
print('G3B close', close[:5])
'''


def test_g3b_everything_said_comes_from_the_one_queue():
    import sys
    probe = G3B_PROBE.format(cnv=str(ROOT / CNV), root=str(ROOT), until=900.0)
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', probe], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert 'G3B builds' in r.stdout and "outside []" in r.stdout, r.stdout.strip()
    assert 'G3B mutation 1' in r.stdout, r.stdout.strip()
    assert 'G3B close []' in r.stdout, r.stdout.strip()


# G10 (ADR 0016 phase 3, K5): a level's camera moves aim at view points (plan.view_point): the site held inside the
# playable area in force, a half screen from its edge. contract.camera_outside_the_view holds it on the product of every
# build (a MOVE_CAMERA_TO at a waypoint the compiler gave no view rect, or outside it, is a problem).
G10_PROBE = '''
import sys
sys.path[:0] = [{cnv!r}, {root!r}]
import build, contract, model
bad, moves = [], 0
for n in sorted(build.MISSIONS):
    m, _, _ = build.resolve(n, '')
    mm = model.merged(m)
    moves += sum(1 for s in mm.scripts for a in s.do if a[0] == 'MOVE_CAMERA_TO' and not s.name.startswith('Test'))
    bad += [(n, p) for p in contract.contract(mm) if 'camera aims at' in p]
print('G10 builds', len(build.MISSIONS), 'moves', moves, 'bad', bad[:3])
m, _, _ = build.resolve('a4', '')
mm = model.merged(m)
name = next(a[1] for s in mm.scripts for a in s.do if a[0] == 'MOVE_CAMERA_TO')
mm.waypoints[name] = (-500.0, -500.0)                                  # a view point pushed out of its rect
n1 = len(contract.camera_outside_the_view(mm))
print('G10 outside', n1 >= 1)
mm.waypoints['CNV A4 Raw'] = (1500.0, 2500.0)
mm.scripts.append(model.Script('CNV A4 - Raw camera', [], [('MOVE_CAMERA_TO', 'CNV A4 Raw', 2.0, 0.0, 1.0, 1.0)]))
print('G10 raw', len(contract.camera_outside_the_view(mm)) == n1 + 1)
'''


def test_g10_every_camera_move_aims_at_a_view_point():
    import sys
    probe = G10_PROBE.format(cnv=str(ROOT / CNV), root=str(ROOT))
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', probe], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert 'G10 builds' in r.stdout and 'bad []' in r.stdout and 'moves 0' not in r.stdout, r.stdout.strip()
    assert 'G10 outside True' in r.stdout and 'G10 raw True' in r.stdout, r.stdout.strip()


# G6 (ADR 0016 phase 3, K6): nothing in a built level orders one unit by name. A group is a team of the map's own,
# ordered as one through ctx.order / Mission.order (the units join the team in the same script). contract.single_orders
# holds it on the product of every build, and on every check's merged build too (a check's own `Test ...` scripts are
# exempt). The scripts still allowed one are a list of name patterns, only ever deleted from: this test fixes it empty.
G6_LEFT = ()
G6_PROBE = '''
import sys
sys.path[:0] = [{cnv!r}, {root!r}]
import build, contract, model
from model import Script
bad, teamed = [], 0
for n in sorted(build.MISSIONS):
    m, _, _ = build.resolve(n, '')
    mm = model.merged(m)
    teamed += sum(1 for s in mm.scripts for a in s.do if a[0].startswith('TEAM_') or a[0] == 'MOVE_TEAM_TO')
    bad += [(n, p) for p in contract.single_orders(mm, ())]
print('G6 builds', len(build.MISSIONS), 'teamed', teamed > 0, 'bad', bad[:3])
m, _, _ = build.resolve('a4', '')
mm = model.merged(m)
mm.scripts.append(Script('CNV A4 - Own order', [], [('MOVE_NAMED_UNIT_TO', 'UNIT - CNV A4 Truck 1', 'CNV A4 Exit')]))
mm.scripts.append(Script('Test - own order', [], [('NAMED_STOP', 'UNIT - CNV A4 Truck 1')]))
print('G6 mutation', len(contract.single_orders(mm, ())), len(contract.single_orders(mm, ('CNV A4 - Own',))),
      len([p for p in contract.contract(mm) if 'orders one unit' in p]))
print('G6 left', contract.SINGLE_ORDERS_LEFT)
'''


def test_g6_nothing_orders_one_unit_by_name():
    import sys
    probe = G6_PROBE.format(cnv=str(ROOT / CNV), root=str(ROOT))
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', probe], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert 'G6 builds' in r.stdout and 'teamed True' in r.stdout and 'bad []' in r.stdout, r.stdout.strip()
    assert 'G6 mutation 1 0 1' in r.stdout, r.stdout.strip()
    assert f'G6 left {G6_LEFT!r}' in r.stdout, r.stdout.strip()


# G8 (ADR 0016 phase 2): a check builds on the campaign shell too. build.py <level> --shell --check <check> is parsed and
# reaches packaging as the plain mission with the check as a layer (package.check_layer), under a mod name of its own
# (CampShellT) so the release CampShell installed stays as it was. Only a check that only observes (contract.observes,
# G11) gets there; one that acts is refused, or with --unit built as a device unit test under a name of its own
# (CampShellU). The build itself is stubbed: only the wiring is held.
G8_PROBE = '''
import sys
sys.path[:0] = [{cnv!r}]
import build, contract, package, shell
package.check_layer = lambda m, t: ('layer', m, t)
build.resolve = lambda name, check: ('M', check, 'CampA4X')
build.missing_report = lambda m: ''
contract.observes = lambda m, t: [] if t == 'look' else ['NAMED_KILL acts']
parse = build.parse

def run(argv):
    a = parse(argv)
    got = {{}}
    build.parse = lambda argv=None: a
    build.parts.assemble = lambda m, t, name=None, shell=False, layers=(): got.update(
        mission=m, test=t, name=name, shell=shell, layers=layers) or 'staging'
    try:
        build.main()
    except SystemExit as e:
        return 'refused' if 'observe' in str(e) else str(e)
    return got

ok = dict(mission='M', test=None, shell='zh')
seen = [run(['a4', '--shell', '--check', 'look']), run(['a4', '--shell', '--check', 'win']),
        run(['a4', '--shell', '--check', 'win', '--unit'])]
want = [dict(ok, name=shell.NAME + 'T', layers=(('layer', 'M', 'look'),)), 'refused',
        dict(ok, name=shell.NAME + 'U', layers=(('layer', 'M', 'win'),))]
print('G8', seen == want, seen)
'''


def test_g8_a_check_builds_on_the_shell():
    import sys
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', G8_PROBE.format(cnv=str(ROOT / CNV))], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8')     # -X utf8 child; the parent would read gbk
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    assert 'G8 True' in r.stdout, r.stdout.strip()
