"""C CountModifier contrast; prediction/evidence: work/re/c_countmodifier_report.md."""
from missions import aiskirm_bench as base


def mission(modifier):
    m = base.mission('CampCMHalf' if modifier == 0.5 else 'CampCMFour', two='diff')
    pid = base.DIFF_PID
    xml = base._two_new_xml(pid, [('CNVCMBuild', 'EASY MEDIUM HARD BRUTAL', [
        f'Build="{base.NEW_PK}" Heuristic="FEWEST_UNIT" CountModifier="{modifier}"',
        f'Build="{base.NEW_JAV}" Heuristic="FEWEST_UNIT"'])])
    m.assets = [(name, xml if asset == f'AIPersonalityDefinition:{pid}' else text, asset)
                for name, text, asset in m.assets]
    m.facts['count modifier'] = modifier
    m.facts.pop('difficulty gate')
    for template, count in [(base.NEW_PK, 4), (base.NEW_JAV, 2)]:
        for i in range(count):
            m.put(template, 'east base', -500 + i * 40, 200 if count == 4 else 300,
                  side='s1', role=f'count seed {template} {i}')
    return m


MISSION = {'aicmhalf': lambda: mission(0.5), 'aicmfour': lambda: mission(4.0)}
