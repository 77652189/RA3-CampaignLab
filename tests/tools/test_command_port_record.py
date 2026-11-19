import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_nothing_in_a_run_reads_the_record():
    """`issued()` is written, never read, outside the port and the tests (R2 13a: so a snapshot leaves it out)."""
    readers = []
    for p in sorted((ROOT / 'experimental').rglob('*.py')):
        if p.name == 'command.py' or 'archive' in p.parts:
            continue
        for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))):
            if isinstance(n, ast.Attribute) and n.attr in ('issued', '_issued'):
                readers.append((p.name, n.lineno))
    assert readers == []
