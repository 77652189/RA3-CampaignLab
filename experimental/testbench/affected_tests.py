r"""Pick the test files a change can affect, from a per-test coverage map (the "affected tests" picker).

Why: nearly every test runs the simulator (experimental/cnv/sim.py, simai.py) and the engine model, so a change to one
movement rule can turn AI tests red. Running only "my own" test file misses those; the full run takes hours. This tool
asks: which tests ever executed the lines I changed?

Use (from the repository root; the map lives in <WORK>/testmap/, outside git):

    pytest $(python -X utf8 experimental/testbench/affected_tests.py)        # working tree vs origin/main
    python -X utf8 experimental/testbench/affected_tests.py --stats           # how many files, rough time
    python -X utf8 experimental/testbench/affected_tests.py HEAD~3..HEAD      # a commit range
    python -X utf8 experimental/testbench/affected_tests.py --why             # which test file came from which change

Build / refresh the map (a parallel full run with per-test coverage contexts, then store it):

    python -X utf8 -m pytest tests -n <workers> --timeout 3000 -p no:cacheprovider --cov=experimental \
        --cov=<engine model dir> --cov-context=test --cov-report= -q --junitxml=work/logs/junit.xml
    python -X utf8 experimental/testbench/affected_tests.py --save-coverage .coverage --save-durations work/logs/junit.xml

stdout: one test file per line (sorted, no duplicates) -- feed it to pytest. stderr: the reasons and warnings.

How a changed line is matched (always "more rather than fewer"):
  * lines are first moved to the coordinates the coverage was recorded at (meta.json keeps that commit);
  * a changed line is widened to its whole statement (coverage only records a statement's first line);
  * tests that covered that line are taken; a line no test ran (a def header, a module-level constant, a branch never
    taken) widens to the whole function, class or file it sits in; a pure insertion uses the lines next to it;
  * comments and blank lines are ignored;
  * a file that is not in the map (XML, data, new files, tests' helpers) falls back to `git grep -l` over tests/ by
    module or file name, and the output says so;
  * a test file with no coverage record at all (the map is partial) is always picked: nothing says what it touches;
  * the guard tests (docs, architecture, no program addresses, inventory) are always added;
  * keep --timeout at 3000 or more: on Windows pytest-timeout's default method ends the WHOLE xdist worker when one test
    passes the limit ("node down: Not properly terminated"), and single simulator tests run 15-50 min under load;
  * --cmd prints a full pytest command with -n min(8, free GB / 1.5): a simulator-test worker needs about 1.5 GB.
"""
import argparse
import ast
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
try:                                                # labpaths by file path, so this file does not edit sys.path (G4)
    import importlib.util
    _spec = importlib.util.spec_from_file_location('labpaths', os.path.join(ROOT, 'experimental', 'campaign', 'labpaths.py'))
    labpaths = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(labpaths)
    WORK, ENGINE_MODEL = labpaths.WORK, labpaths.ENGINE_MODEL
except Exception:                                   # pragma: no cover - the tool must work on a bare clone
    WORK, ENGINE_MODEL = os.path.join(ROOT, 'work'), os.path.join(os.path.dirname(ROOT), 'RA3-EngineModel')

MAPDIR = os.path.join(WORK, 'testmap')
COVDB = os.path.join(MAPDIR, 'coverage.db')
META = os.path.join(MAPDIR, 'meta.json')
DURATIONS = os.path.join(MAPDIR, 'durations.json')
GUARDS = ['tests/test_docs.py', 'tests/test_architecture.py', 'tests/test_no_program_addresses.py']
GUARD_GLOBS = ['tests/test_inventory*.py']
ENGINE_KEY = 'ENGINE:'          # a key prefix: files of the engine model repository
MAX_WORKERS = 8
GB_PER_WORKER = 1.5          # a simulator test worker peaks around here; the full run lost workers when memory ran out


def available_gb():
    """Free physical memory in GB (psutil if there, else the Windows call); None if unknown."""
    try:
        import psutil
        return psutil.virtual_memory().available / 2 ** 30
    except Exception:
        pass
    try:
        import ctypes

        class Mem(ctypes.Structure):
            _fields_ = [('len', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in
                                                                              ('tot', 'avail', 'pt', 'pa', 'vt', 'va', 'ext')]
        m = Mem()
        m.len = ctypes.sizeof(Mem)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.avail / 2 ** 30
    except Exception:
        return None


def workers(avail=None):
    """How many pytest-xdist workers fit now: min(8, free GB / 1.5), at least 1 (avail: GB, for tests)."""
    avail = available_gb() if avail is None else avail
    return MAX_WORKERS if avail is None else max(1, min(MAX_WORKERS, int(avail / GB_PER_WORKER)))


# ---------------------------------------------------------------- the coverage map

def nums_from_bits(blob):
    """coverage's numbits blob -> the line numbers it holds (bit i of byte n = line n*8+i)."""
    out = []
    for n, byte in enumerate(blob):
        for i in range(8):
            if byte >> i & 1:
                out.append(n * 8 + i)
    return out


def path_key(path):
    """A path recorded in the map -> 'experimental/...' or 'ENGINE:<relative path>' (None: not ours)."""
    p = path.replace('\\', '/')
    marker = '/RA3-EngineModel/'
    if marker in p:
        return ENGINE_KEY + p.rsplit(marker, 1)[1]
    if '/experimental/' in p:
        return 'experimental/' + p.split('/experimental/', 1)[1]
    return None


class CovMap:
    """Read-only view of coverage.db: which test file ran which line of which source file."""

    def __init__(self, dbpath):
        self.db = sqlite3.connect('file:%s?mode=ro' % dbpath.replace('\\', '/'), uri=True)
        self.files = {}
        for fid, path in self.db.execute('select id, path from file'):
            key = path_key(path)
            if key:
                self.files[key] = fid
        self.ctx_file = {}
        for cid, ctx in self.db.execute('select id, context from context'):
            name = ctx.split('|')[0].split('::')[0].replace('\\', '/')
            if name:                                # '' is import time: no test owns it
                self.ctx_file[cid] = name
        self._cache = {}

    def has(self, key):
        return key in self.files

    def _rows(self, key):
        if key not in self._cache:
            rows = []
            for cid, blob in self.db.execute('select context_id, numbits from line_bits where file_id=?',
                                             (self.files[key],)):
                if cid in self.ctx_file:
                    rows.append((self.ctx_file[cid], set(nums_from_bits(blob))))
            self._cache[key] = rows
        return self._cache[key]

    def tests_on(self, key, lines):
        """Test files that executed at least one of `lines` in `key`."""
        lines = set(lines)
        return {t for t, ls in self._rows(key) if ls & lines}

    def executed(self, key, lines):
        lines = set(lines)
        return any(ls & lines for _, ls in self._rows(key))

    def test_files(self):
        """Every test file that has at least one coverage record."""
        return set(self.ctx_file.values())

    def all_tests(self, key):
        return {t for t, _ in self._rows(key)}


# ---------------------------------------------------------------- diffs

HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def parse_diff(text):
    """`git diff -U0` text -> {path: [(a, b, c, d)]}: old start/count, new start/count. '/dev/null' sides are kept
    as a key with an empty hunk list marker: added files are {path: None}."""
    out, cur, added = {}, None, False
    for line in text.splitlines():
        if line.startswith('diff --git'):
            cur, added = None, False
        elif line.startswith('--- '):
            added = line.strip() == '--- /dev/null'
        elif line.startswith('+++ '):
            name = line[4:].strip()
            if name == '/dev/null':
                continue
            cur = name[2:] if name.startswith('b/') else name
            out[cur] = None if added else []
        elif line.startswith('--- a/') and cur is None:
            pass
        else:
            m = HUNK.match(line)
            if m and cur is not None and out.get(cur) is not None:
                a, b, c, d = m.groups()
                out[cur].append((int(a), 1 if b is None else int(b), int(c), 1 if d is None else int(d)))
    return out


def deleted_files(text):
    """Paths deleted by a diff (new side is /dev/null)."""
    out, old = [], None
    for line in text.splitlines():
        if line.startswith('--- '):
            old = line[4:].strip()
        elif line.startswith('+++ ') and line[4:].strip() == '/dev/null' and old:
            out.append(old[2:] if old.startswith('a/') else old)
    return out


def old_side_lines(hunks):
    """Changed lines in the OLD file's numbering: the removed/changed lines, plus the neighbours of a pure insertion
    (after old line a: a and a+1) -- 'more rather than fewer'."""
    lines = set()
    for a, b, c, d in hunks:
        if b:
            lines.update(range(a, a + b))
            if not d:                               # pure deletion: the lines on both sides
                lines.update((a - 1, a + b))
        else:
            lines.update((a, a + 1))
    return {n for n in lines if n >= 1}


def remap_lines(lines, hunks):
    """Move old-numbered lines to the other side of `hunks` (git diff -U0 old new -> new numbering are the NEW
    coordinates of that diff). Lines inside a changed hunk map to that hunk's whole new range."""
    out = set()
    for n in lines:
        shift, hit = 0, None
        for a, b, c, d in hunks:
            if b and a <= n < a + b:
                hit = (c, d)
                break
            if (a + b) <= n if b else a < n:        # the hunk lies wholly before line n
                shift += d - b
            else:
                break
        if hit:
            c, d = hit
            out.update(range(c, c + max(d, 1)))
            out.update((c - 1,))
        else:
            out.add(n + shift)
    return {n for n in out if n >= 1}


# ---------------------------------------------------------------- source structure (at the coverage commit)

class Source:
    """Statement and scope structure of one Python source text."""

    def __init__(self, text):
        self.text = text
        self.lines = text.splitlines()
        self.tree = None
        try:
            self.tree = ast.parse(text)
        except SyntaxError:
            pass
        self.stmts = []      # (first, last-of-header-or-whole, node) for simple statements and compound headers
        self.scopes = []     # (start, end, kind, node) for defs and classes (decorators included)
        if self.tree:
            for node in ast.walk(self.tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start = min([node.lineno] + [x.lineno for x in node.decorator_list])
                    kind = 'class' if isinstance(node, ast.ClassDef) else 'def'
                    self.scopes.append((start, node.end_lineno, kind, node))
                if isinstance(node, ast.stmt):
                    body = getattr(node, 'body', None)
                    compound = isinstance(body, list) and body and isinstance(body[0], ast.stmt)
                    if compound:                        # the header only: its body statements are their own entries
                        self.stmts.append((node.lineno, max(node.lineno, body[0].lineno - 1), node))
                    else:
                        self.stmts.append((node.lineno, node.end_lineno, node))

    def inert(self, n):
        """Blank or comment-only line."""
        if n < 1 or n > len(self.lines):
            return True
        s = self.lines[n - 1].strip()
        return not s or s.startswith('#')

    def statement_first(self, n):
        """First line of the innermost statement (or compound header) containing line n; None if none."""
        best = None
        for first, last, node in self.stmts:
            if first <= n <= last and (best is None or (last - first) < (best[1] - best[0])):
                best = (first, last)
        return best[0] if best else None

    def scope_of(self, n):
        """Innermost def (else class) range containing n: (start, end, kind) or None (module level)."""
        best = None
        for start, end, kind, node in self.scopes:
            if start <= n <= end and (best is None or (end - start) < (best[1] - best[0])):
                best = (start, end, kind)
        return best


# ---------------------------------------------------------------- the selection

def select(cov, key, lines, source):
    """Test files (a set) covering the changed `lines` (coverage-commit numbering) of the covered file `key`.
    `source` is a Source of the file at the coverage commit (None: parse failed -> every test touching the file)."""
    if source is None or source.tree is None:
        return cov.all_tests(key)
    tests = set()
    for n in sorted(lines):
        if n > len(source.lines):
            n = len(source.lines)
        if source.inert(n):
            continue
        first = source.statement_first(n)
        probe = {first} if first else {n}
        hit = cov.tests_on(key, probe)
        if hit:
            tests |= hit
            continue
        scope = source.scope_of(n)
        if scope:                                   # a line no test ran: anything run inside the def / class
            tests |= cov.tests_on(key, set(range(scope[0] + 1, scope[1] + 1)))
        else:                                       # module level (runs at import): every test on the file
            tests |= cov.all_tests(key)
    return tests


def name_fallback(path, tests_dir_files):
    """Test files that mention the module or file name (git grep -w -F)."""
    base = os.path.basename(path)
    stem = base[:-3] if base.endswith('.py') else base
    found = set()
    for pat in {stem, base}:
        r = subprocess.run(['git', 'grep', '-l', '-w', '-F', '-e', pat, '--', 'tests/'], cwd=ROOT,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        found.update(x.strip() for x in r.stdout.splitlines() if x.strip().endswith('.py'))
    return found


# ---------------------------------------------------------------- git glue

def git(repo, *args):
    r = subprocess.run(['git', '-C', repo] + list(args), capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.stdout if r.returncode == 0 else ''


def git_show(repo, commit, path):
    r = subprocess.run(['git', '-C', repo, 'show', '%s:%s' % (commit, path)], capture_output=True)
    return r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else None


def repo_diff(repo, spec):
    """(diff text, old-side commit) for one repository. spec None: working tree vs origin/main (ours) / HEAD
    (engine model, which has no origin we trust); 'A..B' or 'A B': a range."""
    if spec and '..' in spec:
        a, b = spec.split('..', 1)
        a, b = a or 'HEAD', b or 'HEAD'
        a = git(repo, 'merge-base', a, b).strip() if '...' in spec else a
        return git(repo, 'diff', '-U0', '--no-renames', a, b), a
    base = spec or ('origin/main' if os.path.abspath(repo) == os.path.abspath(ROOT) else 'HEAD')
    if not git(repo, 'rev-parse', '--verify', '-q', base).strip():
        base = 'HEAD'
    return git(repo, 'diff', '-U0', '--no-renames', base), base


def untracked(repo):
    return [x for x in git(repo, 'ls-files', '--others', '--exclude-standard').splitlines() if x]


# ---------------------------------------------------------------- the driver

def pick(cov, changes, sources, remaps, fallback):
    """changes: [(key, display path, hunks or None for an added file, deleted?)];
    sources[key] -> Source at the coverage commit; remaps[key](lines) -> lines in coverage numbering.
    Returns (tests, reasons {test: [why]}, fallbacks [display path])."""
    tests, why, fell = set(), {}, []

    def add(found, reason):
        for t in found:
            tests.add(t)
            why.setdefault(t, [])
            if reason not in why[t] and len(why[t]) < 3:
                why[t].append(reason)

    for key, shown, hunks, _deleted in changes:
        if shown.startswith('tests/') and re.search(r'tests/test_[^/]*\.py$', shown):
            add({shown}, 'changed test')
            continue
        if hunks is not None and cov is not None and cov.has(key) and key in sources:
            lines = remaps[key](old_side_lines(hunks))
            add(select(cov, key, lines, sources[key]), 'lines of ' + shown)
            continue
        fell.append(shown)
        add(fallback(shown), 'by name: ' + shown)
    return tests, why, fell


def unrecorded(cov):
    """Test files with no coverage record at all (the map is partial, or the test runs no measured code):
    nothing says what they touch, so they are always picked."""
    d = os.path.join(ROOT, 'tests')
    allt = {'tests/' + f for f in os.listdir(d) if re.match(r'test_.*\.py$', f)}
    return sorted(allt - cov.test_files())


def guards():
    out = set(GUARDS)
    d = os.path.join(ROOT, 'tests')
    for f in os.listdir(d):
        if re.match(r'test_inventory.*\.py$', f):
            out.add('tests/' + f)
    return {g for g in out if os.path.exists(os.path.join(ROOT, g))}


def estimate(files, durations, n=MAX_WORKERS):
    """(serial seconds, parallel seconds over n workers) from per-file durations; unknown files get the median."""
    known = sorted(durations.values())
    med = known[len(known) // 2] if known else 30.0
    ds = [durations.get(f, med) for f in files]
    serial = sum(ds)
    return serial, max(serial / n, max(ds) if ds else 0.0), sum(1 for f in files if f not in durations)


def save_durations(junit_path):
    """junit xml -> {test file: seconds of CPU wall in that file} (summed over its tests)."""
    out = {}
    for tc in ET.parse(junit_path).getroot().iter('testcase'):
        cls = tc.get('classname', '')
        parts = cls.split('.')
        i = next((k for k, p in enumerate(parts) if p.startswith('test_')), None)
        if i is None:
            continue
        f = 'tests/' + parts[i] + '.py'
        out[f] = out.get(f, 0.0) + float(tc.get('time', 0))
    os.makedirs(MAPDIR, exist_ok=True)
    with open(DURATIONS, 'w', encoding='utf-8') as fh:
        json.dump({k: round(v, 2) for k, v in sorted(out.items())}, fh, indent=0)
    return out


def save_coverage(src):
    os.makedirs(MAPDIR, exist_ok=True)
    shutil.copyfile(src, COVDB)
    meta = {'commit': git(ROOT, 'rev-parse', 'HEAD').strip(),
            'engine_commit': git(ENGINE_MODEL, 'rev-parse', 'HEAD').strip() if os.path.isdir(ENGINE_MODEL) else '',
            'dirty': bool(git(ROOT, 'status', '--porcelain', '-uno').strip())}
    with open(META, 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, indent=1)
    return meta


def load_json(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def gather(spec):
    """Real changes from git: [(key, shown, hunks|None, deleted)], plus per-repo coverage-commit tools."""
    meta = load_json(META)
    changes, sources, remaps = [], {}, {}
    repos = [('', ROOT, spec, meta.get('commit'))]
    if os.path.isdir(os.path.join(ENGINE_MODEL, '.git')) or os.path.isfile(os.path.join(ENGINE_MODEL, '.git')):
        repos.append((ENGINE_KEY, ENGINE_MODEL, None, meta.get('engine_commit')))
    for prefix, repo, sp, covc in repos:
        text, base = repo_diff(repo, sp)
        for path, hunks in parse_diff(text).items():
            key = path if not prefix else prefix + path
            changes.append((key, path if not prefix else 'RA3-EngineModel/' + path, hunks, False))
            c = covc or base
            old = git_show(repo, base, path)
            if old is None or hunks is None:
                continue
            at_c = old if c == base else git_show(repo, c, path)
            if at_c is None:
                continue
            sources[key] = Source(at_c)
            if c == base:
                remaps[key] = lambda ls: ls
            else:
                h = parse_diff(git(repo, 'diff', '-U0', '--no-renames', base, c, '--', path)).get(path) or []
                remaps[key] = (lambda hh: (lambda ls: remap_lines(ls, hh)))(h)
        for path in deleted_files(text):
            key = path if not prefix else prefix + path
            changes.append((key, path if not prefix else 'RA3-EngineModel/' + path, None, True))
        if not prefix and sp is None:
            for path in untracked(repo):
                changes.append((path, path, None, False))
    return changes, sources, remaps, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('range', nargs='?', help="commit range A..B (default: working tree vs origin/main)")
    ap.add_argument('--stats', action='store_true', help='count and rough running time of the picked files')
    ap.add_argument('--why', action='store_true', help='print the reason after each file (stderr)')
    ap.add_argument('--save-coverage', metavar='.coverage', help='store a coverage file as the map')
    ap.add_argument('--save-durations', metavar='junit.xml', help='store per-file durations from a junit report')
    ap.add_argument('--no-guards', action='store_true')
    ap.add_argument('--cmd', action='store_true', help='print the whole pytest command instead of the file list '
                    '(workers = min(8, free GB / 1.5))')
    args = ap.parse_args(argv)
    if args.save_coverage or args.save_durations:
        if args.save_coverage:
            print('map saved:', save_coverage(args.save_coverage), file=sys.stderr)
        if args.save_durations:
            print('durations of %d files saved' % len(save_durations(args.save_durations)), file=sys.stderr)
        return 0
    cov = None
    if os.path.exists(COVDB):
        cov = CovMap(COVDB)
    else:
        print('no coverage map at %s: every file falls back to name matching (build it: see --help)' % COVDB,
              file=sys.stderr)
    changes, sources, remaps, meta = gather(args.range)
    if cov and meta.get('commit'):
        behind = git(ROOT, 'rev-list', '--count', '%s..HEAD' % meta['commit']).strip()
        if behind.isdigit() and int(behind) > 100:
            print('warning: the coverage map is %s commits old (see the rebuild advice)' % behind, file=sys.stderr)
    elif cov:
        print('warning: meta.json missing: coverage line numbers assumed to match the diff base', file=sys.stderr)
    tests, why, fell = pick(cov, changes, sources, remaps, lambda p: name_fallback(p, None))
    for g in guards() if not args.no_guards else ():
        tests.add(g)
        why.setdefault(g, []).append('guard')
    if cov:
        for t in unrecorded(cov):                   # no coverage record: we cannot tell, so always run
            tests.add(t)
            why.setdefault(t, []).append('no coverage record: always')
        print('always selected (no coverage record): %d test files' % len(unrecorded(cov)), file=sys.stderr)
    tests = {t for t in tests if os.path.exists(os.path.join(ROOT, t))}
    out = sorted(tests)
    n = workers()
    if args.cmd:
        print('python -X utf8 -m pytest -n %d --timeout 3000 -p no:cacheprovider -q %s' % (n, ' '.join(out)))
    else:
        for t in out:
            print(t)
    for p in fell:
        print('by name (not in the coverage map): %s' % p, file=sys.stderr)
    if args.why:
        for t in out:
            print('  %s <- %s' % (t, '; '.join(why.get(t, []))), file=sys.stderr)
    if args.stats:
        durations = load_json(DURATIONS)
        serial, par, unknown = estimate(out, durations, n)
        total = len(durations) or None
        print('%d test files picked%s; %d changed files (%d by name); ~%.0f min serial, ~%.0f min with %d workers%s'
              % (len(out), ' of %d' % total if total else '', len(changes), len(fell), serial / 60, par / 60, n,
                 ' (%d files without a recorded duration)' % unknown if unknown else ''), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
