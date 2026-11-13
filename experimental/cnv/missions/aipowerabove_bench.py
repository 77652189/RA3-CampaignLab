"""C: PowerAdvantageHeuristic.Above, fixed four versus eight Guardians.

Only Above changes in the personality. With identical armies' templates,
the predicted power ratio is 0.25, below the fixed Value=1.0.
At s40 Above=true should leave four home; false should send all four.
Exact evaluation frames, other ratios and defense inclusion remain gap.
"""
from missions import aipoweradv_bench as setup


def mission(above):
    gate = (f'<PowerAdvantageHeuristic Value="1.0" Above="{str(above).lower()}" '
            'IncludeOwnDefenses="false" IncludeEnemyDefenses="false"/>')
    m = setup.mission('CampAIPAb', 4, 8, gate=gate, expect=int(not above))
    m.name = 'CampAIPAbT' if above else 'CampAIPAbF'
    m.facts.update({'power above': above, 'home at 40': 4 if above else 0})
    return m


MISSION = {'aipabtrue': lambda: mission(True), 'aipabfalse': lambda: mission(False)}
