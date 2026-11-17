"""Count actual generated native bridge parts; native tgt rows judge selection.

Prediction at 700 units: End/End2/Center/Center2/GateHouse = 1/1/2/2/2.
Ordinary neutral plants control: all five zero. Counts encode n as n+1;
an unavailable condition cannot pass as zero. Endpoint identities are observed
separately without assuming that the builder's named objects survive generation.
Evidence and unresolved semantics: work/re/c_bridge_report.md.
BENCH: on/off PASS, encoded parts 322/33 and 111/11; endpoint alive 1/0
and 1/1. Both Bridge slots at f16 found=false with zero published candidates.
True bridge NamedObject finds only the start; this is not a Bridge positive.
"""
from parts import Script, Test


def a(m):
    t = Test()
    t.scripts.append(Script('Bridge reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters += [('BrEnds', 'ends'), ('BrCenters', 'centers')]
    t.scripts.append(Script('Bridge reset', [], [('SET_COUNTER', c, 0)
                                                for c in ('BrEnds', 'BrCenters')], once=False))
    for suffix, counter, weight in zip(('End', 'End2', 'Center', 'Center2', 'GateHouse'),
                                       ('BrEnds', 'BrEnds', 'BrCenters', 'BrCenters', 'BrEnds'),
                                       (1, 10, 1, 10, 100)):
        for n in range(8):
            t.scripts.append(Script('Bridge ' + suffix + str(n), [
                ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('neutral'),
                 2, n, 'HB_Bridge_02_' + suffix, 'Bridge count')],
                [('INCREMENT_COUNTER', (n+1)*weight, counter)], once=False))
    t.expect += [('ends', 2, '==', 322 if m.facts['native bridge'] else 111, 15),
                 ('centers', 2, '==', 33 if m.facts['native bridge'] else 11, 15)]
    for i in range(2):
        counter = f'BrNamed{i}'
        t.counters.append((counter, f'endpoint {i} alive'))
        t.scripts += [Script(counter + ' reset', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(counter + ' read', [('NAMED_NOT_DESTROYED', m.role(f'bridge {i}').name)],
                             [('SET_COUNTER', counter, 1)], once=False)]
    t.bench = [('bench_watch', dict(seconds=15, every=1, sheet=False, lines=4))]
    return t


CHECKS = {build: {'a': a} for build in ('aibridgeon', 'aibridgeoff')}
