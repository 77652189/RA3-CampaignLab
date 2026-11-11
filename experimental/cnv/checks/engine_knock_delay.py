"""C: ordinary delayed detonation, 1.9s / 1.2s in one bench run.

Reuse knock_z's observable tall neighbour and default Physics. The second
rocket uses the strong lane (1500 south), with identical local geometry.
Prediction before bench: 15fps gives 28.5 / 18 delay frames (integer rounding
of 28.5 must be read, not assumed). Collision damage remains immediate99%,
neighbours100%; no push before delay, then the same14-frame trajectory as Z.
Observed corrected bench: health-frame counters174/173, shocks204/192.
Delay/collision phase conversion is not settled; this is a diagnostic check,
not an inventory replay. Delayed sample1 occurs in the shock frame, is held
next frame, then samples2..14 follow. See the private C handoff for evidence.
"""
import copy
from parts import Script
from checks import engine_knock_z as base
from checks import engine_knock_probe as probe

SHORT = 'CNV_DelayShort'


def mission():
    m = base.mission()
    m.name = 'CampKD'
    for o in m.objects:
        if o.name == probe.name('strong', 'gun'):
            o.template = SHORT
        if o.name == probe.name('strong', 'near'):
            o.template = base.TALL
    return m


def check(m):
    t = base.check(m)
    gun = next(u for u in m.units if u.id == 'CNV_KnockRocket')
    short = copy.deepcopy(gun)
    short.id = SHORT
    short.xml = short.xml.replace('CNV_KnockRocket', SHORT)
    short.names = {k: v.replace('CNV_KnockRocket', SHORT) for k, v in short.names.items()}
    short.files = {k.replace('CNV_KnockRocket', SHORT): v.replace('CNV_KnockRocket', SHORT)
                   for k, v in short.files.items()}
    short.also = [v.replace('CNV_KnockRocket', SHORT) for v in short.also]
    short.link = [v.replace('CNV_KnockRocket', SHORT) for v in short.link]
    for u, delay in ((gun, '1.9s'), (short, '1.2s')):
        old = '<MetaImpactNugget ShockWaveAmount="89" ShockWaveRadius="250"/>'
        assert u.xml.count(old) == 1
        u.xml = u.xml.replace(old, old[:-2] + f' ShockwaveDelaySeconds="{delay}"/>')
    m.units.append(short)
    fire = next(s for s in t.scripts if s.name == 'Test - fire')
    # Use the existing delayed-fire/stop script phases, not a second timer.
    fire.do += [('UNIT_CHANGE_OBJECT_STATUS', probe.name('strong', 'gun'), 'NO_ATTACK', 0),
                     ('NAMED_ATTACK_NAMED', probe.name('strong', 'gun'), probe.name('strong', 'man'))]
    stop = next(s for s in t.scripts if s.name == 'Test - stop 0')
    stop.do.append(('UNIT_CHANGE_OBJECT_STATUS', probe.name('strong', 'gun'), 'NO_ATTACK', 1))
    # Count full-health script frames. Their exact offset from the collision's
    # engine frame must be supplied by D; do not infer it from these counters.
    # Two target counters pack first-hit frame +1000 for the one percent loss;
    # the two neighbours retain health counters. This prevents a silent gun
    # from passing a health-only neighbour check.
    t.scripts = [s for s in t.scripts if not s.name.startswith(('Test - health', 'Test - dead'))]
    t.counters, t.expect = [], []
    for lane in ('rocket', 'strong'):
        victim = probe.name(lane, 'man')
        c = 'CNV_Delay_' + lane
        t.counters.extend([(c, lane+' hit'), (c+'HP', lane+' near')])
        t.scripts.extend([
            Script('Test - frames '+lane, [('UNIT_HEALTH', victim, 2, 100)],
                   [('INCREMENT_COUNTER', 1, c)], once=False),
            Script('Test - lost '+lane, [('UNIT_HEALTH', victim, 0, 100)],
                   [('INCREMENT_COUNTER', 1000, c)]),
            Script('Test - neighbour '+lane, [],
                   [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', probe.name(lane, 'near'), c+'HP')], once=False)])
        t.expect.extend([(lane+' hit', 18, 'ever>=', 1000, 20),
                         (lane+' near', 18, '==', 100, 20)])
    t.bench = [('bench_watch', dict(seconds=probe.RUNS['land'], every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_knock_delay': mission}
CHECKS = {'engine_knock_delay': {'a': check}}

