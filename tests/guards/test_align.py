"""Every assumption a run can lean on is written down: each literal key a simulator file puts in `used`
(`world.used.add('...')`, `sim.used.add('...')`) has its line in sim.ALIGN, which Sim.report prints as 待对齐. A kernel
module writes its own in its class (Module.ALIGN, gathered by factory.align), so a new family changes no centre file.

A key with no line printed nothing but crashed the report (KeyError 'autoheal', the levelup test, 11-17); the report
now prints the bare key, and this guard keeps new keys written. UNWRITTEN is today's keys with no line yet: it only
shrinks (a key written is taken off it; a new key not written fails). Keys built at run time (f-strings) are not read.
"""
import ast
import subprocess
from pathlib import Path

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import sim  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

UNWRITTEN = {
    'ai team absent', 'air crash', 'assigned repair', 'crash choice', 'crush', 'death weapon', 'flee off map',
    'follow path', 'hit reaction', 'knock landing drowns', 'knock landing moved', 'knock resistance gate',
    'leap ground hit', 'linear damage', 'lose health', 'meta impact', 'miner armor', 'movement special power',
    'path fork', 'reinforcement team unknown', 'reinforcement unit dead', 'reinforcement waypoint unknown', 'repair', 'self power', 'sell', 'stealth',
    'team area k', 'team kindof', 'team path', 'toggle', 'weapon fire ability',
}


def keys(texts):
    """{key: [where]} of the literal keys put in `used` in {where: source text}: every plain string in the argument
    of a `<...>used.add(...)` call (both arms of `'a' if x else 'b'`)."""
    out = {}
    for where, text in texts.items():
        for node in ast.walk(ast.parse(text)):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add'
                    and node.args):
                continue
            owner = node.func.value
            if not ((isinstance(owner, ast.Name) and owner.id == 'used')
                    or (isinstance(owner, ast.Attribute) and owner.attr == 'used')):
                continue
            for c in ast.walk(node.args[0]):
                if isinstance(c, ast.Constant) and isinstance(c.value, str) and not isinstance(node.args[0],
                                                                                              ast.JoinedStr):
                    out.setdefault(c.value, []).append(f'{where}:{node.lineno}')
    return out


def unwritten(texts, align):
    return {k: v for k, v in keys(texts).items() if k not in align}


def sources():
    files = subprocess.run(['git', 'ls-files', 'experimental/cnv'], cwd=ROOT, capture_output=True, text=True,
                           check=True).stdout.split()
    return {f: (ROOT / f).read_text(encoding='utf-8', errors='replace') for f in files if f.endswith('.py')}


def test_every_used_key_has_its_align_line():
    found = unwritten(sources(), sim.ALIGN)
    new = {k: v for k, v in found.items() if k not in UNWRITTEN}
    assert not new, f'write these in sim.ALIGN: {new}'
    assert not UNWRITTEN - set(found), f'written or gone, take off UNWRITTEN: {sorted(UNWRITTEN - set(found))}'


def test_the_guard_catches_an_unwritten_key():
    text = {'x.py': "world.used.add('written')\nsim.used.add('a' if x else \"b\")\nused.add(f'code {a}')\n"
                    "seen.add('not used')\n"}
    assert unwritten(text, {'written': '...', 'a': '...'}) == {'b': ['x.py:2']}


def test_report_prints_an_unwritten_key():
    e = sim.Sim(small())
    e.used.add('no such key')
    assert 'no such key（未写说明）' in '\n'.join(e.report())
