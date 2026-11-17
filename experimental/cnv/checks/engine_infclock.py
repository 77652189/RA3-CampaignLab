"""E199 lossless script-frame discovery trace, independent of capture seconds.

Keep each independent mission's setup. After the hostile spy disappears,
sample NAMED_DISCOVERED on every script pass for 300 passes. Pack fifteen
successive samples per counter, least significant bit first. Replay twenty
immutable pages for thirty passes each: frame / first sample / bits / entry.
Entry means first observed spy disappearance, NOT an accepted-entry event.
No observer identity, lifetime, update rate or periodicity is inferred here.
Prediction: baseline hidden, at least one matching discovery after entry;
whether the intervening zeros form a fixed period is the measured question.
See work/re/e199_vision_clock.md. This check imports no mission content.
"""
from parts import NOT, Script, Test


def trace(m, base):
    t = base(m)
    # Setup/entry only; old reset/increment observers do not run in this probe.
    t.scripts = t.scripts[:2]
    frame, age, entry = 'Clock frame', 'Clock age', 'Clock entry'
    first, bits = 'Clock first', 'Clock bits'
    t.counters = [(frame, 'frame'), (first, 'first'), (bits, 'bits'), (entry, 'entry')]
    t.scripts += [
        Script('Clock tick', [], [('INCREMENT_COUNTER', 1, frame)], once=False),
        Script('Clock entry latch', [('NAMED_NOT_DESTROYED', m.role('enemy spy').name, NOT)],
               [('SET_COUNTER_TO_COUNTER', entry, frame), ('SET_FLAG', 'Clock entered', 1)]),
        Script('Clock age tick', [('FLAG', 'Clock entered', 1)],
               [('INCREMENT_COUNTER', 1, age)], once=False)]
    for page in range(20):
        packed = f'Clock page {page}'
        for bit in range(15):
            sample = page * 15 + bit + 1
            t.scripts.append(Script(f'Clock sample {sample}',
                [('COUNTER', age, 2, sample),
                 ('NAMED_DISCOVERED', m.player('p1'), m.role('match').name)],
                [('INCREMENT_COUNTER', 1 << bit, packed)]))
        # COUNTER 3 is >=, 1 is <=; equality is 2.
        t.scripts.append(Script(f'Clock display {page}',
            [('COUNTER', age, 3, 301 + page * 30), ('COUNTER', age, 1, 330 + page * 30)],
            [('SET_COUNTER', first, page * 15 + 1),
             ('SET_COUNTER_TO_COUNTER', bits, packed)], once=False))
    t.expect = [('entry', 1, 'ever>=', 1, 140), ('first', 1, 'ever>=', 286, 140),
                ('bits', 1, 'ever>=', 1, 140)]
    t.bench = [('bench_watch', dict(seconds=140, every=0.5, sheet=False, lines=4,
                                   until='c2==286'))]
    return t


def dual(m):
    """Final E199 run: frame / aircraft bits / vehicle bits / packed entries.

    Twenty 15-bit pages replay at age 301..900, thirty passes per page.
    Age starts at the last of the two observed disappearances. The fourth
    row is aircraft disappearance frame + 1000 * vehicle disappearance frame.
    Both entries must be below 1000 for this encoding to be unambiguous.
    Prediction from the first run: each stream has a five-pass period; phase
    relative to its own disappearance is tested, not forced into the recorder.
    """
    t = Test()
    frame, age, entry = 'Dual frame', 'Dual age', 'Dual entries'
    t.counters = [(frame, 'frame'), ('Dual air bits', 'air'),
                  ('Dual vehicle bits', 'vehicle'), (entry, 'entries')]
    t.scripts = [Script('Dual start', [], [
        ('SET_MILLISECOND_TIMER', 'Dual enter', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', obj.name, 'NO_ATTACK', 1) for obj in m.objects] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(lane + ' match').name, 'IMMOBILE_ALLOW_ROTATE', 1)
        for lane in ('air', 'vehicle')]),
        Script('Dual enter', [('TIMER_EXPIRED', 'Dual enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(lane + ' spy').name, m.role(lane).name)
            for lane in ('air', 'vehicle')]),
        Script('Dual tick', [], [('INCREMENT_COUNTER', 1, frame)], once=False)]
    for lane in ('air', 'vehicle'):
        t.scripts.append(Script('Dual latch ' + lane,
            [('NAMED_NOT_DESTROYED', m.role(lane + ' spy').name, NOT)],
            [('SET_COUNTER_TO_COUNTER', 'Dual entry ' + lane, frame),
             ('SET_FLAG', 'Dual gone ' + lane, 1)]))
    # Encode entries by adding the current frame once for air, and counting
    # 1000 per pass until vehicle disappearance (including its first pass).
    t.scripts += [
        Script('Dual encode vehicle', [('FLAG', 'Dual gone vehicle', 0)],
               [('INCREMENT_COUNTER', 1000, entry)], once=False),
        Script('Dual encode vehicle final', [('FLAG', 'Dual gone vehicle', 1)],
               [('INCREMENT_COUNTER', 1000, entry)]),
        Script('Dual encode air', [('FLAG', 'Dual gone air', 1)],
               [('COUNTER_MATH_COUNTER', entry, 0, 'Dual entry air')]),
        Script('Dual age', [('FLAG', 'Dual gone air', 1), ('FLAG', 'Dual gone vehicle', 1)],
               [('INCREMENT_COUNTER', 1, age)], once=False)]
    for page in range(20):
        for lane in ('air', 'vehicle'):
            packed = f'Dual {lane} page {page}'
            for bit in range(15):
                sample = page * 15 + bit + 1
                t.scripts.append(Script(f'Dual {lane} sample {sample}',
                    [('COUNTER', age, 2, sample),
                     ('NAMED_DISCOVERED', m.player('p1'), m.role(lane + ' match').name)],
                    [('INCREMENT_COUNTER', 1 << bit, packed)]))
            t.scripts.append(Script(f'Dual {lane} display {page}',
                [('COUNTER', age, 3, 301 + page * 30), ('COUNTER', age, 1, 330 + page * 30)],
                [('SET_COUNTER_TO_COUNTER', 'Dual ' + lane + ' bits', packed)], once=False))
    t.expect = [('air', 1, 'ever>=', 1, 140), ('vehicle', 1, 'ever>=', 1, 140)]
    t.bench = [('bench_watch', dict(seconds=140, every=0.5, sheet=False, lines=4,
                                   until='c1>=1100'))]
    return t


CHECKS = {'engine_infclock': {'a': dual}}


