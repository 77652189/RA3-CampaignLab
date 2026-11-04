"""Architecture guards (ADR 0016, docs/reviews/architecture-2026-11-03.md section 5): ratchets that stop one class of
mess from growing back. Every whitelist below is the CURRENT state written out as a literal set and may only SHRINK.
When a guard fails because something was removed from the code, the fix is to remove it from the set here. Adding to a
set (or raising a ceiling) needs the coordinator.

Files are enumerated with `git ls-files`, so untracked work files, caches and environments never count."""
import ast
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent

# G1: no new experimental/campaign/make_campnewNN.py. All 38 that exist today; shrink as they are archived.
CAMPNEW_FROZEN = {
    'make_campnew', 'make_campnew2', 'make_campnew3', 'make_campnew4', 'make_campnew5', 'make_campnew6',
    'make_campnew7', 'make_campnew8', 'make_campnew9', 'make_campnew10', 'make_campnew11', 'make_campnew12',
    'make_campnew13', 'make_campnew14', 'make_campnew15', 'make_campnew16', 'make_campnew17', 'make_campnew18',
    'make_campnew19', 'make_campnew20', 'make_campnew21', 'make_campnew22', 'make_campnew23', 'make_campnew24',
    'make_campnew25', 'make_campnew26', 'make_campnew27', 'make_campnew28', 'make_campnew29', 'make_campnew30',
    'make_campnew31', 'make_campnew32', 'make_campnew33', 'make_campnew34', 'make_campnew35', 'make_campnew36',
    'make_campnew37', 'make_campnew38',
}

# G3a: the only files under experimental/cnv that may spell out the caption action (one outlet for dialogue).
CAPTION_LITERAL = 'SHOW_MILITARY_CAPTION'
CAPTION_ALLOWED = {
    'experimental/cnv/checks/a8.py',
    'experimental/cnv/checks/liberty.py',
    'experimental/cnv/devices/carrier.py',
    'experimental/cnv/devices/horn.py',
    'experimental/cnv/missions/a8.py',
    'experimental/cnv/missions/festival_parts.py',
    'experimental/cnv/missions/j4.py',
    'experimental/cnv/parts.py',
    'experimental/cnv/plan.py',
    'experimental/cnv/sim.py',
}

# G4: how many tracked .py files still edit sys.path. Only lower it.
SYS_PATH_CEILING = 159

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


def test_g3a_caption_action_has_one_outlet():
    hits = {f for f in _under(_tracked(), CNV) if CAPTION_LITERAL in _read(f)}
    assert hits, 'literal not found anywhere, the guard would pass vacuously'
    assert hits <= CAPTION_ALLOWED, f'new files spell the caption action: {sorted(hits - CAPTION_ALLOWED)}'


def test_g4_sys_path_ratchet():
    needles = ('sys.path.' + 'insert', 'sys.path.' + 'append')    # split so this file does not count itself
    py = [f for f in _tracked() if f.endswith('.py')]
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
