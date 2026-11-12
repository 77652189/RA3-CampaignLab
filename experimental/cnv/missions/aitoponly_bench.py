"""HighestPriorityEnemyPlayersOnly: missing top-tier candidate versus fallback.

Explicit priorities: s4=30 (yard only), p1=10 (barracks). Predict on stays
home, off reaches barracks. Control gives s4 the barracks: on reaches it.
Original evidence: work/re/c_toponly_report.md.
"""
import dataclasses

from missions.aitargetpick_bench import mission


def top_only(name, enabled, positive=False):
    expect = (0, 4, 0, 0) if not enabled or positive else (0, 0, 0, 4)
    m = mission(name, [('CNVHBarracks', None)], expect)
    for role in ('player yard', 'barracks') if positive else ('player yard',):
        m.cast[role] = dataclasses.replace(m.cast[role], side='s4')
        m.find(m.cast[role].name).side = 's4'
    s1, s4 = m.player('s1'), m.player('s4')
    start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
    rel = (0, 0.0, 'Enemy')
    start.do = list(start.do) + [('PLAYER_RELATES_PLAYER', s1, s4, rel),
                                 ('PLAYER_RELATES_PLAYER', s4, s1, rel)]
    wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
    wake.do = [a for a in wake.do if a[0] != 'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES']
    wake.do += [('SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY', s1, s4, 30),
                ('SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY', s1, m.player('p1'), 10)]
    asset, xml, ref = m.assets[0]
    xml = xml.replace('<AITargetingHeuristic id="CNVHBarracks" ',
                      '<AITargetingHeuristic id="CNVHBarracks" '
                      f'HighestPriorityEnemyPlayersOnly="{str(enabled).lower()}" ')
    m.assets[0] = asset, xml, ref
    return m


MISSION = {
    'aitopon': lambda: top_only('CampTopOn', True),
    'aitopoff': lambda: top_only('CampTopOff', False),
    'aitopctl': lambda: top_only('CampTopCtl', True, positive=True),
}
