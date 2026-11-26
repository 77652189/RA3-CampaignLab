"""C: ordinary delayed detonation, 1.9s / 1.2s in one bench run.

Reuse knock_z's observable tall neighbour and default Physics. The second
rocket uses the strong lane (1500 south), with identical local geometry.
Prediction before bench: 15fps gives 28.5 / 18 delay frames (integer rounding
of 28.5 must be read, not assumed). Collision damage remains immediate99%,
neighbours100%; no push before delay, then the same14-frame trajectory as Z.
Observed corrected bench: health-frame counters174/173, shocks204/192.
A380: the simulator sends the shock off Damage's queue (engine/combat/meta_impact);
b's reading (engine_knock_delay.readings.toml) counts both frames. Delayed sample1 occurs in the shock frame, is held
next frame, then samples2..14 follow. See the private C handoff for evidence.
"""
import copy
from model import square
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


def home(m):
    """b (A380): a, each neighbour's health counter swapped for its script frames still on its spot (a 3 box), so
    one run gives the collision (hit - 1000) and the shock (home) of each lane. Prediction from a's raw ra3ext.log
    (shocks 204 / 192) and counters: hit 1174 / 1173, home 204 / 192 -- home - (hit - 1000) = D + 1 = 30 / 19."""
    t = check(m)
    t.scripts = [s for s in t.scripts if not s.name.startswith('Test - neighbour')]
    t.counters, t.expect = [c for c in t.counters if not c[1].endswith('near')], []
    for lane in ('rocket', 'strong'):
        near = next(o for o in m.objects if o.name == probe.name(lane, 'near'))
        c, area = 'CNV_Delay_' + lane + 'Home', probe.name(lane, 'near home')
        t.areas[area] = square(near.x, near.y, 3)
        t.counters.append((c, lane + ' home'))
        t.scripts.append(Script('Test - home ' + lane, [('NAMED_INSIDE_AREA', near.name, area)],
                                [('INCREMENT_COUNTER', 1, c)], once=False))
        t.expect.extend([(lane + ' hit', 18, 'ever>=', 1000, 20), (lane + ' home', 18, '>=', 150, 20)])
    return t


MISSION = {'engine_knock_delay': mission}
CHECKS = {'engine_knock_delay': {'a': check, 'b': home}}

