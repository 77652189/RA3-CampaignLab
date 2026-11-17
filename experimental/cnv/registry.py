"""The registry of builds: each mission module and each check module says what it contributes, nobody keeps a table.

  missions/<x>.py   MISSION = {build name: factory() -> Mission}        one module often makes several builds
  checks/<x>.py     CHECKS = {build name: {check name: check(mission) -> Test}}
  either folder     PAIR_BUILDS = {build name: factory() -> (Mission, Test)}   a build that is both outright

load() reads the source of every module in the two folders and imports only those that declare one of the three
names at module level (a bench scene that pulls in something heavy declares nothing and is reached lazily, see
missions/music_builds.py). A build made twice, a check for a build nobody makes, a check that is not callable: an
error here, at import, not a KeyError at the bench.
"""
import ast
import importlib
import os
import pkgutil
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDERS = ('missions', 'checks')
NAMES = ('MISSION', 'CHECKS', 'PAIR_BUILDS')


class RegistryError(Exception):
    pass


@dataclass(frozen=True)
class Registry:
    builds: dict            # build name -> factory() -> Mission
    checks: dict            # build name -> {check name: check(mission) -> Test}
    pairs: dict             # build name -> factory() -> (Mission, Test)
    where: dict             # build name -> 'missions.a4' (module that makes it)


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
    return out


def load():
    builds, checks, pairs, where, check_where = {}, {}, {}, {}, {}
    for name in modules():
        module = importlib.import_module(name)
        for build, make in getattr(module, 'MISSION', {}).items():
            _claim(where, build, name)
            builds[build] = make
        for build, make in getattr(module, 'PAIR_BUILDS', {}).items():
            _claim(where, build, name)
            pairs[build] = make
        for build, table in getattr(module, 'CHECKS', {}).items():
            if build in check_where:
                raise RegistryError(f'checks of build {build!r} declared twice: {check_where[build]} and {name}')
            check_where[build] = name
            for check, fn in table.items():
                if not callable(fn):
                    raise RegistryError(f'{name}: check {build}/{check} is not callable')
            checks[build] = dict(table)
    for build, name in check_where.items():
        if build not in builds:
            raise RegistryError(f'{name}: checks for build {build!r}, which no mission module makes')
    return Registry(builds, checks, pairs, where)


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
