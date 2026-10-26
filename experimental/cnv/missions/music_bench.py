"""How long a Pathfinder jump takes after the script fires its event: our timing map (experimental/music/ownmap.py
timing) plays a tracer per event, and the mission fires three of its events at irregular, known moments. A recording
of the game (experimental/music/bench_listen.py --nav) then says when each jump was heard; experimental/music/
timing.py lines the two up.

  cut    TIMING_CUT, PREP + GOTO
  plain  TIMING_PLAIN, a GOTO alone (its section routed: leaving it plays the transition first)
  into   TIMING_INTO, a GOTO alone, fired while TIMING_PLAIN's section plays

The intervals are not multiples of the sections' 8 s segments, so a jump that waits for a segment's end shows as a
delay that changes from one jump to the next. Facts: '<kind> <n>' = mission seconds it fires at (kind: cut / plain
/ into, the n-th of that kind; ownmap.TIMING names the event of each kind).
"""
import os
import sys

from maps import island
from parts import Mission, Script

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from experimental.music import ownmap, pack  # noqa: E402

SCHEDULE = [(12.0, 'cut'), (21.3, 'plain'), (33.7, 'into'), (41.1, 'cut'), (50.9, 'plain'), (58.2, 'cut'),
            (67.6, 'plain'), (76.4, 'into')]


def facts():
    seen, out = {}, {}
    for t, kind in SCHEDULE:
        seen[kind] = seen.get(kind, 0) + 1
        out[f'{kind} {seen[kind]}'] = t
    return out


def _pack():
    from experimental.music import extract
    b, lengths = ownmap.timing(extract.retail_map())
    tracks = pack.tracer_tracks(b.m, lengths)
    return pack.make(b.m, tracks)


def mission(name='CampMusic'):
    m = Mission(name=name, map=island, facts=facts(),
                music=pack.Later(_pack, {ownmap.TIMING[kind] for _, kind in SCHEDULE}))
    m.put('AlliedAntiVehicleVehicleTech1', 'west field', 0, 0, name='UNIT - CNV Music Guardian', role='listener')
    m.scripts.append(Script('CNV Music - Start', [], [('SET_MILLISECOND_TIMER', f'CNV Music {k}', t)
                                                      for k, (t, _) in enumerate(SCHEDULE)]))
    m.scripts += [Script(f'CNV Music - {k} {kind}', [('TIMER_EXPIRED', f'CNV Music {k}')],
                         [('PATH_MUSIC_PLAY_EVENT', ownmap.TIMING[kind])]) for k, (_, kind) in enumerate(SCHEDULE)]
    return m
