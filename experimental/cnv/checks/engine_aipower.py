"""Engine probe: the protocol a computer player buys (missions/aipower_bench.py; simtech.Book.ai_buy). The enemy s1
(Soviet, one starting point, AI not woken) with a personality of the probe's; X = PlayerTech_Soviet_MagneticSatellite_
Rank_1, Y = PlayerTech_Soviet_OrbitalRefuse_Rank1 (both 1 point, only PlayerTech_Soviet needed). Counters: 有X, 有Y
(PLAYER_HAS_PLAYER_TECH of s1), 点数 (s1's protocol points, every frame). The model (program read) in brackets:
  aipwra  one PowerChoice X                      [X bought, 点数 1 -> 0 from frame 10]
  aipwrb  Y Weight 0% then X Weight 100%         [X bought, never Y]
  aipwrd  stock DefaultPersonality, no PowerChoice  [nothing bought, 点数 stays 1]
  aipwre  X 50% then Y 50%  /  aipwrf  Y 50% then X 50%   [check e: only 点数 == 0 from s8, no pick expected]

读数
Bench 2026-11-09 (one run each, 76 frames s0.7-s75.7; counters 有X, 有Y, 点数; mods CampAIPwrAA / BA / DA):
  aipwra  s1-s76: 1 0 0   PASS (X bought by s1 -- the first reading -- and the point gone)
  aipwrb  s1-s76: 1 0 0   PASS (X bought, never Y, though Y is listed first at 0%)
  aipwrd  s1-s76: 0 0 1   PASS (nothing bought, the point kept all 75 s)
Bench 2026-11-09, check e (16 frames s1.1-s16.1; counters 有X, 有Y, 点数; first reading s1 = final s16; mods CampAIPwrEE / FE):
  aipwre  run 1: 1 0 0   X bought (X listed first)
  aipwre  run 2: 1 0 0   X bought
  aipwre  run 3: 1 0 0   X bought
  aipwre  run 4: 1 0 0   X bought
  aipwrf  run 1: 0 1 0   Y bought (Y listed first)
  aipwrf  run 2: 0 1 0   Y bought
  aipwrf  run 3: 0 1 0   Y bought
Which of several nonzero-weight lines is drawn is not tested here.
"""
from parts import Script, Test
from checks import engine_protocol as ep

RUN = 75.0


def _check(m, want_x, want_pts):
    t = Test()
    s1 = m.player('s1')
    ep._sum(t, 'CNV_PW_X', '有X', [(1, ('PLAYER_HAS_PLAYER_TECH', s1, 'PlayerTech_Soviet_MagneticSatellite_Rank_1'))])
    ep._sum(t, 'CNV_PW_Y', '有Y', [(1, ('PLAYER_HAS_PLAYER_TECH', s1, 'PlayerTech_Soviet_OrbitalRefuse_Rank1'))])
    ep._points(t, 'CNV_PW_Pts', '点数', s1)
    t.expect += [('有X', 8, '==', want_x, RUN), ('有Y', 1, '==', 0, RUN), ('点数', 8, '==', want_pts, RUN)]
    ep._watch(t, RUN, 1.0)
    return t


def a(m):
    return _check(m, 1, 0)


def d(m):
    return _check(m, 0, 1)


def e(m):
    """Two equal-weight lines: no expectation on which, only that one point was spent (点数 0 at s8)."""
    t = Test()
    s1 = m.player('s1')
    ep._sum(t, 'CNV_PW_X', '有X', [(1, ('PLAYER_HAS_PLAYER_TECH', s1, 'PlayerTech_Soviet_MagneticSatellite_Rank_1'))])
    ep._sum(t, 'CNV_PW_Y', '有Y', [(1, ('PLAYER_HAS_PLAYER_TECH', s1, 'PlayerTech_Soviet_OrbitalRefuse_Rank1'))])
    ep._points(t, 'CNV_PW_Pts', '点数', s1)
    t.expect += [('点数', 8, '==', 0, 15.0)]
    ep._watch(t, 15.0, 1.0)
    return t


CHECKS = {'aipwra': {'a': a}, 'aipwrb': {'a': a}, 'aipwrd': {'a': d},
          'aipwre': {'e': e}, 'aipwrf': {'e': e}}
