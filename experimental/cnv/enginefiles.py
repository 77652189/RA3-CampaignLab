"""Where the simulator's source files are, by module name (ADR 0029 step 10-0): the one place that turns a module name
into a file and back, for the tools and guards that read the simulator's source instead of importing it (simcoverage,
testbench/affected_tests.py, tests/test_sim_layers.py and the guards beside it).

A simulator module is named the way the code imports it: a bare `simheal` (a file of experimental/cnv, as all of them
are today) or a full `engine.objects.heal` (experimental/cnv/engine/objects/heal.py, where step 10 moves the parts).
Both forms are read: `import a.b.c`, `import a.b.c as x`, `from a.b import c` (c a module of a/b) and
`from a.b import name` (a name of module a.b), at the top or inside a function. Nothing is listed by hand: the
simulator's files are sim*.py at the top of experimental/cnv and every .py under experimental/cnv/engine.

Standard library only, no sys.path edit: tools load this file by its path."""
import ast
import os

CNV = os.path.dirname(os.path.abspath(__file__))
PACKAGE = 'engine'          # the package the simulator's parts move into (step 10); not there yet is fine


def is_engine_rel(rel):
    """Is this path (relative to experimental/cnv, '/' separated) one of the simulator's files?"""
    return rel.endswith('.py') and (('/' not in rel and rel.startswith('sim')) or rel.startswith(PACKAGE + '/'))


def file_of(dotted, cnv=CNV):
    """The file a module name of experimental/cnv stands for: a/b/c.py, or a/b/c/__init__.py for a package; None if
    there is no such file (the standard library, experimental/campaign, the engine model)."""
    stem = os.path.join(cnv, *dotted.split('.'))
    for cand in (stem + '.py', os.path.join(stem, '__init__.py')):
        if os.path.isfile(cand):
            return cand
    return None


def name_of(path, cnv=CNV):
    """The module name of a file of experimental/cnv: simheal.py -> simheal, engine/objects/heal.py ->
    engine.objects.heal, engine/objects/__init__.py -> engine.objects."""
    rel = os.path.relpath(path, cnv).replace('\\', '/')
    rel = rel[:-3] if rel.endswith('.py') else rel
    rel = rel[:-len('/__init__')] if rel.endswith('/__init__') else rel
    return rel.replace('/', '.')


def files(cnv=CNV):
    """Every file of the simulator's source (sim*.py at the top, everything under engine/), sorted."""
    out = [os.path.join(cnv, f) for f in os.listdir(cnv) if is_engine_rel(f)]
    for d, dirs, fs in os.walk(os.path.join(cnv, PACKAGE)):
        dirs[:] = sorted(x for x in dirs if x != '__pycache__')
        out += [os.path.join(d, f) for f in fs if f.endswith('.py')]
    return sorted(out)


def parse(dotted, cnv=CNV):
    """The syntax tree of a module of experimental/cnv, by name."""
    path = file_of(dotted, cnv)
    if path is None:
        raise FileNotFoundError(f'no module {dotted} under {cnv}')
    with open(path, encoding='utf-8') as f:
        return ast.parse(f.read())


def _from(node, cnv):
    """(module a `from` imports, [(bound name, module it stands for or None)]) -- None for a name that is not a module."""
    base = node.module
    out = []
    for a in node.names:
        full = f'{base}.{a.name}'
        out.append((a.asname or a.name, full if file_of(full, cnv) else None))
    return base, out


def imports(tree, cnv=CNV, packages=False):
    """The modules of experimental/cnv a tree imports (absolute imports, top level or inside a function), by full name:
    `import a.b.c` and `from a.b import c` (c a module) give a.b.c, `from a.b import name` gives a.b. With
    packages=True the packages on the way are given too (a, a.b: Python runs their __init__ first)."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            base, bound = _from(n, cnv)
            mods = [m for _, m in bound if m] or [base]
            if any(m is None for _, m in bound):
                mods.append(base)
        else:
            continue
        for m in mods:
            parts = m.split('.')
            for k in range(1 if packages else len(parts), len(parts) + 1):
                name = '.'.join(parts[:k])
                if file_of(name, cnv):
                    out.add(name)
    return out


def bindings(tree, cnv=CNV):
    """{local name: module} for the names a tree binds to a module of experimental/cnv (anywhere in the tree):
    `import simheal` -> simheal, `import engine.objects.heal as heal` -> heal, `from engine.objects import heal as
    simheal` -> simheal. A bare `import a.b.c` binds only the package a; it is left out."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if (a.asname or '.' not in a.name) and file_of(a.name, cnv):
                    out[a.asname or a.name] = a.name
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            for local, m in _from(n, cnv)[1]:
                if m:
                    out[local] = m
    return out
