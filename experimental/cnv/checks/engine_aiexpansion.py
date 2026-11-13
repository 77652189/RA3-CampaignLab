"""C Expansion readings; candidate field eligibility remains INFERRED.

Two candidate-field areas and ordinary entity control, plus home.
Team/command logs come from the mission's passive CNVTeams host. First Expansion
reading: east=4, bluff=0, entity=0 at s30; expectations below retain those values.
"""
from parts import Test, Script, counted, square


def a(m):
    t = Test()
    s1 = m.player('s1')
    tank, = m.cnv_units
    plant = m.find(m.role('plant').name)
    points = [('east', m.facts['candidate east'], '候选东'),
              ('bluff', m.facts['candidate bluff'], '候选崖'),
              ('entity', (plant.x, plant.y), '普通实体'),
              ('home', m.site('east base'), '在家')]
    for key, xy, label in points:
        area = 'CNV Expansion ' + key
        t.areas[area] = square(*xy, 350.0)
        counted('CNV_Exp_' + key, label, t, template=tank, player=s1, area=area)
    t.scripts.append(Script('Test - keep targets', [],
                           [('UNIT_SET_HEALTH', m.role(r).name, 100.0)
                            for r in ('plant', 'barracks', 'tank')], once=False))
    if 'base preferred not' in m.facts:
        # Readings only: captured base type/eligibility is not observed.
        # See work/re/c_basenot_report.md; ore fields do not establish bases.
        pass
    elif 'base sort order' in m.facts:
        # BaseSelection.SortOrder contrast: readings only. Two ore fields do
        # not establish two eligible bases or their ages. See work/re/c_basesort_report.md.
        pass
    elif m.facts['expansion']:
        t.expect += [('候选东', 30, '==', 4, 40), ('候选崖', 30, '==', 0, 40),
                     ('普通实体', 30, '==', 0, 40)]
    else:
        # Reach the entity by s30. A one-second terminal window can contain no
        # capture on a busy bench (first run: s14..68 all four, no s30 sample).
        t.expect.append(('普通实体', 1, 'ever>=', 4, 30))
    t.bench = [('bench_watch', dict(seconds=79 if m.facts.get('dual bases') else 49,
                                  every=1, sheet=False, lines=4))]
    return t


CHECKS = {key: {'a': a} for key in ('aiexpc', 'aiexpctl', 'aibsold', 'aibsnew', 'aibncap', 'aibnnone',
                                  'aibs2old', 'aibs2new')}


def buildings(m):
    """Second-round control: confirm both physical yards, beside the team readings.

    Physical yards are not proof of two AI base records or their eligibility.
    """
    t = Test()
    s1 = m.player('s1')
    tank, = m.cnv_units
    points = [('east', m.facts['candidate east'], tank, '候选东'),
              ('bluff', m.facts['candidate bluff'], tank, '候选崖'),
              ('old yard', m.site('east base'), 'AlliedConstructionYard', '东建厂'),
              ('new yard', m.point('new yard'), 'AlliedConstructionYard', '崖建厂')]
    for key, xy, template, label in points:
        area = 'CNV Dual ' + key
        t.areas[area] = square(*xy, 350.0)
        counted('CNV_Dual_' + key.replace(' ', '_'), label, t,
                template=template, player=s1, area=area)
    t.scripts.append(Script('Test - keep targets', [],
                           [('UNIT_SET_HEALTH', m.role(r).name, 100.0)
                            for r in ('plant', 'barracks', 'tank')], once=False))
    t.expect = [('东建厂', 30, '==', 1, 40), ('崖建厂', 30, '==', 1, 40)]
    t.bench = [('bench_watch', dict(seconds=79, every=1, sheet=False, lines=4))]
    return t


CHECKS['aibs2old']['b'] = buildings
CHECKS['aibs2new']['b'] = buildings
CHECKS['aibs3old'] = {'b': buildings}
CHECKS['aibs3new'] = {'b': buildings}
CHECKS['aibn2old'] = {'b': buildings}
CHECKS['aibn2new'] = {'b': buildings}
CHECKS['aibp1old'] = {'b': buildings}
CHECKS['aibp1new'] = {'b': buildings}
