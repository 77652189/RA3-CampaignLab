"""SpecificSpecialPowerDelay variants on the successful aimicspon Hunt team: one delay line, nothing else differs
(no team delay, the same update/health/targets; the inherited manual warrior removed, only the automatic window read).

aidelay0 / aidelay999 (bench 2026-11-11): RUSH_ATTACK MaximumDelay 0 / 999, MinimumDelay 0. Prediction before bench:
zero lets both warriors charge together; 999 still lets the first charge, then samples a cooldown in 0..999 s, so
no second charge in the window (a sampled prediction, NOT a deterministic bound).
aidelaytype: the 999 line on PowerType AOE_ATTACK -- the warriors' RUSH_ATTACK is not delayed: predicted as zero.
aidelaymin: MinimumDelay 999, MaximumDelay 0 -- the program's draw (work/re/l4_toggle.md) is its upper end when the
range is empty or reversed, so 0: predicted as zero (a MinimumDelay taken as a floor would give 999).
"""
from missions import aimicro_bench as am


def mission(maximum, minimum=0, power='RUSH_ATTACK', name=None):
    name = name or ('Long' if maximum else 'Zero')
    m = am.built('CampAD' + name, tactic='Hunt', foes=True, spow=True)
    filename, xml, asset = m.assets[0]
    tag = (f'<SpecificSpecialPowerDelay PowerType="{power}" '
           f'MinimumDelay="{minimum}s" MaximumDelay="{maximum}s"/>')
    # SDK sequence: TargetBias*, SpecificSpecialPowerDelay*, RetreatBaseCriteria,
    # IgnoreTargets. Appending after IgnoreTargets fails BinaryAssetBuilder.
    anchor = '    <RetreatBaseCriteria'
    assert xml.count(anchor) == 1
    xml = xml.replace(anchor, '    ' + tag + '\n' + anchor)
    assert tag in xml
    m.assets[0] = filename, xml, asset
    m.facts['specific maximum'] = maximum
    m.facts['delayed'] = power == 'RUSH_ATTACK' and maximum > 0    # the draw: max when max <= min, else in [min, max]
    return m


MISSION = {'aidelay0': lambda: mission(0), 'aidelay999': lambda: mission(999),
           'aidelaytype': lambda: mission(999, power='AOE_ATTACK', name='Type'),
           'aidelaymin': lambda: mission(0, minimum=999, name='Min')}
