"""Delayed UnderAttack gates with identical friendly-structure controls.

INFERRED prediction: flag activation at 3/9 seconds delays the first target
evaluation until after a real hit / after ceasefire. Native ua: gate rows,
not episode-derived clear times, decide whether that premise holds.
Evidence: work/re/c_underattack_reopen_report.md.
Measured: ordinary controls choose buildings at f49/f139; injured plant is
absent from all four candidate lists, so the post-hit positive remains a gap.
"""
import re

from missions.aiunderattack_bench import mission as original
from parts import Script


def mission():
    m = original()
    m.name = 'CampUAGate'
    filename, xml, asset = m.assets[0]
    xml = xml.replace('<AIStrategicStateDefinition ',
        '<AITargetingHeuristic id="CNVUAControl" HeuristicType="FriendlyStructure"/>'
        '\n  <AIStrategicStateDefinition ', 1)
    for i in range(4):
        pattern = rf'(<AIStrategicStateDefinition id="CNVClosest{i}".*?</AIStrategicStateDefinition>)'
        def change(match, i=i):
            state = match[0].replace('<ConstantHeuristic/>',
                f'<ScriptedFlagHeuristic FlagName="CNV UA {i}"/>')
            return re.sub(r'TargetHeuristic="[^"]+"',
                'TargetHeuristic="' + ('CNVUnderAttack' if i < 2 else 'CNVUAControl') + '"', state)
        xml, n = re.subn(pattern, change, xml, flags=re.S)
        assert n == 1
    m.assets[0] = filename, xml, asset
    start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
    for i in range(4):
        timer = f'CNV UA Gate {i}'
        start.do.append(('SET_MILLISECOND_TIMER', timer, 3.0 if i % 2 == 0 else 9.0))
        m.scripts.append(Script(f'CNV UA Gate {i}', [('TIMER_EXPIRED', timer)],
                                [('SET_FLAG', f'/CNV UA {i}', 1)]))
    m.facts['stop at'] = 3.0
    return m


MISSION = {'aiuagate': mission}
