"""C: IntervalHeuristic.CountFrom, identical personality and s10 wake.

IntervalTime=25s/ActiveTime=30s: MAP_START first on at s25, AI_START
at s35. Predict home counts s24=4/4, s32=0/4, s42=0/0, total=4.
Only the first active window is covered; repeated cycles remain gap.
"""
from missions import aipoweradv_bench as setup


def mission(origin):
    gate = (f'<IntervalHeuristic IntervalTime="25s" ActiveTime="30s" '
            f'CountFrom="{origin}"/>')
    m = setup.mission('CampAIInt', 4, 0, gate=gate)
    m.name = 'CampAIIntM' if origin == 'MAP_START' else 'CampAIIntA'
    m.facts.update({'count from': origin, 'home at 32': 0 if origin == 'MAP_START' else 4})
    return m


MISSION = {'aiintmap': lambda: mission('MAP_START'), 'aiintai': lambda: mission('AI_START')}
