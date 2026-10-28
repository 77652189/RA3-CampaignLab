"""retailref: the retail scripts' export suffix on a condition line -- inverted conditions read as NOT."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))

import retailref  # noqa: E402


def test_inverted_condition_reads_not():
    line = "              IF UNIT_HAS_MODELCONDITION('UNIT - Allied02 - MCV', 'MOVING')  +0100000001000000"
    assert retailref.condition(line) == "              IF NOT UNIT_HAS_MODELCONDITION('UNIT - Allied02 - MCV', 'MOVING')"


def test_plain_condition_loses_only_its_suffix():
    assert retailref.condition("    IF TIMER_EXPIRED('T')  +0100000000000000") == "    IF TIMER_EXPIRED('T')"
    assert retailref.condition("    DO SET_FLAG('F', 1)") == "    DO SET_FLAG('F', 1)"
    assert retailref.condition("    DO SET_FLAG('F', 1)  +01000000") == "    DO SET_FLAG('F', 1)"
    assert retailref.condition("    DO SET_FLAG('F', 1)  +00000000") == "    DO SET_FLAG('F', 1)  +00000000"


def test_rare_suffix_stays():
    line = "    IF NAMED_NOT_DESTROYED('UNIT - Salvaged Tank 04')  +0000000001000000"
    assert retailref.condition(line) == "    IF NOT NAMED_NOT_DESTROYED('UNIT - Salvaged Tank 04')  +0000000001000000"
