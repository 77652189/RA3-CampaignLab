"""Read missions/aiwake_bench.py's aialobsw: when the AI's pre-placed Peacekeepers leave home, against the gated wake.

Prediction (H-a, the cheaper reading, handoff-b section 160): the old wake ran at f0; gated, nothing leaves before
the wake -- 步兵在家 4 to s29, someone at the far plant after it. A FAIL with 步兵在家 0 by ~s10 is H-b (the side
runs its teams before the wake); the team log (ra3ext.log, CNVTeams) gives the frame the named team fills.

MEASURED (bench 11-13, CampAlObsWW_mcp_1113_003603, FAIL as a prediction): the wake ran at pass 450 (唤醒前 stops
at 450, ~s28), yet 步兵在家 4 -> 0 over s10-s12 and 到远厂 4 from s17 -- the 10 s wake's timeline unchanged; the
team log has the SimpleAttack team empty at f17, 4 members at f21, the first team move at f26, as aialobslo.
H-a no (the old wake did not run at f0); H-b yes: a side with a personality runs its states and teams from the
start, before UNIT_AI_TRANSFER_ALL / MAKE_BASE. The simulator's AI starts at the wake (simai.SimAI.attach) -- to fix.
"""
from checks import engine_airetreat as ar
from checks import engine_aistate as st


def probe(m):
    f = m.facts                         # the mission publishes its counters and wake tick (checks ask the mission)
    t = ar.a(m, 'airet')
    t.counters = [c for c in t.counters if c[1] in ('步兵在家', '到远厂')] + [(f['tick counter'], '帧'),
                                                                     (f['pre counter'], '唤醒前')]
    t.expect = [('步兵在家', 1, '==', 4, 29), ('唤醒前', 31, '>=', f['wake tick'] - 1, 60), ('到远厂', 31, 'ever>=', 1, 70)]
    t.bench = [('bench_watch', dict(seconds=72, every=1, sheet=False, lines=len(t.counters)))]
    return t


def const(m):
    """aistateconstw: H-g predicts 步兵在家 / 坦克在家 4 to ~s30 and 0 by ~s36; out by s16 = targets found before
    the wake."""
    f = m.facts
    t = st.a(m)
    t.counters = [c for c in t.counters if c[1] in ('步兵在家', '坦克在家')] + [(f['tick counter'], '帧'),
                                                                        (f['pre counter'], '唤醒前')]
    t.expect = [('步兵在家', 1, '==', 4, 26), ('坦克在家', 1, '==', 4, 26), ('步兵在家', 31, 'ever==', 0, 45)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aialobsw': {'w': probe}, 'aistateconstw': {'w': const}}
