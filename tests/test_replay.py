"""experimental/replay/ra3replay.py: command framing and typed arguments, on command bytes seen in our replays."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experimental', 'replay'))
import ra3replay as R  # noqa: E402


def chunk(*cmds):
    return bytes([1]) + struct.pack('<I', len(cmds)) + b''.join(cmds)


SELECT = bytes.fromhex('f511' + '12010004d7030000' + 'ff')
MOVE = bytes.fromhex('1412' + '07001fa44434c7d244fcff5143' + 'ff')
PRODUCE = bytes.fromhex('0512' + '04d703000000de28fcdd02000002000000' + 'ff')
PLACE = bytes.fromhex('0912' + '04cd030000103d6eb8890100000007d251ad44def4bd440000524301dfedaf40' + 'ff')


def test_a_chunk_splits_into_its_commands():
    cmds, n = R.commands(chunk(SELECT, MOVE, PRODUCE, PLACE))
    assert n == 4 and [c[0] for c in cmds] == [0xF5, 0x14, 0x05, 0x09] and all(c[3] is None for c in cmds)


def test_typed_arguments():
    (_, _, sel, _), (_, _, mv, _), (_, _, pr, _), (_, _, pl, _) = R.commands(chunk(SELECT, MOVE, PRODUCE, PLACE))[0]
    assert R.args(0xF5, sel) == [('obj', [983])]
    (kind, [(x, y, z)]), = R.args(0x14, mv)
    assert kind == 'pos' and round(x) == 1313 and round(y) == 1686 and round(z) == 210
    assert R.args(0x05, pr) == [('obj', [983]), ('int', [0xddfc28de]), ('bool', [0]), ('int', [2])]
    a = R.args(0x09, pl)
    assert a[0] == ('obj', [973]) and a[1] == ('int', [0x89b86e3d, 1]) and a[2][0] == 'pos' and a[3][0] == 'float'


def test_an_unknown_layout_stops_the_chunk_and_says_so():
    cmds, n = R.commands(chunk(MOVE, bytes.fromhex('0112ff'), MOVE))
    assert n == 3 and len(cmds) == 2 and cmds[1][3] == 'layout unknown'
