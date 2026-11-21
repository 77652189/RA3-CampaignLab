"""Every key the simulator makes up for a thing goes through simworld.free_key / free_name (review 1119y P2 #3 / #4):
a key spelt out where a thing is added or written into bodies -- f'#{k}', f'UNIT - SIM Made {n}' -- can come round to
one a living thing holds (Sim.add refuses it, or the map load's shadow puts the new one in its place) or a dead one
the schedule still runs a module of (written straight into bodies, a snapshot fails). The scan: every string or
f-string in experimental/cnv/sim*.py and engine/ that spells an internal key (starts '#<word>', '#<digit>',
'__proto_' or 'UNIT - SIM Made') is an argument of free_key / free_name (or a `.format` handed to free_key) -- no
exceptions by prefix (review 1120aa P3: '#12', '__proto_' and a '#spawn' without its loop went through)."""
import ast
import pathlib
import re

CNV = pathlib.Path(__file__).resolve().parents[2] / 'experimental' / 'cnv'
KEY = re.compile(r'#[\w{]|UNIT - SIM Made|__proto_')
FREE = {'free_key', 'free_name'}


def _text(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and node.values and isinstance(node.values[0], ast.Constant):
        head = node.values[0].value             # what it starts with (f'{name}#{serial}': none)
        return head + '{' if len(node.values) > 1 and head == '#' else head      # f'#{k}': '#{'
    return None


def _callee(call):
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None


def _freed(node, parents):
    """The string is (part of) an argument of free_key / free_name: walked up through a `.format`, a lambda, an
    f-string, until a call."""
    while (p := parents.get(node)) is not None:
        if isinstance(p, ast.Call):
            if _callee(p) in FREE and node in p.args:
                return True
            if not (isinstance(p.func, ast.Attribute) and p.func.attr == 'format' and node is p.func):
                return False
        elif not isinstance(p, (ast.Attribute, ast.Lambda, ast.JoinedStr, ast.FormattedValue, ast.BinOp)):
            return False
        node = p
    return False


def spelt_keys(root=CNV):
    """(file, line, text) of each internal key spelt out without free_key / free_name."""
    out = []
    for path in sorted((*root.glob('sim*.py'), *(root / 'engine').rglob('*.py'))):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
        for node in ast.walk(tree):
            if isinstance(parents.get(node), ast.JoinedStr):
                continue                        # the f-string itself is read, not its pieces
            text = _text(node)
            if text is None or not KEY.match(text) or _freed(node, parents):
                continue
            p = parents.get(node)
            if isinstance(p, ast.Expr):
                continue                        # a docstring
            if isinstance(p, ast.Call) and _callee(p) in ('startswith', 'endswith'):
                continue                        # a key read by its head, not made
            out.append((path.name, node.lineno, text))
    return out


def test_every_internal_key_goes_through_free_key():
    assert spelt_keys() == []


def test_the_scan_sees_a_key_spelt_out(tmp_path):
    """The guard reads what it is meant to (a spelt key flagged, a freed one and a docstring not)."""
    (tmp_path / 'simx.py').write_text(
        '"""#made in a docstring."""\n'
        "import engine.world.handle as simworld\n"
        "def f(s, k):\n"
        "    s.add(f'#thing {k}', 'T', 'P', 0, 0)\n"
        "    s.add(k or f'#{k}', 'T', 'P', 0, 0)\n"
        "    s.add(f'{k}#{k}', 'T', 'P', 0, 0)\n"
        "    s.add(simworld.free_key(s, '#ok {}'.format, k), 'T', 'P', 0, 0)\n"
        "    s.add(simworld.free_name(s, '#fine', 'x'), 'T', 'P', 0, 0)\n"
        "    s.bodies['UNIT - SIM Made 3'] = None\n"
        "    s.add('#12', 'T', 'P', 0, 0)\n"
        "    s.add(f'__proto_{k}', 'T', 'P', 0, 0)\n"
        "    s.add(f'#unpack {k}', 'T', 'P', 0, 0)\n", encoding='utf-8')
    assert sorted((ln, t) for _, ln, t in spelt_keys(tmp_path)) == [
        (4, '#thing '), (5, '#{'), (9, 'UNIT - SIM Made 3'), (10, '#12'), (11, '__proto_'), (12, '#unpack ')]
