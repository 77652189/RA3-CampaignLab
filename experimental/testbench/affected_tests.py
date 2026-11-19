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

    python -X utf8 -m pytest tests -n <workers> -p no:cacheprovider --cov=experimental \
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
  * the guard layer (every test file under tests/guards/) and the inventory tests are always added;
  * the map and the durations name a test by the path it had when they were recorded: a test file moved since (into
    a layer folder, ADR 0035) is found by its file name, which is unique under tests/ (tests/guards/test_layers.py);
  * no --timeout: tests/conftest.py gives every test its layer's limit (time_budget.TEST_TIMEOUT, T7), and that marker
    wins over the command line; past it pytest-timeout ends the xdist worker ("crashed while running <test id>");
  * --cmd prints a full pytest command with -n min(8, free GB / 1.5, the CPU tokens free now, 2): a simulator-test
    worker needs about 1.5 GB, and the machine's heavy jobs share one token pool (cpupool.py; the run waits for its
    tokens, tests/conftest.py; one run takes at most 2 of them unless RA3_CPU_EXCLUSIVE=1, T5c).

The simulator's files (simcoverage.sim_files(): sim.py, simproxy.py and the parts they import -- sim*.py, or
experimental/cnv/engine/... once step 10 moves them; cnv/enginefiles.py says which files those are) go by import
instead (ADR 0029 consequence 3; the map was recorded before the blocks moved out of sim.py, and it counts "ran it" as
"depends on it"): ImportGraph reads every import (and every 'x.py' string) of experimental/ and tests/ as they are now;
  * a part module is picked for the tests that import it, directly or through other files -- but not through the
    facade sim.py: a whole-game replay that only imports sim is not a test of simheal -- and for the tests of the
    facade (they reach sim, by themselves or through simsmall) that name a handle of it on Sim: a forwarder
    (`.autoheal`) or the attribute holding it (`.heal`); found inside one test, only that test is run ('file::test');
  * in sim.py, a changed forwarder (a Sim method of at most 3 statements naming a part module) or an import line of
    a part picks that part's importers and the facade tests naming the changed method; code still in sim.py goes to
    the coverage map as before (it did not move);
  * a part no test imports or names falls back to the coverage map, then to name matching;
  * the always-picked tests without a coverage record are picked only when some change went to the coverage map;
  * a range A..B is read against the tree as it is now; --coverage-only gives the pick before ADR 0029.

The daily pick leaves out the replay tests (tests/replay_tests.txt: whole-game and bench-mission replays, marked
`replay` by tests/conftest.py) unless the change edits that test file itself; --with-replays keeps them. The full run
(pytest tests) still runs them all; `pytest -m "not replay"` is the daily full set.
"""
import argparse
import ast
import importlib.util
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
# labpaths by file path, so this file does not edit sys.path (G4)
_spec = importlib.util.spec_from_file_location('labpaths', os.path.join(ROOT, 'experimental', 'campaign', 'labpaths.py'))
labpaths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(labpaths)
WORK, ENGINE_MODEL = labpaths.WORK, labpaths.ENGINE_MODEL
# which files are the simulator's and how a module name maps to one (sim*, engine.x.y): one place, by file path too
_spec = importlib.util.spec_from_file_location('enginefiles', os.path.join(ROOT, 'experimental', 'cnv', 'enginefiles.py'))
enginefiles = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(enginefiles)

MAPDIR = os.path.join(WORK, 'testmap')
COVDB = os.path.join(MAPDIR, 'coverage.db')
META = os.path.join(MAPDIR, 'meta.json')
DURATIONS = os.path.join(MAPDIR, 'durations.json')
LAYERS = ('modules', 'conformance', 'golden', 'guards', 'content', 'tools')   # tests/<layer>/ (docs/engine/testing.md)
GUARD_LAYER = 'tests/guards'           # every test file in it is always picked
GUARD_NAMES = re.compile(r'test_inventory.*\.py$')   # and these, wherever they sit under tests/
ENGINE_KEY = 'ENGINE:'          # a key prefix: files of the engine model repository
REPLAYS = os.path.join(ROOT, 'tests', 'replay_tests.txt')
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


def _cpupool():
    spec = importlib.util.spec_from_file_location('_cpupool', os.path.join(HERE, 'cpupool.py'))
    cpupool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cpupool)
    return cpupool


def cpu_tokens():
    """The machine's CPU tokens free now (cpupool, T5: every heavy job on the machine shares them); None if unknown."""
    try:
        return _cpupool().free_now()
    except Exception:                               # pragma: no cover - the tool must work on a bare clone
        return None


def cpu_cap():
    """Tokens one run may take (cpupool.cap(), T5c: 2); None for an exclusive run (RA3_CPU_EXCLUSIVE=1) or unknown."""
    if os.environ.get('RA3_CPU_EXCLUSIVE', '') not in ('', '0'):
        return None
    try:
        return _cpupool().cap()
    except Exception:                               # pragma: no cover
        return None


def workers(avail=None, tokens=None, cap=None):
    """How many pytest-xdist workers fit now: min(8, free GB / 1.5, the CPU tokens free now, the most one run may
    take), at least 1 (avail: GB, tokens: free tokens, cap: that most -- default cpu_cap() -- for tests). The run waits
    for that many tokens when it starts (tests/conftest.py): another line taking them first only queues it."""
    avail = available_gb() if avail is None else avail
    tokens = cpu_tokens() if tokens is None else tokens
    cap = cpu_cap() if cap is None else cap
    n = MAX_WORKERS if avail is None else min(MAX_WORKERS, int(avail / GB_PER_WORKER))
    if tokens is not None:
        n = min(n, tokens)
    if cap is not None:
        n = min(n, cap)
    return max(1, n)


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

    def __init__(self, dbpath, where=None):
        where = where or current_path          # a test recorded at an old path -> where it is now
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
                self.ctx_file[cid] = where(name)
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


# ---------------------------------------------------------------- the import graph (ADR 0029: the simulator's files)

FACADE = 'experimental/cnv/sim.py'      # the Sim facade: importing it does not count as importing the parts it imports
CNV = 'experimental/cnv'
RUN_ENDS = ('sim', 'simproxy')          # simcoverage.RUN_ENDS: the player-style run
SEARCH = (CNV, 'experimental/campaign', '', 'tests')    # where a bare import is looked for after the importer's folder
SKIP_DIRS = {'__pycache__', 'archive', 'node_modules'}
PY_STRING = re.compile(r'^(?:[\w./\\-]*[/\\])?([A-Za-z_]\w*)\.py$')     # 'simai.py', 'experimental/cnv/simai.py'
FORWARDER_STMTS = 3                     # a Sim method this short that reaches a part module is that module's forwarder


class ImportGraph:
    """Who imports whom among the Python files of experimental/ and tests/ (as they are in the working tree).

    An edge is an import (top level or inside a function: a lazy import counts), or a string constant naming a .py
    file (importlib.util.spec_from_file_location(..., 'simai.py'), a script a subprocess runs). Bare names resolve
    the way the folders' sys.path edits do: the importer's own folder, then experimental/cnv, experimental/campaign,
    the repository root, tests/; a name found nowhere is not ours (stdlib, the engine model, numpy)."""

    def __init__(self, root=None):
        self.root = root or ROOT
        self.paths = set()
        for top in ('experimental', 'tests'):
            for d, dirs, fs in os.walk(os.path.join(self.root, top)):
                dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith('.')]
                rel = os.path.relpath(d, self.root).replace('\\', '/')
                self.paths.update(rel + '/' + f for f in fs if f.endswith('.py'))
        self.imports, self.strings, self._reach = {}, {}, {}
        self.registries = {}    # {package __init__ that loads its folder: the files it loads that way}
        for p in self.paths:
            self.imports[p], self.strings[p] = self._edges(p)

    def _file(self, base, dotted):
        """base/a/b.py or base/a/b/__init__.py, if it is one of ours."""
        stem = '/'.join(x for x in (base, dotted.replace('.', '/')) if x)
        for cand in (stem + '.py', stem + '/__init__.py'):
            if cand in self.paths:
                return cand
        return None

    def resolve(self, dotted, frm):
        for base in (os.path.dirname(frm),) + SEARCH:
            f = self._file(base, dotted)
            if f:
                return f
        return None

    def packages(self, dotted, frm):
        """import a.b.c runs a/__init__.py and a/b/__init__.py before a/b/c.py: all of them, from the folder a.b.c
        resolves in (empty if it is not ours)."""
        parts = dotted.split('.')
        for base in (os.path.dirname(frm),) + SEARCH:
            if self._file(base, dotted):
                return {self._file(base, '.'.join(parts[:i])) for i in range(1, len(parts) + 1)}
        return set()

    def _edges(self, p):
        try:
            tree = ast.parse(open(os.path.join(self.root, p), encoding='utf-8').read())
        except (OSError, SyntaxError, ValueError):
            return set(), set()
        imp, strs = set(), set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    imp.update(self.packages(a.name, p))
            elif isinstance(n, ast.ImportFrom):
                if n.level:                                 # relative: from the package folder up
                    base = p.rsplit('/', n.level)[0]
                    mod = self._file(base, n.module) if n.module else self._file(base, '')
                    subs = [self._file(base, '.'.join(x for x in (n.module, a.name) if x)) for a in n.names]
                else:
                    imp.update(self.packages(n.module, p))
                    mod = None
                    subs = [self.resolve(n.module + '.' + a.name, p) for a in n.names]
                imp.add(mod)
                imp.update(subs)                            # from checks import a1: the submodule checks/a1.py
            elif isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) < 200:
                m = PY_STRING.match(n.value.strip())
                if m:
                    whole = n.value.strip().replace('\\', '/')
                    strs.add(whole if whole in self.paths else self.resolve(m.group(1), p))
        if p.endswith('/__init__.py') and enginefiles.loads_its_folder(tree):     # engine/modules: every file in it
            folder = p[:-len('__init__.py')]
            loaded = {f for f in self.paths if f.startswith(folder) and f != p and
                      ('/' not in f[len(folder):] or f[len(folder):].count('/') == 1 and f.endswith('/__init__.py'))}
            self.registries[p] = loaded
            imp.update(loaded)
        return imp - {None, p}, strs - {None, p}

    def edges(self, p):
        return self.imports.get(p, set()) | self.strings.get(p, set())

    def reach(self, start):
        """Every file `start` reaches by import; the facade is reached but not walked through (unless it is start),
        and so is a registry -- a package __init__ that loads its folder (engine/modules, step K1.5): importing one
        module file of it (simproxy: from engine.modules import lifetime) loads them all, but only to register them;
        they run when a Sim schedules them, which users() finds by their names, as for the facade."""
        if start not in self._reach:
            seen, todo = set(), [start]
            while todo:
                f = todo.pop()
                if f in seen:
                    continue
                seen.add(f)
                if f == start:
                    todo += sorted(self.edges(f))
                elif f != FACADE:
                    todo += sorted(self.edges(f) - self.registries.get(f, set()))
            self._reach[start] = seen
        return self._reach[start]

    def test_files(self):
        return sorted(p for p in self.paths if is_test_file(p))

    def importers(self, target):
        """Test files that import `target`, directly or through files other than the facade."""
        return {t for t in self.test_files() if t != target and target in self.reach(t)}

    def facade_tests(self):
        """Test files that reach the facade (they build a Sim -- themselves or through simsmall -- and test it) or a
        registry (they can schedule the modules it loads)."""
        return {t for t in self.test_files() if FACADE in self.reach(t) or self.registries.keys() & self.reach(t)}

    def handles(self):
        """{part module: names on Sim that lead to it} off the facade as it is now: its forwarders' names and the Sim
        attributes holding the part (self.heal = simheal.Heal()) -- what a test of the facade calls the part by."""
        if '_handles' not in self.__dict__:
            try:
                src = Source(open(os.path.join(self.root, FACADE), encoding='utf-8').read())
            except OSError:
                src = None
            parts = self.part_names(src)
            found, _ = facade_parts(src, set(range(1, len(src.lines) + 1)) if src else set(), parts)
            for node in ast.walk(src.tree) if src and src.tree else ():
                if isinstance(node, ast.Assign):
                    mods = _part_names(node.value, parts)
                    for t in node.targets:
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == 'self':
                            for m in mods:
                                found.setdefault(m, set()).add(t.attr)
            self._handles = found
        return self._handles

    def users(self, target):
        """Test files a change to the simulator's file `target` can affect: its importers, and the tests of the facade
        that name a handle of it (simheal.py: the tests that call .autoheal or .heal on a Sim; a kernel module file:
        its frame cell and its tags, schedule.run('autoheal', ...) or 'AutoHealBehavior')."""
        names = set(self.handles().get(module_name(target), ())) | self.module_names(target)
        return merge_nodes(self.importers(target) | naming(self.facade_tests(), names, self.root))

    def module_names(self, target):
        """What a facade test reaches a kernel module file (engine/modules/) by: the PHASE strings of its classes and
        the tags it registers (@factory.module('<tag>'))."""
        if not target.startswith(CNV + '/engine/modules/'):
            return set()
        try:
            tree = ast.parse(open(os.path.join(self.root, target), encoding='utf-8').read())
        except (OSError, SyntaxError, ValueError):
            return set()
        out = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PHASE' for t in n.targets):
                if isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                    out.add(n.value.value)
            elif isinstance(n, ast.Call) and getattr(n.func, 'attr', getattr(n.func, 'id', None)) == 'module':
                out.update(a.value for a in n.args if isinstance(a, ast.Constant) and isinstance(a.value, str))
        return out

    def sim_files(self):
        """simcoverage.sim_files() as paths, read off the same imports (tests/test_affected_tests.py checks they agree):
        RUN_ENDS and every simulator module (enginefiles: experimental/cnv/sim*.py, experimental/cnv/engine/...) they
        reach by import, except one that imports sim itself."""
        if '_sim' not in self.__dict__:
            def sims(p):
                return {x for x in self.imports.get(p, ()) if is_sim_path(x)}
            ends = [CNV + '/%s.py' % m for m in RUN_ENDS]
            seen, todo = set(), list(ends)
            while todo:
                m = todo.pop()
                if m in seen or m not in self.paths:
                    continue
                if m not in ends and FACADE in self.imports.get(m, ()):
                    continue
                seen.add(m)
                todo += sorted(sims(m))
            self._sim = frozenset(seen)
        return self._sim

    def part_names(self, facade_source):
        """{name in sim.py: part module} for the parts (sim_files but the facade): a bare part under its own name
        (simheal), and every name the facade binds to a part (`from engine.objects import heal as simheal`)."""
        names = {module_name(p) for p in self.sim_files()} - {'sim'}
        out = {n: n for n in names if '.' not in n}
        if facade_source is not None and facade_source.tree is not None:
            bound = enginefiles.bindings(facade_source.tree, os.path.join(self.root, CNV))
            out.update({local: m for local, m in bound.items() if m in names})
        return out


def is_sim_path(path):
    """Is this repository path (experimental/cnv/...) one of the simulator's files (enginefiles.is_engine_rel)?"""
    return path.startswith(CNV + '/') and enginefiles.is_engine_rel(path[len(CNV) + 1:])


def module_name(path):
    """The module name of a file of experimental/cnv: experimental/cnv/simheal.py -> simheal,
    experimental/cnv/engine/objects/heal.py -> engine.objects.heal."""
    return enginefiles.name_of(path, CNV)


def module_path(name, sim_files):
    """The path of a simulator module among sim_files, by its module name."""
    return next((p for p in sim_files if module_name(p) == name), '%s/%s.py' % (CNV, name.replace('.', '/')))


def new_side_lines(hunks):
    """Changed lines in the NEW file's numbering (a pure deletion: the lines on both sides of the cut)."""
    lines = set()
    for a, b, c, d in hunks:
        lines.update(range(c, c + d) if d else (c, c + 1))
    return {n for n in lines if n >= 1}


def _sim_methods(source):
    """{line: (method name, its def node)} for the lines of each method defined directly in a class of `source`."""
    out = {}
    for node in getattr(source.tree, 'body', []):
        if isinstance(node, ast.ClassDef):
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start = min([m.lineno] + [x.lineno for x in m.decorator_list])
                    for n in range(start, m.end_lineno + 1):
                        out[n] = (m.name, m)
    return out


def _part_names(node, parts):
    """The part modules a node names, through the names sim.py holds them by (parts: {name: module})."""
    return {parts[x.id] for x in ast.walk(node) if isinstance(x, ast.Name) and x.id in parts}


def facade_parts(source, lines, parts):
    """Sort the changed `lines` of the facade (sim.py) by where the code they change lives.

    Returns ({part module: {names}}, lines left). A line of a forwarder -- a Sim method of at most FORWARDER_STMTS
    statements (docstring left out) that names a part module, itself or through one self._helper() -- lives in that
    part module, under the method's name; a module-level `import simX` / `from simX import ...` line lives in simX,
    under the imported names (`from engine.objects import heal` lives in engine.objects.heal, under no name). Every
    other non-blank line is code still in sim.py: left for the coverage map. parts: {name in sim.py: part module}
    (ImportGraph.part_names), or a set of bare part names (each its own module)."""
    found, left = {}, set()
    if source is None or source.tree is None:
        return found, set(lines)
    parts = parts if isinstance(parts, dict) else {p: p for p in parts}
    modules = set(parts.values())
    methods = _sim_methods(source)
    by_name = {name: node for name, node in methods.values()}
    top = {}
    for node in source.tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for n in range(node.lineno, node.end_lineno + 1):
                top[n] = node
    for n in sorted(lines):
        if source.inert(n):
            continue
        if n in top:
            node = top[n]
            names = set()
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif (node.module or '') in modules:                # from simtoggle import LAG: names of the part
                mods, names = [node.module], {a.asname or a.name for a in node.names}
            else:                                               # from engine.objects import heal: the part itself
                mods = ['%s.%s' % (node.module, a.name) for a in node.names]
            hit = [m for m in mods if m in modules]
            if hit and len(hit) == len(mods):
                for m in hit:
                    found.setdefault(m, set()).update(names)
                continue
        elif n in methods:
            name, node = methods[n]
            body = [s for s in node.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
            if len(body) <= FORWARDER_STMTS and not name.startswith('__'):
                mods = _part_names(node, parts)
                for x in ast.walk(node):                    # self._life(): the helper that makes the part
                    if (isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and isinstance(x.func.value, ast.Name)
                            and x.func.value.id == 'self' and x.func.attr in by_name and x.func.attr != name):
                        mods |= _part_names(by_name[x.func.attr], parts)
                if mods:
                    for m in mods:
                        found.setdefault(m, set()).add(name)
                    continue
        left.add(n)
    return found, left


def test_nodes(text, path):
    """[(first line, last line, pytest node id)] of the tests in a test file's text: module-level test_* functions
    and the test_* methods of Test* classes (decorators included)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out = []

    def span(n):
        return min([n.lineno] + [d.lineno for d in n.decorator_list]), n.end_lineno

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test'):
            out.append(span(node) + ('%s::%s' % (path, node.name),))
        elif isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith('test'):
                    out.append(span(m) + ('%s::%s::%s' % (path, node.name, m.name),))
    return out


def naming(test_files, names, root=None):
    """Where the test files name one of `names` as an attribute or a string (`.expire(`, 'expire'): the pytest node
    id of the test it sits in, or the whole file when it sits outside any test (a helper, a fixture, module level)."""
    if not names:
        return set()
    pat = re.compile(r"\.(?:%s)\b|['\"](?:%s)['\"]" % (('|'.join(map(re.escape, sorted(names))),) * 2))
    out = set()
    for t in test_files:
        try:
            text = open(os.path.join(root or ROOT, t), encoding='utf-8').read()
        except OSError:
            continue
        hits = {text.count('\n', 0, m.start()) + 1 for m in pat.finditer(text)}
        if not hits:
            continue
        nodes = test_nodes(text, t)
        for n in hits:
            inside = [node for first, last, node in nodes if first <= n <= last]
            if not inside:
                out.add(t)
                break
            out.add(inside[0])
    return {x for x in out if '::' not in x or x.split('::', 1)[0] not in out}


def file_of(selector):
    """'tests/test_x.py::test_y' -> 'tests/test_x.py'."""
    return selector.split('::', 1)[0]


def merge_nodes(picked):
    """A file picked whole drops its single tests."""
    return {x for x in picked if '::' not in x or file_of(x) not in picked}


def replay_files(path=REPLAYS, where=None):
    """{'tests/<layer>/test_x.py': kind} from the replay list: one file name per line (found wherever it sits under
    tests/; a name found nowhere stays 'tests/<name>'), '[kind]' starts a group, '#' comments."""
    where = where or current_path
    out, kind = {}, ''
    try:
        with open(path, encoding='utf-8') as fh:
            lines = fh.read().splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.split('#', 1)[0].strip()
        if line.startswith('[') and line.endswith(']'):
            kind = line[1:-1].strip()
        elif line:
            out[where('tests/' + line)] = kind
    return out


def drop_replays(tests, replays, changed):
    """The daily pick: the picked tests minus those in a replay file, unless the change edits that test file itself.
    Returns (kept, left out)."""
    out = {t for t in tests if file_of(t) in replays and file_of(t) not in changed}
    return tests - out, out


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

def pick(cov, changes, sources, remaps, fallback, graph=None, facade=(None, None), decided=None):
    """changes: [(key, display path, hunks or None for an added file, deleted?)];
    sources[key] -> Source at the coverage commit; remaps[key](lines) -> lines in coverage numbering.
    graph: an ImportGraph -- a change to one of the simulator's files (graph.sim_files()) picks by import (ADR 0029):
    the test files that import that module; for the facade sim.py, the importers of the part module a changed forwarder
    or import line lives in, plus the tests that import sim and name the changed method; code still in sim.py, and a
    module no test imports, go to the coverage map as before. facade: (Source of sim.py at the diff base, Source now).
    decided: a list the changes that went to the coverage map or name matching are appended to.
    Returns (tests -- files, or 'file::test' -- , reasons {test: [why]}, fallbacks [display path])."""
    tests, why, fell = set(), {}, []

    def add(found, reason):
        for t in found:
            tests.add(t)
            why.setdefault(t, [])
            if reason not in why[t] and len(why[t]) < 3:
                why[t].append(reason)

    def by_coverage(key, shown, hunks):
        if decided is not None:
            decided.append(shown)
        if hunks is not None and cov is not None and cov.has(key) and key in sources:
            add(select(cov, key, remaps[key](old_side_lines(hunks)), sources[key]), 'lines of ' + shown)
        else:
            fell.append(shown)
            add(fallback(shown), 'by name: ' + shown)

    sim_files = graph.sim_files() if graph else ()
    for key, shown, hunks, deleted in changes:
        if is_test_file(shown):
            add({shown}, 'changed test')
            continue
        if key == FACADE and hunks is not None and graph and not deleted:
            old_parts, new_parts = graph.part_names(facade[0]), graph.part_names(facade[1])
            left = []
            for h in hunks:
                a, b, c, d = h
                old_found, old_left = facade_parts(facade[0], set(range(a, a + b)), old_parts)
                new_found, new_left = facade_parts(facade[1], set(range(c, c + d)), new_parts)
                for m, names in list(old_found.items()) + list(new_found.items()):
                    path = module_path(m, sim_files)
                    add(graph.importers(path), 'imports %s (sim.py forwards to it)' % m)
                    add(naming(graph.facade_tests(), names, graph.root), 'tests Sim.%s' % '/'.join(sorted(names)))
                if old_left or new_left or not (old_found or new_found):
                    left.append(h)
            if left:
                by_coverage(key, shown, left)
            continue
        if key in sim_files and not deleted:
            found = graph.users(key)
            if found:
                add(found, 'imports ' + module_name(key))
                continue
        by_coverage(key, shown, hunks)
    tests = merge_nodes(tests)
    return tests, why, fell


def is_test_file(path):
    """A pytest file: tests/test_x.py, or one in a folder under tests/ (tests/modules/test_autoheal.py)."""
    return bool(re.match(r'tests/(?:[^/]+/)*test_[^/]*\.py$', path))


def all_test_files(root=None):
    """Every test file under tests/, sub-folders included."""
    root = root or ROOT
    out = []
    for d, dirs, fs in os.walk(os.path.join(root, 'tests')):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith('.')]
        rel = os.path.relpath(d, root).replace(os.sep, '/')
        out += [rel + '/' + f for f in fs if is_test_file(rel + '/' + f)]
    return sorted(out)


def test_index(root=None):
    """{file name: 'tests/.../test_x.py'} of every test file under tests/. A name in two places is an error: pytest
    imports test files by name (no __init__.py), and the readers here find a moved file by it."""
    out = {}
    for f in all_test_files(root):
        name = f.rsplit('/', 1)[1]
        if name in out:
            raise ValueError('two test files named %s: %s and %s' % (name, out[name], f))
        out[name] = f
    return out


_INDEX = {}


def current_path(name, root=None):
    """A test file as a record names it ('tests/test_x.py', maybe from before a move) -> where it is now: itself if it
    exists, else the test file of that name anywhere under tests/, else the name unchanged."""
    root = root or ROOT
    if not is_test_file(name) or os.path.exists(os.path.join(root, name)):
        return name
    if root not in _INDEX:
        _INDEX[root] = test_index(root)
    return _INDEX[root].get(name.rsplit('/', 1)[-1], name)


def unrecorded(cov):
    """Test files with no coverage record at all (the map is partial, or the test runs no measured code):
    nothing says what they touch, so they are always picked."""
    return sorted(set(all_test_files()) - cov.test_files())


def guards(root=None):
    """Always picked: every test file of the guard layer, and the inventory tests. An empty guard layer is an error,
    not an empty pick (a moved or renamed folder must not turn the guards off without a word)."""
    files = all_test_files(root)
    layer = [f for f in files if f.startswith(GUARD_LAYER + '/')]
    if not layer:
        raise RuntimeError('no test files under %s: the guards would silently not run' % GUARD_LAYER)
    return set(layer) | {f for f in files if GUARD_NAMES.match(f.rsplit('/', 1)[1])}


def estimate(files, durations, n=MAX_WORKERS, tests_in=None):
    """(serial seconds, parallel seconds over n workers) from per-file durations; unknown files get the median.
    A single test ('file::test') counts its file's time over tests_in(file), the file's number of tests (a guess:
    the map keeps files only)."""
    known = sorted(durations.values())
    med = known[len(known) // 2] if known else 30.0
    ds = [durations.get(file_of(f), med) / (max(1, tests_in(file_of(f))) if tests_in and '::' in f else 1)
          for f in files]
    serial = sum(ds)
    return serial, max(serial / n, max(ds) if ds else 0.0), sum(1 for f in files if file_of(f) not in durations)


def tests_in(path):
    """How many tests a test file holds (test_nodes; a parametrized test counts once)."""
    try:
        return len(test_nodes(open(os.path.join(ROOT, path), encoding='utf-8').read(), path))
    except OSError:
        return 1


def save_durations(junit_path, mapdir=None):
    """junit xml -> {test file: seconds of CPU wall in that file} (summed over its tests), written to durations.json;
    and {test id: seconds} to durations_tests.json (time_budget.py's per-test lines: a conformance group)."""
    out, per_test = {}, {}
    for tc in ET.parse(junit_path).getroot().iter('testcase'):
        cls = tc.get('classname', '')
        parts = cls.split('.')
        i = next((k for k, p in enumerate(parts) if p.startswith('test_')), None)
        if i is None:
            continue
        f = '/'.join(['tests'] + [x for x in parts[:i] if x != 'tests'] + [parts[i]]) + '.py'   # tests.modules.test_x
        secs = float(tc.get('time', 0))
        out[f] = out.get(f, 0.0) + secs
        per_test['::'.join([f] + parts[i + 1:] + [tc.get('name', '')])] = secs     # tests/x.py::TestC::test_y[p]
    mapdir = mapdir or MAPDIR
    os.makedirs(mapdir, exist_ok=True)
    for name, data in (('durations.json', out), ('durations_tests.json', per_test)):
        with open(os.path.join(mapdir, name), 'w', encoding='utf-8') as fh:
            json.dump({k: round(v, 2) for k, v in sorted(data.items())}, fh, indent=0, ensure_ascii=False)
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
    """Real changes from git: [(key, shown, hunks|None, deleted)], plus per-repo coverage-commit tools and the
    facade (sim.py) at the diff base and now (the working tree, or the range's end)."""
    meta = load_json(META)
    changes, sources, remaps, facade = [], {}, {}, (None, None)
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
            if not prefix and path == FACADE and old is not None and hunks is not None:
                end = sp.split('..', 1)[1].lstrip('.') or 'HEAD' if sp and '..' in sp else None
                new = git_show(repo, end, path) if end else open(os.path.join(ROOT, path), encoding='utf-8').read()
                facade = (Source(old), Source(new) if new is not None else None)
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
    return changes, sources, remaps, meta, facade


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('range', nargs='?', help="commit range A..B (default: working tree vs origin/main)")
    ap.add_argument('--stats', action='store_true', help='count and rough running time of the picked files')
    ap.add_argument('--why', action='store_true', help='print the reason after each file (stderr)')
    ap.add_argument('--save-coverage', metavar='.coverage', help='store a coverage file as the map')
    ap.add_argument('--save-durations', metavar='junit.xml', help='store per-file durations from a junit report')
    ap.add_argument('--no-guards', action='store_true')
    ap.add_argument('--coverage-only', action='store_true', help="pick the simulator's files by the coverage map too "
                    '(the pick before ADR 0029: the map was recorded before the blocks moved out of sim.py)')
    ap.add_argument('--with-replays', action='store_true', help='keep the replay tests (tests/replay_tests.txt) in '
                    'the pick; the daily pick leaves them out unless the change edits them')
    ap.add_argument('--cmd', action='store_true', help='print the whole pytest command instead of the file list '
                    '(workers = min(8, free GB / 1.5, free CPU tokens, 2))')
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
    changes, sources, remaps, meta, facade = gather(args.range)
    if cov and meta.get('commit'):
        behind = git(ROOT, 'rev-list', '--count', '%s..HEAD' % meta['commit']).strip()
        if behind.isdigit() and int(behind) > 100:
            print('warning: the coverage map is %s commits old (see the rebuild advice)' % behind, file=sys.stderr)
    elif cov:
        print('warning: meta.json missing: coverage line numbers assumed to match the diff base', file=sys.stderr)
    graph = None if args.coverage_only else ImportGraph()
    decided = []
    tests, why, fell = pick(cov, changes, sources, remaps, lambda p: name_fallback(p, None), graph, facade, decided)
    for g in guards() if not args.no_guards else ():
        tests.add(g)
        why.setdefault(g, []).append('guard')
    if cov and (decided or graph is None):         # the import graph sees every test file: only what it left
        for t in unrecorded(cov):                   # no coverage record: we cannot tell, so always run
            tests.add(t)
            why.setdefault(t, []).append('no coverage record: always')
        print('always selected (no coverage record): %d test files' % len(unrecorded(cov)), file=sys.stderr)
    tests = merge_nodes({t for t in tests if os.path.exists(os.path.join(ROOT, file_of(t)))})
    if not args.with_replays:
        replays = replay_files()
        tests, dropped = drop_replays(tests, replays, {c[0] for c in changes})
        if dropped:
            kinds = {}
            for t in dropped:
                kinds[replays[file_of(t)]] = kinds.get(replays[file_of(t)], 0) + 1
            print('left out %d replay tests (%s; tests/replay_tests.txt): --with-replays runs them'
                  % (len(dropped), ', '.join('%s %d' % kv for kv in sorted(kinds.items()))), file=sys.stderr)
    out = sorted(tests)
    n = workers()
    if args.cmd:
        print('python -X utf8 -m pytest -n %d -p no:cacheprovider -q %s' % (n, ' '.join(out)))
    else:
        for t in out:
            print(t)
    for p in fell:
        print('by name (not in the coverage map): %s' % p, file=sys.stderr)
    if args.why:
        for t in out:
            print('  %s <- %s' % (t, '; '.join(why.get(t, []))), file=sys.stderr)
    if args.stats:
        durations = {current_path(k): v for k, v in load_json(DURATIONS).items()}
        serial, par, unknown = estimate(out, durations, n, tests_in)
        total = len(durations) or None
        nodes = sum(1 for t in out if '::' in t)
        print('%d test files picked%s%s; %d changed files (%d by name); ~%.0f min serial, ~%.0f min with %d workers%s'
              % (len(out) - nodes, ' of %d' % total if total else '', ' and %d single tests' % nodes if nodes else '',
                 len(changes), len(fell), serial / 60, par / 60, n,
                 ' (%d files without a recorded duration)' % unknown if unknown else ''), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
