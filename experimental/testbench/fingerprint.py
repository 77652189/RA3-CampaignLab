"""Build fingerprint: proof that a refactor leaves the built mods byte-identical (docs/reviews/architecture-2026-11-03.md
section 4). Builds the three targets into work/fingerprint/<label>/out (CNV_OUT_DIR, parts.assemble: never into the
installed Mods) and records, per target, the sha1 of every file inside each .big plus every other file of the mod folder.
    python -I -X utf8 experimental/testbench/fingerprint.py record <label> [--verbose]
    python -I -X utf8 experimental/testbench/fingerprint.py diff <labelA> <labelB> [--verbose]   (exit 0 = identical)
Full build output: work/logs/fingerprint_<label>_<target>.log."""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
import labpaths  # noqa: E402
sys.path.insert(0, labpaths.ROOT)
from ra3voice import big  # noqa: E402

BUILD = os.path.join(labpaths.ROOT, 'experimental', 'cnv', 'build.py')
# target -> (build.py arguments, the mod folder it makes)
TARGETS = {'a4': (['a4'], 'CampA4'),
           'shell': (['a4', '--shell'], 'CampShell'),
           'shell_intl': (['a4', '--shell', '--lang', 'intl'], 'CampShellEn')}
FP = os.path.join(labpaths.WORK, 'fingerprint')
CAP = 30                                        # diff lines per target without --verbose


def mods_stamp():
    """(newest mtime, file count) under the installed Mods folder: a build here must leave it as it was."""
    root = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods')
    newest, count = 0.0, 0
    for d, _, names in os.walk(root):
        for n in names:
            newest, count = max(newest, os.path.getmtime(os.path.join(d, n))), count + 1
    return newest, count


def fingerprint(mod_dir):
    """{file: sha1} of a mod folder: 'x.big!inner\\name' for each file inside a .big, the relative path for the rest."""
    out = {}
    for d, _, names in os.walk(mod_dir):
        for n in sorted(names):
            path = os.path.join(d, n)
            rel = os.path.relpath(path, mod_dir).replace('\\', '/')
            if not n.lower().endswith('.big'):
                with open(path, 'rb') as f:
                    out[rel] = hashlib.sha1(f.read()).hexdigest()
                continue
            with open(path, 'rb') as f:
                for name, off, size in big.read_index(path):
                    f.seek(off)
                    key, k = f'{rel}!{name}', 1
                    while key in out:               # a name twice in one big: told apart by its order
                        k += 1
                        key = f'{rel}!{name}#{k}'
                    out[key] = hashlib.sha1(f.read(size)).hexdigest()
    return out


def record(label, verbose):
    out_dir = os.path.join(FP, label, 'out')
    logs = os.path.join(labpaths.WORK, 'logs')
    shutil.rmtree(out_dir, ignore_errors=True)  # a label recorded again starts clean (only ever inside work/fingerprint)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(logs, exist_ok=True)
    before, result, bad = mods_stamp(), {}, 0
    for target, (args, mod) in TARGETS.items():
        log = os.path.join(logs, f'fingerprint_{label}_{target}.log')
        with open(log, 'wb') as f:
            code = subprocess.run([sys.executable, '-I', '-X', 'utf8', BUILD] + args, cwd=labpaths.ROOT, stdout=f,
                                  stderr=subprocess.STDOUT, env=dict(os.environ, CNV_OUT_DIR=out_dir)).returncode
        mod_dir = os.path.join(out_dir, mod)
        if code or not os.path.isdir(mod_dir):
            tail = open(log, encoding='utf-8', errors='replace').read().splitlines()[-5:]
            print(f'{target}: BUILD FAILED (exit {code}), see {log}\n  ' + '\n  '.join(tail))
            bad += 1
            continue
        result[target] = fingerprint(mod_dir)
        print(f'{target}: {len(result[target])} files ({mod})' + (f' log {log}' if verbose else ''))
    if mods_stamp() != before:
        print('WARNING: the installed Mods folder changed during the builds (another build, or CNV_OUT_DIR ignored)')
    if bad:
        sys.exit(1)
    path = os.path.join(FP, f'{label}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
    print('wrote', path)


def diff(a, b, verbose):
    ra, rb = (json.load(open(os.path.join(FP, f'{x}.json'), encoding='utf-8')) for x in (a, b))
    same = True
    for target in TARGETS:
        fa, fb = ra.get(target, {}), rb.get(target, {})
        only_a, only_b = sorted(set(fa) - set(fb)), sorted(set(fb) - set(fa))
        changed = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
        if not (only_a or only_b or changed):
            print(f'{target}: identical ({len(fa)} files)')
            continue
        same = False
        print(f'{target}: DIFFERENT, only in {a} {len(only_a)}, only in {b} {len(only_b)}, changed {len(changed)}')
        lines = [f'  only in {a}: {k}' for k in only_a] + [f'  only in {b}: {k}' for k in only_b] + \
                [f'  changed: {k}' for k in changed]
        print('\n'.join(lines if verbose else lines[:CAP]))
        if not verbose and len(lines) > CAP:
            print(f'  ... {len(lines) - CAP} more (--verbose)')
    sys.exit(0 if same else 1)


if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if x != '--verbose']
    verbose = '--verbose' in sys.argv
    if len(args) == 2 and args[0] == 'record':
        record(args[1], verbose)
    elif len(args) == 3 and args[0] == 'diff':
        diff(args[1], args[2], verbose)
    else:
        sys.exit(__doc__)
