"""Retreat fallback distance A/B: airetf, changing only 100 versus 500.

Keep the original guards, power threshold, base distance and flag timing. The
short latch should permit an earlier turn back towards the enemy once enemies
leave the search list; the long latch should carry the team farther home.
Area counts bound movement only; they do not expose the micro state's exit.
"""
from missions import airetreat_bench as ar


def mission(name, distance):
    m = ar.mission(name, guards=ar.GUARDS, flag=True,
                   RetreatPowerAdvantage='0.2', RetreatMinDistanceToFallback=str(distance))
    m.facts['fallback distance'] = distance
    x, y = m.site('east base')[:2]
    m.facts['fallback midway'] = (x, y - 600)
    return m


MISSION = {
    'aifbshort': lambda: mission('CampAIFbShort', 100),
    'aifblong': lambda: mission('CampAIFbLong', 500),
}
