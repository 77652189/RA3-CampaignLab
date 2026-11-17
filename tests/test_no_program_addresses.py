"""Red line (AGENTS.md): reverse-engineering products -- program addresses, struct offsets, decompiler notes -- live
only in work/re/ (the private repo); this repo is public. This guard scans every tracked file under experimental/,
tests/ and docs/ for what reads as one:

- a code address of the game: 0x + six hex digits whose first is 4 to C, the game's code range (optionally
  zero-padded to 7-8 digits);
- a module offset: `<something>.game+0x...`;
- a struct / vtable offset: a plus glued to 0x and hex digits (`template +0x..`, `vtable+0x..`, `(+0x.. = 1`);
  arithmetic in code is written with a space after the plus.
(This file spells no example out: it is scanned too.)

Crash codes (0xC0000005), hashes (8 digits, not zero-padded), masks and file-format words are none of these. Files
whose own subject is a file format full of such words are allowed whole (FORMAT_FILES); add one only for that reason.
The behaviour is described in our own words in the public file, pointing at the work/re note (`work/re/<note>.md`)."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCANNED = ('experimental', 'tests', 'docs')

ADDRESS = re.compile(r'\b0x0{0,2}[4-9a-cA-C][0-9a-fA-F]{5}\b'      # code address, first digit 4 to C
                     r'|\.game\+0x[0-9a-fA-F]+'                     # RA3_1.13.game+0x...
                     r'|\+0x[0-9a-fA-F]+\b')                        # struct / vtable offset: '+0x' glued

# file formats whose constants look like addresses (music event words, replay chunk codes); prefix match
FORMAT_FILES = (
    'experimental/music/pfdx.py',
    'experimental/music/ownmap.py',
    'experimental/replay/',
    'tests/test_pfdx.py',
    'tests/test_replay.py',
)


def hits(text):
    """[(line number, match)] of what reads as a program address in `text`."""
    return [(i, m.group(0)) for i, line in enumerate(text.splitlines(), 1) for m in ADDRESS.finditer(line)]


def _tracked():
    out = subprocess.run(['git', 'ls-files', '--', *SCANNED], cwd=ROOT, capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if not f.startswith(FORMAT_FILES)]


def test_the_pattern_tells_addresses_from_other_hex():
    x = '0' + 'x'                                               # spelled apart: this file is scanned too
    for bad in (f'see {x}8bd780 here', f'RA3_1.13.game+{x}cee55', f'template +{x}dc bit 13', f'vtable+{x}40',
                f'{x}00607873', f'({x}4a0000)', f'{x}CB8510', f'(+{x}24 = 1', f'brain +{x}861?'):
        assert hits(bad), bad
    for fine in ('0xC0000005', '0xc000000d', '0x89b86e3d', '0xFFFFFF', '0x0000FFFF', '0x00FF0000', '0x7FFFFFFF',
                 '0x21e727da', '0x51d5c6a', 'x + 0x10', '0x3FFFF', '0x08000000', '0x00100000'):
        assert not hits(fine), fine


def test_no_program_address_in_the_public_files():
    found = []
    for f in _tracked():
        p = ROOT / f
        try:
            text = p.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue                                            # binary or vanished: nothing to read as text
        found += [f'{f}:{i}: {a}' for i, a in hits(text)]
    assert not found, 'program addresses in public files (move them to work/re, describe in our words):\n' + \
        '\n'.join(found[:40])
