"""MaximumDelay-only pair on the successful aimicspon Hunt team.

Prediction before bench: zero permits both warriors to charge together; long
still permits the first charge, then samples a RUSH_ATTACK cooldown in 0..999s.
Thus long is expected to have no simultaneous pair in the automatic window,
but that is a sampled prediction, NOT a deterministic lower-bound guarantee.
Both builds keep MinimumDelay=0, no team delay, the same update/health/targets.
The old aimicmed all-zero run is not a successful delay control.
Only the automatic window is measured; remove the inherited manual warrior.
"""
from missions import aimicro_bench as am


def mission(maximum):
    m = am.built('CampAD' + ('Long' if maximum else 'Zero'), tactic='Hunt', foes=True, spow=True)
    filename, xml, asset = m.assets[0]
    tag = (f'<SpecificSpecialPowerDelay PowerType="RUSH_ATTACK" '
           f'MinimumDelay="0s" MaximumDelay="{maximum}s"/>')
    # SDK sequence: TargetBias*, SpecificSpecialPowerDelay*, RetreatBaseCriteria,
    # IgnoreTargets. Appending after IgnoreTargets fails BinaryAssetBuilder.
    anchor = '    <RetreatBaseCriteria'
    assert xml.count(anchor) == 1
    xml = xml.replace(anchor, '    ' + tag + '\n' + anchor)
    assert tag in xml
    m.assets[0] = filename, xml, asset
    m.facts['specific maximum'] = maximum
    return m


MISSION = {'aidelay0': lambda: mission(0), 'aidelay999': lambda: mission(999)}
