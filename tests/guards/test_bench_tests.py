"""已对拍 has one way in (ADR 0035 5, docs/engine/testing.md): a reading in the readings data the conformance runner
holds. The legacy ways stay as they were and only shrink: the hand-written registers that make an item 已对拍.

Ceilings are the counts when the readings data became the definition (T4, 11-18); lower one when an entry goes.
Never raise one: write the reading into checks/<bench>.readings.toml instead."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'experimental' / 'cnv' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# register -> ceiling (count of entries that make an item 已对拍)
REGISTER_CEILING = {
    'inventory.BENCHED_TESTS': 205,
    'inventory.NOTES[已对拍]': 36,
    'inventory_ai.BENCHED_REG': 49,
    'inventory_ai.NOTES[已对拍]': 114,
}


def register_counts(inv, ai):
    return {
        'inventory.BENCHED_TESTS': len(inv.BENCHED_TESTS),
        'inventory.NOTES[已对拍]': sum(1 for s, _ in inv.NOTES.values() if s == inv.BENCHED),
        'inventory_ai.BENCHED_REG': len(ai.BENCHED_REG),
        'inventory_ai.NOTES[已对拍]': sum(1 for s, _ in ai.NOTES.values() if s == ai.BENCHED),
    }


def over_ceiling(counts, ceilings=REGISTER_CEILING):
    """[(register, count, ceiling)] that grew."""
    assert set(counts) == set(ceilings), sorted(set(counts) ^ set(ceilings))
    return [(k, counts[k], ceilings[k]) for k in sorted(counts) if counts[k] > ceilings[k]]


def test_the_bench_registers_only_shrink():
    grew = over_ceiling(register_counts(_load('inventory'), _load('inventory_ai')))
    assert not grew, (f'{grew}: a hand-written 已对拍 register grew -- put the reading into '
                      'checks/<bench>.readings.toml (docs/engine/testing.md) instead')


def test_a_register_that_grows_is_caught():
    counts = dict(REGISTER_CEILING)
    assert over_ceiling(counts) == []
    counts['inventory_ai.BENCHED_REG'] += 1
    assert over_ceiling(counts) == [('inventory_ai.BENCHED_REG', 50, 49)]
