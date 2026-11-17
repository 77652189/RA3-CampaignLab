"""C line: change only base's InformTarget Max factor from 1.15 to 1.6.

Prediction before running: same slow shell, damage150, launch302, hit377,
actual damage/removal389 and automatic shield before damage. Default high/low
controls keep expiry404; base expiry becomes444 (launch +142).
The previous hit377/expiry404 constrain t to [75/.85, 102/1.15),
so int(t*1.6+.99) is142 throughout that interval. No fitted distance needed.
Expiry is the entry's recorded deadline; damage removes it before that time,
so this check does not measure the exact automatic expiry-cleanup boundary.
Reuse D's read-only probe without changing injection or the AI recipe.

First run: incoming frames exactly matched; automatic controls all passed.
Inherited manual assertions at43s failed at the first sample, then passed
from44s onward. Preserve that FAIL in work/logs/c_inform_max_first_result.json;
only the manual observation window moves to45s, with game scripts unchanged.
"""
from checks import engine_inform_ai as inform
from checks import engine_inform_probe as probe


def mission():
    m = probe.mission()
    m.name = 'CampIMax'
    return m


def check(m):
    unit = m.units[inform.LANES.index('base')]
    assert unit.xml.count('<InformTargetNugget/>') == 1
    unit.xml = unit.xml.replace('<InformTargetNugget/>',
                                '<InformTargetNugget MaxTimeToImpactFudgeFactor="1.6"/>', 1)
    t = probe._probed(m, inform.check(m))
    t.expect = [(row[0], 45, *row[2:]) if row[1] == 43 else row for row in t.expect]
    return t


MISSION = {'engine_inform_max': mission}
CHECKS = {'engine_inform_max': {'a': check}}
