"""A8 tests (were make_campa8.py's CNV_TEST=1 / lose).

jump: the player's carrier jumps next to platform 1 at 5 s and should carry the four Guardians there and fight
  (a trigger area around the landing point counts the Guardians that arrived).
lose: the carrier starts at 1 % health next to platform 1's Bullfrog: shot down within seconds, Mission Lost.
"""
from missions import a8
from parts import Test, counted, square
from checks.liberty import EARLY, jumps


def jump(m):
    t = Test()
    jumps(t, a8.CARRIER, m.names['power'], 'Test Jump Target', a8.NEAR_P1, at=5.0)
    counted('Test Guardians', '守护者', t, template=a8.GUARDIAN)
    counted('Test Carrier', '自由号', t, template=m.names['unit'])
    t.areas['Test Platform 1'] = square(*a8.NEAR_P1, 250.0)
    counted('Test At P1', '守护者到平台', t, template=a8.GUARDIAN, area='Test Platform 1')
    t.expect += [('自由号', 20, '==', 1), ('守护者', 20, '>=', 3), ('守护者到平台', 0, '==', 0, 5.0 - EARLY),
                 ('守护者到平台', 12, 'ever>=', 3)]
    t.bench = [('bench_watch', dict(seconds=25, every=5, sheet=False))]
    return t


def lose(m):
    """At 1 % health the carrier waits at home, then jumps next to platform 1's Bullfrog at 5 s (starting there,
    it died before the bench was in the mission). Read: it is there first, then the mission ends (Mission Lost
    ends it at once, the counters go with it: a 0 is never shown; nothing else ends it within 20 s)."""
    m.find(a8.CARRIER).props['objectInitialHealth'] = 1
    t = Test()
    jumps(t, a8.CARRIER, m.names['power'], 'Test Bullfrog', (a8.PLATFORMS[0][0] - 60, a8.PLATFORMS[0][1] - 120), at=5.0)
    counted('Test Carrier', '自由号', t, template=m.names['unit'])
    t.expect += [('自由号', 0, 'ever==', 1), ('ENDED', 5, '', None)]
    t.bench = [('bench_watch', dict(seconds=20, every=1, sheet=False))]
    return t
