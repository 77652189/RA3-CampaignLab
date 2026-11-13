"""C: PowerAdvantageHeuristic.Value, fixed Above=true and 4:8 Guardians.

Pre-run s40 home/AI total/player prediction: Value=1.0 gives 4/4/8;
Value=0.1 gives 0/4/8. Only Value changes in the personality.
This brackets the predicted ratio 0.25; the exact formula remains gap.
"""
from missions import aipoweradv_bench as setup


def mission(value):
    gate = (f'<PowerAdvantageHeuristic Value="{value}" Above="true" '
            'IncludeOwnDefenses="false" IncludeEnemyDefenses="false"/>')
    home = 4 if value == 1.0 else 0
    m = setup.mission('CampAIPVal', 4, 8, gate=gate, expect=int(not home))
    m.name = 'CampAIPVal1' if home else 'CampAIPVal01'
    m.facts.update({'power value': value, 'home at 40': home})
    return m


MISSION = {'aipval1': lambda: mission(1.0), 'aipval01': lambda: mission(0.1)}
