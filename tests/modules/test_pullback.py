"""The AI's pullbacks (experimental/cnv/engine/ai/pullback.py): a returner is kept by its serial, never by its name (same-name
review 1119b O60 / N05). The return order itself and its filter: tests/test_ai_reverse_*.py on the bench."""
from types import SimpleNamespace

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.ai.pullback as simpullback  # noqa: E402


class _Commands:
    def __init__(self):
        self.given = []

    def do(self, c):
        self.given.append(c)


def _unit(serial, name='tank'):
    return SimpleNamespace(serial=serial, name=name, owner='p1', move_to=(5.0, 5.0), goal=None, path=[(5.0, 5.0)],
                           x=0.0, y=0.0)


def _pullbacks():
    p = simpullback.Pullbacks(SimpleNamespace(t=1.0), SimpleNamespace(commands=_Commands()))
    p.accepts = lambda u, g: True       # the filter is the bench's (accepts); here only who is kept
    return p


def test_a_unit_made_again_under_a_returners_name_walking_its_very_path_is_not_the_returner():
    """O60 / N05: the returner's entry is its serial's. A new body under its name, given the very path list (the one
    case identity alone does not tell), is not held back, and asking about it leaves the returner's entry."""
    p, g = _pullbacks(), SimpleNamespace(name='yard', x=5.0, y=5.0)
    old = _unit(7)
    assert p.send(old, g)
    new = _unit(8)
    new.path = old.path
    assert not p.busy(new)
    assert p.busy(old) and set(p.returning) == {7}
