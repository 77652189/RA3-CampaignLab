"""The registry of builds: each mission module and each check module says what it contributes, nobody keeps a table.

  missions/<x>.py   MISSION = {build name: factory() -> Mission}        one module often makes several builds
  checks/<x>.py     CHECKS = {build name: {check name: check(mission) -> Test}}
  either folder     PAIR_BUILDS = {build name: factory() -> (Mission, Test)}   a build that is both outright
  either folder     CONTROLS = {control build: original build}   one module taken out of the original, nothing else
                    changed (contract.control_drift holds it to that, tests/test_cnv_parts.py)
  either folder     CONTROL_ARMS = {build: (original tag, control tag, *free Obj fields)}   the same for two arms of one
                    build on one map (contract.arm_drift)

  benches/<domain>/<group>/{checks,scenes}.py   BENCHES = (bench_factory, ...)
                    Each factory is named for its logical bench and returns the same registry tables.

load() reads the source of each candidate and imports only modules that declare registry tables or BENCHES
at module level. Heavy dependencies can stay inside build factories, as in the music scenes. A build made
twice, a check for a build nobody makes, a check that is not callable: an error here, at import, not a KeyError
at the bench.
"""
import ast
import importlib
import os
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDERS = ('missions', 'checks')
NAMES = ('MISSION', 'CHECKS', 'PAIR_BUILDS', 'CONTROLS', 'CONTROL_ARMS')
BENCH_ROOT = Path(HERE) / 'benches'


class RegistryError(Exception):
    pass


@dataclass(frozen=True)
class Registry:
    builds: dict            # build name -> factory() -> Mission
    checks: dict            # build name -> {check name: check(mission) -> Test}
    pairs: dict             # build name -> factory() -> (Mission, Test)
    where: dict             # build name -> 'missions.a4' (module that makes it)
    controls: dict          # control build -> its original (the same checks)
    arms: dict              # build -> (original tag, control tag, *free Obj fields): its two arms on one map


def declared(path):
    """The names a module's source assigns at module level."""
    with open(path, encoding='utf-8') as f:
        tree = ast.parse(f.read())
    out = set()
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        out.update(t.id for t in targets if isinstance(t, ast.Name))
    return out


def modules():
    """('missions.a4', ...) for every module in the folders that declares a registry name."""
    out = []
    for folder in FOLDERS:
        for info in sorted(pkgutil.iter_modules([os.path.join(HERE, folder)]), key=lambda i: i.name):
            if info.ispkg:
                continue
            if declared(os.path.join(HERE, folder, info.name + '.py')) & set(NAMES):
                out.append(f'{folder}.{info.name}')
    for path in sorted(BENCH_ROOT.glob('*/*/*.py')):
        if path.stem in ('checks', 'scenes') and 'BENCHES' in declared(path):
            out.append('.'.join(path.relative_to(HERE).with_suffix('').parts))
    return out


def entries(name, prefix=''):
    """(logical bench, registry tables) for each contribution in a module."""
    if name.startswith('benches.'):
        return [(make.__name__, make()) for make in importlib.import_module(name).BENCHES
                if make.__name__.startswith(prefix)]
    stem = name.rsplit('.', 1)[-1]
    return [(stem, vars(importlib.import_module(name)))] if stem.startswith(prefix) else []


def bench_sources(path):
    """The sources of the registered bench factory bodies, for static evidence and import scans."""
    lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
    body = ast.parse(''.join(lines)).body
    benches = next((n.value.elts for n in body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'BENCHES' for t in n.targets)), ())
    functions = {n.name: n for n in body if isinstance(n, ast.FunctionDef)}
    return {b.id: dedent(''.join(lines[functions[b.id].lineno:functions[b.id].body[-1].lineno - 1]))
            for b in benches}


def load():
    builds, checks, pairs, where, check_where, controls, arms = {}, {}, {}, {}, {}, {}, {}
    for name, tables in ((name, tables) for name in modules() for _, tables in entries(name)):
        for build, make in tables.get('MISSION', {}).items():
            _claim(where, build, name)
            builds[build] = make
        for build, make in tables.get('PAIR_BUILDS', {}).items():
            _claim(where, build, name)
            pairs[build] = make
        for build, table in tables.get('CHECKS', {}).items():
            if build in check_where:
                raise RegistryError(f'checks of build {build!r} declared twice: {check_where[build]} and {name}')
            check_where[build] = name
            for check, fn in table.items():
                if not callable(fn):
                    raise RegistryError(f'{name}: check {build}/{check} is not callable')
            checks[build] = dict(table)
        for off, on in tables.get('CONTROLS', {}).items():
            if off in controls:
                raise RegistryError(f'{name}: control {off!r} declared twice')
            controls[off] = on
        for build, tags in tables.get('CONTROL_ARMS', {}).items():
            if build in arms:
                raise RegistryError(f'{name}: arms of {build!r} declared twice')
            arms[build] = tags
    for build, name in check_where.items():
        if build not in builds:
            raise RegistryError(f'{name}: checks for build {build!r}, which no mission module makes')
    for off, on in controls.items():
        if not {off, on} <= where.keys() or checks.get(off, {}).keys() != checks.get(on, {}).keys():
            raise RegistryError(f'control {off!r} of {on!r}: both must be made, with the same checks')
    if arms.keys() - where.keys():
        raise RegistryError(f'arms of builds nobody makes: {sorted(arms.keys() - where.keys())}')
    return Registry(builds, checks, pairs, where, controls, arms)


def _claim(where, build, module):
    if build in where:
        raise RegistryError(f'build {build!r} made twice: {where[build]} and {module}')
    where[build] = module


_loaded = None


def get():
    global _loaded
    if _loaded is None:
        _loaded = load()
    return _loaded
