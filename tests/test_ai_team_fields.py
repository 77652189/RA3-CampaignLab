"""GatherWaypoint, MaxTypesOfUnits, Priority=HOTSPOT (D round 148): each bench pair differs in one field only.
The pairs' effects are readings: experimental/cnv/checks/engine_aiteamfields.readings.toml."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_pairs_differ_in_one_field_only():
    sys.path[:0] = [str(ROOT / 'experimental/cnv'), str(ROOT / 'experimental/campaign')]
    from benches.ai.tactics.scenes import aiteamfields_bench
    b = aiteamfields_bench()
    xml = {k: f().assets[0][1] for k, f in b["MISSION"].items()}
    assert xml['aigathwp'].replace(' GatherWaypoint="CNV AI WP Target"', '') == xml['aigathno']
    assert xml['aigathbad'].replace(' GatherWaypoint="CNV AI WP Nowhere"', '') == xml['aigathno']
    # the personality id ends in the mod name's last letter (aiteamfilter_bench: PID + name[-1])
    assert xml['aimaxty1'].replace('MaxTypesOfUnits="1"', 'MaxTypesOfUnits="3"').replace('CNVTeamF1', 'CNVTeamF3') \
        == xml['aimaxty3']
    assert xml['aihotdef'].replace('Priority="DEFAULT"', 'Priority="HOTSPOT"') == xml['aihotstd']
    assert xml['aihotscr'].replace('Priority="SCRIPTED"', 'Priority="STANDARD"') == xml['aihotstd']
