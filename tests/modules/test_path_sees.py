"""Cells crossed by the routing grid's line-of-walk check."""
import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
from engine.objects.path import sees  # noqa: E402


@pytest.mark.parametrize(('rows', 'start', 'end'), [
    (('.#', '#.'), (0, 0), (1, 1)),
    (('#.', '.#'), (0, 1), (1, 0)),
    (('..##', '##..'), (0, 0), (1, 3)),
    (('.#', '.#', '#.', '#.'), (0, 0), (3, 1)),
])
def test_path_sees_ignores_cells_only_touched_at_a_corner(rows, start, end):
    flat = bytes(cell == '.' for row in rows for cell in row)
    width = len(rows[0])
    assert sees(flat, width, start, end)
    assert sees(flat, width, end, start)


@pytest.mark.parametrize(('start', 'end', 'blocked'), [
    ((0, 0), (0, 4), (0, 3)),
    ((2, 4), (2, 0), (2, 2)),
    ((0, 4), (2, 4), (1, 4)),
    ((2, 0), (0, 0), (1, 0)),
    ((0, 0), (2, 3), (1, 1)),
])
def test_path_sees_checks_crossed_cells_on_a_rectangular_map(start, end, blocked):
    flat = bytearray([1] * 15)
    assert sees(bytes(flat), 5, start, end)
    row, col = blocked
    flat[row * 5 + col] = 0
    assert not sees(bytes(flat), 5, start, end)


def test_path_sees_skips_the_source_but_checks_the_destination():
    flat = bytes([0, 1])
    assert sees(flat, 2, (0, 0), (0, 1))
    assert not sees(flat, 2, (0, 1), (0, 0))
    assert sees(flat, 2, (0, 0), (0, 0))
