import ast
from importlib.util import resolve_name
from pathlib import Path


PACKAGE = 'experimental.mapgen'
ROOT = Path(__file__).resolve().parents[2] / 'experimental' / 'mapgen'


def test_mapgen_layers():
    order = ast.get_docstring(ast.parse((ROOT / '__init__.py').read_text(encoding='utf-8')))
    layers = {name: level for level, row in enumerate(order.split('\n\n', 1)[1].splitlines())
              for name in row.split()}
    errors = []
    for path in sorted(ROOT.glob('*.py')):
        name = path.stem
        level = -1 if name == '__init__' else layers[name]
        tree = ast.parse(path.read_text(encoding='utf-8'))
        modules = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.ImportFrom):
                source = resolve_name('.' * node.level + (node.module or ''), PACKAGE)
            else:
                source = ''
            for alias in node.names:
                target = f'{source}.{alias.name}' if source else alias.name
                where = f'{path.name}:{node.lineno}'
                if target == 'experimental.mappage' or target.startswith('experimental.mappage.'):
                    errors.append(f'{where}: predecessor import {target}')
                if source and alias.name.startswith('_'):
                    errors.append(f'{where}: private import {target}')
                if target == PACKAGE or target.split('.')[0] in layers:
                    errors.append(f'{where}: import a qualified mapgen module: {target}')
                if target.startswith(PACKAGE + '.'):
                    dependency = target[len(PACKAGE) + 1:].split('.')[0]
                    if layers.get(dependency, level) >= level:
                        errors.append(f'{where}: {name} may only import lower layers: {target}')
                    if alias.name == '*':
                        errors.append(f'{where}: wildcard import {target}')
                    if target == f'{PACKAGE}.{dependency}':
                        modules.add(alias.asname or (alias.name if source else target))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr.startswith('_') and ast.unparse(node.value) in modules:
                errors.append(f'{path.name}:{node.lineno}: private access {ast.unparse(node)}')
    assert not errors, '\n'.join(errors)
